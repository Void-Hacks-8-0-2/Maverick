"""
Step 9: Legal Freeze PDF Document Generator
Operation 'ABHEDYA-CHAKRA'
"""

import io
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.legal_freeze.models import (
    LegalDraftDocument,
    LegalEvidenceSnapshot,
    OfficerDetails,
)


def _safe_str(val: Any) -> str:
    """Sanitizes text for ReportLab XML paragraph parsing."""
    if val is None:
        return "N/A"
    return (
        str(val)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def generate_legal_draft_pdf(
    doc_model: LegalDraftDocument,
    evidence: LegalEvidenceSnapshot,
    officer: OfficerDetails,
) -> bytes:
    """
    Compiles a clean, professional, multi-page legal draft PDF in memory.
    Returns binary PDF bytes.
    Does NOT embed its own final PDF hash (avoids circular hashing).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "LegalTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    header_super = ParagraphStyle(
        "HeaderSuper",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=2,
    )

    draft_alert_style = ParagraphStyle(
        "DraftAlert",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#b45309"),
        alignment=1,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=8,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "LegalBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )

    code_style = ParagraphStyle(
        "LegalCode",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#1e293b"),
    )

    footer_style = ParagraphStyle(
        "LegalFooter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#64748b"),
    )

    story: List[Any] = []

    # 1. Header Banner
    story.append(Paragraph(doc_model.header_notice, header_super))
    story.append(Paragraph(doc_model.title, title_style))
    story.append(Spacer(1, 2))

    # Draft Warning Box
    draft_banner = Table(
        [[Paragraph(doc_model.draft_notice, draft_alert_style)]],
        colWidths=[540],
    )
    draft_banner.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef3c7")),
            ("BORDER", (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(draft_banner)
    story.append(Spacer(1, 6))

    # Metadata Strip
    meta_data = [
        [
            Paragraph("<b>Subject Account:</b> " + _safe_str(evidence.subject_account.account_number), body_style),
            Paragraph("<b>Status:</b> REVIEW REQUIRED", body_style),
        ],
        [
            Paragraph("<b>Case Reference:</b> " + _safe_str(officer.case_reference), body_style),
            Paragraph("<b>Investigating Agency:</b> " + _safe_str(officer.requesting_authority), body_style),
        ],
        [
            Paragraph("<b>Evidence Seal SHA-256:</b> " + _safe_str(evidence.evidence_snapshot_sha256[:24]) + "...", code_style),
            Paragraph("<b>Dataset SHA-256:</b> " + _safe_str(evidence.dataset_sha256[:24]) + "...", code_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # 2. Render Structured Sections
    for s in doc_model.sections:
        story.append(Paragraph(s["heading"], section_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=4))

        # Check if this is a table or text
        content = s["content"]
        if "\n" in content:
            for line in content.split("\n"):
                if line.startswith("- "):
                    story.append(Paragraph("&bull; " + _safe_str(line[2:]), body_style))
                elif "|" in line:
                    story.append(Paragraph(_safe_str(line), code_style))
                else:
                    story.append(Paragraph(_safe_str(line), body_style))
        else:
            story.append(Paragraph(_safe_str(content), body_style))

        story.append(Spacer(1, 6))

    # 3. Transaction Table (if present)
    if evidence.transactions_sample:
        story.append(Spacer(1, 4))
        story.append(Paragraph("Verified Transaction Evidence Schedule", section_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=4))

        tx_rows = [["TX ID", "Timestamp", "Sender", "Receiver", "Amount (INR)", "Mode", "Dir"]]
        for t in evidence.transactions_sample[:15]:
            tx_rows.append([
                Paragraph(_safe_str(t.transaction_id[:12]), code_style),
                Paragraph(_safe_str(t.timestamp[:19]), code_style),
                Paragraph(_safe_str(t.sender_account[:10]), code_style),
                Paragraph(_safe_str(t.receiver_account[:10]), code_style),
                Paragraph(f"{t.amount:,.2f}", code_style),
                Paragraph(_safe_str(t.payment_mode[:6]), code_style),
                Paragraph(_safe_str(t.direction[:4]), code_style),
            ])

        tx_table = Table(tx_rows, colWidths=[80, 95, 75, 75, 75, 45, 35])
        tx_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
                ("TOPPADDING", (0, 0), (-1, 0), 3),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 1), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
            ])
        )
        story.append(tx_table)
        story.append(Spacer(1, 8))

    # 4. Mandatory Review and Statutory Disclaimer Block
    disclaimer_text = (
        "<b>LEGAL NATURE NOTICE:</b> This document is an investigative draft generated from verified analytical "
        "and transactional evidence. It does NOT constitute an issued legal order, freeze instruction, or judicial finding. "
        "Formal execution requires review, endorsement, and issuance by an authorized law-enforcement officer under "
        "applicable statutory powers.<br/>"
        "<b>DATASET INTEGRITY:</b> All factual observations are derived from production dataset "
        f"'{_safe_str(evidence.dataset_name)}' ({evidence.dataset_rows:,} rows, SHA-256: {_safe_str(evidence.dataset_sha256)}).<br/>"
        "<b>PDF HASH:</b> PDF integrity SHA-256 is supplied in the associated document metadata/package record."
    )
    disclaimer_box = Table(
        [[Paragraph(disclaimer_text, footer_style)]],
        colWidths=[540],
    )
    disclaimer_box.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(KeepTogether([disclaimer_box]))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
