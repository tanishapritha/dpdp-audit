import json
import os
from typing import Dict, Any, Optional
from fpdf import FPDF
from datetime import datetime

class AuditExporter:
    """
    Internal utility class for exporting frozen audit snapshots.
    Supports machine-readable JSON and human-readable PDF.
    """

    @staticmethod
    def to_json(snapshot: Dict[str, Any], output_path: str):
        """Exports the complete audit snapshot to a JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

    @classmethod
    def to_pdf(cls, snapshot: Dict[str, Any], output_path: str):
        """Generates a human-friendly audit report in PDF format."""
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "Compliance Audit Report", ln=True, align="C")
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 6, f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", ln=True, align="C")
        pdf.ln(10)

        # Engine Information
        engine = snapshot.get("engine", {})
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, "1. Engine Metadata", ln=True)
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 6, f"Engine Name: {engine.get('name')}", ln=True)
        pdf.cell(0, 6, f"Engine Version: {engine.get('version')}", ln=True)
        pdf.cell(0, 6, f"Audit ID: {snapshot.get('audit_id')}", ln=True)
        pdf.cell(0, 6, f"Snapshot Fingerprint: {snapshot.get('fingerprint')[:16]}...", ln=True)
        pdf.ln(5)

        # Framework Information
        framework = snapshot.get("framework", {})
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, "2. Regulatory Framework", ln=True)
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 6, f"Framework: {framework.get('name')}", ln=True)
        pdf.cell(0, 6, f"Version: {framework.get('version')}", ln=True)
        pdf.cell(0, 6, f"Effective Date: {framework.get('effective_date')}", ln=True)
        pdf.ln(5)

        # Results Summary
        results = snapshot.get("results", {})
        verdict = results.get("overall_verdict", "UNKNOWN")
        
        # Color coding for verdict
        if verdict == "GREEN":
            pdf.set_text_color(0, 128, 0)
        elif verdict == "RED":
            pdf.set_text_color(255, 0, 0)
        else:
            pdf.set_text_color(218, 165, 32) # GoldenRod

        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, f"OVERALL VERDICT: {verdict}", ln=True)
        pdf.set_text_color(0, 0, 0) # Reset color
        
        pdf.ln(10)

        # Requirement Breakdown
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, "3. Detailed Requirement Assessment", ln=True)
        pdf.ln(2)

        for req in results.get("requirements", []):
            pdf.set_font("helvetica", "B", 10)
            status = req.get("status")
            pdf.cell(0, 6, f"Requirement ID: {req.get('requirement_id')} [{status}]", ln=True)
            
            pdf.set_font("helvetica", "I", 9)
            pdf.multi_cell(0, 5, f"Reasoning: {req.get('reasoning')}")
            
            if req.get("evidence_quote"):
                pdf.set_font("helvetica", "", 8)
                pdf.set_fill_color(240, 240, 240)
                pdf.multi_cell(0, 5, f"Evidence: \"{req.get('evidence_quote')}\"", fill=True)
                pdf.cell(0, 5, f"Page(s): {', '.join(map(str, req.get('page_numbers', [])))}", ln=True)
            
            pdf.ln(4)
            if pdf.get_y() > 250:
                pdf.add_page()

        # Integrity footer
        pdf.set_y(-15)
        pdf.set_font("helvetica", "I", 8)
        pdf.cell(0, 10, f"Internal Audit Trail Document - Fingerprint: {snapshot.get('fingerprint')}", align="C")

        pdf.output(output_path)
