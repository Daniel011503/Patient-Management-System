from fastapi import FastAPI, HTTPException, Depends, status, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
import schemas
import crud
from database import SessionLocal, engine, get_db
import auth
from auth import get_current_active_user, create_access_token
import logging
import os
from pydantic import ValidationError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Spectrum Mental Health - Patient Management API",
    description="Professional patient management system with multi-user authentication",
    version="2.0.0"
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
@app.post("/users/", response_model=schemas.User)
async def create_new_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)  # Any logged-in user can create users
):
    """Create a new user"""
    try:
        user = auth.create_user(db, user_data)
        logger.info(f"New user created: {user.username} by {current_user.username}")
        return schemas.User.model_validate(user)
    except auth.AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@app.get("/users/", response_model=list[schemas.User])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)  # Any logged-in user can view users
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
    password_data: dict,  # {"new_password": "password"}
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)  # Any logged-in user
):
    logger.info(f"Loading patients for user: {current_user.username}")
    patients = crud.get_patients(db, skip=skip, limit=limit)
    return patients

@app.post("/patients/", response_model=schemas.Patient)
def create_patient(
    patient: schemas.PatientCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)  # Any logged-in user
):
    logger.info(f"Creating patient {patient.patient_number} by user: {current_user.username}")
    
    # Check if patient number already exists
    existing_patient = db.query(models.Patient).filter(
        models.Patient.patient_number == patient.patient_number
    ).first()
    if existing_patient:
        raise HTTPException(status_code=400, detail="Patient number already exists")
    
    try:
        result = crud.create_patient(db=db, patient=patient)
        logger.info(f"✅ Patient created successfully with ID: {result.id}")
        return result
    except Exception as e:
        logger.error(f"❌ Error creating patient: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating patient: {str(e)}")

@app.get("/patients/{patient_id}", response_model=schemas.Patient)
def read_patient(
    patient_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)  # Any logged-in user
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
    current_user: models.User = Depends(get_current_active_user)  # Any logged-in user
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
    current_user: models.User = Depends(get_current_active_user)  # Any logged-in user
):
    logger.info(f"Deleting patient {patient_id} by user: {current_user.username}")
    db_patient = crud.get_patient(db, patient_id=patient_id)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    crud.delete_patient(db=db, patient_id=patient_id)
    return {"message": "Patient deleted successfully"}

@app.get("/search/")
def search_patients(
    q: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)  # Any logged-in user
):
    logger.info(f"Search query '{q}' by user: {current_user.username}")
    patients = crud.search_patients(db, query=q)
    return patients

if __name__ == "__main__":
    import uvicorn
    print("🏥 Starting Spectrum Mental Health - Multi-User Support")
    print("=" * 60)
    print("🔧 Multiple users, same access level")
    print("🌐 Go to: http://localhost:8000/")
    print("📋 Everyone can manage users and patients")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)