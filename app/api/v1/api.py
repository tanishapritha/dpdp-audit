from fastapi import APIRouter
from app.api.v1.endpoints import auth, upload, status, report, frameworks

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(frameworks.router, prefix="/frameworks", tags=["frameworks"])
api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(status.router, tags=["status"])
api_router.include_router(report.router, tags=["report"])
