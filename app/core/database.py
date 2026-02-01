from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Enable Vector extension on startup
from sqlalchemy import text
from sqlalchemy import event

@event.listens_for(Base.metadata, "before_create")
def create_vector_extension(target, connection, **kw):
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
