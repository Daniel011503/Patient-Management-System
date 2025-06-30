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

            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                    ...options.headers
                }
            };
            
            const response = await fetch(url, { ...defaultOptions, ...options });
            
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
        function showSection(sectionId) {
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
            
            // Add active class to clicked button
            event.target.classList.add('active');
            
            // Load data if needed
            if (sectionId === 'patient-log') {
                loadPatients();
            } else if (sectionId === 'user-management') {
                loadUsers();
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
            
            try {
                const response = await authenticatedFetch(`${API_BASE}/patients/`, {
                    method: 'POST',
                    body: JSON.stringify(patientData)
                });
                
                if (response && response.ok) {
                    const result = await response.json();
                    showAlert('add-alert', 'Patient added successfully!', 'success');
                    this.reset();
                    loadPatients();
                } else if (response) {
                    const error = await response.json();
                    showAlert('add-alert', `Error: ${error.detail}`, 'error');
                }
            } catch (error) {
                console.error('Form submission error:', error);
                showAlert('add-alert', 'Error connecting to server.', 'error');
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
                container.innerHTML = '<p>No patients found</p>';
                return;
            }
            
            container.innerHTML = patients.map(patient => `
                <div class="patient-card">
                    <div class="patient-number">Patient #${patient.patient_number}</div>
                    <div class="patient-name">${patient.first_name} ${patient.last_name}</div>
                    <div class="patient-details">
                        ${patient.phone ? `<strong>Phone:</strong> ${patient.phone}<br />` : '<strong>Phone:</strong> Not provided<br />'}
                        <strong>Session:</strong> ${patient.session}
                    </div>
                    <div style="margin-top: 15px;">
                        <button class="btn btn-small" onclick="viewPatient(${patient.id})" style="background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);">View</button>
                        <button class="btn btn-small" onclick="editPatient(${patient.id})" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%);">Edit</button>
                        <button class="btn btn-danger btn-small" onclick="deletePatient(${patient.id})">Delete</button>
                    </div>
                </div>
            `).join('');
        }

        // Search Patients
        document.getElementById('searchBox').addEventListener('input', function(e) {
            const query = e.target.value.toLowerCase();
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
            try {
                const response = await authenticatedFetch(`${API_BASE}/patients/${patientId}`);
                
                if (response && response.ok) {
                    const patient = await response.json();
                    
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

                    // Move filesHtml below uploadFormHtml and remove servicesHtml
                    const modalContent = `
                        <div class=\"patient-info-grid\">

                            <div class="patient-info-item">
                                <label>Patient Number:</label>
                                <p>${patient.patient_number || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Session:</label>
                                <p>${patient.session || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>First Name:</label>
                                <p>${patient.first_name || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Last Name:</label>
                                <p>${patient.last_name || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item patient-info-full">
                                <label>Address:</label>
                                <p>${patient.address || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Date of Birth:</label>
                                <p>${patient.date_of_birth ? new Date(patient.date_of_birth).toLocaleDateString() : 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Phone:</label>
                                <p>${patient.phone || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Social Security Number:</label>
                                <p>${patient.ssn || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Medicaid ID:</label>
                                <p>${patient.medicaid_id || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Insurance:</label>
                                <p>${patient.insurance || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Insurance ID:</label>
                                <p>${patient.insurance_id || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Referal:</label>
                                <p>${patient.referal || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>PSR Date:</label>
                                <p>${patient.psr_date ? new Date(patient.psr_date).toLocaleDateString() : 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item patient-info-full">
                                <label>Authorization:</label>
                                <p>${patient.authorization || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item patient-info-full">
                                <label>Diagnosis:</label>
                                <p>${patient.diagnosis || 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Start Date:</label>
                                <p>${patient.start_date ? new Date(patient.start_date).toLocaleDateString() : 'Not provided'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>End Date:</label>
                                <p>${patient.end_date ? new Date(patient.end_date).toLocaleDateString() : 'Ongoing'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Code 1:</label>
                                <p>${patient.code1 || 'Not assigned'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Code 2:</label>
                                <p>${patient.code2 || 'Not assigned'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Code 3:</label>
                                <p>${patient.code3 || 'Not assigned'}</p>
                            </div>
                            <div class="patient-info-item">
                                <label>Code 4:</label>
                                <p>${patient.code4 || 'Not assigned'}</p>
                            </div>
                        </div>
                        <div style="margin-top: 20px;">
                            <button class="btn btn-info btn-small attendance-sheet-btn" data-patient-id="${patient.id}">Attendance Sheet</button>
                            <button class="btn btn-primary btn-small appointment-sheet-btn" data-patient-id="${patient.id}">Appointment Sheet</button>
                        </div>
                        ${uploadFormHtml}
                        ${filesHtml}
                    `;

                    showModal('Patient Details', modalContent);

                    // Attach event listeners for Attendance/Appointment Sheet buttons
                    document.querySelector('.attendance-sheet-btn').addEventListener('click', function() {
                        showSheetModal(patient.id, 'attendance');
                    });
                    document.querySelector('.appointment-sheet-btn').addEventListener('click', function() {
                        showSheetModal(patient.id, 'appointment');
                    });

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
                }
            } catch (error) {
                showModal('Error', 'Failed to load patient details.');
            }
        }

        // Show Sheet Modal (Attendance/Appointment)
        async function showSheetModal(patientId, sheetType) {
            try {
                const resp = await authenticatedFetch(`${API_BASE}/patients/${patientId}/services?sheet_type=${sheetType}`);
                let entriesHtml = '';
                if (resp && resp.ok) {
                    const entries = await resp.json();
                    if (entries.length > 0) {
                        entriesHtml = `<table class='service-table' style='width:100%;margin-top:10px;border-collapse:collapse;'><thead><tr><th>Date</th><th>Type</th><th>Billing Code</th><th>Amount Paid</th></tr></thead><tbody>` +
                            entries.map(s => `<tr><td>${s.service_date ? new Date(s.service_date).toLocaleDateString() : ''}</td><td>${s.service_type || ''}</td><td>${s.billing_code || ''}</td><td>${s.amount_paid || ''}</td></tr>`).join('') +
                            `</tbody></table>`;
                    } else {
                        entriesHtml = `<div style='color:#888;'>No ${sheetType} entries for this patient.</div>`;
                    }
                } else {
                    entriesHtml = `<div style='color:#e74c3c;'>Error loading ${sheetType} entries.</div>`;
                }
                // Add a back button to return to patient view
                const backBtn = `<button class='btn btn-small' id='backToPatientBtn' style='margin-bottom:15px;'>&larr; Back to Patient</button>`;
                showModal(sheetType.charAt(0).toUpperCase() + sheetType.slice(1) + ' Sheet', backBtn + entriesHtml);
                // Attach back button event
                document.getElementById('backToPatientBtn').onclick = function() {
                    viewPatient(patientId);
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
            modalBody.innerHTML = content;
            modal.style.display = 'block';
        }

        // Close Modal Utility
        document.getElementById('mainModalClose').addEventListener('click', function() {
            document.getElementById('mainModal').style.display = 'none';
        });

        // Utility: Open patient file in new tab
        function openPatientFileInNewTab(patientId, fileId, filename) {
            window.open(`${API_BASE}/patients/${patientId}/files/${fileId}/download?filename=${encodeURIComponent(filename)}`, '_blank');
        }

        // Utility: Show alert
        function showAlert(elementId, message, type) {
            const el = document.getElementById(elementId);
            if (!el) return;
            el.innerHTML = `<span class="${type === 'success' ? 'alert-success' : 'alert-error'}">${message}</span>`;
            setTimeout(() => { el.innerHTML = ''; }, 3000);
        }

        // Expose openPatientFileInNewTab globally for inline onclick
        window.openPatientFileInNewTab = openPatientFileInNewTab;

        // Expose viewPatient globally for inline onclick
        window.viewPatient = viewPatient;

        // Expose editPatient and deletePatient if needed (implementations not shown here)
        // window.editPatient = editPatient;
        // window.deletePatient = deletePatient;

        // Expose logout globally
        window.logout = logout;
