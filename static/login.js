// API Base URL - Same origin (no CORS issues)
const API_BASE = window.location.origin;

// Authentication Management
class AuthManager {
    constructor() {
        this.TOKEN_KEY = 'spectrum_access_token';
        this.USER_KEY = 'spectrum_current_user';
        this.TOKEN_EXPIRY_KEY = 'spectrum_token_expiry';
    }

    setAuth(token, user, expiresInMinutes = 1440) {
        const expiryTime = new Date().getTime() + (expiresInMinutes * 60 * 1000);
        
        sessionStorage.setItem(this.TOKEN_KEY, token);
        sessionStorage.setItem(this.USER_KEY, JSON.stringify(user));
        sessionStorage.setItem(this.TOKEN_EXPIRY_KEY, expiryTime.toString());
        
        console.log('✅ Authentication data stored');
        return { token, user };
    }

    getAuth() {
        const token = sessionStorage.getItem(this.TOKEN_KEY);
        const userStr = sessionStorage.getItem(this.USER_KEY);
        const expiryStr = sessionStorage.getItem(this.TOKEN_EXPIRY_KEY);

        if (!token || !userStr || !expiryStr) {
            return null;
        }

        const expiryTime = parseInt(expiryStr);
        if (new Date().getTime() > expiryTime) {
            console.log('🕰️ Token expired, clearing auth data');
            this.clearAuth();
            return null;
        }

        try {
            const user = JSON.parse(userStr);
            return { token, user };
        } catch (error) {
            console.error('Error parsing stored user data:', error);
            this.clearAuth();
            return null;
        }
    }

    clearAuth() {
        sessionStorage.removeItem(this.TOKEN_KEY);
        sessionStorage.removeItem(this.USER_KEY);
        sessionStorage.removeItem(this.TOKEN_EXPIRY_KEY);
        console.log('🗑️ Authentication data cleared');
    }

    isAuthenticated() {
        return this.getAuth() !== null;
    }
}

const authManager = new AuthManager();

// Check server status
async function checkServerStatus() {
    const statusDiv = document.getElementById('server-status');
    const statusText = document.getElementById('status-text');
    
    statusDiv.style.display = 'block';
    statusText.textContent = 'Checking server connection...';
    
    try {
        const response = await fetch(`${API_BASE}/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000) // 5 second timeout
        });
        
        if (response.ok) {
            const health = await response.json();
            statusText.textContent = `✅ Server connected - ${health.status}`;
            statusDiv.style.background = '#e8f5e8';
            statusDiv.style.borderColor = '#81c784';
            statusDiv.style.color = '#2e7d32';
            return true;
        } else {
            throw new Error(`Server responded with status ${response.status}`);
        }
    } catch (error) {
        console.error('Server health check failed:', error);
        statusText.textContent = '❌ Cannot connect to server. Please ensure the backend is running.';
        statusDiv.style.background = '#ffebee';
        statusDiv.style.borderColor = '#ef5350';
        statusDiv.style.color = '#c62828';
        return false;
    }
}

// Check if user is already logged in
window.addEventListener('load', async function() {
    console.log('🔍 Checking login status...');
    
    // First check server status
    const serverOnline = await checkServerStatus();
    
    if (!serverOnline) {
        return; // Stay on login page if server is offline
    }
    
    // Check if already authenticated
    const storedAuth = authManager.getAuth();
    if (storedAuth) {
        console.log('🔑 Found stored authentication, verifying...');
        
        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${storedAuth.token}`
                }
            });
            
            if (response.ok) {
                console.log('✅ Already authenticated, redirecting...');
                showAlert('Welcome back! Redirecting to dashboard...', 'success');
                setTimeout(() => {
                    window.location.href = '/static/index.html';
                }, 1000);
                return;
            } else {
                console.log('🔄 Stored token invalid, clearing...');
                authManager.clearAuth();
            }
        } catch (error) {
            console.log('❌ Error verifying stored token:', error);
            authManager.clearAuth();
        }
    }
    
    console.log('Ready for login');
    
    // Hide server status after successful check
    setTimeout(() => {
        document.getElementById('server-status').style.display = 'none';
    }, 2000);
});

// Handle login form submission
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            const rememberMe = document.getElementById('rememberMe').checked;
            const loginBtn = document.getElementById('loginBtn');
            const loading = document.getElementById('loading');
            
            // Validation
            if (!username || !password) {
                showAlert('Please enter both username and password', 'error');
                return;
            }
            
            // Show loading state
            setLoadingState(true, loginBtn, loading);
            clearAlerts();
            
            console.log('🔐 Attempting login for user:', username);
            
            try {
                const response = await fetch(`${API_BASE}/auth/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        username: username,
                        password: password
                    })
                });
                
                console.log('📡 Login response status:', response.status);
                const result = await response.json();
                console.log('📡 Login response data:', result);
                
                if (result.success && result.access_token) {
                    console.log('✅ Login successful');
                    
                    // Store authentication data
                    const expiryMinutes = rememberMe ? 10080 : 1440; // 7 days vs 24 hours
                    authManager.setAuth(result.access_token, result.user, expiryMinutes);
                    
                    showAlert('✅ Login successful! Welcome to Spectrum Mental Health', 'success');
                    
                    // Redirect after short delay
                    setTimeout(() => {
                        console.log('🔄 Redirecting to dashboard...');
                        window.location.href = '/static/index.html';
                    }, 1500);
                    
                } else {
                    console.log('❌ Login failed:', result.message);
                    showAlert(result.message || 'Invalid username or password. Please try again.', 'error');
                    setLoadingState(false, loginBtn, loading);
                    
                    // Clear password field on failed login
                    document.getElementById('password').value = '';
                    document.getElementById('password').focus();
                }
                
            } catch (error) {
                console.error('🚨 Login error:', error);
                showAlert('Connection error. Please check your internet connection and try again.', 'error');
                setLoadingState(false, loginBtn, loading);
            }
        });
    }
});

// Set loading state
function setLoadingState(isLoading, loginBtn, loading) {
    if (isLoading) {
        loginBtn.disabled = true;
        loginBtn.textContent = 'Signing In...';
        loading.style.display = 'block';
    } else {
        loginBtn.disabled = false;
        loginBtn.textContent = 'Sign In';
        loading.style.display = 'none';
    }
}

// Toggle password visibility
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const toggleBtn = document.querySelector('.password-toggle');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleBtn.textContent = '🙈';
    } else {
        passwordInput.type = 'password';
        toggleBtn.textContent = '👁️';
    }
}

// Show alert messages
function showAlert(message, type) {
    const alertContainer = document.getElementById('alert-container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertDiv);
    
    // Auto-hide success messages
    if (type === 'success') {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }
}

// Clear all alerts
function clearAlerts() {
    document.getElementById('alert-container').innerHTML = '';
}

// Handle forgot password
function showForgotPassword() {
    showAlert('Password reset: Please contact your system administrator', 'error');
}

// Fill demo credentials on double-click
document.addEventListener('DOMContentLoaded', function() {
    const demoCredentials = document.querySelector('.demo-credentials');
    if (demoCredentials) {
        demoCredentials.addEventListener('dblclick', function() {
            document.getElementById('username').value = 'admin';
            document.getElementById('password').value = 'SpectrumAdmin2024!';
            showAlert('Demo credentials filled in - click Sign In', 'success');
            document.getElementById('loginBtn').focus();
        });
    }
});

// Enhanced keyboard support
document.addEventListener('keydown', function(e) {
    // Enter key submits form
    if (e.key === 'Enter' && !e.shiftKey) {
        const activeElement = document.activeElement;
        if (activeElement && (activeElement.id === 'username' || activeElement.id === 'password')) {
            e.preventDefault();
            const loginForm = document.getElementById('loginForm');
            if (loginForm) {
                loginForm.dispatchEvent(new Event('submit'));
            }
        }
    }
    
    // Escape key clears alerts
    if (e.key === 'Escape') {
        clearAlerts();
    }
});

// Clear alerts when user starts typing
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', function() {
            clearAlerts();
        });
    });
});

// Prevent form submission with empty fields
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input[required]').forEach(input => {
        input.addEventListener('invalid', function(e) {
            e.preventDefault();
            showAlert('Please fill in all required fields', 'error');
        });
    });
});

// Auto-focus username field
window.addEventListener('load', function() {
    setTimeout(() => {
        const usernameField = document.getElementById('username');
        if (usernameField) {
            usernameField.focus();
        }
    }, 500);
});