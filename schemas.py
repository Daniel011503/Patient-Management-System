from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List

# Patient Schemas - Fixed date field types
class PatientBase(BaseModel):
    patient_number: str
    first_name: str
    last_name: str
    address: Optional[str] = None
    date_of_birth: Optional[date] = None  # Fixed: Changed from datetime to date
    phone: Optional[str] = None
    ssn: Optional[str] = None
    medicaid_id: Optional[str] = None
    insurance: Optional[str] = None
    insurance_id: Optional[str] = None
    referal: Optional[str] = None
    psr_date: Optional[date] = None  # Fixed: Changed from datetime to date
    authorization: Optional[str] = None
    # New authorization fields
    auth_number: Optional[str] = None
    auth_units: Optional[int] = None
    auth_start_date: Optional[date] = None
    auth_end_date: Optional[date] = None
    auth_diagnosis_code: Optional[str] = None
    diagnosis: Optional[str] = None
    start_date: Optional[date] = None  # Fixed: Changed from datetime to date
    end_date: Optional[date] = None  # Fixed: Changed from datetime to date
    code1: Optional[str] = None
    code2: Optional[str] = None
    code3: Optional[str] = None
    code4: Optional[str] = None
    notes: Optional[str] = None  # Added notes field

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    patient_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class Patient(PatientBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# User Authentication Schemas
class UserBase(BaseModel):
    username: str
    email: str  # Changed from EmailStr to str temporarily
    full_name: str
    role: str = "staff"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None  # Changed from EmailStr to str temporarily
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserInDB(User):
    hashed_password: str

# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[User] = None
    redirect_url: Optional[str] = None
    access_token: Optional[str] = None  # JWT access token
    token_type: Optional[str] = None    # Token type (bearer)

# Service Schemas
class Service(BaseModel):
    id: int
    patient_id: int
    service_type: str
    service_date: date
    service_time: str  # Added service_time field
    sheet_type: str
    service_category: str  # "attendance" or "appointment"
    week_start_date: Optional[date] = None  # For attendance tracking
    attended: Optional[bool] = None  # Added attended field
    is_recurring: Optional[bool] = False
    recurring_pattern: Optional[str] = None
    recurring_end_date: Optional[date] = None
    parent_service_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ServiceCreate(BaseModel):
    service_type: str
    service_date: date
    service_time: str  # Added service_time field
    sheet_type: str
    service_category: str  # "attendance" or "appointment"
    week_start_date: Optional[date] = None  # For attendance tracking
    attended: Optional[bool] = None  # Added attended field
    is_recurring: Optional[bool] = False
    recurring_pattern: Optional[str] = None
    recurring_end_date: Optional[date] = None
    parent_service_id: Optional[int] = None

# New schemas for attendance-based services
class AttendanceWeekCreate(BaseModel):
    service_type: str  # PSR or TMS
    week_start_date: date  # Start of the week (Monday)
    selected_days: List[int]  # Days of the week [0=Monday, 1=Tuesday, ..., 4=Friday]
    service_time: str

class AttendanceEntry(BaseModel):
    id: int
    patient_id: int
    service_type: str
    service_date: date
    service_time: str
    attended: Optional[bool] = None
    week_start_date: date
    created_at: datetime

    class Config:
        from_attributes = True