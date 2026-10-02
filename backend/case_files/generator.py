"""
Forensic Case File Generator for Operation 'ABHEDYA-CHAKRA'
Step 7: Orchestrates investigation reconstruction, deterministic evidence snapshot assembly,
canonical SHA-256 hashing, PDF document compilation, and in-memory artifact storage.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import duckdb

from backend.case_files.models import (
    CaseFileRequest,
    CaseFileResponse,
    CaseFileMetadata,
    EvidenceSnapshot,
    ObservedFacts,
    OfficialRiskBreakdown,
    AttributionSummary,
    InvestigationLimitations,
)
from backend.case_files.pdf_generator import generate_case_file_pdf
from backend.case_files.store import CASE_FILE_STORE
from backend.investigations.orchestrator import investigate_victim_account


def generate_forensic_case_file(
    con: duckdb.DuckDBPyConnection,
    req: CaseFileRequest,
) -> CaseFileResponse:
    """
    Generates a structured, reproducible forensic case file and compiled evidence package.
    """
    acc = req.account_number.strip().upper()
    if not acc:
        raise ValueError("Account number cannot be empty")

    # 1. Reconstruct or execute investigation for the subject account
    inv_response = investigate_victim_account(
        con=con,
        account_id=acc,
        max_hops=req.max_hops,
        horizon_seconds=req.horizon_seconds,
        max_branches_per_hop=req.max_branches_per_hop,
    )

    # 2. Extract Observed Facts
    summary = inv_response.account_summary
    source_tx_ids = [tx.transaction_id for tx in inv_response.victim_transactions]
    source_row_ids = [tx.row_id for tx in inv_response.victim_transactions]

    observed_facts = ObservedFacts(
        subject_account=acc,
        total_observed_incoming_volume=summary.observed_incoming_volume,
        total_observed_outgoing_volume=summary.observed_outgoing_volume,
        observed_net_flow_delta=summary.observed_net_flow_delta,
        incoming_transaction_count=summary.incoming_transaction_count,
        outgoing_transaction_count=summary.outgoing_transaction_count,
        unique_counterparties=summary.unique_counterparties,
        unique_ip_count=summary.unique_ip_count,
        unique_device_count=summary.unique_device_count,
        payment_modes_observed=list(summary.payment_modes.keys()) if isinstance(summary.payment_modes, dict) else list(summary.payment_modes),
        first_observed_timestamp=summary.first_observed_timestamp,
        last_observed_timestamp=summary.last_observed_timestamp,
        source_transaction_ids=source_tx_ids,
        source_row_ids=source_row_ids,
        provenance="RAW_AND_ANALYTICAL",
    )

    # 3. Extract Attribution Summary with separation of root outflow vs downstream hops
    root_seed_amount = sum(round(e.attributed_amount, 2) for e in inv_response.trace.edges if e.edge_type == "ROOT_SEED")
    downstream_fifo_amount = sum(round(e.attributed_amount, 2) for e in inv_response.trace.edges if e.edge_type == "FIFO_ATTRIBUTION")
    root_seed_count = sum(1 for e in inv_response.trace.edges if e.edge_type == "ROOT_SEED")
    downstream_fifo_count = sum(1 for e in inv_response.trace.edges if e.edge_type == "FIFO_ATTRIBUTION")

    attribution_summary = AttributionSummary(
        root_seed_outflow=round(root_seed_amount, 2),
        downstream_cumulative_attribution=round(downstream_fifo_amount, 2),
        max_hops_traversed=inv_response.trace.total_hops_found,
        root_seed_edge_count=root_seed_count,
        downstream_fifo_edge_count=downstream_fifo_count,
        attribution_policy=inv_response.data_provenance.attribution_policy,
        attribution_policy_version=inv_response.data_provenance.attribution_policy_version,
    )

    # 4. Extract Official Step 5B Risk Breakdown (preserving exact official family contributions)
    official_risk = OfficialRiskBreakdown(
        risk_index=inv_response.risk.risk_index,
        risk_band=inv_response.risk.risk_band,
        scoring_version=inv_response.risk.risk_model_version,
        family_points=inv_response.risk.risk_family_scores,
        evidence_reasons=inv_response.risk.risk_reasons,
        provenance="DERIVED",
    )

    # 5. Extract Limitations
    trunc_reasons = []
    if inv_response.trace.truncation_reason:
        trunc_reasons.append(inv_response.trace.truncation_reason)

    limitations = InvestigationLimitations(
        is_truncated=inv_response.trace.truncated,
        truncation_reasons=trunc_reasons,
        cycles_detected=inv_response.trace.cycles_detected,
    )

    # 6. Assemble Self-Contained Evidence Snapshot
    snapshot = EvidenceSnapshot(
        snapshot_version="v1",
        subject_account=acc,
        dataset_name=inv_response.data_provenance.dataset_name,
        dataset_rows=inv_response.data_provenance.dataset_rows,
        dataset_sha256=inv_response.data_provenance.dataset_sha256,
        observed_facts=observed_facts,
        transactions_sample=inv_response.victim_transactions[:50],
        attribution=attribution_summary,
        trace_nodes_count=len(inv_response.trace.nodes),
        trace_edges_count=len(inv_response.trace.edges),
        terminal_accounts=inv_response.terminals,
        official_risk=official_risk,
        velocity_profile=inv_response.velocity,
        mule_roles=inv_response.roles,
        limitations=limitations,
        provenance_chain="RAW -> ANALYTICAL -> DERIVED -> CASE_FILE",
    )

    # 7. Compute Canonical Evidence Snapshot SHA-256
    # Note: snapshot is serialized using sorted keys and consistent indentation
    snapshot_dict = snapshot.model_dump(mode="json")
    snapshot_json_bytes = json.dumps(snapshot_dict, indent=2, sort_keys=True).encode("utf-8")
    evidence_sha256 = hashlib.sha256(snapshot_json_bytes).hexdigest()

    # 8. Deterministic Case File ID
    case_hash = hashlib.sha256(f"{acc}_{evidence_sha256}".encode("utf-8")).hexdigest()[:8].upper()
    case_file_id = f"CASE-{acc}-{case_hash}"

    created_at_iso = datetime.now(timezone.utc).isoformat()

    metadata = CaseFileMetadata(
        case_file_id=case_file_id,
        investigation_id=inv_response.investigation_id,
        subject_account=acc,
        status=inv_response.status,
        created_at=created_at_iso,
        source_dataset=inv_response.data_provenance.dataset_name,
        dataset_rows=inv_response.data_provenance.dataset_rows,
        dataset_sha256=inv_response.data_provenance.dataset_sha256,
        evidence_snapshot_sha256=evidence_sha256,
        pdf_sha256=None,
        json_sha256=None,
        pdf_download_url=f"/api/case-files/{case_file_id}/pdf" if req.include_pdf else None,
        json_download_url=f"/api/case-files/{case_file_id}/json" if req.include_json else None,
    )

    pdf_bytes: Optional[bytes] = None
    if req.include_pdf:
        pdf_bytes = generate_case_file_pdf(metadata, snapshot, inv_response)
        metadata.pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    json_bytes: Optional[bytes] = None
    if req.include_json:
        json_bytes = snapshot_json_bytes
        metadata.json_sha256 = hashlib.sha256(json_bytes).hexdigest()

    response = CaseFileResponse(
        metadata=metadata,
        evidence_snapshot=snapshot,
        trace=inv_response.trace,
        warnings=inv_response.warnings,
        evidence_narrative=inv_response.evidence_summary.narrative,
    )

    # Save compiled artifacts in store
    CASE_FILE_STORE.save(
        case_file_id=case_file_id,
        response=response,
        pdf_data=pdf_bytes,
        json_data=json_bytes,
    )

    return response
