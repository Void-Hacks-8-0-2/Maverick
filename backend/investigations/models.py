"""
Step 6: Blind Victim Investigation Engine Models for Operation 'ABHEDYA-CHAKRA'
Strongly typed Pydantic models for multi-hop forensic victim investigations.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.detection.risk_models import MuleRiskScore
from backend.attribution.models import AttributionTraceResponse


class DataProvenance(BaseModel):
    """Integrity and provenance metadata for the investigation evidence."""
    dataset_name: str = Field("VoidHacks8_MuleAccount_2M_Transactions.csv", description="Authoritative dataset filename")
    dataset_rows: int = Field(2000000, description="Total verified row count")
    dataset_sha256: str = Field("2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101", description="Dataset integrity SHA-256 seal")
    attribution_policy: str = Field("TEMPORAL_FIFO", description="Forensic fund attribution policy")
    attribution_policy_version: str = Field("v1", description="Attribution engine version")
    risk_scoring_version: str = Field("v1", description="Risk scoring engine version")
    velocity_classification_version: str = Field("v1", description="Velocity detection version")
    integrity_statement: str = Field("Dataset integrity verified by SHA-256.", description="Factual integrity certification")


class VictimAccountSummary(BaseModel):
    """Observed analytical summary of the victim or subject account."""
    account_number: str = Field(..., description="Subject account identifier")
    first_observed_timestamp: Optional[str] = Field(None, description="Earliest observed activity timestamp")
    last_observed_timestamp: Optional[str] = Field(None, description="Latest observed activity timestamp")
    observed_incoming_volume: float = Field(..., description="Total observed inflow (INR)")
    observed_outgoing_volume: float = Field(..., description="Total observed outflow (INR)")
    observed_net_flow_delta: float = Field(..., description="Observed Net Flow Delta (Inflow minus Outflow) -- NOT a current bank balance")
    incoming_transaction_count: int = Field(..., description="Count of incoming transactions")
    outgoing_transaction_count: int = Field(..., description="Count of outgoing transactions")
    unique_counterparties: int = Field(..., description="Unique counterparties observed")
    unique_ip_count: int = Field(..., description="Unique IP addresses observed")
    unique_device_count: int = Field(..., description="Unique device types observed")
    payment_modes: Dict[str, int] = Field(default_factory=dict, description="Distribution of payment modes")
    associated_ifscs: List[str] = Field(default_factory=list, description="Associated IFSC codes")
    associated_ips: List[str] = Field(default_factory=list, description="Associated IP addresses")
    account_provenance: str = Field("ANALYTICAL", description="Data provenance tier")


class VictimTransactionItem(BaseModel):
    """Raw transaction involving the subject account."""
    transaction_id: str = Field(..., description="Transaction reference ID")
    row_id: int = Field(..., description="Stable virtual row identifier in analytical engine")
    sender_account: str = Field(..., description="Sender account number")
    receiver_account: str = Field(..., description="Receiver account number")
    amount: float = Field(..., description="Transaction amount (INR)")
    timestamp: str = Field(..., description="ISO formatted timestamp")
    payment_mode: str = Field(..., description="Payment rail (UPI, IMPS, NEFT, RTGS)")
    sender_ifsc: str = Field(..., description="Sender bank IFSC")
    receiver_ifsc: str = Field(..., description="Receiver bank IFSC")
    ip_address: str = Field(..., description="Originating IP address")
    device_type: Optional[str] = Field(None, description="Originating device type")
    narration: str = Field(..., description="Transaction narration string")
    direction: str = Field(..., description="'INCOMING' or 'OUTGOING' relative to subject account")
    provenance: str = Field("RAW", description="Data provenance tier")


class VictimRolesSummary(BaseModel):
    """Step 4 Mule Role Classification for the subject account."""
    l1_collector_candidate: bool = Field(False, description="Collector mule candidate flag")
    l2_distributor_candidate: bool = Field(False, description="Distributor mule candidate flag")
    l3_terminal_candidate: bool = Field(False, description="Terminal / cash-out candidate flag")
    fan_in: int = Field(0, description="Observed unique senders")
    fan_out: int = Field(0, description="Observed unique receivers")
    primary_role_label: str = Field(..., description="Neutral role description")
    classification_reasons: List[str] = Field(default_factory=list, description="Rule-based trigger reasons")
    l3_classification_signals: List[str] = Field(default_factory=list, description="Specific L3 drain signals if triggered")
    provenance: str = Field("DERIVED", description="Data provenance tier")


class VictimVelocitySummary(BaseModel):
    """Step 5A 3-15 Minute Pass-Through Velocity for the subject account."""
    pass_through_candidate: bool = Field(False, description="True if rapid pass-through velocity criteria met")
    pass_through_ratio: float = Field(0.0, description="Proportion of qualifying rapid pass-through outflow")
    qualifying_event_count: int = Field(0, description="Count of 3-15 minute paired pass-through matches")
    outgoing_qualifying_count: int = Field(0, description="Distinct outgoing transactions funded rapidly")
    attributed_volume: float = Field(0.0, description="Rapid pass-through volume in INR")
    median_delay_seconds: Optional[float] = Field(None, description="Median delay between incoming and outgoing")
    rapid_outflow_count: int = Field(0, description="Total rapid outflows under 15 minutes")
    window_description: str = Field("3_TO_15_MINUTES", description="Qualifying window description")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Representative pass-through events")
    classification_version: str = Field("v1", description="Velocity engine version")
    provenance: str = Field("DERIVED", description="Data provenance tier")


class TerminalAccountEvidence(BaseModel):
    """Forensic evidence for an account reached at the termination of the 4-hop trace."""
    account_number: str = Field(..., description="Terminal or destination account")
    hop: int = Field(..., description="Hop index where this account was reached (1-4)")
    attributed_amount: float = Field(..., description="Total money attributed reaching this account (INR)")
    primary_role: str = Field("Unknown", description="Step 4 role classification")
    risk_index: Optional[float] = Field(None, description="Step 5B Mule Risk Index (0-100)")
    risk_band: Optional[str] = Field(None, description="Risk band: LOW, MODERATE, HIGH, VERY_HIGH")
    velocity_status: Optional[str] = Field(None, description="Velocity candidate status")
    reason_codes: List[str] = Field(default_factory=list, description="Key evidence triggers")
    provenance: str = Field("DERIVED", description="Data provenance tier")


class InvestigationEvidenceSummary(BaseModel):
    """Structured deterministic summary of forensic investigation findings."""
    subject_account: str = Field(..., description="Investigated subject account")
    observed_activity: str = Field(..., description="Incoming / outgoing transaction summary")
    observed_outflow: float = Field(..., description="Total observed outflow")
    observed_inflow: float = Field(..., description="Total observed inflow")
    temporal_attribution_summary: str = Field(..., description="Root seed & FIFO attribution count summary")
    max_verified_propagation: int = Field(..., description="Deepest hop reached with positive attribution")
    risk_summary: str = Field(..., description="Risk score and band summary")
    role_summary: str = Field(..., description="Role classification summary")
    velocity_summary: str = Field(..., description="Velocity behavior summary")
    narrative: str = Field(..., description="Concise neutral forensic narrative")


class VictimInvestigationResponse(BaseModel):
    """Comprehensive investigation response for blind victim fund-flow tracing."""
    investigation_id: str = Field(..., description="Application-level investigation identifier")
    account_number: str = Field(..., description="Investigated victim account ID")
    status: str = Field(..., description="Investigation status: COMPLETED, NO_QUALIFYING_OUTFLOW, PARTIAL_EVIDENCE")
    generated_at: str = Field(..., description="ISO 8601 generation timestamp")
    data_provenance: DataProvenance = Field(default_factory=DataProvenance, description="Integrity and dataset provenance")
    account_summary: VictimAccountSummary = Field(..., description="Analytical account summary")
    victim_transactions: List[VictimTransactionItem] = Field(default_factory=list, description="Subject account transactions")
    risk: MuleRiskScore = Field(..., description="Step 5B Mule Risk Index and breakdown")
    roles: VictimRolesSummary = Field(..., description="Step 4 Mule role classification")
    velocity: VictimVelocitySummary = Field(..., description="Step 5A 3-15 minute pass-through velocity")
    trace: AttributionTraceResponse = Field(..., description="Step 5C 4-hop temporal FIFO money-flow trace")
    terminals: List[TerminalAccountEvidence] = Field(default_factory=list, description="Terminal / downstream accounts reached")
    warnings: List[str] = Field(default_factory=list, description="Investigation alerts, cycle notifications, or truncation notes")
    evidence_summary: InvestigationEvidenceSummary = Field(..., description="Deterministic structured forensic summary")
    disclaimer: str = Field(
        "INVESTIGATIVE FORENSICS ONLY -- Deterministic accounting and behavioral models. "
        "Does not constitute legal proof of beneficial ownership, criminal intent, or judicial determination.",
        description="Mandatory legal disclaimer"
    )
