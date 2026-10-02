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
from backend.detection.risk_scoring import get_account_risk
from backend.detection.risk_models import MuleRiskScore
from backend.attribution import (
    AccountAttributionResponse,
    AttributionTraceResponse,
    TransactionAttributionResponse,
    compute_account_fifo_attribution,
    trace_fifo_attribution_4hop,
    get_transaction_fifo_attribution,
)
from backend.investigations import (
    VictimInvestigationResponse,
    investigate_victim_account,
)
from fastapi import Response
from backend.case_files import (
    CaseFileRequest,
    CaseFileResponse,
    generate_forensic_case_file,
    CASE_FILE_STORE,
)
from backend.case_diary import (
    CaseDiaryRequest,
    CaseDiaryResponse,
    build_case_diary,
    CASE_DIARY_STORE,
)
from backend.case_diary.models import GenerateNarrativeRequest
from backend.case_diary.service import regenerate_narrative

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


@router.get("/accounts/{account_id}/risk", response_model=MuleRiskScore)
def get_account_risk_score(account_id: str):
    """
    Step 5B: Returns explainable 0-100 Mule Risk Index for one account.

    Aggregates 6 independent evidence families into a bounded, reproducible score:
      - FLOW_STRUCTURE (max 20)
      - VELOCITY (max 25)
      - AUTOMATION (max 20)
      - NETWORK_STRUCTURE (max 15)
      - TRANSACTION_BEHAVIOR (max 10)
      - ROLE_SUPPORT (max 10)

    INVESTIGATIVE CANDIDATE INDICATORS ONLY -- not a declaration of criminality or legal determination.
    """
    con = get_db()
    acc = account_id.strip()

    # Verify account exists
    exists = con.execute(
        "SELECT COUNT(*) FROM accounts_dimension WHERE account_number = ?", [acc]
    ).fetchone()[0]
    if not exists:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found in dataset")

    risk_score = get_account_risk(con, acc)
    if not risk_score:
        raise HTTPException(status_code=404, detail=f"Risk score not found for account '{account_id}'")

    return risk_score


@router.get("/accounts/{account_id}/attribution", response_model=AccountAttributionResponse)
def get_account_attribution(
    account_id: str,
    horizon_seconds: Optional[int] = Query(None, ge=1, description="Maximum elapsed seconds between inflow and outflow")
):
    """
    Step 5C: Returns exact chronological FIFO attribution for one account.
    Tracks which earlier incoming transactions funded each outgoing transaction.
    """
    con = get_db()
    acc = account_id.strip()

    exists = con.execute(
        "SELECT COUNT(*) FROM accounts_dimension WHERE account_number = ?", [acc]
    ).fetchone()[0]
    if not exists:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found in dataset")

    return compute_account_fifo_attribution(con, acc, horizon_seconds=horizon_seconds)


@router.get("/accounts/{account_id}/attribution/trace", response_model=AttributionTraceResponse)
def get_account_attribution_trace(
    account_id: str,
    root_row_id: Optional[int] = Query(None, description="Optional root transaction rowid to trace specific transfer"),
    max_hops: int = Query(4, ge=1, le=6, description="Maximum downstream hops (default 4)"),
    horizon_seconds: Optional[int] = Query(None, ge=1, description="Attribution horizon per hop in seconds")
):
    """
    Step 5C: Traces up to 4 hops of temporal money-flow attribution starting from a victim or origin account.
    Distinguishes temporal money-flow attribution from mere structural connectivity.
    """
    con = get_db()
    acc = account_id.strip()

    exists = con.execute(
        "SELECT COUNT(*) FROM accounts_dimension WHERE account_number = ?", [acc]
    ).fetchone()[0]
    if not exists:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found in dataset")

    return trace_fifo_attribution_4hop(
        con, acc, root_row_id=root_row_id, max_hops=max_hops, horizon_seconds=horizon_seconds
    )


@router.get("/transactions/{transaction_id}/attribution", response_model=TransactionAttributionResponse)
def get_transaction_attribution(
    transaction_id: str,
    row_id: Optional[int] = Query(None, description="Stable rowid to disambiguate duplicate Transaction_IDs")
):
    """
    Step 5C: Returns FIFO attribution details for a specific transaction row.
    Disambiguates duplicate Transaction_IDs using row_id.
    """
    con = get_db()
    tx_id = transaction_id.strip()

    try:
        return get_transaction_fifo_attribution(con, tx_id, row_id=row_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/investigations/victim/{account_id}", response_model=VictimInvestigationResponse)
def get_victim_investigation(
    account_id: str,
    max_hops: int = Query(4, ge=1, le=6, description="Maximum downstream attribution hops"),
    horizon_seconds: Optional[int] = Query(None, ge=1, description="Attribution horizon per hop in seconds"),
    max_branches_per_hop: int = Query(50, ge=1, le=200, description="Maximum branching fanout per hop")
):
    """
    Step 6: Blind Victim Investigation Endpoint for Operation 'ABHEDYA-CHAKRA'.
    Orchestrates account validation, transaction correlation, L1/L2/L3 role classification,
    Step 5B Mule Risk Index, Step 5A velocity evidence, Step 5C temporal FIFO 4-hop money trace,
    and terminal recipient identification.
    """
    con = get_db()
    try:
        return investigate_victim_account(
            con,
            account_id,
            max_hops=max_hops,
            horizon_seconds=horizon_seconds,
            max_branches_per_hop=max_branches_per_hop
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/case-files", response_model=CaseFileResponse)
def create_case_file(req: CaseFileRequest):
    """
    Step 7: Compiles a reproducible, evidence-grounded forensic case file and compiled package.
    """
    con = get_db()
    try:
        return generate_forensic_case_file(con, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Case file generation error: {str(e)}")


@router.get("/case-files/{case_file_id}", response_model=CaseFileResponse)
def get_case_file_metadata(case_file_id: str):
    """
    Step 7: Retrieves metadata for a previously generated forensic case file.
    """
    cf_id = case_file_id.strip()
    resp = CASE_FILE_STORE.get_response(cf_id)
    if resp:
        return resp
    # If not in store, attempt to reconstruct if valid format: CASE-{account}-{hash}
    parts = cf_id.split("-")
    if len(parts) >= 3 and parts[0] == "CASE":
        acc = parts[1]
        con = get_db()
        try:
            return generate_forensic_case_file(con, CaseFileRequest(account_number=acc))
        except Exception:
            pass
    raise HTTPException(status_code=404, detail=f"Case file '{cf_id}' not found")


@router.get("/case-files/{case_file_id}/pdf")
def download_case_file_pdf(case_file_id: str):
    """
    Step 7: Downloads the compiled forensic PDF case report.
    """
    cf_id = case_file_id.strip()
    pdf_bytes = CASE_FILE_STORE.get_pdf(cf_id)
    if not pdf_bytes:
        # Reconstruct on demand
        parts = cf_id.split("-")
        if len(parts) >= 3 and parts[0] == "CASE":
            acc = parts[1]
            con = get_db()
            try:
                generate_forensic_case_file(con, CaseFileRequest(account_number=acc, include_pdf=True))
                pdf_bytes = CASE_FILE_STORE.get_pdf(cf_id)
            except Exception:
                pass
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail=f"PDF for case file '{cf_id}' not found")

    safe_filename = f"abhedya_case_{cf_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )


@router.get("/case-files/{case_file_id}/json")
def download_case_file_json(case_file_id: str):
    """
    Step 7: Downloads the complete JSON evidence package.
    """
    cf_id = case_file_id.strip()
    json_bytes = CASE_FILE_STORE.get_json(cf_id)
    if not json_bytes:
        # Reconstruct on demand
        parts = cf_id.split("-")
        if len(parts) >= 3 and parts[0] == "CASE":
            acc = parts[1]
            con = get_db()
            try:
                generate_forensic_case_file(con, CaseFileRequest(account_number=acc, include_json=True))
                json_bytes = CASE_FILE_STORE.get_json(cf_id)
            except Exception:
                pass
    if not json_bytes:
        raise HTTPException(status_code=404, detail=f"Evidence JSON for case file '{cf_id}' not found")

    safe_filename = f"abhedya_evidence_{cf_id}.json"
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )

# ==============================================================================
# Step 8: Case Diary + AI-Assisted Officer Narrative
# ==============================================================================

@router.post("/case-diaries", response_model=CaseDiaryResponse)
def create_case_diary(req: CaseDiaryRequest):
    """
    Step 8: Creates a Case Diary for a subject account.

    Pipeline:
    1. Run investigation (Step 6 engine)
    2. Extract deterministic VerifiedFacts
    3. Build timestamp-sorted chronology
    4. Extract DiaryFindings (risk, role, velocity, attribution)
    5. Optionally generate AI narrative (Gemini or deterministic fallback)
    6. Validate narrative (hallucination guardrail)
    7. Store in process-local store

    FORENSIC RULE: AI narrative is an interpretation layer only.
    The AI does NOT create, modify, or independently establish evidence.

    Process-local persistence: case diaries are not retained across backend restarts.
    """
    con = get_db()
    try:
        return build_case_diary(con, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Case diary generation error: {str(e)}")


@router.get("/case-diaries/{diary_id}", response_model=CaseDiaryResponse)
def get_case_diary(diary_id: str):
    """
    Step 8: Retrieves a previously generated case diary from process-local storage.

    Returns 404 if the diary is not found (e.g., after a backend restart).
    """
    d_id = diary_id.strip()
    diary = CASE_DIARY_STORE.get(d_id)
    if diary is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Case diary '{d_id}' not found in process-local store. "
                "Case diaries are not persistent across backend restarts. "
                "Use POST /api/case-diaries to regenerate."
            )
        )
    import time
    return CaseDiaryResponse(case_diary=diary, generation_time_ms=0.0)


@router.post("/case-diaries/{diary_id}/generate-narrative", response_model=CaseDiaryResponse)
def generate_case_diary_narrative(diary_id: str, req: GenerateNarrativeRequest):
    """
    Step 8: (Re)generates the AI-assisted narrative for an existing case diary.

    Uses the same verified facts already extracted during diary creation.
    Does not re-run the full investigation.

    If force_deterministic=True, skips AI and uses the deterministic fallback.
    If GEMINI_API_KEY is not configured, deterministic fallback is used automatically.

    FORENSIC RULE: AI narrative is derived from pre-extracted verified evidence only.
    """
    d_id = diary_id.strip()
    try:
        return regenerate_narrative(d_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Narrative generation error: {str(e)}")
