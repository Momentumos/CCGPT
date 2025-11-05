import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from account.models import GPTAccount
from .models import MessageRequest
from django.utils import timezone
import httpx


class BrowserExtensionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for browser extension to receive message requests
    and send back responses
    """
    
    async def connect(self):
        # Get API key from query parameters
        query_string = self.scope['query_string'].decode()
        params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
        api_key = params.get('api_key')
        
        if not api_key:
            await self.close()
            return
        
        # Authenticate
        self.account = await self.get_account_by_api_key(api_key)
        if not self.account:
            await self.close()
            return
        
        # Join account-specific group
        self.account_group_name = f"account_{self.account.id}"
        await self.channel_layer.group_add(
            self.account_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send pending requests
        await self.send_pending_requests()
    
    async def disconnect(self, close_code):
        # Leave account group
        if hasattr(self, 'account_group_name'):
            await self.channel_layer.group_discard(
                self.account_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Receive response from browser extension
        
        Expected format:
        {
            "type": "response|error|status_update",
            "request_id": "uuid",
            "response": "response text",
            "error": "error message",
            "chat_id": "chatgpt-chat-id"
        }
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            request_id = data.get('request_id')
            
            if not request_id:
                return
            
            if message_type == 'response':
                await self.handle_response(request_id, data)
            elif message_type == 'error':
                await self.handle_error(request_id, data)
            elif message_type == 'status_update':
                await self.handle_status_update(request_id, data)
                
        except json.JSONDecodeError:
            pass
    
    async def handle_response(self, request_id, data):
        """Handle successful response from browser extension"""
        response_text = data.get('response', '')
        chat_id = data.get('chat_id')  # ChatGPT chat ID from extension
        chat_title = data.get('chat_title')  # Chat title from extension
        
        # Update message request and chat info
        await self.update_request_done(request_id, response_text, chat_id, chat_title)
        
        # Send webhook notification
        await self.send_webhook_notification(request_id)
    
    async def handle_error(self, request_id, data):
        """Handle error from browser extension"""
        error_message = data.get('error', 'Unknown error')
        
        # Update message request
        await self.update_request_failed(request_id, error_message)
        
        # Send webhook notification
        await self.send_webhook_notification(request_id)
    
    async def handle_status_update(self, request_id, data):
        """Handle status update (e.g., started executing)"""
        if data.get('status') == 'executing':
            await self.update_request_executing(request_id)
    
    async def new_message_request(self, event):
        """
        Handler for new message requests from the group
        Send to browser extension
        """
        await self.send(text_data=json.dumps({
            'type': 'new_request',
            'request_id': event['request_id'],
            'message': event['message'],
            'response_type': event['response_type'],
            'thinking_time': event['thinking_time'],
            'chat_id': event.get('chat_id'),  # ChatGPT chat ID (if continuing existing chat)
            'chat_db_id': event.get('chat_db_id'),  # Our database chat ID
        }))
    
    # Database operations
    
    @database_sync_to_async
    def get_account_by_api_key(self, api_key):
        try:
            return GPTAccount.objects.get(api_key=api_key, is_active=True)
        except GPTAccount.DoesNotExist:
            return None
    
    @database_sync_to_async
    def send_pending_requests(self):
        """Send all pending (idle) requests to the browser extension"""
        pending_requests = MessageRequest.objects.filter(
            account=self.account,
            status=MessageRequest.Status.IDLE
        ).select_related('chat').order_by('queued_at')
        
        for req in pending_requests:
            self.channel_layer.group_send(
                self.account_group_name,
                {
                    "type": "new_message_request",
                    "request_id": str(req.id),
                    "message": req.message,
                    "response_type": req.response_type,
                    "thinking_time": req.thinking_time,
                    "chat_id": req.chat.chat_id if req.chat else None,
                    "chat_db_id": req.chat.id if req.chat else None,
                }
            )
    
    @database_sync_to_async
    def update_request_executing(self, request_id):
        try:
            req = MessageRequest.objects.get(id=request_id, account=self.account)
            req.mark_executing()
        except MessageRequest.DoesNotExist:
            pass
    
    @database_sync_to_async
    def update_request_done(self, request_id, response_text, chat_id, chat_title=None):
        try:
            req = MessageRequest.objects.get(id=request_id, account=self.account)
            req.mark_done(response_text)
            
            # Update chat with info from extension
            if req.chat:
                update_fields = []
                
                if chat_id:
                    req.chat.chat_id = chat_id
                    update_fields.append('chat_id')
                
                if chat_title:
                    req.chat.title = chat_title
                    update_fields.append('title')
                
                if update_fields:
                    update_fields.append('updated_at')
                    req.chat.save(update_fields=update_fields)
        except MessageRequest.DoesNotExist:
            pass
    
    @database_sync_to_async
    def update_request_failed(self, request_id, error_message):
        try:
            req = MessageRequest.objects.get(id=request_id, account=self.account)
            req.mark_failed(error_message)
        except MessageRequest.DoesNotExist:
            pass
    
    @database_sync_to_async
    def get_request_data(self, request_id):
        try:
            req = MessageRequest.objects.select_related('account').get(
                id=request_id,
                account=self.account
            )
            return {
                'id': str(req.id),
                'message': req.message,
                'response': req.response,
                'error_message': req.error_message,
                'status': req.status,
                'response_type': req.response_type,
                'thinking_time': req.thinking_time,
                'webhook_url': req.account.webhook_url,
            }
        except MessageRequest.DoesNotExist:
            return None
    
    async def send_webhook_notification(self, request_id):
        """Send webhook notification to the account's webhook URL"""
        request_data = await self.get_request_data(request_id)
        
        if not request_data or not request_data['webhook_url']:
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    request_data['webhook_url'],
                    json={
                        'request_id': request_data['id'],
                        'status': request_data['status'],
                        'message': request_data['message'],
                        'response': request_data['response'],
                        'error': request_data['error_message'],
                        'response_type': request_data['response_type'],
                        'thinking_time': request_data['thinking_time'],
                    },
                    timeout=30.0
                )
                
                # Mark webhook as sent
                await self.mark_webhook_sent(request_id)
                
        except Exception as e:
            # Log error but don't fail
            print(f"Webhook notification failed: {e}")
    
    @database_sync_to_async
    def mark_webhook_sent(self, request_id):
        try:
            req = MessageRequest.objects.get(id=request_id, account=self.account)
            req.webhook_sent = True
            req.webhook_sent_at = timezone.now()
            req.save(update_fields=['webhook_sent', 'webhook_sent_at'])
        except MessageRequest.DoesNotExist:
            pass
