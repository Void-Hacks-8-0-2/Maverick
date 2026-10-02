"""
Step 9: Deterministic Legal Document Templates
Operation 'ABHEDYA-CHAKRA'
"""

from typing import List, Dict, Any
from backend.legal_freeze.models import (
    LegalDocumentType,
    LegalDraftDocument,
    LegalEvidenceSnapshot,
    OfficerDetails,
)


def build_legal_draft_document(
    doc_type: LegalDocumentType,
    evidence: LegalEvidenceSnapshot,
    officer: OfficerDetails,
) -> LegalDraftDocument:
    """
    Renders structured deterministic sections and plain text for the requested document type.
    """
    if doc_type == LegalDocumentType.ACCOUNT_FREEZE_REQUEST:
        return _template_freeze_request(evidence, officer)
    elif doc_type == LegalDocumentType.RECORD_PRESERVATION_REQUEST:
        return _template_preservation_request(evidence, officer)
    elif doc_type == LegalDocumentType.BANK_INFORMATION_REQUISITION:
        return _template_bank_requisition(evidence, officer)
    elif doc_type == LegalDocumentType.EVIDENCE_ANNEXURE:
        return _template_evidence_annexure(evidence, officer)
    else:
        raise ValueError(f"Unsupported document type: {doc_type}")


# ===========================================================================
# 1. ACCOUNT FREEZE / HOLD REQUEST DRAFT
# ===========================================================================

def _template_freeze_request(
    evidence: LegalEvidenceSnapshot,
    officer: OfficerDetails,
) -> LegalDraftDocument:
    subj = evidence.subject_account
    risk = evidence.risk
    role = evidence.roles
    vel = evidence.velocity
    attr = evidence.attribution

    sections: List[Dict[str, Any]] = [
        {
            "id": "statutory_framework",
            "heading": "Statutory Authority & Enabling Framework",
            "content": (
                "Statutory Empowering Provision: Requisition issued under Section 94 and Section 106 of the Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS) "
                "(applicable to proceedings/FIRs registered on or after 1 July 2024), or the corresponding legacy provisions of Section 91 and Section 102 of the Code of Criminal Procedure, 1973 (CrPC) "
                "(applicable to proceedings instituted prior to 1 July 2024 pursuant to the Section 531 BNSS savings clause), for the production of documents/records and temporary preservation of suspected proceeds of cyber-enabled financial crime.\n"
                "Operational Status: DRAFT NOTICE — SUBJECT TO INDEPENDENT REVIEW, JURISDICTIONAL VERIFICATION, AND EXECUTION BY AUTHORIZED INVESTIGATING OFFICER PRIOR TO SERVICE UPON NODAL BANK."
            ),
        },
        {
            "id": "authority",
            "heading": "1. Requesting Authority & Investigating Officer",
            "content": (
                f"Agency / Unit: {officer.requesting_authority}\n"
                f"Investigating Officer: {officer.officer_name}\n"
                f"Designation: {officer.officer_designation}\n"
                f"Police Station / Jurisdiction: {officer.police_station}\n"
                f"Recipient Financial Institution: {officer.recipient_bank}\n"
                f"Branch / Nodal Officer: {officer.recipient_branch}"
            ),
        },
        {
            "id": "case_reference",
            "heading": "2. Official Reference & Incident Details",
            "content": (
                f"Case / Crime Reference No.: {officer.case_reference}\n"
                f"Cyber Crime Incident Ack No.: {officer.incident_reference}\n"
                f"Internal Forensic Case File ID: {evidence.case_file_id or '[NOT LINKED]'}\n"
                f"Internal Case Diary ID: {evidence.case_diary_id or '[NOT LINKED]'}"
            ),
        },
        {
            "id": "subject_account",
            "heading": "3. Subject Account Details",
            "content": (
                f"Target Account Number: {subj.account_number}\n"
                f"Associated IFSC Codes: {', '.join(subj.associated_ifscs) if subj.associated_ifscs else '[NOT OBSERVED]'}\n"
                f"Observed Activity Window: {subj.first_observed_timestamp or 'N/A'} to {subj.last_observed_timestamp or 'N/A'}\n"
                f"Observed Incoming Volume: INR {subj.observed_inflow:,.2f} ({subj.incoming_transaction_count} transactions)\n"
                f"Observed Outgoing Volume: INR {subj.observed_outflow:,.2f} ({subj.outgoing_transaction_count} transactions)\n"
                f"Observed Net Flow Delta: INR {subj.observed_net_flow_delta:,.2f} (Note: {subj.disclaimer})"
            ),
        },
        {
            "id": "basis_of_request",
            "heading": "4. Factual Basis of Request (Investigative Indicators)",
            "content": (
                f"Cyber-forensic analysis of transaction flows identified the following verified indicators:\n"
                f"a) Mule Risk Index: {risk.risk_index:.1f}/100 ({risk.risk_band} band) evaluated under analytical model {risk.scoring_version}.\n"
                f"b) Behavioral Role Classification: Identified as an investigative candidate for {role.primary_role_label} "
                f"with observed fan-in of {role.fan_in} and fan-out of {role.fan_out}.\n"
                f"c) Velocity Analysis: Pass-through candidate status = {vel.pass_through_candidate}. "
                f"Qualifying 3-15 min rapid pass-through events: {vel.qualifying_event_count} "
                f"with attributed volume of INR {vel.attributed_volume:,.2f}.\n"
                f"d) Multi-Hop Attribution: Direct root outflow of INR {attr.root_seed_outflow:,.2f} exiting the subject account, "
                f"propagating across {attr.max_hops_traversed} downstream hop(s) terminating in {attr.terminal_accounts_count} identified candidate account(s).\n"
                f"Statement: These factual observations are forensic indicators derived from analytical accounting models, "
                f"and do not constitute an independent judicial determination of criminal liability."
            ),
        },
        {
            "id": "requested_action",
            "heading": "5. Requested Action",
            "content": (
                f"Request for appropriate review and, where legally authorized, temporary restriction/hold/preservation "
                f"of debit activity associated with account number {subj.account_number} pending further lawful investigation.\n\n"
                f"Specific Action: {officer.requested_action}"
            ),
        },
        {
            "id": "relevant_transactions",
            "heading": "6. Verified Transaction Schedule (Sample of Observed Records)",
            "content": _format_transactions_table_text(evidence.transactions_sample),
        },
        {
            "id": "attribution_summary",
            "heading": "7. Multi-Hop Fund Attribution Summary",
            "content": (
                f"Attribution Policy: {attr.attribution_policy} ({attr.attribution_policy_version})\n"
                f"Direct Root Seed Outflow: INR {attr.root_seed_outflow:,.2f} ({attr.root_seed_edge_count} direct edges)\n"
                f"Downstream Cumulative Attribution: INR {attr.downstream_cumulative_attribution:,.2f} ({attr.downstream_fifo_edge_count} hops)\n"
                f"Maximum Traversed Hops: {attr.max_hops_traversed}\n"
                f"Terminal Downstream Accounts: {attr.terminal_accounts_count}\n"
                f"Conservation Note: {attr.conservation_note}"
            ),
        },
        {
            "id": "evidence_integrity",
            "heading": "8. Forensic Evidence Integrity Seals",
            "content": (
                f"Production Dataset: {evidence.dataset_name} ({evidence.dataset_rows:,} rows)\n"
                f"Dataset SHA-256: {evidence.dataset_sha256}\n"
                f"Evidence Snapshot SHA-256: {evidence.evidence_snapshot_sha256}\n"
                f"PDF integrity SHA-256 is supplied in the associated document metadata/package record."
            ),
        },
        {
            "id": "authorization",
            "heading": "9. Review & Authorization (To Be Executed by Competent Officer)",
            "content": (
                f"Prepared By: {officer.officer_name} ({officer.officer_designation})\n"
                f"Police Station / Agency: {officer.police_station}\n\n"
                f"Signature of Investigating Officer: __________________________    Date: ____________\n\n"
                f"Signature of Authorizing / Supervisory Officer: ________________    Date: ____________\n"
                f"Official Seal / Stamp:"
            ),
        },
    ]

    title = f"ACCOUNT FREEZE / HOLD REQUEST DRAFT — {subj.account_number}"
    plain_text = _assemble_plain_text(title, sections)

    return LegalDraftDocument(
        title=title,
        document_type=LegalDocumentType.ACCOUNT_FREEZE_REQUEST,
        sections=sections,
        plain_text_content=plain_text,
    )


# ===========================================================================
# 2. RECORD PRESERVATION REQUEST DRAFT
# ===========================================================================

def _template_preservation_request(
    evidence: LegalEvidenceSnapshot,
    officer: OfficerDetails,
) -> LegalDraftDocument:
    subj = evidence.subject_account

    sections: List[Dict[str, Any]] = [
        {
            "id": "authority",
            "heading": "1. Requesting Officer & Agency",
            "content": (
                f"Agency / Cyber Crime Unit: {officer.requesting_authority}\n"
                f"Officer Name: {officer.officer_name}\n"
                f"Designation: {officer.officer_designation}\n"
                f"Police Station: {officer.police_station}\n"
                f"Recipient Institution: {officer.recipient_bank} ({officer.recipient_branch})"
            ),
        },
        {
            "id": "case_reference",
            "heading": "2. Crime & Incident Reference",
            "content": (
                f"Case Reference: {officer.case_reference}\n"
                f"Cyber Incident Reference: {officer.incident_reference}"
            ),
        },
        {
            "id": "subject_account",
            "heading": "3. Subject Account Details",
            "content": (
                f"Account Number: {subj.account_number}\n"
                f"Observed Activity Window: {subj.first_observed_timestamp or 'N/A'} to {subj.last_observed_timestamp or 'N/A'}\n"
                f"Observed Transaction Count: {subj.incoming_transaction_count + subj.outgoing_transaction_count}\n"
                f"Known IFSC Codes: {', '.join(subj.associated_ifscs) if subj.associated_ifscs else '[NOT OBSERVED]'}\n"
                f"Known IP Addresses: {', '.join(subj.associated_ips[:5]) if subj.associated_ips else '[NOT OBSERVED]'}"
            ),
        },
        {
            "id": "preservation_request",
            "heading": "4. Scope of Records Requested for Preservation",
            "content": (
                f"Please preserve, subject to applicable statutory authority and institutional retention policies, "
                f"all records, electronic logs, and documents relating to account number {subj.account_number}.\n\n"
                f"Preservation Period: {officer.preservation_period}\n\n"
                f"Categories of Records:\n"
                + "\n".join(f"- {cat}" for cat in officer.requested_record_categories)
            ),
        },
        {
            "id": "basis",
            "heading": "5. Basis of Preservation Notice",
            "content": (
                f"The subject account has been identified in connection with rapid multi-hop fund flows "
                f"exhibiting an observed Mule Risk Index of {evidence.risk.risk_index:.1f}/100 ({evidence.risk.risk_band}). "
                f"Immediate preservation of digital and transactional audit trails is requested to prevent data spoliation "
                f"pending formal judicial process."
            ),
        },
        {
            "id": "integrity",
            "heading": "6. Forensic Integrity Reference",
            "content": (
                f"Evidence Snapshot SHA-256: {evidence.evidence_snapshot_sha256}\n"
                f"Dataset SHA-256: {evidence.dataset_sha256}\n"
                f"PDF integrity SHA-256 is supplied in the associated document metadata/package record."
            ),
        },
        {
            "id": "authorization",
            "heading": "7. Officer Verification & Endorsement",
            "content": (
                f"Officer Name: {officer.officer_name}\n"
                f"Signature: __________________________    Date: ____________\n"
                f"Official Stamp / Seal:"
            ),
        },
    ]

    title = f"RECORD PRESERVATION REQUEST DRAFT — {subj.account_number}"
    plain_text = _assemble_plain_text(title, sections)

    return LegalDraftDocument(
        title=title,
        document_type=LegalDocumentType.RECORD_PRESERVATION_REQUEST,
        sections=sections,
        plain_text_content=plain_text,
    )


# ===========================================================================
# 3. BANK INFORMATION REQUISITION DRAFT
# ===========================================================================

def _template_bank_requisition(
    evidence: LegalEvidenceSnapshot,
    officer: OfficerDetails,
) -> LegalDraftDocument:
    subj = evidence.subject_account

    sections: List[Dict[str, Any]] = [
        {
            "id": "recipient",
            "heading": "1. Recipient Bank / Nodal Officer",
            "content": (
                f"To: The Nodal Officer / Law Enforcement Liaison Cell\n"
                f"Bank / Financial Institution: {officer.recipient_bank}\n"
                f"Branch: {officer.recipient_branch}"
            ),
        },
        {
            "id": "issuing_officer",
            "heading": "2. Issuing Officer & Investigation Unit",
            "content": (
                f"From: {officer.officer_name}, {officer.officer_designation}\n"
                f"Agency / Station: {officer.police_station} ({officer.requesting_authority})\n"
                f"Case Reference: {officer.case_reference}\n"
                f"Cyber Incident Reference: {officer.incident_reference}"
            ),
        },
        {
            "id": "subject_account",
            "heading": "3. Subject Account Identification",
            "content": (
                f"Target Account Number: {subj.account_number}\n"
                f"Associated IFSC: {', '.join(subj.associated_ifscs) if subj.associated_ifscs else '[NOT OBSERVED]'}\n"
                f"Relevant Observation Period: {subj.first_observed_timestamp or 'N/A'} to {subj.last_observed_timestamp or 'N/A'}"
            ),
        },
        {
            "id": "requisition_items",
            "heading": "4. Requisition Checklist of Information Required",
            "content": (
                f"In furtherance of lawful investigation, certified copies of the following information "
                f"are requested in respect of account number {subj.account_number}:\n\n"
                + "\n".join(f"[  ] {idx+1}. {cat}" for idx, cat in enumerate(officer.requested_record_categories))
                + "\n\nNote: Do NOT assume or fabricate account-holder identities. Provide authentic certified bank master records."
            ),
        },
        {
            "id": "sample_transactions",
            "heading": "5. Relevant Observed Transactions for Cross-Verification",
            "content": _format_transactions_table_text(evidence.transactions_sample[:10]),
        },
        {
            "id": "authorization",
            "heading": "6. Requisition Signature & Notice",
            "content": (
                f"This requisition is issued as an investigative draft subject to review and execution "
                f"under applicable statutory powers by an authorized officer.\n\n"
                f"Officer Signature: __________________________    Date: ____________\n"
                f"Designation: {officer.officer_designation}\n"
                f"Office Seal:"
            ),
        },
    ]

    title = f"BANK INFORMATION REQUISITION DRAFT — {subj.account_number}"
    plain_text = _assemble_plain_text(title, sections)

    return LegalDraftDocument(
        title=title,
        document_type=LegalDocumentType.BANK_INFORMATION_REQUISITION,
        sections=sections,
        plain_text_content=plain_text,
    )


# ===========================================================================
# 4. EVIDENCE ANNEXURE DRAFT
# ===========================================================================

def _template_evidence_annexure(
    evidence: LegalEvidenceSnapshot,
    officer: OfficerDetails,
) -> LegalDraftDocument:
    subj = evidence.subject_account
    risk = evidence.risk
    role = evidence.roles
    vel = evidence.velocity
    attr = evidence.attribution

    # Format risk families
    risk_fam_lines = [f"- {k}: {v:.1f} pts" for k, v in risk.family_contributions.items()]
    risk_fam_str = "\n".join(risk_fam_lines) if risk_fam_lines else "None recorded"

    # Format terminals
    term_lines = [
        f"- Hop {t['hop']}: Account {t['account_number']} (Role: {t['primary_role']}, Attributed: INR {t['attributed_amount']:,.2f}, Risk: {t['risk_index']:.1f})"
        for t in attr.terminal_accounts_sample[:10]
    ]
    term_str = "\n".join(term_lines) if term_lines else "No terminal endpoints identified in closed window."

    sections: List[Dict[str, Any]] = [
        {
            "id": "annexure_header",
            "heading": "Annexure Header & Linkages",
            "content": (
                f"Subject Account: {subj.account_number}\n"
                f"Case Reference: {officer.case_reference}\n"
                f"Linked Case File ID: {evidence.case_file_id or '[NOT LINKED]'}\n"
                f"Linked Case Diary ID: {evidence.case_diary_id or '[NOT LINKED]'}\n"
                f"Investigating Unit: {officer.police_station} ({officer.requesting_authority})"
            ),
        },
        {
            "id": "section_a",
            "heading": "Section A — Subject Account Profile & Observed Activity",
            "content": (
                f"Account Number: {subj.account_number}\n"
                f"Observation Period: {subj.first_observed_timestamp or 'N/A'} to {subj.last_observed_timestamp or 'N/A'}\n"
                f"Total Observed Inflow: INR {subj.observed_inflow:,.2f} ({subj.incoming_transaction_count} txs)\n"
                f"Total Observed Outflow: INR {subj.observed_outflow:,.2f} ({subj.outgoing_transaction_count} txs)\n"
                f"Observed Net Flow Delta: INR {subj.observed_net_flow_delta:,.2f}\n"
                f"Unique Counterparties: {subj.unique_counterparties}\n"
                f"Unique IP Addresses: {subj.unique_ip_count}\n"
                f"Unique Device Types: {subj.unique_device_count}\n"
                f"Observed Payment Modes: {', '.join(subj.payment_modes)}"
            ),
        },
        {
            "id": "section_b",
            "heading": "Section B — Step 5B Mule Risk Index & Exact 6-Family Contributions",
            "content": (
                f"Official Mule Risk Index: {risk.risk_index:.1f}/100\n"
                f"Assigned Risk Band: {risk.risk_band}\n"
                f"Model Version: {risk.scoring_version}\n"
                f"Family Score Breakdown:\n{risk_fam_str}\n"
                f"Triggered Reason Codes: {', '.join(risk.reason_codes) if risk.reason_codes else 'None'}"
            ),
        },
        {
            "id": "section_c",
            "heading": "Section C — Step 4 Mule Role Classification",
            "content": (
                f"Primary Role Label: {role.primary_role_label}\n"
                f"Layer 1 Collector Candidate: {role.l1_collector_candidate}\n"
                f"Layer 2 Distributor Candidate: {role.l2_distributor_candidate}\n"
                f"Layer 3 Terminal/Cash-Out Candidate: {role.l3_terminal_candidate}\n"
                f"Fan-in: {role.fan_in} | Fan-out: {role.fan_out}\n"
                f"Classification Triggers: {', '.join(role.classification_reasons) if role.classification_reasons else 'None'}"
            ),
        },
        {
            "id": "section_d",
            "heading": "Section D — Step 5A Rapid Pass-Through Velocity Analysis",
            "content": (
                f"Pass-Through Candidate: {vel.pass_through_candidate}\n"
                f"Pass-Through Ratio: {vel.pass_through_ratio:.3f}\n"
                f"Qualifying Pass-Through Events: {vel.qualifying_event_count}\n"
                f"Attributed Rapid Volume: INR {vel.attributed_volume:,.2f}\n"
                f"Outgoing Qualifying Count: {vel.outgoing_qualifying_count}\n"
                f"Median Turnaround Delay: {f'{vel.median_delay_seconds:.1f} seconds' if vel.median_delay_seconds is not None else 'N/A'}\n"
                f"Window Definition: {vel.window_description} ({vel.classification_version})"
            ),
        },
        {
            "id": "section_e",
            "heading": "Section E — Verified Root Transactions Schedule",
            "content": _format_transactions_table_text(evidence.transactions_sample),
        },
        {
            "id": "section_f",
            "heading": "Section F — Step 5C Multi-Hop FIFO Fund Attribution",
            "content": (
                f"Attribution Policy: {attr.attribution_policy} ({attr.attribution_policy_version})\n"
                f"Root Seed Outflow (Direct exits from subject): INR {attr.root_seed_outflow:,.2f}\n"
                f"Downstream Cumulative Attribution: INR {attr.downstream_cumulative_attribution:,.2f}\n"
                f"Hops Traversed: {attr.max_hops_traversed}\n"
                f"Trace Truncated: {attr.is_truncated} (Reasons: {', '.join(attr.truncation_reasons) if attr.truncation_reasons else 'None'})\n"
                f"Cycles Detected: {', '.join(attr.cycles_detected) if attr.cycles_detected else 'None'}\n"
                f"Conservation Note: {attr.conservation_note}"
            ),
        },
        {
            "id": "section_g",
            "heading": "Section G — Downstream Terminal Accounts",
            "content": (
                f"Total Terminal Accounts Reached: {attr.terminal_accounts_count}\n"
                f"Sample of Reached Terminal Accounts:\n{term_str}"
            ),
        },
        {
            "id": "section_h",
            "heading": "Section H — Cryptographic Integrity & Dataset Provenance",
            "content": (
                f"Production Dataset: {evidence.dataset_name} ({evidence.dataset_rows:,} rows)\n"
                f"Dataset SHA-256: {evidence.dataset_sha256}\n"
                f"Evidence Snapshot SHA-256: {evidence.evidence_snapshot_sha256}\n"
                f"Provenance Chain: {evidence.provenance_chain}\n"
                f"PDF integrity SHA-256 is supplied in the associated document metadata/package record."
            ),
        },
        {
            "id": "section_i",
            "heading": "Section I — Investigative Limitations & Disclaimer",
            "content": (
                "1. Closed Observation Window: Analysis is bounded within the 15-day closed dataset window (2,000,000 transactions).\n"
                "2. Non-Judicial Determination: Analytical models (Mule Risk Index, Temporal FIFO Attribution, and Role Classification) "
                "provide structured investigative indicators. They do NOT constitute judicial proof of beneficial ownership or legal guilt.\n"
                "3. In-Memory Persistence: Legal draft metadata and generated artifacts are maintained in process-local storage and "
                "are not persistent across backend restarts.\n"
                "4. Officer Discretion: This annexure is a draft document compiled for authorized officer review."
            ),
        },
    ]

    title = f"SUPPORTING EVIDENCE ANNEXURE — {subj.account_number}"
    plain_text = _assemble_plain_text(title, sections)

    return LegalDraftDocument(
        title=title,
        document_type=LegalDocumentType.EVIDENCE_ANNEXURE,
        sections=sections,
        plain_text_content=plain_text,
    )


# ===========================================================================
# Helpers
# ===========================================================================

def _format_transactions_table_text(txs: List[Any]) -> str:
    if not txs:
        return "No transactions observed."
    lines = [
        f"{'TX ID':<16} | {'Timestamp':<19} | {'Sender':<12} | {'Receiver':<12} | {'Amount (INR)':>12} | {'Mode':<6} | {'Dir':<8}",
        "-" * 95,
    ]
    for t in txs:
        amt_str = f"{t.amount:,.2f}"
        lines.append(
            f"{t.transaction_id[:16]:<16} | {t.timestamp[:19]:<19} | {t.sender_account[:12]:<12} | "
            f"{t.receiver_account[:12]:<12} | {amt_str:>12} | {t.payment_mode[:6]:<6} | {t.direction:<8}"
        )
    return "\n".join(lines)


def _assemble_plain_text(title: str, sections: List[Dict[str, Any]]) -> str:
    lines = [
        "=" * 80,
        "OPERATION \"ABHEDYA-CHAKRA\" — FINANCIAL CYBER-FORENSICS INVESTIGATION",
        "DRAFT — SUBJECT TO INVESTIGATOR AND LEGAL AUTHORITY REVIEW",
        "=" * 80,
        "",
        title,
        "-" * len(title),
        "",
    ]
    for s in sections:
        lines.append(s["heading"])
        lines.append("-" * len(s["heading"]))
        lines.append(s["content"])
        lines.append("")
    return "\n".join(lines)
