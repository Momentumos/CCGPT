# HTML/JS Client Application

A simple, beautiful web client for the ChatGPT Bridge API, built with vanilla HTML, CSS, and JavaScript.

---

## Features

✨ **Beautiful UI** - Modern gradient design with smooth animations  
🔐 **API Key Authentication** - Secure login with API key  
💬 **Real-time Chat** - Send messages and receive responses  
🔄 **Webhook + SSE** - Real-time updates via Server-Sent Events  
📝 **Conversation Continuity** - Maintains chat history  
⚙️ **Configurable Options** - Choose response type and thinking time  
📱 **Responsive Design** - Works on desktop and mobile  
⚡ **Instant Updates** - No polling, instant response delivery  

---

## Access the Client

The client is hosted on your Django server at:

- **Root**: `http://localhost:8000/`
- **Client path**: `http://localhost:8000/client/`

---

## How to Use

### 1. Get Your API Key and Set Webhook URL

1. Go to the admin panel: `http://localhost:8000/admin/`
2. Login with your superuser credentials
3. Navigate to **GPT Accounts**
4. Create or edit your account:
   - **Email**: Your identifier
   - **API Key**: Copy this for login
   - **Webhook URL**: `http://localhost:8000/api/webhooks/chatgpt/`
   - **Is Active**: ✓ (checked)
5. Click **Save**

### 2. Login to the Client

1. Open `http://localhost:8000/` in your browser
2. Enter your API key
3. Click **Connect**

### 3. Start Chatting

1. Type your message in the input box
2. Choose response type (Auto, Thinking, or Instant)
3. Choose thinking time (Standard or Extended)
4. Press **Enter** or click the **Send** button
5. Wait for the response (indicated by loading dots)

### 4. Continue Conversations

- Messages in the same session continue the same chat
- Click **New Chat** to start a fresh conversation
- Your chat history is maintained automatically

---

## Response Types

| Type | Description |
|------|-------------|
| **Auto** | Let ChatGPT decide the best response mode |
| **Thinking** | Use ChatGPT's "Think" mode for deeper reasoning |
| **Instant** | Get quick, instant responses |

## Thinking Time

| Time | Description |
|------|-------------|
| **Standard** | Normal thinking duration |
| **Extended** | Longer thinking time for complex questions |

---

## Technical Details

### Architecture

```
Client (Browser)
    ↓ 1. POST /api/chat/submit/
Django Server (API)
    ↓ 2. WebSocket
Browser Extension (Processing)
    ↓ 3. ChatGPT
ChatGPT Website
    ↓ 4. Response
Browser Extension
    ↓ 5. WebSocket
Django Server
    ↓ 6. POST /api/webhooks/chatgpt/
Django Server (Webhook)
    ↓ 7. SSE (Server-Sent Events)
Client (Browser) - Instant Update!
```

### Files Structure

```
templates/client/
    └── index.html          # Main HTML template

static/client/
    ├── css/
    │   └── style.css       # Styling
    └── js/
        └── app.js          # Application logic

chat/
    └── client_views.py     # Django view
```

### How It Works

1. **Login**: Validates API key by making a test request to `/api/chat/requests/`
2. **Send Message**: POST to `/api/chat/submit/` with message and options
3. **Connect SSE**: Opens EventSource connection to `/api/sse/{request_id}/`
4. **Wait for Webhook**: Server receives webhook and broadcasts via SSE
5. **Instant Update**: UI updates immediately when response arrives
6. **Continue Chat**: Use `chat_id` from response for next message

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/requests/` | GET | Validate API key |
| `/api/chat/submit/` | POST | Create message request |
| `/api/sse/{id}/` | GET (SSE) | Real-time response updates |
| `/api/webhooks/chatgpt/` | POST | Receive webhook from API |

---

## Features Explained

### Auto-resize Textarea
The message input automatically expands as you type multiple lines.

### Loading States
- **Waiting...** - Request queued, waiting for extension
- **Processing...** - Extension is actively processing
- **Loading dots** - Visual indicator while waiting

### Error Handling
- Invalid API key detection
- Connection error messages
- Request timeout after 2 minutes
- Failed request notifications

### Local Storage
- API key is saved in browser's localStorage
- Automatically logs you in on return visits
- Cleared on logout

---

## Keyboard Shortcuts

- **Enter** - Send message
- **Shift + Enter** - New line in message

---

## Customization

### Change Colors

Edit `static/client/css/style.css`:

```css
/* Main gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Change to your colors */
background: linear-gradient(135deg, #your-color-1 0%, #your-color-2 100%);
```

### Change Polling Interval

Edit `static/client/js/app.js`:

```javascript
// Current: Poll every 2 seconds
}, 2000);

// Change to 3 seconds
}, 3000);
```

### Change Timeout

Edit `static/client/js/app.js`:

```javascript
// Current: 60 attempts × 2s = 2 minutes
const maxAttempts = 60;

// Change to 3 minutes
const maxAttempts = 90;
```

---

## Troubleshooting

### Login Issues

**Problem**: "Invalid API key" error  
**Solution**: 
- Check API key is correct
- Verify account is active in admin panel
- Ensure server is running

**Problem**: "Connection error"  
**Solution**:
- Check if Django server is running
- Verify URL is correct
- Check browser console for errors

### Message Issues

**Problem**: Messages not sending  
**Solution**:
- Check API key is still valid
- Verify extension is connected
- Check server logs

**Problem**: No response received  
**Solution**:
- Ensure browser extension is running
- Check extension is logged into ChatGPT
- Wait up to 2 minutes for timeout

### Display Issues

**Problem**: Styles not loading  
**Solution**:
- Run `python manage.py collectstatic`
- Check static files configuration
- Clear browser cache

---

## Development

### Local Development

```bash
# Start Django server
python manage.py runserver

# Or with Docker
docker-compose up
```

### Production Deployment

1. Set `DEBUG=False` in settings
2. Run `python manage.py collectstatic`
3. Configure proper static files serving
4. Use HTTPS for security

---

## Browser Compatibility

✅ Chrome/Edge (recommended)  
✅ Firefox  
✅ Safari  
✅ Opera  

Requires modern browser with:
- ES6 JavaScript support
- Fetch API
- LocalStorage
- CSS Grid/Flexbox

---

## Security Notes

⚠️ **API Key Storage**: Stored in browser's localStorage  
⚠️ **HTTPS**: Use HTTPS in production  
⚠️ **CORS**: Configure CORS for production domains  

---

## Future Enhancements

Potential improvements:
- [ ] WebSocket support for real-time updates
- [ ] Message history persistence
- [ ] Export chat functionality
- [ ] Dark mode toggle
- [ ] Multiple chat sessions
- [ ] File upload support
- [ ] Voice input
- [ ] Markdown rendering

---

## Support

For issues or questions:
- Check server logs: `docker-compose logs web`
- Review API documentation: `/api/docs/`
- Test API endpoints with Swagger UI

---

**Enjoy chatting! 🚀**
