from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import time
import threading

# Store SSE connections for each request
sse_connections = {}
sse_lock = threading.Lock()


@csrf_exempt
@require_http_methods(["POST"])
def webhook_receiver(request):
    """
    Receive webhook notifications from the ChatGPT Bridge API
    and broadcast to connected SSE clients
    """
    try:
        data = json.loads(request.body)
        request_id = data.get('request_id')
        
        if not request_id:
            return JsonResponse({'error': 'Missing request_id'}, status=400)
        
        print(f"📨 Webhook received for request: {request_id}")
        print(f"   Status: {data.get('status')}")
        
        # Broadcast to all SSE connections waiting for this request
        with sse_lock:
            if request_id in sse_connections:
                connections = sse_connections[request_id]
                for response in connections:
                    try:
                        # Send data to SSE client
                        message = f"data: {json.dumps(data)}\n\n"
                        response.write(message.encode('utf-8'))
                        response.flush()
                    except Exception as e:
                        print(f"Error sending to SSE client: {e}")
                
                # Clean up connections for this request
                del sse_connections[request_id]
        
        return JsonResponse({'received': True, 'request_id': request_id})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Webhook error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def sse_stream(request, request_id):
    """
    Server-Sent Events endpoint for real-time updates
    Clients connect here to receive webhook notifications
    """
    def event_stream():
        # Create a response object that we can write to
        class ResponseWriter:
            def __init__(self):
                self.data = []
                self.closed = False
            
            def write(self, data):
                if not self.closed:
                    self.data.append(data)
            
            def flush(self):
                pass
        
        writer = ResponseWriter()
        
        # Register this connection
        with sse_lock:
            if request_id not in sse_connections:
                sse_connections[request_id] = []
            sse_connections[request_id].append(writer)
        
        print(f"🔌 SSE client connected for request: {request_id}")
        
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'request_id': request_id})}\n\n".encode('utf-8')
        
        # Keep connection alive and yield data when available
        timeout = 120  # 2 minutes timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if writer.data:
                # Send accumulated data
                for data in writer.data:
                    yield data
                writer.closed = True
                break
            
            # Send keepalive comment every 15 seconds
            if int(time.time() - start_time) % 15 == 0:
                yield ": keepalive\n\n".encode('utf-8')
            
            time.sleep(0.5)
        
        # Cleanup on disconnect
        with sse_lock:
            if request_id in sse_connections:
                if writer in sse_connections[request_id]:
                    sse_connections[request_id].remove(writer)
                if not sse_connections[request_id]:
                    del sse_connections[request_id]
        
        print(f"🔌 SSE client disconnected for request: {request_id}")
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
