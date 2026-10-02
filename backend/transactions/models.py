"""
Transaction Explorer Data Models for Operation 'ABHEDYA-CHAKRA' (Step 10B)
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ForensicTransactionItem(BaseModel):
    stable_id: str = Field(..., description="Unique deterministic row identifier, e.g. row_10492")
    row_id: int = Field(..., description="0-indexed source row ID in dataset")
    Transaction_ID: str
    Sender_Account: str
    Receiver_Account: str
    Sender_IFSC: str
    Receiver_IFSC: str
    Amount: float
    Timestamp: str
    Payment_Mode: str
    Narration: str
    IP_Address: str
    Device_Type: str
    is_duplicate_tx_id: bool = Field(default=False, description="True if Transaction_ID occurs multiple times in dataset")


class TransactionProvenance(BaseModel):
    source: str = "ANALYTICAL_DATASET"
    dataset_name: str = "VoidHacks8_MuleAccount_2M_Transactions.csv"
    dataset_sha256: str = "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
    total_dataset_rows: int = 2000000


class PaginatedTransactionsExplorerResponse(BaseModel):
    items: List[ForensicTransactionItem]
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool
    provenance: TransactionProvenance = Field(default_factory=TransactionProvenance)


class TransactionDetailResponse(BaseModel):
    transaction: ForensicTransactionItem
    investigation_links: Dict[str, Any]
    provenance: TransactionProvenance = Field(default_factory=TransactionProvenance)
