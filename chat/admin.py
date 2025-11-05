from django.contrib import admin
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
    readonly_fields = ('id', 'queued_at', 'started_at', 'completed_at', 'webhook_sent_at')
    ordering = ('-queued_at',)
    list_select_related = ('account', 'chat')
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
        ('Webhook', {
            'fields': ('webhook_sent', 'webhook_sent_at')
        }),
        ('Timestamps', {
            'fields': ('queued_at', 'started_at', 'completed_at')
        }),
    )
