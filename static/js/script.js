// Global utility functions for Mailgram

// Initialize tooltips and interactive elements
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Auto-resize textareas
    const autoResizeTextareas = document.querySelectorAll('textarea[data-auto-resize]');
    autoResizeTextareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });

    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    });

    // Initialize file upload previews
    initializeFileUploads();
}

function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            showInputError(input, 'این فیلد اجباری است');
            isValid = false;
        } else {
            clearInputError(input);
        }
    });

    return isValid;
}

function showInputError(input, message) {
    clearInputError(input);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'input-error';
    errorDiv.textContent = message;
    errorDiv.style.color = '#dc3545';
    errorDiv.style.fontSize = '0.8rem';
    errorDiv.style.marginTop = '0.25rem';
    
    input.style.borderColor = '#dc3545';
    input.parentNode.appendChild(errorDiv);
}

function clearInputError(input) {
    const existingError = input.parentNode.querySelector('.input-error');
    if (existingError) {
        existingError.remove();
    }
    input.style.borderColor = '';
}

function initializeFileUploads() {
    const fileInputs = document.querySelectorAll('input[type="file"][data-preview]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const files = e.target.files;
            const previewContainer = document.getElementById(this.getAttribute('data-preview'));
            
            if (previewContainer) {
                previewContainer.innerHTML = '';
                
                Array.from(files).forEach(file => {
                    const fileElement = createFilePreview(file);
                    previewContainer.appendChild(fileElement);
                });
            }
        });
    });
}

function createFilePreview(file) {
    const div = document.createElement('div');
    div.className = 'file-preview';
    div.innerHTML = `
        <span class="file-name">${file.name}</span>
        <span class="file-size">(${formatFileSize(file.size)})</span>
        <button type="button" class="remove-file" onclick="this.parentElement.remove()">×</button>
    `;
    return div;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Notification system
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">${message}</div>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        background: type === 'success' ? '#d4edda' : 
                   type === 'error' ? '#f8d7da' : 
                   type === 'warning' ? '#fff3cd' : '#d1ecf1',
        color: type === 'success' ? '#155724' : 
              type === 'error' ? '#721c24' : 
              type === 'warning' ? '#856404' : '#0c5460',
        padding: '1rem 2rem',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        zIndex: '10000',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        minWidth: '300px',
        maxWidth: '500px'
    });
    
    document.body.appendChild(notification);
    
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, duration);
    }
}

// AJAX helper functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'خطا در ارتباط با سرور');
        }
        
        return data;
    } catch (error) {
        showNotification(error.message, 'error');
        throw error;
    }
}

// User status management
function updateUserStatus(userId, status) {
    const statusElement = document.querySelector(`[data-user-id="${userId}"] .online-status`);
    if (statusElement) {
        statusElement.style.backgroundColor = status === 'online' ? '#25D366' : '#888888';
    }
}

// Search functionality
function initializeSearch() {
    const searchInputs = document.querySelectorAll('[data-search]');
    
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const container = document.querySelector(this.getAttribute('data-search-target'));
            const items = container.querySelectorAll('[data-search-item]');
            
            items.forEach(item => {
                const text = item.getAttribute('data-search-text') || item.textContent;
                if (text.toLowerCase().includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        }, 300));
    });
}

// Utility function for debouncing
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Mobile menu toggle
function initializeMobileMenu() {
    const menuToggle = document.querySelector('[data-menu-toggle]');
    const menu = document.querySelector('[data-menu]');
    
    if (menuToggle && menu) {
        menuToggle.addEventListener('click', function() {
            menu.classList.toggle('active');
        });
    }
}

// Export for global use
window.Mailgram = {
    showNotification,
    apiCall,
    updateUserStatus,
    debounce
};