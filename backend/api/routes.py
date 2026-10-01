"""
FastAPI Route Handlers for Operation 'ABHEDYA-CHAKRA'
Base v0.1: Analytical endpoints over recovered Parquet dataset.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.db.connection import get_db
from backend.services.graph_service import get_account_graph, get_account_trace
from backend.features import AccountFeatures, get_account_features
from backend.detection.velocity_detector import get_velocity_events

router = APIRouter()


# -------------------------------------------------------------
# Models
# -------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    service: str


class DatasetSummaryResponse(BaseModel):
    row_count: int
    unique_accounts: int
    unique_transactions: int
    payment_modes: Dict[str, int]
    total_amount: float
    timestamp_available: bool = True
    device_type_available: bool = True
    source_type: str = "PRODUCTION_DATASET"


class AccountSearchItem(BaseModel):
    account: str
    inbound_transaction_count: int
    outbound_transaction_count: int
    observed_inflow: float
    observed_outflow: float
    dataset_observed_net_movement: float


class AccountDetailResponse(BaseModel):
    account_id: str
    inbound_transaction_count: int
    outbound_transaction_count: int
    unique_senders: int
    unique_receivers: int
    observed_inflow: float
    observed_outflow: float
    dataset_observed_net_movement: float
    payment_mode_distribution: Dict[str, int]
    associated_ifscs: List[str]
    associated_ips: List[str]


class TransactionItem(BaseModel):
    Transaction_ID: str
    Sender_Account: str
    Receiver_Account: str
    Sender_IFSC: str
    Receiver_IFSC: str
    Amount: float
    Timestamp: Optional[str] = None
    Payment_Mode: str
    Narration: str
    IP_Address: str
    Device_Type: Optional[str] = None


class PaginatedTransactionsResponse(BaseModel):
    account_id: str
    direction: str
    total_count: int
    limit: int
    offset: int
    items: List[TransactionItem]


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@router.get("/health", response_model=HealthResponse)
def get_health():
    return {"status": "ok", "service": "abhedya-chakra-api"}


@router.get("/dataset/summary", response_model=DatasetSummaryResponse)
def get_dataset_summary():
    con = get_db()
    
    # 1. Total row count, tx count, total amount
    stats = con.execute("""
        SELECT 
            COUNT(*) as row_count,
            COUNT(DISTINCT Transaction_ID) as unique_tx,
            COALESCE(SUM(Amount), 0.0) as total_amt
        FROM transactions
    """).fetchone()

    # 2. Unique accounts (Senders + Receivers)
    unique_accs = con.execute("""
        SELECT COUNT(DISTINCT acc) FROM (
            SELECT Sender_Account AS acc FROM transactions
            UNION
            SELECT Receiver_Account AS acc FROM transactions
        )
    """).fetchone()[0]

    # 3. Payment mode distribution
    pm_rows = con.execute("""
        SELECT Payment_Mode, COUNT(*) 
        FROM transactions 
        WHERE Payment_Mode IS NOT NULL
        GROUP BY Payment_Mode
    """).fetchall()
    pm_dist = {row[0]: row[1] for row in pm_rows}

    return {
        "row_count": stats[0],
        "unique_accounts": unique_accs,
        "unique_transactions": stats[1],
        "payment_modes": pm_dist,
        "total_amount": round(stats[2], 2),
        "timestamp_available": True,
        "device_type_available": True,
        "source_type": "PRODUCTION_DATASET"
    }


@router.get("/accounts/search", response_model=List[AccountSearchItem])
def search_accounts(
    q: str = Query("", description="Account ID query substring"),
    limit: int = Query(20, ge=1, le=100)
):
    con = get_db()
    query_str = q.strip().upper()

    # Query pre-materialized accounts_dimension (sub-10ms response)
    if query_str:
        query = """
            SELECT 
                account_number,
                incoming_txn_count,
                outgoing_txn_count,
                total_inflow,
                total_outflow,
                net_flow_delta
            FROM accounts_dimension
            WHERE account_number ILIKE ?
            ORDER BY transaction_count DESC
            LIMIT ?
        """
        rows = con.execute(query, [f"%{query_str}%", limit]).fetchall()
    else:
        query = """
            SELECT 
                account_number,
                incoming_txn_count,
                outgoing_txn_count,
                total_inflow,
                total_outflow,
                net_flow_delta
            FROM accounts_dimension
            ORDER BY transaction_count DESC
            LIMIT ?
        """
        rows = con.execute(query, [limit]).fetchall()

    results = []
    for acc, in_cnt, out_cnt, inflow, outflow, net_flow in rows:
        results.append({
            "account": acc,
            "inbound_transaction_count": in_cnt,
            "outbound_transaction_count": out_cnt,
            "observed_inflow": round(inflow, 2),
            "observed_outflow": round(outflow, 2),
            "dataset_observed_net_movement": round(net_flow, 2)
        })

    return results


@router.get("/accounts/{account_id}", response_model=AccountDetailResponse)
def get_account_detail(account_id: str):
    con = get_db()
    acc = account_id.strip()

    # Check existence & retrieve pre-materialized metrics from accounts_dimension
    acc_row = con.execute("""
        SELECT 
            incoming_txn_count, 
            outgoing_txn_count, 
            unique_senders, 
            unique_receivers, 
            total_inflow, 
            total_outflow, 
            net_flow_delta
        FROM accounts_dimension 
        WHERE account_number = ?
    """, [acc]).fetchone()

    if not acc_row:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found in dataset")

    in_cnt, out_cnt, u_senders, u_receivers, inflow, outflow, net_flow = acc_row

    # Payment modes
    pm_rows = con.execute("""
        SELECT Payment_Mode, COUNT(*) 
        FROM transactions 
        WHERE Sender_Account = ? OR Receiver_Account = ?
        GROUP BY Payment_Mode
    """, [acc, acc]).fetchall()
    pm_dist = {r[0]: r[1] for r in pm_rows}

    # Associated IFSCs
    ifsc_rows = con.execute("""
        SELECT DISTINCT ifsc FROM (
            SELECT Sender_IFSC AS ifsc FROM transactions WHERE Sender_Account = ?
            UNION
            SELECT Receiver_IFSC AS ifsc FROM transactions WHERE Receiver_Account = ?
        ) WHERE ifsc IS NOT NULL ORDER BY ifsc
    """, [acc, acc]).fetchall()
    ifscs = [r[0] for r in ifsc_rows]

    # Associated IPs
    ip_rows = con.execute("""
        SELECT DISTINCT IP_Address 
        FROM transactions 
        WHERE Sender_Account = ? OR Receiver_Account = ?
        ORDER BY IP_Address
    """, [acc, acc]).fetchall()
    ips = [r[0] for r in ip_rows]

    return {
        "account_id": acc,
        "inbound_transaction_count": in_cnt,
        "outbound_transaction_count": out_cnt,
        "unique_senders": u_senders,
        "unique_receivers": u_receivers,
        "observed_inflow": round(inflow, 2),
        "observed_outflow": round(outflow, 2),
        "dataset_observed_net_movement": round(net_flow, 2),
        "payment_mode_distribution": pm_dist,
        "associated_ifscs": ifscs,
        "associated_ips": ips
    }


@router.get("/accounts/{account_id}/features", response_model=AccountFeatures)
def get_account_behavioral_features(account_id: str):
    """
    Internal/forensic feature inspection endpoint.
    Returns deterministic account behavioral features computed across the 2M production dataset.
    """
    con = get_db()
    features = get_account_features(con, account_id)
    if not features:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found in feature store")
    return features


@router.get("/accounts/{account_id}/transactions", response_model=PaginatedTransactionsResponse)
def get_account_transactions(
    account_id: str,
    direction: str = Query("all", pattern="^(in|out|all)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    con = get_db()
    acc = account_id.strip()

    if direction == "in":
        where_clause = "Receiver_Account = ?"
        params = [acc]
    elif direction == "out":
        where_clause = "Sender_Account = ?"
        params = [acc]
    else:
        where_clause = "(Sender_Account = ? OR Receiver_Account = ?)"
        params = [acc, acc]

    total_count = con.execute(
        f"SELECT COUNT(*) FROM transactions WHERE {where_clause}",
        params
    ).fetchone()[0]

    rows = con.execute(f"""
        SELECT 
            Transaction_ID,
            Sender_Account,
            Receiver_Account,
            Sender_IFSC,
            Receiver_IFSC,
            Amount,
            Timestamp,
            Payment_Mode,
            Narration,
            IP_Address,
            Device_Type
        FROM transactions
        WHERE {where_clause}
        ORDER BY Amount DESC
        LIMIT ? OFFSET ?
    """, params + [limit, offset]).fetchall()

    items = []
    for r in rows:
        items.append({
            "Transaction_ID": r[0],
            "Sender_Account": r[1],
            "Receiver_Account": r[2],
            "Sender_IFSC": r[3],
            "Receiver_IFSC": r[4],
            "Amount": float(r[5]) if r[5] is not None else 0.0,
            "Timestamp": str(r[6]) if r[6] is not None else None,
            "Payment_Mode": r[7],
            "Narration": r[8],
            "IP_Address": r[9],
            "Device_Type": r[10]
        })

    return {
        "account_id": acc,
        "direction": direction,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "items": items
    }


@router.get("/accounts/{account_id}/graph")
def get_graph(
    account_id: str,
    max_hops: int = Query(1, ge=1, le=3),
    max_nodes: int = Query(500, ge=10, le=1000)
):
    con = get_db()
    acc = account_id.strip()
    return get_account_graph(con, acc, max_hops=max_hops, max_nodes=max_nodes)


@router.get("/accounts/{account_id}/trace")
def get_trace(
    account_id: str,
    max_nodes: int = Query(1000, ge=50, le=2000)
):
    con = get_db()
    acc = account_id.strip()
    return get_account_trace(con, acc, max_hops=4, max_nodes=max_nodes)


@router.get("/accounts/{account_id}/velocity")
def get_account_velocity_events(
    account_id: str,
    limit: int = Query(100, ge=1, le=500)
):
    """
    Step 5A: Returns event-level pass-through velocity explainability for one account.

    Each event represents one outgoing transaction matched to a qualifying incoming
    transaction within the 3-15 minute window.

    Field provenance:
        OBSERVED  -- incoming_transaction_id, outgoing_transaction_id,
                     incoming_timestamp, outgoing_timestamp,
                     incoming_amount, outgoing_amount
        DERIVED   -- delay_seconds, attributed_amount, window label

    Returns an empty list if the account has no qualifying events.
    INVESTIGATIVE INDICATOR ONLY -- not a legal conclusion.
    """
    con = get_db()
    acc = account_id.strip()

    # Verify account exists
    exists = con.execute(
        "SELECT COUNT(*) FROM accounts_dimension WHERE account_number = ?", [acc]
    ).fetchone()[0]
    if not exists:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found in dataset")

    events = get_velocity_events(con, acc, limit=limit)
    return {
        "account_id": acc,
        "event_count": len(events),
        "qualifying_window": "3_TO_15_MINUTES",
        "window_min_seconds": 180,
        "window_max_seconds": 900,
        "provenance": "DERIVED",
        "events": events,
    }
