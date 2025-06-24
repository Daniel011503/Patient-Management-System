from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Date, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
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
    
    # Relationship to financial records
    financial_records = relationship("PatientFinancial", back_populates="patient", cascade="all, delete-orphan")

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

class PatientFinancial(Base):
    __tablename__ = "patient_financials"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    month_year = Column(String, nullable=False)  # Format: "2024-01" (YYYY-MM)
    monthly_revenue = Column(Float, nullable=False)  # Revenue generated this month
    sessions_attended = Column(Integer, default=0)  # Number of sessions attended
    notes = Column(Text)  # Optional notes about the financial record
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String)  # Username of who created this record
    
    # Relationship back to patient
    patient = relationship("Patient", back_populates="financial_records")
    
    def __repr__(self):
        return f"<PatientFinancial(patient_id={self.patient_id}, month_year='{self.month_year}', revenue=${self.monthly_revenue})>"