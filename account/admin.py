from django.contrib import admin
from .models import GPTAccount


@admin.register(GPTAccount)
class GPTAccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'webhook_url', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('email', 'api_key')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('Account Info', {
            'fields': ('email', 'api_key', 'webhook_url', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
