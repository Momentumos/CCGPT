// ChatGPT Bridge Client Application
class ChatApp {
    constructor() {
        this.apiKey = null;
        this.currentChatId = null;
        this.messages = [];
        this.pollingIntervals = new Map();
        this.baseURL = window.location.origin;
        
        this.init();
    }

    init() {
        // Check if already logged in
        const savedApiKey = localStorage.getItem('chatgpt_bridge_api_key');
        if (savedApiKey) {
            this.apiKey = savedApiKey;
            this.showChatScreen();
        }

        this.attachEventListeners();
    }

    attachEventListeners() {
        // Login form
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });

        // New chat button
        document.getElementById('new-chat-btn').addEventListener('click', () => {
            this.startNewChat();
        });

        // Send button
        document.getElementById('send-btn').addEventListener('click', () => {
            this.sendMessage();
        });

        // Message input - Enter to send, Shift+Enter for new line
        document.getElementById('message-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
        document.getElementById('message-input').addEventListener('input', (e) => {
            e.target.style.height = 'auto';
            e.target.style.height = e.target.scrollHeight + 'px';
        });
    }

    async handleLogin() {
        const apiKeyInput = document.getElementById('api-key');
        const apiKey = apiKeyInput.value.trim();
        const errorDiv = document.getElementById('login-error');
        const submitBtn = document.querySelector('#login-form button');

        if (!apiKey) {
            this.showError(errorDiv, 'Please enter an API key');
            return;
        }

        // Disable form
        submitBtn.disabled = true;
        submitBtn.textContent = 'Connecting...';
        errorDiv.style.display = 'none';

        try {
            // Test the API key by making a request
            const response = await fetch(`${this.baseURL}/api/chat/requests/`, {
                headers: {
                    'X-API-Key': apiKey,
                }
            });

            if (response.ok) {
                // API key is valid
                this.apiKey = apiKey;
                localStorage.setItem('chatgpt_bridge_api_key', apiKey);
                this.showChatScreen();
            } else if (response.status === 401) {
                this.showError(errorDiv, 'Invalid API key. Please check and try again.');
            } else {
                this.showError(errorDiv, 'Connection failed. Please try again.');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError(errorDiv, 'Connection error. Please check if the server is running.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Connect';
        }
    }

    handleLogout() {
        if (confirm('Are you sure you want to logout?')) {
            localStorage.removeItem('chatgpt_bridge_api_key');
            this.apiKey = null;
            this.currentChatId = null;
            this.messages = [];
            
            // Close all SSE connections
            this.pollingIntervals.forEach(connection => {
                if (connection instanceof EventSource) {
                    connection.close();
                } else {
                    clearInterval(connection);
                }
            });
            this.pollingIntervals.clear();
            
            this.showLoginScreen();
        }
    }

    startNewChat() {
        if (this.messages.length > 0) {
            if (confirm('Start a new conversation? Current chat will be saved.')) {
                this.currentChatId = null;
                this.messages = [];
                this.renderMessages();
            }
        }
    }

    showLoginScreen() {
        document.getElementById('login-screen').classList.add('active');
        document.getElementById('chat-screen').classList.remove('active');
        document.getElementById('api-key').value = '';
    }

    showChatScreen() {
        document.getElementById('login-screen').classList.remove('active');
        document.getElementById('chat-screen').classList.add('active');
        this.renderMessages();
    }

    showError(element, message) {
        element.textContent = message;
        element.style.display = 'block';
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();

        if (!message) return;

        const responseType = document.getElementById('response-type').value;
        const thinkingTime = document.getElementById('thinking-time').value;
        const sendBtn = document.getElementById('send-btn');

        // Add user message to UI
        this.addMessage({
            text: message,
            sender: 'user',
            timestamp: new Date(),
        });

        // Clear input
        input.value = '';
        input.style.height = 'auto';

        // Disable send button
        sendBtn.disabled = true;

        try {
            // Create request
            const response = await fetch(`${this.baseURL}/api/chat/submit/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey,
                },
                body: JSON.stringify({
                    message: message,
                    response_type: responseType,
                    thinking_time: thinkingTime,
                    chat_id: this.currentChatId,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Add assistant message placeholder
            const assistantMessage = {
                id: data.id,
                requestId: data.id,
                text: null,
                sender: 'assistant',
                timestamp: new Date(),
                status: 'pending',
            };

            this.addMessage(assistantMessage);

            // Start polling for response
            this.pollForResponse(data.id);

        } catch (error) {
            console.error('Send message error:', error);
            this.addMessage({
                text: 'Failed to send message. Please try again.',
                sender: 'assistant',
                timestamp: new Date(),
                error: true,
            });
        } finally {
            sendBtn.disabled = false;
        }
    }

    pollForResponse(requestId) {
        console.log('📡 Connecting to SSE for request:', requestId);
        
        // Connect to SSE endpoint
        const eventSource = new EventSource(`${this.baseURL}/api/sse/${requestId}/`);
        
        eventSource.onopen = () => {
            console.log('✅ SSE connection established');
        };
        
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('📨 SSE message received:', data);
                
                if (data.type === 'connected') {
                    // Initial connection confirmation
                    return;
                }
                
                // Handle webhook data
                if (data.status === 'done') {
                    eventSource.close();
                    
                    // Update message with response
                    this.updateMessage(requestId, {
                        text: data.response,
                        status: 'done',
                    });
                    
                    console.log('✅ Response received successfully');
                    
                } else if (data.status === 'failed') {
                    eventSource.close();
                    
                    this.updateMessage(requestId, {
                        text: data.error || 'Request failed',
                        status: 'failed',
                        error: true,
                    });
                    
                    console.log('❌ Request failed');
                }
                
            } catch (error) {
                console.error('Error parsing SSE data:', error);
            }
        };
        
        eventSource.onerror = (error) => {
            console.error('❌ SSE error:', error);
            eventSource.close();
            
            // Fallback: try to get status via API
            this.fallbackToPolling(requestId);
        };
        
        // Store event source for cleanup
        this.pollingIntervals.set(requestId, eventSource);
    }
    
    async fallbackToPolling(requestId) {
        console.log('🔄 Falling back to polling for request:', requestId);
        
        try {
            const response = await fetch(`${this.baseURL}/api/chat/requests/${requestId}/`, {
                headers: {
                    'X-API-Key': this.apiKey,
                },
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.status === 'done') {
                    this.updateMessage(requestId, {
                        text: data.response,
                        status: 'done',
                    });
                } else if (data.status === 'failed') {
                    this.updateMessage(requestId, {
                        text: data.error_message || 'Request failed',
                        status: 'failed',
                        error: true,
                    });
                } else {
                    // Still processing, show message
                    this.updateMessage(requestId, {
                        text: 'Waiting for response...',
                        status: 'processing',
                    });
                }
            }
        } catch (error) {
            console.error('Fallback polling error:', error);
            this.updateMessage(requestId, {
                text: 'Connection lost. Please refresh and try again.',
                status: 'error',
                error: true,
            });
        }
    }

    addMessage(message) {
        this.messages.push(message);
        this.renderMessages();
    }

    updateMessage(requestId, updates) {
        const messageIndex = this.messages.findIndex(m => m.requestId === requestId);
        if (messageIndex !== -1) {
            this.messages[messageIndex] = {
                ...this.messages[messageIndex],
                ...updates,
            };
            this.renderMessages();
        }
    }

    renderMessages() {
        const container = document.getElementById('messages-container');
        
        if (this.messages.length === 0) {
            container.innerHTML = `
                <div class="welcome-message">
                    <h3>👋 Welcome to ChatGPT Bridge</h3>
                    <p>Start a conversation by typing a message below.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.messages.map(msg => this.renderMessage(msg)).join('');
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    renderMessage(message) {
        const time = message.timestamp.toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        let content = '';
        let statusText = '';

        if (message.sender === 'user') {
            content = this.escapeHtml(message.text);
        } else {
            if (message.text) {
                if (message.error) {
                    content = `<span class="error-content">${this.escapeHtml(message.text)}</span>`;
                } else {
                    content = this.escapeHtml(message.text);
                }
            } else {
                // Loading state
                if (message.status === 'executing') {
                    statusText = '<div class="message-status">Processing...</div>';
                } else {
                    statusText = '<div class="message-status">Waiting...</div>';
                }
                content = `
                    <div class="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                `;
            }
        }

        return `
            <div class="message ${message.sender}">
                <div class="message-content">${content}</div>
                ${statusText}
                <div class="message-time">${time}</div>
            </div>
        `;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
