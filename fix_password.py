
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def change_password():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "test@example.com").first()
        if user:
            print(f"Found user {user.email}.")
            new_hash = get_password_hash("wordpass321")
            user.hashed_password = new_hash
            db.commit()
            print("✅ Password updated to 'wordpass321'")
        else:
            print("User not found.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    change_password()
