from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
import os
from dotenv import load_dotenv

load_dotenv()

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
security = HTTPBearer(auto_error=False)

class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[schemas.TokenData]:
    """Verify JWT token and return token data"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = schemas.TokenData(username=username)
        return token_data
    except JWTError:
        return None

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Get user by username"""
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get user by email"""
    return db.query(models.User).filter(models.User.email == email).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """Authenticate user with username/email and password"""
    # Try username first
    user = get_user_by_username(db, username)
    if not user:
        # Try email
        user = get_user_by_email(db, username)
    
    if not user or not verify_password(password, user.hashed_password):
        return None
    
    if not user.is_active:
        raise AuthError("Account is disabled", 403)
    
    return user

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create a new user"""
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
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> models.User:
    """Get current authenticated user from token or session"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = None
    
    # Try to get token from Authorization header first
    if credentials:
        token = credentials.credentials
    # Fallback to session cookie
    elif session_token:
        token = session_token
    
    if not token:
        raise credentials_exception
    
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception
    
    user = get_user_by_username(db, token_data.username)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """Get current active user"""
    return current_user

def require_role(allowed_roles: list):
    """Decorator to require specific roles"""
    def role_checker(current_user: models.User = Depends(get_current_active_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

# Create default admin user if it doesn't exist
def create_default_admin(db: Session):
    """Create default admin user if none exists"""
    admin_user = db.query(models.User).filter(models.User.role == "admin").first()
    if not admin_user:
        default_admin = schemas.UserCreate(
            username="admin",
            email="admin@spectrumhealth.com",
            full_name="System Administrator", 
            password="SpectrumAdmin2024!",  # More secure password
            role="admin"
        )
        try:
            create_user(db, default_admin)
            print("✅ Default admin user created: admin/SpectrumAdmin2024!")
        except AuthError:
            pass  # User might already exist