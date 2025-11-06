# Webhook Setup Guide

Complete guide for setting up webhooks with the ChatGPT Bridge API.

---

## Overview

The client now uses **Webhooks + Server-Sent Events (SSE)** for real-time updates instead of polling.

### Flow

```
1. Client sends message → API
2. API notifies Extension via WebSocket
3. Extension processes on ChatGPT
4. Extension sends response back via WebSocket
5. API sends webhook POST to configured URL
6. Webhook endpoint broadcasts to SSE clients
7. Client receives instant update via SSE
```

---

## Webhook URL Configuration

### For the HTML/JS Client

Set the webhook URL in the admin panel to:

```
http://localhost:8000/api/webhooks/chatgpt/
```

**For production (Render.com):**
```
https://your-app.onrender.com/api/webhooks/chatgpt/
```

### Steps

1. Go to `/admin/`
2. Navigate to **GPT Accounts**
3. Create or edit your account
4. Set **Webhook URL**: `http://localhost:8000/api/webhooks/chatgpt/`
5. Copy the **API Key**
6. Click **Save**

---

## How It Works

### 1. Client Sends Message

```javascript
// POST to create request
fetch('/api/chat/submit/', {
    method: 'POST',
    headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        message: "Hello",
        response_type: "auto",
    }),
});
```

### 2. Client Connects to SSE

```javascript
// Open SSE connection
const eventSource = new EventSource(`/api/sse/${requestId}/`);

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.status === 'done') {
        // Update UI with response
        displayResponse(data.response);
        eventSource.close();
    }
};
```

### 3. Server Receives Webhook

When the extension completes processing, the API sends:

```http
POST /api/webhooks/chatgpt/
Content-Type: application/json

{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "done",
  "message": "Hello",
  "response": "Hi! How can I help you?",
  "error": null,
  "response_type": "auto",
  "thinking_time": "standard"
}
```

### 4. Webhook Broadcasts to SSE

The webhook endpoint finds all SSE connections waiting for this `request_id` and sends the data:

```python
# Broadcast to SSE clients
for response in sse_connections[request_id]:
    message = f"data: {json.dumps(data)}\n\n"
    response.write(message.encode('utf-8'))
    response.flush()
```

### 5. Client Receives Update

The SSE connection receives the data and updates the UI instantly.

---

## Endpoints

### Webhook Receiver

**URL**: `/api/webhooks/chatgpt/`  
**Method**: POST  
**Purpose**: Receive webhook notifications from the API  
**Authentication**: None (internal endpoint)

**Request Body**:
```json
{
  "request_id": "uuid",
  "status": "done|failed",
  "message": "original message",
  "response": "response text",
  "error": "error message or null",
  "response_type": "auto|thinking|instant",
  "thinking_time": "standard|extended"
}
```

**Response**:
```json
{
  "received": true,
  "request_id": "uuid"
}
```

### SSE Stream

**URL**: `/api/sse/{request_id}/`  
**Method**: GET  
**Purpose**: Server-Sent Events stream for real-time updates  
**Authentication**: None (public endpoint)

**Response**: Text/event-stream

```
data: {"type": "connected", "request_id": "uuid"}

data: {"status": "done", "response": "text", ...}
```

---

## Advantages Over Polling

### Polling (Old Method)
❌ Constant HTTP requests every 2 seconds  
❌ Delayed updates (up to 2 seconds)  
❌ Higher server load  
❌ Wasted bandwidth  

### Webhooks + SSE (New Method)
✅ Single persistent connection  
✅ Instant updates (< 100ms)  
✅ Lower server load  
✅ Efficient bandwidth usage  
✅ Real-time experience  

---

## Testing

### 1. Test Webhook Endpoint

```bash
curl -X POST http://localhost:8000/api/webhooks/chatgpt/ \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-123",
    "status": "done",
    "message": "Test",
    "response": "Test response",
    "error": null
  }'
```

### 2. Test SSE Connection

Open in browser or use curl:

```bash
curl -N http://localhost:8000/api/sse/test-123/
```

You should see:
```
data: {"type": "connected", "request_id": "test-123"}
```

### 3. Test Complete Flow

1. Open the client: `http://localhost:8000/`
2. Login with your API key
3. Send a message
4. Watch browser console for SSE logs
5. Response should appear instantly when ready

---

## Browser Console Logs

When working correctly, you'll see:

```
📡 Connecting to SSE for request: 550e8400-...
✅ SSE connection established
📨 SSE message received: {type: "connected", ...}
📨 SSE message received: {status: "done", response: "...", ...}
✅ Response received successfully
```

---

## Troubleshooting

### Webhook Not Received

**Problem**: Client waits forever, no response  
**Solution**:
- Check webhook URL is set correctly in admin
- Verify webhook URL is accessible
- Check server logs for webhook POST

### SSE Connection Fails

**Problem**: "SSE error" in console  
**Solution**:
- Check `/api/sse/{id}/` endpoint is accessible
- Verify no CORS issues
- Check browser supports EventSource

### Fallback to Polling

If SSE fails, the client automatically falls back to a single API check:

```javascript
// Fallback: get status via API
const response = await fetch(`/api/chat/requests/${requestId}/`);
```

---

## Production Deployment

### Render.com

1. Set webhook URL in admin:
   ```
   https://your-app.onrender.com/api/webhooks/chatgpt/
   ```

2. Ensure CORS is configured if needed

3. Test webhook endpoint is accessible:
   ```bash
   curl https://your-app.onrender.com/api/webhooks/chatgpt/
   ```

### HTTPS Required

For production, always use HTTPS:
- Webhook URL: `https://...`
- SSE endpoint: `https://...`

---

## Code Reference

### Webhook Handler

`chat/webhook_views.py`:
- `webhook_receiver()` - Receives POST webhooks
- `sse_stream()` - Serves SSE connections

### Client Code

`static/client/js/app.js`:
- `pollForResponse()` - Opens SSE connection
- `fallbackToPolling()` - Fallback if SSE fails

---

## Security Notes

⚠️ **Webhook Endpoint**: Currently public, consider adding authentication  
⚠️ **SSE Endpoint**: Public, no sensitive data exposed  
⚠️ **HTTPS**: Required for production  

---

## Future Enhancements

Potential improvements:
- [ ] Webhook signature verification
- [ ] SSE authentication
- [ ] Reconnection with exponential backoff
- [ ] Multiple SSE connections per user
- [ ] WebSocket as alternative to SSE

---

**Enjoy real-time updates! ⚡**
