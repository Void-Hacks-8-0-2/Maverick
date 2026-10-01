"""
Feature Store Models for Operation 'ABHEDYA-CHAKRA'
Base v0.4: Deterministic Account Behavioral Feature Contracts.
Step 5A: 3-15 Minute Pass-Through Velocity Detection fields added.
Separates RAW TRANSACTIONS -> ANALYTICAL DIMENSION -> FEATURE STORE -> FORENSIC DETECTION -> EVIDENCE.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator


class CandidateReason(BaseModel):
    """
    Structured explainable reason for candidate classification.
    Factual evidence derived deterministically from observed account metrics.
    """
    code: str = Field(..., description="Stable deterministic reason code (e.g. HIGH_FAN_IN)")
    observed_value: Any = Field(..., description="Observed or derived metric value from dataset")
    threshold: Optional[Any] = Field(None, description="Configured heuristic threshold reference")
    description: str = Field(..., description="Factual explanatory description of observed evidence")

    @field_validator("observed_value", "threshold", mode="before")
    @classmethod
    def cast_numeric(cls, v):
        if isinstance(v, str):
            try:
                if v.isdigit() or (v.startswith("-") and v[1:].isdigit()):
                    return int(v)
                return float(v)
            except ValueError:
                return v
        return v


class AccountFeatures(BaseModel):

    """
    Forensic behavioral feature contract for an account entity.
    Derived deterministically from production transactions.
    Uncomputed detection flags remain NULL/None.
    """
    account_number: str = Field(..., description="Unique account identifier (entity)")
    
    # 1. Basic Flow Features
    incoming_txn_count: Optional[int] = Field(None, description="Total count of incoming credit transactions")
    outgoing_txn_count: Optional[int] = Field(None, description="Total count of outgoing debit transactions")
    incoming_volume: Optional[float] = Field(None, description="Total monetary sum of inbound transactions")
    outgoing_volume: Optional[float] = Field(None, description="Total monetary sum of outbound transactions")
    net_flow_delta: Optional[float] = Field(None, description="Observed Net Flow Delta (inflow - outflow)")
    
    # 2. Graph Topology & Counterparty Features
    fan_in: Optional[int] = Field(None, description="Number of unique sender accounts transferring into this account")
    fan_out: Optional[int] = Field(None, description="Number of unique receiver accounts receiving from this account")
    unique_counterparties: Optional[int] = Field(None, description="Distinct count of all counterparty accounts (senders ∪ receivers)")
    
    # 3. Flow Ratios (Safe NULL on zero denominator)
    outflow_to_inflow_ratio: Optional[float] = Field(None, description="Ratio of total outflow to total inflow (NULL if inflow == 0)")
    inflow_to_outflow_ratio: Optional[float] = Field(None, description="Ratio of total inflow to total outflow (NULL if outflow == 0)")
    
    # 4. Activity Span
    first_seen_timestamp: Optional[datetime] = Field(None, description="Earliest transaction timestamp involving this account")
    last_seen_timestamp: Optional[datetime] = Field(None, description="Latest transaction timestamp involving this account")
    activity_span_seconds: Optional[int] = Field(None, description="Total activity span in seconds (last_seen - first_seen)")
    
    # 5. Transaction Frequency
    active_day_count: Optional[int] = Field(None, description="Number of distinct calendar days with transaction activity")
    active_hour_count: Optional[int] = Field(None, description="Number of distinct calendar hours with transaction activity")
    transactions_per_active_day: Optional[float] = Field(None, description="Average transactions per active calendar day")
    
    # 6. Incoming Amount Statistics (NULL if incoming_txn_count == 0)
    incoming_amount_min: Optional[float] = Field(None, description="Minimum inbound transaction amount")
    incoming_amount_max: Optional[float] = Field(None, description="Maximum inbound transaction amount")
    incoming_amount_mean: Optional[float] = Field(None, description="Mean inbound transaction amount")
    incoming_amount_median: Optional[float] = Field(None, description="Median inbound transaction amount")
    incoming_amount_stddev: Optional[float] = Field(None, description="Population standard deviation of inbound transaction amounts")
    
    # 7. Outgoing Amount Statistics (NULL if outgoing_txn_count == 0)
    outgoing_amount_min: Optional[float] = Field(None, description="Minimum outbound transaction amount")
    outgoing_amount_max: Optional[float] = Field(None, description="Maximum outbound transaction amount")
    outgoing_amount_mean: Optional[float] = Field(None, description="Mean outbound transaction amount")
    outgoing_amount_median: Optional[float] = Field(None, description="Median outbound transaction amount")
    outgoing_amount_stddev: Optional[float] = Field(None, description="Population standard deviation of outbound transaction amounts")
    
    # 8. Device Profile
    unique_device_count: Optional[int] = Field(None, description="Count of distinct device types used by this account")
    android_txn_count: Optional[int] = Field(None, description="Transactions conducted via Android devices")
    ios_txn_count: Optional[int] = Field(None, description="Transactions conducted via iOS devices")
    windows_browser_txn_count: Optional[int] = Field(None, description="Transactions conducted via Windows_Browser")
    web_emulator_txn_count: Optional[int] = Field(None, description="Transactions conducted via Web_Emulator")
    linux_script_txn_count: Optional[int] = Field(None, description="Transactions conducted via Linux_Script")
    web_emulator_ratio: Optional[float] = Field(None, description="Proportion of transactions originating from Web_Emulator")
    linux_script_ratio: Optional[float] = Field(None, description="Proportion of transactions originating from Linux_Script")
    
    # 9. IP Profile
    unique_ip_count: Optional[int] = Field(None, description="Count of distinct IP addresses used by this account")
    transactions_per_unique_ip: Optional[float] = Field(None, description="Average transactions per unique IP address")
    top_ip_transaction_count: Optional[int] = Field(None, description="Number of transactions from the most active IP address")
    top_ip_transaction_ratio: Optional[float] = Field(None, description="Proportion of transactions from the top IP address")
    
    # 10. Payment Mode Profile
    upi_txn_count: Optional[int] = Field(None, description="Count of UPI transactions")
    imps_txn_count: Optional[int] = Field(None, description="Count of IMPS transactions")
    neft_txn_count: Optional[int] = Field(None, description="Count of NEFT transactions")
    rtgs_txn_count: Optional[int] = Field(None, description="Count of RTGS transactions")
    upi_ratio: Optional[float] = Field(None, description="Proportion of transactions conducted via UPI")
    imps_ratio: Optional[float] = Field(None, description="Proportion of transactions conducted via IMPS")
    neft_ratio: Optional[float] = Field(None, description="Proportion of transactions conducted via NEFT")
    rtgs_ratio: Optional[float] = Field(None, description="Proportion of transactions conducted via RTGS")
    
    # 11. Narration Profile
    unique_narration_count: Optional[int] = Field(None, description="Count of distinct narrations associated with transactions")
    empty_narration_count: Optional[int] = Field(None, description="Count of transactions with empty or null narrations")
    narration_repeat_ratio: Optional[float] = Field(None, description="Repetition ratio of transaction narrations (1 - unique/total)")
    
    # 12. Temporal Behavior Profile
    unique_active_dates: Optional[int] = Field(None, description="Distinct calendar dates with activity (matches active_day_count)")
    unique_active_hours: Optional[int] = Field(None, description="Count of distinct hours of the day (0-23) with observed activity")
    night_transaction_count: Optional[int] = Field(None, description="Transactions conducted during night hours (00:00 - 05:59)")
    night_transaction_ratio: Optional[float] = Field(None, description="Proportion of transactions occurring during night hours")
    
    # 13. Deterministic Role Candidate Classifications (Step 4)
    layer1_candidate: Optional[bool] = Field(None, description="Layer 1 Collector Candidate")
    layer2_candidate: Optional[bool] = Field(None, description="Layer 2 Distributor Candidate")
    layer3_candidate: Optional[bool] = Field(None, description="Layer 3 Terminal Candidate")
    layer1_reasons: List[CandidateReason] = Field(default_factory=list, description="Structured explainable reasons for Layer 1 candidacy")
    layer2_reasons: List[CandidateReason] = Field(default_factory=list, description="Structured explainable reasons for Layer 2 candidacy")
    layer3_reasons: List[CandidateReason] = Field(default_factory=list, description="Structured explainable reasons for Layer 3 candidacy")
    layer1_signal_count: Optional[int] = Field(0, description="Count of active signals for Layer 1")
    layer2_signal_count: Optional[int] = Field(0, description="Count of active signals for Layer 2")
    layer3_signal_count: Optional[int] = Field(0, description="Count of active signals for Layer 3")

    # Future Detection Placeholders (Prohibited in Step 4; reserved for later steps)
    mule_risk_index: Optional[float] = Field(None, description="Deterministic 0-100 Mule Risk Index (Future Step)")
    risk_factors: Optional[str] = Field(None, description="Explainable factor breakdown (Future Step)")
    cycle_indicator: Optional[bool] = Field(None, description="Circular transaction routing indicator (Future Step)")

    # 14. Step 5A -- Pass-Through Velocity Detection (3-15 minute window)
    # Reused placeholders (formerly Future Step; now populated by Step 5A)
    pass_through_ratio: Optional[float] = Field(
        None,
        description="Pass-through velocity ratio: qualifying_attributed_volume / total_incoming_volume. "
                    "NULL when account has no incoming transactions."
    )
    pass_through_event_count: Optional[int] = Field(
        None,
        description="Count of qualifying outgoing transactions matched to incoming funds "
                    "within the 3-15 minute window."
    )
    median_incoming_to_outgoing_seconds: Optional[float] = Field(
        None,
        description="Median delay (seconds) between incoming and matched outgoing transactions "
                    "within the qualifying 3-15 minute window."
    )
    rapid_outflow_count: Optional[int] = Field(
        None,
        description="Count of outgoing transactions with at least one eligible incoming "
                    "transaction in the 3-15 minute qualifying window."
    )
    # New Step 5A fields
    pass_through_candidate: Optional[bool] = Field(
        None,
        description="Pass-Through Velocity Candidate: pass_through_ratio >= 0.90 AND "
                    "qualifying_outgoing_transaction_count >= 2. "
                    "INVESTIGATIVE INDICATOR ONLY -- not a legal conclusion."
    )
    pass_through_incoming_volume: Optional[float] = Field(
        None,
        description="Total incoming (inbound) monetary volume for this account across all transactions."
    )
    pass_through_attributed_volume: Optional[float] = Field(
        None,
        description="Total outgoing volume attributed to qualifying 3-15 minute pass-through events "
                    "(capped per incoming transaction to prevent double-counting)."
    )
    pass_through_outgoing_transaction_count: Optional[int] = Field(
        None,
        description="Count of outgoing transactions participating in qualifying 3-15 minute "
                    "pass-through events."
    )
    pass_through_outgoing_volume: Optional[float] = Field(
        None,
        description="Total outgoing amount across qualifying pass-through outgoing transactions."
    )
    under_3_minute_event_count: Optional[int] = Field(
        None,
        description="Count of outgoing transactions with at least one incoming-to-outgoing delay "
                    "< 3 minutes (BEFORE_WINDOW bucket)."
    )
    over_15_minute_event_count: Optional[int] = Field(
        None,
        description="Count of outgoing transactions with at least one incoming-to-outgoing delay "
                    "> 15 minutes (AFTER_WINDOW bucket)."
    )
    velocity_classification_version: Optional[str] = Field(
        None,
        description="Step 5A velocity classification schema version."
    )
    velocity_classification_computed_at: Optional[datetime] = Field(
        None,
        description="Timestamp when Step 5A velocity classification was computed."
    )
    velocity_classification_provenance: Optional[str] = Field(
        None,
        description="Step 5A provenance marker (DERIVED)."
    )

    # 14. Provenance & Versioning Metadata
    feature_version: str = Field("v1", description="Feature schema definition version")
    computed_at: Optional[datetime] = Field(None, description="Timestamp when features were calculated")
    provenance: str = Field("DERIVED", description="Provenance marker: OBSERVED, DERIVED, or AI-GENERATED")
    classification_version: Optional[str] = Field("v1", description="Candidate classification schema version")
    classification_computed_at: Optional[datetime] = Field(None, description="Timestamp when candidate classification was computed")
    classification_provenance: Optional[str] = Field("CANDIDATE_CLASSIFICATION", description="Classification provenance marker")

    @field_validator("layer1_reasons", "layer2_reasons", "layer3_reasons", mode="before")
    @classmethod
    def parse_reasons(cls, v):
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                return []
        if v is None:
            return []
        return v

