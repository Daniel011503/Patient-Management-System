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
    session: str
    referal: Optional[str] = None
    psr_date: Optional[date] = None  # Fixed: Changed from datetime to date
    authorization: Optional[str] = None
    diagnosis: Optional[str] = None
    start_date: Optional[date] = None  # Fixed: Changed from datetime to date
    end_date: Optional[date] = None  # Fixed: Changed from datetime to date
    code1: Optional[str] = None
    code2: Optional[str] = None
    code3: Optional[str] = None
    code4: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    patient_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    session: Optional[str] = None

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
    billing_code: str
    amount_paid: float
    sheet_type: str
    created_at: datetime

    class Config:
        from_attributes = True

class ServiceCreate(BaseModel):
    service_type: str
    service_date: date
    billing_code: str
    amount_paid: float
    sheet_type: str