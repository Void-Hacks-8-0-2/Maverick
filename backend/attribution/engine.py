"""
Temporal FIFO Attribution Engine for Operation 'ABHEDYA-CHAKRA'
Step 5C: Deterministic, Explainable, Amount-Conserving Money-Flow Attribution.

Core Invariants:
1. Source Conservation: SUM(attributed from source) <= source_amount.
2. Destination Conservation: SUM(attributed to destination) <= destination_amount.
3. Chronological Causality: source_timestamp <= destination_timestamp (and source_row_id < destination_row_id for ties).
4. No Self-Funding: source_row_id != destination_row_id.
5. Horizon Enforcement: elapsed seconds <= configured horizon_seconds.
6. Zero Fabrication: Unattributed amounts are explicitly reported as unallocated.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
import duckdb

from backend.attribution.config import AttributionPolicyConfig, DEFAULT_ATTRIBUTION_CONFIG
from backend.attribution.models import (
    AttributionRecord,
    UnallocatedOutflowRecord,
    AccountAttributionResponse,
    AttributionTraceResponse,
    TraceAttributionNode,
    TraceHopSummary,
    TransactionAttributionResponse
)


def _format_ts(ts: Any) -> str:
    """Format DuckDB timestamp into ISO-8601 string."""
    if ts is None:
        return "NA"
    return str(ts).replace(" ", "T")


def compute_account_fifo_attribution(
    con: duckdb.DuckDBPyConnection,
    account_id: str,
    config: AttributionPolicyConfig = DEFAULT_ATTRIBUTION_CONFIG,
    horizon_seconds: Optional[int] = None
) -> AccountAttributionResponse:
    """
    Computes exact chronological FIFO attribution for a single account.
    Conserves monetary amounts and tracks unallocated outflows without fabricating sources.
    """
    acc = account_id.strip()
    active_horizon = horizon_seconds if horizon_seconds is not None else config.horizon_seconds

    # Query all incoming transactions into this account
    in_query = """
        SELECT rowid, Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp
        FROM transactions
        WHERE Receiver_Account = ?
        ORDER BY Timestamp ASC, rowid ASC, Transaction_ID ASC
    """
    in_rows = con.execute(in_query, [acc]).fetchall()

    # Query all outgoing transactions from this account
    out_query = """
        SELECT rowid, Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp
        FROM transactions
        WHERE Sender_Account = ?
        ORDER BY Timestamp ASC, rowid ASC, Transaction_ID ASC
    """
    out_rows = con.execute(out_query, [acc]).fetchall()

    # Initialize incoming pool: [row_id, tx_id, sender, receiver, original_amount, remaining_amount, timestamp]
    in_pool: List[List[Any]] = []
    total_in_vol = 0.0
    for r in in_rows:
        amt = float(r[4]) if r[4] is not None else 0.0
        total_in_vol += amt
        in_pool.append([int(r[0]), str(r[1]), str(r[2]), str(r[3]), amt, amt, r[5]])

    total_out_vol = 0.0
    for r in out_rows:
        total_out_vol += float(r[4]) if r[4] is not None else 0.0

    attribution_records: List[AttributionRecord] = []
    unallocated_records: List[UnallocatedOutflowRecord] = []
    total_attributed_vol = 0.0
    total_unallocated_vol = 0.0

    in_len = len(in_pool)

    # Process each outgoing transaction in chronological FIFO order
    for out in out_rows:
        out_row_id = int(out[0])
        out_tx_id = str(out[1])
        out_sender = str(out[2])
        out_receiver = str(out[3])
        out_amount = round(float(out[4]), 2) if out[4] is not None else 0.0
        out_ts = out[5]

        needed_paise = round(out_amount * 100)
        attributed_paise_for_out = 0
        had_eligible_pool = False
        expired_by_horizon = False

        for inc in in_pool:
            inc_row_id = inc[0]
            inc_tx_id = inc[1]
            inc_sender = inc[2]
            inc_orig_amt = inc[4]
            inc_rem = inc[5]
            inc_ts = inc[6]

            # Enforce strict temporal ordering
            if inc_ts > out_ts:
                # Inflow occurs strictly after outflow -> stop searching (pool is sorted asc)
                break
            if inc_ts == out_ts and inc_row_id >= out_row_id:
                # Same timestamp tie-breaking: source must have smaller row_id and never self-fund
                continue

            # Check attribution horizon if configured
            delta_sec = (out_ts - inc_ts).total_seconds()
            if active_horizon is not None and delta_sec > active_horizon:
                expired_by_horizon = True
                continue

            had_eligible_pool = True

            inc_rem_paise = round(inc_rem * 100)
            if inc_rem_paise <= 0:
                continue

            take_paise = min(inc_rem_paise, needed_paise)
            if take_paise <= 0:
                continue

            take = take_paise / 100.0
            inc[5] = round((inc_rem_paise - take_paise) / 100.0, 2)
            needed_paise -= take_paise
            attributed_paise_for_out += take_paise

            attr_record = AttributionRecord(
                attribution_id=f"ATTR_{inc_row_id}_{out_row_id}_H1",
                source_row_id=inc_row_id,
                source_transaction_id=inc_tx_id,
                source_account=inc_sender,
                intermediary_account=acc,
                source_timestamp=_format_ts(inc_ts),
                source_amount=inc_orig_amt,
                destination_row_id=out_row_id,
                destination_transaction_id=out_tx_id,
                destination_account=out_receiver,
                destination_timestamp=_format_ts(out_ts),
                destination_amount=out_amount,
                attributed_amount=take,
                delay_seconds=delta_sec,
                hop_number=1,
                edge_type="FIFO_ATTRIBUTION",
                attribution_policy=config.policy_name,
                attribution_policy_version=config.policy_version,
                provenance=config.provenance,
            )
            attribution_records.append(attr_record)

            if needed_paise <= 0:
                break

        attributed_for_out = attributed_paise_for_out / 100.0
        total_attributed_vol = round(total_attributed_vol + attributed_for_out, 2)

        # Check for unallocated remainder
        if needed_paise > 0:
            unallocated = needed_paise / 100.0
            total_unallocated_vol = round(total_unallocated_vol + unallocated, 2)
            
            if attributed_for_out == 0.0 and not had_eligible_pool:
                reason = "HORIZON_EXCEEDED" if expired_by_horizon else "NO_PRIOR_INFLOW"
            else:
                reason = "INFLOW_DEPLETED"

            unallocated_records.append(UnallocatedOutflowRecord(
                destination_row_id=out_row_id,
                destination_transaction_id=out_tx_id,
                destination_account=out_receiver,
                destination_timestamp=_format_ts(out_ts),
                destination_amount=out_amount,
                attributed_amount=attributed_for_out,
                unallocated_amount=unallocated,
                reason=reason
            ))

    return AccountAttributionResponse(
        account_id=acc,
        policy_name=config.policy_name,
        policy_version=config.policy_version,
        horizon_seconds=active_horizon,
        total_incoming_volume=round(total_in_vol, 2),
        total_outgoing_volume=round(total_out_vol, 2),
        total_attributed_volume=round(total_attributed_vol, 2),
        total_unallocated_outflow=round(total_unallocated_vol, 2),
        incoming_transaction_count=len(in_rows),
        outgoing_transaction_count=len(out_rows),
        attribution_edge_count=len(attribution_records),
        attribution_records=attribution_records,
        unallocated_records=unallocated_records,
        provenance=config.provenance,
        disclaimer=config.disclaimer
    )


def trace_fifo_attribution_4hop(
    con: duckdb.DuckDBPyConnection,
    root_account: str,
    root_row_id: Optional[int] = None,
    max_hops: int = 4,
    horizon_seconds: Optional[int] = None,
    config: AttributionPolicyConfig = DEFAULT_ATTRIBUTION_CONFIG
) -> AttributionTraceResponse:
    """
    Forensic 4-Hop Temporal Money-Flow Attribution Traversal.
    Strictly follows temporal attribution: funds at Hop N+1 must be attributed
    to the specific incoming transactions delivered at Hop N.
    """
    root_acc = root_account.strip()
    effective_max_hops = min(max_hops, config.max_hops_limit)
    active_horizon = horizon_seconds if horizon_seconds is not None else config.horizon_seconds

    nodes_map: Dict[str, TraceAttributionNode] = {
        root_acc: TraceAttributionNode(
            id=root_acc,
            type="account",
            is_root=True,
            hop=0,
            inflow_attributed=0.0,
            outflow_attributed=0.0
        )
    }
    all_edges: List[AttributionRecord] = []
    hop_summaries: List[TraceHopSummary] = []
    truncated = False
    truncation_reason: Optional[str] = None
    cycles_detected: List[str] = []

    # Step 1: Get originating outgoing transactions from root
    if root_row_id is not None:
        root_out_query = """
            SELECT rowid, Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp
            FROM transactions
            WHERE rowid = ? AND Sender_Account = ?
        """
        root_out_rows = con.execute(root_out_query, [root_row_id, root_acc]).fetchall()
    else:
        root_out_query = """
            SELECT rowid, Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp
            FROM transactions
            WHERE Sender_Account = ?
            ORDER BY Timestamp ASC, rowid ASC
            LIMIT ?
        """
        # Fetch max_branches_per_hop + 1 to detect whether truncation occurred
        root_out_rows = con.execute(root_out_query, [root_acc, config.max_branches_per_hop + 1]).fetchall()
        if len(root_out_rows) > config.max_branches_per_hop:
            truncated = True
            truncation_reason = "ROOT_OUTGOING_BRANCH_LIMIT"
            root_out_rows = root_out_rows[:config.max_branches_per_hop]

    if not root_out_rows:
        return AttributionTraceResponse(
            root_account=root_acc,
            root_row_id=root_row_id,
            root_transaction_id=None,
            max_hops=effective_max_hops,
            horizon_seconds=active_horizon,
            policy_name=config.policy_name,
            policy_version=config.policy_version,
            total_attributed_amount=0.0,
            total_hops_found=0,
            nodes=list(nodes_map.values()),
            edges=[],
            hop_summaries=[],
            truncated=False,
            cycles_detected=[],
            provenance=config.provenance,
            disclaimer=config.disclaimer
        )

    # active_inflows_at_hop: maps account_number -> list of eligible [row_id, tx_id, sender, amount, remaining, timestamp, branch_path]
    # At Hop 1, each root_out_row is delivered to its receiver
    current_hop_inflows: Dict[str, List[List[Any]]] = {}

    for row in root_out_rows:
        r_id, t_id, s_acc, r_acc, amt, ts = row
        f_amt = round(float(amt), 2) if amt is not None else 0.0

        # Hop 1 Root Seed edge
        edge = AttributionRecord(
            attribution_id=f"ATTR_ROOT_{r_id}_H1",
            source_row_id=r_id,
            source_transaction_id=t_id,
            source_account=s_acc,
            intermediary_account=s_acc,
            source_timestamp=_format_ts(ts),
            source_amount=f_amt,
            destination_row_id=r_id,
            destination_transaction_id=t_id,
            destination_account=r_acc,
            destination_timestamp=_format_ts(ts),
            destination_amount=f_amt,
            attributed_amount=f_amt,
            delay_seconds=0.0,
            hop_number=1,
            edge_type="ROOT_SEED",
            attribution_policy=config.policy_name,
            attribution_policy_version=config.policy_version,
            provenance=config.provenance
        )
        all_edges.append(edge)

        nodes_map[root_acc].outflow_attributed = round(nodes_map[root_acc].outflow_attributed + f_amt, 2)
        if r_acc not in nodes_map:
            nodes_map[r_acc] = TraceAttributionNode(
                id=r_acc,
                type="account",
                is_root=False,
                hop=1,
                inflow_attributed=f_amt,
                outflow_attributed=0.0
            )
        else:
            nodes_map[r_acc].inflow_attributed = round(nodes_map[r_acc].inflow_attributed + f_amt, 2)

        # Register inflow pool for Hop 2 at r_acc with path-aware history
        initial_path = (root_acc, r_acc)
        current_hop_inflows.setdefault(r_acc, []).append([int(r_id), str(t_id), str(s_acc), f_amt, f_amt, ts, initial_path])

    current_hop = 1

    # Traverse downstream hops 2, 3, 4
    while current_hop < effective_max_hops and current_hop_inflows:
        next_hop = current_hop + 1
        next_hop_inflows: Dict[str, List[List[Any]]] = {}

        for intermediary_acc, eligible_inflows in list(current_hop_inflows.items()):
            if len(all_edges) >= config.max_trace_edges:
                truncated = True
                if not truncation_reason:
                    truncation_reason = f"Exceeded maximum trace edges ({config.max_trace_edges})"
                break

            # Fetch outgoing transactions from intermediary_acc (fetch limit + 1 to detect truncation)
            out_query = """
                SELECT rowid, Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp
                FROM transactions
                WHERE Sender_Account = ?
                ORDER BY Timestamp ASC, rowid ASC
                LIMIT ?
            """
            out_rows = con.execute(out_query, [intermediary_acc, config.max_branches_per_hop + 1]).fetchall()
            if len(out_rows) > config.max_branches_per_hop:
                truncated = True
                if not truncation_reason:
                    truncation_reason = f"ACCOUNT_OUTGOING_BRANCH_LIMIT:{intermediary_acc}"
                out_rows = out_rows[:config.max_branches_per_hop]

            if not out_rows:
                continue

            # Sort eligible inflows chronologically
            eligible_inflows.sort(key=lambda x: (x[5], x[0]))

            for out_row in out_rows:
                out_r_id, out_t_id, out_s, out_r, out_a, out_ts = out_row
                out_needed_paise = round(float(out_a) * 100)

                for inc in eligible_inflows:
                    inc_rem_paise = round(inc[4] * 100)
                    if inc_rem_paise <= 0:
                        continue
                    if inc[5] > out_ts or (inc[5] == out_ts and inc[0] >= out_r_id):
                        break

                    delta_sec = (out_ts - inc[5]).total_seconds()
                    if active_horizon is not None and delta_sec > active_horizon:
                        continue

                    take_paise = min(inc_rem_paise, out_needed_paise)
                    if take_paise <= 0:
                        continue

                    take = take_paise / 100.0
                    inc[4] = round((inc_rem_paise - take_paise) / 100.0, 2)
                    out_needed_paise -= take_paise

                    edge = AttributionRecord(
                        attribution_id=f"ATTR_{inc[0]}_{out_r_id}_H{next_hop}",
                        source_row_id=inc[0],
                        source_transaction_id=inc[1],
                        source_account=inc[2],
                        intermediary_account=intermediary_acc,
                        source_timestamp=_format_ts(inc[5]),
                        source_amount=inc[3],
                        destination_row_id=out_r_id,
                        destination_transaction_id=out_t_id,
                        destination_account=out_r,
                        destination_timestamp=_format_ts(out_ts),
                        destination_amount=round(float(out_a), 2),
                        attributed_amount=take,
                        delay_seconds=delta_sec,
                        hop_number=next_hop,
                        edge_type="FIFO_ATTRIBUTION",
                        attribution_policy=config.policy_name,
                        attribution_policy_version=config.policy_version,
                        provenance=config.provenance
                    )
                    all_edges.append(edge)

                    # Update node flow tracking
                    nodes_map[intermediary_acc].outflow_attributed = round(nodes_map[intermediary_acc].outflow_attributed + take, 2)
                    if out_r not in nodes_map:
                        nodes_map[out_r] = TraceAttributionNode(
                            id=out_r,
                            type="account",
                            is_root=False,
                            hop=next_hop,
                            inflow_attributed=take,
                            outflow_attributed=0.0
                        )
                    else:
                        nodes_map[out_r].inflow_attributed = round(nodes_map[out_r].inflow_attributed + take, 2)

                    # Path-aware cycle detection
                    branch_path = inc[6]
                    if out_r in branch_path:
                        cycle_path_str = f"{' -> '.join(branch_path)} -> {out_r}"
                        if cycle_path_str not in cycles_detected:
                            cycles_detected.append(cycle_path_str)
                        # Do not enqueue this branch for further downstream traversal
                    else:
                        # Queue for next hop with extended path
                        next_hop_inflows.setdefault(out_r, []).append([
                            int(out_r_id), str(out_t_id), intermediary_acc, take, take, out_ts, branch_path + (out_r,)
                        ])

                    if out_needed_paise <= 0:
                        break

                if truncated and len(all_edges) >= config.max_trace_edges:
                    break

            if truncated and len(all_edges) >= config.max_trace_edges:
                break

        current_hop_inflows = next_hop_inflows
        current_hop += 1

    # Build hop summaries
    hop_groups: Dict[int, List[AttributionRecord]] = {}
    for e in all_edges:
        hop_groups.setdefault(e.hop_number, []).append(e)

    for h in sorted(hop_groups.keys()):
        h_edges = hop_groups[h]
        for e in h_edges:
            hop_summaries.append(TraceHopSummary(
                hop_number=h,
                sender_account=e.intermediary_account if h > 1 else e.source_account,
                receiver_account=e.destination_account,
                attributed_amount=e.attributed_amount,
                edge_count=1
            ))

    max_hop_depth = max(e.hop_number for e in all_edges) if all_edges else 0

    return AttributionTraceResponse(
        root_account=root_acc,
        root_row_id=root_row_id,
        root_transaction_id=str(root_out_rows[0][1]) if (root_row_id is not None and root_out_rows) else None,
        max_hops=effective_max_hops,
        horizon_seconds=active_horizon,
        policy_name=config.policy_name,
        policy_version=config.policy_version,
        total_attributed_amount=round(sum(e.attributed_amount for e in all_edges), 2),
        total_hops_found=max_hop_depth,
        nodes=list(nodes_map.values()),
        edges=all_edges,
        hop_summaries=hop_summaries,
        truncated=truncated,
        truncation_reason=truncation_reason,
        cycles_detected=cycles_detected,
        provenance=config.provenance,
        disclaimer=config.disclaimer
    )


def get_transaction_fifo_attribution(
    con: duckdb.DuckDBPyConnection,
    transaction_id: str,
    row_id: Optional[int] = None,
    config: AttributionPolicyConfig = DEFAULT_ATTRIBUTION_CONFIG
) -> TransactionAttributionResponse:
    """
    Retrieves attribution details for a specific transaction.
    Uses row_id to disambiguate duplicate Transaction_IDs.
    """
    t_id = transaction_id.strip()
    if row_id is not None:
        query = "SELECT rowid, Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp FROM transactions WHERE rowid = ? AND Transaction_ID = ?"
        rows = con.execute(query, [row_id, t_id]).fetchall()
    else:
        query = "SELECT rowid, Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp FROM transactions WHERE Transaction_ID = ? ORDER BY rowid ASC"
        rows = con.execute(query, [t_id]).fetchall()

    if not rows:
        raise ValueError(f"Transaction '{transaction_id}' (row_id={row_id}) not found")

    target = rows[0]
    t_row_id, t_tx_id, t_sender, t_receiver, t_amount, t_ts = target
    t_amount = float(t_amount)

    # Compute attribution for the sender account (outflow funding perspective)
    sender_dossier = compute_account_fifo_attribution(con, t_sender, config=config)
    matched = [e for e in sender_dossier.attribution_records if e.destination_row_id == t_row_id]
    attributed_amt = sum(e.attributed_amount for e in matched)
    unallocated = round(t_amount - attributed_amt, 2)

    return TransactionAttributionResponse(
        row_id=t_row_id,
        transaction_id=t_tx_id,
        account_number=t_sender,
        direction="OUTGOING",
        amount=t_amount,
        timestamp=_format_ts(t_ts),
        attributed_amount=round(attributed_amt, 2),
        remaining_or_unallocated_amount=max(0.0, unallocated),
        matched_attributions=matched,
        policy_name=config.policy_name,
        policy_version=config.policy_version,
        disclaimer=config.disclaimer
    )
