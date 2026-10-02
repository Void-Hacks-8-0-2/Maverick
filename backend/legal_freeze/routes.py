"""
Step 9: FastAPI Routes for Legal Freeze & Requisition Drafts
Operation 'ABHEDYA-CHAKRA'
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
import duckdb

from backend.db.connection import get_db
from backend.legal_freeze.generator import generate_legal_draft
from backend.legal_freeze.models import (
    LegalDraftPackage,
    LegalDraftRequest,
    LegalDraftResponse,
)
from backend.legal_freeze.store import LEGAL_DRAFT_STORE

router = APIRouter(prefix="/api/legal-freeze", tags=["Legal Freeze & Bank Requisitions"])


@router.post("/drafts", response_model=LegalDraftResponse)
def create_legal_draft_endpoint(
    req: LegalDraftRequest,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Generate a new structured legal draft document (Freeze Request, Preservation Request,
    Bank Requisition, or Evidence Annexure) from verified investigation evidence.
    """
    try:
        return generate_legal_draft(db, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Legal draft generation failed: {str(e)}")


@router.get("/drafts/{draft_id}", response_model=LegalDraftResponse)
def get_legal_draft_endpoint(draft_id: str):
    """Retrieve an existing legal draft package by ID from process-local storage."""
    pkg = LEGAL_DRAFT_STORE.get(draft_id)
    if not pkg:
        raise HTTPException(
            status_code=404,
            detail=f"Legal draft '{draft_id}' not found in process-local store",
        )
    return LegalDraftResponse(
        draft=pkg,
        generation_time_ms=0.0,
    )


@router.get("/drafts/{draft_id}/pdf")
def download_legal_draft_pdf(draft_id: str):
    """Download the compiled PDF legal draft document."""
    pdf_bytes = LEGAL_DRAFT_STORE.get_pdf(draft_id)
    if not pdf_bytes:
        raise HTTPException(
            status_code=404,
            detail=f"PDF binary for legal draft '{draft_id}' not found in store",
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={draft_id}.pdf",
            "Content-Type": "application/pdf",
        },
    )


@router.get("/drafts/{draft_id}/json")
def download_legal_draft_json(draft_id: str):
    """Download the canonical JSON evidence package for the legal draft."""
    json_bytes = LEGAL_DRAFT_STORE.get_json(draft_id)
    if not json_bytes:
        raise HTTPException(
            status_code=404,
            detail=f"JSON package for legal draft '{draft_id}' not found in store",
        )
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={draft_id}.json",
            "Content-Type": "application/json",
        },
    )


@router.get("/drafts", response_model=List[LegalDraftPackage])
def list_legal_drafts_endpoint(
    account_number: Optional[str] = Query(None, description="Filter by subject account")
):
    """List recent legal drafts stored in process-local memory."""
    if account_number:
        return LEGAL_DRAFT_STORE.list_by_account(account_number)
    return LEGAL_DRAFT_STORE.list_all()
