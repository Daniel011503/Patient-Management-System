# Create this as reset_admin.py and run it to fix the admin user

from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from passlib.context import CryptContext
from datetime import datetime

# Initialize password context with a different approach
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def reset_admin_user():
    """Reset the admin user with a new password hash"""
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Find the admin user
        admin_user = db.query(models.User).filter(models.User.username == "admin").first()
        
        if admin_user:
            print("Found existing admin user, updating password...")
            
            # Create a new password hash
            new_password = "SpectrumAdmin2024!"
            try:
                # Try to hash the password
                hashed_password = pwd_context.hash(new_password)
                print("✅ Password hashed successfully")
                
                # Update the user
                admin_user.hashed_password = hashed_password
                admin_user.updated_at = datetime.utcnow()
                
                db.commit()
                print("✅ Admin user password updated successfully!")
                print(f"Username: admin")
                print(f"Password: {new_password}")
                
            except Exception as hash_error:
                print(f"❌ Error hashing password: {hash_error}")
                
                # Fallback: Use a simple hash for testing
                import hashlib
                simple_hash = hashlib.sha256(new_password.encode()).hexdigest()
                admin_user.hashed_password = simple_hash
                db.commit()
                
                print("⚠️ Used simple hash as fallback")
                print("You'll need to update auth.py to use simple hash verification")
                
        else:
            print("No admin user found, creating new one...")
            
            # Create new admin user
            new_password = "SpectrumAdmin2024!"
            try:
                hashed_password = pwd_context.hash(new_password)
                
                new_admin = models.User(
                    username="admin",
                    email="admin@spectrumhealth.com",
                    full_name="System Administrator",
                    hashed_password=hashed_password,
                    role="admin",
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                
                db.add(new_admin)
                db.commit()
                
                print("✅ New admin user created successfully!")
                print(f"Username: admin")
                print(f"Password: {new_password}")
                
            except Exception as e:
                print(f"❌ Error creating admin user: {e}")
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        
    finally:
        db.close()

def test_password_verification():
    """Test if password verification is working"""
    
    password = "SpectrumAdmin2024!"
    
    try:
        # Test hashing
        hashed = pwd_context.hash(password)
        print(f"✅ Hashing test successful")
        
        # Test verification
        is_valid = pwd_context.verify(password, hashed)
        print(f"✅ Verification test: {is_valid}")
        
        return True
        
    except Exception as e:
        print(f"❌ Password test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Resetting admin user...")
    print("=" * 50)
    
    # First test if bcrypt is working
    print("Testing password hashing...")
    if test_password_verification():
        print("Password system is working, proceeding with reset...")
        reset_admin_user()
    else:
        print("❌ Password system is not working properly")
        print("Try installing a different bcrypt version:")
        print("pip uninstall bcrypt")
        print("pip install bcrypt==4.0.1")
        
    print("=" * 50)
    print("🏁 Script completed")