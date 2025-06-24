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

# === FINANCIAL CRUD OPERATIONS ===

def create_financial_record(db: Session, financial: schemas.PatientFinancialCreate, created_by: str):
    """Create a new financial record for a patient"""
    db_financial = models.PatientFinancial(**financial.dict(), created_by=created_by)
    db.add(db_financial)
    db.commit()
    db.refresh(db_financial)
    return db_financial

def get_patient_financial_records(db: Session, patient_id: int):
    """Get all financial records for a specific patient"""
    return db.query(models.PatientFinancial).filter(
        models.PatientFinancial.patient_id == patient_id
    ).order_by(desc(models.PatientFinancial.month_year)).all()

def get_financial_record(db: Session, financial_id: int):
    """Get a specific financial record by ID"""
    return db.query(models.PatientFinancial).filter(models.PatientFinancial.id == financial_id).first()

def get_financial_record_by_month(db: Session, patient_id: int, month_year: str):
    """Get financial record for a specific patient and month"""
    return db.query(models.PatientFinancial).filter(
        models.PatientFinancial.patient_id == patient_id,
        models.PatientFinancial.month_year == month_year
    ).first()

def update_financial_record(db: Session, financial_id: int, financial: schemas.PatientFinancialUpdate):
    """Update a financial record"""
    db_financial = db.query(models.PatientFinancial).filter(models.PatientFinancial.id == financial_id).first()
    if db_financial:
        update_data = financial.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_financial, field, value)
        db.commit()
        db.refresh(db_financial)
    return db_financial

def delete_financial_record(db: Session, financial_id: int):
    """Delete a financial record"""
    db_financial = db.query(models.PatientFinancial).filter(models.PatientFinancial.id == financial_id).first()
    if db_financial:
        db.delete(db_financial)
        db.commit()
    return db_financial

def get_all_financial_records(db: Session, skip: int = 0, limit: int = 100, month_year: str = None):
    """Get all financial records with optional filtering"""
    query = db.query(models.PatientFinancial)
    
    if month_year:
        query = query.filter(models.PatientFinancial.month_year == month_year)
    
    return query.order_by(
        desc(models.PatientFinancial.month_year),
        desc(models.PatientFinancial.monthly_revenue)
    ).offset(skip).limit(limit).all()

def get_financial_summary_data(db: Session, month_year: str = None):
    """Get data for financial summary calculations"""
    query = db.query(models.PatientFinancial)
    
    if month_year:
        query = query.filter(models.PatientFinancial.month_year == month_year)
    
    return query.all()

def search_financial_records(db: Session, query: str):
    """Search financial records by patient information"""
    # Join with Patient table to search by patient name or number
    return db.query(models.PatientFinancial).join(models.Patient).filter(
        or_(
            models.Patient.patient_number.contains(query),
            models.Patient.first_name.contains(query),
            models.Patient.last_name.contains(query),
            models.PatientFinancial.month_year.contains(query),
            models.PatientFinancial.notes.contains(query) if models.PatientFinancial.notes else False
        )
    ).order_by(desc(models.PatientFinancial.month_year)).all()

def get_top_revenue_patients(db: Session, limit: int = 10, month_year: str = None):
    """Get top revenue generating patients"""
    from sqlalchemy import func
    
    query = db.query(
        models.PatientFinancial.patient_id,
        func.sum(models.PatientFinancial.monthly_revenue).label('total_revenue'),
        func.count(models.PatientFinancial.id).label('record_count')
    )
    
    if month_year:
        query = query.filter(models.PatientFinancial.month_year == month_year)
    
    return query.group_by(
        models.PatientFinancial.patient_id
    ).order_by(
        desc('total_revenue')
    ).limit(limit).all()

def get_monthly_trends(db: Session, months_back: int = 12):
    """Get monthly revenue trends"""
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Calculate the date range for the last N months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months_back * 30)  # Approximate
    
    return db.query(
        models.PatientFinancial.month_year,
        func.sum(models.PatientFinancial.monthly_revenue).label('total_revenue'),
        func.count(func.distinct(models.PatientFinancial.patient_id)).label('patient_count'),
        func.avg(models.PatientFinancial.monthly_revenue).label('avg_revenue'),
        func.sum(models.PatientFinancial.sessions_attended).label('total_sessions')
    ).group_by(
        models.PatientFinancial.month_year
    ).order_by(
        models.PatientFinancial.month_year
    ).all()

def get_patient_with_financials(db: Session, patient_id: int):
    """Get patient with all their financial records"""
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if patient:
        # This will automatically load financial records due to the relationship
        return patient
    return None