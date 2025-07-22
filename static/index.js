// API Base URL
        const API_BASE = window.location.origin;
        let allPatients = [];
        let allUsers = [];
        let currentUser = null;
        let accessToken = null;

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
                
                accessToken = token;
                currentUser = user;
                
                console.log('✅ Authentication data stored');
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
                    accessToken = token;
                    currentUser = user;
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
                accessToken = null;
                currentUser = null;
                console.log('🗑️ Authentication data cleared');
            }

            isAuthenticated() {
                return this.getAuth() !== null;
            }
        }

        const authManager = new AuthManager();

        // Authentication check
        async function checkAuthentication() {
            console.log('🔐 Checking authentication status...');
            
            const storedAuth = authManager.getAuth();
            if (!storedAuth) {
                console.log('❌ No valid stored authentication');
                return false;
            }

            console.log('🔑 Found stored authentication, verifying with server...');

            try {
                const response = await fetch(`${API_BASE}/auth/me`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${storedAuth.token}`
                    }
                });
                
                console.log('📡 Auth verification response status:', response.status);
                
                if (response.ok) {
                    const user = await response.json();
                    currentUser = user;
                    console.log('✅ Authentication verified:', user);
                    return true;
                } else {
                    console.log('❌ Authentication verification failed');
                    authManager.clearAuth();
                    return false;
                }
            } catch (error) {
                console.error('🚨 Authentication check error:', error);
                return false;
            }
        }

        // Helper function to make authenticated requests
        async function authenticatedFetch(url, options = {}) {
            if (!accessToken) {
                console.log('❌ No access token for request');
                window.location.href = '/static/login.html';
                return null;
            }

            // Make sure we don't lose headers when merging options
            const mergedOptions = {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                    ...(options.headers || {})
                }
            };
            
            // Debug logging
            console.log(`🔄 API Request: ${options.method || 'GET'} ${url}`);
            if (options.body) {
                console.log(`📦 Request Body: ${options.body}`);
            }
            
            const response = await fetch(url, mergedOptions);
            
            if (response.status === 401) {
                console.log('❌ Token expired or invalid, redirecting to login');
                authManager.clearAuth();
                window.location.href = '/static/login.html';
                return null;
            }
            
            return response;
        }

        // Display user information
        function displayUserInfo() {
            const userInfoDiv = document.getElementById('userInfo');
            if (currentUser) {
                userInfoDiv.innerHTML = `
                    <span>Welcome, <strong>${currentUser.full_name}</strong> | 🔒 Secure Session</span>
                `;
                // Hide Manage Users nav and section for non-admins
                const manageUsersBtn = Array.from(document.getElementsByClassName('nav-btn')).find(btn => btn.textContent.trim() === 'Manage Users');
                const userManagementSection = document.getElementById('user-management');
                const financialTabBtn = Array.from(document.getElementsByClassName('nav-btn')).find(btn => btn.textContent.trim() === 'Financial Tracking');
                const financialSection = document.getElementById('financial-tracking');
                if (currentUser.role !== 'admin') {
                    if (manageUsersBtn) manageUsersBtn.style.display = 'none';
                    if (userManagementSection) userManagementSection.style.display = 'none';
                    if (financialTabBtn) financialTabBtn.style.display = 'none';
                    if (financialSection) financialSection.style.display = 'none';
                } else {
                    if (manageUsersBtn) manageUsersBtn.style.display = '';
                    if (userManagementSection) userManagementSection.style.display = '';
                    if (financialTabBtn) financialTabBtn.style.display = '';
                    if (financialSection) financialSection.style.display = '';
                }
            }
        }

        // Logout function
        async function logout() {
            if (confirm('Are you sure you want to logout?')) {
                try {
                    console.log('🚪 Logging out...');
                    
                    if (accessToken) {
                        await fetch(`${API_BASE}/auth/logout`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Authorization': `Bearer ${accessToken}`
                            }
                        });
                    }
                    
                    authManager.clearAuth();
                    console.log('✅ Logout completed, redirecting to login');
                    window.location.href = '/static/login.html';
                } catch (error) {
                    console.error('Logout error:', error);
                    authManager.clearAuth();
                    window.location.href = '/static/login.html';
                }
            }
        }

        // Check authentication on page load
        window.addEventListener('load', async function() {
            console.log('🔍 Starting application...');
            
            const isAuthenticated = await checkAuthentication();
            
            if (isAuthenticated && currentUser) {
                console.log('✅ User authenticated, loading application');
                displayUserInfo();
                setTimeout(() => {
                    loadPatients();
                    loadUsers();
                }, 500);
            } else {
                console.log('❌ User not authenticated, redirecting to login');
                setTimeout(() => {
                    window.location.href = '/static/login.html';
                }, 1000);
            }
        });

        // Navigation
        function showSection(sectionId, event) {
            // Hide all sections
            document.querySelectorAll('.section').forEach(section => {
                section.classList.remove('active');
            });
            // Remove active class from all nav buttons
            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            // Show selected section
            document.getElementById(sectionId).classList.add('active');
            // Add active class to clicked button if event is provided
            if (event && event.target) {
                event.target.classList.add('active');
            } else {
                // If no event, set active class based on sectionId
                const btns = document.querySelectorAll('.nav-btn');
                btns.forEach(btn => {
                    if (btn.textContent.trim().toLowerCase() ===
                        (sectionId.replace('-section', '').replace('-', ' ') === 'add patient' ? 'add patient' :
                        sectionId.replace('-section', '').replace('-', ' ')).toLowerCase()) {
                        btn.classList.add('active');
                    }
                });
            }
            // Load data if needed
            if (sectionId === 'patient-log') {
                loadPatients();
            } else if (sectionId === 'user-management') {
                loadUsers();
            } else if (sectionId === 'calendar-section') {
                // Refresh the calendar to show updated appointments
                renderCalendar();
            }
        }

        // USER MANAGEMENT FUNCTIONS

        // Load Users
        async function loadUsers() {
            document.getElementById('userLoading').style.display = 'block';
            
            try {
                const response = await authenticatedFetch(`${API_BASE}/users/`);
                if (response && response.ok) {
                    allUsers = await response.json();
                    displayUsers(allUsers);
                    console.log(`✅ Loaded ${allUsers.length} users`);
                } else {
                    document.getElementById('usersContainer').innerHTML = '<p>Error loading users</p>';
                }
            } catch (error) {
                console.error('Error loading users:', error);
                document.getElementById('usersContainer').innerHTML = '<p>Error connecting to server</p>';
            }
            
            document.getElementById('userLoading').style.display = 'none';
        }

        // Display Users
        function displayUsers(users) {
            const container = document.getElementById('usersContainer');
            
            if (users.length === 0) {
                container.innerHTML = '<p>No users found</p>';
                return;
            }
            
            container.innerHTML = users.map(user => `
                <div class="user-card ${user.is_active ? '' : 'inactive'}">
                    <span class="status-badge ${user.is_active ? 'active' : 'inactive'}">
                        ${user.is_active ? 'Active' : 'Disabled'}
                    </span>
                    <div class="user-name">${user.full_name}</div>
                    <div class="user-details">
                        <strong>Username:</strong> ${user.username}<br>
                        <strong>Email:</strong> ${user.email}<br>
                        <strong>Role:</strong> ${user.role}<br>
                        <strong>Created:</strong> ${new Date(user.created_at).toLocaleDateString()}<br>
                        <strong>Last Login:</strong> ${user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}
                    </div>
                    <div style="margin-top: 15px;">
                        ${user.id !== currentUser.id ? `
                            <button class="btn btn-small btn-warning" onclick="showResetPasswordModal(${user.id}, '${user.username}')">Reset Password</button>
                            <button class="btn btn-small ${user.is_active ? 'btn-danger' : 'btn-success'}" onclick="toggleUserStatus(${user.id})">
                                ${user.is_active ? 'Disable' : 'Enable'}
                            </button>
                            <button class="btn btn-danger btn-small" onclick="deleteUser(${user.id}, '${user.username}')">Delete</button>
                        ` : '<span style="color: #666; font-style: italic;">Current User</span>'}
                    </div>
                </div>
            `).join('');
        }

        // Search Users
        document.addEventListener('DOMContentLoaded', function() {
            const userSearchBox = document.getElementById('userSearchBox');
            if (userSearchBox) {
                userSearchBox.addEventListener('input', function(e) {
                    const query = e.target.value.toLowerCase();
                    const filteredUsers = allUsers.filter(user => 
                        user.username.toLowerCase().includes(query) ||
                        user.full_name.toLowerCase().includes(query) ||
                        user.email.toLowerCase().includes(query) ||
                        user.role.toLowerCase().includes(query)
                    );
                    displayUsers(filteredUsers);
                });
            }
        });

        // Modal functions
        function showAddUserModal() {
            document.getElementById('addUserModal').style.display = 'block';
            document.getElementById('addUserAlert').innerHTML = '';
            document.getElementById('addUserForm').reset();
        }

        function closeAddUserModal() {
            document.getElementById('addUserModal').style.display = 'none';
        }

        function showResetPasswordModal(userId, username) {
            document.getElementById('resetUserId').value = userId;
            document.getElementById('resetUserName').textContent = username;
            document.getElementById('resetPasswordModal').style.display = 'block';
            document.getElementById('resetPasswordAlert').innerHTML = '';
            document.getElementById('resetPasswordForm').reset();
        }

        function closeResetPasswordModal() {
            document.getElementById('resetPasswordModal').style.display = 'none';
        }

        // User management actions
        async function toggleUserStatus(userId) {
            try {
                const response = await authenticatedFetch(`${API_BASE}/users/${userId}/toggle-status`, {
                    method: 'POST'
                });
                
                if (response && response.ok) {
                    const result = await response.json();
                    showAlert('add-alert', result.message, 'success');
                    loadUsers();
                } else if (response) {
                    const error = await response.json();
                    showAlert('add-alert', `Error: ${error.detail}`, 'error');
                }
            } catch (error) {
                console.error('Toggle status error:', error);
                showAlert('add-alert', 'Error connecting to server.', 'error');
            }
        }

        async function deleteUser(userId, username) {
            if (confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
                try {
                    const response = await authenticatedFetch(`${API_BASE}/users/${userId}`, {
                        method: 'DELETE'
                    });
                    
                    if (response && response.ok) {
                        showAlert('add-alert', `User "${username}" deleted successfully`, 'success');
                        loadUsers();
                    } else if (response) {
                        const error = await response.json();
                        showAlert('add-alert', `Error: ${error.detail}`, 'error');
                    }
                } catch (error) {
                    console.error('Delete user error:', error);
                    showAlert('add-alert', 'Error connecting to server.', 'error');
                }
            }
        }

        // Form handlers
        document.addEventListener('DOMContentLoaded', function() {
            // Add User Form
            const addUserForm = document.getElementById('addUserForm');
            if (addUserForm) {
                addUserForm.addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    const userData = {};
                    
                    for (let [key, value] of formData.entries()) {
                        userData[key] = value;
                    }
                    
                    try {
                        const response = await authenticatedFetch(`${API_BASE}/users/`, {
                            method: 'POST',
                            body: JSON.stringify(userData)
                        });
                        
                        if (response && response.ok) {
                            const result = await response.json();
                            showAlert('addUserAlert', 'User created successfully!', 'success');
                            loadUsers();
                            setTimeout(() => {
                                closeAddUserModal();
                            }, 1500);
                        } else if (response) {
                            const error = await response.json();
                            showAlert('addUserAlert', `Error: ${error.detail}`, 'error');
                        }
                    } catch (error) {
                        console.error('User creation error:', error);
                        showAlert('addUserAlert', 'Error connecting to server.', 'error');
                    }
                });
            }

            // Reset Password Form
            const resetPasswordForm = document.getElementById('resetPasswordForm');
            if (resetPasswordForm) {
                resetPasswordForm.addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const userId = document.getElementById('resetUserId').value;
                    const newPassword = document.getElementById('resetNewPassword').value;
                    
                    if (newPassword.length < 8) {
                        showAlert('resetPasswordAlert', 'Password must be at least 8 characters long', 'error');
                        return;
                    }
                    
                    try {
                        const response = await authenticatedFetch(`${API_BASE}/users/${userId}/reset-password`, {
                            method: 'POST',
                            body: JSON.stringify({ new_password: newPassword })
                        });
                        
                        if (response && response.ok) {
                            showAlert('resetPasswordAlert', 'Password reset successfully!', 'success');
                            setTimeout(() => {
                                closeResetPasswordModal();
                            }, 1500);
                        } else if (response) {
                            const error = await response.json();
                            showAlert('resetPasswordAlert', `Error: ${error.detail}`, 'error');
                        }
                    } catch (error) {
                        console.error('Password reset error:', error);
                        showAlert('resetPasswordAlert', 'Error connecting to server.', 'error');
                    }
                });
            }
        });

        // PATIENT MANAGEMENT FUNCTIONS

        // Add Patient Form
        document.getElementById('patientForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const patientData = {};
            for (let [key, value] of formData.entries()) {
                if (value.trim() !== '') {
                    patientData[key] = value;
                }
            }
            
            // Show loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.innerHTML = 'Adding Patient...';
            submitBtn.disabled = true;
            
            try {
                const response = await authenticatedFetch(`${API_BASE}/patients/`, {
                    method: 'POST',
                    body: JSON.stringify(patientData)
                });
                
                if (response && response.ok) {
                    const result = await response.json();
                    
                    // Clear the form
                    this.reset();
                    
                    // Show success message
                    showAlert('add-alert', 'Patient added successfully!', 'success');
                    
                    // Scroll to alert
                    const alertDiv = document.getElementById('add-alert');
                    if (alertDiv) {
                        alertDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    
                    // Focus on first input
                    const firstInput = this.querySelector('input, select, textarea');
                    if (firstInput) firstInput.focus();
                    
                    // Update patient list
                    await loadPatients();
                } else if (response) {
                    const error = await response.json();
                    showAlert('add-alert', `Error: ${error.detail}`, 'error');
                    const alertDiv = document.getElementById('add-alert');
                    if (alertDiv) {
                        alertDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            } catch (error) {
                console.error('Form submission error:', error);
                showAlert('add-alert', 'Error connecting to server.', 'error');
                const alertDiv = document.getElementById('add-alert');
                if (alertDiv) {
                    alertDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            } finally {
                // Reset button state
                submitBtn.innerHTML = originalBtnText;
                submitBtn.disabled = false;
            }
        });

        // Load Patients
        async function loadPatients() {
            document.getElementById('loading').style.display = 'block';
            
            try {
                const response = await authenticatedFetch(`${API_BASE}/patients/`);
                if (response && response.ok) {
                    allPatients = await response.json();
                    displayPatients(allPatients);
                    console.log(`✅ Loaded ${allPatients.length} patients`);
                } else {
                    document.getElementById('patientsContainer').innerHTML = '<p>Error loading patients</p>';
                }
            } catch (error) {
                console.error('Error loading patients:', error);
                document.getElementById('patientsContainer').innerHTML = '<p>Error connecting to server</p>';
            }
            
            document.getElementById('loading').style.display = 'none';
        }

        // Display Patients
        function displayPatients(patients) {
            const container = document.getElementById('patientsContainer');
            
            if (patients.length === 0) {
                container.innerHTML = '<div class="no-patients">No patients found.</div>';
                return;
            }
            
            // Create table structure
            let html = `
                <table class="patients-table">
                    <thead>
                        <tr>
                            <th>Patient ID</th>
                            <th>Name</th>
                            <th>Phone Number</th>
                            <th>Info</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            patients.forEach(patient => {
                const phone = patient.phone || 'Not provided';
                html += `
                    <tr class="patient-row">
                        <td class="patient-id">${patient.patient_number}</td>
                        <td class="patient-name-cell">${patient.first_name} ${patient.last_name}</td>
                        <td class="patient-phone">${phone}</td>
                        <td class="patient-actions">
                            <button class="btn btn-primary btn-small" onclick="viewPatient(${patient.id})">
                                View
                            </button>
                        </td>
                    </tr>
                `;
            });
            
            html += `
                    </tbody>
                </table>
            `;
            
            container.innerHTML = html;
        }

        // Search Patients
        document.getElementById('searchBox').addEventListener('input', function(e) {
            const query = e.target.value.toLowerCase();
            // Use the current allPatients array (which will be updated after deletion)
            const filteredPatients = allPatients.filter(patient => 
                patient.patient_number.toLowerCase().includes(query) ||
                patient.first_name.toLowerCase().includes(query) ||
                patient.last_name.toLowerCase().includes(query) ||
                (patient.phone && patient.phone.toLowerCase().includes(query))
            );
            displayPatients(filteredPatients);
        });

        // View Patient Function
        async function viewPatient(patientId) {
            console.log('🔍 Loading patient details for ID:', patientId);
            try {
                const response = await authenticatedFetch(`${API_BASE}/patients/${patientId}`);
                console.log('📡 Patient API response:', response);
                
                if (response && response.ok) {
                    const patient = await response.json();
                    console.log('👤 Patient data loaded:', patient);
                    
                    // Fetch patient files
                    let filesHtml = '';
                    try {
                        const filesResp = await fetch(`${API_BASE}/patients/${patientId}/files`, {
                            method: 'GET',
                            headers: {
                                'Authorization': `Bearer ${accessToken}`
                            }
                        });
                        if (filesResp && filesResp.ok) {
                            const files = await filesResp.json();
                            if (files.length > 0) {
                                filesHtml = `<div style="margin-top:20px;"><strong>Uploaded Files:</strong><ul style='margin-top:10px;'>` +
                                    files.map(f => `<li><a href="#" onclick="openPatientFileInNewTab(${patientId}, '${f.id}', '${f.filename.replace(/'/g, "\\'")}'); return false;">${f.filename}</a></li>`).join('') +
                                    `</ul></div>`;
                            } else {
                                filesHtml = `<div style='margin-top:20px; color:#888;'>No files uploaded for this patient.</div>`;
                            }
                        } else {
                            filesHtml = `<div style='margin-top:20px; color:#e74c3c;'>Error loading files.</div>`;
                        }
                    } catch (e) {
                        console.error('Error loading patient files:', e);
                        filesHtml = `<div style='margin-top:20px; color:#e74c3c;'>Error loading files.</div>`;
                    }

                    // File upload form
                    const uploadFormHtml = `
                        <form id=\"patientFileUploadForm\" enctype=\"multipart/form-data\" style=\"margin-top:20px;\">
                            <label><strong>Upload File for this Patient:</strong></label><br>
                            <input type=\"file\" id=\"patientFileInput\" name=\"file\" required style=\"margin-top:8px;\" />
                            <button type=\"submit\" class=\"btn btn-small\" style=\"margin-left:10px;\">Upload</button>
                            <div id=\"patientFileUploadAlert\" style=\"margin-top:10px;\"></div>
                        </form>
                    `;

                    // Modern patient info view with organized sections
                    const modalContent = `
                        <div class="patient-view-header">
                            <div class="patient-avatar">
                                <div class="avatar-circle">
                                    ${patient.first_name.charAt(0)}${patient.last_name.charAt(0)}
                                </div>
                            </div>
                            <div class="patient-title-info">
                                <h2 class="patient-name">${patient.first_name} ${patient.last_name}</h2>
                                <p class="patient-number">ID: ${patient.patient_number}</p>
                                <p class="patient-status">Status: ${patient.end_date ? 'Inactive' : 'Active'}</p>
                            </div>
                        </div>

                        <div class="patient-info-sections">
                            <!-- Personal Information Section -->
                            <div class="info-section">
                                <h3 class="section-title">
                                    <span class="section-icon">👤</span>
                                    Personal Information
                                </h3>
                                <div class="info-grid">
                                    <div class="info-item">
                                        <label>Date of Birth</label>
                                        <span>${patient.date_of_birth ? formatDateString(patient.date_of_birth) : 'Not provided'}</span>
                                    </div>
                                    <div class="info-item">
                                        <label>Phone</label>
                                        <span>${patient.phone || 'Not provided'}</span>
                                    </div>
                                    <div class="info-item full-width">
                                        <label>Address</label>
                                        <span>${patient.address || 'Not provided'}</span>
                                    </div>
                                    <div class="info-item">
                                        <label>SSN</label>
                                        <span>${patient.ssn ? '***-**-' + patient.ssn.slice(-4) : 'Not provided'}</span>
                                    </div>
                                </div>
                            </div>

                            <!-- Insurance Information Section -->
                            <div class="info-section">
                                <h3 class="section-title">
                                    <span class="section-icon">🏥</span>
                                    Insurance & Medical
                                </h3>
                                <div class="info-grid">
                                    <div class="info-item">
                                        <label>Insurance Provider</label>
                                        <span>${patient.insurance || 'Not provided'}</span>
                                    </div>
                                    <div class="info-item">
                                        <label>Insurance ID</label>
                                        <span>${patient.insurance_id || 'Not provided'}</span>
                                    </div>
                                    <div class="info-item">
                                        <label>Medicaid ID</label>
                                        <span>${patient.medicaid_id || 'Not provided'}</span>
                                    </div>
                                    <div class="info-item">
                                        <label>PSR Date</label>
                                        <span>${patient.psr_date ? formatDateString(patient.psr_date) : 'Not provided'}</span>
                                    </div>
                                    <div class="info-item full-width">
                                        <label>Authorization</label>
                                        <span>${patient.authorization || 'Not provided'}</span>
                                    </div>
                                    <div class="info-item full-width">
                                        <label>Diagnosis</label>
                                        <span>${patient.diagnosis || 'Not provided'}</span>
                                    </div>
                                    <div class="info-item">
                                        <label>Referral</label>
                                        <span>${patient.referal || 'Not provided'}</span>
                                    </div>
                                </div>
                            </div>

                            <!-- Authorization Details Section -->
                            <div class="info-section">
                                <h3 class="section-title">
                                    <span class="section-icon">🔒</span>
                                    Authorization Details
                                    <button class="btn btn-small add-auth-btn" onclick="showAddAuthorizationModal(${patient.id})" style="float:right;margin-top:-5px;">
                                        <span class="btn-icon">+</span> Add New
                                    </button>
                                </h3>
                                <div id="authorizationsContainer">
                                    <p>Loading authorizations...</p>
                                </div>
                            </div>

                            <!-- Treatment Information Section -->
                            <div class="info-section">
                                <h3 class="section-title">
                                    <span class="section-icon">📋</span>
                                    Treatment Information
                                </h3>
                                <div class="info-grid">
                                    <div class="info-item">
                                        <label>Start Date</label>
                                        <span>${patient.start_date ? formatDateString(patient.start_date) : 'Not provided'}</span>
                                    </div>
                                    <div class="info-item">
                                        <label>End Date</label>
                                        <span class="${patient.end_date ? 'status-inactive' : 'status-active'}">
                                            ${patient.end_date ? formatDateString(patient.end_date) : 'Ongoing'}
                                        </span>
                                    </div>
                                    <div class="codes-grid">
                                        <div class="code-item">
                                            <label>Code 1</label>
                                            <span class="code-value">${patient.code1 || 'N/A'}</span>
                                        </div>
                                        <div class="code-item">
                                            <label>Code 2</label>
                                            <span class="code-value">${patient.code2 || 'N/A'}</span>
                                        </div>
                                        <div class="code-item">
                                            <label>Code 3</label>
                                            <span class="code-value">${patient.code3 || 'N/A'}</span>
                                        </div>
                                        <div class="code-item">
                                            <label>Code 4</label>
                                            <span class="code-value">${patient.code4 || 'N/A'}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Notes Section -->
                            <div class="info-section">
                                <h3 class="section-title">
                                    <span class="section-icon">📝</span>
                                    Notes
                                </h3>
                                <div class="notes-section">
                                    <textarea 
                                        id="patientNotes" 
                                        class="notes-textarea" 
                                        rows="4" 
                                        placeholder="Enter notes about this patient..."
                                    >${patient.notes || ''}</textarea>
                                    <button class="btn btn-primary btn-small" id="saveNotesBtn" onclick="savePatientNotes(${patient.id})">
                                        Save Notes
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Action Buttons Section -->
                        <div class="patient-actions">
                            <div class="action-buttons">
                                <button class="btn btn-secondary" onclick="editPatient(${patient.id})">
                                    <span class="btn-icon">✏️</span> Edit Patient
                                </button>
                                <button class="btn btn-danger" onclick="deletePatient(${patient.id})" style="margin-left: 10px;">
                                    <span class="btn-icon">🗑️</span> Delete Patient
                                </button>
                                <button class="btn btn-info attendance-sheet-btn">
                                    <span class="btn-icon">📊</span> Attendance Sheet
                                </button>
                                <button class="btn btn-info appointment-sheet-btn">
                                    <span class="btn-icon">📅</span> Appointment Sheet
                                </button>
                            </div>
                        </div>

                        <!-- File Upload Section -->
                        ${uploadFormHtml}
                        ${filesHtml}
                    `;

                    showModal('Patient Details', modalContent);

                    // Use setTimeout to ensure modal content is rendered before attaching listeners
                    setTimeout(() => {
                        // Load patient authorizations
                        loadPatientAuthorizations(patientId);

                        // Attach event listeners for Attendance/Appointment Sheet buttons
                        const attendanceBtn = document.querySelector('.attendance-sheet-btn');
                        const appointmentBtn = document.querySelector('.appointment-sheet-btn');
                        
                        if (attendanceBtn) {
                            attendanceBtn.addEventListener('click', function() {
                                showSheetModal(patient.id, 'attendance');
                            });
                        }
                        
                        if (appointmentBtn) {
                            appointmentBtn.addEventListener('click', function() {
                                showSheetModal(patient.id, 'appointment');
                            });
                        }

                        // Attach file upload handler
                        const uploadForm = document.getElementById('patientFileUploadForm');
                        if (uploadForm) {
                            uploadForm.addEventListener('submit', async function(e) {
                                e.preventDefault();
                                const fileInput = document.getElementById('patientFileInput');
                                const alertDiv = document.getElementById('patientFileUploadAlert');
                                if (!fileInput.files.length) {
                                    alertDiv.innerHTML = '<span style="color:red;">Please select a file.</span>';
                                    return;
                                }
                                const formData = new FormData();
                                formData.append('file', fileInput.files[0]);
                                try {
                                    const resp = await fetch(`${API_BASE}/patients/${patient.id}/files`, {
                                        method: 'POST',
                                        headers: { 'Authorization': `Bearer ${accessToken}` },
                                        body: formData
                                    });
                                    if (resp.ok) {
                                        alertDiv.innerHTML = '<span style="color:green;">File uploaded!</span>';
                                        setTimeout(() => viewPatient(patient.id), 1000);
                                    } else {
                                        alertDiv.innerHTML = '<span style="color:red;">Upload failed.</span>';
                                    }
                                } catch (err) {
                                    alertDiv.innerHTML = '<span style="color:red;">Error uploading file.</span>';
                                }
                            });
                        }
                    }, 100); // Small delay to ensure DOM is ready
                } else {
                    console.error('❌ Failed to load patient data:', response ? response.status : 'No response');
                    showModal('Error', `Failed to load patient details. Status: ${response ? response.status : 'No response'}`);
                }
            } catch (error) {
                console.error('❌ Error in viewPatient:', error);
                showModal('Error', `Failed to load patient details: ${error.message}`);
            }
        }

        // Function to show services for a specific date (appointments only)
        async function showServicesByDate(dateString) {
            try {
                // Fetch all patients
                const patientsResponse = await authenticatedFetch(`${API_BASE}/patients/`);
                if (!patientsResponse.ok) {
                    showAlert('Failed to load patients', 'danger');
                    return;
                }
                
                const patients = await patientsResponse.json();
                let servicesForDate = [];
                
                // Fetch appointment services for each patient on this date
                const fetchPromises = patients.map(async patient => {
                    try {
                        const servicesResp = await authenticatedFetch(`${API_BASE}/patients/${patient.id}/services?service_category=appointment`);
                        if (servicesResp.ok) {
                            const services = await servicesResp.json();
                            
                            // Filter services for the specific date
                            const dateServices = services.filter(service => service.service_date === dateString);
                            dateServices.forEach(service => {
                                servicesForDate.push({
                                    ...service,
                                    patient_name: `${patient.first_name} ${patient.last_name}`,
                                    patient_number: patient.patient_number
                                });
                            });
                        }
                    } catch (err) {
                        console.error(`Error fetching services for patient ${patient.id}:`, err);
                    }
                });
                
                await Promise.all(fetchPromises);
                
                // Sort services by time
                servicesForDate.sort((a, b) => {
                    if (a.service_time && b.service_time) {
                        return a.service_time.localeCompare(b.service_time);
                    }
                    return 0;
                });
                
                // Create modal content
                let modalContent = `
                    <div class="modal-header">
                        <h3>Appointments for ${formatDateString(dateString)}</h3>
                    </div>
                    <div class="modal-body">
                `;
                
                if (servicesForDate.length === 0) {
                    modalContent += '<p>No appointments scheduled for this date.</p>';
                } else {
                    modalContent += '<div class="services-list">';
                    servicesForDate.forEach(service => {
                        // Always use the formatted time for display in the calendar modal
                        // Strictly use only the formatted time for display; never fallback to military time
                        const timeDisplay = service.service_time_formatted ? service.service_time_formatted : 'No time specified';
                        const attendedStatus = service.attended === true ? 'Attended' : 
                                             service.attended === false ? 'No-show' : 'Scheduled';
                        const statusClass = service.attended === true ? 'status-attended' : 
                                          service.attended === false ? 'status-no-show' : 'status-scheduled';
                        
                        modalContent += `
                            <div class="service-entry">
                                <div class="service-time">${timeDisplay}</div>
                                <div class="service-details">
                                    <strong>${service.patient_name} (${service.patient_number})</strong><br>
                                    <span class="service-type">${service.service_type}</span><br>
                                    <span class="service-status ${statusClass}">${attendedStatus}</span>
                                </div>
                            </div>
                        `;
                    });
                    modalContent += '</div>';
                }
                
                modalContent += '</div>';
                
                // Show modal
                showModal('Day Appointments', modalContent);
                
            } catch (error) {
                console.error('Error fetching services for date:', error);
                showAlert('Error loading appointments for this date', 'danger');
            }
        }

        // Helper to format 24-hour time ("HH:MM") to 12-hour AM/PM ("h:mm AM/PM")
        function formatTime12hr(timeStr) {
            if (!timeStr) return '';
            console.log("Formatting time:", timeStr);
            const [hourStr, minute] = timeStr.split(":");
            let hour = parseInt(hourStr, 10);
            const ampm = hour >= 12 ? "PM" : "AM";
            hour = hour % 12;
            if (hour === 0) hour = 12;
            const formatted = `${hour}:${minute} ${ampm}`;
            console.log("Formatted time:", formatted);
            return formatted;
        }

        // Show Sheet Modal (Attendance/Appointment)
        async function showSheetModal(patientId, sheetType) {
            try {
                // Close the main modal first to avoid stacking
                document.getElementById('mainModal').style.display = 'none';
                
                const resp = await authenticatedFetch(`${API_BASE}/patients/${patientId}/services?sheet_type=${sheetType}`);
                let entriesHtml = '';
                if (resp && resp.ok) {
                    const entries = await resp.json();
                    console.log("Sheet entries:", entries); // Debug log to check entries
                    if (entries.length > 0) {
                        entriesHtml = `<table class='service-table' style='width:100%;margin-top:10px;border-collapse:collapse;'>
                            <thead>
                                <tr>
                                    <th style="width:25%;padding:8px;text-align:left;border-bottom:1px solid #ddd;">Date</th>
                                    <th style="width:25%;padding:8px;text-align:left;border-bottom:1px solid #ddd;">Time</th>
                                    <th style="width:25%;padding:8px;text-align:left;border-bottom:1px solid #ddd;">Type</th>
                                    <th style="width:25%;padding:8px;text-align:left;border-bottom:1px solid #ddd;">Attendance</th>
                                </tr>
                            </thead>
                            <tbody>` +
                            entries.map(s => `<tr ${s.is_recurring || s.parent_service_id ? 'class="recurring-row"' : ''}>
                                <td style="padding:8px;text-align:left;border-bottom:1px solid #eee;">
                                    ${s.service_date ? formatDateString(s.service_date) : ''}
                                    ${s.is_recurring ? '<span title="Series parent" style="margin-left:5px;color:#5555AA;font-weight:bold;">⟳</span>' : ''}
                                    ${s.parent_service_id ? '<span title="Part of recurring series" style="margin-left:5px;color:#5555AA;">⟳</span>' : ''}
                                </td>
                                <td style="padding:8px;text-align:left;border-bottom:1px solid #eee;">${s.service_time_formatted || 'N/A'}</td>
                                <td style="padding:8px;text-align:left;border-bottom:1px solid #eee;">${s.service_type || ''}</td>
                                <td style="padding:8px;text-align:left;border-bottom:1px solid #eee;">
                                    <select 
                                        class="attendance-select" 
                                        data-service-id="${s.id}" 
                                        style="padding:4px; border-radius:4px; border: 1px solid #ccc;"
                                        onchange="updateAttendance(${s.id}, this.value)">
                                        <option value="">Not Marked</option>
                                        <option value="true" ${s.attended === true ? 'selected' : ''}>Attended</option>
                                        <option value="false" ${s.attended === false ? 'selected' : ''}>No Show</option>
                                    </select>
                                </td>
                            </tr>`).join('') +
                            `</tbody></table>`;
                    } else {
                        entriesHtml = `<div style='color:#888;'>No ${sheetType} entries for this patient.</div>`;
                    }
                } else {
                    entriesHtml = `<div style='color:#e74c3c;'>Error loading ${sheetType} entries.</div>`;
                }
                // Add a back button to return to patient view
                const backBtn = `<button class='btn btn-small' id='backToPatientBtn' style='margin-bottom:15px;'>&larr; Back to Patient</button>`;
                
                // Use the dedicated sheet modal
                const sheetModal = document.getElementById('sheetModal');
                const sheetModalTitle = document.getElementById('sheetModalTitle');
                const sheetEntriesContainer = document.getElementById('sheetEntriesContainer');
                
                sheetModalTitle.textContent = sheetType.charAt(0).toUpperCase() + sheetType.slice(1) + ' Sheet';
                sheetEntriesContainer.innerHTML = backBtn + entriesHtml;
                sheetModal.style.display = 'block';
                
                // Attach back button event
                document.getElementById('backToPatientBtn').onclick = function() {
                    closeSheetModal();
                    viewPatient(patientId); // Reopen patient modal
                };
            } catch (error) {
                showModal('Error', 'Failed to load sheet entries.');
            }
        }

        // Show Modal Utility
        function showModal(title, content) {
            const modal = document.getElementById('mainModal');
            const modalTitle = document.getElementById('mainModalTitle');
            const modalBody = document.getElementById('mainModalBody');
            modalTitle.textContent = title;
            
            // Clear previous content first
            modalBody.innerHTML = '';
            
            // Insert new content
            modalBody.innerHTML = content;
            modal.style.display = 'block';
            
            // Ensure modal has the right z-index (below alerts)
            modal.style.zIndex = '2000';
            
            // Log the modal content to ensure it's being rendered correctly
            console.log("Modal content set:", {
                title: title,
                contentLength: content.length,
                firstFormElement: modalBody.querySelector('form') ? modalBody.querySelector('form').id : 'no form found'
            });
            
            // Make sure the mainAlert container is moved to be a direct child of body
            // This ensures it's not affected by stacking contexts
            const mainAlert = document.getElementById('mainAlert');
            if (mainAlert && mainAlert.parentElement !== document.body) {
                document.body.appendChild(mainAlert);
            }
        }

        // Close Modal Utility
        document.getElementById('mainModalClose').addEventListener('click', function() {
            document.getElementById('mainModal').style.display = 'none';
        });

        // Function to close sheet modal
        function closeSheetModal() {
            document.getElementById('sheetModal').style.display = 'none';
        }
        window.closeSheetModal = closeSheetModal;

        // Utility: Open patient file in new tab (view inline)
        async function openPatientFileInNewTab(patientId, fileId, filename) {
            try {
                const storedAuth = authManager.getAuth();
                if (!storedAuth || !storedAuth.token) {
                    showAlert('mainAlert', 'You are not authenticated. Please log in again.', 'error');
                    window.location.href = '/static/login.html';
                    return;
                }
                const url = `${API_BASE}/patients/${patientId}/files/${fileId}?filename=${encodeURIComponent(filename)}`;
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${storedAuth.token}`
                    }
                });
                if (!response.ok) {
                    showAlert('mainAlert', 'Failed to open file. You may not have access.', 'error');
                    return;
                }
                const blob = await response.blob();
                const blobUrl = window.URL.createObjectURL(blob);
                window.open(blobUrl, '_blank');
                // Optionally, revoke the blob URL after some time
                setTimeout(() => {
                    window.URL.revokeObjectURL(blobUrl);
                }, 60000); // 1 minute
            } catch (err) {
                showAlert('mainAlert', 'Error opening file.', 'error');
            }
        }

        // Expose openPatientFileInNewTab globally for inline onclick
        window.openPatientFileInNewTab = openPatientFileInNewTab;

        // Expose viewPatient globally for inline onclick
        window.viewPatient = viewPatient;

        // Expose editPatient and deletePatient if needed
        // window.editPatient = editPatient;
        // window.deletePatient = deletePatient;

        // Expose logout globally
        window.logout = logout;

        // Delete Patient Function
        async function deletePatient(patientId) {
            if (!confirm('Are you sure you want to delete this patient? This action cannot be undone.')) return;
            try {
                const response = await authenticatedFetch(`${API_BASE}/patients/${patientId}`, {
                    method: 'DELETE'
                });
                if (response && response.ok) {
                    // Remove the patient from the allPatients array in memory
                    allPatients = allPatients.filter(patient => patient.id !== patientId);
                    
                    // Update the display with the filtered array
                    displayPatients(allPatients);
                    
                    showAlert('add-alert', 'Patient deleted successfully!', 'success');
                    
                    // Update the calendar if it's visible
                    if (calendarState && calendarState.currentDate) {
                        refreshCalendarView();
                    }
                } else if (response) {
                    const error = await response.json();
                    showAlert('add-alert', `Error: ${error.detail}`, 'error');
                }
            } catch (error) {
                console.error('Delete patient error:', error);
                showAlert('add-alert', 'Error connecting to server.', 'error');
            }
        }
        // Expose deletePatient globally for inline onclick
        window.deletePatient = deletePatient;

        // --- Calendar with Month Switching ---
        let calendarState = {
            year: new Date().getFullYear(),
            month: new Date().getMonth()
        };

        // Function to fetch all services for a month
        async function fetchServicesForMonth(year, month) {
            try {
                // Fetch all patients
                const response = await authenticatedFetch(`${API_BASE}/patients/`);
                if (!response.ok) {
                    console.error('Failed to load patients');
                    return {};
                }
                
                const patients = await response.json();
                let servicesByDate = {};
                
                // Fetch services for each patient (only appointment-based services for calendar)
                const fetchPromises = patients.map(async patient => {
                    try {
                        const servicesResp = await authenticatedFetch(`${API_BASE}/patients/${patient.id}/services?service_category=appointment`);
                        if (servicesResp.ok) {
                            const services = await servicesResp.json();
                            
                            // Group services by date
                            services.forEach(service => {
                                if (!servicesByDate[service.service_date]) {
                                    servicesByDate[service.service_date] = [];
                                }
                                servicesByDate[service.service_date].push(service);
                            });
                        }
                    } catch (err) {
                        console.error(`Error fetching services for patient ${patient.id}:`, err);
                    }
                });
                
                // Wait for all patient service fetches to complete
                await Promise.all(fetchPromises);
                return servicesByDate;
            } catch (err) {
                console.error('Error fetching services for month:', err);
                return {};
            }
        }

        async function renderCalendar() {
            const calendarContainer = document.getElementById('calendarContainer');
            if (!calendarContainer) return;
            const today = new Date();
            const { year, month } = calendarState;
            const monthNames = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ];
            const firstDay = new Date(year, month, 1).getDay();
            const daysInMonth = new Date(year, month + 1, 0).getDate();
            
            // Fetch services for the current month
            const servicesByDate = await fetchServicesForMonth(year, month);
            
            let html = `<div class='calendar-header'>
                <button id='prevMonthBtn' class='calendar-nav'>&lt;</button>
                <span class='calendar-month'>${monthNames[month]} ${year}</span>
                <button id='nextMonthBtn' class='calendar-nav'>&gt;</button>
            </div>`;
            html += `<table class='calendar-table'><thead><tr>`;
            ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(d => {
                html += `<th>${d}</th>`;
            });
            html += `</tr></thead><tbody><tr>`;
            for (let i = 0; i < firstDay; i++) html += '<td></td>';
            for (let day = 1; day <= daysInMonth; day++) {
                const date = new Date(year, month, day);
                const isToday = (day === today.getDate() && month === today.getMonth() && year === today.getFullYear());
                if ((firstDay + day - 1) % 7 === 0 && day !== 1) html += '</tr><tr>';
                // Make the day clickable
                const formattedDate = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                
                // Check if this date has services
                const hasServices = servicesByDate[formattedDate] && servicesByDate[formattedDate].length > 0;
                
                // Add classes for visual indicators
                let dayClasses = 'calendar-day';
                if (isToday) dayClasses += ' today';
                if (hasServices) dayClasses += ' has-services';
                
                // Also add data about services for this day to be used for hover information
                let titleText = '';
                if (hasServices) {
                    const services = servicesByDate[formattedDate];
                    const total = services.length;
                    const attended = services.filter(s => s.attended === true).length;
                    const noShow = services.filter(s => s.attended === false).length;
                    const hasRecurring = services.some(s => s.is_recurring);
                    
                    titleText = `Services: ${total}, Attended: ${attended}, No-show: ${noShow}`;
                    if (hasRecurring) {
                        titleText += " (includes recurring appointments)";
                    }
                }
                
                html += `<td class='${dayClasses}' data-date='${formattedDate}' onclick='showServicesByDate("${formattedDate}")' ${titleText ? `title="${titleText}"` : ''}>${day}</td>`;
            }
            html += '</tr></tbody></table>';
            calendarContainer.innerHTML = html;
            // Attach navigation events
            document.getElementById('prevMonthBtn').onclick = function() {
                calendarState.month--;
                if (calendarState.month < 0) {
                    calendarState.month = 11;
                    calendarState.year--;
                }
                renderCalendar();
            };
            document.getElementById('nextMonthBtn').onclick = function() {
                calendarState.month++;
                if (calendarState.month > 11) {
                    calendarState.month = 0;
                    calendarState.year++;
                }
                renderCalendar();
            };
        }

        // Show calendar section by default after login
        window.addEventListener('load', async function() {
            // ...existing code...
            const isAuthenticated = await checkAuthentication();
            if (isAuthenticated && currentUser) {
                // ...existing code...
                renderCalendar();
                showSection('calendar-section');
                // ...existing code...
            }
            // ...existing code...
        });

        // Function to refresh calendar view when appointments change
        function refreshCalendarView() {
            console.log("Refreshing calendar view");
            renderCalendar();
        }
        
        // Expose refreshCalendarView globally
        window.refreshCalendarView = refreshCalendarView;
        
        // Function to refresh calendar view when needed
        function refreshCalendarView() {
            if (calendarState && calendarState.currentDate) {
                renderCalendar();
            }
        }
        
        // Edit Patient Function
        async function editPatient(patientId) {
            try {
                const response = await authenticatedFetch(`${API_BASE}/patients/${patientId}`);
                if (response && response.ok) {
                    const patient = await response.json();
                    // Build edit form modal
                    const modalContent = `
                        <form id='editPatientForm'>
                            <!-- Basic Information Section -->
                            <div class='form-section'>
                                <h3 class='section-title'>Basic Information</h3>
                                <div class='form-group'>
                                    <label>Patient Number</label>
                                    <input name='patient_number' value='${patient.patient_number || ''}' required />
                                </div>
                                <div class='form-row-2'>
                                    <div class='form-group'>
                                        <label>First Name</label>
                                        <input name='first_name' value='${patient.first_name || ''}' required />
                                    </div>
                                    <div class='form-group'>
                                        <label>Last Name</label>
                                        <input name='last_name' value='${patient.last_name || ''}' required />
                                    </div>
                                </div>
                                <div class='form-row-3'>
                                    <div class='form-group'>
                                        <label>Date of Birth</label>
                                        <input name='date_of_birth' type='date' value='${patient.date_of_birth ? patient.date_of_birth.split('T')[0] : ''}' />
                                    </div>
                                    <div class='form-group'>
                                        <label>Phone</label>
                                        <input name='phone' value='${patient.phone || ''}' />
                                    </div>
                                    <div class='form-group'>
                                        <label>SSN</label>
                                        <input name='ssn' value='${patient.ssn || ''}' />
                                    </div>
                                </div>
                                <div class='form-group'>
                                    <label>Address</label>
                                    <input name='address' value='${patient.address || ''}' />
                                </div>
                            </div>

                            <!-- Insurance Information Section -->
                            <div class='form-section'>
                                <h3 class='section-title'>Insurance & Coverage</h3>
                                <div class='form-row-2'>
                                    <div class='form-group'>
                                        <label>Insurance Provider</label>
                                        <input name='insurance' value='${patient.insurance || ''}' />
                                    </div>
                                    <div class='form-group'>
                                        <label>Insurance ID</label>
                                        <input name='insurance_id' value='${patient.insurance_id || ''}' />
                                    </div>
                                </div>
                                <div class='form-row-2'>
                                    <div class='form-group'>
                                        <label>Medicaid ID</label>
                                        <input name='medicaid_id' value='${patient.medicaid_id || ''}' />
                                    </div>
                                    <div class='form-group'>
                                        <label>Authorization</label>
                                        <input name='authorization' value='${patient.authorization || ''}' />
                                    </div>
                                </div>
                            </div>

                            <!-- Authorization Section -->
                            <div class='form-section'>
                                <h3 class='section-title'>Authorization Details</h3>
                                <div class='form-row-2'>
                                    <div class='form-group'>
                                        <label>Authorization Number</label>
                                        <input name='auth_number' value='${patient.auth_number || ''}' />
                                    </div>
                                    <div class='form-group'>
                                        <label>Units (max 4 digits)</label>
                                        <input name='auth_units' value='${patient.auth_units || ''}' type='number' max='9999' oninput="if(this.value.length > 4) this.value = this.value.slice(0,4)" />
                                    </div>
                                </div>
                                <div class='form-row-2'>
                                    <div class='form-group'>
                                        <label>Start Date</label>
                                        <input name='auth_start_date' type='date' value='${patient.auth_start_date ? patient.auth_start_date.split('T')[0] : ''}' />
                                    </div>
                                    <div class='form-group'>
                                        <label>End Date</label>
                                        <input name='auth_end_date' type='date' value='${patient.auth_end_date ? patient.auth_end_date.split('T')[0] : ''}' />
                                    </div>
                                </div>
                                <div class='form-group'>
                                    <label>Diagnosis Code</label>
                                    <input name='auth_diagnosis_code' value='${patient.auth_diagnosis_code || ''}' />
                                </div>
                            </div>

                            <!-- Medical Information Section -->
                            <div class='form-section'>
                                <h3 class='section-title'>Medical Information</h3>
                                <div class='form-group'>
                                    <label>Diagnosis</label>
                                    <input name='diagnosis' value='${patient.diagnosis || ''}' />
                                </div>
                                <div class='form-row-2'>
                                    <div class='form-group'>
                                        <label>Referral Source</label>
                                        <input name='referal' value='${patient.referal || ''}' />
                                    </div>
                                    <div class='form-group'>
                                        <label>PSR Date</label>
                                        <input name='psr_date' type='date' value='${patient.psr_date ? patient.psr_date.split('T')[0] : ''}' />
                                    </div>
                                </div>
                            </div>

                            <!-- Service Period Section -->
                            <div class='form-section'>
                                <h3 class='section-title'>Service Period</h3>
                                <div class='form-row-2'>
                                    <div class='form-group'>
                                        <label>Start Date</label>
                                        <input name='start_date' type='date' value='${patient.start_date ? patient.start_date.split('T')[0] : ''}' />
                                    </div>
                                    <div class='form-group'>
                                        <label>End Date</label>
                                        <input name='end_date' type='date' value='${patient.end_date ? patient.end_date.split('T')[0] : ''}' />
                                    </div>
                                </div>
                            </div>

                            <!-- Billing Codes Section -->
                            <div class='form-section'>
                                <h3 class='section-title'>Billing Codes</h3>
                                <div class='form-row-2'>
                                    <div class='form-group'>
                                        <label>Code 1</label>
                                        <input name='code1' value='${patient.code1 || ''}' />
                                    </div>
                                    <div class='form-group'>
                                        <label>Code 2</label>
                                        <input name='code2' value='${patient.code2 || ''}' />
                                    </div>
                                </div>
                                <div class='form-row-2'>
                                    <div class='form-group'>
                                        <label>Code 3</label>
                                        <input name='code3' value='${patient.code3 || ''}' />
                                    </div>
                                    <div class='form-group'>
                                        <label>Code 4</label>
                                        <input name='code4' value='${patient.code4 || ''}' />
                                    </div>
                                </div>
                            </div>

                            <!-- Additional Notes Section -->
                            <div class='form-section'>
                                <h3 class='section-title'>Additional Notes</h3>
                                <div class='form-group'>
                                    <label>Notes</label>
                                    <textarea name='notes' rows='4' placeholder='Enter any additional notes about this patient...'>${patient.notes || ''}</textarea>
                                </div>
                            </div>

                            <div class='form-actions'>
                                <button class='btn' type='submit'>Save Changes</button>
                                <button class='btn btn-danger' type='button' id='cancelEditPatientBtn' style='margin-left:15px;'>Cancel</button>
                            </div>
                            <div id='editPatientAlert' style='margin-top:10px;'></div>
                        </form>`;
                    showModal('Edit Patient', modalContent);
                    document.getElementById('cancelEditPatientBtn').onclick = function() {
                        document.getElementById('mainModal').style.display = 'none';
                    };
                    document.getElementById('editPatientForm').onsubmit = async function(e) {
                        e.preventDefault();
                        const formData = new FormData(this);
                        const data = {};
                        for (let [key, value] of formData.entries()) {
                            data[key] = value;
                        }
                        try {
                            const resp = await authenticatedFetch(`${API_BASE}/patients/${patientId}`, {
                                method: 'PUT',
                                body: JSON.stringify(data)
                            });
                            if (resp && resp.ok) {
                                showAlert('editPatientAlert', 'Patient updated successfully!', 'success');
                                setTimeout(() => {
                                    document.getElementById('mainModal').style.display = 'none';
                                    loadPatients();
                                }, 1000);
                            } else if (resp) {
                                const error = await resp.json();
                                showAlert('editPatientAlert', `Error: ${error.detail}`, 'error');
                            }
                        } catch (err) {
                            showAlert('editPatientAlert', 'Error connecting to server.', 'error');
                        }
                    };
                } else {
                    showModal('Error', 'Failed to load patient data.');
                }
            } catch (error) {
                showModal('Error', 'Failed to load patient data.');
            }
        }
        // Expose editPatient globally for inline onclick
        window.editPatient = editPatient;

        // Open Service Form Modal
        function openServiceForm(serviceType) {
            // First reset the form to clear any previous values
            document.getElementById('serviceEntryForm').reset();
            
            // Then set the service type in the dropdown
            const serviceTypeSelect = document.getElementById('serviceTypeSelect');
            if (serviceTypeSelect) {
                // Find the option that matches the serviceType parameter
                for (let i = 0; i < serviceTypeSelect.options.length; i++) {
                    if (serviceTypeSelect.options[i].value === serviceType) {
                        serviceTypeSelect.selectedIndex = i;
                        break;
                    }
                }
            }
            
            document.getElementById('servicePatientSuggestions').innerHTML = '';
            document.getElementById('serviceEntryModal').style.display = 'block';
            document.getElementById('serviceFormTitle').textContent = `Add ${serviceType} Entry`;
        }
        window.openServiceForm = openServiceForm;

        // Close Service Entry Modal
        function closeServiceEntryModal() {
            document.getElementById('serviceEntryModal').style.display = 'none';
        }
        window.closeServiceEntryModal = closeServiceEntryModal;

        // Patient name autocomplete for service entry
        async function searchPatientNames(query) {
            const suggestionsDiv = document.getElementById('servicePatientSuggestions');
            if (!query || query.length < 2) {
                suggestionsDiv.innerHTML = '';
                return;
            }
            const response = await authenticatedFetch(`${API_BASE}/patients/?q=${encodeURIComponent(query)}`);
            if (response && response.ok) {
                const patients = await response.json();
                suggestionsDiv.innerHTML = patients.map(p => `<div class='autocomplete-suggestion' data-id='${p.id}' data-name='${p.first_name} ${p.last_name}'>${p.first_name} ${p.last_name} (#${p.patient_number})</div>`).join('');
                Array.from(suggestionsDiv.children).forEach(child => {
                    child.onclick = function() {
                        document.getElementById('servicePatientSearch').value = this.getAttribute('data-name');
                        document.getElementById('servicePatientSearch').setAttribute('data-id', this.getAttribute('data-id'));
                        suggestionsDiv.innerHTML = '';
                    };
                });
            } else {
                suggestionsDiv.innerHTML = '';
            }
        }
        window.searchPatientNames = searchPatientNames;

        // Submit Service Entry
        async function submitServiceEntry(e) {
            // Make sure mainAlert is properly positioned for visibility above all modals
            document.getElementById('mainAlert').style.zIndex = '9999';
            e.preventDefault();
            const patientNameInput = document.getElementById('servicePatientSearch');
            const patientId = patientNameInput.getAttribute('data-id');
            if (!patientId) {
                showAlert('mainAlert', 'Please select a patient from the suggestions.', 'warning');
                return;
            }
            
            // Build service data from form
            const formData = new FormData(document.getElementById('serviceEntryForm'));
            const data = {};
            
            // Process form data and handle checkbox correctly
            for (let [key, value] of formData.entries()) {
                // Handle the attended checkbox - convert to boolean
                if (key === 'attended') {
                    data[key] = value === 'true';
                } else {
                    data[key] = value;
                }
            }
            
            // If attended checkbox wasn't checked, it won't be in the formData
            // So we need to check if it exists, and if not, set it to null
            if (!formData.has('attended')) {
                data.attended = null;
            }
            
            // Check if this is a recurring appointment
            const isRecurring = document.getElementById('isRecurring').checked;
            
            try {
                if (isRecurring) {
                    // Get recurring options
                    const recurringType = document.querySelector('input[name="recurring_type"]:checked').value;
                    
                    let recurringDays = [];
                    let weeksCount = 0;
                    let monthsCount = 0;
                    
                    if (recurringType === 'weekly') {
                        // Get selected days for weekly recurrence
                        document.querySelectorAll('.day-checkbox:checked').forEach(checkbox => {
                            recurringDays.push(parseInt(checkbox.value));
                        });
                        
                        if (recurringDays.length === 0) {
                            showAlert('mainAlert', 'Please select at least one day of the week for recurring appointments.', 'warning');
                            return;
                        }
                        
                        weeksCount = parseInt(document.getElementById('weeksCount').value);
                    } else {
                        // For monthly, just get the count
                        monthsCount = parseInt(document.getElementById('monthsCount').value);
                    }
                    
                    // Add recurring data to the request
                    const recurringData = {
                        ...data,
                        recurring_type: recurringType,
                        recurring_days: recurringDays,
                        weeks_count: weeksCount,
                        months_count: monthsCount
                    };
                    
                    // Send to recurring service endpoint
                    const response = await authenticatedFetch(`${API_BASE}/patients/${patientId}/recurring-services`, {
                        method: 'POST',
                        body: JSON.stringify(recurringData)
                    });
                    
                    if (response && response.ok) {
                        const result = await response.json();
                        closeServiceEntryModal();
                        
                        // Use custom alert instead of browser alert
                        showAlert('mainAlert', `Service entry added successfully with ${result.recurring_appointments_count} recurring appointments!`, 'success');
                        
                        // Always refresh calendar data regardless of which tab is active
                        renderCalendar();
                        
                        // Show additional message if not on calendar tab
                        if (!document.getElementById('calendar-section').classList.contains('active')) {
                            setTimeout(() => {
                                showAlert('mainAlert', 'The calendar has been updated with your recurring appointments.', 'info');
                            }, 3000);
                        }
                    } else if (response) {
                        const error = await response.json();
                        showAlert('mainAlert', 'Error: ' + (error.detail || 'Failed to add recurring service entries.'), 'error');
                    } else {
                        showAlert('mainAlert', 'Error: Failed to add recurring service entries.', 'error');
                    }
                } else {
                    // Regular non-recurring service
                    const response = await authenticatedFetch(`${API_BASE}/patients/${patientId}/services`, {
                        method: 'POST',
                        body: JSON.stringify(data)
                    });
                    
                    if (response && response.ok) {
                        closeServiceEntryModal();
                        
                        // Use custom alert instead of browser alert
                        showAlert('mainAlert', 'Service entry added successfully!', 'success');
                        
                        // Always refresh calendar data regardless of which tab is active
                        renderCalendar();
                        
                        // Show additional message if not on calendar tab
                        if (!document.getElementById('calendar-section').classList.contains('active')) {
                            setTimeout(() => {
                                showAlert('mainAlert', 'The calendar has been updated with your new appointment.', 'info');
                            }, 3000);
                        }
                    } else if (response) {
                        const error = await response.json();
                        showAlert('mainAlert', 'Error: ' + (error.detail || 'Failed to add service entry.'), 'error');
                    } else {
                        showAlert('mainAlert', 'Error: Failed to add service entry.', 'error');
                    }
                }
            } catch (error) {
                console.error('Error submitting service entry:', error);
                showAlert('mainAlert', 'Error: Failed to add service entry.', 'error');
            }
        }
        window.submitServiceEntry = submitServiceEntry;

        // ==================== ATTENDANCE AND APPOINTMENT FUNCTIONS ====================

        // Open attendance form for PSR or TMS
        function openAttendanceForm(serviceType) {
            document.getElementById('attendanceForm').reset();
            document.getElementById('attendanceServiceType').value = serviceType;
            document.getElementById('attendanceFormTitle').textContent = `Add ${serviceType} Attendance`;
            document.getElementById('attendancePatientSuggestions').innerHTML = '';
            
            // Set default week start to current Monday
            const today = new Date();
            const monday = new Date(today);
            monday.setDate(today.getDate() - (today.getDay() - 1));
            document.getElementById('attendanceWeekStart').value = monday.toISOString().split('T')[0];
            updateWeekDays();
            
            document.getElementById('attendanceModal').style.display = 'block';
        }
        window.openAttendanceForm = openAttendanceForm;

        // Open appointment form for Individual Therapy or Evaluations
        function openAppointmentForm(serviceType) {
            document.getElementById('appointmentForm').reset();
            document.getElementById('appointmentServiceType').value = serviceType;
            document.getElementById('appointmentFormTitle').textContent = `Add ${serviceType} Appointment`;
            document.getElementById('appointmentPatientSuggestions').innerHTML = '';
            
            // Set default date to today
            document.getElementById('appointmentDate').value = new Date().toISOString().split('T')[0];
            
            document.getElementById('appointmentModal').style.display = 'block';
        }
        window.openAppointmentForm = openAppointmentForm;

        // Close modals
        function closeAttendanceModal() {
            document.getElementById('attendanceModal').style.display = 'none';
        }
        window.closeAttendanceModal = closeAttendanceModal;

        function closeAppointmentModal() {
            document.getElementById('appointmentModal').style.display = 'none';
        }
        window.closeAppointmentModal = closeAppointmentModal;

        // Update week days display when week start changes
        function updateWeekDays() {
            const weekStart = document.getElementById('attendanceWeekStart').value;
            if (!weekStart) return;
            
            // Parse the date string correctly to avoid timezone issues
            const [year, month, day] = weekStart.split('-').map(Number);
            const startDate = new Date(year, month - 1, day); // month is 0-indexed in JavaScript
            const days = ['monDate', 'tueDate', 'wedDate', 'thuDate', 'friDate'];
            
            days.forEach((dayId, index) => {
                const date = new Date(startDate);
                date.setDate(startDate.getDate() + index);
                document.getElementById(dayId).textContent = `(${date.getMonth() + 1}/${date.getDate()})`;
            });
        }
        window.updateWeekDays = updateWeekDays;

        // Patient search for attendance
        async function searchAttendancePatients(query) {
            const suggestionsDiv = document.getElementById('attendancePatientSuggestions');
            if (!query || query.length < 2) {
                suggestionsDiv.innerHTML = '';
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/search/?q=${encodeURIComponent(query)}`, {
                    headers: {
                        'Authorization': `Bearer ${accessToken}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    const patients = await response.json();
                    let suggestionsHTML = '';
                    patients.forEach(patient => {
                        suggestionsHTML += `
                            <div class="suggestion-item" onclick="selectAttendancePatient(${patient.id}, '${patient.first_name} ${patient.last_name}')">
                                ${patient.first_name} ${patient.last_name} (${patient.patient_number})
                            </div>
                        `;
                    });
                    suggestionsDiv.innerHTML = suggestionsHTML;
                }
            } catch (error) {
                console.error('Error searching patients:', error);
            }
        }
        window.searchAttendancePatients = searchAttendancePatients;

        // Patient search for appointment
        async function searchAppointmentPatients(query) {
            const suggestionsDiv = document.getElementById('appointmentPatientSuggestions');
            if (!query || query.length < 2) {
                suggestionsDiv.innerHTML = '';
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/search/?q=${encodeURIComponent(query)}`, {
                    headers: {
                        'Authorization': `Bearer ${accessToken}`,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    const patients = await response.json();
                    let suggestionsHTML = '';
                    patients.forEach(patient => {
                        suggestionsHTML += `
                            <div class="suggestion-item" onclick="selectAppointmentPatient(${patient.id}, '${patient.first_name} ${patient.last_name}')">
                                ${patient.first_name} ${patient.last_name} (${patient.patient_number})
                            </div>
                        `;
                    });
                    suggestionsDiv.innerHTML = suggestionsHTML;
                }
            } catch (error) {
                console.error('Error searching patients:', error);
            }
        }
        window.searchAppointmentPatients = searchAppointmentPatients;

        // Select patient for attendance
        function selectAttendancePatient(patientId, patientName) {
            document.getElementById('attendancePatientSearch').value = patientName;
            document.getElementById('attendancePatientId').value = patientId;
            document.getElementById('attendancePatientSuggestions').innerHTML = '';
        }
        window.selectAttendancePatient = selectAttendancePatient;

        // Select patient for appointment
        function selectAppointmentPatient(patientId, patientName) {
            document.getElementById('appointmentPatientSearch').value = patientName;
            document.getElementById('appointmentPatientId').value = patientId;
            document.getElementById('appointmentPatientSuggestions').innerHTML = '';
        }
        window.selectAppointmentPatient = selectAppointmentPatient;

        // Submit attendance form
        async function submitAttendance(event) {
            event.preventDefault();
            
            const formData = new FormData(event.target);
            const patientId = document.getElementById('attendancePatientId').value;
            const serviceType = document.getElementById('attendanceServiceType').value;
            const weekStart = document.getElementById('attendanceWeekStart').value;
            const serviceTime = formData.get('service_time');
            
            if (!patientId) {
                showAlert('Please select a patient', 'error');
                return;
            }
            
            // Get selected days
            const selectedDays = [];
            document.querySelectorAll('input[name="attendance_days"]:checked').forEach(checkbox => {
                selectedDays.push(parseInt(checkbox.value));
            });
            
            if (selectedDays.length === 0) {
                showAlert('Please select at least one day of attendance', 'error');
                return;
            }
            
            const attendanceData = {
                service_type: serviceType,
                week_start_date: weekStart,
                selected_days: selectedDays,
                service_time: serviceTime
            };
            
            try {
                const response = await fetch(`/patients/${patientId}/attendance`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${accessToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(attendanceData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    showAlert('mainAlert', `Success! Created ${result.services.length} attendance entries.`, 'success');
                    closeAttendanceModal();
                } else {
                    const errorData = await response.json();
                    showAlert('mainAlert', `Error: ${errorData.detail}`, 'error');
                }
            } catch (error) {
                console.error('Error submitting attendance:', error);
                showAlert('mainAlert', 'Error submitting attendance. Please try again.', 'error');
            }
        }
        window.submitAttendance = submitAttendance;

        // Submit appointment form
        async function submitAppointment(event) {
            event.preventDefault();
            
            const formData = new FormData(event.target);
            const patientId = document.getElementById('appointmentPatientId').value;
            const serviceType = document.getElementById('appointmentServiceType').value;
            
            if (!patientId) {
                showAlert('mainAlert', 'Please select a patient', 'error');
                return;
            }
            
            const serviceData = {
                service_type: serviceType,
                service_date: formData.get('service_date'),
                service_time: formData.get('service_time'),
                attended: formData.get('attended') === 'true' ? true : null,
                sheet_type: 'appointment',
                service_category: 'appointment'
            };
            
            try {
                const response = await fetch(`/patients/${patientId}/services`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${accessToken}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(serviceData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    showAlert('mainAlert', 'Appointment added successfully!', 'success');
                    closeAppointmentModal();
                    loadCalendar(); // Refresh calendar to show new appointment
                } else {
                    const errorData = await response.json();
                    showAlert('mainAlert', `Error: ${errorData.detail}`, 'error');
                }
            } catch (error) {
                console.error('Error submitting appointment:', error);
                showAlert('Error submitting appointment. Please try again.', 'error');
            }
        }
        window.submitAppointment = submitAppointment;
        
        // Call this function when the page loads
        window.addEventListener('load', ensureAlertVisibility);
        
        // Also call it before showing any modal
        const originalShowModal = showModal;
        showModal = function(title, content) {
            ensureAlertVisibility();
            originalShowModal(title, content);
        };

        // Utility function to format date strings without timezone issues
        function formatDateString(dateString) {
            if (!dateString) return '';
            
            // Parse the date string manually to avoid timezone issues
            const [year, month, day] = dateString.split('-').map(Number);
            const date = new Date(year, month - 1, day); // month is 0-indexed
            return date.toLocaleDateString();
        }

        // Function to save patient notes
        async function savePatientNotes(patientId) {
            try {
                const notesTextarea = document.getElementById('patientNotes');
                const notes = notesTextarea.value.trim();
                
                // Show loading state
                const saveBtn = document.getElementById('saveNotesBtn');
                const originalText = saveBtn.textContent;
                saveBtn.textContent = 'Saving...';
                saveBtn.disabled = true;
                
                const response = await authenticatedFetch(`${API_BASE}/patients/${patientId}`, {
                    method: 'PUT',
                    body: JSON.stringify({ notes: notes })
                });
                
                if (response && response.ok) {
                    showAlert('Notes saved successfully!', 'success');
                    
                    // Update the patient in the allPatients array
                    const patientIndex = allPatients.findIndex(p => p.id === patientId);
                    if (patientIndex !== -1) {
                        allPatients[patientIndex].notes = notes;
                    }
                } else if (response) {
                    const error = await response.json();
                    showAlert(`Error saving notes: ${error.detail}`, 'danger');
                }
                
            } catch (error) {
                console.error('Error saving patient notes:', error);
                showAlert('Error connecting to server while saving notes.', 'danger');
            } finally {
                // Reset button state
                const saveBtn = document.getElementById('saveNotesBtn');
                saveBtn.textContent = 'Save Notes';
                saveBtn.disabled = false;
            }
        }

        // Expose savePatientNotes globally
        window.savePatientNotes = savePatientNotes;

        // Alert and utility functions
        function showAlert(containerId, message, type = 'info') {
            const container = document.getElementById(containerId);
            if (!container) {
                console.error(`Alert container with ID "${containerId}" not found`);
                return;
            }
            
            const alertClass = type === 'error' ? 'alert-error' : 
                             type === 'success' ? 'alert-success' : 'alert-info';
            
            container.innerHTML = `
                <div class="alert ${alertClass}" style="display: block;">
                    ${message}
                </div>
            `;
            
            // Auto-hide success messages after 5 seconds
            if (type === 'success') {
                setTimeout(() => {
                    container.innerHTML = '';
                }, 5000);
            }
        }

        function ensureAlertVisibility() {
            // Ensure alert containers are visible when needed
            const alertContainers = document.querySelectorAll('[id$="Alert"], [id$="alert"]');
            alertContainers.forEach(container => {
                if (container.innerHTML.trim()) {
                    container.style.display = 'block';
                }
            });
        }

        // Make functions globally available
        window.showAlert = showAlert;
        window.ensureAlertVisibility = ensureAlertVisibility;

        // Authorization Management Functions
        async function loadPatientAuthorizations(patientId) {
            try {
                const response = await authenticatedFetch(`${API_BASE}/patients/${patientId}/authorizations`);
                
                if (response && response.ok) {
                    const authorizations = await response.json();
                    
                    // Debug logging
                    console.log('🔍 LOADED AUTHORIZATIONS FROM SERVER:');
                    authorizations.forEach((auth, index) => {
                        console.log(`  Authorization ${index + 1}:`);
                        console.log(`    ID: ${auth.id}`);
                        console.log(`    Auth Number: "${auth.auth_number}" (type: ${typeof auth.auth_number})`);
                        console.log(`    Auth Diagnosis Code: "${auth.auth_diagnosis_code}" (type: ${typeof auth.auth_diagnosis_code})`);
                        console.log(`    Full object:`, auth);
                    });
                    
                    const container = document.getElementById('authorizationsContainer');
                    
                    if (!container) {
                        console.error('Authorization container not found');
                        return;
                    }
                    
                    if (authorizations.length === 0) {
                        container.innerHTML = `
                            <div class="no-authorizations">
                                <p>No authorization records found. Click "Add New" to create one.</p>
                            </div>
                        `;
                        return;
                    }
                    
                    let html = `<div class="authorizations-list">`;
                    
                    authorizations.forEach(auth => {
                        // Improved handling of auth_number display
                        const authNumberDisplay = (auth.auth_number !== null && auth.auth_number !== undefined) 
                            ? auth.auth_number.toString()
                            : 'Not set';
                        
                        // Improved handling of diagnosis code display
                        const diagnosisCodeDisplay = (auth.auth_diagnosis_code && auth.auth_diagnosis_code.trim() !== '') 
                            ? auth.auth_diagnosis_code.trim()
                            : 'Not set';
                        
                        html += `
                            <div class="authorization-card">
                                <div class="auth-header">
                                    <h4>Auth #: ${authNumberDisplay}</h4>
                                    <div class="auth-actions">
                                        <button class="btn btn-small" onclick="editAuthorization(${auth.id})">Edit</button>
                                        <button class="btn btn-small btn-danger" onclick="deleteAuthorization(${auth.id}, ${patientId})">Delete</button>
                                    </div>
                                </div>
                                <div class="auth-details">
                                    <div class="auth-item">
                                        <label>Units:</label>
                                        <span>${auth.auth_units || 1}</span>
                                    </div>
                                    <div class="auth-item">
                                        <label>Start Date:</label>
                                        <span>${formatDateString(auth.auth_start_date)}</span>
                                    </div>
                                    <div class="auth-item">
                                        <label>End Date:</label>
                                        <span>${formatDateString(auth.auth_end_date)}</span>
                                    </div>
                                    <div class="auth-item">
                                        <label>Diagnosis Code:</label>
                                        <span>${diagnosisCodeDisplay}</span>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    
                    html += `</div>`;
                    container.innerHTML = html;
                } else {
                    console.error('Failed to load authorizations');
                    document.getElementById('authorizationsContainer').innerHTML = 
                        `<div class="error-message">Failed to load authorizations. Please try again.</div>`;
                }
            } catch (error) {
                console.error('Error loading authorizations:', error);
                document.getElementById('authorizationsContainer').innerHTML = 
                    `<div class="error-message">Error loading authorizations: ${error.message}</div>`;
            }
        }

        function showAddAuthorizationModal(patientId) {
            // Create the form with an explicitly set auth_number field
            const modalContent = `
                <form id="authorizationForm" class="authorization-form">
                    <input type="hidden" id="authPatientId" name="patientId" value="${patientId}">
                    
                    <div class="form-group">
                        <label for="authNumber">Authorization Number</label>
                        <input id="authNumber" name="auth_number" type="number" autocomplete="off"
                               placeholder="Enter authorization number (integer only)" 
                               min="1" step="1">
                    </div>
                    
                    <div class="form-row-2">
                        <div class="form-group">
                            <label for="authUnits">Units</label>
                            <input id="authUnits" name="auth_units" type="number" value="1" max="9999"
                                oninput="if(this.value.length > 4) this.value = this.value.slice(0,4)">
                        </div>
                        
                        <div class="form-group">
                            <label for="authDiagnosisCode">Diagnosis Code</label>
                            <input id="authDiagnosisCode" name="auth_diagnosis_code" type="text" autocomplete="off">
                        </div>
                    </div>
                    
                    <div class="form-row-2">
                        <div class="form-group">
                            <label for="authStartDate">Start Date</label>
                            <input id="authStartDate" name="auth_start_date" type="date">
                        </div>
                        
                        <div class="form-group">
                            <label for="authEndDate">End Date</label>
                            <input id="authEndDate" name="auth_end_date" type="date">
                        </div>
                    </div>
                    
                    <div id="authFormAlert" style="margin-top:10px;"></div>
                    
                    <div class="form-actions">
                        <button type="submit" class="btn">Save Authorization</button>
                        <button type="button" class="btn" onclick="document.getElementById('mainModal').style.display = 'none';">Cancel</button>
                    </div>
                </form>
            `;
            
            // Reset modal completely
            const mainModal = document.getElementById('mainModal');
            const modalTitle = document.getElementById('mainModalTitle');
            const modalBody = document.getElementById('mainModalBody');
            
            // Clear everything
            modalBody.innerHTML = '';
            
            // Set modal content
            modalTitle.textContent = 'Add Authorization';
            modalBody.innerHTML = modalContent;
            
            // Get today's date for defaults
            const today = new Date().toISOString().split('T')[0];
            
            // Show modal and then set values after rendering
            mainModal.style.display = 'block';
            
            // Find the form and fields
            const form = document.getElementById('authorizationForm');
            const authNumberField = document.getElementById('authNumber');
            const diagnosisCodeField = document.getElementById('authDiagnosisCode');
            const startDateField = document.getElementById('authStartDate');
            const endDateField = document.getElementById('authEndDate');
            const unitsField = document.getElementById('authUnits');
            
            // Set initial field values
            if (authNumberField) {
                authNumberField.value = '';
                setTimeout(() => authNumberField.focus(), 100);
            }
            
            if (diagnosisCodeField) {
                diagnosisCodeField.value = '';
            }

            if (startDateField) startDateField.value = today;
            if (endDateField) endDateField.value = today;
            if (unitsField) unitsField.value = '1';
            
            // Add submit handler to the form directly (no cloning)
            if (form) {
                // Remove any existing event listeners by replacing the form's onsubmit
                form.onsubmit = null;
                
                // Add the submit handler directly
                form.addEventListener('submit', async function(e) {
                    e.preventDefault(); // Prevent default form submission
                    
                    console.log(`🚨 FORM SUBMISSION STARTED`);
                    
                    // Use FormData like the Add Patient form does - this should capture all form values
                    const formData = new FormData(this);
                    const authData = {};
                    
                    console.log(`📝 FormData entries:`);
                    for (let [key, value] of formData.entries()) {
                        console.log(`  ${key}: "${value}"`);
                        if (value.trim() !== '') {
                            authData[key] = value;
                        }
                    }
                    
                    // Get patient ID from hidden field
                    const patientId = formData.get('patientId') || document.getElementById('authPatientId').value;
                    
                    console.log(`� Captured form data:`, authData);
                    console.log(`👤 Patient ID: "${patientId}"`);
                    
                    // Validate required fields
                    if (!authData.auth_number && !authData.auth_diagnosis_code) {
                        console.log(`⚠️ Both Auth Number and Diagnosis Code are empty!`);
                    }
                    
                    // Submit the authorization directly here instead of calling separate function
                    try {
                        // Helper function for date formatting
                        function formatDateForAPI(dateString) {
                            if (!dateString) return null;
                            return dateString.split('T')[0]; // Ensure YYYY-MM-DD format
                        }
                        
                        // Build the data object from FormData
                        let authNumberValue = null;
                        if (authData.auth_number && authData.auth_number !== '') {
                            const parsedAuthNumber = parseInt(authData.auth_number);
                            if (!isNaN(parsedAuthNumber)) {
                                authNumberValue = parsedAuthNumber;
                            }
                        }
                        
                        const data = {
                            auth_number: authNumberValue,
                            auth_units: authData.auth_units ? parseInt(authData.auth_units) : 1,
                            auth_diagnosis_code: authData.auth_diagnosis_code || null,
                            auth_start_date: authData.auth_start_date ? formatDateForAPI(authData.auth_start_date) : null,
                            auth_end_date: authData.auth_end_date ? formatDateForAPI(authData.auth_end_date) : null
                        };
                        
                        console.log(`📤 Sending data:`, data);
                        
                        const response = await authenticatedFetch(`${API_BASE}/patients/${patientId}/authorizations`, {
                            method: 'POST',
                            body: JSON.stringify(data)
                        });
                        
                        if (response && response.ok) {
                            const createdAuth = await response.json();
                            console.log('✅ Authorization created successfully:', createdAuth);
                            
                            document.getElementById('mainModal').style.display = 'none';
                            showAlert('mainAlert', 'Authorization added successfully!', 'success');
                            
                            // Refresh patient view to show new authorization
                            viewPatient(patientId);
                        } else if (response) {
                            const error = await response.json();
                            console.error('❌ Authorization validation error:', error);
                            let errorMsg = 'Failed to add authorization';
                            
                            if (error.detail) {
                                if (Array.isArray(error.detail)) {
                                    errorMsg = error.detail.map(err => `${err.loc.join('.')}: ${err.msg}`).join('<br>');
                                } else {
                                    errorMsg = error.detail;
                                }
                            }
                            
                            showAlert('authFormAlert', `Error: ${errorMsg}`, 'error');
                        }
                    } catch (error) {
                        console.error('❌ Error adding authorization:', error);
                        showAlert('authFormAlert', `Error: ${error.message || 'Failed to add authorization'}`, 'error');
                    }
                });
                
                console.log('Form submit handler attached directly');
            } else {
                console.error('AUTHORIZATION FORM NOT FOUND IN DOM');
            }
        }

        async function editAuthorization(authorizationId) {
            try {
                const response = await authenticatedFetch(`${API_BASE}/authorizations/${authorizationId}`);
                
                if (response && response.ok) {
                    const authorization = await response.json();
                    
                    const modalContent = `
                        <form id="editAuthorizationForm" class="authorization-form">
                            <input type="hidden" id="editAuthId" value="${authorization.id}">
                            <input type="hidden" id="editAuthPatientId" value="${authorization.patient_id}">
                            
                            <div class="form-group">
                                <label for="editAuthNumber">Authorization Number</label>
                                <input id="editAuthNumber" name="auth_number" type="number" 
                                       value="${authorization.auth_number || ''}"
                                       placeholder="Enter authorization number (integer only)" 
                                       min="1" step="1">
                            </div>
                            
                            <div class="form-row-2">
                                <div class="form-group">
                                    <label for="editAuthUnits">Units <span class="required">*</span></label>
                                    <input id="editAuthUnits" name="auth_units" type="number" max="9999" 
                                        value="${authorization.auth_units}" required
                                        oninput="if(this.value.length > 4) this.value = this.value.slice(0,4)">
                                </div>
                                
                                <div class="form-group">
                                    <label for="editAuthDiagnosisCode">Diagnosis Code</label>
                                    <input id="editAuthDiagnosisCode" name="auth_diagnosis_code" 
                                        value="${authorization.auth_diagnosis_code || ''}">
                                </div>
                            </div>
                            
                            <div class="form-row-2">
                                <div class="form-group">
                                    <label for="editAuthStartDate">Start Date <span class="required">*</span></label>
                                    <input id="editAuthStartDate" name="auth_start_date" type="date" 
                                        value="${authorization.auth_start_date.split('T')[0]}" required>
                                </div>
                                
                                <div class="form-group">
                                    <label for="editAuthEndDate">End Date <span class="required">*</span></label>
                                    <input id="editAuthEndDate" name="auth_end_date" type="date" 
                                        value="${authorization.auth_end_date.split('T')[0]}" required>
                                </div>
                            </div>
                            
                            <div class="form-actions">
                                <button type="submit" class="btn">Update Authorization</button>
                                <button type="button" class="btn" onclick="document.getElementById('mainModal').style.display = 'none';">Cancel</button>
                            </div>
                            
                            <div id="editAuthFormAlert" style="margin-top:10px;"></div>
                        </form>
                    `;
                    
                    showModal('Edit Authorization', modalContent);
                    
                    // Add submit handler with a delay to ensure DOM is ready
                    setTimeout(() => {
                        try {
                            const editForm = document.getElementById('editAuthorizationForm');
                            if (editForm) {
                                console.log('Edit authorization form found, attaching submit handler');
                                editForm.addEventListener('submit', async function(e) {
                                    e.preventDefault();
                                    await updateAuthorization();
                                });
                            } else {
                                console.error('Could not find edit authorization form in the DOM');
                            }
                        } catch (e) {
                            console.error('Error attaching edit form submit handler:', e);
                        }
                    }, 300);
                } else {
                    showAlert('mainAlert', 'Failed to load authorization details.', 'error');
                }
            } catch (error) {
                console.error('Error loading authorization:', error);
                showAlert('mainAlert', `Error: ${error.message || 'Failed to load authorization'}`, 'error');
            }
        }

        async function updateAuthorization() {
            try {
                const authId = document.getElementById('editAuthId').value;
                const patientId = document.getElementById('editAuthPatientId').value;
                const authNumber = document.getElementById('editAuthNumber').value;
                const authUnits = document.getElementById('editAuthUnits').value;
                const authDiagnosisCode = document.getElementById('editAuthDiagnosisCode').value;
                const authStartDate = document.getElementById('editAuthStartDate').value;
                const authEndDate = document.getElementById('editAuthEndDate').value;
                
                // Helper function for date formatting
                function formatDateForAPI(dateString) {
                    if (!dateString) return null;
                    return dateString.split('T')[0]; // Ensure YYYY-MM-DD format
                }
                
                // No validation needed for auth_number - it's optional and integer-only
                
                if (!authUnits || isNaN(parseInt(authUnits))) {
                    showAlert('editAuthFormAlert', 'Units must be a valid number', 'error');
                    return;
                }
                
                if (!authStartDate) {
                    showAlert('editAuthFormAlert', 'Start Date is required', 'error');
                    return;
                }
                
                if (!authEndDate) {
                    showAlert('editAuthFormAlert', 'End Date is required', 'error');
                    return;
                }
                
                const data = {
                    auth_number: authNumber.trim() !== '' ? parseInt(authNumber.trim()) : null, // Convert to integer
                    auth_units: parseInt(authUnits),
                    auth_diagnosis_code: authDiagnosisCode.trim() || null,
                    auth_start_date: formatDateForAPI(authStartDate),
                    auth_end_date: formatDateForAPI(authEndDate)
                };
                
                const response = await authenticatedFetch(`${API_BASE}/authorizations/${authId}`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
                
                if (response && response.ok) {
                    document.getElementById('mainModal').style.display = 'none';
                    showAlert('mainAlert', 'Authorization updated successfully!', 'success');
                    
                    // Refresh patient view to show updated authorization
                    viewPatient(patientId);
                } else if (response) {
                    const error = await response.json();
                    showAlert('editAuthFormAlert', `Error: ${error.detail || 'Failed to update authorization'}`, 'error');
                }
            } catch (error) {
                console.error('Error updating authorization:', error);
                showAlert('editAuthFormAlert', `Error: ${error.message || 'Failed to update authorization'}`, 'error');
            }
        }

        async function deleteAuthorization(authorizationId, patientId) {
            if (!confirm('Are you sure you want to delete this authorization?')) return;
            
            try {
                const response = await authenticatedFetch(`${API_BASE}/authorizations/${authorizationId}`, {
                    method: 'DELETE'
                });
                
                if (response && response.ok) {
                    showAlert('mainAlert', 'Authorization deleted successfully!', 'success');
                    
                    // Refresh patient view to update authorizations list
                    loadPatientAuthorizations(patientId);
                } else if (response) {
                    const error = await response.json();
                    showAlert('mainAlert', `Error: ${error.detail || 'Failed to delete authorization'}`, 'error');
                }
            } catch (error) {
                console.error('Error deleting authorization:', error);
                showAlert('mainAlert', `Error: ${error.message || 'Failed to delete authorization'}`, 'error');
            }
        }
        
        // Make authorization functions available globally
        window.showAddAuthorizationModal = showAddAuthorizationModal;
        window.editAuthorization = editAuthorization;
        window.deleteAuthorization = deleteAuthorization;