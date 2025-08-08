# unlock_admin.py
"""
Unlock the 'admin' account and reset failed login attempts in the database.
Run this script in your project environment.
"""
from database import SessionLocal
import models

def unlock_admin():
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if admin:
            # Reset lock and failed attempts
            if hasattr(admin, "is_locked"):
                admin.is_locked = False
            if hasattr(admin, "failed_login_attempts"):
                admin.failed_login_attempts = 0
            # Reset password to demo password
            from auth import get_password_hash
            admin.hashed_password = get_password_hash("SpectrumAdmin2024!")
            db.commit()
            print("✅ Admin account unlocked, failed attempts reset, and password set to 'SpectrumAdmin2024!'.")
        else:
            print("❌ Admin user not found.")
    finally:
        db.close()

if __name__ == "__main__":
    unlock_admin()
