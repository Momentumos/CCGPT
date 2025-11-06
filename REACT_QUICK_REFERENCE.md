# React App Quick Reference

## Setup

```javascript
// .env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_API_KEY=your-api-key-here

// src/config/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL,
  headers: {
    'X-API-Key': process.env.REACT_APP_API_KEY,
  },
});

export default api;
```

---

## Create Request

```javascript
const response = await api.post('/api/chat/submit/', {
  message: "Your message here",
  response_type: "auto",        // "thinking", "auto", "instant"
  thinking_time: "standard",    // "standard", "extended"
  chat_id: null,                // null for new chat, or chat_id to continue
});

// Response
{
  "id": "uuid",
  "status": "idle",
  "chat": { "id": 1, "chat_id": null, ... }
}
```

---

## Get Status (Polling)

```javascript
const response = await api.get(`/api/chat/requests/${requestId}/`);

// Response
{
  "id": "uuid",
  "status": "done",              // "idle", "executing", "done", "failed"
  "response": "Response text",
  "error_message": null,
  "chat": { "id": 1, "chat_id": "chatcmpl-xxx", ... }
}
```

---

## Webhook Payload

```json
{
  "request_id": "uuid",
  "status": "done",
  "message": "Original message",
  "response": "Response text",
  "error": null,
  "response_type": "auto",
  "thinking_time": "standard"
}
```

---

## Polling Hook

```javascript
import { useState, useEffect } from 'react';
import api from '../config/api';

export const useRequestPolling = (requestId) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!requestId) return;

    const poll = setInterval(async () => {
      const res = await api.get(`/api/chat/requests/${requestId}/`);
      setData(res.data);
      
      if (res.data.status === 'done' || res.data.status === 'failed') {
        clearInterval(poll);
        setLoading(false);
      }
    }, 2000);

    return () => clearInterval(poll);
  }, [requestId]);

  return { data, loading };
};
```

---

## Complete Flow

```javascript
// 1. Send message
const result = await api.post('/api/chat/submit/', {
  message: "Hello",
  response_type: "auto",
});

const requestId = result.data.id;

// 2. Poll for response
const poll = setInterval(async () => {
  const status = await api.get(`/api/chat/requests/${requestId}/`);
  
  if (status.data.status === 'done') {
    console.log('Response:', status.data.response);
    clearInterval(poll);
  }
}, 2000);

// 3. Continue conversation
const nextResult = await api.post('/api/chat/submit/', {
  message: "Follow-up question",
  chat_id: status.data.chat.chat_id,  // Use chat_id from previous response
});
```

---

## Status Values

| Status | Description |
|--------|-------------|
| `idle` | Waiting for extension to process |
| `executing` | Extension is processing |
| `done` | Completed successfully |
| `failed` | Failed with error |

---

## Response Types

| Type | Description |
|------|-------------|
| `thinking` | Use ChatGPT's "Think" mode |
| `auto` | Let ChatGPT decide |
| `instant` | Use instant response |

---

## Error Handling

```javascript
try {
  const result = await api.post('/api/chat/submit/', { message });
} catch (error) {
  if (error.response?.status === 401) {
    console.error('Invalid API key');
  } else if (error.response?.status === 404) {
    console.error('Chat not found');
  } else {
    console.error('Request failed');
  }
}
```

---

## Best Practices

✅ **Store chat_id** - Continue conversations  
✅ **Implement timeouts** - Don't poll forever  
✅ **Handle errors** - Show user-friendly messages  
✅ **Use webhooks in production** - More efficient than polling  
✅ **Secure API keys** - Never expose in frontend  
✅ **Show loading states** - Better UX  

---

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/submit/` | POST | Create request |
| `/api/chat/requests/{id}/` | GET | Get status |
| `/api/chat/requests/` | GET | List all |
| `/api/chat/chats/` | GET | List chats |

---

## Testing

```bash
# Create request
curl -X POST http://localhost:8000/api/chat/submit/ \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Test"}'

# Get status
curl http://localhost:8000/api/chat/requests/REQUEST_ID/ \
  -H "X-API-Key: YOUR_KEY"
```
