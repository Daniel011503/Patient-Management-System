def format_time_12hr(dt):
    """Format a datetime, time object, or string to 12-hour AM/PM string."""
    if dt is None or dt == '':
        return 'No time specified'
    
    if isinstance(dt, datetime):
        return dt.strftime("%I:%M %p").lstrip('0')
    elif hasattr(dt, 'hour') and hasattr(dt, 'minute'):
        return f"{(dt.hour % 12 or 12)}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"
    elif isinstance(dt, str):
        # Handle empty or whitespace strings
        if not dt.strip():
            return 'No time specified'
        
        # Try to parse string time like '16:30' or '08:05'
        import re
        match = re.match(r"^(\d{1,2}):(\d{2})$", dt.strip())
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            ampm = 'AM' if hour < 12 else 'PM'
            hour12 = (hour % 12) or 12
            return f"{hour12}:{minute:02d} {ampm}"
        
        # If it's already formatted (contains AM/PM), return as-is
        if 'AM' in dt.upper() or 'PM' in dt.upper():
            return dt
            
        return 'No time specified'  # fallback for unrecognized format
    
    return 'No time specified'
from fastapi import FastAPI, HTTPException, Depends, status, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
from datetime import datetime, timedelta, date
from pydantic import ValidationError
import models
import schemas
import crud
from database import SessionLocal, engine, get_db
import auth
from auth import get_current_active_user, create_access_token
import logging
import os
from pydantic import ValidationError
from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List
import shutil
import uuid
import calendar
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Spectrum Mental Health - Patient Management API",
    description="Professional patient management system with multi-user authentication and financial tracking",
    version="2.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"❌ Validation Error on {request.method} {request.url}")
    logger.error(f"❌ Validation Details: {exc.errors()}")
    
    try:
        body = await request.body()
        logger.error(f"❌ Request Body: {body.decode()}")
    except:
        logger.error("❌ Could not read request body")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": exc.body,
            "message": "Validation error - please check your input data"
        }
    )

# Check and create static directory
static_path = "static"
if not os.path.exists(static_path):
    os.makedirs(static_path)
    logger.info(f"✅ Created {static_path} directory")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    logger.info(f"✅ Static files mounted from {static_path}")
except Exception as e:
    logger.error(f"❌ Failed to mount static files: {e}")

# Add middleware to log requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"📡 {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"📤 Response: {response.status_code}")
    return response

# HIPAA Compliance: Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # HIPAA-compliant security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Remove server information for security
    if "server" in response.headers:
        del response.headers["server"]
    
    return response

# Create default admin user on startup
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        auth.create_default_admin(db)
        logger.info("🚀 Application started successfully")
        logger.info("=" * 60)
        logger.info("🌐 Available URLs:")
        logger.info("   • Root: http://localhost:8000/")
        logger.info("   • Login: http://localhost:8000/static/login.html")
        logger.info("   • Main App: http://localhost:8000/static/index.html")
        logger.info("   • API Docs: http://localhost:8000/docs")
        logger.info("   • Health: http://localhost:8000/health")
        logger.info("=" * 60)
    finally:
        db.close()

# Root routes
@app.get("/")
def read_root():
    return RedirectResponse(url="/static/login.html", status_code=302)

@app.get("/login")
def login_redirect():
    return RedirectResponse(url="/static/login.html", status_code=302)

@app.get("/app")
def app_redirect():
    return RedirectResponse(url="/static/index.html", status_code=302)

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "static_files_mounted": True,
        "static_directory": os.path.exists("static")
    }

# Authentication Routes
@app.post("/auth/login", response_model=schemas.LoginResponse)
async def login(
    login_data: schemas.LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token"""
    logger.info(f"Login attempt for user: {login_data.username}")
    
    try:
        user = auth.authenticate_user(db, login_data.username, login_data.password)
        if not user:
            logger.warning(f"Failed login attempt for user: {login_data.username}")
            return schemas.LoginResponse(
                success=False,
                message="Invalid username or password"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create access token
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        logger.info(f"Successful login for user: {user.username}")
        
        return schemas.LoginResponse(
            success=True,
            message="Login successful",
            user=schemas.User.model_validate(user),
            access_token=access_token,
            token_type="bearer",
            redirect_url="/static/index.html"
        )
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return schemas.LoginResponse(
            success=False,
            message="An error occurred during login"
        )

@app.get("/auth/me", response_model=schemas.User)
async def get_current_user_info(current_user: models.User = Depends(get_current_active_user)):
    """Get current user information"""
    return schemas.User.model_validate(current_user)

@app.post("/auth/logout")
async def logout(request: Request, current_user: models.User = Depends(get_current_active_user)):
    """Logout user (token-based, so just confirmation)"""
    logger.info(f"Logout request for user: {current_user.username}")
    return {"message": "Logged out successfully", "redirect_url": "/static/login.html"}

# USER MANAGEMENT ROUTES (SIMPLIFIED - NO ROLE RESTRICTIONS)

# Create or edit user endpoint
@app.post("/users/", response_model=schemas.User)
async def create_new_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new user"""
    # Allow system admin to create any user, including other admins
    try:
        # Check if username already exists
        existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
        if existing_user:
            logger.error(f"Attempt to create user with existing username: {user_data.username}")
            raise HTTPException(status_code=400, detail="Username already exists")
        # Only system admin can create users with role 'admin'
        if user_data.role == "admin" and current_user.role != "admin":
            logger.error(f"Non-admin user {current_user.username} tried to create admin user")
            raise HTTPException(status_code=403, detail="Only system admin can create admin users")
        # Password validation
        import re
        password = user_data.password
        logger.info(f"Validating password for new user: {password}")
        if not password or len(password) < 12:
            logger.error("Password too short")
            raise HTTPException(status_code=400, detail="Password must be at least 12 characters")
        if not re.search(r"[A-Z]", password):
            logger.error("Password missing uppercase letter")
            raise HTTPException(status_code=400, detail="Password must contain an uppercase letter")
        if not re.search(r"[a-z]", password):
            logger.error("Password missing lowercase letter")
            raise HTTPException(status_code=400, detail="Password must contain a lowercase letter")
        if not re.search(r"[0-9]", password):
            logger.error("Password missing number")
            raise HTTPException(status_code=400, detail="Password must contain a number")
        if not re.search(r"[^A-Za-z0-9]", password):
            logger.error("Password missing special character")
            raise HTTPException(status_code=400, detail="Password must contain a special character")
        user = auth.create_user(db, user_data)
        logger.info(f"New user created: {user.username} by {current_user.username}")
        return schemas.User.model_validate(user)
    except auth.AuthError as e:
        logger.error(f"AuthError creating user: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error creating user: {str(e)}")

# Edit user endpoint
@app.put("/users/{user_id}", response_model=schemas.User)
async def edit_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Edit an existing user"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        logger.error(f"Edit user failed: User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")
    # Only non-admins are restricted from editing admin users
    if user.role == "admin" and current_user.role != "admin":
        logger.error(f"Non-admin user {current_user.username} tried to edit admin user {user.username}")
        raise HTTPException(status_code=403, detail="Only system admin can edit admin users")
    # System admin can edit other admins
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    logger.info(f"User {user.username} updated by {current_user.username}")
    return schemas.User.model_validate(user)

@app.get("/users/", response_model=list[schemas.User])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List all users"""
    users = db.query(models.User).offset(skip).limit(limit).all()
    logger.info(f"User list requested by: {current_user.username}")
    return [schemas.User.model_validate(user) for user in users]

@app.get("/users/{user_id}", response_model=schemas.User)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get specific user by ID"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return schemas.User.model_validate(user)

@app.put("/users/{user_id}", response_model=schemas.User)
async def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update user information"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update only provided fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user.username} updated by {current_user.username}")
    return schemas.User.model_validate(user)

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete user"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent user from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    username = user.username
    db.delete(user)
    db.commit()
    
    logger.info(f"User {username} deleted by {current_user.username}")
    return {"message": f"User {username} deleted successfully"}

@app.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    password_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Reset user password"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_password = password_data.get("new_password")
    if not new_password:
        raise HTTPException(status_code=400, detail="New password is required")
    
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    
    user.hashed_password = auth.get_password_hash(new_password)
    db.commit()
    
    logger.info(f"Password reset for user {user.username} by {current_user.username}")
    return {"message": f"Password reset successfully for user {user.username}"}

@app.post("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Enable/disable user account"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent user from disabling themselves
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    
    user.is_active = not user.is_active
    db.commit()
    
    status_text = "enabled" if user.is_active else "disabled"
    logger.info(f"User {user.username} {status_text} by {current_user.username}")
    return {"message": f"User {user.username} {status_text} successfully", "is_active": user.is_active}

# Patient Routes (NO ROLE RESTRICTIONS - ALL LOGGED-IN USERS HAVE SAME ACCESS)
@app.get("/patients/", response_model=list[schemas.Patient])
def read_patients(
    skip: int = 0,
    limit: int = 100,
    q: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    logger.info(f"Loading patients for user: {current_user.username}")
    if q:
        # Use the same search logic as /search/ endpoint
        patients = crud.search_patients(db, query=q)
        return patients
    patients = crud.get_patients(db, skip=skip, limit=limit)
    return patients

@app.post("/patients/", response_model=schemas.Patient)
def create_patient(
    patient: schemas.PatientCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    logger.info(f"Creating patient {patient.patient_number} by user: {current_user.username}")
    
    # HIPAA Audit: Log patient creation attempt
    from auth import log_phi_access
    log_phi_access(current_user, 0, "CREATE_PATIENT", f"Creating new patient: {patient.patient_number}")
    
    # Check if patient number already exists
    existing_patient = db.query(models.Patient).filter(
        models.Patient.patient_number == patient.patient_number
    ).first()
    if existing_patient:
        raise HTTPException(status_code=400, detail="Patient number already exists")
    
    try:
        # Log the authorization data being received
        auth_data = {
            "auth_number": patient.auth_number,
            "auth_units": patient.auth_units,
            "auth_start_date": patient.auth_start_date,
            "auth_end_date": patient.auth_end_date,
            "auth_diagnosis_code": patient.auth_diagnosis_code
        }
        logger.info(f"Authorization data received: {auth_data}")
        
        result = crud.create_patient(db=db, patient=patient)
        
        # HIPAA Audit: Log successful patient creation
        log_phi_access(current_user, result.id, "PATIENT_CREATED", f"Patient created successfully: {result.patient_number}")
        
        logger.info(f"✅ Patient created successfully with ID: {result.id}")
        logger.info(f"✅ Authorization fields saved: auth_number={result.auth_number}, auth_units={result.auth_units}")
        return result
    except Exception as e:
        logger.error(f"❌ Error creating patient: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating patient: {str(e)}")

@app.get("/patients/{patient_id}", response_model=schemas.Patient)
def read_patient(
    patient_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    logger.info(f"Reading patient {patient_id} by user: {current_user.username}")
    db_patient = crud.get_patient(db, patient_id=patient_id)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient

@app.put("/patients/{patient_id}", response_model=schemas.Patient)
def update_patient(
    patient_id: int,
    patient: schemas.PatientUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    logger.info(f"Updating patient {patient_id} by user: {current_user.username}")
    db_patient = crud.get_patient(db, patient_id=patient_id)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.update_patient(db=db, patient_id=patient_id, patient=patient)

@app.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    logger.info(f"Deleting patient {patient_id} by user: {current_user.username}")
    db_patient = crud.get_patient(db, patient_id=patient_id)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    crud.delete_patient(db=db, patient_id=patient_id)
    # Delete patient files from uploads directory
    patient_folder = Path(UPLOAD_DIR) / str(patient_id)
    if patient_folder.exists() and patient_folder.is_dir():
        shutil.rmtree(patient_folder)
        logger.info(f"Deleted files for patient {patient_id} from {patient_folder}")
    return {"message": "Patient deleted successfully"}

@app.get("/search/")
def search_patients(
    q: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    logger.info(f"Search query '{q}' by user: {current_user.username}")
    patients = crud.search_patients(db, query=q)
    return patients

# --- PATIENT FILE UPLOAD ENDPOINTS ---
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.post("/patients/{patient_id}/files")
async def upload_patient_file(
    patient_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Upload a file for a patient (single file per request, saves .meta for original filename)"""
    patient_folder = Path(UPLOAD_DIR) / str(patient_id)
    patient_folder.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    save_path = patient_folder / f"{file_id}{ext}"
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Save original filename as .meta
    meta_path = patient_folder / f"{file_id}.meta"
    with open(meta_path, "w", encoding="utf-8") as meta:
        meta.write(file.filename)
    return {"id": file_id, "filename": file.filename}

@app.get("/patients/{patient_id}/files")
def list_patient_files(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """List all files for a patient"""
    patient_folder = Path(UPLOAD_DIR) / str(patient_id)
    if not patient_folder.exists():
        return []
    files = []
    for f in patient_folder.iterdir():
        if f.is_file() and not f.name.endswith('.meta'):
            file_id = f.stem
            ext = f.suffix
            meta_path = patient_folder / f"{file_id}.meta"
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as meta:
                    orig_name = meta.read().strip()
            else:
                orig_name = f.name
            files.append({"id": file_id, "filename": orig_name})
    return files

@app.get("/patients/{patient_id}/files/{file_id}")
def get_patient_file(
    patient_id: int,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Download a file for a patient by file id"""
    patient_folder = Path(UPLOAD_DIR) / str(patient_id)
    matches = list(patient_folder.glob(f"{file_id}.*"))
    matches = [f for f in matches if not f.name.endswith('.meta')]
    if not matches:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = matches[0]
    meta_path = patient_folder / f"{file_id}.meta"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as meta:
            orig_name = meta.read().strip()
    else:
        orig_name = file_path.name
    response = FileResponse(file_path)
    response.headers["Content-Disposition"] = f'inline; filename="{orig_name}"'
    return response

@app.post("/patients/{patient_id}/services")
def add_service_entry(
    patient_id: int,
    service: schemas.ServiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_patient = crud.get_patient(db, patient_id)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Determine service category based on service type
    if service.service_type in ["PSR", "TMS"]:
        service.service_category = "attendance"
        service.sheet_type = "attendance"
    elif service.service_type in ["Evaluations", "Individual Therapy"]:
        service.service_category = "appointment"
        service.sheet_type = "appointment"
    else:
        # Default to appointment for any other service types
        service.service_category = "appointment"
        service.sheet_type = "appointment"
    
    db_service = crud.add_service_entry(db, patient_id=patient_id, service=service)
    return {"success": True, "service": schemas.Service.model_validate(db_service)}

@app.get("/patients/{patient_id}/services")
def get_patient_services(
    patient_id: int,
    sheet_type: str = None,
    service_category: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get services for a specific patient with optional filters"""
    db_patient = crud.get_patient(db, patient_id)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    try:
        # Start with base query for this patient
        query = db.query(models.Service).filter(models.Service.patient_id == patient_id)
        
        # Apply filters if provided
        if sheet_type:
            query = query.filter(models.Service.sheet_type == sheet_type)
        if service_category:
            query = query.filter(models.Service.service_category == service_category)
        
        # Get the services ordered by date
        services = query.order_by(models.Service.service_date.desc()).all()
        formatted_services = []
        for s in services:
            service_dict = s.__dict__.copy() if hasattr(s, '__dict__') else dict(s)
            
            # Extract time value with better logic
            time_val = None
            
            # Debug: Log raw database values for patient services
            logger.info(f"🔍 Patient Service {s.id} RAW DATA:")
            logger.info(f"  - service_time: {getattr(s, 'service_time', 'NOT SET')} (type: {type(getattr(s, 'service_time', None))})")
            logger.info(f"  - service_date: {getattr(s, 'service_date', 'NOT SET')} (type: {type(getattr(s, 'service_date', None))})")
            
            # First, try to get service_time directly
            if hasattr(s, 'service_time') and s.service_time:
                time_val = s.service_time
                logger.info(f"  - Using service_time: {time_val}")
            # If no service_time, try to extract from service_date if it's a datetime
            elif hasattr(s, 'service_date') and s.service_date:
                if isinstance(s.service_date, datetime):
                    # Extract time portion from datetime
                    time_val = f"{s.service_date.hour:02d}:{s.service_date.minute:02d}"
                    logger.info(f"  - Extracted from service_date datetime: {time_val}")
                elif hasattr(s.service_date, 'time'):
                    # If service_date has a time component
                    time_obj = s.service_date.time()
                    time_val = f"{time_obj.hour:02d}:{time_obj.minute:02d}"
                    logger.info(f"  - Extracted from service_date time: {time_val}")
                else:
                    logger.info(f"  - service_date is not datetime: {type(s.service_date)}")
            else:
                logger.info(f"  - No time data found")
            
            # Format the time
            formatted_time = format_time_12hr(time_val)
            service_dict['service_time_formatted'] = formatted_time
            
            # Always provide both fields for frontend compatibility
            service_dict['service_time'] = formatted_time
            
            # Debug logging to see what we're sending to frontend
            logger.info(f"🔍 Patient Service {s.id}: raw_time='{time_val}', formatted='{formatted_time}'")
            
            formatted_services.append(schemas.Service.model_validate(service_dict))
        return formatted_services
    except Exception as e:
        logger.error(f"Error fetching patient services: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching services: {str(e)}")

@app.post("/patients/{patient_id}/attendance")
def add_attendance_week(
    patient_id: int,
    attendance_data: schemas.AttendanceWeekCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Add attendance entries for a patient for selected days in a week"""
    db_patient = crud.get_patient(db, patient_id)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Validate service type is attendance-based
    if attendance_data.service_type not in ["PSR", "TMS"]:
        raise HTTPException(status_code=400, detail="Service type must be PSR or TMS for attendance tracking")
    
    try:
        created_services = crud.add_attendance_week(db, patient_id=patient_id, attendance_data=attendance_data)
        return {
            "success": True, 
            "message": f"Created {len(created_services)} attendance entries",
            "services": [schemas.Service.model_validate(s) for s in created_services]
        }
    except Exception as e:
        logger.error(f"Error creating attendance week: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating attendance entries: {str(e)}")

@app.get("/attendance")
def get_attendance_sheet(
    patient_id: int = None,
    service_type: str = None,
    week_start: date = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get attendance sheet data with optional filters"""
    try:
        services = crud.get_attendance_services(db, patient_id=patient_id, service_type=service_type, week_start=week_start)
        formatted_services = []
        for s in services:
            service_dict = s.__dict__.copy() if hasattr(s, '__dict__') else dict(s)
            
            # Extract time value with better logic
            time_val = None
            
            # First, try to get service_time directly
            if hasattr(s, 'service_time') and s.service_time:
                time_val = s.service_time
            # If no service_time, try to extract from service_date if it's a datetime
            elif hasattr(s, 'service_date') and s.service_date:
                if isinstance(s.service_date, datetime):
                    # Extract time portion from datetime
                    time_val = f"{s.service_date.hour:02d}:{s.service_date.minute:02d}"
                elif hasattr(s.service_date, 'time'):
                    # If service_date has a time component
                    time_obj = s.service_date.time()
                    time_val = f"{time_obj.hour:02d}:{time_obj.minute:02d}"
            
            # Format the time
            formatted_time = format_time_12hr(time_val)
            service_dict['service_time_formatted'] = formatted_time
            
            # Always provide both fields for frontend compatibility
            service_dict['service_time'] = formatted_time
            
            formatted_services.append(schemas.Service.model_validate(service_dict))
        return formatted_services
    except Exception as e:
        logger.error(f"Error fetching attendance data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching attendance data: {str(e)}")

@app.get("/appointments") 
def get_appointment_sheet(
    patient_id: int = None,
    service_type: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get appointment sheet data with optional filters"""
    try:
        services = crud.get_appointment_services(db, patient_id=patient_id, service_type=service_type)
        formatted_services = []
        for s in services:
            service_dict = s.__dict__.copy() if hasattr(s, '__dict__') else dict(s)
            
            # Extract time value with better logic
            time_val = None
            
            # Debug: Log raw database values for appointments
            logger.info(f"🔍 Appointment Service {s.id} RAW DATA:")
            logger.info(f"  - service_time: {getattr(s, 'service_time', 'NOT SET')} (type: {type(getattr(s, 'service_time', None))})")
            logger.info(f"  - service_date: {getattr(s, 'service_date', 'NOT SET')} (type: {type(getattr(s, 'service_date', None))})")
            
            # First, try to get service_time directly
            if hasattr(s, 'service_time') and s.service_time:
                time_val = s.service_time
                logger.info(f"  - Using service_time: {time_val}")
            # If no service_time, try to extract from service_date if it's a datetime
            elif hasattr(s, 'service_date') and s.service_date:
                if isinstance(s.service_date, datetime):
                    # Extract time portion from datetime
                    time_val = f"{s.service_date.hour:02d}:{s.service_date.minute:02d}"
                    logger.info(f"  - Extracted from service_date datetime: {time_val}")
                elif hasattr(s.service_date, 'time'):
                    # If service_date has a time component
                    time_obj = s.service_date.time()
                    time_val = f"{time_obj.hour:02d}:{time_obj.minute:02d}"
                    logger.info(f"  - Extracted from service_date time: {time_val}")
                else:
                    logger.info(f"  - service_date is not datetime: {type(s.service_date)}")
            else:
                logger.info(f"  - No time data found")
            
            # Format the time
            formatted_time = format_time_12hr(time_val)
            service_dict['service_time_formatted'] = formatted_time
            
            # Always provide both fields for frontend compatibility
            service_dict['service_time'] = formatted_time
            
            # Debug logging to see what we're sending to frontend
            logger.info(f"🔍 Appointment Service {s.id}: raw_time='{time_val}', formatted='{formatted_time}'")
            
            formatted_services.append(schemas.Service.model_validate(service_dict))
        return formatted_services
    except Exception as e:
        logger.error(f"Error fetching appointment data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching appointment data: {str(e)}")

@app.put("/services/{service_id}")
def update_service_entry(
    service_id: int,
    service_update: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_service = crud.update_service_entry(db, service_id=service_id, service_update=service_update)
    if db_service is None:
        raise HTTPException(status_code=404, detail="Service entry not found")
    return {"success": True, "service": schemas.Service.model_validate(db_service)}

@app.post("/patients/{patient_id}/recurring-services")
def add_recurring_service_entry(
    patient_id: int,
    service_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a recurring service entry with auto-generated appointments"""
    # Validate patient exists
    db_patient = crud.get_patient(db, patient_id)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    try:
        # Extract recurring fields from service_data
        recurring_type = service_data.pop("recurring_type", None)
        recurring_days = service_data.pop("recurring_days", [])
        weeks_count = service_data.pop("weeks_count", 0)
        months_count = service_data.pop("months_count", 0)
        
        # Create the parent service
        service = schemas.ServiceCreate(**service_data)
        service.is_recurring = True
        service.recurring_pattern = json.dumps(recurring_days)
        
        # Set recurring_end_date based on recurrence type
        if recurring_type == "weekly" and weeks_count > 0:
            end_date = service.service_date + timedelta(days=(weeks_count * 7))
            service.recurring_end_date = end_date
        elif recurring_type == "monthly" and months_count > 0:
            # Approximate end date - not exact due to varying month lengths
            service_date = service.service_date
            year = service_date.year + ((service_date.month - 1 + months_count) // 12)
            month = ((service_date.month - 1 + months_count) % 12) + 1
            day = min(service_date.day, calendar.monthrange(year, month)[1])
            service.recurring_end_date = date(year, month, day)
        
        # Create parent service
        db_service = crud.add_service_entry(db, patient_id=patient_id, service=service)
        
        # Create all recurring instances
        created_ids = crud.create_recurring_appointments(
            db=db, 
            parent_service=db_service,
            recurring_type=recurring_type,
            recurring_days=recurring_days,
            weeks_count=weeks_count,
            months_count=months_count
        )
        
        return {
            "success": True, 
            "parent_service": schemas.Service.model_validate(db_service),
            "recurring_appointments_count": len(created_ids)
        }
        
    except Exception as e:
        logger.error(f"Error creating recurring appointments: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error creating recurring appointments: {str(e)}"
        )

# Authorization Endpoints
@app.get("/patients/{patient_id}/authorizations", response_model=list[schemas.Authorization])
def get_patient_authorizations(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all authorizations for a patient"""
    db_patient = crud.get_patient(db, patient_id=patient_id)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.get_authorizations(db, patient_id=patient_id)

@app.post("/patients/{patient_id}/authorizations", response_model=schemas.Authorization)
def create_patient_authorization(
    patient_id: int,
    authorization: schemas.AuthorizationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a new authorization for a patient"""
    print(f"🔍 POST /patients/{patient_id}/authorizations - Request received!")
    logger.info(f"POST /patients/{patient_id}/authorizations - Request received!")
    
    db_patient = crud.get_patient(db, patient_id=patient_id)
    if db_patient is None:
        print(f"❌ Patient {patient_id} not found!")
        raise HTTPException(status_code=404, detail="Patient not found")
    
    try:
        # Enhanced debug logging
        auth_data = authorization.dict()
        auth_number_value = auth_data.get('auth_number', '')
        
        logger.info(f"Creating authorization for patient {patient_id}: {auth_data}")
        print(f"🔍 Creating authorization: patient={patient_id}")
        print(f"🔍 Auth Number from dict: '{auth_number_value}' (type: {type(auth_number_value)})")
        print(f"🔍 Units: {auth_data.get('auth_units', 'Not provided')}")
        print(f"🔍 FULL INCOMING AUTH DATA: {auth_data}")
        
        # Auth number is now optional - no validation needed
        auth_number = getattr(authorization, "auth_number", None)
        
        # Just log the auth_number attribute for debugging
        print(f"🔍 Auth Number from attribute: '{auth_number}' (type: {type(auth_number)})")
        print(f"🔍 Auth Number is None: {auth_number is None}")
        print(f"🔍 Auth Number == None: {auth_number == None}")
        
        # No validation needed since auth_number is now optional
        # If auth_number is provided, ensure it's an integer
        if auth_number is not None:
            try:
                # Convert to integer if it's not already
                final_auth_number = int(auth_number)
                authorization.auth_number = final_auth_number
                print(f"✅ Converted auth number to integer: {authorization.auth_number}")
            except (ValueError, TypeError):
                print(f"❌ Failed to convert auth number '{auth_number}' to integer")
                raise HTTPException(
                    status_code=422,
                    detail="Authorization Number must be a valid integer"
                )
        else:
            print(f"⚠️ Auth number is None, keeping as null")
            
        # Set default values for missing fields (start/end date if not provided)
        if not authorization.auth_start_date:
            authorization.auth_start_date = date.today()
        if not authorization.auth_end_date:
            # Default to one year from start date
            if authorization.auth_start_date:
                authorization.auth_end_date = authorization.auth_start_date.replace(year=authorization.auth_start_date.year + 1)
            else:
                authorization.auth_end_date = date.today().replace(year=date.today().year + 1)
        
        # Create the authorization
        created_auth = crud.create_authorization(db, patient_id=patient_id, authorization=authorization)
        
        # Debug what was actually saved
        print(f"🔍 Created authorization in DB:")
        print(f"🔍   ID: {created_auth.id}")
        print(f"🔍   Auth Number: {created_auth.auth_number} (type: {type(created_auth.auth_number)})")
        print(f"🔍   Patient ID: {created_auth.patient_id}")
        print(f"🔍   Units: {created_auth.auth_units}")
        
        return created_auth
    except ValidationError as ve:
        logger.error(f"Validation error creating authorization: {str(ve)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(ve)}")
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Error creating authorization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating authorization: {str(e)}")

@app.get("/authorizations/{authorization_id}", response_model=schemas.Authorization)
def get_authorization(
    authorization_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get a specific authorization by ID"""
    db_authorization = crud.get_authorization(db, authorization_id=authorization_id)
    if db_authorization is None:
        raise HTTPException(status_code=404, detail="Authorization not found")
    return db_authorization

@app.put("/authorizations/{authorization_id}", response_model=schemas.Authorization)
def update_authorization(
    authorization_id: int,
    authorization: schemas.AuthorizationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update an existing authorization"""
    db_authorization = crud.get_authorization(db, authorization_id=authorization_id)
    if db_authorization is None:
        raise HTTPException(status_code=404, detail="Authorization not found")
    
    # No validation needed for auth_number - it's now optional
    # If auth_number is provided, ensure it's an integer
    if hasattr(authorization, 'auth_number') and authorization.auth_number is not None:
        try:
            # Convert to integer if it's not already
            authorization.auth_number = int(authorization.auth_number)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422,
                detail="Authorization Number must be a valid integer"
            )
            
    return crud.update_authorization(db, authorization_id=authorization_id, authorization=authorization)

@app.delete("/authorizations/{authorization_id}")
def delete_authorization(
    authorization_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete an authorization"""
    db_authorization = crud.get_authorization(db, authorization_id=authorization_id)
    if db_authorization is None:
        raise HTTPException(status_code=404, detail="Authorization not found")
    
    if crud.delete_authorization(db, authorization_id=authorization_id):
        return {"message": "Authorization deleted successfully"}
    
    raise HTTPException(status_code=500, detail="Failed to delete authorization")

if __name__ == "__main__":
    import uvicorn
    import socket
    
    # Always use port 8000
    port = 8000
    
    # Check if port 8000 is available
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
    except OSError:
        print(f"❌ Port {port} is already in use!")
        print("To fix this:")
        print("1. Close any other instances of this application")
        print("2. Stop any other web servers running on port 8000")
        print("3. Or run: netstat -ano | findstr :8000  (to find what's using the port)")
        print("4. Then use: taskkill /PID <PID> /F  (to kill the process)")
        exit(1)
    
    print("🏥 Starting Spectrum Mental Health - Multi-User Support with Financial Tracking")
    print("=" * 70)
    print("🔧 Multiple users, same access level")
    print("💰 Financial tracking enabled")
    print(f"🌐 Go to: http://localhost:{port}/")
    print(f"🌐 Login: http://localhost:{port}/static/login.html")
    print(f"🌐 Main App: http://localhost:{port}/static/index.html")
    print("📋 Everyone can manage users, patients, and finances")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=port)