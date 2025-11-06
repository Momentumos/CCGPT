from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from account.models import GPTAccount
from .models import MessageRequest, Chat
from .serializers import MessageRequestSerializer, MessageSubmitSerializer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes


def health_check(request):
    """Health check endpoint for monitoring services like Render.com"""
    return JsonResponse({
        "status": "healthy",
        "service": "CCGPT API"
    })


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


@extend_schema(
    tags=['Chat'],
    summary='Submit a new message request',
    description=(
        'Submit a message to be processed by the browser extension. '
        'If chat_id is not provided, a new chat will be created. '
        'If chat_id is provided, the message will be added to that existing chat. '
        'The request will be queued and sent to the connected browser extension via WebSocket.'
    ),
    request=MessageSubmitSerializer,
    responses={
        201: MessageRequestSerializer,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            'New Chat Request',
            value={
                "message": "Explain quantum computing in simple terms",
                "response_type": "thinking",
                "thinking_time": "extended"
            },
            request_only=True,
        ),
        OpenApiExample(
            'Continue Existing Chat',
            value={
                "message": "Can you give me more details?",
                "response_type": "auto",
                "thinking_time": "standard",
                "chat_id": "chatcmpl-abc123xyz"
            },
            request_only=True,
        ),
        OpenApiExample(
            'Success Response',
            value={
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Explain quantum computing in simple terms",
                "response_type": "thinking",
                "thinking_time": "extended",
                "status": "idle",
                "response": None,
                "error_message": None,
                "chat": 1,
                "queued_at": "2024-01-15T10:30:00Z",
                "started_at": None,
                "completed_at": None
            },
            response_only=True,
            status_codes=['201'],
        ),
    ],
)
@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
def submit_message(request):
    """
    Submit a message request to be processed by browser extension
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
    
    # Broadcast to ALL connected browser extensions for this account via WebSocket
    # All extensions connected with this account's API key will receive this request
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


@extend_schema(
    tags=['Chat'],
    summary='Get message request status',
    description='Retrieve the current status and details of a specific message request by its ID.',
    responses={
        200: MessageRequestSerializer,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            'Idle Request',
            value={
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Explain quantum computing",
                "response_type": "thinking",
                "thinking_time": "extended",
                "status": "idle",
                "response": None,
                "error_message": None,
                "chat": 1,
                "queued_at": "2024-01-15T10:30:00Z",
                "started_at": None,
                "completed_at": None
            },
            response_only=True,
        ),
        OpenApiExample(
            'Completed Request',
            value={
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Explain quantum computing",
                "response_type": "thinking",
                "thinking_time": "extended",
                "status": "done",
                "response": "Quantum computing is a type of computing that uses quantum-mechanical phenomena...",
                "error_message": None,
                "chat": 1,
                "queued_at": "2024-01-15T10:30:00Z",
                "started_at": "2024-01-15T10:30:05Z",
                "completed_at": "2024-01-15T10:30:45Z"
            },
            response_only=True,
        ),
        OpenApiExample(
            'Failed Request',
            value={
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Explain quantum computing",
                "response_type": "thinking",
                "thinking_time": "extended",
                "status": "failed",
                "response": None,
                "error_message": "ChatGPT session expired. Please reconnect the extension.",
                "chat": 1,
                "queued_at": "2024-01-15T10:30:00Z",
                "started_at": "2024-01-15T10:30:05Z",
                "completed_at": "2024-01-15T10:30:10Z"
            },
            response_only=True,
        ),
    ],
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


@extend_schema(
    tags=['Chat'],
    summary='List all message requests',
    description='Retrieve a list of all message requests for the authenticated account. Optionally filter by status.',
    parameters=[
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by request status',
            enum=['idle', 'executing', 'done', 'failed'],
            required=False,
        ),
    ],
    responses={
        200: MessageRequestSerializer(many=True),
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            'List of Requests',
            value=[
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "message": "Explain quantum computing",
                    "response_type": "thinking",
                    "thinking_time": "extended",
                    "status": "done",
                    "response": "Quantum computing is...",
                    "error_message": None,
                    "chat": 1,
                    "queued_at": "2024-01-15T10:30:00Z",
                    "started_at": "2024-01-15T10:30:05Z",
                    "completed_at": "2024-01-15T10:30:45Z"
                },
                {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "message": "What is machine learning?",
                    "response_type": "auto",
                    "thinking_time": "standard",
                    "status": "idle",
                    "response": None,
                    "error_message": None,
                    "chat": 2,
                    "queued_at": "2024-01-15T11:00:00Z",
                    "started_at": None,
                    "completed_at": None
                }
            ],
            response_only=True,
        ),
    ],
)
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


@extend_schema(
    tags=['Chat'],
    summary='List all chats',
    description='Retrieve a list of all chats for the authenticated account.',
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            'List of Chats',
            value=[
                {
                    "id": 1,
                    "chat_id": "chatcmpl-abc123xyz",
                    "title": "Quantum Computing Discussion",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:35:00Z"
                },
                {
                    "id": 2,
                    "chat_id": "chatcmpl-def456uvw",
                    "title": "Machine Learning Basics",
                    "created_at": "2024-01-15T11:00:00Z",
                    "updated_at": "2024-01-15T11:05:00Z"
                }
            ],
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def list_chats(request):
    """List all chats for the authenticated account"""
    from .serializers import ChatSerializer
    account = request.user
    chats = Chat.objects.filter(account=account)
    
    serializer = ChatSerializer(chats, many=True)
    return Response(serializer.data)


@extend_schema(
    tags=['Chat'],
    summary='Get chat details',
    description='Retrieve details of a specific chat by its ChatGPT chat_id.',
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            'Chat Details',
            value={
                "id": 1,
                "chat_id": "chatcmpl-abc123xyz",
                "title": "Quantum Computing Discussion",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:35:00Z"
            },
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def get_chat(request, chat_id):
    """Get a specific chat by its ChatGPT chat_id"""
    from .serializers import ChatSerializer
    account = request.user
    chat = get_object_or_404(Chat, chat_id=chat_id, account=account)
    
    serializer = ChatSerializer(chat)
    return Response(serializer.data)


@extend_schema(
    tags=['Chat'],
    summary='Get next available idle request',
    description=(
        'Retrieve the next available idle message request that needs processing. '
        'Returns the oldest idle request that has either never been retrieved or was retrieved longest ago. '
        'Updates the last_retrieved_at timestamp when fetched.'
    ),
    responses={
        200: MessageRequestSerializer,
        204: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            'Available Request',
            value={
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Explain quantum computing",
                "response_type": "thinking",
                "thinking_time": "extended",
                "status": "idle",
                "response": None,
                "error_message": None,
                "chat": {
                    "id": 1,
                    "chat_id": None,
                    "title": None,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                },
                "queued_at": "2024-01-15T10:30:00Z",
                "started_at": None,
                "completed_at": None,
                "last_retrieved_at": "2024-01-15T10:30:05Z"
            },
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
def get_next_idle_request(request):
    """Get the next available idle request for processing"""
    account = request.user
    
    # Get the oldest idle request (prioritize never-retrieved, then oldest retrieved)
    idle_request = MessageRequest.objects.filter(
        account=account,
        status=MessageRequest.Status.IDLE
    ).order_by('last_retrieved_at', 'queued_at').first()
    
    if not idle_request:
        return Response(
            {"message": "No idle requests available"},
            status=status.HTTP_204_NO_CONTENT
        )
    
    # Mark as retrieved
    idle_request.mark_retrieved()
    
    serializer = MessageRequestSerializer(idle_request)
    return Response(serializer.data)
