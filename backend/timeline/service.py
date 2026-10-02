"""
Timeline Investigation Service for Operation 'ABHEDYA-CHAKRA' (Step 10A)
"""

from typing import Optional, List, Dict, Any, Tuple
import duckdb

from backend.timeline.models import (
    TimelineEventType,
    TimelineEvent,
    TimelineSummary,
    TimelineRange,
    TimelineResponse,
    TimelineProvenance,
)
from backend.detection.velocity_detector import get_velocity_events
from backend.detection.risk_scoring import get_account_risk
from backend.detection.role_classifier import get_account_role
from backend.attribution import compute_account_fifo_attribution


def build_timeline(
    con: duckdb.DuckDBPyConnection,
    account_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    direction: str = "all",
    payment_mode: str = "all",
    device_type: str = "all",
    event_type: str = "all",
    page: int = 1,
    page_size: int = 50,
) -> TimelineResponse:
    """
    Constructs an investigator-grade chronological event stream across 
    transactions, velocity alerts, FIFO fund attributions, and risk findings.
    """
    effective_start = start_time.strip() if start_time and start_time.strip() else "2026-09-15 00:00:00"
    effective_end = end_time.strip() if end_time and end_time.strip() else "2026-09-29 23:59:58"
    acc = account_id.strip().upper() if account_id and account_id.strip() else None

    events: List[TimelineEvent] = []
    summary_tx_count = 0
    summary_inflow = 0.0
    summary_outflow = 0.0
    velocity_count = 0
    attribution_count = 0
    terminal_count = 0
    risk_findings: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # 1. QUERY TRANSACTIONS
    # ------------------------------------------------------------------
    tx_where = ["Timestamp >= ? AND Timestamp <= ?"]
    tx_params: List[Any] = [effective_start, effective_end]

    if acc:
        if direction.lower() == "in":
            tx_where.append("Receiver_Account = ?")
            tx_params.append(acc)
        elif direction.lower() == "out":
            tx_where.append("Sender_Account = ?")
            tx_params.append(acc)
        else:
            tx_where.append("(Sender_Account = ? OR Receiver_Account = ?)")
            tx_params.extend([acc, acc])

    if payment_mode and payment_mode.lower() != "all":
        tx_where.append("Payment_Mode = ?")
        tx_params.append(payment_mode.upper())

    if device_type and device_type.lower() != "all":
        tx_where.append("Device_Type = ?")
        tx_params.append(device_type)

    where_sql = " AND ".join(tx_where)

    # Summary aggregations
    sum_query = f"""
        SELECT 
            COUNT(*),
            COALESCE(SUM(CASE WHEN Receiver_Account = '{acc}' THEN Amount ELSE (CASE WHEN '{acc}' = 'None' THEN Amount ELSE 0.0 END) END), 0.0),
            COALESCE(SUM(CASE WHEN Sender_Account = '{acc}' THEN Amount ELSE 0.0 END), 0.0)
        FROM transactions
        WHERE {where_sql}
    """ if acc else f"""
        SELECT 
            COUNT(*),
            COALESCE(SUM(Amount), 0.0),
            0.0
        FROM transactions
        WHERE {where_sql}
    """
    sum_row = con.execute(sum_query, tx_params).fetchone()
    if sum_row:
        summary_tx_count = sum_row[0] or 0
        summary_inflow = float(sum_row[1] or 0.0)
        summary_outflow = float(sum_row[2] or 0.0)

    # Fetch transactions (bounded to prevent runaway memory if global)
    limit_clause = "LIMIT 1000" if not acc else "LIMIT 5000"
    tx_rows = con.execute(f"""
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
        ORDER BY Timestamp ASC, rowid ASC
        {limit_clause}
    """, tx_params).fetchall()

    for r in tx_rows:
        row_id, tx_id, sender, receiver, s_ifsc, r_ifsc, amt, ts, pm, narr, ip, dev = r
        ts_str = str(ts)
        float_amt = float(amt) if amt is not None else 0.0

        dir_str = "OBSERVED"
        if acc:
            if receiver == acc:
                dir_str = "INCOMING"
            elif sender == acc:
                dir_str = "OUTGOING"

        events.append(TimelineEvent(
            event_id=f"tx_{row_id}_{tx_id}",
            event_type=TimelineEventType.TRANSACTION,
            timestamp=ts_str,
            title=f"Transaction: ₹{float_amt:,.2f} via {pm}",
            description=f"{sender} -> {receiver} [{pm}]",
            amount=round(float_amt, 2),
            direction=dir_str,
            source_account=sender,
            destination_account=receiver,
            transaction_id=tx_id,
            source_row_id=row_id,
            payment_mode=pm,
            device_type=dev,
            ip_address=ip,
            sender_ifsc=s_ifsc,
            receiver_ifsc=r_ifsc,
            narration=narr,
            details={
                "sender": sender,
                "receiver": receiver,
                "amount": round(float_amt, 2),
                "payment_mode": pm,
                "timestamp": ts_str,
                "row_id": row_id
            }
        ))

    # ------------------------------------------------------------------
    # 2. QUERY VELOCITY, ATTRIBUTION & RISK FINDINGS (when account supplied)
    # ------------------------------------------------------------------
    if acc:
        # A. Velocity Events
        try:
            vel_resp = get_velocity_events(con, acc)
            for ve in vel_resp.events:
                ts_str = str(ve.timestamp)
                if effective_start <= ts_str <= effective_end:
                    delay_mins = round(ve.delay_seconds / 60.0, 2)
                    if ve.delay_seconds < 180:
                        window_cls = "<3 min"
                    elif 180 <= ve.delay_seconds <= 900:
                        window_cls = "3–15 min"
                    else:
                        window_cls = ">15 min"

                    events.append(TimelineEvent(
                        event_id=f"vel_{acc}_{ve.outgoing_tx_id}_{ts_str}",
                        event_type=TimelineEventType.VELOCITY,
                        timestamp=ts_str,
                        title=f"Velocity Alert ({window_cls}): ₹{ve.attributed_amount:,.2f}",
                        description=f"Rapid pass-through: {delay_mins}m ({ve.delay_seconds:.0f}s). Qualifying Step 5A: {ve.qualifies_step5a}",
                        amount=round(ve.attributed_amount, 2),
                        direction="OUTGOING",
                        source_account=acc,
                        transaction_id=ve.outgoing_tx_id,
                        details={
                            "outgoing_tx_id": ve.outgoing_tx_id,
                            "incoming_tx_ids": ve.incoming_tx_ids,
                            "delay_seconds": ve.delay_seconds,
                            "delay_minutes": delay_mins,
                            "window_classification": window_cls,
                            "qualifies_step5a": ve.qualifies_step5a,
                            "attributed_amount": ve.attributed_amount
                        }
                    ))
                    velocity_count += 1
        except Exception:
            pass

        # B. FIFO Attribution Events
        try:
            fifo_resp = compute_account_fifo_attribution(con, acc)
            for edge in fifo_resp.attributed_edges:
                ts_str = str(edge.outflow_timestamp)
                if effective_start <= ts_str <= effective_end:
                    events.append(TimelineEvent(
                        event_id=f"attr_{acc}_{edge.flow_id}_{ts_str}",
                        event_type=TimelineEventType.ATTRIBUTION,
                        timestamp=ts_str,
                        title=f"FIFO Flow ({edge.edge_type}): ₹{edge.attributed_amount:,.2f}",
                        description=f"Attributed to {edge.destination_account} (Hop {edge.hop}, delta {edge.time_delta_seconds:.0f}s)",
                        amount=round(edge.attributed_amount, 2),
                        direction="OUTGOING",
                        source_account=edge.source_account,
                        destination_account=edge.destination_account,
                        transaction_id=edge.outflow_tx_id,
                        details={
                            "edge_type": edge.edge_type,
                            "hop": edge.hop,
                            "flow_id": edge.flow_id,
                            "inflow_tx_id": edge.inflow_tx_id,
                            "outflow_tx_id": edge.outflow_tx_id,
                            "time_delta_seconds": edge.time_delta_seconds,
                            "attributed_amount": edge.attributed_amount
                        }
                    ))
                    attribution_count += 1
        except Exception:
            pass

        # C. Risk & Role Assessment
        try:
            risk = get_account_risk(con, acc)
            role = get_account_role(con, acc)

            # Get first transaction timestamp as risk event anchor
            dim_row = con.execute(
                "SELECT first_seen_timestamp, last_seen_timestamp FROM accounts_dimension WHERE account_number = ?",
                [acc]
            ).fetchone()
            first_ts = str(dim_row[0]) if dim_row and dim_row[0] else effective_start
            last_ts = str(dim_row[1]) if dim_row and dim_row[1] else effective_end

            risk_score = round(risk.risk_index, 1) if risk else None
            risk_band = risk.risk_band if risk else "UNKNOWN"
            role_str = role.role if role else "NONE"

            if risk and effective_start <= first_ts <= effective_end:
                events.append(TimelineEvent(
                    event_id=f"risk_{acc}",
                    event_type=TimelineEventType.RISK_ROLE,
                    timestamp=first_ts,
                    title=f"Forensic Assessment: Mule Risk {risk_score}/100 ({risk_band})",
                    description=f"Identified Role: {role_str}. Risk and velocity indicators assessed.",
                    source_account=acc,
                    details={
                        "mule_risk_score": risk_score,
                        "risk_band": risk_band,
                        "role": role_str,
                        "layer1": role.layer1 if role else False,
                        "layer2": role.layer2 if role else False,
                        "layer3": role.layer3 if role else False,
                    }
                ))

            risk_findings = {
                "mule_risk_score": risk_score,
                "risk_band": risk_band,
                "role": role_str,
            }

            # D. Terminal Sink Finding
            if role and role.layer3 and not role.layer1 and not role.layer2:
                if effective_start <= last_ts <= effective_end:
                    events.append(TimelineEvent(
                        event_id=f"term_{acc}",
                        event_type=TimelineEventType.TERMINAL,
                        timestamp=last_ts,
                        title=f"Terminal Sink Identified: {acc}",
                        description="Account identified as terminal absorption point with no recorded forward velocity.",
                        source_account=acc,
                        details={
                            "account_id": acc,
                            "terminal_indicator": True,
                            "timestamp": last_ts
                        }
                    ))
                    terminal_count += 1
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 3. FILTER BY EVENT TYPE
    # ------------------------------------------------------------------
    filtered_events = events
    if event_type and event_type.lower() != "all":
        target_type = event_type.upper()
        filtered_events = [e for e in events if e.event_type.value == target_type]

    # ------------------------------------------------------------------
    # 4. DETERMINISTIC SORTING & TIE-BREAKING
    # ------------------------------------------------------------------
    # Primary: timestamp ASC, Secondary: row_id ASC, Tertiary: event_id
    filtered_events.sort(key=lambda e: (
        e.timestamp,
        e.source_row_id if e.source_row_id is not None else -1,
        e.event_id
    ))

    # ------------------------------------------------------------------
    # 5. SERVER-SIDE PAGINATION
    # ------------------------------------------------------------------
    total_events = len(filtered_events)
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 250))
    start_idx = (safe_page - 1) * safe_page_size
    end_idx = start_idx + safe_page_size
    page_items = filtered_events[start_idx:end_idx]
    has_more = end_idx < total_events

    summary = TimelineSummary(
        total_events=total_events,
        transaction_count=summary_tx_count,
        incoming_volume=round(summary_inflow, 2),
        outgoing_volume=round(summary_outflow, 2),
        net_volume=round(summary_inflow - summary_outflow, 2),
        velocity_event_count=velocity_count,
        attribution_event_count=attribution_count,
        terminal_event_count=terminal_count,
        risk_role_findings=risk_findings
    )

    return TimelineResponse(
        account_id=acc,
        range=TimelineRange(
            start_time=effective_start,
            end_time=effective_end,
            dataset_min_time="2026-09-15 00:00:00",
            dataset_max_time="2026-09-29 23:59:58"
        ),
        summary=summary,
        events=page_items,
        page=safe_page,
        page_size=safe_page_size,
        total_events=total_events,
        has_more=has_more,
        provenance=TimelineProvenance()
    )
