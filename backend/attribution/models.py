"""
Attribution Data Models and Schema Contracts for Operation 'ABHEDYA-CHAKRA'
Step 5C: Temporal FIFO Attribution Models.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AttributionRecord(BaseModel):
    """
    Forensic edge attributing an outgoing fund transfer back to an earlier incoming transfer.
    Identified strictly by stable database row_ids to preserve duplicate Transaction_IDs.
    """
    attribution_id: str = Field(..., description="Deterministic unique identifier for this attribution match")
    source_row_id: int = Field(..., description="Stable rowid of the source (inflow) transaction")
    source_transaction_id: str = Field(..., description="Observed Transaction_ID of the source transaction")
    source_account: str = Field(..., description="Account that originally sent funds into the intermediary")
    intermediary_account: str = Field(..., description="The account through which funds flowed")
    source_timestamp: str = Field(..., description="Timestamp when incoming funds entered the intermediary")
    source_amount: float = Field(..., description="Original total amount of the source incoming transaction")
    
    destination_row_id: int = Field(..., description="Stable rowid of the destination (outflow) transaction")
    destination_transaction_id: str = Field(..., description="Observed Transaction_ID of the destination transaction")
    destination_account: str = Field(..., description="Account that received funds from the intermediary")
    destination_timestamp: str = Field(..., description="Timestamp when outgoing funds exited the intermediary")
    destination_amount: float = Field(..., description="Original total amount of the destination outgoing transaction")
    
    attributed_amount: float = Field(..., description="Specific amount attributed from source to destination")
    delay_seconds: float = Field(..., description="Elapsed duration (in seconds) between inflow and outflow")
    hop_number: int = Field(1, description="Hop index along the forensic attribution path (1 to 4)")
    edge_type: str = Field("FIFO_ATTRIBUTION", description="Type of edge: 'ROOT_SEED' or 'FIFO_ATTRIBUTION'")
    attribution_policy: str = Field("TEMPORAL_FIFO", description="Accounting attribution policy used")
    attribution_policy_version: str = Field("v1", description="Attribution engine version")
    provenance: str = Field("ATTRIBUTION", description="Provenance marker")
    created_at: Optional[str] = Field(None, description="Computation timestamp")


class UnallocatedOutflowRecord(BaseModel):
    """
    Represents an outgoing transaction that could not be fully attributed
    due to depleted or unavailable eligible incoming funds.
    """
    destination_row_id: int = Field(..., description="Stable rowid of the outgoing transaction")
    destination_transaction_id: str = Field(..., description="Transaction_ID of the outgoing transaction")
    destination_account: str = Field(..., description="Account that received funds")
    destination_timestamp: str = Field(..., description="Timestamp of the outgoing transaction")
    destination_amount: float = Field(..., description="Total amount of the outgoing transaction")
    attributed_amount: float = Field(..., description="Amount funded by eligible prior incoming transactions")
    unallocated_amount: float = Field(..., description="Unfunded remainder (destination_amount - attributed_amount)")
    reason: str = Field(..., description="Explanation code: NO_PRIOR_INFLOW, INFLOW_DEPLETED, or HORIZON_EXCEEDED")


class AccountAttributionResponse(BaseModel):
    """
    Account-level Temporal FIFO Attribution dossier.
    Fully conserves monetary amounts and exposes all attribution matches and unallocated outflows.
    """
    account_id: str = Field(..., description="Account entity analyzed")
    policy_name: str = Field("TEMPORAL_FIFO", description="Attribution rule applied")
    policy_version: str = Field("v1", description="Policy schema version")
    horizon_seconds: Optional[int] = Field(None, description="Max allowed seconds between inflow and outflow (None = dataset window)")
    
    total_incoming_volume: float = Field(..., description="Total observed inbound amount")
    total_outgoing_volume: float = Field(..., description="Total observed outbound amount")
    total_attributed_volume: float = Field(..., description="Total outbound amount successfully attributed to prior inflows")
    total_unallocated_outflow: float = Field(..., description="Total outbound amount exceeding available prior inflows")
    
    incoming_transaction_count: int = Field(..., description="Count of inbound transactions")
    outgoing_transaction_count: int = Field(..., description="Count of outbound transactions")
    attribution_edge_count: int = Field(..., description="Total attribution linkages formed")
    
    attribution_records: List[AttributionRecord] = Field(default_factory=list, description="List of attribution matches")
    unallocated_records: List[UnallocatedOutflowRecord] = Field(default_factory=list, description="List of unallocated or partially funded outflows")
    
    provenance: str = Field("ATTRIBUTION", description="Data provenance tier")
    disclaimer: str = Field(
        "INVESTIGATIVE ATTRIBUTION ONLY -- Deterministic accounting model based on chronological FIFO rules. "
        "Does not constitute legal proof of beneficial ownership or judicial determination of criminality.",
        description="Mandatory forensic disclaimer"
    )


class TraceHopSummary(BaseModel):
    """Aggregated summary of fund attribution for a single hop level."""
    hop_number: int = Field(..., description="Hop index (1 to 4)")
    sender_account: str = Field(..., description="Upstream account")
    receiver_account: str = Field(..., description="Downstream account")
    attributed_amount: float = Field(..., description="Total attributed amount across this hop")
    edge_count: int = Field(..., description="Number of distinct transaction attribution links")


class TraceAttributionNode(BaseModel):
    """Graph node in the 4-hop temporal attribution trace."""
    id: str = Field(..., description="Account identifier")
    type: str = Field("account", description="Node type")
    is_root: bool = Field(False, description="True if root victim/source account")
    hop: int = Field(0, description="Hop level from root")
    inflow_attributed: float = Field(0.0, description="Amount attributed into this account from upstream")
    outflow_attributed: float = Field(0.0, description="Amount attributed out of this account to downstream")


class AttributionTraceResponse(BaseModel):
    """
    Forensic 4-hop Temporal Money-Flow Attribution Trace.
    Traces fund provenance through multiple hops with amount conservation.
    """
    root_account: str = Field(..., description="Root victim or originating account")
    root_row_id: Optional[int] = Field(None, description="Optional root transaction rowid if tracing specific transaction")
    root_transaction_id: Optional[str] = Field(None, description="Optional root Transaction_ID")
    max_hops: int = Field(4, description="Maximum hops traversed (1 to 4)")
    horizon_seconds: Optional[int] = Field(None, description="Attribution horizon per hop in seconds")
    policy_name: str = Field("TEMPORAL_FIFO", description="Attribution policy name")
    policy_version: str = Field("v1", description="Policy version")
    
    total_attributed_amount: float = Field(..., description="Total money tracked across all hops")
    total_hops_found: int = Field(..., description="Maximum hop depth reached")
    
    nodes: List[TraceAttributionNode] = Field(default_factory=list, description="Graph nodes in the trace")
    edges: List[AttributionRecord] = Field(default_factory=list, description="Forensic attribution edges linking transactions")
    hop_summaries: List[TraceHopSummary] = Field(default_factory=list, description="Per-hop financial summary")
    
    truncated: bool = Field(False, description="True if traversal limits capped branch expansion")
    truncation_reason: Optional[str] = Field(None, description="Reason for truncation if applicable")
    cycles_detected: List[str] = Field(default_factory=list, description="Cycle paths detected during traversal")
    provenance: str = Field("ATTRIBUTION", description="Provenance marker")
    disclaimer: str = Field(
        "INVESTIGATIVE ATTRIBUTION ONLY -- Deterministic accounting model based on chronological FIFO rules. "
        "Does not constitute legal proof of beneficial ownership or judicial determination of criminality.",
        description="Mandatory forensic disclaimer"
    )


class TransactionAttributionResponse(BaseModel):
    """
    Transaction-level attribution details for a specific transaction row.
    """
    row_id: int = Field(..., description="Stable database rowid")
    transaction_id: str = Field(..., description="Observed Transaction_ID")
    account_number: str = Field(..., description="Account evaluated")
    direction: str = Field(..., description="INCOMING or OUTGOING")
    amount: float = Field(..., description="Original transaction amount")
    timestamp: str = Field(..., description="Transaction timestamp")
    
    attributed_amount: float = Field(..., description="Total amount attributed (either funded or dispersed)")
    remaining_or_unallocated_amount: float = Field(..., description="Unattributed remainder")
    
    matched_attributions: List[AttributionRecord] = Field(default_factory=list, description="Attribution matches linking this transaction")
    policy_name: str = Field("TEMPORAL_FIFO", description="Policy name")
    policy_version: str = Field("v1", description="Policy version")
    disclaimer: str = Field(
        "INVESTIGATIVE ATTRIBUTION ONLY -- Deterministic accounting model based on chronological FIFO rules.",
        description="Mandatory forensic disclaimer"
    )
