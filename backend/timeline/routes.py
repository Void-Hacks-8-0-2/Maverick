"""
FastAPI Routes for Timeline Investigation (Step 10A)
"""

from typing import Optional
from fastapi import APIRouter, Query, Depends
import duckdb

from backend.db.connection import get_db
from backend.timeline.models import TimelineResponse
from backend.timeline.service import build_timeline

router = APIRouter(prefix="/timeline", tags=["Timeline"])


@router.get("", response_model=TimelineResponse)
def get_timeline_endpoint(
    account_id: Optional[str] = Query(None, description="Subject account ID to anchor investigation"),
    start_time: Optional[str] = Query(None, description="Start timestamp (YYYY-MM-DD HH:MM:SS)"),
    end_time: Optional[str] = Query(None, description="End timestamp (YYYY-MM-DD HH:MM:SS)"),
    direction: str = Query("all", pattern="^(in|out|all)$", description="Transaction direction relative to account"),
    payment_mode: str = Query("all", description="Payment mode filter (UPI, IMPS, NEFT, RTGS, all)"),
    device_type: str = Query("all", description="Device type filter"),
    event_type: str = Query("all", description="Event filter (all, transaction, velocity, attribution, risk, terminal)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=250, description="Items per page"),
    con: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Returns a unified, chronologically sorted, multi-layered forensic timeline.
    Merges atomic transactions, velocity alerts, FIFO attributions, and role findings.
    """
    return build_timeline(
        con=con,
        account_id=account_id,
        start_time=start_time,
        end_time=end_time,
        direction=direction,
        payment_mode=payment_mode,
        device_type=device_type,
        event_type=event_type,
        page=page,
        page_size=page_size
    )
