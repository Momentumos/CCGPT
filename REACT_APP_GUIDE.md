# React Application Integration Guide

Complete guide for integrating your React application with the ChatGPT Bridge API using REST endpoints and webhook callbacks.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Setup](#setup)
- [Creating Requests](#creating-requests)
- [Receiving Responses](#receiving-responses)
- [Complete Example](#complete-example)
- [Best Practices](#best-practices)

---

## Overview

Your React application communicates with the ChatGPT Bridge API using:

1. **REST API** - To create and manage message requests
2. **Webhook Callbacks** - To receive responses asynchronously
3. **Polling (Alternative)** - For development without webhooks

**Flow:**
```
React App → API (Create Request) → Extension → API → Webhook → Your Backend → React App
```

---

## Architecture

```
┌─────────────────┐
│   React App     │  1. POST /api/chat/submit/
│  (Frontend)     │────────────────────────────┐
└─────────────────┘                            │
                                               ↓
                                    ┌─────────────────┐
                                    │  Bridge API     │
                                    │   (Server)      │
                                    └────────┬────────┘
                                             │ 2. WebSocket
                                             ↓
                                    ┌─────────────────┐
                                    │   Extension     │
                                    │  (Processes)    │
                                    └────────┬────────┘
                                             │ 3. Response
                                             ↓
                                    ┌─────────────────┐
                                    │  Bridge API     │
                                    └────────┬────────┘
                                             │ 4. POST webhook
                                             ↓
┌─────────────────┐              ┌─────────────────┐
│   React App     │ 5. Update    │  Your Backend   │
│  (Updates UI)   │◄─────────────│  (Receives)     │
└─────────────────┘              └─────────────────┘
```

---

## Setup

### 1. Install Dependencies

```bash
npm install axios
```

### 2. Environment Variables

```env
# .env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_API_KEY=your-api-key-here
```

### 3. API Configuration

```javascript
// src/config/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': process.env.REACT_APP_API_KEY,
  },
});

export default api;
```

### 4. Get Your API Key

1. Login to admin: `http://localhost:8000/admin/`
2. Go to **GPT Accounts**
3. Copy your **API Key**
4. Set your **Webhook URL**: `https://your-app.com/api/webhooks/chatgpt`

---

## Creating Requests

### Basic Service

```javascript
// src/services/chatService.js
import api from '../config/api';

export const createChatRequest = async (message, options = {}) => {
  const response = await api.post('/api/chat/submit/', {
    message: message,
    response_type: options.responseType || 'auto',
    thinking_time: options.thinkingTime || 'standard',
    chat_id: options.chatId || null,
  });
  
  return response.data;
};

export const getRequestStatus = async (requestId) => {
  const response = await api.get(`/api/chat/requests/${requestId}/`);
  return response.data;
};

export const listChats = async () => {
  const response = await api.get('/api/chat/chats/');
  return response.data;
};
```

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `message` | string | Yes | - | Message to send to ChatGPT |
| `response_type` | string | No | `"auto"` | `"thinking"`, `"auto"`, or `"instant"` |
| `thinking_time` | string | No | `"standard"` | `"standard"` or `"extended"` |
| `chat_id` | string | No | `null` | ChatGPT chat ID to continue conversation |

### Response Format

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Explain quantum computing",
  "response_type": "thinking",
  "thinking_time": "extended",
  "status": "idle",
  "response": null,
  "error_message": null,
  "chat": {
    "id": 1,
    "chat_id": null,
    "title": null,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "queued_at": "2024-01-15T10:30:00Z",
  "started_at": null,
  "completed_at": null,
  "last_retrieved_at": null
}
```

---

## Receiving Responses

### Option 1: Webhook Callbacks (Production)

#### Webhook Payload

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "done",
  "message": "Explain quantum computing",
  "response": "Quantum computing is...",
  "error": null,
  "response_type": "thinking",
  "thinking_time": "extended"
}
```

#### Backend Webhook Handler (Express.js)

```javascript
// backend/routes/webhooks.js
const express = require('express');
const router = express.Router();

// Store SSE connections
const sseConnections = new Map();

// Webhook endpoint
router.post('/chatgpt', express.json(), (req, res) => {
  const { request_id, status, response, error } = req.body;
  
  console.log('Webhook received:', request_id, status);
  
  // Broadcast to connected clients
  const connections = sseConnections.get(request_id) || [];
  connections.forEach(client => {
    client.write(`data: ${JSON.stringify(req.body)}\n\n`);
  });
  
  sseConnections.delete(request_id);
  res.status(200).json({ received: true });
});

// SSE endpoint for React
router.get('/stream/:requestId', (req, res) => {
  const { requestId } = req.params;
  
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  
  if (!sseConnections.has(requestId)) {
    sseConnections.set(requestId, []);
  }
  sseConnections.get(requestId).push(res);
  
  req.on('close', () => {
    const connections = sseConnections.get(requestId) || [];
    const index = connections.indexOf(res);
    if (index > -1) connections.splice(index, 1);
  });
});

module.exports = router;
```

#### React Component with SSE

```javascript
// src/hooks/useSSE.js
import { useEffect, useState } from 'react';

export const useSSE = (requestId) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!requestId) return;

    const eventSource = new EventSource(
      `http://your-backend.com/api/webhooks/stream/${requestId}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setData(data);
      eventSource.close();
    };

    eventSource.onerror = (err) => {
      setError(err);
      eventSource.close();
    };

    return () => eventSource.close();
  }, [requestId]);

  return { data, error };
};
```

### Option 2: Polling (Development)

```javascript
// src/hooks/useRequestPolling.js
import { useState, useEffect } from 'react';
import { getRequestStatus } from '../services/chatService';

export const useRequestPolling = (requestId, interval = 2000) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!requestId) return;

    let pollInterval;
    let mounted = true;

    const poll = async () => {
      try {
        const status = await getRequestStatus(requestId);
        
        if (mounted) {
          setData(status);
          setLoading(false);
          
          if (status.status === 'done' || status.status === 'failed') {
            clearInterval(pollInterval);
          }
        }
      } catch (error) {
        if (mounted) {
          setLoading(false);
          clearInterval(pollInterval);
        }
      }
    };

    poll();
    pollInterval = setInterval(poll, interval);

    return () => {
      mounted = false;
      clearInterval(pollInterval);
    };
  }, [requestId, interval]);

  return { data, loading };
};
```

---

## Complete Example

### Full Chat Application

```javascript
// src/App.jsx
import React, { useState } from 'react';
import { createChatRequest, getRequestStatus } from './services/chatService';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [currentChatId, setCurrentChatId] = useState(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = {
      id: Date.now(),
      text: input,
      sender: 'user',
    };

    setMessages(prev => [...prev, userMessage]);
    const messageText = input;
    setInput('');

    try {
      const result = await createChatRequest(messageText, {
        response_type: 'auto',
        chat_id: currentChatId,
      });

      const assistantMessage = {
        id: result.id,
        requestId: result.id,
        text: null,
        sender: 'assistant',
        status: 'pending',
      };

      setMessages(prev => [...prev, assistantMessage]);
      pollForResponse(result.id);

    } catch (error) {
      console.error('Error:', error);
    }
  };

  const pollForResponse = async (requestId) => {
    const maxAttempts = 60;
    let attempts = 0;

    const poll = setInterval(async () => {
      attempts++;

      try {
        const data = await getRequestStatus(requestId);

        if (data.status === 'done') {
          clearInterval(poll);
          
          setMessages(prev => prev.map(msg =>
            msg.requestId === requestId
              ? { ...msg, text: data.response, status: 'done' }
              : msg
          ));

          if (data.chat && data.chat.chat_id) {
            setCurrentChatId(data.chat.chat_id);
          }

        } else if (data.status === 'failed') {
          clearInterval(poll);
          
          setMessages(prev => prev.map(msg =>
            msg.requestId === requestId
              ? { ...msg, text: `Error: ${data.error_message}`, status: 'failed' }
              : msg
          ));
        }

        if (attempts >= maxAttempts) {
          clearInterval(poll);
        }

      } catch (error) {
        clearInterval(poll);
      }
    }, 2000);
  };

  return (
    <div className="app">
      <div className="header">
        <h1>ChatGPT Bridge</h1>
      </div>

      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.sender}`}>
            {msg.text || <div className="loading">...</div>}
          </div>
        ))}
      </div>

      <div className="input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Type a message..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

export default App;
```

### Styling

```css
/* src/App.css */
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0 auto;
}

.header {
  padding: 1rem;
  background: #2c3e50;
  color: white;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: #ecf0f1;
}

.message {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 1rem;
  max-width: 70%;
}

.message.user {
  background: #3498db;
  color: white;
  margin-left: auto;
}

.message.assistant {
  background: white;
  color: #2c3e50;
}

.loading {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.input-area {
  display: flex;
  padding: 1rem;
  background: white;
  border-top: 1px solid #ddd;
}

.input-area input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
}

.input-area button {
  margin-left: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
}
```

---

## Best Practices

### 1. Store Chat IDs
```javascript
// Continue conversations
const [currentChatId, setCurrentChatId] = useState(null);

if (response.chat && response.chat.chat_id) {
  setCurrentChatId(response.chat.chat_id);
}
```

### 2. Handle Timeouts
```javascript
const MAX_POLL_TIME = 120000; // 2 minutes
const startTime = Date.now();

if (Date.now() - startTime > MAX_POLL_TIME) {
  clearInterval(poll);
  handleTimeout();
}
```

### 3. Error Handling
```javascript
try {
  const result = await createChatRequest(message);
} catch (error) {
  if (error.response?.status === 401) {
    alert('Invalid API key');
  } else {
    alert('Failed to send message');
  }
}
```

### 4. Secure API Keys
**Never expose API keys in frontend code!**

```javascript
// ❌ Bad
const API_KEY = 'your-api-key';

// ✅ Good - Proxy through your backend
// Frontend → Your Backend → ChatGPT Bridge
```

### 5. Loading States
```javascript
const [loading, setLoading] = useState(false);

// Show loading UI
{loading && <div>Sending...</div>}
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/submit/` | POST | Create message request |
| `/api/chat/requests/` | GET | List all requests |
| `/api/chat/requests/next-idle/` | GET | Get next idle request |
| `/api/chat/requests/{id}/` | GET | Get request status |
| `/api/chat/chats/` | GET | List all chats |
| `/api/chat/chats/{chat_id}/` | GET | Get chat details |

---

## Testing

```bash
# Test creating a request
curl -X POST http://localhost:8000/api/chat/submit/ \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "response_type": "auto"}'

# Test getting status
curl -X GET http://localhost:8000/api/chat/requests/REQUEST_ID/ \
  -H "X-API-Key: YOUR_API_KEY"
```

---

## Support

- **Swagger Docs**: `/api/docs/`
- **Admin Panel**: `/admin/`
- **Health Check**: `/health/`

---

**Happy coding! 🚀**
