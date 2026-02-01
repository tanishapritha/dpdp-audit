
import json
import uuid
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.audit import PolicyAudit, AuditStatus
from app.models.user import User

def diagnostic_run():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "test@example.com").first()
        if not user:
            print("User not found, run seed first")
            return

        # Create a mock completed audit
        audit_id = uuid.uuid4()
        mock_report = {
            "snapshot_version": "1.0",
            "results": {
                "overall_verdict": "YELLOW",
                "requirements": [
                    {
                        "requirement_id": "DPDP-R-01",
                        "status": "PARTIAL",
                        "reasoning": "Notice is mentioned but missing retention period.",
                        "evidence_quote": "We collect data for processing.",
                        "page_numbers": [2]
                    }
                ]
            },
            "timestamp": "2026-01-30T22:00:00Z"
        }

        audit = PolicyAudit(
            id=audit_id,
            filename="diag_test.pdf",
            owner_id=user.id,
            status=AuditStatus.COMPLETED,
            progress=1.0,
            report=mock_report
        )
        db.add(audit)
        db.commit()

        print(f"Created Mock Audit: {audit_id}")

        # Now simulate a GET to /report logic
        # (Copying logic from report.py)
        report_data = audit.report
        
        if "results" in report_data and "overall_verdict" in report_data["results"]:
            mapped_report = {
                "policy_id": audit.id,
                "filename": audit.filename,
                "evaluated_at": report_data.get("timestamp"),
                "overall_verdict": report_data["results"]["overall_verdict"],
                "requirements": [
                    {
                        "requirement_id": r["requirement_id"],
                        "status": r["status"],
                        "reason": r["reasoning"],
                        "evidence": [r["evidence_quote"]] if r.get("evidence_quote") else [],
                        "page_numbers": r.get("page_numbers", []),
                        #"metadata": r.get("metadata", {})
                    }
                    for r in report_data["results"]["requirements"]
                ]
            }
            print("\n--- DIAGNOSTIC JSON STRUCTURE ---")
            print(json.dumps(mapped_report, indent=4, default=str))
            print("----------------------------------")
            
            # Validation
            req = mapped_report["requirements"][0]
            assert "page_numbers" in req, "MISSING page_numbers"
            assert isinstance(req["evidence"], list), "evidence MUST BE LIST"
            print("✅ JSON Structure Validated for Frontend requirements.")

    finally:
        db.close()

if __name__ == "__main__":
    diagnostic_run()
