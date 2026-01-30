import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.compliance import ComplianceRequirement, ComplianceFramework, RiskLevel
from datetime import date

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

# For testing with SQLite, we need to use JSON instead of JSONB
# This is handled automatically by SQLAlchemy's type coercion

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(db):
    user = User(
        email="test_tester@example.com",
        hashed_password=get_password_hash("testpassword"),
        role="USER"
    )
    db.add(user)
    db.commit()
    return user

@pytest.fixture(scope="function")
def user_token_headers(client, test_user):
    login_data = {
        "username": "test_tester@example.com",
        "password": "testpassword",
    }
    r = client.post("/api/v1/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    return {"Authorization": f"Bearer {a_token}"}

@pytest.fixture(scope="function")
def seeded_requirements(db):
    """Seed test database with DPDP requirements."""
    framework = ComplianceFramework(
        name="DPDP",
        version="2023",
        effective_date=date(2023, 8, 11),
        description="Test framework"
    )
    db.add(framework)
    db.flush()
    
    requirements = [
        ComplianceRequirement(
            framework_id=framework.id,
            requirement_id="DPDP_6_1",
            section_ref="Section 6(1)",
            title="Valid Consent Before Processing",
            requirement_text="The Data Fiduciary must obtain consent.",
            risk_level=RiskLevel.HIGH
        ),
        ComplianceRequirement(
            framework_id=framework.id,
            requirement_id="DPDP_8_7",
            section_ref="Section 8(7)",
            title="Erasure of Personal Data",
            requirement_text="Data must be erased upon withdrawal.",
            risk_level=RiskLevel.HIGH
        )
    ]
    for req in requirements:
        db.add(req)
    db.commit()
    return requirements
