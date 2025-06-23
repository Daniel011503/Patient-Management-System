from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.sql import func
from database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_number = Column(String, unique=True, index=True)  # Letters and numbers
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    address = Column(String)
    date_of_birth = Column(Date)  # DOB
    phone = Column(String)
    medicaid_id = Column(String)
    insurance = Column(String)
    insurance_id = Column(String)
    session = Column(String)  # AM or PM
    referal = Column(String)  # Who referred the patient
    ssn = Column(String)  # Social Security Number
    psr_date = Column(Date)
    authorization = Column(String)  # Words or numbers
    diagnosis = Column(String)  # Letters and numbers
    start_date = Column(Date)
    end_date = Column(Date)
    code1 = Column(String)  # Code 1 field
    code2 = Column(String)  # Code 2 field
    code3 = Column(String)  # Code 3 field
    code4 = Column(String)  # Code 4 field
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())