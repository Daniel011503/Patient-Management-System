from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Date, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from datetime import datetime

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_number = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    address = Column(Text)
    date_of_birth = Column(Date)
    phone = Column(String)
    ssn = Column(String)
    medicaid_id = Column(String)
    insurance = Column(String)
    insurance_id = Column(String)
    session = Column(String, nullable=False)  # AM or PM
    referal = Column(String)
    psr_date = Column(Date)
    authorization = Column(String)
    diagnosis = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    code1 = Column(String)
    code2 = Column(String)
    code3 = Column(String)
    code4 = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    services = relationship(
        "Service",
        backref=backref("patient"),
        cascade="all, delete-orphan"
    )

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="staff")  # admin, staff, readonly
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    service_type = Column(String, nullable=False)
    service_date = Column(Date, nullable=False)
    service_time = Column(String, nullable=False)  # Added service_time field
    sheet_type = Column(String, nullable=False, default="attendance")
    attended = Column(Boolean, default=None, nullable=True)  # Track if patient attended the appointment
    is_recurring = Column(Boolean, default=False)  # Flag for recurring appointments
    recurring_pattern = Column(String, nullable=True)  # JSON string: days of week, e.g., "[1,3,5]" for Mon,Wed,Fri
    recurring_end_date = Column(Date, nullable=True)  # End date for recurring series
    parent_service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)  # Parent service for recurring series
    created_at = Column(DateTime, default=datetime.utcnow)