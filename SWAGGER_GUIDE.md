# Swagger API Documentation Guide

## Accessing the Documentation

After starting your Docker containers, access the interactive API documentation at:

### 🎯 Swagger UI (Recommended)
**URL:** http://localhost:8000/api/docs/

Interactive interface with:
- Try-it-out functionality
- Request/response examples
- Authentication testing
- Model schemas

### 📖 ReDoc
**URL:** http://localhost:8000/api/redoc/

Clean, readable documentation with:
- Three-panel layout
- Search functionality
- Code samples
- Detailed descriptions

### 📄 OpenAPI Schema
**URL:** http://localhost:8000/api/schema/

Raw OpenAPI 3.0 schema in JSON format for:
- API client generation
- Custom documentation tools
- Integration with other services

---

## Using Swagger UI

### 1. Authentication Setup

All endpoints require API key authentication:

1. Click the **"Authorize"** button at the top right
2. Enter your API key in the `X-API-Key` field
3. Click **"Authorize"**
4. Click **"Close"**

Now all requests will include your API key automatically.

### 2. Testing Endpoints

#### Submit a Message Request

1. Navigate to **POST /api/chat/submit/**
2. Click **"Try it out"**
3. Edit the request body:
   ```json
   {
     "message": "Explain quantum computing in simple terms",
     "response_type": "thinking",
     "thinking_time": "extended"
   }
   ```
4. Click **"Execute"**
5. View the response below with status code and data

#### Check Request Status

1. Copy the `id` from the previous response
2. Navigate to **GET /api/chat/requests/{request_id}/**
3. Click **"Try it out"**
4. Paste the request ID in the `request_id` field
5. Click **"Execute"**
6. View the current status and response

---

## Request Examples

### Example 1: New Chat with Thinking Mode

**Request:**
```json
POST /api/chat/submit/
{
  "message": "Explain quantum computing in simple terms",
  "response_type": "thinking",
  "thinking_time": "extended"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Explain quantum computing in simple terms",
  "response_type": "thinking",
  "thinking_time": "extended",
  "status": "idle",
  "response": null,
  "error_message": null,
  "chat": 1,
  "queued_at": "2024-01-15T10:30:00Z",
  "started_at": null,
  "completed_at": null
}
```

### Example 2: Continue Existing Chat

**Request:**
```json
POST /api/chat/submit/
{
  "message": "Can you give me more details?",
  "response_type": "auto",
  "chat_id": "chatcmpl-abc123xyz"
}
```

**Response (201 Created):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "message": "Can you give me more details?",
  "response_type": "auto",
  "thinking_time": "standard",
  "status": "idle",
  "response": null,
  "error_message": null,
  "chat": 1,
  "queued_at": "2024-01-15T10:35:00Z",
  "started_at": null,
  "completed_at": null
}
```

### Example 3: Check Completed Request

**Request:**
```
GET /api/chat/requests/550e8400-e29b-41d4-a716-446655440000/
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Explain quantum computing in simple terms",
  "response_type": "thinking",
  "thinking_time": "extended",
  "status": "done",
  "response": "Quantum computing is a type of computing that uses quantum-mechanical phenomena such as superposition and entanglement to perform operations on data. Unlike classical computers that use bits (0 or 1), quantum computers use quantum bits or 'qubits' that can exist in multiple states simultaneously...",
  "error_message": null,
  "chat": 1,
  "queued_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:30:05Z",
  "completed_at": "2024-01-15T10:30:45Z"
}
```

### Example 4: List Requests with Filter

**Request:**
```
GET /api/chat/requests/?status=done
```

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Explain quantum computing",
    "response_type": "thinking",
    "thinking_time": "extended",
    "status": "done",
    "response": "Quantum computing is...",
    "error_message": null,
    "chat": 1,
    "queued_at": "2024-01-15T10:30:00Z",
    "started_at": "2024-01-15T10:30:05Z",
    "completed_at": "2024-01-15T10:30:45Z"
  }
]
```

---

## Response Status Codes

### Success Codes
- **200 OK** - Request successful
- **201 Created** - Resource created successfully

### Client Error Codes
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Missing or invalid API key
- **404 Not Found** - Resource not found

### Server Error Codes
- **500 Internal Server Error** - Server error

---

## Request States

Message requests go through these states:

1. **idle** - Request queued, waiting for extension
2. **executing** - Extension is processing the request
3. **done** - Successfully completed with response
4. **failed** - Failed with error message

---

## Response Types

### thinking
Use ChatGPT's thinking mode for complex reasoning:
- **thinking_time: standard** - Normal thinking duration
- **thinking_time: extended** - Longer thinking for complex problems

### auto
Let ChatGPT automatically choose the best mode

### instant
Get quick responses without extended thinking

---

## Tips for Using Swagger UI

1. **Save Your API Key**: After authorizing once, it persists during your session
2. **Use Examples**: Click on examples in the request body for quick testing
3. **Copy as cURL**: Use the "Copy as cURL" button to get command-line examples
4. **Download Spec**: Download the OpenAPI spec for offline use or client generation
5. **Search**: Use Ctrl+F (Cmd+F on Mac) to search through the documentation

---

## Generating API Clients

Use the OpenAPI schema to generate client libraries:

### Python
```bash
# Install openapi-generator
pip install openapi-generator-cli

# Generate Python client
openapi-generator-cli generate \
  -i http://localhost:8000/api/schema/ \
  -g python \
  -o ./python-client
```

### JavaScript/TypeScript
```bash
# Install openapi-generator
npm install @openapitools/openapi-generator-cli -g

# Generate TypeScript client
openapi-generator-cli generate \
  -i http://localhost:8000/api/schema/ \
  -g typescript-axios \
  -o ./typescript-client
```

### Other Languages
OpenAPI Generator supports 50+ languages including:
- Java
- Go
- Ruby
- PHP
- C#
- Swift
- Kotlin
- And many more...

---

## Troubleshooting

### "Failed to fetch" Error
- Ensure Docker containers are running: `docker-compose ps`
- Check if the API is accessible: `curl http://localhost:8000/api/docs/`
- Verify CORS settings if accessing from different domain

### "401 Unauthorized" Error
- Click "Authorize" and enter your API key
- Verify your API key is active in the admin panel
- Check that the account is not deactivated

### "404 Not Found" Error
- Verify the resource exists (chat_id, request_id)
- Ensure you're using the correct endpoint URL
- Check that the resource belongs to your account

---

## Additional Resources

- **Full API Documentation**: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **README**: See [README.md](README.md) for setup instructions
- **OpenAPI Specification**: https://swagger.io/specification/
- **drf-spectacular Docs**: https://drf-spectacular.readthedocs.io/
