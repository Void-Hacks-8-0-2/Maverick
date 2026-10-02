"""
Case Diary Service for Operation 'ABHEDYA-CHAKRA'
Step 8: Orchestrates investigation reconstruction → evidence extraction →
        chronology assembly → finding extraction → narrative generation → storage.

Performance strategy:
- Reuses the existing investigate_victim_account() pipeline (Step 6)
- Does NOT recompute 2M-row dataset independently
- Reuses materialized features from DuckDB tier
- Targets similar O(investigation) performance as Step 6/7
"""

import hashlib
import time
from datetime import datetime, timezone
from typing import Optional

import duckdb

from backend.case_diary.evidence import (
    extract_chronology,
    extract_findings,
    extract_verified_facts,
)
from backend.case_diary.models import (
    CaseDiary,
    CaseDiaryRequest,
    CaseDiaryResponse,
    GenerateNarrativeRequest,
)
from backend.case_diary.narrative import generate_narrative
from backend.case_diary.store import CASE_DIARY_STORE
from backend.investigations.orchestrator import investigate_victim_account


def build_case_diary(
    con: duckdb.DuckDBPyConnection,
    req: CaseDiaryRequest,
) -> CaseDiaryResponse:
    """
    Full case diary construction pipeline.

    Steps:
    1. Run (or reconstruct) investigation via existing Step 6 engine
    2. Extract VerifiedFacts
    3. Build deterministic chronology
    4. Extract DiaryFindings
    5. Optionally generate AI narrative (with validation + fallback)
    6. Compute evidence SHA
    7. Assemble CaseDiary
    8. Store in process-local CASE_DIARY_STORE
    """
    t_start = time.perf_counter()
    acc = req.account_number.strip().upper()
    if not acc:
        raise ValueError("account_number cannot be empty")

    # Step 1: Run investigation (reuses materialized features, does not reload CSV)
    inv = investigate_victim_account(
        con=con,
        account_id=acc,
        max_hops=req.max_hops,
        horizon_seconds=req.horizon_seconds,
        max_branches_per_hop=req.max_branches_per_hop,
    )

    # Step 2: Extract VerifiedFacts
    facts = extract_verified_facts(inv)

    # Step 3: Build chronology
    chronology = extract_chronology(inv)

    # Step 4: Extract structured findings
    findings = extract_findings(inv)

    # Step 5: Compute evidence SHA (over facts, deterministic)
    import json
    facts_dict = [f.model_dump(mode="json") for f in facts]
    evidence_sha = hashlib.sha256(
        json.dumps(facts_dict, sort_keys=True, indent=2).encode("utf-8")
    ).hexdigest()

    # Step 6: Deterministic IDs
    diary_hash = hashlib.sha256(f"{acc}_{evidence_sha}".encode()).hexdigest()[:8].upper()
    diary_id = f"DIARY-{acc}-{diary_hash}"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Step 7: Build provenance dict
    prov = inv.data_provenance
    data_provenance = {
        "dataset_name": prov.dataset_name,
        "dataset_rows": prov.dataset_rows,
        "dataset_sha256": prov.dataset_sha256,
        "attribution_policy": prov.attribution_policy,
        "attribution_policy_version": prov.attribution_policy_version,
        "risk_scoring_version": prov.risk_scoring_version,
        "velocity_classification_version": prov.velocity_classification_version,
        "integrity_statement": prov.integrity_statement,
    }

    # Step 8: Generate narrative (if requested)
    ai_narrative: Optional[str] = None
    narrative_metadata = None

    if req.generate_narrative:
        ai_narrative, narrative_metadata = generate_narrative(
            subject_account=acc,
            facts=facts,
            findings=findings,
            chronology=chronology,
            warnings=inv.warnings,
        )

    # Step 9: Determine status
    status = inv.status  # COMPLETED, NO_QUALIFYING_OUTFLOW, PARTIAL_EVIDENCE

    # Step 10: Limitations dict
    limitations = {
        "dataset_observation_window": "15-day closed dataset window (2,000,000 transactions)",
        "ground_truth_status": "No external ground-truth labels; analytical findings are deterministic heuristics.",
        "legal_nature_disclaimer": (
            "TEMPORAL_FIFO is a deterministic accounting policy, not judicial proof."
        ),
        "branch_limits_applied": f"max_branches_per_hop={req.max_branches_per_hop}",
        "persistence_limitation": (
            "Case-diary metadata and generated artifacts are maintained in process-local storage "
            "and are not persistent across backend restarts."
        ),
        "is_truncated": inv.trace.truncated,
        "truncation_reasons": [inv.trace.truncation_reason] if inv.trace.truncation_reason else [],
        "cycles_detected": inv.trace.cycles_detected or [],
    }

    # Step 11: Assemble diary
    diary = CaseDiary(
        case_diary_id=diary_id,
        case_file_id=req.case_file_id,
        investigation_id=inv.investigation_id,
        subject_account=acc,
        created_at=now_iso,
        updated_at=now_iso,
        status=status,
        investigator_notes=req.investigator_notes,
        evidence_snapshot_sha256=evidence_sha,
        data_provenance=data_provenance,
        verified_facts=facts,
        chronology=chronology,
        findings=findings,
        warnings=inv.warnings,
        limitations=limitations,
        ai_narrative=ai_narrative,
        narrative_metadata=narrative_metadata,
    )

    # Step 12: Store
    CASE_DIARY_STORE.save(diary)

    t_end = time.perf_counter()
    elapsed_ms = round((t_end - t_start) * 1000, 1)

    return CaseDiaryResponse(
        case_diary=diary,
        generation_time_ms=elapsed_ms,
    )


def regenerate_narrative(
    diary_id: str,
    req: GenerateNarrativeRequest,
) -> CaseDiaryResponse:
    """
    (Re)generate the AI narrative for an existing case diary.
    Does not re-run the full investigation.
    """
    t_start = time.perf_counter()
    diary = CASE_DIARY_STORE.get(diary_id)
    if diary is None:
        raise ValueError(f"Case diary '{diary_id}' not found in process-local store.")

    if req.investigator_notes is not None:
        diary.investigator_notes = req.investigator_notes

    narrative, metadata = generate_narrative(
        subject_account=diary.subject_account,
        facts=diary.verified_facts,
        findings=diary.findings,
        chronology=diary.chronology,
        warnings=diary.warnings,
        force_deterministic=req.force_deterministic,
    )

    updated_at = datetime.now(timezone.utc).isoformat()
    updated = CASE_DIARY_STORE.update_narrative(
        diary_id=diary_id,
        narrative=narrative,
        narrative_metadata=metadata,
        updated_at=updated_at,
    )

    t_end = time.perf_counter()
    return CaseDiaryResponse(
        case_diary=updated,
        generation_time_ms=round((t_end - t_start) * 1000, 1),
    )
