# API Documentation

## Overview

This system provides a robust message queuing and processing system for ChatGPT interactions via a browser extension. Clients submit messages via API, which are queued and sent to a browser extension via WebSocket. The extension processes them in ChatGPT and returns responses.

## Architecture Flow

```
Client → API (with API Key) → Queue → WebSocket → Browser Extension → ChatGPT → Response → Webhook
```

## Authentication

All API endpoints require authentication using an API key in the request header:

```
X-API-Key: your-api-key-here
```

## REST API Endpoints

### 1. Submit Message

**Endpoint:** `POST /api/chat/submit/`

**Description:** Submit a new message request to be processed by the browser extension.

**Headers:**
```
X-API-Key: your-api-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "Your message to ChatGPT",
  "response_type": "thinking|auto|instant",
  "thinking_time": "standard|extended",
  "chat_id": "optional-chatgpt-chat-id"
}
```

**Parameters:**
- `message` (required): The message to send to ChatGPT
- `response_type` (optional): Type of response
  - `thinking`: Use thinking mode
  - `auto`: Auto-select mode (default)
  - `instant`: Instant response
- `thinking_time` (optional): Thinking duration (only for thinking mode)
  - `standard`: Standard thinking time (default)
  - `extended`: Extended thinking time
- `chat_id` (optional): ChatGPT chat ID to continue existing conversation
  - If provided: Message will be sent to that specific chat
  - If omitted: New chat will be created (chat_id and title filled by extension later)

**Response:**
```json
{
  "id": "uuid-of-request",
  "message": "Your message",
  "response_type": "auto",
  "thinking_time": "standard",
  "status": "idle",
  "response": null,
  "error_message": null,
  "chat": null,
  "queued_at": "2024-01-01T12:00:00Z",
  "started_at": null,
  "completed_at": null
}
```

**Status Codes:**
- `201`: Request created successfully
- `400`: Invalid request data
- `401`: Invalid or missing API key

---

### 2. Get Request Status

**Endpoint:** `GET /api/chat/requests/{request_id}/`

**Description:** Get the current status and response of a message request.

**Headers:**
```
X-API-Key: your-api-key
```

**Response:**
```json
{
  "id": "uuid-of-request",
  "message": "Your message",
  "response_type": "auto",
  "thinking_time": "standard",
  "status": "done",
  "response": "ChatGPT's response here",
  "error_message": null,
  "chat": "chatgpt-chat-id",
  "queued_at": "2024-01-01T12:00:00Z",
  "started_at": "2024-01-01T12:00:05Z",
  "completed_at": "2024-01-01T12:00:15Z"
}
```

**Status Values:**
- `idle`: Request is queued, waiting to be processed
- `executing`: Request is currently being processed
- `done`: Request completed successfully
- `failed`: Request failed with error

**Status Codes:**
- `200`: Success
- `401`: Invalid or missing API key
- `404`: Request not found

---

### 3. List Requests

**Endpoint:** `GET /api/chat/requests/`

**Description:** List all message requests for your account.

**Headers:**
```
X-API-Key: your-api-key
```

**Query Parameters:**
- `status` (optional): Filter by status (`idle`, `executing`, `done`, `failed`)

**Example:**
```
GET /api/chat/requests/?status=done
```

**Response:**
```json
[
  {
    "id": "uuid-1",
    "message": "Message 1",
    "status": "done",
    "response": "Response 1",
    ...
  },
  {
    "id": "uuid-2",
    "message": "Message 2",
    "status": "executing",
    "response": null,
    ...
  }
]
```

**Status Codes:**
- `200`: Success
- `401`: Invalid or missing API key

---

### 4. List Chats

**Endpoint:** `GET /api/chat/chats/`

**Description:** List all chats for your account.

**Headers:**
```
X-API-Key: your-api-key
```

**Response:**
```json
[
  {
    "id": 123,
    "chat_id": "chatgpt-abc123",
    "title": "Quantum Computing Basics",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:05:00Z"
  },
  {
    "id": 124,
    "chat_id": null,
    "title": null,
    "created_at": "2024-01-01T13:00:00Z",
    "updated_at": "2024-01-01T13:00:00Z"
  }
]
```

**Note:** Chats with `null` chat_id and title are newly created and waiting for the extension to fill in the details.

**Status Codes:**
- `200`: Success
- `401`: Invalid or missing API key

---

## WebSocket API (Browser Extension)

### Connection

**Endpoint:** `ws://your-domain/ws/extension/?api_key=your-api-key`

**Description:** WebSocket connection for browser extension to receive message requests and send responses.

### Messages from Server to Extension

#### New Request
```json
{
  "type": "new_request",
  "request_id": "uuid",
  "message": "Message to send",
  "response_type": "thinking|auto|instant",
  "thinking_time": "standard|extended",
  "chat_id": "chatgpt-chat-id or null",
  "chat_db_id": "database-chat-id (integer)"
}
```

**Fields:**
- `chat_id`: ChatGPT website chat ID (null for new chats)
- `chat_db_id`: Our database chat ID (always present, use to update chat info)

### Messages from Extension to Server

#### Status Update
```json
{
  "type": "status_update",
  "request_id": "uuid",
  "status": "executing"
}
```

#### Success Response
```json
{
  "type": "response",
  "request_id": "uuid",
  "response": "ChatGPT's response text",
  "chat_id": "chatgpt-chat-id",
  "chat_title": "Chat title from ChatGPT (optional)"
}
```

**Important:** When responding, the extension should:
- Always include `chat_id` (the ChatGPT website chat ID)
- Include `chat_title` if available (especially for new chats)
- These will update the Chat record in the database

#### Error Response
```json
{
  "type": "error",
  "request_id": "uuid",
  "error": "Error message"
}
```

---

## Webhook Notifications

When a request is completed (success or failure), the system sends a POST request to the `webhook_url` configured in your account.

**Webhook Payload:**
```json
{
  "request_id": "uuid",
  "status": "done|failed",
  "message": "Original message",
  "response": "ChatGPT response (if successful)",
  "error": "Error message (if failed)",
  "response_type": "thinking|auto|instant",
  "thinking_time": "standard|extended"
}
```

**Your webhook endpoint should:**
- Accept POST requests
- Return 2xx status code
- Process the response asynchronously if needed

---

## Request Lifecycle

1. **Client submits message** via API with API key
2. **System creates MessageRequest** with status `idle`
3. **WebSocket notifies browser extension** of new request
4. **Extension updates status** to `executing`
5. **Extension processes in ChatGPT** and sends response
6. **System updates status** to `done` or `failed`
7. **System sends webhook notification** to configured URL

---

## Example Usage

### Python Client Example

```python
import requests
import time

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Submit message
response = requests.post(
    f"{BASE_URL}/api/chat/submit/",
    headers=headers,
    json={
        "message": "Explain quantum computing",
        "response_type": "thinking",
        "thinking_time": "extended"
    }
)

request_data = response.json()
request_id = request_data["id"]
print(f"Request submitted: {request_id}")

# Poll for completion
while True:
    response = requests.get(
        f"{BASE_URL}/api/chat/requests/{request_id}/",
        headers=headers
    )
    data = response.json()
    
    if data["status"] == "done":
        print(f"Response: {data['response']}")
        break
    elif data["status"] == "failed":
        print(f"Error: {data['error_message']}")
        break
    
    time.sleep(2)
```

### JavaScript Client Example

```javascript
const API_KEY = 'your-api-key';
const BASE_URL = 'http://localhost:8000';

async function submitMessage(message) {
  const response = await fetch(`${BASE_URL}/api/chat/submit/`, {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: message,
      response_type: 'auto'
    })
  });
  
  return await response.json();
}

async function getStatus(requestId) {
  const response = await fetch(
    `${BASE_URL}/api/chat/requests/${requestId}/`,
    {
      headers: { 'X-API-Key': API_KEY }
    }
  );
  
  return await response.json();
}

// Usage
const request = await submitMessage('Hello ChatGPT!');
console.log('Request ID:', request.id);

// Check status
const status = await getStatus(request.id);
console.log('Status:', status.status);
```

---

## Error Handling

### API Errors

```json
{
  "detail": "Error message"
}
```

### Common Error Codes

- `400`: Bad request (invalid parameters)
- `401`: Unauthorized (invalid/missing API key)
- `404`: Not found (request doesn't exist)
- `500`: Server error

---

## Rate Limiting

Currently, there are no rate limits, but it's recommended to:
- Avoid submitting more than 10 requests per second
- Wait for previous requests to complete before submitting new ones
- Implement exponential backoff for retries

---

## Best Practices

1. **Store API keys securely** - Never commit API keys to version control
2. **Use webhooks** - Don't poll for status; configure a webhook endpoint
3. **Handle errors gracefully** - Implement retry logic for failed requests
4. **Monitor request status** - Track idle requests that may be stuck
5. **Use chat_id** - Continue conversations by providing the same chat_id
6. **Choose appropriate response_type** - Use thinking mode for complex queries

---

## Support

For issues or questions, please check the admin panel or contact support.
