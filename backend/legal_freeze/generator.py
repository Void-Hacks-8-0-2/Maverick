"""
Step 9: Legal Freeze & Requisition Generator Orchestrator
Operation 'ABHEDYA-CHAKRA'
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

import duckdb

from backend.investigations.orchestrator import investigate_victim_account
from backend.legal_freeze.evidence import extract_legal_evidence, normalize_officer_details
from backend.legal_freeze.models import (
    LegalDocumentType,
    LegalDraftPackage,
    LegalDraftRequest,
    LegalDraftResponse,
    LegalDraftStatus,
)
from backend.legal_freeze.pdf_generator import generate_legal_draft_pdf
from backend.legal_freeze.store import LEGAL_DRAFT_STORE
from backend.legal_freeze.templates import build_legal_draft_document


def generate_legal_draft(
    con: duckdb.DuckDBPyConnection,
    req: LegalDraftRequest,
) -> LegalDraftResponse:
    """
    Orchestrates end-to-end deterministic generation of a structured legal draft document:
    1. Reconstructs investigation using materialized feature store (no raw CSV reload)
    2. Normalizes officer details with strict explicit placeholders for missing fields
    3. Extracts atomic verified legal evidence and computes evidence snapshot SHA-256
    4. Renders deterministic document template
    5. Compiles PDF document and calculates exact pdf_sha256
    6. Serializes canonical JSON and calculates exact json_sha256
    7. Stores artifacts in thread-safe process-local store
    8. Returns complete LegalDraftResponse with generation metrics
    """
    t_start = time.perf_counter()

    acc = req.subject_account.strip().upper()
    if not acc:
        raise ValueError("Subject account cannot be empty")

    # 1. Execute or reconstruct blind investigation
    inv = investigate_victim_account(
        con=con,
        account_id=acc,
        max_hops=req.max_hops,
        horizon_seconds=req.horizon_seconds,
        max_branches_per_hop=req.max_branches_per_hop,
    )

    # 2. Normalize officer and authority details (no fabrication of missing data)
    officer = normalize_officer_details(req)

    # 3. Extract atomic verified legal evidence
    evidence = extract_legal_evidence(inv, req)

    # 4. Render deterministic legal draft template
    doc_model = build_legal_draft_document(req.document_type, evidence, officer)

    # 5. Compile PDF document
    pdf_bytes = generate_legal_draft_pdf(doc_model, evidence, officer)
    pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    # 6. Generate deterministic package ID
    doc_prefix = req.document_type.value[:6]
    pkg_seed = f"{acc}_{doc_prefix}_{evidence.evidence_snapshot_sha256[:16]}"
    pkg_hash = hashlib.sha256(pkg_seed.encode("utf-8")).hexdigest()[:8].upper()
    package_id = f"DRAFT-{acc}-{doc_prefix}-{pkg_hash}"

    now_iso = datetime.now(timezone.utc).isoformat()

    download_urls = {
        "pdf": f"/api/legal-freeze/drafts/{package_id}/pdf",
        "json": f"/api/legal-freeze/drafts/{package_id}/json",
    }

    # 7. Compile canonical JSON representation
    package_dict = {
        "package_id": package_id,
        "document_type": req.document_type.value,
        "subject_account": acc,
        "case_file_id": req.case_file_id,
        "case_diary_id": req.case_diary_id,
        "investigation_id": inv.investigation_id,
        "created_at": now_iso,
        "status": LegalDraftStatus.REVIEW_REQUIRED.value,
        "officer_details": officer.model_dump(mode="json"),
        "evidence": evidence.model_dump(mode="json"),
        "document": doc_model.model_dump(mode="json"),
        "evidence_snapshot_sha256": evidence.evidence_snapshot_sha256,
        "pdf_sha256": pdf_sha256,
        "download_urls": download_urls,
    }
    json_bytes = json.dumps(package_dict, sort_keys=True, indent=2).encode("utf-8")
    json_sha256 = hashlib.sha256(json_bytes).hexdigest()

    # 8. Assemble complete package
    package = LegalDraftPackage(
        package_id=package_id,
        document_type=req.document_type,
        subject_account=acc,
        case_file_id=req.case_file_id,
        case_diary_id=req.case_diary_id,
        investigation_id=inv.investigation_id,
        created_at=now_iso,
        status=LegalDraftStatus.REVIEW_REQUIRED,
        officer_details=officer,
        evidence=evidence,
        document=doc_model,
        evidence_snapshot_sha256=evidence.evidence_snapshot_sha256,
        pdf_sha256=pdf_sha256,
        json_sha256=json_sha256,
        download_urls=download_urls,
    )

    # 9. Store in process-local store
    LEGAL_DRAFT_STORE.save(package, pdf_bytes, json_bytes)

    t_end = time.perf_counter()
    latency_ms = round((t_end - t_start) * 1000, 2)

    return LegalDraftResponse(
        draft=package,
        generation_time_ms=latency_ms,
    )
