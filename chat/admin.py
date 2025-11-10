from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from .models import Chat, MessageRequest


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('title', 'chat_id', 'account', 'created_at', 'updated_at')
    list_filter = ('account', 'created_at', 'updated_at')
    search_fields = ('title', 'chat_id', 'account__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)
    list_select_related = ('account',)


@admin.register(MessageRequest)
class MessageRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'status', 'response_type', 'thinking_time', 'queued_at', 'completed_at')
    list_filter = ('status', 'response_type', 'thinking_time', 'webhook_sent', 'queued_at')
    search_fields = ('id', 'account__email', 'message', 'response')
    readonly_fields = ('id', 'queued_at', 'started_at', 'completed_at', 'webhook_sent_at', 'related_market_node_link')
    ordering = ('-queued_at',)
    list_select_related = ('account', 'chat')
    actions = ['reprocess_market_node_action']
    
    fieldsets = (
        ('Request Info', {
            'fields': ('id', 'account', 'chat', 'message')
        }),
        ('Options', {
            'fields': ('response_type', 'thinking_time')
        }),
        ('Status', {
            'fields': ('status', 'response', 'error_message')
        }),
        ('Related Data', {
            'fields': ('related_market_node_link',)
        }),
        ('Webhook', {
            'fields': ('webhook_sent', 'webhook_sent_at')
        }),
        ('Timestamps', {
            'fields': ('queued_at', 'started_at', 'completed_at')
        }),
    )
    
    def related_market_node_link(self, obj):
        """Show link to related MarketNode if this is a market analysis request"""
        from market.models import MarketNode
        import json
        import re
        
        # Strategy 1: Try to extract node name from JSON in the message
        matching_nodes = []
        
        # Look for "name": "Node Title" pattern in the message
        name_pattern = r'"name":\s*"([^"]+)"'
        matches = re.findall(name_pattern, obj.message)
        
        if matches:
            # Get the first name (usually the parent node)
            node_title = matches[0]
            
            # Find nodes with this exact title
            nodes = MarketNode.objects.filter(
                account=obj.account,
                title__iexact=node_title  # Case-insensitive exact match
            ).order_by('-created_at')
            
            matching_nodes.extend(nodes[:5])
        
        # Strategy 2: Fallback - check if any node title appears in message
        if not matching_nodes:
            nodes = MarketNode.objects.filter(
                account=obj.account
            ).order_by('-created_at')
            
            for node in nodes[:50]:  # Check recent 50 nodes
                # Use case-insensitive search
                if node.title.lower() in obj.message.lower():
                    matching_nodes.append(node)
                    if len(matching_nodes) >= 5:
                        break
        
        if not matching_nodes:
            return "No related MarketNode found"
        
        links = []
        for node in matching_nodes[:5]:  # Show top 5 matches
            url = reverse('admin:market_marketnode_change', args=[node.id])
            status_color = {
                'pending': 'gray',
                'analyzing': 'blue',
                'completed': 'green',
                'failed': 'red'
            }.get(node.status, 'gray')
            
            links.append(
                f'<a href="{url}" style="color: {status_color}; margin-right: 10px;">'
                f'{node.title} (Level {node.level}, {node.status})'
                f'</a>'
            )
        
        return format_html('<br>'.join(links))
    
    related_market_node_link.short_description = 'Related MarketNode'
    
    def reprocess_market_node_action(self, request, queryset):
        """Admin action to reprocess market nodes from MessageRequests"""
        from market.models import MarketNode
        from market.services import MarketAnalysisService
        
        processed = 0
        errors = []
        
        for message_request in queryset:
            # Check if status is DONE and has response
            if message_request.status != MessageRequest.Status.DONE:
                errors.append(f"MessageRequest {message_request.id}: Status is not DONE")
                continue
            
            if not message_request.response:
                errors.append(f"MessageRequest {message_request.id}: No response available")
                continue
            
            # Find related MarketNode using improved matching
            import re
            matching_node = None
            
            # Strategy 1: Extract node name from JSON in message
            name_pattern = r'"name":\s*"([^"]+)"'
            matches = re.findall(name_pattern, message_request.message)
            
            if matches:
                node_title = matches[0]
                # Try exact match first
                matching_node = MarketNode.objects.filter(
                    account=message_request.account,
                    title__iexact=node_title
                ).order_by('-created_at').first()
            
            # Strategy 2: Fallback - search by title substring
            if not matching_node:
                nodes = MarketNode.objects.filter(
                    account=message_request.account
                ).order_by('-created_at')
                
                for node in nodes[:50]:
                    if node.title.lower() in message_request.message.lower():
                        matching_node = node
                        break
            
            if not matching_node:
                errors.append(f"MessageRequest {message_request.id}: No matching MarketNode found")
                continue
            
            # Reprocess the node
            try:
                service = MarketAnalysisService(message_request.account)
                analysis_data = service._parse_llm_response(message_request.response)
                
                if not analysis_data:
                    errors.append(f"Node {matching_node.title}: Failed to parse response")
                    continue
                
                # Add metadata
                from django.utils import timezone
                analysis_data['metadata'] = {
                    'analysis_date': timezone.now().isoformat(),
                    'llm_response': message_request.response,
                    'chat_id': message_request.chat.chat_id if message_request.chat else None,
                    'request_id': str(message_request.id),
                    'reprocessed_via_admin': True
                }
                
                # Update the node
                matching_node.mark_completed(analysis_data)
                
                # Create child nodes if not at max depth
                if matching_node.level < 3:
                    children = matching_node.create_child_nodes()
                    self.message_user(
                        request,
                        f"✓ Reprocessed '{matching_node.title}' and created {len(children)} child nodes",
                        messages.SUCCESS
                    )
                else:
                    self.message_user(
                        request,
                        f"✓ Reprocessed '{matching_node.title}' (max depth, no children created)",
                        messages.SUCCESS
                    )
                
                processed += 1
                
            except Exception as e:
                errors.append(f"Node {matching_node.title}: {str(e)}")
        
        # Show summary
        if processed > 0:
            self.message_user(
                request,
                f"Successfully reprocessed {processed} market node(s)",
                messages.SUCCESS
            )
        
        for error in errors:
            self.message_user(request, f"✗ {error}", messages.ERROR)
    
    reprocess_market_node_action.short_description = "Reprocess related MarketNode(s)"
