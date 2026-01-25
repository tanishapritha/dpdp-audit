from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import engine, Base
from app.core.compliance_seeder import seed_compliance_data, validate_compliance_readiness

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For MVP we allow all, should be restricted in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    """
    Seed compliance data and validate system readiness on startup.
    Application will fail to start if compliance requirements are not loaded.
    """
    try:
        seed_compliance_data()
        validate_compliance_readiness()
        print("✓ Compliance framework initialized successfully")
    except Exception as e:
        print(f"✗ FATAL: Application startup failed: {str(e)}")
        raise e

@app.get("/")
async def root():
    return {"message": "Company Compliance Engine API is running"}
