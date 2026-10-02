"""
Step 9: Legal Freeze + Bank Requisition Draft Models
Operation 'ABHEDYA-CHAKRA'
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LegalDocumentType(str, Enum):
    """Supported legal/bank-request draft document types."""
    ACCOUNT_FREEZE_REQUEST = "ACCOUNT_FREEZE_REQUEST"
    RECORD_PRESERVATION_REQUEST = "RECORD_PRESERVATION_REQUEST"
    BANK_INFORMATION_REQUISITION = "BANK_INFORMATION_REQUISITION"
    EVIDENCE_ANNEXURE = "EVIDENCE_ANNEXURE"


class LegalDraftStatus(str, Enum):
    """Status lifecycle for legal draft documents."""
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    GENERATED = "GENERATED"
    FINALIZED = "FINALIZED"


class LegalDraftRequest(BaseModel):
    """Payload to generate a structured legal draft document."""
    subject_account: str = Field(..., description="Subject account number")
    document_type: LegalDocumentType = Field(
        LegalDocumentType.ACCOUNT_FREEZE_REQUEST,
        description="Type of legal draft to generate"
    )
    case_file_id: Optional[str] = Field(None, description="Linked Case File ID if existing")
    case_diary_id: Optional[str] = Field(None, description="Linked Case Diary ID if existing")
    max_hops: int = Field(4, ge=1, le=4, description="Attribution hop depth")
    horizon_seconds: Optional[int] = Field(None, description="Temporal horizon in seconds")
    max_branches_per_hop: int = Field(50, ge=1, le=500, description="Max branches per hop")
    
    # Officer and Case details (all optional, fallback to explicit placeholders)
    requesting_authority: Optional[str] = Field(None, description="Requesting Agency / Cyber Cell")
    officer_name: Optional[str] = Field(None, description="Investigating Officer Name")
    officer_designation: Optional[str] = Field(None, description="Officer Designation")
    police_station: Optional[str] = Field(None, description="Police Station / Cyber Crime Unit")
    case_reference: Optional[str] = Field(None, description="Crime Reference / Diary No.")
    incident_reference: Optional[str] = Field(None, description="National Cyber Crime Portal Ack No.")
    recipient_bank: Optional[str] = Field(None, description="Recipient Bank / Financial Institution")
    recipient_branch: Optional[str] = Field(None, description="Bank Branch / Nodal Officer")
    requested_action: Optional[str] = Field(None, description="Specific action requested")
    preservation_period: Optional[str] = Field(None, description="Record preservation period")
    requested_record_categories: Optional[List[str]] = Field(
        None, description="Categories of records requested in requisition"
    )
    investigator_notes: Optional[str] = Field(None, description="Officer operational notes")
    include_ai_narrative: bool = Field(False, description="Optionally include Step 8 AI narrative as annexure")


class OfficerDetails(BaseModel):
    """Normalized officer and authority details with guaranteed explicit placeholders."""
    officer_name: str
    officer_designation: str
    police_station: str
    requesting_authority: str
    case_reference: str
    incident_reference: str
    recipient_bank: str
    recipient_branch: str
    requested_action: str
    preservation_period: str
    requested_record_categories: List[str]
    investigator_notes: str


class SubjectAccountLegalEvidence(BaseModel):
    """Verified subject account data points."""
    account_number: str
    first_observed_timestamp: Optional[str]
    last_observed_timestamp: Optional[str]
    incoming_transaction_count: int
    outgoing_transaction_count: int
    observed_inflow: float
    observed_outflow: float
    observed_net_flow_delta: float
    unique_counterparties: int
    unique_ip_count: int
    unique_device_count: int
    payment_modes: List[str]
    associated_ifscs: List[str]
    associated_ips: List[str]
    disclaimer: str = (
        "Observed net flow delta is inflow minus outflow in the closed window, "
        "NOT a verified current bank balance."
    )


class VerifiedTransactionLegalItem(BaseModel):
    """Verified transaction item for legal document schedules."""
    transaction_id: str
    row_id: int
    timestamp: str
    sender_account: str
    receiver_account: str
    amount: float
    payment_mode: str
    sender_ifsc: str
    receiver_ifsc: str
    ip_address: str
    device_type: Optional[str] = None
    narration: str
    direction: str


class LegalRiskEvidence(BaseModel):
    """Step 5B Mule Risk Index evidence."""
    risk_index: float
    risk_band: str
    scoring_version: str
    family_contributions: Dict[str, float]
    reason_codes: List[str]
    statement: str = "Investigative indicator, not a judicial finding of criminal guilt."


class LegalRoleEvidence(BaseModel):
    """Step 4 Mule Role Classification evidence."""
    l1_collector_candidate: bool
    l2_distributor_candidate: bool
    l3_terminal_candidate: bool
    primary_role_label: str
    classification_reasons: List[str]
    fan_in: int
    fan_out: int


class LegalVelocityEvidence(BaseModel):
    """Step 5A Rapid Pass-Through Velocity evidence."""
    pass_through_candidate: bool
    pass_through_ratio: float
    qualifying_event_count: int
    attributed_volume: float
    outgoing_qualifying_count: int
    median_delay_seconds: Optional[float]
    window_description: str
    classification_version: str


class LegalAttributionEvidence(BaseModel):
    """Step 5C FIFO Fund Attribution evidence."""
    root_seed_outflow: float
    downstream_cumulative_attribution: float
    max_hops_traversed: int
    root_seed_edge_count: int
    downstream_fifo_edge_count: int
    terminal_accounts_count: int
    terminal_accounts_sample: List[Dict[str, Any]]
    attribution_policy: str = "TEMPORAL_FIFO"
    attribution_policy_version: str = "v1"
    is_truncated: bool
    truncation_reasons: List[str]
    cycles_detected: List[str]
    conservation_note: str = (
        "Downstream cumulative attribution represents fund propagation across subsequent hops "
        "and must NOT be summed across hops as unique new funds."
    )


class LegalEvidenceSnapshot(BaseModel):
    """Deterministic, self-contained verified evidence snapshot."""
    snapshot_version: str = "v1"
    subject_account: SubjectAccountLegalEvidence
    transactions_sample: List[VerifiedTransactionLegalItem]
    risk: LegalRiskEvidence
    roles: LegalRoleEvidence
    velocity: LegalVelocityEvidence
    attribution: LegalAttributionEvidence
    case_file_id: Optional[str] = None
    case_diary_id: Optional[str] = None
    dataset_name: str
    dataset_rows: int
    dataset_sha256: str
    evidence_snapshot_sha256: str
    provenance_chain: str = "RAW -> ANALYTICAL -> DERIVED -> LEGAL_DRAFT"


class LegalDraftDocument(BaseModel):
    """Structured sections of the compiled legal draft."""
    title: str
    document_type: LegalDocumentType
    header_notice: str = "OPERATION \"ABHEDYA-CHAKRA\" — FINANCIAL CYBER-FORENSICS INVESTIGATION"
    draft_notice: str = "DRAFT — SUBJECT TO INVESTIGATOR AND LEGAL AUTHORITY REVIEW"
    sections: List[Dict[str, Any]]
    plain_text_content: str


class LegalDraftPackage(BaseModel):
    """Complete Legal Draft Package containing metadata, evidence, document, and hashes."""
    package_id: str
    document_type: LegalDocumentType
    subject_account: str
    case_file_id: Optional[str] = None
    case_diary_id: Optional[str] = None
    investigation_id: str
    created_at: str
    status: LegalDraftStatus = LegalDraftStatus.REVIEW_REQUIRED
    officer_details: OfficerDetails
    evidence: LegalEvidenceSnapshot
    document: LegalDraftDocument
    evidence_snapshot_sha256: str
    pdf_sha256: Optional[str] = None
    json_sha256: str
    download_urls: Dict[str, str]
    draft_disclaimer: str = (
        "DRAFT DOCUMENT — SUBJECT TO INVESTIGATOR AND LEGAL AUTHORITY REVIEW. "
        "This draft was deterministically compiled from verified cyber-forensic evidence. "
        "It does NOT constitute an issued legal order, freeze instruction, or judicial determination. "
        "Authorized officer review and formal issuance under applicable statutory powers are required."
    )
    persistence_note: str = (
        "Legal draft metadata and generated artifacts are maintained in process-local storage "
        "and are not persistent across backend restarts."
    )


class LegalDraftResponse(BaseModel):
    """API response wrapping the legal draft package."""
    draft: LegalDraftPackage
    generation_time_ms: float
    disclaimer: str = (
        "INVESTIGATIVE FORENSICS ONLY — Deterministic accounting and behavioral models. "
        "Does not constitute legal proof of beneficial ownership, criminal intent, or judicial determination."
    )
