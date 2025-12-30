from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if user already exists
    email = "test@example.com"
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        user = User(
            email=email,
            hashed_password=get_password_hash("password123"),
            role=UserRole.USER
        )
        db.add(user)
        db.commit()
        print(f"Created user: {email} with password: password123")
    else:
        print(f"User {email} already exists")
    
    db.close()

if __name__ == "__main__":
    seed_db()
