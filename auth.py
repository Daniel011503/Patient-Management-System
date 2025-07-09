from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
import os
import re
import logging
import hashlib
import secrets
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# HIPAA Compliance Logging
hipaa_logger = logging.getLogger("hipaa_audit")
hipaa_logger.setLevel(logging.INFO)
handler = logging.FileHandler("hipaa_audit.log")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
hipaa_logger.addHandler(handler)

# Security Configuration - HIPAA Compliant
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  # Reduced for HIPAA compliance
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 1))  # Refresh token expires in 1 day
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 3))  # Account lockout after failed attempts
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", 15))  # Lockout period
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", 12))  # HIPAA requires strong passwords
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", 60))  # Auto-logout after inactivity

# Encryption key for PHI data (should be stored securely)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Generate a new key if none exists
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"⚠️  Generated new encryption key: {ENCRYPTION_KEY}")
    print("⚠️  Add this to your .env file: ENCRYPTION_KEY=" + ENCRYPTION_KEY)

try:
    if isinstance(ENCRYPTION_KEY, str):
        cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    else:
        cipher_suite = Fernet(ENCRYPTION_KEY)
except Exception as e:
    print(f"⚠️  Invalid encryption key, generating new one: {e}")
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
    print(f"⚠️  New encryption key: {ENCRYPTION_KEY}")
    print("⚠️  Update your .env file: ENCRYPTION_KEY=" + ENCRYPTION_KEY)

# Password hashing - Enhanced for HIPAA
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=12  # Increased rounds for better security
)

# OAuth2 scheme
security = HTTPBearer(auto_error=False)

class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code

def log_hipaa_event(event_type: str, user_id: str = None, details: str = "", ip_address: str = None):
    """Log HIPAA compliance events"""
    hipaa_logger.info(f"EVENT: {event_type} | USER: {user_id} | IP: {ip_address} | DETAILS: {details}")

def validate_password_strength(password: str) -> bool:
    """Validate password meets HIPAA requirements"""
    if len(password) < PASSWORD_MIN_LENGTH:
        return False
    
    # Must contain uppercase, lowercase, number, and special character
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    
    return True

def encrypt_phi_data(data: str) -> str:
    """Encrypt PHI data for storage"""
    if not data:
        return data
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_phi_data(encrypted_data: str) -> str:
    """Decrypt PHI data for use"""
    if not encrypted_data:
        return encrypted_data
    try:
        return cipher_suite.decrypt(encrypted_data.encode()).decode()
    except:
        return encrypted_data  # Return as-is if decryption fails (for backward compatibility)

def hash_identifier(data: str) -> str:
    """Create a hash of sensitive identifiers for audit purposes"""
    return hashlib.sha256(data.encode()).hexdigest()[:16]

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token with enhanced security"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add additional security claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(16),  # JWT ID for token tracking
        "token_type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(16),
        "token_type": "refresh"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> Optional[schemas.TokenData]:
    """Verify JWT token and return token data with enhanced validation"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        jti: str = payload.get("jti")
        token_type_claim: str = payload.get("token_type", "access")
        
        if username is None or jti is None:
            return None
            
        if token_type_claim != token_type:
            return None
            
        token_data = schemas.TokenData(username=username, jti=jti)
        return token_data
    except JWTError:
        return None

def check_account_lockout(db: Session, user: models.User) -> bool:
    """Check if account is locked due to failed login attempts"""
    if not user.failed_login_attempts:
        return False
        
    if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
        if user.lockout_until and datetime.utcnow() < user.lockout_until:
            return True
        elif user.lockout_until and datetime.utcnow() >= user.lockout_until:
            # Reset lockout
            user.failed_login_attempts = 0
            user.lockout_until = None
            db.commit()
            return False
    return False

def handle_failed_login(db: Session, user: models.User, ip_address: str = None):
    """Handle failed login attempt"""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    
    if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
        user.lockout_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        log_hipaa_event("ACCOUNT_LOCKED", user.username, f"Account locked after {MAX_LOGIN_ATTEMPTS} failed attempts", ip_address)
    
    db.commit()
    log_hipaa_event("FAILED_LOGIN", user.username, f"Failed login attempt #{user.failed_login_attempts}", ip_address)

def handle_successful_login(db: Session, user: models.User, ip_address: str = None):
    """Handle successful login"""
    user.failed_login_attempts = 0
    user.lockout_until = None
    user.last_login = datetime.utcnow()
    user.last_activity = datetime.utcnow()  # Update last activity on successful login
    user.last_login_ip = ip_address
    db.commit()
    log_hipaa_event("SUCCESSFUL_LOGIN", user.username, "User logged in successfully", ip_address)

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Get user by username"""
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get user by email"""
    return db.query(models.User).filter(models.User.email == email).first()

def authenticate_user(db: Session, username: str, password: str, ip_address: str = None) -> Optional[models.User]:
    """Authenticate user with username/email and password - HIPAA compliant"""
    # Try username first
    user = get_user_by_username(db, username)
    if not user:
        # Try email
        user = get_user_by_email(db, username)
    
    if not user:
        log_hipaa_event("FAILED_LOGIN", username, "User not found", ip_address)
        return None
    
    # Check account lockout
    if check_account_lockout(db, user):
        log_hipaa_event("LOGIN_BLOCKED", user.username, "Account locked", ip_address)
        raise AuthError("Account is temporarily locked due to multiple failed login attempts", 423)
    
    if not verify_password(password, user.hashed_password):
        handle_failed_login(db, user, ip_address)
        return None
    
    if not user.is_active:
        log_hipaa_event("LOGIN_BLOCKED", user.username, "Account disabled", ip_address)
        raise AuthError("Account is disabled", 403)
    
    handle_successful_login(db, user, ip_address)
    return user

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create a new user with HIPAA compliance validation"""
    # Validate password strength
    if not validate_password_strength(user.password):
        raise AuthError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters and contain uppercase, lowercase, number, and special character",
            400
        )
    
    # Check if username exists
    if get_user_by_username(db, user.username):
        raise AuthError("Username already exists", 400)
    
    # Check if email exists
    if get_user_by_email(db, user.email):
        raise AuthError("Email already exists", 400)
    
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role,
        password_last_changed=datetime.utcnow(),
        must_change_password=True  # Force password change on first login
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    log_hipaa_event("USER_CREATED", user.username, f"New user created with role: {user.role}")
    return db_user

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> models.User:
    """Get current authenticated user from token or session with HIPAA compliance"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = None
    client_ip = get_client_ip(request)
    
    # Try to get token from Authorization header first
    if credentials:
        token = credentials.credentials
    # Fallback to session cookie
    elif session_token:
        token = session_token
    
    if not token:
        log_hipaa_event("UNAUTHORIZED_ACCESS", None, "No token provided", client_ip)
        raise credentials_exception
    
    token_data = verify_token(token)
    if token_data is None:
        log_hipaa_event("INVALID_TOKEN", None, "Invalid token used", client_ip)
        raise credentials_exception
    
    user = get_user_by_username(db, token_data.username)
    if user is None:
        log_hipaa_event("USER_NOT_FOUND", token_data.username, "Token valid but user not found", client_ip)
        raise credentials_exception
    
    if not user.is_active:
        log_hipaa_event("INACTIVE_USER_ACCESS", user.username, "Inactive user attempted access", client_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Check session timeout
    if user.last_activity:
        inactive_time = datetime.utcnow() - user.last_activity
        if inactive_time.total_seconds() > (SESSION_TIMEOUT_MINUTES * 60):
            log_hipaa_event("SESSION_TIMEOUT", user.username, "Session timed out", client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired due to inactivity"
            )
    
    # Update last activity
    user.last_activity = datetime.utcnow()
    db.commit()
    
    return user

def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """Get current active user"""
    return current_user

def require_role(allowed_roles: list):
    """Decorator to require specific roles with HIPAA audit logging"""
    def role_checker(current_user: models.User = Depends(get_current_active_user)):
        if current_user.role not in allowed_roles:
            log_hipaa_event(
                "ACCESS_DENIED", 
                current_user.username, 
                f"Insufficient permissions. Required: {allowed_roles}, Has: {current_user.role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        log_hipaa_event(
            "ACCESS_GRANTED", 
            current_user.username, 
            f"Access granted with role: {current_user.role}"
        )
        return current_user
    return role_checker

def check_password_expiry(user: models.User) -> bool:
    """Check if password has expired (HIPAA requires regular password changes)"""
    if not user.password_last_changed:
        return True  # Force change if no date recorded
    
    days_since_change = (datetime.utcnow() - user.password_last_changed).days
    return days_since_change > 90  # 90 days password expiry

def change_password(db: Session, user: models.User, old_password: str, new_password: str) -> bool:
    """Change user password with validation"""
    if not verify_password(old_password, user.hashed_password):
        log_hipaa_event("PASSWORD_CHANGE_FAILED", user.username, "Invalid old password")
        return False
    
    if not validate_password_strength(new_password):
        log_hipaa_event("PASSWORD_CHANGE_FAILED", user.username, "New password doesn't meet requirements")
        return False
    
    # Prevent password reuse (check against last 5 passwords if implemented)
    user.hashed_password = get_password_hash(new_password)
    user.password_last_changed = datetime.utcnow()
    user.must_change_password = False
    db.commit()
    
    log_hipaa_event("PASSWORD_CHANGED", user.username, "Password successfully changed")
    return True

# Create default admin user if it doesn't exist
def create_default_admin(db: Session):
    """Create default admin user if none exists with HIPAA compliance"""
    admin_user = db.query(models.User).filter(models.User.role == "admin").first()
    if not admin_user:
        # Generate a secure random password
        secure_password = secrets.token_urlsafe(16) + "!A1"  # Ensures it meets requirements
        
        default_admin = schemas.UserCreate(
            username="admin",
            email="admin@spectrumhealth.com",
            full_name="System Administrator", 
            password=secure_password,
            role="admin"
        )
        try:
            admin_user = create_user(db, default_admin)
            print(f"✅ Default admin user created: admin/{secure_password}")
            print("⚠️  SECURITY: Please change the default password immediately!")
            
            # Log the creation
            log_hipaa_event("ADMIN_CREATED", "admin", "Default admin user created")
            
        except AuthError:
            pass  # User might already exist

# HIPAA Data Access Logging
def log_phi_access(user: models.User, patient_id: int, action: str, details: str = ""):
    """Log access to PHI data"""
    log_hipaa_event(
        "PHI_ACCESS",
        user.username,
        f"Patient ID: {hash_identifier(str(patient_id))} | Action: {action} | Details: {details}"
    )

def log_data_export(user: models.User, data_type: str, record_count: int):
    """Log data export activities"""
    log_hipaa_event(
        "DATA_EXPORT",
        user.username,
        f"Exported {record_count} records of type: {data_type}"
    )

def log_system_access(user: models.User, action: str, resource: str = ""):
    """Log general system access"""
    log_hipaa_event(
        "SYSTEM_ACCESS",
        user.username,
        f"Action: {action} | Resource: {resource}"
    )