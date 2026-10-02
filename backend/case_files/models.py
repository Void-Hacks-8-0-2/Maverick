"""
Case File and Evidence Package Models for Operation 'ABHEDYA-CHAKRA'
Step 7: Structured, reproducible, evidence-grounded forensic case file contracts.

Strictly distinguishes:
- OBSERVED FACTS (raw transactions, dimension records)
- DERIVED ANALYTICAL FINDINGS (features, FIFO attribution, risk index, velocity classification, mule roles)
- INVESTIGATIVE INTERPRETATION (deterministic narrative findings)
- LIMITATIONS (observation window, attribution policy limits, truncation, cycle notices)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.investigations.models import (
    DataProvenance,
    VictimAccountSummary,
    VictimTransactionItem,
    VictimRolesSummary,
    VictimVelocitySummary,
    TerminalAccountEvidence,
    InvestigationEvidenceSummary,
)
from backend.attribution.models import AttributionTraceResponse, AttributionRecord
from backend.detection.risk_models import MuleRiskScore, RiskReason


class CaseFileRequest(BaseModel):
    """Payload to generate a reproducible forensic case file."""
    account_number: str = Field(..., description="Subject account to generate case file for")
    investigation_id: Optional[str] = Field(None, description="Optional existing investigation identifier")
    max_hops: int = Field(4, ge=1, le=4, description="Attribution hop depth")
    horizon_seconds: Optional[int] = Field(None, description="Optional temporal horizon limit")
    max_branches_per_hop: int = Field(50, ge=1, le=500, description="Max branches per hop")
    include_pdf: bool = Field(True, description="Whether to compile PDF report artifact")
    include_json: bool = Field(True, description="Whether to compile JSON evidence package")


class ObservedFacts(BaseModel):
    """Factual, unmanipulated records observed directly in the production dataset."""
    subject_account: str
    total_observed_incoming_volume: float
    total_observed_outgoing_volume: float
    observed_net_flow_delta: float
    incoming_transaction_count: int
    outgoing_transaction_count: int
    unique_counterparties: int
    unique_ip_count: int
    unique_device_count: int
    payment_modes_observed: List[str]
    first_observed_timestamp: Optional[str]
    last_observed_timestamp: Optional[str]
    source_transaction_ids: List[str]
    source_row_ids: List[int]
    provenance: str = Field("RAW_AND_ANALYTICAL", description="Observed source provenance")


class OfficialRiskBreakdown(BaseModel):
    """Official Step 5B 6-Family Risk Score Contribution Breakdown."""
    risk_index: float
    risk_band: str
    scoring_version: str
    family_points: Dict[str, float] = Field(
        ...,
        description="Official point contributions: FLOW_STRUCTURE, VELOCITY, AUTOMATION, NETWORK_STRUCTURE, TRANSACTION_BEHAVIOR, ROLE_SUPPORT"
    )
    evidence_reasons: List[RiskReason]
    provenance: str = Field("DERIVED", description="Step 5B derived analytical score")


class AttributionSummary(BaseModel):
    """Forensically sound attribution summary distinguishing root seed outflow from downstream cumulative hops."""
    root_seed_outflow: float = Field(..., description="Total outflow directly exiting the subject account")
    downstream_cumulative_attribution: float = Field(..., description="Cumulative funds attributed across subsequent downstream hops")
    max_hops_traversed: int
    root_seed_edge_count: int
    downstream_fifo_edge_count: int
    attribution_policy: str = "TEMPORAL_FIFO"
    attribution_policy_version: str = "v1"
    note: str = Field(
        "Downstream amounts represent fund propagation across subsequent hops and must not be summed across hops as unique new funds.",
        description="Mandatory money conservation clarification"
    )
    provenance: str = Field("ATTRIBUTION", description="Derived attribution policy tier")


class InvestigationLimitations(BaseModel):
    """Explicit analytical boundaries and legal limitations."""
    dataset_observation_window: str = "15-day closed dataset window (2,000,000 transactions)"
    ground_truth_status: str = "No external ground-truth labels; analytical findings are based on deterministic forensic heuristics."
    legal_nature_disclaimer: str = (
        "TEMPORAL_FIFO is a deterministic accounting and fund-flow attribution policy, not judicial proof of beneficial ownership "
        "or legal certainty of criminality. This report is an investigative draft."
    )
    branch_limits_applied: str = "Configured max_branches_per_hop = 50, max_trace_edges = 500"
    persistence_limitation: str = (
        "Case-file metadata and generated artifacts are currently maintained in process-local storage "
        "and are not persistent across backend restarts."
    )
    is_truncated: bool
    truncation_reasons: List[str]
    cycles_detected: List[str]


class EvidenceSnapshot(BaseModel):
    """
    Deterministic self-contained snapshot of all relevant records needed to
    reproduce the analytical findings for this subject account.
    """
    snapshot_version: str = "v1"
    subject_account: str
    dataset_name: str
    dataset_rows: int
    dataset_sha256: str
    observed_facts: ObservedFacts
    transactions_sample: List[VictimTransactionItem]
    attribution: AttributionSummary
    trace_nodes_count: int
    trace_edges_count: int
    terminal_accounts: List[TerminalAccountEvidence]
    official_risk: OfficialRiskBreakdown
    velocity_profile: VictimVelocitySummary
    mule_roles: VictimRolesSummary
    limitations: InvestigationLimitations
    provenance_chain: str = "RAW -> ANALYTICAL -> DERIVED -> CASE_FILE"


class CaseFileMetadata(BaseModel):
    """Header metadata and integrity hashes for the forensic case file."""
    case_file_id: str = Field(..., description="Application Case File ID (e.g. CASE-KKBK10000402-A1B2C3D4)")
    investigation_id: str = Field(..., description="Associated investigation identifier")
    subject_account: str = Field(..., description="Account entity evaluated")
    status: str = Field(..., description="Status: COMPLETED, TRUNCATED, etc.")
    created_at: str = Field(..., description="ISO-8601 UTC creation timestamp")
    source_dataset: str
    dataset_rows: int
    dataset_sha256: str
    evidence_snapshot_sha256: str = Field(..., description="SHA-256 seal over canonical evidence snapshot")
    pdf_sha256: Optional[str] = Field(None, description="SHA-256 seal over generated PDF document")
    json_sha256: Optional[str] = Field(None, description="SHA-256 seal over generated JSON evidence package")
    pdf_download_url: Optional[str] = None
    json_download_url: Optional[str] = None
    disclaimer: str = Field(
        "FOR INVESTIGATIVE USE / DRAFT ONLY -- Deterministic analytical report derived from production dataset. "
        "SHA-256 provides an integrity seal for the generated artifact; it does not by itself establish legal chain of custody. "
        "Not a judicial determination of guilt or statutory finding.",
        description="Mandatory forensic disclaimer"
    )


class CaseFileResponse(BaseModel):
    """Complete forensic case file response."""
    metadata: CaseFileMetadata
    evidence_snapshot: EvidenceSnapshot
    trace: AttributionTraceResponse
    warnings: List[str]
    evidence_narrative: str
