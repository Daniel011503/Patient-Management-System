from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
import models
import schemas
import json
from datetime import timedelta, date
import calendar

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
        service_time=service.service_time,
        sheet_type=service.sheet_type,
        service_category=service.service_category,
        week_start_date=service.week_start_date,
        attended=service.attended,
        is_recurring=service.is_recurring,
        recurring_pattern=service.recurring_pattern,
        recurring_end_date=service.recurring_end_date,
        parent_service_id=service.parent_service_id
    )
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

def update_service_entry(db: Session, service_id: int, service_update: dict):
    db_service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if db_service:
        for key, value in service_update.items():
            if hasattr(db_service, key):
                setattr(db_service, key, value)
        db.commit()
        db.refresh(db_service)
    return db_service

def create_recurring_appointments(db: Session, parent_service: models.Service, recurring_type: str, recurring_days: list, weeks_count: int = 0, months_count: int = 0):
    """
    Create recurring appointments based on parent service
    
    Parameters:
    - db: Database session
    - parent_service: Parent service object to base recurring appointments on
    - recurring_type: 'weekly' or 'monthly'
    - recurring_days: List of weekdays (0=Monday, 6=Sunday) for weekly recurrence or list of days for monthly recurrence
    - weeks_count: Number of weeks to repeat (for weekly)
    - months_count: Number of months to repeat (for monthly)
    
    Returns:
    - List of created service IDs
    """
    created_services = []
    start_date = parent_service.service_date
    
    # For weekly recurrence
    if recurring_type == 'weekly' and weeks_count > 0:
        current_date = start_date
        # Get the weekday of the start date (0 = Monday, 6 = Sunday)
        start_weekday = current_date.weekday()
        
        # Loop through the number of weeks
        for week in range(weeks_count):
            # Start from the beginning of each week (week after start week for the first iteration)
            if week > 0:  # Skip the first week as we're starting from it
                # Move to first day of next week
                days_to_monday = 7 - current_date.weekday()
                current_date = current_date + timedelta(days=days_to_monday)
            
            # Create appointments for each selected weekday
            for day in recurring_days:
                # Skip if the day is a weekend (5=Saturday, 6=Sunday)
                if day >= 5:
                    continue
                    
                # Skip the original appointment date
                if week == 0 and day == start_weekday:
                    continue
                
                # Calculate the date for this weekday in the current week
                if week == 0:
                    # Special handling for first week
                    if day < start_weekday:
                        # This day already passed in the first week
                        continue
                    day_date = start_date + timedelta(days=(day - start_weekday))
                else:
                    # For subsequent weeks, calculate from Monday
                    day_date = current_date + timedelta(days=day)
                
                # Create a new service for this date
                new_service = models.Service(
                    patient_id=parent_service.patient_id,
                    service_type=parent_service.service_type,
                    service_date=day_date,
                    service_time=parent_service.service_time,
                    sheet_type=parent_service.sheet_type,
                    is_recurring=False,  # Children aren't themselves recurring
                    parent_service_id=parent_service.id
                )
                
                db.add(new_service)
                db.flush()  # Get ID without committing
                created_services.append(new_service.id)
    
    # For monthly recurrence
    elif recurring_type == 'monthly' and months_count > 0:
        current_month = start_date.month
        current_year = start_date.year
        day_of_month = start_date.day
        
        # Loop through the number of months
        for i in range(1, months_count + 1):  # Start from 1 to skip the original month
            # Calculate the next month
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
            
            # Check if the day exists in this month
            month_days = calendar.monthrange(current_year, current_month)[1]
            if day_of_month > month_days:
                continue  # Skip months where the day doesn't exist
            
            # Create the date for the same day in the next month
            next_date = date(current_year, current_month, day_of_month)
            
            # Skip weekends
            if next_date.weekday() >= 5:  # Saturday or Sunday
                continue
            
            # Create a new service for this date
            new_service = models.Service(
                patient_id=parent_service.patient_id,
                service_type=parent_service.service_type,
                service_date=next_date,
                service_time=parent_service.service_time,
                sheet_type=parent_service.sheet_type,
                is_recurring=False,  # Children aren't themselves recurring
                parent_service_id=parent_service.id
            )
            
            db.add(new_service)
            db.flush()  # Get ID without committing
            created_services.append(new_service.id)
    
    # Commit all new services
    if created_services:
        db.commit()
        
    return created_services

def add_attendance_week(db: Session, patient_id: int, attendance_data: schemas.AttendanceWeekCreate):
    """Create attendance entries for a full week with selected days"""
    created_services = []
    
    # Calculate dates for the selected days
    for day_offset in attendance_data.selected_days:
        service_date = attendance_data.week_start_date + timedelta(days=day_offset)
        
        # Create a service entry for each selected day
        service = schemas.ServiceCreate(
            service_type=attendance_data.service_type,
            service_date=service_date,
            service_time=attendance_data.service_time,
            sheet_type="attendance",
            service_category="attendance",
            week_start_date=attendance_data.week_start_date,
            attended=True,  # Mark selected days as attended
            is_recurring=False,
            recurring_pattern=None,
            recurring_end_date=None,
            parent_service_id=None
        )
        
        db_service = add_service_entry(db, patient_id, service)
        created_services.append(db_service)
    
    return created_services

def get_attendance_services(db: Session, patient_id: int = None, service_type: str = None, week_start: date = None):
    """Get attendance-based services with optional filters"""
    query = db.query(models.Service).filter(models.Service.service_category == "attendance")
    
    if patient_id:
        query = query.filter(models.Service.patient_id == patient_id)
    if service_type:
        query = query.filter(models.Service.service_type == service_type)
    if week_start:
        query = query.filter(models.Service.week_start_date == week_start)
    
    return query.order_by(models.Service.service_date).all()

def get_appointment_services(db: Session, patient_id: int = None, service_type: str = None):
    """Get appointment-based services with optional filters"""
    query = db.query(models.Service).filter(models.Service.service_category == "appointment")
    
    if patient_id:
        query = query.filter(models.Service.patient_id == patient_id)
    if service_type:
        query = query.filter(models.Service.service_type == service_type)
    
    return query.order_by(models.Service.service_date, models.Service.service_time).all()