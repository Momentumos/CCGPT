# Browser Extension Integration Guide

This guide explains how to integrate your browser extension with the ChatGPT Bridge API using WebSockets.

---

## Table of Contents

- [Overview](#overview)
- [WebSocket Connection](#websocket-connection)
- [Authentication](#authentication)
- [Message Flow](#message-flow)
- [Receiving Requests](#receiving-requests)
- [Submitting Responses](#submitting-responses)
- [Error Handling](#error-handling)
- [Complete Example](#complete-example)
- [Testing](#testing)

---

## Overview

The browser extension communicates with the API **exclusively via WebSocket**. The extension:

1. **Connects** to the WebSocket server with an API key
2. **Receives** message requests from the server
3. **Processes** them on ChatGPT website
4. **Sends back** responses or errors

**No REST API calls are needed** - everything happens through the WebSocket connection.

---

## WebSocket Connection

### Connection URL

```
ws://localhost:8000/ws/extension/?api_key=YOUR_API_KEY
```

**Production:**
```
wss://your-app.onrender.com/ws/extension/?api_key=YOUR_API_KEY
```

### Connection Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `api_key` | Yes | Your account's API key for authentication |

### JavaScript Example

```javascript
const API_KEY = 'your-api-key-here';
const WS_URL = `ws://localhost:8000/ws/extension/?api_key=${API_KEY}`;

const socket = new WebSocket(WS_URL);

socket.onopen = () => {
    console.log('✅ Connected to ChatGPT Bridge API');
};

socket.onclose = (event) => {
    console.log('❌ Disconnected:', event.code, event.reason);
};

socket.onerror = (error) => {
    console.error('⚠️ WebSocket error:', error);
};

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
};
```

---

## Authentication

Authentication happens automatically during the WebSocket handshake using the `api_key` query parameter.

### Success
- Connection is accepted
- You receive any pending idle requests immediately

### Failure
- Connection is closed immediately
- Check that your API key is valid and active

---

## Message Flow

```
┌─────────────┐                    ┌─────────────┐
│  Extension  │                    │   Server    │
└──────┬──────┘                    └──────┬──────┘
       │                                  │
       │  1. Connect with API key         │
       ├─────────────────────────────────>│
       │                                  │
       │  2. Connection accepted          │
       │<─────────────────────────────────┤
       │                                  │
       │  3. Pending requests (if any)    │
       │<─────────────────────────────────┤
       │                                  │
       │  4. New request arrives          │
       │<─────────────────────────────────┤
       │                                  │
       │  5. Status update (executing)    │
       ├─────────────────────────────────>│
       │                                  │
       │  6. Process on ChatGPT...        │
       │                                  │
       │  7. Send response                │
       ├─────────────────────────────────>│
       │                                  │
       │  8. Webhook notification sent    │
       │                                  │
```

---

## Receiving Requests

### Message Type: `new_request`

When a new message request is created (or when you first connect), you'll receive:

```json
{
  "type": "new_request",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Explain quantum computing in simple terms",
  "response_type": "thinking",
  "thinking_time": "extended",
  "chat_id": "chatcmpl-abc123xyz",
  "chat_db_id": 1
}
```

### Fields Explanation

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"new_request"` |
| `request_id` | UUID | Unique identifier for this request |
| `message` | string | The message to send to ChatGPT |
| `response_type` | string | `"thinking"`, `"auto"`, or `"instant"` |
| `thinking_time` | string | `"standard"` or `"extended"` (only for thinking mode) |
| `chat_id` | string/null | ChatGPT chat ID to continue existing conversation, or `null` for new chat |
| `chat_db_id` | integer | Internal database ID for the chat |

### Response Types

- **`thinking`**: Use ChatGPT's "Think" mode
- **`auto`**: Let ChatGPT decide automatically
- **`instant`**: Use instant response mode

### Thinking Time

- **`standard`**: Standard thinking time
- **`extended`**: Extended thinking time

### Chat Handling

- **`chat_id` is `null`**: Create a new chat on ChatGPT
- **`chat_id` has value**: Continue the existing chat with that ID

### JavaScript Handler Example

```javascript
function handleMessage(data) {
    if (data.type === 'new_request') {
        console.log('📨 New request received:', data.request_id);
        processRequest(data);
    }
}

async function processRequest(request) {
    const {
        request_id,
        message,
        response_type,
        thinking_time,
        chat_id
    } = request;
    
    // Send status update
    sendStatusUpdate(request_id, 'executing');
    
    try {
        // Process on ChatGPT
        const result = await sendToChat(message, response_type, thinking_time, chat_id);
        
        // Send response back
        sendResponse(request_id, result);
    } catch (error) {
        // Send error back
        sendError(request_id, error.message);
    }
}
```

---

## Submitting Responses

### 1. Status Update (Optional)

Send this when you start processing a request:

```json
{
  "type": "status_update",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "executing"
}
```

**JavaScript:**
```javascript
function sendStatusUpdate(requestId, status) {
    socket.send(JSON.stringify({
        type: 'status_update',
        request_id: requestId,
        status: status
    }));
}
```

**Effect:**
- Updates request status to `"executing"`
- Sets `started_at` timestamp
- Lets the system know you're working on it

---

### 2. Successful Response

Send this when you get a response from ChatGPT:

```json
{
  "type": "response",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Quantum computing is a revolutionary computing paradigm that leverages quantum mechanics...",
  "chat_id": "chatcmpl-abc123xyz",
  "chat_title": "Quantum Computing Discussion"
}
```

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Must be `"response"` |
| `request_id` | Yes | The request ID you received |
| `response` | Yes | The response text from ChatGPT |
| `chat_id` | Yes | The ChatGPT chat ID (from URL or API) |
| `chat_title` | Optional | The chat title (if available) |

**JavaScript:**
```javascript
function sendResponse(requestId, result) {
    socket.send(JSON.stringify({
        type: 'response',
        request_id: requestId,
        response: result.responseText,
        chat_id: result.chatId,
        chat_title: result.chatTitle || null
    }));
}
```

**Effect:**
- Updates request status to `"done"`
- Saves the response text
- Updates chat with `chat_id` and `chat_title`
- Sets `completed_at` timestamp
- Triggers webhook notification (if configured)

---

### 3. Error Response

Send this if something goes wrong:

```json
{
  "type": "error",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": "ChatGPT session expired. Please log in again."
}
```

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | Must be `"error"` |
| `request_id` | Yes | The request ID you received |
| `error` | Yes | Error message describing what went wrong |

**JavaScript:**
```javascript
function sendError(requestId, errorMessage) {
    socket.send(JSON.stringify({
        type: 'error',
        request_id: requestId,
        error: errorMessage
    }));
}
```

**Effect:**
- Updates request status to `"failed"`
- Saves the error message
- Sets `completed_at` timestamp
- Triggers webhook notification (if configured)

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Connection closed immediately | Invalid API key | Check your API key is correct and active |
| No messages received | No pending requests | Wait for new requests to arrive |
| ChatGPT not logged in | User not authenticated | Prompt user to log in to ChatGPT |
| Rate limit exceeded | Too many requests | Implement backoff strategy |
| Chat not found | Invalid chat_id | Start a new chat instead |

### Reconnection Strategy

```javascript
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000; // 3 seconds

function connect() {
    const socket = new WebSocket(WS_URL);
    
    socket.onopen = () => {
        console.log('✅ Connected');
        reconnectAttempts = 0;
    };
    
    socket.onclose = (event) => {
        console.log('❌ Disconnected');
        
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            console.log(`🔄 Reconnecting... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
            setTimeout(connect, RECONNECT_DELAY);
        } else {
            console.error('❌ Max reconnection attempts reached');
        }
    };
    
    socket.onerror = (error) => {
        console.error('⚠️ WebSocket error:', error);
    };
    
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };
    
    return socket;
}

let socket = connect();
```

---

## Complete Example

Here's a complete browser extension implementation:

```javascript
class ChatGPTBridgeExtension {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
    }
    
    connect() {
        const wsUrl = `ws://localhost:8000/ws/extension/?api_key=${this.apiKey}`;
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('✅ Connected to ChatGPT Bridge API');
            this.reconnectAttempts = 0;
        };
        
        this.socket.onclose = (event) => {
            console.log('❌ Disconnected:', event.code, event.reason);
            this.handleReconnect();
        };
        
        this.socket.onerror = (error) => {
            console.error('⚠️ WebSocket error:', error);
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
    }
    
    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`🔄 Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => this.connect(), this.reconnectDelay);
        } else {
            console.error('❌ Max reconnection attempts reached');
        }
    }
    
    handleMessage(data) {
        if (data.type === 'new_request') {
            console.log('📨 New request received:', data.request_id);
            this.processRequest(data);
        }
    }
    
    async processRequest(request) {
        const { request_id, message, response_type, thinking_time, chat_id } = request;
        
        // Send status update
        this.sendStatusUpdate(request_id, 'executing');
        
        try {
            // Check if user is logged in to ChatGPT
            if (!this.isLoggedInToChatGPT()) {
                throw new Error('Not logged in to ChatGPT. Please log in first.');
            }
            
            // Send message to ChatGPT
            const result = await this.sendToChatGPT(
                message,
                response_type,
                thinking_time,
                chat_id
            );
            
            // Send response back
            this.sendResponse(request_id, result);
            
        } catch (error) {
            console.error('❌ Error processing request:', error);
            this.sendError(request_id, error.message);
        }
    }
    
    async sendToChatGPT(message, responseType, thinkingTime, chatId) {
        // TODO: Implement your ChatGPT interaction logic here
        // This will depend on how you interact with the ChatGPT website
        
        // Example structure:
        // 1. Navigate to chat (or create new one)
        // 2. Set response mode (thinking/auto/instant)
        // 3. Send message
        // 4. Wait for response
        // 5. Extract response text and chat info
        
        return {
            responseText: 'Response from ChatGPT...',
            chatId: 'chatcmpl-abc123xyz',
            chatTitle: 'Chat Title'
        };
    }
    
    isLoggedInToChatGPT() {
        // TODO: Check if user is logged in to ChatGPT
        // Check for auth cookies, session tokens, etc.
        return true;
    }
    
    sendStatusUpdate(requestId, status) {
        this.socket.send(JSON.stringify({
            type: 'status_update',
            request_id: requestId,
            status: status
        }));
    }
    
    sendResponse(requestId, result) {
        this.socket.send(JSON.stringify({
            type: 'response',
            request_id: requestId,
            response: result.responseText,
            chat_id: result.chatId,
            chat_title: result.chatTitle || null
        }));
        console.log('✅ Response sent for request:', requestId);
    }
    
    sendError(requestId, errorMessage) {
        this.socket.send(JSON.stringify({
            type: 'error',
            request_id: requestId,
            error: errorMessage
        }));
        console.log('❌ Error sent for request:', requestId);
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Usage
const extension = new ChatGPTBridgeExtension('your-api-key-here');
extension.connect();
```

---

## Testing

### 1. Test Connection

```javascript
const socket = new WebSocket('ws://localhost:8000/ws/extension/?api_key=YOUR_API_KEY');

socket.onopen = () => {
    console.log('✅ Connection successful!');
};

socket.onclose = (event) => {
    console.log('Connection closed:', event.code, event.reason);
};
```

### 2. Test Receiving Requests

Use the REST API to create a test request:

```bash
curl -X POST http://localhost:8000/api/chat/submit/ \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test message",
    "response_type": "auto",
    "thinking_time": "standard"
  }'
```

Your extension should receive the request via WebSocket.

### 3. Test Sending Response

```javascript
socket.send(JSON.stringify({
    type: 'response',
    request_id: 'REQUEST_ID_FROM_SERVER',
    response: 'Test response',
    chat_id: 'chatcmpl-test123',
    chat_title: 'Test Chat'
}));
```

### 4. Test Error Handling

```javascript
socket.send(JSON.stringify({
    type: 'error',
    request_id: 'REQUEST_ID_FROM_SERVER',
    error: 'Test error message'
}));
```

---

## Best Practices

### 1. **Always Send Status Updates**
Let the server know you're processing a request:
```javascript
sendStatusUpdate(request_id, 'executing');
```

### 2. **Handle Reconnections**
Implement automatic reconnection with exponential backoff.

### 3. **Validate Messages**
Always validate incoming messages before processing:
```javascript
if (!data.request_id || !data.message) {
    console.error('Invalid message received');
    return;
}
```

### 4. **Error Reporting**
Always send detailed error messages:
```javascript
sendError(request_id, 'ChatGPT rate limit exceeded. Try again in 1 minute.');
```

### 5. **Chat ID Extraction**
Make sure to extract the correct chat ID from ChatGPT's URL or API response.

### 6. **Keep Connection Alive**
Send periodic ping messages if needed to keep the connection alive.

### 7. **Handle Multiple Requests**
Process requests one at a time or implement a queue system.

---

## Troubleshooting

### Connection Issues

**Problem:** WebSocket connection closes immediately  
**Solution:** Check API key is valid and active in admin panel

**Problem:** No messages received  
**Solution:** Create a test request via REST API to trigger a message

### Processing Issues

**Problem:** Can't extract chat ID  
**Solution:** Check ChatGPT's URL structure or API response format

**Problem:** Response not updating in database  
**Solution:** Ensure you're sending the correct `request_id`

### Performance Issues

**Problem:** Slow response times  
**Solution:** Optimize ChatGPT interaction, use appropriate response types

**Problem:** Multiple extensions processing same request  
**Solution:** Implement locking mechanism or use `last_retrieved_at` field

---

## API Endpoints Reference

While the extension primarily uses WebSocket, these REST endpoints are available for testing:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/submit/` | POST | Create new message request |
| `/api/chat/requests/` | GET | List all requests |
| `/api/chat/requests/next-idle/` | GET | Get next idle request |
| `/api/chat/requests/{id}/` | GET | Get specific request status |
| `/api/chat/chats/` | GET | List all chats |
| `/api/chat/chats/{chat_id}/` | GET | Get specific chat |

**Note:** These are for testing and monitoring only. The extension should use WebSocket exclusively.

---

## Support

For issues or questions:
- Check server logs for error messages
- Verify API key is active in admin panel
- Test connection with simple WebSocket client first
- Review Swagger documentation at `/api/docs/`

---

**Happy coding! 🚀**
