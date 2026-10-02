"""
Step 9: Legal Evidence Extraction & Normalization
Operation 'ABHEDYA-CHAKRA'
"""

import hashlib
import json
from typing import Dict, Any, List, Optional

from backend.investigations.models import (
    VictimInvestigationResponse,
    VictimTransactionItem,
)
from backend.legal_freeze.models import (
    LegalDraftRequest,
    OfficerDetails,
    SubjectAccountLegalEvidence,
    VerifiedTransactionLegalItem,
    LegalRiskEvidence,
    LegalRoleEvidence,
    LegalVelocityEvidence,
    LegalAttributionEvidence,
    LegalEvidenceSnapshot,
)

OFFICER_PLACEHOLDER = "[TO BE COMPLETED BY AUTHORIZED OFFICER]"
BANK_PLACEHOLDER = "[RECIPIENT BANK TO BE COMPLETED]"
BRANCH_PLACEHOLDER = "[RECIPIENT BRANCH TO BE COMPLETED]"
PRESERVATION_PERIOD_PLACEHOLDER = "[PRESERVATION PERIOD TO BE COMPLETED]"


def normalize_officer_details(req: LegalDraftRequest) -> OfficerDetails:
    """
    Normalizes officer and case details.
    Guarantees that missing or blank inputs resolve to explicit placeholders,
    never fabricated or assumed data.
    """
    name = (req.officer_name or "").strip()
    desig = (req.officer_designation or "").strip()
    station = (req.police_station or "").strip()
    auth = (req.requesting_authority or "").strip()
    case_ref = (req.case_reference or "").strip()
    inc_ref = (req.incident_reference or "").strip()
    bank = (req.recipient_bank or "").strip()
    branch = (req.recipient_branch or "").strip()
    action = (req.requested_action or "").strip()
    pres_period = (req.preservation_period or "").strip()
    notes = (req.investigator_notes or "").strip()

    # Default categories for bank requisition if not specified
    record_cats = req.requested_record_categories or [
        "Account Opening Form & Verified KYC Documents",
        "Complete Certified Bank Account Statement with Balance Progression",
        "Beneficiary & Originator Transaction Details with IP/Device Logs",
        "Registered Mobile Number, Email ID, and Internet Banking Audit Logs",
        "Linked and Sibling Accounts under the Same CIF/Customer ID",
    ]

    # Default action description based on document type if none specified
    if not action:
        if req.document_type == "ACCOUNT_FREEZE_REQUEST":
            action = (
                "Request for immediate temporary debit-freeze / lien / hold on the identified account "
                "under applicable statutory powers pending forensic cyber investigation."
            )
        elif req.document_type == "RECORD_PRESERVATION_REQUEST":
            action = (
                "Request for immediate preservation and retention of all digital, transactional, and KYC records "
                "associated with the identified account."
            )
        elif req.document_type == "BANK_INFORMATION_REQUISITION":
            action = (
                "Requisition for certified copies of account records, transaction logs, and subscriber details "
                "for lawful cyber-crime investigation."
            )
        else:
            action = "Forensic cyber-crime evidence annexure for official investigation file."

    return OfficerDetails(
        officer_name=name if name else OFFICER_PLACEHOLDER,
        officer_designation=desig if desig else OFFICER_PLACEHOLDER,
        police_station=station if station else OFFICER_PLACEHOLDER,
        requesting_authority=auth if auth else OFFICER_PLACEHOLDER,
        case_reference=case_ref if case_ref else OFFICER_PLACEHOLDER,
        incident_reference=inc_ref if inc_ref else OFFICER_PLACEHOLDER,
        recipient_bank=bank if bank else BANK_PLACEHOLDER,
        recipient_branch=branch if branch else BRANCH_PLACEHOLDER,
        requested_action=action,
        preservation_period=pres_period if pres_period else PRESERVATION_PERIOD_PLACEHOLDER,
        requested_record_categories=record_cats,
        investigator_notes=notes if notes else "No additional officer remarks recorded.",
    )


def extract_legal_evidence(
    inv: VictimInvestigationResponse,
    req: LegalDraftRequest,
) -> LegalEvidenceSnapshot:
    """
    Builds a deterministic, self-contained LegalEvidenceSnapshot directly from
    the verified investigation response.
    """
    acc = inv.account_number
    summary = inv.account_summary

    # 1. Subject Account Evidence
    subj_evidence = SubjectAccountLegalEvidence(
        account_number=acc,
        first_observed_timestamp=summary.first_observed_timestamp,
        last_observed_timestamp=summary.last_observed_timestamp,
        incoming_transaction_count=summary.incoming_transaction_count,
        outgoing_transaction_count=summary.outgoing_transaction_count,
        observed_inflow=summary.observed_incoming_volume,
        observed_outflow=summary.observed_outgoing_volume,
        observed_net_flow_delta=summary.observed_net_flow_delta,
        unique_counterparties=summary.unique_counterparties,
        unique_ip_count=summary.unique_ip_count,
        unique_device_count=summary.unique_device_count,
        payment_modes=list(summary.payment_modes.keys()) if isinstance(summary.payment_modes, dict) else list(summary.payment_modes),
        associated_ifscs=summary.associated_ifscs or [],
        associated_ips=summary.associated_ips or [],
    )

    # 2. Verified Transactions (sorted stably by timestamp ascending, row_id ascending)
    tx_items: List[VerifiedTransactionLegalItem] = []
    sorted_txs = sorted(inv.victim_transactions, key=lambda t: (t.timestamp or "", t.row_id or 0))
    for t in sorted_txs:
        tx_items.append(
            VerifiedTransactionLegalItem(
                transaction_id=t.transaction_id,
                row_id=t.row_id,
                timestamp=t.timestamp,
                sender_account=t.sender_account,
                receiver_account=t.receiver_account,
                amount=t.amount,
                payment_mode=t.payment_mode,
                sender_ifsc=t.sender_ifsc,
                receiver_ifsc=t.receiver_ifsc,
                ip_address=t.ip_address,
                device_type=t.device_type,
                narration=t.narration,
                direction=t.direction,
            )
        )

    # 3. Risk Evidence (Step 5B official 6-family point breakdown)
    risk_ev = LegalRiskEvidence(
        risk_index=inv.risk.risk_index,
        risk_band=inv.risk.risk_band,
        scoring_version=getattr(inv.risk, "risk_model_version", getattr(inv.risk, "scoring_version", "v1")),
        family_contributions=inv.risk.risk_family_scores,
        reason_codes=[r.code for r in inv.risk.risk_reasons],
    )

    # 4. Role Evidence (Step 4 Mule Roles)
    role_ev = LegalRoleEvidence(
        l1_collector_candidate=inv.roles.l1_collector_candidate,
        l2_distributor_candidate=inv.roles.l2_distributor_candidate,
        l3_terminal_candidate=inv.roles.l3_terminal_candidate,
        primary_role_label=inv.roles.primary_role_label,
        classification_reasons=inv.roles.classification_reasons,
        fan_in=inv.roles.fan_in,
        fan_out=inv.roles.fan_out,
    )

    # 5. Velocity Evidence (Step 5A 3-15 min window)
    vel_ev = LegalVelocityEvidence(
        pass_through_candidate=inv.velocity.pass_through_candidate,
        pass_through_ratio=inv.velocity.pass_through_ratio,
        qualifying_event_count=inv.velocity.qualifying_event_count,
        attributed_volume=inv.velocity.attributed_volume,
        outgoing_qualifying_count=inv.velocity.outgoing_qualifying_count,
        median_delay_seconds=inv.velocity.median_delay_seconds,
        window_description=inv.velocity.window_description,
        classification_version=inv.velocity.classification_version,
    )

    # 6. Attribution Evidence (Step 5C FIFO Fund Attribution)
    root_seed_amount = sum(round(e.attributed_amount, 2) for e in inv.trace.edges if e.edge_type == "ROOT_SEED")
    downstream_fifo_amount = sum(round(e.attributed_amount, 2) for e in inv.trace.edges if e.edge_type == "FIFO_ATTRIBUTION")
    root_seed_count = sum(1 for e in inv.trace.edges if e.edge_type == "ROOT_SEED")
    downstream_fifo_count = sum(1 for e in inv.trace.edges if e.edge_type == "FIFO_ATTRIBUTION")

    terminals_sample = [
        {
            "account_number": term.account_number,
            "hop": term.hop,
            "attributed_amount": term.attributed_amount,
            "primary_role": term.primary_role,
            "risk_index": term.risk_index,
            "risk_band": term.risk_band,
        }
        for term in inv.terminals[:20]
    ]

    attr_ev = LegalAttributionEvidence(
        root_seed_outflow=round(root_seed_amount, 2),
        downstream_cumulative_attribution=round(downstream_fifo_amount, 2),
        max_hops_traversed=inv.trace.total_hops_found,
        root_seed_edge_count=root_seed_count,
        downstream_fifo_edge_count=downstream_fifo_count,
        terminal_accounts_count=len(inv.terminals),
        terminal_accounts_sample=terminals_sample,
        attribution_policy=inv.trace.policy_name,
        attribution_policy_version=inv.trace.policy_version,
        is_truncated=inv.trace.truncated,
        truncation_reasons=[inv.trace.truncation_reason] if inv.trace.truncation_reason else [],
        cycles_detected=inv.trace.cycles_detected or [],
    )

    # 7. Compute deterministic canonical evidence hash
    # Build canonical payload omitting volatile timestamps
    canonical_payload = {
        "subject_account": subj_evidence.model_dump(mode="json"),
        "transactions_count": len(tx_items),
        "transactions_sample": [t.model_dump(mode="json") for t in tx_items[:25]],
        "risk": risk_ev.model_dump(mode="json"),
        "roles": role_ev.model_dump(mode="json"),
        "velocity": vel_ev.model_dump(mode="json"),
        "attribution": attr_ev.model_dump(mode="json"),
        "dataset_sha256": inv.data_provenance.dataset_sha256,
        "dataset_rows": inv.data_provenance.dataset_rows,
    }

    evidence_sha = hashlib.sha256(
        json.dumps(canonical_payload, sort_keys=True, indent=2).encode("utf-8")
    ).hexdigest()

    return LegalEvidenceSnapshot(
        snapshot_version="v1",
        subject_account=subj_evidence,
        transactions_sample=tx_items[:25],
        risk=risk_ev,
        roles=role_ev,
        velocity=vel_ev,
        attribution=attr_ev,
        case_file_id=req.case_file_id,
        case_diary_id=req.case_diary_id,
        dataset_name=inv.data_provenance.dataset_name,
        dataset_rows=inv.data_provenance.dataset_rows,
        dataset_sha256=inv.data_provenance.dataset_sha256,
        evidence_snapshot_sha256=evidence_sha,
        provenance_chain="RAW -> ANALYTICAL -> DERIVED -> LEGAL_DRAFT",
    )
