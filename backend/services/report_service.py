"""
Report Service: Generates comprehensive JSON and professional PDF clinical documentation reports.
Uses ReportLab with high-density clinical layout, zero footer overlap, clean timestamps,
and robust text cell wrapping.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.pdfgen import canvas
from backend.database.db import get_record, get_record_audit_logs

REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports"))
os.makedirs(REPORTS_DIR, exist_ok=True)

def format_clean_timestamp(ts_str):
    """Format raw ISO timestamps (e.g. 2026-10-22T14:59:38.770939+00:00) into clean human-readable date."""
    if not ts_str or ts_str in ("N/A", "Pending Review", "Pending Approval"):
        return ts_str or "N/A"
    try:
        clean = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts_str[:19].replace("T", " ") + " UTC"

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for total page count and robust, non-colliding footers and running headers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()

        # Top Running Header (Pages > 1 or subtle on all)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, 756, 612 - 40, 756)

        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(40, 760, "FIELD-TO-RECORD • PRE-HOSPITAL CLINICAL ENCOUNTER SUMMARY")
        self.drawRightString(612 - 40, 760, "OFFICIAL FIRST RESPONDER CARE RECORD")

        # Bottom Divider Rule
        self.line(40, 36, 612 - 40, 36)

        # Footer Line 1: Left system name, Right page count
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawString(40, 24, "Field-to-Record Clinical Documentation Assistant")
        self.drawRightString(612 - 40, 24, f"Page {self._pageNumber} of {page_count}")

        # Footer Line 2: Legal/Clinical Disclaimer
        self.setFont("Helvetica-Bold", 6.5)
        self.setFillColor(colors.HexColor("#94a3b8"))
        disclaimer = "CONFIDENTIAL MEDICAL RECORD • DOCUMENTATION ASSISTANT ONLY • NOT AN AUTOMATED DIAGNOSTIC OR TREATMENT RECOMMENDATION"
        self.drawString(40, 14, disclaimer)

        self.restoreState()

class ReportService:

    @classmethod
    def generate_json_report(cls, record_id):
        """Build full structured JSON export."""
        record = get_record(record_id)
        if not record:
            return None

        audit_logs = get_record_audit_logs(record_id)

        report_payload = {
            "export_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "system": "Field-to-Record EMS Documentation Assistant",
                "system_version": "1.0.0",
                "notice": "Documentation assistant record. Not a diagnostic or treatment recommendation system."
            },
            "record": record,
            "audit_trail": audit_logs
        }
        return report_payload

    @classmethod
    def generate_pdf_report(cls, record_id, output_filename=None):
        """
        Generate an upgraded, professional clinical PDF report using ReportLab.
        Uses compact padding, elegant medical typography, and automatic cell wrapping.
        """
        record = get_record(record_id)
        if not record:
            return None

        if not output_filename:
            output_filename = f"report_{record_id}_{int(datetime.now().timestamp())}.pdf"

        pdf_path = os.path.join(REPORTS_DIR, output_filename)

        # Usable width: 612 - 80 = 532 pt
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            leftMargin=40,
            rightMargin=40,
            topMargin=42,
            bottomMargin=45
        )

        styles = getSampleStyleSheet()

        # Custom Typography
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=2
        )
        subtitle_style = ParagraphStyle(
            'DocSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0d9488"),
            spaceAfter=6
        )
        section_style = ParagraphStyle(
            'DocSection',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#0f766e"),
            spaceBefore=6,
            spaceAfter=3
        )
        narrative_style = ParagraphStyle(
            'DocNarrative',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b")
        )
        cell_bold = ParagraphStyle(
            'CellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#0f172a")
        )
        cell_regular = ParagraphStyle(
            'CellRegular',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#334155")
        )
        cell_italic = ParagraphStyle(
            'CellItalic',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#64748b")
        )
        header_cell = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9.5,
            textColor=colors.white
        )
        alert_style = ParagraphStyle(
            'DocAlert',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#991b1b")
        )

        elements = []

        # 1. Document Title & Subtitle Header
        elements.append(Paragraph("FIELD-TO-RECORD", title_style))
        elements.append(Paragraph("PRE-HOSPITAL CLINICAL ENCOUNTER SUMMARY", subtitle_style))

        # 2. Status Badge Coloring
        status_name = record.get("status", "Draft").upper()
        status_badge_bg = (
            "#dcfce7" if "APPROVED" in status_name else
            "#f3e8ff" if "AMENDED" in status_name else
            "#fef3c7" if "REVIEW" in status_name else "#f1f5f9"
        )
        status_badge_txt = (
            "#166534" if "APPROVED" in status_name else
            "#6b21a8" if "AMENDED" in status_name else
            "#92400e" if "REVIEW" in status_name else "#475569"
        )

        status_html = f'<font color="{status_badge_txt}"><b>{status_name}</b></font>'
        if record.get("version", 1) > 1:
            status_html += f' <font color="#6b21a8">(v{record["version"]})</font>'

        created_formatted = format_clean_timestamp(record.get("created_at"))
        approved_formatted = format_clean_timestamp(record.get("approved_at"))

        # Metadata Table (Width: 100 + 166 + 100 + 166 = 532 pt)
        meta_data = [
            [
                Paragraph("<b>RECORD ID:</b>", cell_bold),
                Paragraph(record["id"], cell_regular),
                Paragraph("<b>STATUS:</b>", cell_bold),
                Paragraph(status_html, cell_bold)
            ],
            [
                Paragraph("<b>INCIDENT / CALL #:</b>", cell_bold),
                Paragraph(record.get("call_number") or "N/A", cell_regular),
                Paragraph("<b>RESPONDER ID:</b>", cell_bold),
                Paragraph(record.get("responder_id") or "N/A", cell_regular)
            ],
            [
                Paragraph("<b>CREATED AT:</b>", cell_bold),
                Paragraph(created_formatted, cell_regular),
                Paragraph("<b>APPROVED AT:</b>", cell_bold),
                Paragraph(approved_formatted, cell_regular)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[90, 176, 90, 176])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 5))

        # 3. Field Narrative Transcript Section
        elements.append(Paragraph("Field Notes & Narrative Transcript", section_style))
        trans_text = record.get("corrected_transcript") or record.get("machine_transcript") or "[No transcript recorded]"
        narrative_box = Table(
            [[Paragraph(trans_text, narrative_style)]],
            colWidths=[532]
        )
        narrative_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(narrative_box)
        elements.append(Spacer(1, 5))

        # 4. Physiological Vital Signs Table (Width: 120 + 62 + 60 + 90 + 200 = 532)
        clinical_data = record.get("clinical_data", {})
        vitals = clinical_data.get("vital_signs", [])
        elements.append(Paragraph("Recorded Physiological Vital Signs", section_style))
        if vitals:
            v_rows = [[
                Paragraph("Vital Sign", header_cell),
                Paragraph("Reading", header_cell),
                Paragraph("Unit", header_cell),
                Paragraph("Verification", header_cell),
                Paragraph("Verbatim Source Evidence", header_cell)
            ]]
            for v in vitals:
                v_rows.append([
                    Paragraph(v.get("name", "Unknown"), cell_bold),
                    Paragraph(str(v.get("value", "")), cell_bold),
                    Paragraph(str(v.get("unit", "")).replace("°", "&deg;"), cell_regular),
                    Paragraph(v.get("verification_state", "Extracted"), cell_regular),
                    Paragraph(f"\"{v.get('source_phrase', '')}\"", cell_italic)
                ])
            v_table = Table(v_rows, colWidths=[120, 62, 60, 90, 200])
            v_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ('TOPPADDING', (0, 0), (-1, -1), 2.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ]))
            elements.append(v_table)
        else:
            elements.append(Paragraph("<i>No vital signs captured in encounter narrative.</i>", cell_italic))
        elements.append(Spacer(1, 5))

        # 5. Medications Administered & Assessed (Width: 110 + 72 + 65 + 115 + 80 + 90 = 532)
        meds = clinical_data.get("medications", [])
        elements.append(Paragraph("Medications Administered & Assessed", section_style))
        if meds:
            m_rows = [[
                Paragraph("Medication", header_cell),
                Paragraph("Dosage", header_cell),
                Paragraph("Route", header_cell),
                Paragraph("Clinical Status", header_cell),
                Paragraph("Verification", header_cell),
                Paragraph("Provenance", header_cell)
            ]]
            for m in meds:
                neg_html = (
                    '<font color="#b91c1c"><b>WITHHELD / DENIED</b></font>'
                    if m.get("is_negated") else
                    '<font color="#15803d"><b>ADMINISTERED</b></font>'
                )
                m_rows.append([
                    Paragraph(m.get("canonical_name", m.get("raw_mention", "Unknown")), cell_bold),
                    Paragraph(f"{m.get('dosage') or 'Unspecified'} {m.get('unit') or ''}".strip(), cell_regular),
                    Paragraph(m.get("route") or "Unspecified", cell_regular),
                    Paragraph(neg_html, cell_regular),
                    Paragraph(m.get("verification_state", "Extracted"), cell_regular),
                    Paragraph((m.get("provenance") or "Local Catalogue")[:28], cell_italic)
                ])
            m_table = Table(m_rows, colWidths=[110, 72, 65, 115, 80, 90])
            m_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d9488")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ('TOPPADDING', (0, 0), (-1, -1), 2.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ]))
            elements.append(m_table)
        else:
            elements.append(Paragraph("<i>No medications documented in encounter narrative.</i>", cell_italic))
        elements.append(Spacer(1, 5))

        # 6. Symptoms & Pre-Hospital Interventions (Width: 80 + 130 + 122 + 200 = 532)
        symptoms = clinical_data.get("symptoms", [])
        procedures = clinical_data.get("procedures", [])
        elements.append(Paragraph("Symptoms & Pre-Hospital Interventions", section_style))
        sp_rows = [[
            Paragraph("Category", header_cell),
            Paragraph("Finding / Intervention", header_cell),
            Paragraph("Assessment Status", header_cell),
            Paragraph("Source Phrase", header_cell)
        ]]
        for s in symptoms:
            neg_badge = (
                '<font color="#b91c1c"><b>DENIED (Pertinent Negative)</b></font>'
                if s.get("is_negated") else
                '<font color="#0f766e"><b>PRESENT / REPORTED</b></font>'
            )
            sp_rows.append([
                Paragraph("Symptom", cell_regular),
                Paragraph(s.get("symptom"), cell_bold),
                Paragraph(neg_badge, cell_regular),
                Paragraph(f"\"{s.get('source_phrase', '')}\"", cell_italic)
            ])
        for p in procedures:
            sp_rows.append([
                Paragraph("Procedure", cell_regular),
                Paragraph(p.get("procedure"), cell_bold),
                Paragraph("PERFORMED", cell_bold),
                Paragraph(f"\"{p.get('source_phrase', '')}\"", cell_italic)
            ])

        if symptoms or procedures:
            sp_table = Table(sp_rows, colWidths=[80, 130, 122, 200])
            sp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#334155")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ('TOPPADDING', (0, 0), (-1, -1), 2.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ]))
            elements.append(sp_table)
        else:
            elements.append(Paragraph("<i>No specific symptoms or procedures extracted.</i>", cell_italic))
        elements.append(Spacer(1, 5))

        # 7. Safety & Validation Warnings Audit (Width: 65 + 115 + 242 + 110 = 532)
        warnings = record.get("validation_warnings", [])
        elements.append(Paragraph("Safety & Validation Warnings Audit", section_style))
        if warnings:
            w_rows = [[
                Paragraph("Severity", header_cell),
                Paragraph("Category", header_cell),
                Paragraph("Description", header_cell),
                Paragraph("Resolution Status", header_cell)
            ]]
            for w in warnings:
                res_txt = "RESOLVED" if w.get("resolved") else "ACKNOWLEDGED / REVIEWED"
                w_rows.append([
                    Paragraph(w.get("severity", "WARNING"), cell_bold),
                    Paragraph(w.get("category", "General"), cell_regular),
                    Paragraph(w.get("message", ""), alert_style),
                    Paragraph(res_txt, cell_bold)
                ])
            w_table = Table(w_rows, colWidths=[65, 115, 242, 110])
            w_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#b91c1c")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff1f2")]),
                ('TOPPADDING', (0, 0), (-1, -1), 2.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ]))
            elements.append(w_table)
        else:
            elements.append(Paragraph("<i>All validation checks passed with zero unresolved warnings.</i>", cell_italic))
        elements.append(Spacer(1, 6))

        # 8. Chronological Event Timeline (Width: 120 + 172 + 240 = 532)
        elements.append(Paragraph("Clinical Encounter Timeline", section_style))
        time_rows = [
            [
                Paragraph("Milestone", header_cell),
                Paragraph("Timestamp (UTC)", header_cell),
                Paragraph("Context & System Details", header_cell)
            ],
            [
                Paragraph("Field Recording", cell_bold),
                Paragraph(format_clean_timestamp(record.get("recording_time") or record.get("created_at")), cell_regular),
                Paragraph("Field narrative audio input captured", cell_regular)
            ],
            [
                Paragraph("Speech-to-Text", cell_bold),
                Paragraph(format_clean_timestamp(record.get("transcription_time") or record.get("created_at")), cell_regular),
                Paragraph(f"Local Whisper ({record.get('transcription_metadata', {}).get('model_used', 'base')})", cell_regular)
            ],
            [
                Paragraph("Clinical Review", cell_bold),
                Paragraph(format_clean_timestamp(record.get("reviewed_at") or "Pending Review"), cell_regular),
                Paragraph("Clinician verified clinical entities & acknowledged checks", cell_regular)
            ],
            [
                Paragraph("Record Finalization", cell_bold),
                Paragraph(format_clean_timestamp(record.get("approved_at") or "Pending Approval"), cell_regular),
                Paragraph(f"Official status: {record.get('status')}", cell_regular)
            ]
        ]
        t_table = Table(time_rows, colWidths=[120, 172, 240])
        t_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#475569")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_table)
        elements.append(Spacer(1, 8))

        # 9. Attending First Responder Sign-off Box (Width: 352 + 180 = 532)
        sign_block = [
            [
                Paragraph("<b>Attending First Responder Signature / Sign-off:</b>", cell_bold),
                Paragraph("<b>Date & Time:</b>", cell_bold)
            ],
            [
                Paragraph(f"Signed by: <b>{record.get('responder_id', 'Paramedic')}</b> (Credential ID: Verified)", cell_regular),
                Paragraph(approved_formatted if approved_formatted != "N/A" else "____________________", cell_regular)
            ]
        ]
        s_table = Table(sign_block, colWidths=[352, 180])
        s_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(KeepTogether([s_table]))

        # Build document
        doc.build(elements, canvasmaker=NumberedCanvas)
        return pdf_path
