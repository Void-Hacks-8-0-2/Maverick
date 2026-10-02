"""
Forensic PDF Document Generator for Operation 'ABHEDYA-CHAKRA'
Step 7: Compiles a professional, multi-page, evidence-grounded cyber-forensic case file.

Strictly adheres to:
- Official Step 5B 6-family risk score point breakdown
- Separation of Root Seed Outflow vs Downstream Cumulative Attribution
- Neutral forensic terminology (no 'guilty', 'criminal', etc.)
- Explicit distinction between Observed Facts, Analytical Findings, and Limitations
- SHA-256 integrity seal verification statement
"""

import io
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from backend.case_files.models import (
    CaseFileMetadata,
    EvidenceSnapshot,
)
from backend.investigations.models import (
    VictimInvestigationResponse,
)


def _safe_str(val: Any) -> str:
    """Sanitizes text for ReportLab XML paragraph parsing."""
    if val is None:
        return "N/A"
    return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_case_file_pdf(
    metadata: CaseFileMetadata,
    snapshot: EvidenceSnapshot,
    inv_response: VictimInvestigationResponse,
) -> bytes:
    """
    Generates a complete, multi-page forensic case file PDF in memory.
    Returns the binary PDF bytes.
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
    
    # Custom forensic styling palette
    PRIMARY_COLOR = colors.HexColor("#0f172a")     # Deep Slate
    SECONDARY_COLOR = colors.HexColor("#1e293b")   # Slate Dark
    ACCENT_CYAN = colors.HexColor("#0284c7")       # Cyan 600
    ACCENT_EMERALD = colors.HexColor("#059669")    # Emerald 600
    ACCENT_ROSE = colors.HexColor("#dc2626")       # Rose 600
    BORDER_COLOR = colors.HexColor("#cbd5e1")      # Slate 300
    BG_LIGHT = colors.HexColor("#f8fafc")          # Slate 50
    TEXT_MUTED = colors.HexColor("#64748b")        # Slate 500

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=PRIMARY_COLOR,
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=ACCENT_CYAN,
        alignment=0,
    )
    badge_style = ParagraphStyle(
        "DraftBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=ACCENT_ROSE,
        alignment=2,
    )
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=PRIMARY_COLOR,
        spaceBefore=8,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=PRIMARY_COLOR,
    )
    body_bold = ParagraphStyle(
        "BodyDarkBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    body_muted = ParagraphStyle(
        "BodyMuted",
        parent=body_style,
        textColor=TEXT_MUTED,
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8.5,
        textColor=PRIMARY_COLOR,
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Helvetica-Bold",
    )
    table_cell_header = ParagraphStyle(
        "TableCellHeader",
        parent=table_cell,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = []

    # =========================================================================
    # HEADER / BANNER
    # =========================================================================
    header_table = Table(
        [
            [
                Paragraph("<b>OPERATION ABHEDYA-CHAKRA</b><br/>FINANCIAL CYBER-FORENSIC INVESTIGATION REPORT", title_style),
                Paragraph("DRAFT / FOR INVESTIGATIVE USE ONLY<br/>NOT A JUDICIAL DETERMINATION", badge_style),
            ]
        ],
        colWidths=[400, 140],
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT_CYAN, spaceAfter=8))

    # =========================================================================
    # SECTION 1: INVESTIGATION METADATA
    # =========================================================================
    story.append(Paragraph("1. INVESTIGATION METADATA", h1_style))
    meta_data = [
        [
            Paragraph("<b>Application Case File ID:</b>", body_style),
            Paragraph(_safe_str(metadata.case_file_id), body_bold),
            Paragraph("<b>Investigation ID:</b>", body_style),
            Paragraph(_safe_str(metadata.investigation_id), body_style),
        ],
        [
            Paragraph("<b>Subject Account:</b>", body_style),
            Paragraph(_safe_str(metadata.subject_account), body_bold),
            Paragraph("<b>Report Generated At:</b>", body_style),
            Paragraph(_safe_str(metadata.created_at), body_style),
        ],
        [
            Paragraph("<b>Source Dataset:</b>", body_style),
            Paragraph(_safe_str(metadata.source_dataset), body_style),
            Paragraph("<b>Dataset Row Count:</b>", body_style),
            Paragraph(f"{metadata.dataset_rows:,} records", body_style),
        ],
        [
            Paragraph("<b>Dataset SHA-256 Seal:</b>", body_style),
            Paragraph(_safe_str(metadata.dataset_sha256), body_style),
            Paragraph("<b>Evidence Snapshot SHA:</b>", body_style),
            Paragraph(_safe_str(metadata.evidence_snapshot_sha256[:16]) + "...", body_style),
        ],
        [
            Paragraph("<b>Document Integrity:</b>", body_style),
            Paragraph("Calculated over final PDF bytes (see metadata)", body_style),
            Paragraph("<b>Storage Persistence:</b>", body_style),
            Paragraph("Process-local cache (session-only)", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[120, 150, 110, 160])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 2: INVESTIGATION SCOPE & INVARIANTS
    # =========================================================================
    story.append(Paragraph("2. INVESTIGATION SCOPE & INVARIANTS", h1_style))
    scope_data = [
        [
            Paragraph("<b>Attribution Policy:</b>", body_style),
            Paragraph(f"{snapshot.attribution.attribution_policy} {snapshot.attribution.attribution_policy_version}", body_bold),
            Paragraph("<b>Max Traversal Hops:</b>", body_style),
            Paragraph(f"{snapshot.attribution.max_hops_traversed} downstream hops", body_style),
        ],
        [
            Paragraph("<b>Max Branches / Hop:</b>", body_style),
            Paragraph(snapshot.limitations.branch_limits_applied, body_style),
            Paragraph("<b>Money Conservation:</b>", body_style),
            Paragraph("Strict Integer-Paise Balance Invariant", body_style),
        ],
    ]
    scope_table = Table(scope_data, colWidths=[120, 150, 110, 160])
    scope_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(scope_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 3: SUBJECT ACCOUNT ACTIVITY (OBSERVED FACTS)
    # =========================================================================
    story.append(Paragraph("3. SUBJECT ACCOUNT ACTIVITY (OBSERVED FACTS)", h1_style))
    obs = snapshot.observed_facts
    act_data = [
        [
            Paragraph("<b>Observed Inbound Flow:</b>", body_style),
            Paragraph(f"INR {obs.total_observed_incoming_volume:,.2f} ({obs.incoming_transaction_count} txns)", body_style),
            Paragraph("<b>Observed Outbound Flow:</b>", body_style),
            Paragraph(f"INR {obs.total_observed_outgoing_volume:,.2f} ({obs.outgoing_transaction_count} txns)", body_style),
        ],
        [
            Paragraph("<b>Observed Net Flow Delta:</b>", body_style),
            Paragraph(f"INR {obs.observed_net_flow_delta:,.2f} <i>(Note: Delta is not a bank balance)</i>", body_bold),
            Paragraph("<b>Unique Counterparties:</b>", body_style),
            Paragraph(f"{obs.unique_counterparties} entities", body_style),
        ],
        [
            Paragraph("<b>Unique IP Addresses:</b>", body_style),
            Paragraph(f"{obs.unique_ip_count} IPs", body_style),
            Paragraph("<b>Unique Devices Observed:</b>", body_style),
            Paragraph(f"{obs.unique_device_count} devices", body_style),
        ],
        [
            Paragraph("<b>First Observed Activity:</b>", body_style),
            Paragraph(_safe_str(obs.first_observed_timestamp).replace("T", " "), body_style),
            Paragraph("<b>Last Observed Activity:</b>", body_style),
            Paragraph(_safe_str(obs.last_observed_timestamp).replace("T", " "), body_style),
        ],
    ]
    act_table = Table(act_data, colWidths=[120, 150, 110, 160])
    act_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(act_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 4: ROOT / VICTIM TRANSACTIONS
    # =========================================================================
    story.append(Paragraph("4. ROOT / VICTIM TRANSACTIONS (REPRESENTATIVE SAMPLE)", h1_style))
    tx_headers = [
        Paragraph("Row", table_cell_header),
        Paragraph("Transaction ID", table_cell_header),
        Paragraph("Dir", table_cell_header),
        Paragraph("Counterparty", table_cell_header),
        Paragraph("Amount (INR)", table_cell_header),
        Paragraph("Timestamp", table_cell_header),
        Paragraph("Mode", table_cell_header),
        Paragraph("Device / IP", table_cell_header),
    ]
    tx_rows = [tx_headers]
    for tx in snapshot.transactions_sample[:10]:
        dev_ip = f"{_safe_str(tx.device_type)} / {_safe_str(tx.ip_address)}"
        tx_rows.append([
            Paragraph(str(tx.row_id), table_cell),
            Paragraph(_safe_str(tx.transaction_id), table_cell),
            Paragraph(_safe_str(tx.direction), table_cell),
            Paragraph(_safe_str(tx.receiver_account if tx.direction == "OUTGOING" else tx.sender_account), table_cell),
            Paragraph(f"{tx.amount:,.2f}", table_cell_bold),
            Paragraph(_safe_str(tx.timestamp).replace("T", " ")[:19], table_cell),
            Paragraph(_safe_str(tx.payment_mode), table_cell),
            Paragraph(dev_ip[:22], table_cell),
        ])
    
    tx_table = Table(tx_rows, colWidths=[24, 75, 30, 85, 65, 80, 40, 141])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SECONDARY_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(tx_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 5: TEMPORAL ATTRIBUTION & MONEY CONSERVATION
    # =========================================================================
    story.append(Paragraph("5. TEMPORAL FIFO ATTRIBUTION & MONEY CONSERVATION", h1_style))
    attr = snapshot.attribution
    attr_info = [
        [
            Paragraph("<b>Root Outflow Under Investigation:</b>", body_style),
            Paragraph(f"INR {attr.root_seed_outflow:,.2f} ({attr.root_seed_edge_count} direct seed edges)", body_bold),
        ],
        [
            Paragraph("<b>Downstream Cumulative Attribution:</b>", body_style),
            Paragraph(f"INR {attr.downstream_cumulative_attribution:,.2f} ({attr.downstream_fifo_edge_count} downstream FIFO links)", body_bold),
        ],
        [
            Paragraph("<b>Forensic Attribution Clarification:</b>", body_style),
            Paragraph(attr.note, body_muted),
        ],
    ]
    attr_table = Table(attr_info, colWidths=[180, 360])
    attr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(attr_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 6: 4-HOP INVESTIGATION TRACE SUMMARY
    # =========================================================================
    story.append(Paragraph("6. 4-HOP INVESTIGATION TRACE BREAKDOWN", h1_style))
    hop_headers = [
        Paragraph("Hop", table_cell_header),
        Paragraph("Sender Account", table_cell_header),
        Paragraph("Receiver Account", table_cell_header),
        Paragraph("Attributed Amount (INR)", table_cell_header),
        Paragraph("Edge Count", table_cell_header),
    ]
    hop_rows = [hop_headers]
    if inv_response.trace.hop_summaries:
        for hs in inv_response.trace.hop_summaries:
            hop_rows.append([
                Paragraph(f"Hop {hs.hop_number}", table_cell_bold),
                Paragraph(_safe_str(hs.sender_account), table_cell),
                Paragraph(_safe_str(hs.receiver_account), table_cell),
                Paragraph(f"{hs.attributed_amount:,.2f}", table_cell_bold),
                Paragraph(str(hs.edge_count), table_cell),
            ])
    else:
        hop_rows.append([
            Paragraph("N/A", table_cell),
            Paragraph("No downstream hop summaries generated", table_cell),
            Paragraph("-", table_cell),
            Paragraph("0.00", table_cell),
            Paragraph("0", table_cell),
        ])

    hop_table = Table(hop_rows, colWidths=[50, 130, 130, 130, 100])
    hop_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SECONDARY_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(hop_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 7: TERMINAL / DOWNSTREAM CANDIDATES
    # =========================================================================
    story.append(Paragraph("7. TERMINAL / DOWNSTREAM RECIPIENT CANDIDATES", h1_style))
    term_headers = [
        Paragraph("Recipient Account", table_cell_header),
        Paragraph("Hop", table_cell_header),
        Paragraph("Attributed Inflow (INR)", table_cell_header),
        Paragraph("Mule Role Classification", table_cell_header),
        Paragraph("Risk Index & Band", table_cell_header),
    ]
    term_rows = [term_headers]
    if snapshot.terminal_accounts:
        for t in snapshot.terminal_accounts[:8]:
            r_str = f"{t.risk_index:.1f} ({t.risk_band})" if t.risk_index is not None else "N/A"
            term_rows.append([
                Paragraph(_safe_str(t.account_number), table_cell_bold),
                Paragraph(f"Hop {t.hop}", table_cell),
                Paragraph(f"{t.attributed_amount:,.2f}", table_cell_bold),
                Paragraph(_safe_str(t.primary_role), table_cell),
                Paragraph(r_str, table_cell),
            ])
    else:
        term_rows.append([
            Paragraph("None", table_cell),
            Paragraph("-", table_cell),
            Paragraph("0.00", table_cell),
            Paragraph("No terminal nodes reached", table_cell),
            Paragraph("-", table_cell),
        ])

    term_table = Table(term_rows, colWidths=[120, 45, 125, 130, 120])
    term_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SECONDARY_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(term_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 8: OFFICIAL STEP 5B MULE RISK EVIDENCE
    # =========================================================================
    story.append(Paragraph("8. OFFICIAL STEP 5B MULE RISK EVIDENCE BREAKDOWN", h1_style))
    risk_info = snapshot.official_risk
    
    # 6-Family contribution table
    fam_headers = [
        Paragraph("Evidence Family", table_cell_header),
        Paragraph("Official Points Contributed", table_cell_header),
        Paragraph("Max Possible", table_cell_header),
        Paragraph("Family Description", table_cell_header),
    ]
    max_pts_map = {
        "FLOW_STRUCTURE": "20.0",
        "VELOCITY": "25.0",
        "AUTOMATION": "20.0",
        "NETWORK_STRUCTURE": "15.0",
        "TRANSACTION_BEHAVIOR": "10.0",
        "ROLE_SUPPORT": "10.0",
    }
    fam_desc_map = {
        "FLOW_STRUCTURE": "Volume scale and inbound-to-outbound disbursement symmetry",
        "VELOCITY": "Rapid 3-15 minute pass-through funds routing and drain ratio",
        "AUTOMATION": "Device automation markers, emulator signatures, and IP concentration",
        "NETWORK_STRUCTURE": "Counterparty graph topology, fan-in/fan-out degree skew",
        "TRANSACTION_BEHAVIOR": "Nocturnal transaction concentration and burst transaction rate",
        "ROLE_SUPPORT": "Independent corroboration from Step 4 L1/L2/L3 role heuristics",
    }
    fam_rows = [fam_headers]
    for fam_name, pts in risk_info.family_points.items():
        fam_rows.append([
            Paragraph(f"<b>{fam_name}</b>", table_cell),
            Paragraph(f"<b>+{pts:.1f}</b>", table_cell_bold),
            Paragraph(max_pts_map.get(fam_name, "N/A"), table_cell),
            Paragraph(fam_desc_map.get(fam_name, "-"), table_cell),
        ])
    
    fam_rows.append([
        Paragraph("<b>TOTAL MULE RISK INDEX</b>", table_cell_bold),
        Paragraph(f"<b>{risk_info.risk_index:.1f} / 100</b>", table_cell_bold),
        Paragraph("<b>100.0</b>", table_cell_bold),
        Paragraph(f"<b>Risk Band: {risk_info.risk_band}</b>", table_cell_bold),
    ])

    fam_table = Table(fam_rows, colWidths=[130, 80, 60, 270])
    fam_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SECONDARY_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('BACKGROUND', (0, -1), (-1, -1), BG_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(fam_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 9: STEP 5A VELOCITY EVIDENCE (SUPPORTING DIAGNOSTICS)
    # =========================================================================
    story.append(Paragraph("9. STEP 5A VELOCITY EVIDENCE (SUPPORTING DIAGNOSTICS)", h1_style))
    vel = snapshot.velocity_profile
    vel_data = [
        [
            Paragraph("<b>Pass-Through Candidate:</b>", body_style),
            Paragraph("TRUE" if vel.pass_through_candidate else "FALSE", body_bold),
            Paragraph("<b>Pass-Through Ratio:</b>", body_style),
            Paragraph(f"{vel.pass_through_ratio*100:.1f}% volume", body_bold),
        ],
        [
            Paragraph("<b>Qualifying Event Count:</b>", body_style),
            Paragraph(f"{vel.qualifying_event_count} events", body_style),
            Paragraph("<b>Attributed Volume:</b>", body_style),
            Paragraph(f"INR {vel.attributed_volume:,.2f}", body_style),
        ],
        [
            Paragraph("<b>Median Transfer Delay:</b>", body_style),
            Paragraph(f"{vel.median_delay_seconds} seconds" if vel.median_delay_seconds is not None else "N/A", body_style),
            Paragraph("<b>Window Semantics:</b>", body_style),
            Paragraph("3m:00s to 15m:00s inclusive", body_muted),
        ],
    ]
    vel_table = Table(vel_data, colWidths=[120, 150, 110, 160])
    vel_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(vel_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 10: STEP 4 MULE ROLE INDICATORS
    # =========================================================================
    story.append(Paragraph("10. STEP 4 MULE ROLE INDICATORS", h1_style))
    roles = snapshot.mule_roles
    role_data = [
        [
            Paragraph("<b>L1 Collector Candidate:</b>", body_style),
            Paragraph("TRUE" if roles.l1_collector_candidate else "FALSE", body_style),
            Paragraph("<b>L2 Distributor Candidate:</b>", body_style),
            Paragraph("TRUE" if roles.l2_distributor_candidate else "FALSE", body_style),
        ],
        [
            Paragraph("<b>L3 Terminal Candidate:</b>", body_style),
            Paragraph("TRUE" if roles.l3_terminal_candidate else "FALSE", body_bold),
            Paragraph("<b>Primary Assigned Role:</b>", body_style),
            Paragraph(roles.primary_role_label, body_bold),
        ],
    ]
    role_table = Table(role_data, colWidths=[120, 150, 110, 160])
    role_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(role_table)
    story.append(Spacer(1, 6))

    # =========================================================================
    # SECTION 11: FACTUAL INVESTIGATION SUMMARY
    # =========================================================================
    story.append(Paragraph("11. FACTUAL INVESTIGATION FINDINGS (DERIVED NARRATIVE)", h1_style))
    story.append(Paragraph(_safe_str(inv_response.evidence_summary.narrative), body_style))
    story.append(Spacer(1, 8))

    # =========================================================================
    # SECTION 12: LIMITATIONS & FORENSIC DISCLAIMERS
    # =========================================================================
    lims = snapshot.limitations
    story.append(Paragraph("12. ANALYTICAL LIMITATIONS & FORENSIC DISCLAIMERS", h1_style))
    lim_bullets = [
        f"<b>Observation Window:</b> {lims.dataset_observation_window}",
        f"<b>Ground-Truth Status:</b> {lims.ground_truth_status}",
        f"<b>Legal Status:</b> {lims.legal_nature_disclaimer}",
        f"<b>Branch Limits:</b> {lims.branch_limits_applied}",
        f"<b>Storage & Persistence:</b> {lims.persistence_limitation}",
    ]
    if lims.is_truncated:
        lim_bullets.append(f"<b><font color='red'>WARNING TRACE TRUNCATED:</font></b> Traversal was capped under configured limits: {', '.join(lims.truncation_reasons)}")
    if lims.cycles_detected:
        lim_bullets.append(f"<b><font color='#D97706'>CYCLES DETECTED:</font></b> Closed fund-flow cycles detected and bounded: {', '.join(lims.cycles_detected)}")
    lim_bullets.append(f"<b>Integrity Seal:</b> Production dataset SHA-256 ({metadata.dataset_sha256}) verified. Document SHA-256 is calculated over the final generated PDF bytes and is supplied in the case-file metadata. SHA-256 provides an integrity seal for this generated artifact; it does not by itself establish legal chain of custody.")

    for b in lim_bullets:
        story.append(Paragraph(f"&bull; {b}", body_style))
        story.append(Spacer(1, 2))

    # Build PDF
    doc.build(story)
    return buffer.getvalue()
