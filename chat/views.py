from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.shortcuts import get_object_or_404
from account.models import GPTAccount
from .models import MessageRequest, Chat
from .serializers import MessageRequestSerializer, MessageSubmitSerializer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class APIKeyAuthentication(BaseAuthentication):
    """Custom authentication using API key from header"""
    
    def authenticate(self, request):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return None
        
        try:
            account = GPTAccount.objects.get(api_key=api_key, is_active=True)
            return (account, None)
        except GPTAccount.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')


@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
def submit_message(request):
    """
    Submit a message request to be processed by browser extension
    
    Headers:
        X-API-Key: Your API key
    
    Body:
        {
            "message": "Your message here",
            "response_type": "thinking|auto|instant",
            "thinking_time": "standard|extended",
            "chat_id": "optional-chat-id"
        }
    """
    serializer = MessageSubmitSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    account = request.user
    data = serializer.validated_data
    
    # Handle chat
    chat = None
    chat_id_provided = data.get('chat_id')
    
    if chat_id_provided:
        # Try to find existing chat with this chat_id
        try:
            chat = Chat.objects.get(chat_id=chat_id_provided, account=account)
        except Chat.DoesNotExist:
            # Chat doesn't exist, this shouldn't happen but handle gracefully
            return Response(
                {"error": f"Chat with id '{chat_id_provided}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        # Create new chat (chat_id and title will be filled by extension)
        chat = Chat.objects.create(account=account)
    
    # Create message request
    message_request = MessageRequest.objects.create(
        account=account,
        chat=chat,
        message=data['message'],
        response_type=data['response_type'],
        thinking_time=data['thinking_time']
    )
    
    # Notify browser extension via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"account_{account.id}",
        {
            "type": "new_message_request",
            "request_id": str(message_request.id),
            "message": message_request.message,
            "response_type": message_request.response_type,
            "thinking_time": message_request.thinking_time,
            "chat_id": chat.chat_id if chat else None,
            "chat_db_id": chat.id if chat else None,
        }
    )
    
    return Response(
        MessageRequestSerializer(message_request).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def get_request_status(request, request_id):
    """Get the status of a message request"""
    account = request.user
    message_request = get_object_or_404(
        MessageRequest,
        id=request_id,
        account=account
    )
    
    return Response(MessageRequestSerializer(message_request).data)


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def list_requests(request):
    """List all message requests for the authenticated account"""
    account = request.user
    requests = MessageRequest.objects.filter(account=account)
    
    # Filter by status if provided
    status_filter = request.query_params.get('status')
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    serializer = MessageRequestSerializer(requests, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def list_chats(request):
    """List all chats for the authenticated account"""
    from .serializers import ChatSerializer
    account = request.user
    chats = Chat.objects.filter(account=account)
    
    serializer = ChatSerializer(chats, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def get_chat(request, chat_id):
    """Get a specific chat by its ChatGPT chat_id"""
    from .serializers import ChatSerializer
    account = request.user
    chat = get_object_or_404(Chat, chat_id=chat_id, account=account)
    
    serializer = ChatSerializer(chat)
    return Response(serializer.data)
