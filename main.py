from fastapi import FastAPI, HTTPException, Depends, status, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
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
from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List
import shutil
import uuid
import calendar

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
    current_user: models.User = Depends(get_current_active_user)
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    logger.info(f"Loading patients for user: {current_user.username}")
    patients = crud.get_patients(db, skip=skip, limit=limit)
    return patients

@app.post("/patients/", response_model=schemas.Patient)
def create_patient(
    patient: schemas.PatientCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
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

# === FINANCIAL TRACKING ENDPOINTS ===

@app.post("/patients/{patient_id}/financial", response_model=schemas.PatientFinancial)
async def create_financial_record(
    patient_id: int,
    financial_data: schemas.PatientFinancialCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Create a financial record for a patient"""
    # Verify patient exists
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if record already exists for this month
    existing_record = db.query(models.PatientFinancial).filter(
        models.PatientFinancial.patient_id == patient_id,
        models.PatientFinancial.month_year == financial_data.month_year
    ).first()
    
    if existing_record:
        raise HTTPException(status_code=400, detail="Financial record already exists for this month")
    
    # Create new financial record
    db_financial = models.PatientFinancial(
        **financial_data.model_dump(),
        created_by=current_user.username
    )
    
    db.add(db_financial)
    db.commit()
    db.refresh(db_financial)
    
    logger.info(f"Financial record created for patient {patient_id} by {current_user.username}")
    return schemas.PatientFinancial.model_validate(db_financial)

@app.get("/patients/{patient_id}/financial", response_model=list[schemas.PatientFinancial])
async def get_patient_financial_records(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all financial records for a patient"""
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    financial_records = db.query(models.PatientFinancial).filter(
        models.PatientFinancial.patient_id == patient_id
    ).order_by(desc(models.PatientFinancial.month_year)).all()
    
    return [schemas.PatientFinancial.model_validate(record) for record in financial_records]

@app.put("/patients/{patient_id}/financial/{financial_id}", response_model=schemas.PatientFinancial)
async def update_financial_record(
    patient_id: int,
    financial_id: int,
    financial_update: schemas.PatientFinancialUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update a financial record"""
    financial_record = db.query(models.PatientFinancial).filter(
        models.PatientFinancial.id == financial_id,
        models.PatientFinancial.patient_id == patient_id
    ).first()
    
    if not financial_record:
        raise HTTPException(status_code=404, detail="Financial record not found")
    
    # Update only provided fields
    update_data = financial_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(financial_record, field, value)
    
    financial_record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(financial_record)
    
    logger.info(f"Financial record {financial_id} updated by {current_user.username}")
    return schemas.PatientFinancial.model_validate(financial_record)

@app.delete("/patients/{patient_id}/financial/{financial_id}")
async def delete_financial_record(
    patient_id: int,
    financial_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete a financial record"""
    financial_record = db.query(models.PatientFinancial).filter(
        models.PatientFinancial.id == financial_id,
        models.PatientFinancial.patient_id == patient_id
    ).first()
    
    if not financial_record:
        raise HTTPException(status_code=404, detail="Financial record not found")
    
    db.delete(financial_record)
    db.commit()
    
    logger.info(f"Financial record {financial_id} deleted by {current_user.username}")
    return {"message": "Financial record deleted successfully"}

@app.get("/financial/summary", response_model=schemas.FinancialSummary)
async def get_financial_summary(
    month_year: str = None,  # Optional filter by month (YYYY-MM)
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get financial summary with top revenue patients and trends"""
    query = db.query(models.PatientFinancial)
    
    if month_year:
        query = query.filter(models.PatientFinancial.month_year == month_year)
    
    # Get total revenue and patient count
    financial_records = query.all()
    total_revenue = sum(record.monthly_revenue for record in financial_records)
    unique_patients = len(set(record.patient_id for record in financial_records))
    
    # Calculate average revenue per patient
    avg_revenue = total_revenue / unique_patients if unique_patients > 0 else 0
    
    # Get top revenue patients
    patient_revenue = {}
    for record in financial_records:
        if record.patient_id not in patient_revenue:
            patient_revenue[record.patient_id] = 0
        patient_revenue[record.patient_id] += record.monthly_revenue
    
    # Get patient details for top revenue
    top_patients = []
    for patient_id, revenue in sorted(patient_revenue.items(), key=lambda x: x[1], reverse=True)[:10]:
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        if patient:
            top_patients.append({
                "patient_id": patient_id,
                "patient_number": patient.patient_number,
                "name": f"{patient.first_name} {patient.last_name}",
                "total_revenue": revenue
            })
    
    # Get monthly trends (last 12 months)
    monthly_trends = []
    monthly_data = db.query(
        models.PatientFinancial.month_year,
        func.sum(models.PatientFinancial.monthly_revenue).label('total_revenue'),
        func.count(func.distinct(models.PatientFinancial.patient_id)).label('patient_count')
    ).group_by(models.PatientFinancial.month_year).order_by(models.PatientFinancial.month_year).all()
    
    for month_data in monthly_data:
        monthly_trends.append({
            "month_year": month_data.month_year,
            "total_revenue": float(month_data.total_revenue),
            "patient_count": month_data.patient_count
        })
    
    return schemas.FinancialSummary(
        total_patients=unique_patients,
        total_monthly_revenue=total_revenue,
        average_revenue_per_patient=avg_revenue,
        top_revenue_patients=top_patients,
        monthly_trends=monthly_trends
    )

@app.get("/financial/monthly-report/{month_year}", response_model=schemas.MonthlyFinancialReport)
async def get_monthly_financial_report(
    month_year: str,  # Format: YYYY-MM
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get detailed financial report for a specific month"""
    # Get all financial records for the month
    financial_records = db.query(models.PatientFinancial).filter(
        models.PatientFinancial.month_year == month_year
    ).all()
    
    if not financial_records:
        raise HTTPException(status_code=404, detail="No financial records found for this month")
    
    # Calculate totals
    total_revenue = sum(record.monthly_revenue for record in financial_records)
    total_patients = len(financial_records)
    total_sessions = sum(record.sessions_attended for record in financial_records)
    avg_sessions = total_sessions / total_patients if total_patients > 0 else 0
    
    # Get patient details
    patient_details = []
    for record in financial_records:
        patient = db.query(models.Patient).filter(models.Patient.id == record.patient_id).first()
        if patient:
            patient_details.append({
                "patient_id": record.patient_id,
                "patient_number": patient.patient_number,
                "name": f"{patient.first_name} {patient.last_name}",
                "monthly_revenue": record.monthly_revenue,
                "sessions_attended": record.sessions_attended,
                "notes": record.notes
            })
    
    # Sort by revenue (highest first)
    patient_details.sort(key=lambda x: x["monthly_revenue"], reverse=True)
    
    return schemas.MonthlyFinancialReport(
        month_year=month_year,
        total_revenue=total_revenue,
        total_patients=total_patients,
        average_sessions_per_patient=avg_sessions,
        patient_details=patient_details
    )

@app.get("/financial/all-records", response_model=list[schemas.PatientFinancial])
async def get_all_financial_records(
    skip: int = 0,
    limit: int = 100,
    month_year: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get all financial records with optional filtering"""
    query = db.query(models.PatientFinancial)
    
    if month_year:
        query = query.filter(models.PatientFinancial.month_year == month_year)
    
    financial_records = query.order_by(
        desc(models.PatientFinancial.month_year),
        desc(models.PatientFinancial.monthly_revenue)
    ).offset(skip).limit(limit).all()
    
    return [schemas.PatientFinancial.model_validate(record) for record in financial_records]

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
    return FileResponse(file_path, filename=orig_name)

if __name__ == "__main__":
    import uvicorn
    print("🏥 Starting Spectrum Mental Health - Multi-User Support with Financial Tracking")
    print("=" * 70)
    print("🔧 Multiple users, same access level")
    print("💰 Financial tracking enabled")
    print("🌐 Go to: http://localhost:8000/")
    print("📋 Everyone can manage users, patients, and finances")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=8000)