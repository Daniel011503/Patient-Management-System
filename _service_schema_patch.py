from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional

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
