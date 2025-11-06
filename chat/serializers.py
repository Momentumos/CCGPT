from rest_framework import serializers
from .models import MessageRequest, Chat


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = ['id', 'chat_id', 'title', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class MessageRequestSerializer(serializers.ModelSerializer):
    chat = ChatSerializer(read_only=True)
    
    class Meta:
        model = MessageRequest
        fields = [
            'id', 'message', 'response_type', 'thinking_time',
            'status', 'response', 'error_message', 'chat',
            'queued_at', 'started_at', 'completed_at', 'last_retrieved_at'
        ]
        read_only_fields = [
            'id', 'status', 'response', 'error_message',
            'queued_at', 'started_at', 'completed_at', 'last_retrieved_at'
        ]


class MessageSubmitSerializer(serializers.Serializer):
    message = serializers.CharField()
    response_type = serializers.ChoiceField(
        choices=MessageRequest.ResponseType.choices,
        default=MessageRequest.ResponseType.AUTO
    )
    thinking_time = serializers.ChoiceField(
        choices=MessageRequest.ThinkingTime.choices,
        default=MessageRequest.ThinkingTime.STANDARD
    )
    chat_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
