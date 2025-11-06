from django.db import models
from account.models import GPTAccount
import uuid


class Chat(models.Model):
    chat_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text="ChatGPT website chat ID (filled by extension)")
    account = models.ForeignKey(GPTAccount, on_delete=models.CASCADE, related_name='chats')
    title = models.CharField(max_length=500, null=True, blank=True, help_text="Chat title (filled by extension)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chat"
        verbose_name_plural = "Chats"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['chat_id']),
            models.Index(fields=['account', '-updated_at']),
        ]

    def __str__(self):
        if self.title and self.chat_id:
            return f"{self.title} ({self.chat_id})"
        elif self.chat_id:
            return f"Chat {self.chat_id}"
        elif self.title:
            return self.title
        return f"Chat #{self.id}"


class MessageRequest(models.Model):
    class ResponseType(models.TextChoices):
        THINKING = 'thinking', 'Thinking'
        AUTO = 'auto', 'Auto'
        INSTANT = 'instant', 'Instant'
    
    class ThinkingTime(models.TextChoices):
        STANDARD = 'standard', 'Standard'
        EXTENDED = 'extended', 'Extended'
    
    class Status(models.TextChoices):
        IDLE = 'idle', 'Idle'
        EXECUTING = 'executing', 'Executing'
        DONE = 'done', 'Done'
        FAILED = 'failed', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(GPTAccount, on_delete=models.CASCADE, related_name='message_requests')
    chat = models.ForeignKey(Chat, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    
    # Message content
    message = models.TextField()
    
    # Request options
    response_type = models.CharField(
        max_length=20,
        choices=ResponseType.choices,
        default=ResponseType.AUTO
    )
    thinking_time = models.CharField(
        max_length=20,
        choices=ThinkingTime.choices,
        default=ThinkingTime.STANDARD,
        help_text="Only applicable when response_type is 'thinking'"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IDLE
    )
    
    # Response data
    response = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Metadata
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_retrieved_at = models.DateTimeField(null=True, blank=True, help_text="Last time this request was retrieved via API")
    webhook_sent = models.BooleanField(default=False)
    webhook_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Message Request"
        verbose_name_plural = "Message Requests"
        ordering = ['-queued_at']
        indexes = [
            models.Index(fields=['account', 'status']),
            models.Index(fields=['status', 'queued_at']),
            models.Index(fields=['chat']),
        ]
    
    def __str__(self):
        return f"{self.account.email} - {self.status} - {self.message[:50]}"
    
    def mark_retrieved(self):
        """Mark request as retrieved via API"""
        from django.utils import timezone
        self.last_retrieved_at = timezone.now()
        self.save(update_fields=['last_retrieved_at'])
    
    def mark_executing(self):
        """Mark request as executing"""
        from django.utils import timezone
        self.status = self.Status.EXECUTING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_done(self, response_text):
        """Mark request as done with response"""
        from django.utils import timezone
        self.status = self.Status.DONE
        self.response = response_text
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'response', 'completed_at'])
    
    def mark_failed(self, error_msg):
        """Mark request as failed with error message"""
        from django.utils import timezone
        self.status = self.Status.FAILED
        self.error_message = error_msg
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])
