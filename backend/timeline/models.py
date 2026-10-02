"""
Timeline Investigation Data Models for Operation 'ABHEDYA-CHAKRA' (Step 10A)
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TimelineEventType(str, Enum):
    TRANSACTION = "TRANSACTION"
    VELOCITY = "VELOCITY"
    ATTRIBUTION = "ATTRIBUTION"
    RISK_ROLE = "RISK_ROLE"
    TERMINAL = "TERMINAL"


class TimelineEvent(BaseModel):
    event_id: str = Field(..., description="Stable deterministic event identifier")
    event_type: TimelineEventType
    timestamp: str
    title: str
    description: str
    amount: Optional[float] = None
    direction: Optional[str] = None  # "INCOMING", "OUTGOING", "INTERNAL", "OBSERVED"
    source_account: Optional[str] = None
    destination_account: Optional[str] = None
    transaction_id: Optional[str] = None
    source_row_id: Optional[int] = None
    payment_mode: Optional[str] = None
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    sender_ifsc: Optional[str] = None
    receiver_ifsc: Optional[str] = None
    narration: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class TimelineSummary(BaseModel):
    total_events: int
    transaction_count: int
    incoming_volume: float
    outgoing_volume: float
    net_volume: float
    velocity_event_count: int
    attribution_event_count: int
    terminal_event_count: int
    risk_role_findings: Optional[Dict[str, Any]] = None


class TimelineRange(BaseModel):
    start_time: str
    end_time: str
    dataset_min_time: str = "2026-09-15 00:00:00"
    dataset_max_time: str = "2026-09-29 23:59:58"


class TimelineProvenance(BaseModel):
    source: str = "ANALYTICAL_DATASET"
    dataset_name: str = "VoidHacks8_MuleAccount_2M_Transactions.csv"
    dataset_sha256: str = "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
    total_dataset_rows: int = 2000000


class TimelineResponse(BaseModel):
    account_id: Optional[str] = None
    range: TimelineRange
    summary: TimelineSummary
    events: List[TimelineEvent]
    page: int
    page_size: int
    total_events: int
    has_more: bool
    provenance: TimelineProvenance = Field(default_factory=TimelineProvenance)
