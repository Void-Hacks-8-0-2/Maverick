"""
Transaction Explorer Service for Operation 'ABHEDYA-CHAKRA' (Step 10B)
High-density forensic query engine with parameterized DuckDB filtering,
duplicate-ID handling, and cross-investigation contextualization.
"""

from typing import Optional, List, Dict, Any, Tuple
import duckdb
from fastapi import HTTPException

from backend.transactions.models import (
    ForensicTransactionItem,
    PaginatedTransactionsExplorerResponse,
    TransactionDetailResponse,
    TransactionProvenance,
)
from backend.detection.risk_scoring import get_account_risk
from backend.detection.role_classifier import get_account_role


def query_transactions_explorer(
    con: duckdb.DuckDBPyConnection,
    transaction_id: Optional[str] = None,
    account_id: Optional[str] = None,
    sender_account: Optional[str] = None,
    receiver_account: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    payment_mode: Optional[str] = None,
    device_type: Optional[str] = None,
    ip_address: Optional[str] = None,
    narration: Optional[str] = None,
    sender_ifsc: Optional[str] = None,
    receiver_ifsc: Optional[str] = None,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> PaginatedTransactionsExplorerResponse:
    """
    Executes a high-performance, parameterized DuckDB query over the 2M-row transactions table.
    """
    where_clauses: List[str] = []
    params: List[Any] = []

    # Filter: Transaction ID (exact or wildcard)
    if transaction_id and transaction_id.strip():
        tid = transaction_id.strip().upper()
        if len(tid) == 12 and tid.startswith("TXN"):
            where_clauses.append("Transaction_ID = ?")
            params.append(tid)
        else:
            where_clauses.append("Transaction_ID ILIKE ?")
            params.append(f"%{tid}%")

    # Filter: General Account ID (Sender OR Receiver)
    if account_id and account_id.strip():
        acc = account_id.strip().upper()
        where_clauses.append("(Sender_Account = ? OR Receiver_Account = ?)")
        params.extend([acc, acc])

    # Filter: Specific Sender
    if sender_account and sender_account.strip():
        where_clauses.append("Sender_Account = ?")
        params.append(sender_account.strip().upper())

    # Filter: Specific Receiver
    if receiver_account and receiver_account.strip():
        where_clauses.append("Receiver_Account = ?")
        params.append(receiver_account.strip().upper())

    # Filter: Amount Bounds
    if min_amount is not None:
        where_clauses.append("Amount >= ?")
        params.append(float(min_amount))

    if max_amount is not None:
        where_clauses.append("Amount <= ?")
        params.append(float(max_amount))

    # Filter: Temporal Bounds
    if start_time and start_time.strip():
        where_clauses.append("Timestamp >= ?")
        params.append(start_time.strip())

    if end_time and end_time.strip():
        where_clauses.append("Timestamp <= ?")
        params.append(end_time.strip())

    # Filter: Payment Mode
    if payment_mode and payment_mode.strip() and payment_mode.lower() != "all":
        where_clauses.append("Payment_Mode = ?")
        params.append(payment_mode.strip().upper())

    # Filter: Device Type
    if device_type and device_type.strip() and device_type.lower() != "all":
        where_clauses.append("Device_Type = ?")
        params.append(device_type.strip())

    # Filter: IP Address
    if ip_address and ip_address.strip():
        where_clauses.append("IP_Address ILIKE ?")
        params.append(f"%{ip_address.strip()}%")

    # Filter: Narration
    if narration and narration.strip():
        where_clauses.append("Narration ILIKE ?")
        params.append(f"%{narration.strip()}%")

    # Filter: IFSCs
    if sender_ifsc and sender_ifsc.strip():
        where_clauses.append("Sender_IFSC = ?")
        params.append(sender_ifsc.strip().upper())

    if receiver_ifsc and receiver_ifsc.strip():
        where_clauses.append("Receiver_IFSC = ?")
        params.append(receiver_ifsc.strip().upper())

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Count query
    count_sql = f"SELECT COUNT(*) FROM transactions WHERE {where_sql}"
    total_count = con.execute(count_sql, params).fetchone()[0]

    # Ordering & Deterministic Tie-breaking
    direction_sql = "DESC" if sort_order.lower() == "desc" else "ASC"
    if sort_by.lower() == "amount":
        order_sql = f"ORDER BY Amount {direction_sql}, Timestamp DESC, rowid ASC"
    elif sort_by.lower() == "transaction_id":
        order_sql = f"ORDER BY Transaction_ID {direction_sql}, Timestamp DESC, rowid ASC"
    else:
        order_sql = f"ORDER BY Timestamp {direction_sql}, rowid ASC"

    # Pagination bounds
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 250))
    offset = (safe_page - 1) * safe_page_size

    # Data query
    data_sql = f"""
        SELECT 
            rowid,
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
        WHERE {where_sql}
        {order_sql}
        LIMIT ? OFFSET ?
    """
    rows = con.execute(data_sql, params + [safe_page_size, offset]).fetchall()

    # Identify duplicate Transaction_IDs within this page's results
    page_tx_ids = [r[1] for r in rows if r[1]]
    duplicate_set = set()
    if page_tx_ids:
        placeholders = ", ".join(["?"] * len(page_tx_ids))
        dup_rows = con.execute(f"""
            SELECT Transaction_ID 
            FROM transactions 
            WHERE Transaction_ID IN ({placeholders})
            GROUP BY Transaction_ID 
            HAVING COUNT(*) > 1
        """, page_tx_ids).fetchall()
        duplicate_set = {r[0] for r in dup_rows}

    items: List[ForensicTransactionItem] = []
    for r in rows:
        row_id, tx_id, sender, receiver, s_ifsc, r_ifsc, amt, ts, pm, narr, ip, dev = r
        items.append(ForensicTransactionItem(
            stable_id=f"row_{row_id}",
            row_id=row_id,
            Transaction_ID=tx_id,
            Sender_Account=sender,
            Receiver_Account=receiver,
            Sender_IFSC=s_ifsc or "",
            Receiver_IFSC=r_ifsc or "",
            Amount=round(float(amt), 2) if amt is not None else 0.0,
            Timestamp=str(ts),
            Payment_Mode=pm or "UNKNOWN",
            Narration=narr or "",
            IP_Address=ip or "",
            Device_Type=dev or "UNKNOWN",
            is_duplicate_tx_id=(tx_id in duplicate_set)
        ))

    total_pages = (total_count + safe_page_size - 1) // safe_page_size if total_count > 0 else 1
    has_next = safe_page < total_pages
    has_previous = safe_page > 1

    return PaginatedTransactionsExplorerResponse(
        items=items,
        page=safe_page,
        page_size=safe_page_size,
        total_count=total_count,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
        provenance=TransactionProvenance()
    )


def get_transaction_by_stable_id(
    con: duckdb.DuckDBPyConnection,
    stable_id: str
) -> TransactionDetailResponse:
    """
    Retrieves full transaction record by stable identifier (e.g. 'row_123' or '123' or 'TXN...')
    and enriches with cross-investigation links.
    """
    clean_id = stable_id.strip()
    row = None

    if clean_id.startswith("row_"):
        try:
            target_row_id = int(clean_id[4:])
            row = con.execute("""
                SELECT rowid, Transaction_ID, Sender_Account, Receiver_Account,
                       Sender_IFSC, Receiver_IFSC, Amount, Timestamp, Payment_Mode,
                       Narration, IP_Address, Device_Type
                FROM transactions
                WHERE rowid = ?
            """, [target_row_id]).fetchone()
        except ValueError:
            pass
    elif clean_id.isdigit():
        row = con.execute("""
            SELECT rowid, Transaction_ID, Sender_Account, Receiver_Account,
                   Sender_IFSC, Receiver_IFSC, Amount, Timestamp, Payment_Mode,
                   Narration, IP_Address, Device_Type
            FROM transactions
            WHERE rowid = ?
        """, [int(clean_id)]).fetchone()
    else:
        # Fallback to Transaction_ID lookup
        row = con.execute("""
            SELECT rowid, Transaction_ID, Sender_Account, Receiver_Account,
                   Sender_IFSC, Receiver_IFSC, Amount, Timestamp, Payment_Mode,
                   Narration, IP_Address, Device_Type
            FROM transactions
            WHERE Transaction_ID = ?
            ORDER BY rowid ASC
            LIMIT 1
        """, [clean_id.upper()]).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction with stable ID '{stable_id}' not found in dataset"
        )

    row_id, tx_id, sender, receiver, s_ifsc, r_ifsc, amt, ts, pm, narr, ip, dev = row

    # Check if duplicate in dataset
    dup_count = con.execute(
        "SELECT COUNT(*) FROM transactions WHERE Transaction_ID = ?",
        [tx_id]
    ).fetchone()[0]

    tx_item = ForensicTransactionItem(
        stable_id=f"row_{row_id}",
        row_id=row_id,
        Transaction_ID=tx_id,
        Sender_Account=sender,
        Receiver_Account=receiver,
        Sender_IFSC=s_ifsc or "",
        Receiver_IFSC=r_ifsc or "",
        Amount=round(float(amt), 2) if amt is not None else 0.0,
        Timestamp=str(ts),
        Payment_Mode=pm or "UNKNOWN",
        Narration=narr or "",
        IP_Address=ip or "",
        Device_Type=dev or "UNKNOWN",
        is_duplicate_tx_id=(dup_count > 1)
    )

    # Contextual investigation links
    sender_risk = None
    sender_role = None
    try:
        sr = get_account_risk(con, sender)
        sender_risk = {"score": round(sr.risk_index, 1), "band": sr.risk_band}
        s_role = get_account_role(con, sender)
        sender_role = s_role.role if s_role else "NONE"
    except Exception:
        pass

    receiver_risk = None
    receiver_role = None
    try:
        rr = get_account_risk(con, receiver)
        receiver_risk = {"score": round(rr.risk_index, 1), "band": rr.risk_band}
        r_role = get_account_role(con, receiver)
        receiver_role = r_role.role if r_role else "NONE"
    except Exception:
        pass

    investigation_links = {
        "sender_account": sender,
        "receiver_account": receiver,
        "sender_mule_risk": sender_risk,
        "sender_mule_role": sender_role,
        "receiver_mule_risk": receiver_risk,
        "receiver_mule_role": receiver_role,
        "duplicate_occurrence_count": dup_count,
        "links": {
            "sender_timeline": f"/timeline?account_id={sender}",
            "receiver_timeline": f"/timeline?account_id={receiver}",
            "sender_investigation": f"/victim?account={sender}",
            "receiver_investigation": f"/victim?account={receiver}",
            "sender_graph": f"/graph?account={sender}",
            "receiver_graph": f"/graph?account={receiver}",
        }
    }

    return TransactionDetailResponse(
        transaction=tx_item,
        investigation_links=investigation_links,
        provenance=TransactionProvenance()
    )
