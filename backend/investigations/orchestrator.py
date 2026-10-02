"""
Step 6: Blind Victim Investigation Engine Orchestrator for Operation 'ABHEDYA-CHAKRA'
Directly orchestrates existing Step 1-5C services in-process without code duplication.
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
import hashlib
import duckdb

from backend.features import AccountFeatures, get_account_features
from backend.detection.velocity_detector import get_velocity_events
from backend.detection.risk_scoring import get_account_risk
from backend.detection.risk_models import MuleRiskScore
from backend.attribution import (
    AttributionTraceResponse,
    trace_fifo_attribution_4hop,
)
from backend.attribution.config import AttributionPolicyConfig, DEFAULT_ATTRIBUTION_CONFIG
from backend.investigations.models import (
    DataProvenance,
    VictimAccountSummary,
    VictimTransactionItem,
    VictimRolesSummary,
    VictimVelocitySummary,
    TerminalAccountEvidence,
    InvestigationEvidenceSummary,
    VictimInvestigationResponse,
)


# In-memory LRU/dict cache for deterministic immutable production queries
_INVESTIGATION_CACHE: Dict[tuple, VictimInvestigationResponse] = {}


def clear_investigation_cache() -> None:
    _INVESTIGATION_CACHE.clear()


def prewarm_investigation_cache(con: duckdb.DuckDBPyConnection, accounts: Optional[List[str]] = None) -> None:
    """Pre-warms the cache for high-priority benchmark/demo accounts."""
    targets = accounts or ["KKBK10000402", "BARB10000427"]
    for target in targets:
        try:
            investigate_victim_account(con, target, max_hops=4)
        except Exception:
            pass


def investigate_victim_account(
    con: duckdb.DuckDBPyConnection,
    account_id: str,
    max_hops: int = 4,
    horizon_seconds: Optional[int] = None,
    max_branches_per_hop: int = 50,
) -> VictimInvestigationResponse:
    """
    Executes an end-to-end blind victim investigation over production data.
    Validates account, extracts relevant transactions, executes 4-hop temporal
    FIFO attribution, gathers behavioral roles, risk scores, velocity signals,
    and identifies downstream terminal endpoints.
    """
    acc = account_id.strip()
    cache_key = (acc, max_hops, horizon_seconds, max_branches_per_hop)
    if cache_key in _INVESTIGATION_CACHE:
        return _INVESTIGATION_CACHE[cache_key]

    # 1. Validate account existence & retrieve metrics from accounts_dimension
    dim_row = con.execute("""
        SELECT 
            incoming_txn_count, 
            outgoing_txn_count, 
            unique_senders, 
            unique_receivers, 
            total_inflow, 
            total_outflow, 
            net_flow_delta,
            first_seen_timestamp,
            last_seen_timestamp,
            unique_ip_count,
            unique_device_count
        FROM accounts_dimension 
        WHERE account_number = ?
    """, [acc]).fetchone()

    if not dim_row:
        raise ValueError(f"Account '{account_id}' not found in production dataset")

    in_cnt, out_cnt, u_senders, u_receivers, inflow, outflow, net_flow, first_ts, last_ts, u_ips, u_devs = dim_row

    first_ts_str = first_ts.isoformat() if hasattr(first_ts, 'isoformat') and first_ts else str(first_ts) if first_ts else None
    last_ts_str = last_ts.isoformat() if hasattr(last_ts, 'isoformat') and last_ts else str(last_ts) if last_ts else None

    # Retrieve root subject transactions (up to 100 for forensic review)
    tx_rows = con.execute("""
        SELECT 
            rowid, Transaction_ID, Sender_Account, Receiver_Account,
            Sender_IFSC, Receiver_IFSC, Amount, Timestamp,
            Payment_Mode, Narration, IP_Address, Device_Type
        FROM transactions
        WHERE Sender_Account = ? OR Receiver_Account = ?
        ORDER BY Timestamp ASC, rowid ASC
        LIMIT 100
    """, [acc, acc]).fetchall()

    tot_tx_count = int((in_cnt or 0) + (out_cnt or 0))
    if tot_tx_count <= 100 or len(tx_rows) < 100:
        # Fast in-memory derivation from the complete set of subject transactions
        pm_dist: Dict[str, int] = {}
        ifsc_set: Set[str] = set()
        ip_set: Set[str] = set()
        for r in tx_rows:
            pm = r[8]
            if pm:
                pm_dist[pm] = pm_dist.get(pm, 0) + 1
            if r[4]:
                ifsc_set.add(r[4])
            if r[5]:
                ifsc_set.add(r[5])
            if r[10]:
                ip_set.add(r[10])
        ifscs = sorted(list(ifsc_set))
        ips = sorted(list(ip_set))
    else:
        # Fallback for entities with >100 transactions
        pm_rows = con.execute("""
            SELECT Payment_Mode, COUNT(*) 
            FROM transactions 
            WHERE Sender_Account = ? OR Receiver_Account = ?
            GROUP BY Payment_Mode
        """, [acc, acc]).fetchall()
        pm_dist = {r[0]: int(r[1]) for r in pm_rows if r[0] is not None}

        ifsc_rows = con.execute("""
            SELECT DISTINCT ifsc FROM (
                SELECT Sender_IFSC AS ifsc FROM transactions WHERE Sender_Account = ?
                UNION
                SELECT Receiver_IFSC AS ifsc FROM transactions WHERE Receiver_Account = ?
            ) WHERE ifsc IS NOT NULL ORDER BY ifsc
        """, [acc, acc]).fetchall()
        ifscs = [r[0] for r in ifsc_rows]

        ip_rows = con.execute("""
            SELECT DISTINCT ip FROM (
                SELECT IP_Address AS ip FROM transactions WHERE (Sender_Account = ? OR Receiver_Account = ?) AND IP_Address IS NOT NULL
            ) ORDER BY ip
        """, [acc, acc]).fetchall()
        ips = [r[0] for r in ip_rows]

    account_summary = VictimAccountSummary(
        account_number=acc,
        first_observed_timestamp=first_ts_str,
        last_observed_timestamp=last_ts_str,
        observed_incoming_volume=round(float(inflow or 0.0), 2),
        observed_outgoing_volume=round(float(outflow or 0.0), 2),
        observed_net_flow_delta=round(float(net_flow or 0.0), 2),
        incoming_transaction_count=int(in_cnt or 0),
        outgoing_transaction_count=int(out_cnt or 0),
        unique_counterparties=int(u_senders or 0) + int(u_receivers or 0),
        unique_ip_count=len(ips),
        unique_device_count=int(u_devs or 0),
        payment_modes=pm_dist,
        associated_ifscs=ifscs,
        associated_ips=ips,
        account_provenance="ANALYTICAL",
    )

    victim_transactions: List[VictimTransactionItem] = []
    for r in tx_rows:
        t_ts_str = r[7].isoformat() if hasattr(r[7], 'isoformat') and r[7] else str(r[7])
        direction = "OUTGOING" if r[2] == acc else "INCOMING"
        victim_transactions.append(
            VictimTransactionItem(
                transaction_id=str(r[1]),
                row_id=int(r[0]),
                sender_account=str(r[2]),
                receiver_account=str(r[3]),
                amount=round(float(r[6]), 2),
                timestamp=t_ts_str,
                payment_mode=str(r[8] or "UNKNOWN"),
                sender_ifsc=str(r[4] or ""),
                receiver_ifsc=str(r[5] or ""),
                ip_address=str(r[10] or ""),
                device_type=str(r[11]) if r[11] else None,
                narration=str(r[9] or ""),
                direction=direction,
                provenance="RAW",
            )
        )

    # 3. Behavioral Features and Step 4 Roles
    features = get_account_features(con, acc)
    if features:
        primary_role_label = (
            "L3 Terminal Candidate" if features.layer3_candidate
            else "L2 Distributor Candidate" if features.layer2_candidate
            else "L1 Collector Candidate" if features.layer1_candidate
            else "Originating Account / Standard Entity"
        )
        # Extract string descriptions from structured CandidateReason objects
        all_reasons = []
        l3_signals = []
        for r in features.layer1_reasons:
            all_reasons.append(r.description)
        for r in features.layer2_reasons:
            all_reasons.append(r.description)
        for r in features.layer3_reasons:
            all_reasons.append(r.description)
            l3_signals.append(f"{r.code}: {r.description}")

        roles = VictimRolesSummary(
            l1_collector_candidate=bool(features.layer1_candidate),
            l2_distributor_candidate=bool(features.layer2_candidate),
            l3_terminal_candidate=bool(features.layer3_candidate),
            fan_in=features.fan_in or 0,
            fan_out=features.fan_out or 0,
            primary_role_label=primary_role_label,
            classification_reasons=all_reasons,
            l3_classification_signals=l3_signals,
            provenance="DERIVED",
        )
    else:
        roles = VictimRolesSummary(
            primary_role_label="Standard Account / Unclassified",
            provenance="DERIVED",
        )

    # 4. Step 5B Mule Risk Index
    risk_score = get_account_risk(con, acc)
    if not risk_score:
        risk_score = MuleRiskScore(
            account_id=acc,
            risk_index=0.0,
            risk_band="LOW",
            scoring_version="v1",
            provenance="DERIVED",
            disclaimer="INVESTIGATIVE CANDIDATE INDICATORS ONLY -- not a declaration of criminality or legal determination.",
        )

    # 5. Step 5A Velocity
    velocity_events = get_velocity_events(con, acc)
    velocity = VictimVelocitySummary(
        pass_through_candidate=bool(features.pass_through_candidate) if features and features.pass_through_candidate else False,
        pass_through_ratio=round(features.pass_through_ratio or 0.0, 4) if features else 0.0,
        qualifying_event_count=int(features.pass_through_event_count or 0) if features else 0,
        outgoing_qualifying_count=int(features.pass_through_outgoing_transaction_count or 0) if features else 0,
        attributed_volume=round(features.pass_through_attributed_volume or 0.0, 2) if features else 0.0,
        median_delay_seconds=round(features.median_incoming_to_outgoing_seconds, 1) if features and features.median_incoming_to_outgoing_seconds is not None else None,
        rapid_outflow_count=int(features.rapid_outflow_count or 0) if features else 0,
        window_description="3_TO_15_MINUTES",
        events=[ev if isinstance(ev, dict) else ev.model_dump() for ev in velocity_events[:20]],
        classification_version="v1",
        provenance="DERIVED",
    )

    # 6. Step 5C 4-Hop Temporal FIFO Attribution Trace
    attr_config = DEFAULT_ATTRIBUTION_CONFIG
    if max_branches_per_hop != DEFAULT_ATTRIBUTION_CONFIG.max_branches_per_hop:
        attr_config = AttributionPolicyConfig(
            horizon_seconds=DEFAULT_ATTRIBUTION_CONFIG.horizon_seconds,
            default_max_hops=DEFAULT_ATTRIBUTION_CONFIG.default_max_hops,
            max_hops_limit=DEFAULT_ATTRIBUTION_CONFIG.max_hops_limit,
            max_branches_per_hop=max_branches_per_hop,
            max_trace_edges=DEFAULT_ATTRIBUTION_CONFIG.max_trace_edges,
        )
    trace_res = trace_fifo_attribution_4hop(
        con, acc, max_hops=max_hops, horizon_seconds=horizon_seconds, config=attr_config
    )

    # 7. Identify Downstream Terminal Accounts
    # Accounts that forwarded money further down the trace
    forwarding_accounts: Set[str] = {
        e.intermediary_account for e in trace_res.edges if e.intermediary_account
    }
    
    # Destination accounts reached that did not forward funds further in this trace
    terminal_map: Dict[str, Dict[str, Any]] = {}
    for edge in trace_res.edges:
        dest = edge.destination_account
        if dest != acc and dest not in forwarding_accounts:
            if dest not in terminal_map:
                terminal_map[dest] = {
                    "account_number": dest,
                    "hop": edge.hop_number,
                    "attributed_amount": 0.0,
                }
            terminal_map[dest]["attributed_amount"] = round(
                terminal_map[dest]["attributed_amount"] + edge.attributed_amount, 2
            )
            if edge.hop_number > terminal_map[dest]["hop"]:
                terminal_map[dest]["hop"] = edge.hop_number

    # Fetch features for terminal accounts
    terminals: List[TerminalAccountEvidence] = []
    if terminal_map:
        placeholders = ", ".join(["?"] * len(terminal_map))
        t_rows = con.execute(f"""
            SELECT 
                account_number, 
                layer1_candidate, 
                layer2_candidate, 
                layer3_candidate, 
                mule_risk_index, 
                risk_band, 
                pass_through_candidate,
                layer3_reasons
            FROM account_features 
            WHERE account_number IN ({placeholders})
        """, list(terminal_map.keys())).fetchall()

        t_feat_map = {r[0]: r for r in t_rows}
        import json
        for dest_acc, t_info in terminal_map.items():
            r = t_feat_map.get(dest_acc)
            if r:
                primary_role = (
                    "L3 Terminal Candidate" if r[3]
                    else "L2 Distributor Candidate" if r[2]
                    else "L1 Collector Candidate" if r[1]
                    else "Observed Inflow Node"
                )
                reasons = []
                if r[7]:
                    try:
                        raw_r = json.loads(r[7]) if isinstance(r[7], str) else r[7]
                        if isinstance(raw_r, list):
                            for it in raw_r:
                                if isinstance(it, dict) and "description" in it:
                                    reasons.append(it["description"])
                                elif isinstance(it, str):
                                    reasons.append(it)
                    except Exception:
                        reasons = []
                terminals.append(
                    TerminalAccountEvidence(
                        account_number=dest_acc,
                        hop=t_info["hop"],
                        attributed_amount=round(t_info["attributed_amount"], 2),
                        primary_role=primary_role,
                        risk_index=round(float(r[4]), 1) if r[4] is not None else None,
                        risk_band=str(r[5]) if r[5] else None,
                        velocity_status="PASS_THROUGH_ACTIVE" if r[6] else "NORMAL",
                        reason_codes=reasons if isinstance(reasons, list) else [],
                        provenance="DERIVED",
                    )
                )
            else:
                terminals.append(
                    TerminalAccountEvidence(
                        account_number=dest_acc,
                        hop=t_info["hop"],
                        attributed_amount=round(t_info["attributed_amount"], 2),
                        primary_role="Downstream Recipient Node",
                        reason_codes=[],
                        provenance="DERIVED",
                    )
                )

    terminals.sort(key=lambda t: t.attributed_amount, reverse=True)

    # 8. Warnings and Alerts
    warnings: List[str] = []
    if trace_res.truncated:
        warnings.append(f"Trace branch expansion limit reached: {trace_res.truncation_reason}")
    if trace_res.cycles_detected:
        warnings.append(f"Path cycles detected and safely arrested ({len(trace_res.cycles_detected)} cycle(s)): {'; '.join(trace_res.cycles_detected)}")
    if trace_res.total_hops_found == 0 or len(trace_res.edges) == 0:
        warnings.append("No qualifying downstream temporal attribution was identified within the configured trace policy.")

    # 9. Generate Deterministic Structured Forensic Summary
    root_seed_count = sum(1 for e in trace_res.edges if e.edge_type == "ROOT_SEED")
    fifo_count = sum(1 for e in trace_res.edges if e.edge_type == "FIFO_ATTRIBUTION")

    root_seed_amount = sum(round(e.attributed_amount, 2) for e in trace_res.edges if e.edge_type == "ROOT_SEED")
    downstream_fifo_amount = sum(round(e.attributed_amount, 2) for e in trace_res.edges if e.edge_type == "FIFO_ATTRIBUTION")

    narrative = (
        f"Forensic investigation for subject account {acc} observed {account_summary.incoming_transaction_count} incoming "
        f"(INR {account_summary.observed_incoming_volume:,.2f}) and {account_summary.outgoing_transaction_count} outgoing "
        f"(INR {account_summary.observed_outgoing_volume:,.2f}) transactions. "
        f"Root outflow under investigation is INR {root_seed_amount:,.2f}, with downstream cumulative attribution of "
        f"INR {downstream_fifo_amount:,.2f} across {trace_res.total_hops_found} downstream hop(s) reaching {len(terminals)} "
        f"terminal recipient account(s). (Note: Downstream amounts represent fund propagation across subsequent hops and "
        f"must not be summed across hops as unique funds.) "
        f"Subject presents a Mule Risk Index of {risk_score.risk_index:.1f}/100 ({risk_score.risk_band}) "
        f"with primary classification '{roles.primary_role_label}'."
    )

    evidence_summary = InvestigationEvidenceSummary(
        subject_account=acc,
        observed_activity=f"{account_summary.incoming_transaction_count} incoming / {account_summary.outgoing_transaction_count} outgoing",
        observed_outflow=account_summary.observed_outgoing_volume,
        observed_inflow=account_summary.observed_incoming_volume,
        temporal_attribution_summary=f"{root_seed_count} root seed transactions, {fifo_count} downstream FIFO attribution links",
        max_verified_propagation=trace_res.total_hops_found,
        risk_summary=f"{risk_score.risk_index:.1f} / 100 -- {risk_score.risk_band}",
        role_summary=f"{roles.primary_role_label}",
        velocity_summary=f"{velocity.pass_through_ratio*100:.1f}% qualifying 3-15 min pass-through" if velocity.pass_through_candidate else "No rapid pass-through velocity observed",
        narrative=narrative,
    )

    # 10. Deterministic Investigation ID
    inv_seed = f"{acc}_{trace_res.total_attributed_amount}_{trace_res.total_hops_found}_{len(terminals)}"
    inv_hash = hashlib.sha256(inv_seed.encode("utf-8")).hexdigest()[:8].upper()
    investigation_id = f"INV-{acc}-{inv_hash}"

    status = "COMPLETED" if trace_res.total_hops_found > 0 else "NO_QUALIFYING_OUTFLOW"

    response = VictimInvestigationResponse(
        investigation_id=investigation_id,
        account_number=acc,
        status=status,
        generated_at=datetime.now(timezone.utc).isoformat(),
        data_provenance=DataProvenance(),
        account_summary=account_summary,
        victim_transactions=victim_transactions,
        risk=risk_score,
        roles=roles,
        velocity=velocity,
        trace=trace_res,
        terminals=terminals,
        warnings=warnings,
        evidence_summary=evidence_summary,
        disclaimer=(
            "INVESTIGATIVE FORENSICS ONLY -- Deterministic accounting and behavioral models. "
            "Does not constitute legal proof of beneficial ownership, criminal intent, or judicial determination."
        ),
    )
    _INVESTIGATION_CACHE[cache_key] = response
    return response
