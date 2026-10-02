"""
Case Diary Pydantic Models for Operation 'ABHEDYA-CHAKRA'
Step 8: Strongly typed evidence diary, chronology, findings, and AI narrative contracts.

Architecture:
  Verified Investigation / Case File
      ↓
  Deterministic Structured Evidence Facts (VerifiedFact)
      ↓
  Case Diary Evidence Model (CaseDiary)
      ↓
  Constrained AI Narrative Generation
      ↓
  Officer-readable Case Diary (ai_narrative)

FORENSIC RULE: AI is ONLY a narrative-generation layer.
               The AI must NEVER become a source of evidence.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Verified Fact — atomic traceable evidence item
# ---------------------------------------------------------------------------

class VerifiedFact(BaseModel):
    """
    A single atomic forensic fact directly traceable to its source.
    Every fact carries a category, machine-readable code, and source reference.
    """
    fact_id: str = Field(..., description="Stable unique fact identifier (e.g. FACT-RISK-01)")
    category: str = Field(..., description="Fact category: SUBJECT, TRANSACTION, RISK, ROLE, VELOCITY, ATTRIBUTION, PROVENANCE")
    code: str = Field(..., description="Machine-readable fact code (e.g. RISK_INDEX, PASS_THROUGH_CANDIDATE)")
    statement: str = Field(..., description="Human-readable neutral factual statement")
    value: Any = Field(..., description="Machine-readable value (numeric, boolean, string, or structured)")
    source_type: str = Field(..., description="Source tier: RAW | DERIVED | ATTRIBUTED | CASE_FILE")
    source_reference: str = Field(..., description="Reference to the originating record/field (e.g. transaction_id, risk_family)")
    confidence: str = Field("DETERMINISTIC", description="DETERMINISTIC | ANALYTICAL | INFERRED")
    provenance: str = Field("VERIFIED", description="VERIFIED | DERIVED | ATTRIBUTED")


# ---------------------------------------------------------------------------
# Chronology Events
# ---------------------------------------------------------------------------

class DiaryChronologyEvent(BaseModel):
    """
    A single chronological event in the case diary.
    Always derived from verified sources; never invented.
    """
    event_id: str = Field(..., description="Stable sequential event identifier")
    event_type: str = Field(
        ...,
        description=(
            "CASE_OPENED | ROOT_TRANSACTION | ATTRIBUTION_HOP | VELOCITY_EVENT | "
            "RISK_FINDING | ROLE_FINDING | TERMINAL_ACCOUNT | INVESTIGATOR_NOTE | CASE_FILE_GENERATED"
        )
    )
    timestamp: Optional[str] = Field(None, description="ISO-8601 UTC event timestamp (from verified source)")
    sort_key: str = Field(..., description="Deterministic sort key: timestamp + source_row_id + tx_id for stable ordering")
    description: str = Field(..., description="Factual neutral description of this event")
    source_reference: str = Field(..., description="Originating source (transaction_id, edge_id, investigation_id, etc.)")
    amount: Optional[float] = Field(None, description="Monetary amount if applicable (INR)")
    hop: Optional[int] = Field(None, description="Hop index for ATTRIBUTION_HOP events")
    sender_account: Optional[str] = Field(None, description="Sender account for transaction events")
    receiver_account: Optional[str] = Field(None, description="Receiver account for transaction events")
    edge_type: Optional[str] = Field(None, description="ROOT_SEED or FIFO_ATTRIBUTION for attribution events")
    provenance: str = Field("VERIFIED", description="VERIFIED | DERIVED")


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

class RiskFinding(BaseModel):
    """Step 5B official risk finding extracted verbatim."""
    risk_index: float
    risk_band: str
    scoring_version: str
    family_contributions: Dict[str, float]
    top_reason_codes: List[str]
    provenance: str = "DERIVED"


class RoleFinding(BaseModel):
    """Step 4 mule role classification finding."""
    l1_collector_candidate: bool
    l2_distributor_candidate: bool
    l3_terminal_candidate: bool
    primary_role_label: str
    classification_reasons: List[str]
    fan_in: int
    fan_out: int
    provenance: str = "DERIVED"


class VelocityFinding(BaseModel):
    """Step 5A pass-through velocity finding."""
    pass_through_candidate: bool
    pass_through_ratio: float
    qualifying_event_count: int
    attributed_volume: float
    outgoing_qualifying_count: int
    median_delay_seconds: Optional[float]
    window_description: str
    classification_version: str
    provenance: str = "DERIVED"


class AttributionFinding(BaseModel):
    """Step 5C FIFO attribution finding."""
    root_seed_outflow: float
    downstream_cumulative_attribution: float
    max_hops_traversed: int
    root_seed_edge_count: int
    downstream_fifo_edge_count: int
    attribution_policy: str
    attribution_policy_version: str
    is_truncated: bool
    truncation_reasons: List[str]
    cycles_detected: List[str]
    terminal_account_count: int
    conservation_note: str = (
        "downstream_cumulative_attribution represents fund propagation across hops "
        "and must NOT be summed as unique new funds."
    )
    provenance: str = "ATTRIBUTED"


class DiaryFindings(BaseModel):
    """Structured, deterministic forensic findings for the subject account."""
    risk: RiskFinding
    role: RoleFinding
    velocity: VelocityFinding
    attribution: AttributionFinding
    provenance: str = "DERIVED"


# ---------------------------------------------------------------------------
# Narrative metadata & validation
# ---------------------------------------------------------------------------

class NarrativeValidationResult(BaseModel):
    """Result of the post-generation hallucination guardrail validation."""
    validation_status: str = Field(
        ...,
        description="PASSED | FAILED | SKIPPED (SKIPPED only when deterministic fallback used)"
    )
    validated_at: Optional[str] = Field(None, description="ISO-8601 UTC timestamp of validation")
    checks_performed: List[str] = Field(default_factory=list, description="List of validation checks run")
    violations_found: List[str] = Field(default_factory=list, description="Specific violations detected")
    fallback_triggered: bool = Field(False, description="True if deterministic fallback was used")
    fallback_reason: Optional[str] = Field(None, description="Why fallback was triggered")


class NarrativeMetadata(BaseModel):
    """Metadata for the AI-assisted narrative generation."""
    narrative_version: str = Field("v1", description="Narrative generation version")
    narrative_source: str = Field(
        ...,
        description="AI_GEMINI | DETERMINISTIC_FALLBACK"
    )
    ai_model: Optional[str] = Field(None, description="AI model identifier used, if any")
    generated_at: str = Field(..., description="ISO-8601 UTC generation timestamp")
    input_fact_count: int = Field(..., description="Number of verified facts supplied to narrative engine")
    input_event_count: int = Field(..., description="Number of chronology events supplied to narrative engine")
    validation: NarrativeValidationResult
    disclaimer: str = Field(
        "AI-generated narrative is derived from verified investigative data and is provided as an "
        "officer-assistance layer. It does not create, modify, or independently establish evidence "
        "or legal conclusions.",
        description="Mandatory AI interpretation disclaimer"
    )


# ---------------------------------------------------------------------------
# Core CaseDiary model
# ---------------------------------------------------------------------------

class CaseDiary(BaseModel):
    """
    Complete Case Diary for a subject account.

    Strictly separates:
    - VERIFIED EVIDENCE (facts, chronology, findings) — deterministic
    - AI-ASSISTED NARRATIVE — interpretation layer only

    The AI narrative is derived solely from verified_facts and chronology.
    It does not independently establish evidence.
    """
    # Identity
    case_diary_id: str = Field(..., description="Case Diary identifier (e.g. DIARY-KKBK10000402-ABCD1234)")
    case_file_id: Optional[str] = Field(None, description="Linked Step 7 Case File ID if generated")
    investigation_id: str = Field(..., description="Step 6 investigation identifier")
    subject_account: str = Field(..., description="Subject account number")
    created_at: str = Field(..., description="ISO-8601 UTC creation timestamp")
    updated_at: str = Field(..., description="ISO-8601 UTC last update timestamp")
    status: str = Field(..., description="COMPLETED | PARTIAL_EVIDENCE | NARRATIVE_FAILED")

    # Investigator notes (editable after creation)
    investigator_notes: str = Field("", description="Free-text officer investigation notes")

    # Integrity seals
    evidence_snapshot_sha256: str = Field(..., description="SHA-256 of the evidence snapshot used")
    data_provenance: Dict[str, Any] = Field(..., description="Dataset provenance information")

    # Verified structured evidence
    verified_facts: List[VerifiedFact] = Field(default_factory=list, description="Deterministic atomic facts")
    chronology: List[DiaryChronologyEvent] = Field(default_factory=list, description="Timestamp-sorted verified events")
    findings: DiaryFindings = Field(..., description="Structured forensic findings")

    # Warnings and limitations (propagated from investigation)
    warnings: List[str] = Field(default_factory=list)
    limitations: Dict[str, Any] = Field(default_factory=dict)

    # AI Narrative — CLEARLY SEPARATED from verified evidence
    ai_narrative: Optional[str] = Field(
        None,
        description=(
            "AI-ASSISTED NARRATIVE — GENERATED FROM VERIFIED EVIDENCE ONLY. "
            "This is an interpretive layer and does not independently establish evidence or legal conclusions."
        )
    )
    narrative_metadata: Optional[NarrativeMetadata] = Field(None)

    persistence_note: str = Field(
        "Case-diary metadata and generated artifacts are maintained in process-local storage "
        "and are not persistent across backend restarts.",
        description="Process-local persistence limitation"
    )


# ---------------------------------------------------------------------------
# API request/response contracts
# ---------------------------------------------------------------------------

class CaseDiaryRequest(BaseModel):
    """Request to create a new Case Diary for a subject account."""
    account_number: str = Field(..., description="Subject account to generate case diary for")
    case_file_id: Optional[str] = Field(None, description="Existing case file ID to link (optional)")
    max_hops: int = Field(4, ge=1, le=4)
    horizon_seconds: Optional[int] = Field(None)
    max_branches_per_hop: int = Field(50, ge=1, le=500)
    generate_narrative: bool = Field(True, description="Whether to generate AI narrative immediately")
    investigator_notes: str = Field("", description="Initial officer notes")


class GenerateNarrativeRequest(BaseModel):
    """Request to (re)generate the AI narrative for an existing case diary."""
    force_deterministic: bool = Field(
        False,
        description="If True, skip AI and use deterministic fallback narrative"
    )
    investigator_notes: Optional[str] = Field(None, description="Updated officer notes")


class CaseDiaryResponse(BaseModel):
    """API response wrapping a complete CaseDiary."""
    case_diary: CaseDiary
    generation_time_ms: float = Field(..., description="Total generation time in milliseconds")
    disclaimer: str = Field(
        "INVESTIGATIVE FORENSICS ONLY — Deterministic accounting and behavioral models. "
        "AI narrative is an interpretation layer derived from verified evidence. "
        "Does not constitute legal proof, beneficial ownership determination, or judicial finding.",
        description="Mandatory forensic + AI disclaimer"
    )
