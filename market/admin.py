from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import redirect
from django.contrib import messages
from django.core.management import call_command
from .models import MarketNode, MarketAnalysisJob


@admin.register(MarketNode)
class MarketNodeAdmin(admin.ModelAdmin):
    list_display = ['title', 'level', 'status', 'account', 'value_added', 'employment', 'created_at']
    list_filter = ['status', 'level', 'created_at']
    search_fields = ['title', 'account__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'analyzed_at', 'related_message_requests_link', 'reprocess_button']
    raw_id_fields = ['account', 'parent']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'account', 'title', 'parent', 'level')
        }),
        ('Status', {
            'fields': ('status', 'analyzed_at')
        }),
        ('Related Data', {
            'fields': ('related_message_requests_link', 'reprocess_button')
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
        """Show the ONE MessageRequest linked to this node via OneToOneField"""
        if not obj.message_request:
            return format_html('<span style="color: gray;">No MessageRequest linked</span>')
        
        req = obj.message_request
        url = reverse('admin:chat_messagerequest_change', args=[req.id])
        status_color = {
            'idle': 'gray',
            'executing': 'blue',
            'done': 'green',
            'failed': 'red'
        }.get(req.status, 'gray')
        
        return format_html(
            '<a href="{}" style="color: {};">{} ({}) - {}</a>',
            url,
            status_color,
            req.id,
            req.status,
            req.queued_at.strftime("%Y-%m-%d %H:%M")
        )
    
    related_message_requests_link.short_description = 'Linked MessageRequest'
    
    def reprocess_button(self, obj):
        """Show a button to reprocess this node"""
        if obj.pk:
            url = reverse('admin:reprocess_market_node', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" style="padding: 10px 15px; background-color: #417690; '
                'color: white; text-decoration: none; border-radius: 4px; display: inline-block;">'
                'Reprocess Node</a>',
                url
            )
        return "Save the node first"
    
    reprocess_button.short_description = 'Actions'
    
    def get_urls(self):
        """Add custom URL for reprocessing"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/reprocess/',
                self.admin_site.admin_view(self.reprocess_node_view),
                name='reprocess_market_node',
            ),
        ]
        return custom_urls + urls
    
    def reprocess_node_view(self, request, object_id):
        """Handle the reprocess action"""
        try:
            node = MarketNode.objects.get(pk=object_id)
            
            # Run the management command
            from io import StringIO
            import sys
            
            # Capture command output
            output = StringIO()
            call_command('reprocess_market_node', str(node.id), stdout=output)
            
            # Show success message with output
            messages.success(request, f"Node reprocessed successfully!\n\n{output.getvalue()}")
            
        except MarketNode.DoesNotExist:
            messages.error(request, f"MarketNode with ID '{object_id}' not found")
        except Exception as e:
            messages.error(request, f"Error reprocessing node: {str(e)}")
        
        # Redirect back to the change page
        return redirect('admin:market_marketnode_change', object_id)


@admin.register(MarketAnalysisJob)
class MarketAnalysisJobAdmin(admin.ModelAdmin):
    list_display = ['root_node', 'status', 'progress_percentage', 'completed_nodes', 'total_nodes', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['root_node__title', 'account__email']
    readonly_fields = ['id', 'progress_percentage', 'created_at', 'started_at', 'completed_at']
    raw_id_fields = ['account', 'root_node']
