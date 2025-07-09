# Production Configuration for main.py
# Add these imports and configurations to your main.py for production readiness

import os
from pathlib import Path

# Production environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./people.db")

# CORS origins for production
if ENVIRONMENT == "production":
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
    # Remove empty strings and strip whitespace
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]
else:
    ALLOWED_ORIGINS = ["*"]  # Allow all for development

# SSL/HTTPS enforcement
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "False").lower() == "true"

# File upload configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default
UPLOAD_PATH = os.getenv("UPLOAD_PATH", "uploads")

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-development-secret-key")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Production modifications to add to your FastAPI app configuration:

"""
# Update your FastAPI app creation:
app = FastAPI(
    title="Spectrum Mental Health - Patient Management API",
    description="Professional patient management system with multi-user authentication and financial tracking",
    version="2.1.0",
    docs_url="/docs" if DEBUG else None,  # Hide docs in production
    redoc_url="/redoc" if DEBUG else None,  # Hide redoc in production
    openapi_url="/openapi.json" if DEBUG else None  # Hide OpenAPI schema in production
)

# Update CORS middleware:
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add security headers for HTTPS enforcement:
if FORCE_HTTPS:
    @app.middleware("http")
    async def enforce_https(request: Request, call_next):
        if not request.url.scheme == "https":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url, status_code=301)
        response = await call_next(request)
        return response

# Production logging configuration:
if ENVIRONMENT == "production":
    import logging
    
    # Configure logging for production
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/var/log/spectrum-app.log'),
            logging.StreamHandler()
        ]
    )
    
    # Disable uvicorn access logs in production (optional)
    logging.getLogger("uvicorn.access").disabled = True
"""
