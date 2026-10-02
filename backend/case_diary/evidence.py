"""
Case Diary Evidence Extraction for Operation 'ABHEDYA-CHAKRA'
Step 8: Deterministic extraction of structured VerifiedFacts and chronology events
        from the existing Step 6 VictimInvestigationResponse.

All evidence is derived EXCLUSIVELY from the existing verified investigation pipeline.
No new computation is introduced here — this is an adapter/extraction layer only.
"""

from datetime import datetime, timezone
from typing import List, Optional

from backend.investigations.models import VictimInvestigationResponse
from backend.case_diary.models import (
    VerifiedFact,
    DiaryChronologyEvent,
    RiskFinding,
    RoleFinding,
    VelocityFinding,
    AttributionFinding,
    DiaryFindings,
)


# ---------------------------------------------------------------------------
# VerifiedFact extraction helpers
# ---------------------------------------------------------------------------

def _fact(
    idx: int,
    category: str,
    code: str,
    statement: str,
    value,
    source_type: str,
    source_ref: str,
    confidence: str = "DETERMINISTIC",
    provenance: str = "VERIFIED",
) -> VerifiedFact:
    return VerifiedFact(
        fact_id=f"FACT-{category}-{idx:03d}",
        category=category,
        code=code,
        statement=statement,
        value=value,
        source_type=source_type,
        source_reference=source_ref,
        confidence=confidence,
        provenance=provenance,
    )


def extract_verified_facts(inv: VictimInvestigationResponse) -> List[VerifiedFact]:
    """
    Derive all VerifiedFacts from the investigation response.
    Strictly maps to fields that actually exist in the response.
    """
    facts: List[VerifiedFact] = []
    idx = 1
    acc = inv.account_number
    summary = inv.account_summary

    # --- SUBJECT FACTS ---
    facts.append(_fact(idx, "SUBJECT", "ACCOUNT_NUMBER",
        f"Subject account number is {acc}.", acc, "RAW", "account_number"))
    idx += 1

    facts.append(_fact(idx, "SUBJECT", "OBSERVED_INFLOW",
        f"Total observed incoming volume for {acc} is INR {summary.observed_incoming_volume:,.2f}.",
        summary.observed_incoming_volume, "RAW", "account_summary.observed_incoming_volume"))
    idx += 1

    facts.append(_fact(idx, "SUBJECT", "OBSERVED_OUTFLOW",
        f"Total observed outgoing volume for {acc} is INR {summary.observed_outgoing_volume:,.2f}.",
        summary.observed_outgoing_volume, "RAW", "account_summary.observed_outgoing_volume"))
    idx += 1

    facts.append(_fact(idx, "SUBJECT", "NET_FLOW_DELTA",
        f"Observed net flow delta (inflow minus outflow) is INR {summary.observed_net_flow_delta:,.2f}. "
        f"This is NOT a current bank balance.",
        summary.observed_net_flow_delta, "RAW", "account_summary.observed_net_flow_delta"))
    idx += 1

    facts.append(_fact(idx, "SUBJECT", "INCOMING_TX_COUNT",
        f"Account {acc} has {summary.incoming_transaction_count} observed incoming transactions.",
        summary.incoming_transaction_count, "RAW", "account_summary.incoming_transaction_count"))
    idx += 1

    facts.append(_fact(idx, "SUBJECT", "OUTGOING_TX_COUNT",
        f"Account {acc} has {summary.outgoing_transaction_count} observed outgoing transactions.",
        summary.outgoing_transaction_count, "RAW", "account_summary.outgoing_transaction_count"))
    idx += 1

    facts.append(_fact(idx, "SUBJECT", "UNIQUE_COUNTERPARTIES",
        f"Account {acc} interacted with {summary.unique_counterparties} unique counterparties.",
        summary.unique_counterparties, "RAW", "account_summary.unique_counterparties"))
    idx += 1

    facts.append(_fact(idx, "SUBJECT", "UNIQUE_IPS",
        f"Account {acc} used {summary.unique_ip_count} unique IP addresses.",
        summary.unique_ip_count, "RAW", "account_summary.unique_ip_count"))
    idx += 1

    facts.append(_fact(idx, "SUBJECT", "UNIQUE_DEVICES",
        f"Account {acc} used {summary.unique_device_count} unique device types.",
        summary.unique_device_count, "RAW", "account_summary.unique_device_count"))
    idx += 1

    if summary.first_observed_timestamp:
        facts.append(_fact(idx, "SUBJECT", "FIRST_ACTIVITY",
            f"Earliest observed transaction timestamp: {summary.first_observed_timestamp}.",
            summary.first_observed_timestamp, "RAW", "account_summary.first_observed_timestamp"))
        idx += 1

    if summary.last_observed_timestamp:
        facts.append(_fact(idx, "SUBJECT", "LAST_ACTIVITY",
            f"Latest observed transaction timestamp: {summary.last_observed_timestamp}.",
            summary.last_observed_timestamp, "RAW", "account_summary.last_observed_timestamp"))
        idx += 1

    if summary.payment_modes:
        mode_str = ", ".join(f"{k}: {v}" for k, v in summary.payment_modes.items())
        facts.append(_fact(idx, "SUBJECT", "PAYMENT_MODES",
            f"Payment mode distribution for {acc}: {mode_str}.",
            summary.payment_modes, "RAW", "account_summary.payment_modes"))
        idx += 1

    if summary.associated_ifscs:
        facts.append(_fact(idx, "SUBJECT", "ASSOCIATED_IFSCS",
            f"Account {acc} is associated with IFSC codes: {', '.join(summary.associated_ifscs[:10])}.",
            summary.associated_ifscs, "RAW", "account_summary.associated_ifscs"))
        idx += 1

    if summary.associated_ips:
        facts.append(_fact(idx, "SUBJECT", "ASSOCIATED_IPS",
            f"Account {acc} used IP addresses: {', '.join(summary.associated_ips[:10])}.",
            summary.associated_ips[:10], "RAW", "account_summary.associated_ips"))
        idx += 1

    # --- TRANSACTION FACTS (sampled first 5 for verified facts; all are in chronology) ---
    tx_sample = sorted(inv.victim_transactions[:5], key=lambda t: t.timestamp)
    for tx in tx_sample:
        direction_str = "incoming" if tx.direction == "INCOMING" else "outgoing"
        facts.append(_fact(idx, "TRANSACTION", f"TX_{tx.transaction_id[:8]}",
            f"{direction_str.capitalize()} transaction {tx.transaction_id} "
            f"for INR {tx.amount:,.2f} at {tx.timestamp} via {tx.payment_mode}. "
            f"Sender: {tx.sender_account}, Receiver: {tx.receiver_account}.",
            {
                "transaction_id": tx.transaction_id,
                "row_id": tx.row_id,
                "amount": tx.amount,
                "timestamp": tx.timestamp,
                "direction": tx.direction,
                "sender": tx.sender_account,
                "receiver": tx.receiver_account,
                "payment_mode": tx.payment_mode,
            },
            "RAW", f"transaction:{tx.transaction_id}:row:{tx.row_id}"))
        idx += 1

    # --- RISK FACTS ---
    risk = inv.risk
    facts.append(_fact(idx, "RISK", "RISK_INDEX",
        f"Step 5B Mule Risk Index for {acc} is {risk.risk_index:.1f}/100 (band: {risk.risk_band}). "
        f"This is an investigative indicator, not a legal determination.",
        {"risk_index": risk.risk_index, "risk_band": risk.risk_band},
        "DERIVED", "risk.risk_index", "DETERMINISTIC", "DERIVED"))
    idx += 1

    for family, pts in risk.risk_family_scores.items():
        facts.append(_fact(idx, "RISK", f"RISK_FAMILY_{family}",
            f"Risk family {family} contributed {pts:.1f} points to the risk index.",
            pts, "DERIVED", f"risk.risk_family_scores.{family}", "DETERMINISTIC", "DERIVED"))
        idx += 1

    for reason in risk.risk_reasons:
        facts.append(_fact(idx, "RISK", f"RISK_REASON_{reason.code}",
            reason.description,
            {"code": reason.code, "points": reason.points, "observed_value": reason.observed_value},
            "DERIVED", f"risk.risk_reasons.{reason.code}", "DETERMINISTIC", "DERIVED"))
        idx += 1

    # --- ROLE FACTS ---
    roles = inv.roles
    facts.append(_fact(idx, "ROLE", "L1_COLLECTOR",
        f"Account {acc} L1 Collector Mule candidate: {roles.l1_collector_candidate}.",
        roles.l1_collector_candidate, "DERIVED", "roles.l1_collector_candidate"))
    idx += 1

    facts.append(_fact(idx, "ROLE", "L2_DISTRIBUTOR",
        f"Account {acc} L2 Distributor Mule candidate: {roles.l2_distributor_candidate}.",
        roles.l2_distributor_candidate, "DERIVED", "roles.l2_distributor_candidate"))
    idx += 1

    facts.append(_fact(idx, "ROLE", "L3_TERMINAL",
        f"Account {acc} L3 Terminal/Cash-out candidate: {roles.l3_terminal_candidate}.",
        roles.l3_terminal_candidate, "DERIVED", "roles.l3_terminal_candidate"))
    idx += 1

    facts.append(_fact(idx, "ROLE", "PRIMARY_ROLE",
        f"Primary role label: {roles.primary_role_label}. Fan-in: {roles.fan_in}, Fan-out: {roles.fan_out}.",
        {"label": roles.primary_role_label, "fan_in": roles.fan_in, "fan_out": roles.fan_out},
        "DERIVED", "roles.primary_role_label"))
    idx += 1

    if roles.classification_reasons:
        facts.append(_fact(idx, "ROLE", "CLASSIFICATION_REASONS",
            f"Role classification triggers: {'; '.join(roles.classification_reasons)}.",
            roles.classification_reasons, "DERIVED", "roles.classification_reasons"))
        idx += 1

    # --- VELOCITY FACTS ---
    vel = inv.velocity
    facts.append(_fact(idx, "VELOCITY", "PASS_THROUGH_CANDIDATE",
        f"Account {acc} pass-through candidate (3-15 min window): {vel.pass_through_candidate}. "
        f"Qualifying event count: {vel.qualifying_event_count}. Ratio: {vel.pass_through_ratio:.3f}.",
        {
            "pass_through_candidate": vel.pass_through_candidate,
            "qualifying_event_count": vel.qualifying_event_count,
            "pass_through_ratio": vel.pass_through_ratio,
        },
        "DERIVED", "velocity.pass_through_candidate"))
    idx += 1

    facts.append(_fact(idx, "VELOCITY", "ATTRIBUTED_VOLUME",
        f"Rapid pass-through (3-15 min) attributed volume: INR {vel.attributed_volume:,.2f}. "
        f"Outgoing qualifying count: {vel.outgoing_qualifying_count}.",
        {"attributed_volume": vel.attributed_volume, "outgoing_qualifying_count": vel.outgoing_qualifying_count},
        "DERIVED", "velocity.attributed_volume"))
    idx += 1

    if vel.median_delay_seconds is not None:
        facts.append(_fact(idx, "VELOCITY", "MEDIAN_DELAY",
            f"Median delay between incoming and qualifying outgoing: {vel.median_delay_seconds:.1f} seconds.",
            vel.median_delay_seconds, "DERIVED", "velocity.median_delay_seconds"))
        idx += 1

    facts.append(_fact(idx, "VELOCITY", "WINDOW_DEFINITION",
        f"Qualifying pass-through window: {vel.window_description} (inclusive 3:00 – 15:00 minutes). "
        f"Version: {vel.classification_version}.",
        vel.window_description, "DERIVED", "velocity.window_description"))
    idx += 1

    # --- ATTRIBUTION FACTS ---
    trace = inv.trace
    root_seed = sum(e.attributed_amount for e in trace.edges if e.edge_type == "ROOT_SEED")
    downstream = sum(e.attributed_amount for e in trace.edges if e.edge_type == "FIFO_ATTRIBUTION")
    facts.append(_fact(idx, "ATTRIBUTION", "ROOT_SEED_OUTFLOW",
        f"Root seed outflow (direct exits from {acc}): INR {root_seed:,.2f}. "
        f"This is the primary fund quantity directly leaving the subject account.",
        round(root_seed, 2), "ATTRIBUTED", "trace.edges[edge_type=ROOT_SEED]"))
    idx += 1

    facts.append(_fact(idx, "ATTRIBUTION", "DOWNSTREAM_FIFO",
        f"Downstream cumulative FIFO attribution across subsequent hops: INR {downstream:,.2f}. "
        f"This represents propagation across hops and must NOT be summed as unique new funds.",
        round(downstream, 2), "ATTRIBUTED", "trace.edges[edge_type=FIFO_ATTRIBUTION]"))
    idx += 1

    facts.append(_fact(idx, "ATTRIBUTION", "MAX_HOPS",
        f"Maximum hop depth traversed: {trace.total_hops_found}. "
        f"Policy: {trace.policy_name} {trace.policy_version}.",
        trace.total_hops_found, "ATTRIBUTED", "trace.total_hops_found"))
    idx += 1

    facts.append(_fact(idx, "ATTRIBUTION", "TRUNCATED",
        f"Attribution trace truncated: {trace.truncated}."
        + (f" Reason: {trace.truncation_reason}" if trace.truncation_reason else ""),
        trace.truncated, "ATTRIBUTED", "trace.truncated"))
    idx += 1

    if trace.cycles_detected:
        facts.append(_fact(idx, "ATTRIBUTION", "CYCLES_DETECTED",
            f"Cycles detected in attribution graph: {', '.join(trace.cycles_detected)}.",
            trace.cycles_detected, "ATTRIBUTED", "trace.cycles_detected"))
        idx += 1

    # Terminal accounts
    for term in inv.terminals[:10]:
        facts.append(_fact(idx, "ATTRIBUTION", f"TERMINAL_{term.account_number}",
            f"Terminal account {term.account_number} reached at hop {term.hop} "
            f"with attributed amount INR {term.attributed_amount:,.2f}. Role: {term.primary_role}.",
            {
                "account": term.account_number,
                "hop": term.hop,
                "attributed_amount": term.attributed_amount,
                "role": term.primary_role,
                "risk_index": term.risk_index,
                "risk_band": term.risk_band,
            },
            "ATTRIBUTED", f"terminals.{term.account_number}"))
        idx += 1

    # --- PROVENANCE FACTS ---
    prov = inv.data_provenance
    facts.append(_fact(idx, "PROVENANCE", "DATASET",
        f"Production dataset: {prov.dataset_name} — {prov.dataset_rows:,} rows. "
        f"SHA-256: {prov.dataset_sha256}.",
        {
            "dataset_name": prov.dataset_name,
            "dataset_rows": prov.dataset_rows,
            "dataset_sha256": prov.dataset_sha256,
        },
        "RAW", "data_provenance.dataset_sha256"))
    idx += 1

    facts.append(_fact(idx, "PROVENANCE", "INVESTIGATION_ID",
        f"Investigation ID: {inv.investigation_id}. Status: {inv.status}.",
        {"investigation_id": inv.investigation_id, "status": inv.status},
        "RAW", "investigation_id"))
    idx += 1

    return facts


# ---------------------------------------------------------------------------
# Chronology extraction
# ---------------------------------------------------------------------------

def extract_chronology(inv: VictimInvestigationResponse) -> List[DiaryChronologyEvent]:
    """
    Build a deterministic, timestamp-sorted chronological event list.

    Sorting: timestamp ascending → source_row_id ascending → transaction_id lexicographic.
    Never relies on raw CSV order.
    """
    events: List[DiaryChronologyEvent] = []
    acc = inv.account_number
    now_iso = datetime.now(timezone.utc).isoformat()

    # Event 1: CASE_OPENED (created now, sort key pinned to earliest tx or now)
    earliest_ts = inv.account_summary.first_observed_timestamp or now_iso
    events.append(DiaryChronologyEvent(
        event_id="EVT-0001",
        event_type="CASE_OPENED",
        timestamp=now_iso,
        sort_key=f"0000-00-00T00:00:00|0000000000|CASE_OPENED",
        description=f"Case diary opened for subject account {acc}. "
                    f"Investigation ID: {inv.investigation_id}. Status: {inv.status}.",
        source_reference=inv.investigation_id,
    ))

    # ROOT_TRANSACTION events — from victim_transactions, sorted deterministically
    sorted_txs = sorted(
        inv.victim_transactions,
        key=lambda t: (t.timestamp or "0000-00-00T00:00:00", t.row_id, t.transaction_id)
    )
    ev_idx = 2
    for tx in sorted_txs:
        direction_label = "Incoming" if tx.direction == "INCOMING" else "Outgoing"
        events.append(DiaryChronologyEvent(
            event_id=f"EVT-{ev_idx:04d}",
            event_type="ROOT_TRANSACTION",
            timestamp=tx.timestamp,
            sort_key=f"{tx.timestamp or '0000'}|{tx.row_id:010d}|{tx.transaction_id}",
            description=(
                f"{direction_label} transaction {tx.transaction_id} — "
                f"INR {tx.amount:,.2f} via {tx.payment_mode}. "
                f"Sender: {tx.sender_account} → Receiver: {tx.receiver_account}. "
                f"IP: {tx.ip_address}. Device: {tx.device_type or 'Not recorded'}."
            ),
            source_reference=f"transaction:{tx.transaction_id}:row:{tx.row_id}",
            amount=tx.amount,
            sender_account=tx.sender_account,
            receiver_account=tx.receiver_account,
            provenance="VERIFIED",
        ))
        ev_idx += 1

    # ATTRIBUTION_HOP events — from trace edges
    sorted_edges = sorted(
        inv.trace.edges,
        key=lambda e: (
            e.source_timestamp or "0000-00-00T00:00:00",
            e.source_row_id,
            e.source_transaction_id,
        )
    )
    for edge in sorted_edges:
        events.append(DiaryChronologyEvent(
            event_id=f"EVT-{ev_idx:04d}",
            event_type="ATTRIBUTION_HOP",
            timestamp=edge.source_timestamp,
            sort_key=(
                f"{edge.source_timestamp or '0000'}|{edge.source_row_id:010d}|{edge.source_transaction_id}"
            ),
            description=(
                f"[Hop {edge.hop_number}] {edge.edge_type}: "
                f"{edge.intermediary_account} → {edge.destination_account} — "
                f"INR {edge.attributed_amount:,.2f} attributed. "
                f"Delay: {edge.delay_seconds:.0f}s. "
                f"Source TX: {edge.source_transaction_id}."
            ),
            source_reference=(
                f"edge:{edge.attribution_id}:source:{edge.source_transaction_id}"
            ),
            amount=edge.attributed_amount,
            hop=edge.hop_number,
            sender_account=edge.intermediary_account,
            receiver_account=edge.destination_account,
            edge_type=edge.edge_type,
            provenance="ATTRIBUTED",
        ))
        ev_idx += 1

    # VELOCITY_EVENT events — from velocity events
    for vel_ev in inv.velocity.events[:20]:
        ts = vel_ev.get("outgoing_timestamp") or vel_ev.get("incoming_timestamp") or ""
        out_tx = vel_ev.get("outgoing_transaction_id", "unknown")
        in_tx = vel_ev.get("incoming_transaction_id", "unknown")
        row_id = vel_ev.get("outgoing_row_id", 0)
        events.append(DiaryChronologyEvent(
            event_id=f"EVT-{ev_idx:04d}",
            event_type="VELOCITY_EVENT",
            timestamp=ts or None,
            sort_key=f"{ts or '0000'}|{row_id:010d}|{out_tx}",
            description=(
                f"Pass-through velocity event: incoming TX {in_tx} "
                f"→ outgoing TX {out_tx}. "
                f"Delay: {vel_ev.get('delay_seconds', 0):.0f}s "
                f"(window: {vel_ev.get('window', '3_TO_15_MINUTES')}). "
                f"Attributed: INR {vel_ev.get('attributed_amount', 0):,.2f}."
            ),
            source_reference=f"velocity_event:out:{out_tx}",
            amount=vel_ev.get("attributed_amount"),
            provenance="DERIVED",
        ))
        ev_idx += 1

    # RISK_FINDING event
    events.append(DiaryChronologyEvent(
        event_id=f"EVT-{ev_idx:04d}",
        event_type="RISK_FINDING",
        timestamp=now_iso,
        sort_key=f"9999-12-31T23:59:58|9999999998|RISK_FINDING",
        description=(
            f"Step 5B Mule Risk Index: {inv.risk.risk_index:.1f}/100 ({inv.risk.risk_band}). "
            f"Top families: {', '.join(f'{k}={v:.1f}' for k, v in list(inv.risk.risk_family_scores.items())[:3])}. "
            f"This is an investigative indicator only."
        ),
        source_reference="risk.risk_index",
        provenance="DERIVED",
    ))
    ev_idx += 1

    # ROLE_FINDING event
    roles = inv.roles
    roles_triggered = []
    if roles.l1_collector_candidate:
        roles_triggered.append("L1-COLLECTOR")
    if roles.l2_distributor_candidate:
        roles_triggered.append("L2-DISTRIBUTOR")
    if roles.l3_terminal_candidate:
        roles_triggered.append("L3-TERMINAL")

    events.append(DiaryChronologyEvent(
        event_id=f"EVT-{ev_idx:04d}",
        event_type="ROLE_FINDING",
        timestamp=now_iso,
        sort_key=f"9999-12-31T23:59:59|9999999999|ROLE_FINDING",
        description=(
            f"Step 4 mule role classification: {roles.primary_role_label}. "
            f"Triggered roles: {', '.join(roles_triggered) if roles_triggered else 'None'}. "
            f"Fan-in: {roles.fan_in}, Fan-out: {roles.fan_out}."
        ),
        source_reference="roles.primary_role_label",
        provenance="DERIVED",
    ))
    ev_idx += 1

    # TERMINAL_ACCOUNT events
    for term in inv.terminals:
        events.append(DiaryChronologyEvent(
            event_id=f"EVT-{ev_idx:04d}",
            event_type="TERMINAL_ACCOUNT",
            timestamp=now_iso,
            sort_key=(
                f"9999-12-31T23:58:{term.hop:02d}|{0:010d}|{term.account_number}"
            ),
            description=(
                f"Terminal account {term.account_number} reached at hop {term.hop}. "
                f"Attributed: INR {term.attributed_amount:,.2f}. "
                f"Role: {term.primary_role}. "
                + (f"Risk index: {term.risk_index:.1f} ({term.risk_band})."
                   if term.risk_index is not None else "Risk not computed.")
            ),
            source_reference=f"terminal:{term.account_number}:hop:{term.hop}",
            amount=term.attributed_amount,
            hop=term.hop,
            receiver_account=term.account_number,
            provenance="ATTRIBUTED",
        ))
        ev_idx += 1

    # Sort all events by sort_key (stable, deterministic)
    events.sort(key=lambda e: e.sort_key)

    # Re-sequence event IDs after sort
    for i, ev in enumerate(events, 1):
        ev.event_id = f"EVT-{i:04d}"

    return events


# ---------------------------------------------------------------------------
# DiaryFindings extraction
# ---------------------------------------------------------------------------

def extract_findings(inv: VictimInvestigationResponse) -> DiaryFindings:
    """Extract all structured DiaryFindings from the investigation response."""

    # Risk
    risk = inv.risk
    top_codes = [r.code for r in sorted(risk.risk_reasons, key=lambda r: -r.points)[:5]]
    risk_finding = RiskFinding(
        risk_index=risk.risk_index,
        risk_band=risk.risk_band,
        scoring_version=risk.risk_model_version,
        family_contributions=risk.risk_family_scores,
        top_reason_codes=top_codes,
    )

    # Role
    roles = inv.roles
    role_finding = RoleFinding(
        l1_collector_candidate=roles.l1_collector_candidate,
        l2_distributor_candidate=roles.l2_distributor_candidate,
        l3_terminal_candidate=roles.l3_terminal_candidate,
        primary_role_label=roles.primary_role_label,
        classification_reasons=roles.classification_reasons,
        fan_in=roles.fan_in,
        fan_out=roles.fan_out,
    )

    # Velocity
    vel = inv.velocity
    velocity_finding = VelocityFinding(
        pass_through_candidate=vel.pass_through_candidate,
        pass_through_ratio=vel.pass_through_ratio,
        qualifying_event_count=vel.qualifying_event_count,
        attributed_volume=vel.attributed_volume,
        outgoing_qualifying_count=vel.outgoing_qualifying_count,
        median_delay_seconds=vel.median_delay_seconds,
        window_description=vel.window_description,
        classification_version=vel.classification_version,
    )

    # Attribution
    trace = inv.trace
    root_seed = round(sum(e.attributed_amount for e in trace.edges if e.edge_type == "ROOT_SEED"), 2)
    downstream = round(sum(e.attributed_amount for e in trace.edges if e.edge_type == "FIFO_ATTRIBUTION"), 2)
    root_count = sum(1 for e in trace.edges if e.edge_type == "ROOT_SEED")
    fifo_count = sum(1 for e in trace.edges if e.edge_type == "FIFO_ATTRIBUTION")
    trunc_reasons = [trace.truncation_reason] if trace.truncation_reason else []

    attr_finding = AttributionFinding(
        root_seed_outflow=root_seed,
        downstream_cumulative_attribution=downstream,
        max_hops_traversed=trace.total_hops_found,
        root_seed_edge_count=root_count,
        downstream_fifo_edge_count=fifo_count,
        attribution_policy=trace.policy_name,
        attribution_policy_version=trace.policy_version,
        is_truncated=trace.truncated,
        truncation_reasons=trunc_reasons,
        cycles_detected=trace.cycles_detected or [],
        terminal_account_count=len(inv.terminals),
    )

    return DiaryFindings(risk=risk_finding, role=role_finding, velocity=velocity_finding, attribution=attr_finding)
