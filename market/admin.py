from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import MarketNode, MarketAnalysisJob


@admin.register(MarketNode)
class MarketNodeAdmin(admin.ModelAdmin):
    list_display = ['title', 'level', 'status', 'account', 'value_added', 'employment', 'created_at']
    list_filter = ['status', 'level', 'created_at']
    search_fields = ['title', 'account__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'analyzed_at', 'related_message_requests_link']
    raw_id_fields = ['account', 'parent']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'account', 'title', 'parent', 'level')
        }),
        ('Status', {
            'fields': ('status', 'analyzed_at')
        }),
        ('Related Data', {
            'fields': ('related_message_requests_link',)
        }),
        ('Economic Data (JSON)', {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def related_message_requests_link(self, obj):
        """Show links to related MessageRequests"""
        from chat.models import MessageRequest
        
        # Find MessageRequests that contain this node's title
        requests = MessageRequest.objects.filter(
            message__icontains=obj.title,
            account=obj.account
        ).order_by('-queued_at')[:10]
        
        if not requests:
            return "No related MessageRequests found"
        
        links = []
        for req in requests:
            url = reverse('admin:chat_messagerequest_change', args=[req.id])
            status_color = {
                'idle': 'gray',
                'executing': 'blue',
                'done': 'green',
                'failed': 'red'
            }.get(req.status, 'gray')
            
            links.append(
                f'<a href="{url}" style="color: {status_color}; margin-right: 10px;">'
                f'{req.id} ({req.status}) - {req.queued_at.strftime("%Y-%m-%d %H:%M")}'
                f'</a>'
            )
        
        return format_html('<br>'.join(links))
    
    related_message_requests_link.short_description = 'Related MessageRequests'


@admin.register(MarketAnalysisJob)
class MarketAnalysisJobAdmin(admin.ModelAdmin):
    list_display = ['root_node', 'status', 'progress_percentage', 'completed_nodes', 'total_nodes', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['root_node__title', 'account__email']
    readonly_fields = ['id', 'progress_percentage', 'created_at', 'started_at', 'completed_at']
    raw_id_fields = ['account', 'root_node']
