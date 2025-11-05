# Chat Flow Documentation

## Overview

This document explains how chat creation and continuation works in the system.

## Chat Lifecycle

### Scenario 1: New Chat (No chat_id provided)

**Client Request:**
```json
POST /api/chat/submit/
{
  "message": "Hello, what is quantum computing?",
  "response_type": "auto"
  // No chat_id provided
}
```

**What Happens:**

1. **API creates new Chat record**
   - `chat_id`: `null` (will be filled by extension)
   - `title`: `null` (will be filled by extension)
   - `account`: Current account
   - Gets database ID (e.g., `123`)

2. **MessageRequest created**
   - Links to the new Chat (ID: 123)
   - Status: `idle`

3. **WebSocket sends to extension**
   ```json
   {
     "type": "new_request",
     "request_id": "uuid-123",
     "message": "Hello, what is quantum computing?",
     "response_type": "auto",
     "thinking_time": "standard",
     "chat_id": null,           // No existing ChatGPT chat
     "chat_db_id": 123          // Our database chat ID
   }
   ```

4. **Extension processes**
   - Sees `chat_id` is `null` → Creates new chat in ChatGPT
   - Sends message in new chat
   - Gets response and ChatGPT's chat ID (e.g., `"chatgpt-abc123"`)
   - Gets chat title from ChatGPT (e.g., `"Quantum Computing Basics"`)

5. **Extension responds**
   ```json
   {
     "type": "response",
     "request_id": "uuid-123",
     "response": "Quantum computing is...",
     "chat_id": "chatgpt-abc123",        // ChatGPT's chat ID
     "chat_title": "Quantum Computing Basics"
   }
   ```

6. **System updates Chat record**
   - `chat_id`: `"chatgpt-abc123"` ✓
   - `title`: `"Quantum Computing Basics"` ✓
   - MessageRequest status: `done`

7. **Webhook sent to client**
   ```json
   POST {webhook_url}
   {
     "request_id": "uuid-123",
     "status": "done",
     "message": "Hello, what is quantum computing?",
     "response": "Quantum computing is...",
     "error": null
   }
   ```

---

### Scenario 2: Continue Existing Chat (chat_id provided)

**Client Request:**
```json
POST /api/chat/submit/
{
  "message": "Can you explain more about qubits?",
  "response_type": "auto",
  "chat_id": "chatgpt-abc123"  // Existing ChatGPT chat ID
}
```

**What Happens:**

1. **API finds existing Chat**
   - Looks up Chat with `chat_id="chatgpt-abc123"`
   - Found: Chat ID 123 with title "Quantum Computing Basics"

2. **MessageRequest created**
   - Links to existing Chat (ID: 123)
   - Status: `idle`

3. **WebSocket sends to extension**
   ```json
   {
     "type": "new_request",
     "request_id": "uuid-456",
     "message": "Can you explain more about qubits?",
     "response_type": "auto",
     "thinking_time": "standard",
     "chat_id": "chatgpt-abc123",  // Continue this chat
     "chat_db_id": 123
   }
   ```

4. **Extension processes**
   - Sees `chat_id` is `"chatgpt-abc123"` → Opens existing chat
   - Sends message in that chat
   - Gets response

5. **Extension responds**
   ```json
   {
     "type": "response",
     "request_id": "uuid-456",
     "response": "Qubits are quantum bits...",
     "chat_id": "chatgpt-abc123",
     "chat_title": "Quantum Computing Basics"  // May update if changed
   }
   ```

6. **System updates**
   - MessageRequest status: `done`
   - Chat title updated if changed

7. **Webhook sent to client**

---

## API Endpoints for Chat Management

### List All Chats

```bash
GET /api/chat/chats/
Headers: X-API-Key: your-api-key
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
    "chat_id": "chatgpt-xyz789",
    "title": "Machine Learning Overview",
    "created_at": "2024-01-01T13:00:00Z",
    "updated_at": "2024-01-01T13:10:00Z"
  }
]
```

---

## Database Schema

### Chat Model
```python
class Chat(models.Model):
    id                # Auto-increment primary key
    chat_id           # ChatGPT website chat ID (nullable, filled by extension)
    account           # ForeignKey to GPTAccount
    title             # Chat title (nullable, filled by extension)
    created_at        # Auto timestamp
    updated_at        # Auto timestamp
```

### MessageRequest Model
```python
class MessageRequest(models.Model):
    id                # UUID primary key
    account           # ForeignKey to GPTAccount
    chat              # ForeignKey to Chat (nullable)
    message           # The message text
    response_type     # thinking/auto/instant
    thinking_time     # standard/extended
    status            # idle/executing/done/failed
    response          # ChatGPT's response
    error_message     # Error if failed
    queued_at         # Timestamp
    started_at        # Timestamp
    completed_at      # Timestamp
```

---

## Extension Implementation Guide

### When Receiving New Request

```javascript
// Extension receives WebSocket message
{
  "type": "new_request",
  "request_id": "uuid",
  "message": "User message",
  "chat_id": "chatgpt-abc123" or null,
  "chat_db_id": 123
}

// Extension logic
if (data.chat_id) {
  // Continue existing chat
  navigateToChatGPTChat(data.chat_id);
  sendMessage(data.message);
} else {
  // Create new chat
  createNewChatGPTChat();
  sendMessage(data.message);
}

// Wait for response...
const response = getChatGPTResponse();
const chatId = getCurrentChatGPTChatId();
const chatTitle = getCurrentChatTitle();

// Send back to server
websocket.send({
  "type": "response",
  "request_id": data.request_id,
  "response": response,
  "chat_id": chatId,
  "chat_title": chatTitle
});
```

---

## Client Usage Examples

### Start New Conversation

```python
import requests

headers = {"X-API-Key": "your-api-key"}

# First message - creates new chat
response = requests.post(
    "http://localhost:8000/api/chat/submit/",
    headers=headers,
    json={"message": "What is Python?"}
)
request1 = response.json()
# Wait for completion via webhook or polling...

# Get all chats to find the chat_id
chats = requests.get(
    "http://localhost:8000/api/chat/chats/",
    headers=headers
).json()

# Find the chat (most recent one)
latest_chat = chats[0]
chat_id = latest_chat["chat_id"]  # e.g., "chatgpt-abc123"

# Continue conversation
response = requests.post(
    "http://localhost:8000/api/chat/submit/",
    headers=headers,
    json={
        "message": "Can you give me an example?",
        "chat_id": chat_id  # Continue in same chat
    }
)
```

---

## Key Points

1. **Chat Creation**
   - Omit `chat_id` in request → New chat created
   - Chat starts with `null` chat_id and title
   - Extension fills these after creating ChatGPT chat

2. **Chat Continuation**
   - Provide `chat_id` in request → Continue existing chat
   - System validates chat exists and belongs to account

3. **Chat Tracking**
   - Each Chat has database ID (`id`) and ChatGPT ID (`chat_id`)
   - Use database ID internally
   - Use ChatGPT ID for API requests

4. **Extension Responsibilities**
   - Detect new vs existing chat via `chat_id` field
   - Always return `chat_id` and `chat_title` in response
   - Update chat info even for existing chats (title may change)

5. **Error Handling**
   - If chat_id provided but not found → 404 error
   - If extension fails → Send error type message
   - System tracks all states in MessageRequest
