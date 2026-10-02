"""
FastAPI Routes for Transaction Explorer (Step 10B)
"""

from typing import Optional
from fastapi import APIRouter, Query, Depends
import duckdb

from backend.db.connection import get_db
from backend.transactions.models import (
    PaginatedTransactionsExplorerResponse,
    TransactionDetailResponse,
)
from backend.transactions.service import (
    query_transactions_explorer,
    get_transaction_by_stable_id,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=PaginatedTransactionsExplorerResponse)
def get_transactions_explorer_endpoint(
    transaction_id: Optional[str] = Query(None, description="Exact or partial transaction ID"),
    account_id: Optional[str] = Query(None, description="Account involved as sender OR receiver"),
    sender_account: Optional[str] = Query(None, description="Sender account"),
    receiver_account: Optional[str] = Query(None, description="Receiver account"),
    min_amount: Optional[float] = Query(None, ge=0, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, ge=0, description="Maximum amount"),
    start_time: Optional[str] = Query(None, description="Start timestamp (YYYY-MM-DD HH:MM:SS)"),
    end_time: Optional[str] = Query(None, description="End timestamp (YYYY-MM-DD HH:MM:SS)"),
    payment_mode: Optional[str] = Query(None, description="Payment mode filter"),
    device_type: Optional[str] = Query(None, description="Device type filter"),
    ip_address: Optional[str] = Query(None, description="IP address filter"),
    narration: Optional[str] = Query(None, description="Narration substring"),
    sender_ifsc: Optional[str] = Query(None, description="Sender IFSC code"),
    receiver_ifsc: Optional[str] = Query(None, description="Receiver IFSC code"),
    sort_by: str = Query("timestamp", pattern="^(timestamp|amount|transaction_id)$", description="Sort column"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=250, description="Items per page (25, 50, 100, 250)"),
    con: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Forensic transaction ledger search and filtering across 2,000,000 production records.
    Server-side pagination, parameterized filters, deterministic sorting, and duplicate ID detection.
    """
    return query_transactions_explorer(
        con=con,
        transaction_id=transaction_id,
        account_id=account_id,
        sender_account=sender_account,
        receiver_account=receiver_account,
        min_amount=min_amount,
        max_amount=max_amount,
        start_time=start_time,
        end_time=end_time,
        payment_mode=payment_mode,
        device_type=device_type,
        ip_address=ip_address,
        narration=narration,
        sender_ifsc=sender_ifsc,
        receiver_ifsc=receiver_ifsc,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )


@router.get("/{stable_id}", response_model=TransactionDetailResponse)
def get_transaction_detail_endpoint(
    stable_id: str,
    con: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Retrieves full transaction record by stable identifier (e.g. 'row_123' or 'TXN...')
    enriched with cross-investigative links and party risk indicators.
    """
    return get_transaction_by_stable_id(con=con, stable_id=stable_id)
