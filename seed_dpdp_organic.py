
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.compliance import ComplianceFramework, ComplianceRequirement, RiskLevel
from datetime import datetime
import uuid

def seed_dpdp():
    db = SessionLocal()
    try:
        # Check if DPDP exists
        fw = db.query(ComplianceFramework).filter(ComplianceFramework.name == "Digital Personal Data Protection Act 2023").first()
        if not fw:
            print("Creating DPDP Framework...")
            fw = ComplianceFramework(
                id=uuid.uuid4(),
                name="Digital Personal Data Protection Act 2023",
                version="1.0",
                effective_date=datetime(2023, 8, 11),
                description="The primary legislation governing personal data protection in India."
            )
            db.add(fw)
            db.commit()
            print(f"Created Framework: {fw.id}")
        else:
            print(f"Framework exists: {fw.id}")

            # Clean existing requirements to ensure no GDPR pollution
            db.query(ComplianceRequirement).filter(ComplianceRequirement.framework_id == fw.id).delete()
            db.commit()
            print("Purged old requirements.")

        # Seed DPDP Requirements
        reqs = [
            {
                "id": "DPDP-R-01", 
                "title": "Grounds for Processing", 
                "section": "Section 4", 
                "text": "Personal data may only be processed for a lawful purpose for which the Data Principal has given consent or for certain legitimate uses.",
                "risk": RiskLevel.HIGH
            },
            {
                "id": "DPDP-R-02", 
                "title": "Notice Requirement", 
                "section": "Section 5", 
                "text": "A request for consent must be accompanied or preceded by a notice informing the Data Principal of the personal data to be collected and the purpose of processing.",
                "risk": RiskLevel.HIGH
            },
            {
                "id": "DPDP-R-03", 
                "title": "Consent Framework", 
                "section": "Section 6", 
                "text": "Consent given by the Data Principal shall be free, specific, informed, unconditional, and unambiguous with a clear affirmative action.",
                "risk": RiskLevel.CRITICAL if hasattr(RiskLevel, 'CRITICAL') else RiskLevel.HIGH
            },
            {
                "id": "DPDP-R-04", 
                "title": "Right to Withdraw Consent", 
                "section": "Section 6(4)", 
                "text": "The Data Principal shall have the right to withdraw consent at any time, with the ease of doing so being comparable to giving consent.",
                "risk": RiskLevel.HIGH
            },
            {
                "id": "DPDP-R-05", 
                "title": "Data Accuracy", 
                "section": "Section 8(1)", 
                "text": "Data Fiduciaries must ensure the completeness, accuracy, and consistency of personal data if it is used to make a decision that affects the Data Principal.",
                "risk": RiskLevel.MEDIUM
            },
            {
                "id": "DPDP-R-06", 
                "title": "Data Retention", 
                "section": "Section 8(7)", 
                "text": "Data Fiduciaries must erase personal data upon the Data Principal withdrawing consent or as soon as the purpose for processing is no longer served.",
                "risk": RiskLevel.HIGH
            },
            {
                "id": "DPDP-R-07", 
                "title": "Personal Data Breach", 
                "section": "Section 8(6)", 
                "text": "In the event of a personal data breach, the Data Fiduciary shall intimate the Board and each affected Data Principal in such form and manner as may be prescribed.",
                "risk": RiskLevel.HIGH
            },
            {
                "id": "DPDP-R-08", 
                "title": "Grievance Redressal", 
                "section": "Section 10(1)", 
                "text": "A Data Fiduciary shall establish an effective mechanism to redress the grievances of Data Principals.",
                "risk": RiskLevel.MEDIUM
            }
        ]

        for r in reqs:
            req_obj = ComplianceRequirement(
                id=uuid.uuid4(),
                framework_id=fw.id,
                requirement_id=r["id"],
                title=r["title"],
                section_ref=r["section"],
                requirement_text=r["text"],
                risk_level=r["risk"]
            )
            db.add(req_obj)
        
        db.commit()
        print(f"✅ Seeded {len(reqs)} DPDP Requirements.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_dpdp()
