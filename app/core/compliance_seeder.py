import json
import os
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from app.models.compliance import ComplianceFramework, ComplianceRequirement, RiskLevel
from app.core.database import SessionLocal

def seed_compliance_data(db: Optional[Session] = None):
    """
    Seeds the database with all compliance framework and requirements found in the compliance directory.
    Fails startup if seeding fails.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    try:
        # Search for all requirement json files in the compliance subdirectories
        compliance_dir = "compliance"
        requirement_files = []
        for root, dirs, files in os.walk(compliance_dir):
            for file in files:
                if file.endswith("requirements.json"):
                    requirement_files.append(os.path.join(root, file))

        if not requirement_files:
            raise RuntimeError(f"Seeding failed: No requirements files found in {compliance_dir}")

        for requirements_path in requirement_files:
            with open(requirements_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            framework_data = data.get("framework")
            requirements_list = data.get("requirements", [])

            if not framework_data or not requirements_list:
                print(f"Skipping invalid structure in {requirements_path}")
                continue

            # Seed Framework
            framework = db.query(ComplianceFramework).filter(
                ComplianceFramework.name == framework_data["name"],
                ComplianceFramework.version == framework_data["version"]
            ).first()

            if not framework:
                framework = ComplianceFramework(
                    name=framework_data["name"],
                    version=framework_data["version"],
                    effective_date=date.fromisoformat(framework_data["effective_date"]),
                    description=f"Automated seed for {framework_data['name']} {framework_data['version']}"
                )
                db.add(framework)
                db.flush() # Get ID

            # Seed Requirements
            for req_data in requirements_list:
                existing = db.query(ComplianceRequirement).filter(
                    ComplianceRequirement.requirement_id == req_data["requirement_id"]
                ).first()

                if not existing:
                    requirement = ComplianceRequirement(
                        framework_id=framework.id,
                        requirement_id=req_data["requirement_id"],
                        section_ref=req_data["section_ref"],
                        title=req_data["title"],
                        requirement_text=req_data["requirement_text"],
                        risk_level=RiskLevel(req_data["risk_level"])
                    )
                    db.add(requirement)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"CRITICAL: Compliance seeding failed: {str(e)}")
        raise e
    finally:
        if should_close:
            db.close()

def validate_compliance_readiness():
    """
    Ensures that compliance requirements are loaded in the database.
    """
    db = SessionLocal()
    try:
        count = db.query(ComplianceRequirement).count()
        if count == 0:
             raise RuntimeError("System integrity error: Compliance requirements table is empty.")
    finally:
        db.close()
