import pytest
from uuid import uuid4
from app.services.audit_snapshotter import AuditSnapshotter
from app.schemas.agents import RequirementAssessment
from datetime import datetime

class TestAuditDefensibility:
    """
    Tests for Phase 4: Audit Defensibility features.
    """

    def test_snapshot_creation_and_integrity(self):
        """Tests that frozen snapshots are created with valid integrity hashes."""
        audit_id = uuid4()
        framework = {"name": "Test Framework", "version": "1.0", "effective_date": "2024-01-01"}
        assessments = [
            RequirementAssessment(
                requirement_id="REQ_1",
                status="COMPLIANT",
                confidence=0.9,
                evidence_quote="This is the evidence text.",
                reasoning="Explicitly mentioned.",
                page_numbers=[1]
            )
        ]
        
        snapshot = AuditSnapshotter.create_frozen_snapshot(
            audit_id=audit_id,
            framework_metadata=framework,
            assessments=assessments,
            overall_verdict="GREEN",
            execution_trace={}
        )

        assert snapshot["audit_id"] == str(audit_id)
        assert snapshot["framework"]["name"] == "Test Framework"
        assert len(snapshot["results"]["requirements"]) == 1
        assert snapshot["results"]["requirements"][0]["evidence_hash"] is not None
        assert "fingerprint" in snapshot
        
        # Verify integrity
        assert AuditSnapshotter.verify_integrity(snapshot) is True

    def test_integrity_failure_on_evidence_mutation(self):
        """Tests that evidence mutation invalidates the snapshot integrity."""
        audit_id = uuid4()
        assessments = [
            RequirementAssessment(
                requirement_id="REQ_1",
                status="COMPLIANT",
                confidence=0.9,
                evidence_quote="Original evidence",
                reasoning="Reasoning",
                page_numbers=[1]
            )
        ]
        
        snapshot = AuditSnapshotter.create_frozen_snapshot(
            audit_id=audit_id,
            framework_metadata={"name": "F"},
            assessments=assessments,
            overall_verdict="GREEN",
            execution_trace={}
        )

        # Mutate evidence quote in the snapshot
        snapshot["results"]["requirements"][0]["evidence_quote"] = "MUTATED evidence"
        
        # Integrity should fail
        assert AuditSnapshotter.verify_integrity(snapshot) is False

    @pytest.mark.asyncio
    async def test_multi_framework_seeding(self, db):
        """Tests that the seeder correctly loads multiple frameworks."""
        from app.core.compliance_seeder import seed_compliance_data
        from app.models.compliance import ComplianceFramework
        
        # Seed all frameworks using the test database session
        seed_compliance_data(db=db)
        
        frameworks = db.query(ComplianceFramework).all()
        fw_names = [fw.name for fw in frameworks]
        
        assert "DPDP" in fw_names
        assert "GDPR-Lite" in fw_names
        assert len(frameworks) >= 2
