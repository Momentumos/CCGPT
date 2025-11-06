# Browser Extension Quick Reference

## WebSocket Connection

```javascript
const socket = new WebSocket('ws://localhost:8000/ws/extension/?api_key=YOUR_API_KEY');
```

**Production:**
```javascript
const socket = new WebSocket('wss://your-app.onrender.com/ws/extension/?api_key=YOUR_API_KEY');
```

---

## Incoming Messages

### New Request
```json
{
  "type": "new_request",
  "request_id": "uuid",
  "message": "text",
  "response_type": "thinking|auto|instant",
  "thinking_time": "standard|extended",
  "chat_id": "chatcmpl-xxx or null",
  "chat_db_id": 1
}
```

---

## Outgoing Messages

### 1. Status Update (Optional)
```json
{
  "type": "status_update",
  "request_id": "uuid",
  "status": "executing"
}
```

### 2. Success Response
```json
{
  "type": "response",
  "request_id": "uuid",
  "response": "response text",
  "chat_id": "chatcmpl-xxx",
  "chat_title": "Chat Title"
}
```

### 3. Error Response
```json
{
  "type": "error",
  "request_id": "uuid",
  "error": "error message"
}
```

---

## Complete Flow

```javascript
// 1. Connect
const socket = new WebSocket(WS_URL);

// 2. Listen for requests
socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'new_request') {
        processRequest(data);
    }
};

// 3. Send status update
socket.send(JSON.stringify({
    type: 'status_update',
    request_id: data.request_id,
    status: 'executing'
}));

// 4. Process on ChatGPT
const result = await sendToChatGPT(data);

// 5. Send response
socket.send(JSON.stringify({
    type: 'response',
    request_id: data.request_id,
    response: result.text,
    chat_id: result.chatId,
    chat_title: result.title
}));
```

---

## Key Points

✅ **WebSocket Only** - No REST API calls needed  
✅ **Always authenticate** - Include `api_key` in URL  
✅ **Send status updates** - Let server know you're processing  
✅ **Include chat_id** - Required for tracking conversations  
✅ **Handle errors** - Always send error messages back  
✅ **Reconnect on disconnect** - Implement reconnection logic  

---

## Testing

```bash
# Create test request
curl -X POST http://localhost:8000/api/chat/submit/ \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Test", "response_type": "auto"}'
```

Your extension should receive it via WebSocket immediately.
