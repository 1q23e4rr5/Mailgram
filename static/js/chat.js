class ChatApp {
    constructor() {
        this.socket = io();
        this.currentChat = null;
        this.currentGroup = null;
        this.typingTimer = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupSocketListeners();
    }

    bindEvents() {
        // Message input events
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('input', () => this.handleTyping());
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // Send button
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        // File upload
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        if (uploadBtn && fileInput) {
            uploadBtn.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
        }
    }

    setupSocketListeners() {
        // Private messages
        this.socket.on('new_message', (data) => {
            this.displayMessage(data, 'received');
            this.scrollToBottom();
        });

        this.socket.on('message_sent', (data) => {
            this.updateMessageTimestamp(data.id, data.timestamp);
        });

        // Group messages
        this.socket.on('new_group_message', (data) => {
            if (this.currentGroup && data.group_id == this.currentGroup) {
                this.displayMessage(data, 'received');
                this.scrollToBottom();
            }
        });

        // Typing indicators
        this.socket.on('user_typing', (data) => {
            this.showTypingIndicator(data);
        });

        this.socket.on('group_typing', (data) => {
            if (this.currentGroup && data.group_id == this.currentGroup) {
                this.showTypingIndicator(data);
            }
        });

        // User status
        this.socket.on('user_status', (data) => {
            this.updateUserStatus(data.user_id, data.status);
        });
    }

    setCurrentChat(userId) {
        this.currentChat = userId;
        this.currentGroup = null;
        this.clearMessages();
        this.loadChatHistory();
    }

    setCurrentGroup(groupId) {
        this.currentGroup = groupId;
        this.currentChat = null;
        this.clearMessages();
        this.loadGroupHistory();
    }

    loadChatHistory() {
        // Messages are loaded with the page, no additional AJAX needed
        this.scrollToBottom();
    }

    loadGroupHistory() {
        // Messages are loaded with the page, no additional AJAX needed
        this.scrollToBottom();
    }

    sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) return;

        if (this.currentChat) {
            this.sendPrivateMessage(message);
        } else if (this.currentGroup) {
            this.sendGroupMessage(message);
        }

        messageInput.value = '';
        this.stopTyping();
    }

    sendPrivateMessage(message) {
        const messageData = {
            receiver_id: this.currentChat,
            message: message,
            type: 'text'
        };

        // Display message immediately
        const tempMessage = {
            id: 'temp-' + Date.now(),
            sender_id: currentUserId,
            sender_name: currentUserName,
            content: message,
            timestamp: new Date().toISOString(),
            type: 'text'
        };

        this.displayMessage(tempMessage, 'sent');
        this.scrollToBottom();

        // Send via socket
        this.socket.emit('private_message', messageData);
    }

    sendGroupMessage(message) {
        const messageData = {
            group_id: this.currentGroup,
            message: message,
            type: 'text'
        };

        // Display message immediately
        const tempMessage = {
            id: 'temp-' + Date.now(),
            group_id: this.currentGroup,
            sender_id: currentUserId,
            sender_name: currentUserName,
            content: message,
            timestamp: new Date().toISOString(),
            type: 'text'
        };

        this.displayMessage(tempMessage, 'sent');
        this.scrollToBottom();

        // Send via socket
        this.socket.emit('group_message', messageData);
    }

    displayMessage(data, type) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageElement = this.createMessageElement(data, type);
        messagesContainer.appendChild(messageElement);
    }

    createMessageElement(data, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.dataset.messageId = data.id;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (data.type === 'text') {
            contentDiv.textContent = data.content;
        } else {
            contentDiv.appendChild(this.createMediaElement(data));
        }

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = this.formatTime(data.timestamp);

        bubbleDiv.appendChild(contentDiv);
        bubbleDiv.appendChild(timeDiv);
        messageDiv.appendChild(bubbleDiv);

        return messageDiv;
    }

    createMediaElement(data) {
        // Implementation for different media types
        // This would handle images, videos, audio, documents
        // Simplified for this example
        const container = document.createElement('div');
        container.className = `media-message ${data.type}-message`;
        
        switch(data.type) {
            case 'image':
                const img = document.createElement('img');
                img.src = data.content;
                img.alt = 'Image message';
                container.appendChild(img);
                break;
            case 'video':
                const video = document.createElement('video');
                video.src = data.content;
                video.controls = true;
                container.appendChild(video);
                break;
            case 'audio':
                const audio = document.createElement('audio');
                audio.src = data.content;
                audio.controls = true;
                container.appendChild(audio);
                break;
            case 'document':
                const link = document.createElement('a');
                link.href = data.content;
                link.target = '_blank';
                link.className = 'document-message';
                link.innerHTML = `
                    <div class="document-icon">📎</div>
                    <div class="document-info">
                        <div class="document-name">Document</div>
                        <div class="document-size">Click to download</div>
                    </div>
                `;
                container.appendChild(link);
                break;
        }
        
        return container;
    }

    handleTyping() {
        if (this.typingTimer) {
            clearTimeout(this.typingTimer);
        }

        if (this.currentChat) {
            this.socket.emit('typing', {
                receiver_id: this.currentChat,
                typing: true
            });
        } else if (this.currentGroup) {
            this.socket.emit('typing', {
                group_id: this.currentGroup,
                typing: true
            });
        }

        this.typingTimer = setTimeout(() => {
            this.stopTyping();
        }, 1000);
    }

    stopTyping() {
        if (this.currentChat) {
            this.socket.emit('typing', {
                receiver_id: this.currentChat,
                typing: false
            });
        } else if (this.currentGroup) {
            this.socket.emit('typing', {
                group_id: this.currentGroup,
                typing: false
            });
        }
    }

    showTypingIndicator(data) {
        const messagesContainer = document.getElementById('chatMessages');
        let typingIndicator = messagesContainer.querySelector('.typing-indicator');

        if (data.typing) {
            if (!typingIndicator) {
                typingIndicator = document.createElement('div');
                typingIndicator.className = 'typing-indicator';
                typingIndicator.innerHTML = `
                    <div>${data.user_name} is typing</div>
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                `;
                messagesContainer.appendChild(typingIndicator);
            }
        } else {
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }
        
        this.scrollToBottom();
    }

    updateMessageTimestamp(messageId, timestamp) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            const timeElement = messageElement.querySelector('.message-time');
            if (timeElement) {
                timeElement.textContent = this.formatTime(timestamp);
            }
            
            // Remove temporary indicator
            if (messageId.startsWith('temp-')) {
                messageElement.dataset.messageId = messageId.replace('temp-', '');
            }
        }
    }

    updateUserStatus(userId, status) {
        const statusElement = document.querySelector(`[data-user-id="${userId}"] .online-status`);
        if (statusElement) {
            statusElement.style.background = status === 'online' ? '#25D366' : '#888888';
        }
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Create form data for file upload
        const formData = new FormData();
        formData.append('file', file);

        // Determine file type
        let fileType = 'document';
        if (file.type.startsWith('image/')) fileType = 'image';
        else if (file.type.startsWith('video/')) fileType = 'video';
        else if (file.type.startsWith('audio/')) fileType = 'audio';

        // Upload file and send message
        this.uploadFile(formData, fileType);
    }

    uploadFile(formData, fileType) {
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (this.currentChat) {
                    this.sendPrivateMessage(data.file_url, fileType);
                } else if (this.currentGroup) {
                    this.sendGroupMessage(data.file_url, fileType);
                }
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
        });
    }

    clearMessages() {
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) {
            messagesContainer.innerHTML = '';
        }
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('fa-IR', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// Initialize chat app when page loads
document.addEventListener('DOMContentLoaded', function() {
    window.chatApp = new ChatApp();
    
    // Set global variables from data attributes
    const body = document.body;
    window.currentUserId = body.dataset.userId;
    window.currentUserName = body.dataset.userName;
});