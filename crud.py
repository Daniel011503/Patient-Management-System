from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
import models
import schemas

def get_patient(db: Session, patient_id: int):
    return db.query(models.Patient).filter(models.Patient.id == patient_id).first()

def get_patients(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Patient).offset(skip).limit(limit).all()

def create_patient(db: Session, patient: schemas.PatientCreate):
    db_patient = models.Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

def update_patient(db: Session, patient_id: int, patient: schemas.PatientUpdate):
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient:
        update_data = patient.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_patient, field, value)
        db.commit()
        db.refresh(db_patient)
    return db_patient

def delete_patient(db: Session, patient_id: int):
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient:
        db.delete(db_patient)
        db.commit()
    return db_patient

def search_patients(db: Session, query: str):
    return db.query(models.Patient).filter(
        or_(
            models.Patient.patient_number.contains(query),
            models.Patient.first_name.contains(query),
            models.Patient.last_name.contains(query),
            models.Patient.medicaid_id.contains(query),
            models.Patient.insurance.contains(query),
            models.Patient.diagnosis.contains(query),
            models.Patient.referal.contains(query)
        )
    ).all()

def get_patient_by_number(db: Session, patient_number: str):
    """Get patient by patient number"""
    return db.query(models.Patient).filter(models.Patient.patient_number == patient_number).first()

def get_patient_with_financials(db: Session, patient_id: int):
    """Get patient with all their financial records"""
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if patient:
        # This will automatically load financial records due to the relationship
        return patient
    return None

def add_service_entry(db: Session, patient_id: int, service: schemas.ServiceCreate):
    db_service = models.Service(
        patient_id=patient_id,
        service_type=service.service_type,
        service_date=service.service_date,
        billing_code=service.billing_code,
        amount_paid=service.amount_paid,
        sheet_type=service.sheet_type
    )
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service