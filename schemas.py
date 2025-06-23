from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional

class PatientBase(BaseModel):
    patient_number: str
    first_name: str
    last_name: str
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    medicaid_id: Optional[str] = None
    insurance: Optional[str] = None
    insurance_id: Optional[str] = None
    session: Optional[str] = None  # AM or PM
    referal: Optional[str] = None
    ssn: Optional[str] = None
    psr_date: Optional[date] = None
    authorization: Optional[str] = None
    diagnosis: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    code1: Optional[str] = None
    code2: Optional[str] = None
    code3: Optional[str] = None
    code4: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientUpdate(BaseModel):
    patient_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    medicaid_id: Optional[str] = None
    insurance: Optional[str] = None
    insurance_id: Optional[str] = None
    session: Optional[str] = None
    referal: Optional[str] = None
    ssn: Optional[str] = None
    psr_date: Optional[date] = None
    authorization: Optional[str] = None
    diagnosis: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    code1: Optional[str] = None
    code2: Optional[str] = None
    code3: Optional[str] = None
    code4: Optional[str] = None

class Patient(PatientBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True