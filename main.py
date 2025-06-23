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
from auth import get_current_active_user, require_role, AuthError, create_access_token
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
    description="Professional patient management system with authentication",
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
    
    # Try to get the request body for debugging
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
    
    # Create basic HTML files if they don't exist
    login_content = """<!DOCTYPE html>
<html><head><title>Setup Required</title></head>
<body style="font-family: Arial; padding: 20px; text-align: center;">
<h1>🔧 Setup Required</h1>
<p>Please save your login.html file in the static/ folder</p>
<p>Current path should be: <code>static/login.html</code></p>
</body></html>"""
    
    with open(f"{static_path}/login.html", "w") as f:
        f.write(login_content)
    
    index_content = """<!DOCTYPE html>
<html><head><title>Setup Required</title></head>
<body style="font-family: Arial; padding: 20px; text-align: center;">
<h1>🔧 Setup Required</h1>
<p>Please save your index.html file in the static/ folder</p>
<p>Current path should be: <code>static/index.html</code></p>
</body></html>"""
    
    with open(f"{static_path}/index.html", "w") as f:
        f.write(index_content)
    
    logger.info("📄 Created placeholder HTML files")

# Check what files exist
logger.info("📁 Checking file structure:")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Static directory exists: {os.path.exists(static_path)}")

if os.path.exists(static_path):
    files = os.listdir(static_path)
    logger.info(f"Files in static/: {files}")
    
    for file in ['login.html', 'index.html']:
        file_path = os.path.join(static_path, file)
        exists = os.path.exists(file_path)
        size = os.path.getsize(file_path) if exists else 0
        logger.info(f"  {file}: {'✅' if exists else '❌'} ({size} bytes)")

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

# Root routes with better error handling
@app.get("/")
def read_root():
    try:
        return RedirectResponse(url="/static/login.html", status_code=302)
    except Exception as e:
        logger.error(f"Root redirect error: {e}")
        return HTMLResponse("""
        <html><body style="font-family: Arial; padding: 20px;">
        <h1>🔧 Spectrum Mental Health</h1>
        <p>Setup in progress...</p>
        <ul>
        <li><a href="/static/login.html">Login Page</a></li>
        <li><a href="/static/index.html">Main Application</a></li>
        <li><a href="/docs">API Documentation</a></li>
        <li><a href="/health">Health Check</a></li>
        </ul>
        </body></html>
        """)

@app.get("/login")
def login_redirect():
    return RedirectResponse(url="/static/login.html", status_code=302)

@app.get("/app")
def app_redirect():
    return RedirectResponse(url="/static/index.html", status_code=302)

# Debug route to check files
@app.get("/debug/files")
def debug_files():
    """Debug endpoint to check file structure"""
    try:
        current_dir = os.getcwd()
        static_exists = os.path.exists("static")
        static_files = os.listdir("static") if static_exists else []
        
        file_info = {}
        for file in ["login.html", "index.html"]:
            path = f"static/{file}"
            if os.path.exists(path):
                file_info[file] = {
                    "exists": True,
                    "size": os.path.getsize(path),
                    "path": os.path.abspath(path)
                }
            else:
                file_info[file] = {"exists": False}
        
        return {
            "current_directory": current_dir,
            "static_directory_exists": static_exists,
            "static_files": static_files,
            "file_details": file_info
        }
    except Exception as e:
        return {"error": str(e)}

# Debug endpoint to test patient creation
@app.post("/debug/test-patient")
def test_patient_creation(request_data: dict):
    """Debug endpoint to test patient data validation"""
    try:
        logger.info(f"🔍 Testing patient data: {request_data}")
        
        # Try to validate the data with our schema
        patient_data = schemas.PatientCreate(**request_data)
        logger.info(f"✅ Validation successful: {patient_data}")
        
        return {
            "success": True,
            "message": "Data validation passed",
            "validated_data": patient_data.model_dump()
        }
    except ValidationError as e:
        logger.error(f"❌ Validation failed: {e}")
        return {
            "success": False,
            "message": "Validation failed",
            "errors": e.errors(),
            "received_data": request_data
        }
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "received_data": request_data
        }

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "static_files_mounted": True,
        "static_directory": os.path.exists("static")
    }

# Authentication Routes (keeping your existing auth code)
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

# Add your other existing routes here (patients, etc.)
@app.post("/auth/logout")
async def logout(request: Request, current_user: models.User = Depends(get_current_active_user)):
    """Logout user (token-based, so just confirmation)"""
    logger.info(f"Logout request for user: {current_user.username}")
    return {"message": "Logged out successfully", "redirect_url": "/static/login.html"}

@app.post("/auth/register", response_model=schemas.User)
async def register_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin"]))
):
    """Register a new user (admin only)"""
    try:
        user = auth.create_user(db, user_data)
        logger.info(f"New user registered: {user.username} by {current_user.username}")
        return schemas.User.model_validate(user)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

# Protected Patient Routes (require authentication)
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
    current_user: models.User = Depends(require_role(["admin", "staff"]))
):
    logger.info(f"Creating patient {patient.patient_number} by user: {current_user.username}")
    logger.info(f"Patient data received: {patient.model_dump()}")  # Log the actual data
    
    # Check if patient number already exists
    try:
        existing_patient = crud.get_patient_by_number(db, patient_number=patient.patient_number)
        if existing_patient:
            raise HTTPException(status_code=400, detail="Patient number already exists")
    except AttributeError:
        # Fallback if get_patient_by_number doesn't exist
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
    current_user: models.User = Depends(require_role(["admin", "staff"]))
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
    current_user: models.User = Depends(require_role(["admin"]))
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
    current_user: models.User = Depends(get_current_active_user)
):
    logger.info(f"Search query '{q}' by user: {current_user.username}")
    patients = crud.search_patients(db, query=q)
    return patients

if __name__ == "__main__":
    import uvicorn
    print("🏥 Starting Spectrum Mental Health - DEBUG MODE")
    print("=" * 60)
    print("🔧 This version includes extra debugging")
    print("🌐 Go to: http://localhost:8000/debug/files")
    print("📋 To check your file structure")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)