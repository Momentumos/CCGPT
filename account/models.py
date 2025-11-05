from django.db import models


class GPTAccount(models.Model):
    email = models.EmailField(unique=True, max_length=255)
    api_key = models.CharField(max_length=500, unique=True)
    webhook_url = models.URLField(max_length=500, help_text="Endpoint to send response back to")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "GPT Account"
        verbose_name_plural = "GPT Accounts"
        ordering = ['-created_at']

    def __str__(self):
        return self.email
