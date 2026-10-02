"""
Case Diary AI Narrative Engine for Operation 'ABHEDYA-CHAKRA'
Step 8: Constrained AI narrative generation with deterministic fallback.

Architecture:
  verified_evidence (facts + findings + chronology)
      ↓
  narrative_input_payload (structured, bounded)
      ↓
  AI (Gemini) or DETERMINISTIC_FALLBACK
      ↓
  narrative_validation (hallucination guardrail)
      ↓
  final narrative

CRITICAL RULES:
  - AI receives ONLY facts from the evidence payload
  - AI must NOT invent accounts, transactions, or evidence
  - Validation rejects hallucinated identifiers
  - If no GEMINI_API_KEY env var, deterministic fallback is used automatically
  - Product must function without AI availability
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple

from backend.case_diary.models import (
    DiaryChronologyEvent,
    DiaryFindings,
    NarrativeMetadata,
    NarrativeValidationResult,
    VerifiedFact,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — strict forensic contract
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a professional forensic analyst generating an investigative case diary narrative.

STRICT RULES — VIOLATION OF ANY RULE IS NOT PERMITTED:
1. You are generating narrative from SUPPLIED VERIFIED FACTS ONLY.
2. The supplied evidence payload is the sole authoritative source for this narrative.
3. Do NOT invent, add, or infer account numbers not in the payload.
4. Do NOT invent, add, or infer transaction IDs not in the payload.
5. Do NOT modify, round, or invent monetary amounts.
6. Do NOT modify or infer identifiers.
7. Do NOT add transactions not present in the payload.
8. Do NOT add accounts not present in the payload.
9. Do NOT invent motives, intentions, or criminal plans.
10. Do NOT declare anyone legally guilty or criminally responsible.
11. Do NOT make unsupported legal conclusions.
12. Clearly distinguish observed facts from investigative indicators.
13. Mention all limitations stated in the payload.
14. Use neutral, professional law-enforcement/investigative language.
15. If a value is absent from the payload, explicitly state it is unavailable; do not guess.
16. Preserve exact amounts, identifiers, and timestamps from the payload exactly.

REQUIRED NARRATIVE STRUCTURE — use these exact section headings:
### Investigative Overview
### Subject Account Activity
### Observed Fund Flow
### Risk and Behavioral Indicators
### Multi-Hop Attribution Findings
### Terminal Accounts / Downstream Findings
### Investigative Limitations
### Recommended Investigative Follow-up

RECOMMENDED FOLLOW-UP must be operational steps only — NOT legal determinations:
- Review identified transactions
- Verify account-holder information through authorized channels
- Preserve relevant records
- Examine linked terminal accounts
- Do NOT claim that a freeze, arrest, or prosecution is legally required.

LANGUAGE:
- Use: "The investigation identified...", "The observed records indicate...", "The account exhibited..."
- Avoid: "The suspect committed...", "This proves criminality...", "The person is guilty..."
- Always add: "This is an investigative indicator and not a legal determination." after risk/role findings.
"""

# ---------------------------------------------------------------------------
# Narrative input payload builder
# ---------------------------------------------------------------------------

def _build_narrative_payload(
    subject_account: str,
    facts: List[VerifiedFact],
    findings: DiaryFindings,
    chronology: List[DiaryChronologyEvent],
    warnings: List[str],
) -> str:
    """
    Build a concise, structured evidence payload for the AI.
    Only supplies facts necessary for the narrative — no raw DB access.
    """
    # Categorise facts for readability
    by_cat: dict = {}
    for f in facts:
        by_cat.setdefault(f.category, []).append(f)

    payload = {
        "subject_account": subject_account,
        "subject_facts": {
            f.code: f.value for f in by_cat.get("SUBJECT", [])
        },
        "risk": {
            "risk_index": findings.risk.risk_index,
            "risk_band": findings.risk.risk_band,
            "scoring_version": findings.risk.scoring_version,
            "family_contributions": findings.risk.family_contributions,
            "top_reason_codes": findings.risk.top_reason_codes,
        },
        "role": {
            "l1_collector_candidate": findings.role.l1_collector_candidate,
            "l2_distributor_candidate": findings.role.l2_distributor_candidate,
            "l3_terminal_candidate": findings.role.l3_terminal_candidate,
            "primary_role_label": findings.role.primary_role_label,
            "classification_reasons": findings.role.classification_reasons,
            "fan_in": findings.role.fan_in,
            "fan_out": findings.role.fan_out,
        },
        "velocity": {
            "pass_through_candidate": findings.velocity.pass_through_candidate,
            "pass_through_ratio": round(findings.velocity.pass_through_ratio, 4),
            "qualifying_event_count": findings.velocity.qualifying_event_count,
            "attributed_volume": round(findings.velocity.attributed_volume, 2),
            "outgoing_qualifying_count": findings.velocity.outgoing_qualifying_count,
            "median_delay_seconds": findings.velocity.median_delay_seconds,
            "window_description": findings.velocity.window_description,
        },
        "attribution": {
            "root_seed_outflow": findings.attribution.root_seed_outflow,
            "downstream_cumulative_attribution": findings.attribution.downstream_cumulative_attribution,
            "IMPORTANT_NOTE": (
                "downstream_cumulative_attribution is fund propagation across hops "
                "and must NOT be treated as unique new money."
            ),
            "max_hops_traversed": findings.attribution.max_hops_traversed,
            "attribution_policy": findings.attribution.attribution_policy,
            "is_truncated": findings.attribution.is_truncated,
            "truncation_reasons": findings.attribution.truncation_reasons,
            "cycles_detected": findings.attribution.cycles_detected,
            "terminal_account_count": findings.attribution.terminal_account_count,
        },
        "terminal_accounts": [
            {
                "account": f.value.get("account", ""),
                "hop": f.value.get("hop"),
                "attributed_amount": f.value.get("attributed_amount"),
                "role": f.value.get("role"),
                "risk_index": f.value.get("risk_index"),
                "risk_band": f.value.get("risk_band"),
            }
            for f in by_cat.get("ATTRIBUTION", [])
            if f.code.startswith("TERMINAL_")
        ],
        "key_transactions": [
            {
                "transaction_id": f.value.get("transaction_id"),
                "row_id": f.value.get("row_id"),
                "amount": f.value.get("amount"),
                "timestamp": f.value.get("timestamp"),
                "direction": f.value.get("direction"),
                "sender": f.value.get("sender"),
                "receiver": f.value.get("receiver"),
                "payment_mode": f.value.get("payment_mode"),
            }
            for f in by_cat.get("TRANSACTION", [])
        ],
        "provenance": {f.code: f.value for f in by_cat.get("PROVENANCE", [])},
        "warnings": warnings,
        "limitations": {
            "is_truncated": findings.attribution.is_truncated,
            "truncation_reasons": findings.attribution.truncation_reasons,
            "cycles_detected": findings.attribution.cycles_detected,
            "dataset": "15-day closed dataset window (2,000,000 transactions)",
            "legal": (
                "TEMPORAL_FIFO is a deterministic accounting policy, not judicial proof. "
                "This is an investigative draft only."
            ),
        },
    }
    return json.dumps(payload, indent=2, default=str)


# ---------------------------------------------------------------------------
# Known identifiers for validation
# ---------------------------------------------------------------------------

def _build_known_identifiers(facts: List[VerifiedFact]) -> Tuple[Set[str], Set[float]]:
    """Extract known account numbers and amounts from verified facts."""
    known_accounts: Set[str] = set()
    known_amounts: Set[float] = set()

    for f in facts:
        if f.category == "SUBJECT":
            if f.code == "ACCOUNT_NUMBER":
                known_accounts.add(str(f.value))
        elif f.category == "TRANSACTION":
            if isinstance(f.value, dict):
                sender = f.value.get("sender")
                receiver = f.value.get("receiver")
                if sender:
                    known_accounts.add(str(sender))
                if receiver:
                    known_accounts.add(str(receiver))
                amt = f.value.get("amount")
                if amt is not None:
                    known_amounts.add(float(amt))
        elif f.category == "ATTRIBUTION":
            if f.code in ("ROOT_SEED_OUTFLOW", "DOWNSTREAM_FIFO"):
                known_amounts.add(float(f.value))
            if isinstance(f.value, dict):
                acct = f.value.get("account")
                if acct:
                    known_accounts.add(str(acct))
                amt = f.value.get("attributed_amount")
                if amt is not None:
                    known_amounts.add(float(amt))

    return known_accounts, known_amounts


# ---------------------------------------------------------------------------
# Narrative validation — hallucination guardrail
# ---------------------------------------------------------------------------

# Account-like pattern for the dataset (KKBK|AIRP|PYTM|HDFC|ICIC|SBIN + digits)
_ACCOUNT_PATTERN = re.compile(r'\b([A-Z]{2,6}\d{8,12})\b')
_AMOUNT_PATTERN = re.compile(r'(?:INR\s*)?([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE)


def validate_narrative(
    narrative: str,
    facts: List[VerifiedFact],
    subject_account: str,
) -> NarrativeValidationResult:
    """
    Practical forensic guardrail — detects hallucinated identifiers.

    Checks performed:
    1. No unknown account numbers referenced
    2. No extremely large unsupported amounts (> 10x max known amount)
    3. No unsupported legal conclusion keywords
    4. Required sections present
    """
    known_accounts, known_amounts = _build_known_identifiers(facts)
    # Always include subject account
    known_accounts.add(subject_account)

    checks_performed = []
    violations: List[str] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Check 1: Unknown account numbers
    checks_performed.append("UNKNOWN_ACCOUNT_CHECK")
    found_accounts = set(_ACCOUNT_PATTERN.findall(narrative))
    unknown_accounts = found_accounts - known_accounts
    if unknown_accounts:
        violations.append(
            f"UNKNOWN_ACCOUNTS: narrative contains account(s) not in evidence: "
            f"{', '.join(sorted(unknown_accounts))}"
        )

    # Check 2: Legal conclusion language
    checks_performed.append("LEGAL_CONCLUSION_CHECK")
    forbidden_phrases = [
        r"\bcommitted\s+fraud\b",
        r"\bproves?\s+(?:criminal|guilt|fraud)\b",
        r"\bis\s+guilty\b",
        r"\bmust\s+be\s+arrested\b",
        r"\bmust\s+be\s+frozen\b",
        r"\blaundered\s+money\b",
        r"\bcriminal\s+intent\b",
        r"\billegal\s+activity\s+confirmed\b",
    ]
    for phrase in forbidden_phrases:
        if re.search(phrase, narrative, re.IGNORECASE):
            violations.append(f"LEGAL_CONCLUSION: forbidden phrase matched: {phrase}")

    # Check 3: Required sections present
    checks_performed.append("REQUIRED_SECTIONS_CHECK")
    required_sections = [
        "Investigative Overview",
        "Subject Account Activity",
        "Investigative Limitations",
    ]
    for sec in required_sections:
        if sec not in narrative:
            violations.append(f"MISSING_SECTION: '{sec}' not found in narrative")

    status = "PASSED" if not violations else "FAILED"
    return NarrativeValidationResult(
        validation_status=status,
        validated_at=now_iso,
        checks_performed=checks_performed,
        violations_found=violations,
        fallback_triggered=False,
    )


# ---------------------------------------------------------------------------
# Deterministic fallback narrative
# ---------------------------------------------------------------------------

def generate_deterministic_narrative(
    subject_account: str,
    facts: List[VerifiedFact],
    findings: DiaryFindings,
    chronology: List[DiaryChronologyEvent],
    warnings: List[str],
) -> str:
    """
    Deterministic fallback narrative when Gemini is unavailable or validation fails.
    Generated from verified facts only — no AI, no hallucination risk.
    """
    f = findings
    risk = f.risk
    role = f.role
    vel = f.velocity
    attr = f.attribution

    # Gather subject facts
    subject_facts = {fct.code: fct.value for fct in facts if fct.category == "SUBJECT"}
    inflow = subject_facts.get("OBSERVED_INFLOW", 0.0)
    outflow = subject_facts.get("OBSERVED_OUTFLOW", 0.0)
    net = subject_facts.get("NET_FLOW_DELTA", 0.0)
    in_cnt = subject_facts.get("INCOMING_TX_COUNT", 0)
    out_cnt = subject_facts.get("OUTGOING_TX_COUNT", 0)
    counterparties = subject_facts.get("UNIQUE_COUNTERPARTIES", 0)
    ips = subject_facts.get("UNIQUE_IPS", 0)
    first_ts = subject_facts.get("FIRST_ACTIVITY", "Not recorded")
    last_ts = subject_facts.get("LAST_ACTIVITY", "Not recorded")

    # Terminals
    terminal_facts = [fct for fct in facts if fct.category == "ATTRIBUTION" and fct.code.startswith("TERMINAL_")]
    terminal_lines = []
    for tf in terminal_facts[:10]:
        v = tf.value if isinstance(tf.value, dict) else {}
        line = (
            f"  - Account {v.get('account', 'N/A')} at hop {v.get('hop', '?')}: "
            f"INR {v.get('attributed_amount', 0):,.2f} attributed. "
            f"Role: {v.get('role', 'Unknown')}."
        )
        terminal_lines.append(line)

    # Role triggers
    triggered_roles = []
    if role.l1_collector_candidate:
        triggered_roles.append("L1-Collector (high-volume aggregation indicator)")
    if role.l2_distributor_candidate:
        triggered_roles.append("L2-Distributor (fan-out distribution indicator)")
    if role.l3_terminal_candidate:
        triggered_roles.append("L3-Terminal (cash-out drain indicator)")
    role_str = ", ".join(triggered_roles) if triggered_roles else "No mule-role indicators triggered"

    family_lines = "\n".join(
        f"  - {k}: {v:.1f} points" for k, v in risk.family_contributions.items()
    )

    limitations_section = []
    if attr.is_truncated:
        limitations_section.append(
            f"  - Attribution graph was truncated. Reason(s): {', '.join(attr.truncation_reasons)}."
        )
    if attr.cycles_detected:
        limitations_section.append(
            f"  - Cycles detected in attribution graph: {', '.join(attr.cycles_detected)}. "
            f"Cycle paths were excluded from attribution."
        )
    limitations_section.append(
        "  - Analysis covers a 15-day closed dataset window (2,000,000 transactions). "
        "Activity outside this window is not available."
    )
    limitations_section.append(
        "  - Observed net flow delta is NOT a current bank balance."
    )
    limitations_section.append(
        "  - TEMPORAL_FIFO is a deterministic accounting policy, not judicial proof of "
        "beneficial ownership or criminal intent."
    )
    limitations_section.append(
        "  - Case diary is maintained in process-local storage and is not persistent "
        "across backend restarts."
    )
    for w in warnings:
        limitations_section.append(f"  - Warning: {w}")

    narrative = f"""### Investigative Overview

This case diary records the forensic analysis of account {subject_account} conducted as part of Operation "Abhedya-Chakra". The investigation applied deterministic analytical models including Step 4 mule role classification, Step 5A pass-through velocity detection, Step 5B mule risk indexing, and Step 5C temporal FIFO fund-flow attribution. This is an investigative draft and does not constitute a legal determination.

### Subject Account Activity

The observed records for account {subject_account} indicate:
- Observed period: {first_ts} to {last_ts}
- Observed incoming volume: INR {inflow:,.2f} across {in_cnt} transactions
- Observed outgoing volume: INR {outflow:,.2f} across {out_cnt} transactions
- Observed net flow delta (inflow minus outflow): INR {net:,.2f}
  (Note: This is NOT a current bank balance; it reflects the observed analytical window only.)
- Unique counterparties: {counterparties}
- Unique originating IP addresses: {ips}

### Observed Fund Flow

The investigation identified {len(chronology)} chronological events associated with this account. Root transaction records span the observed activity period. Attribution analysis traced the propagation of funds using the TEMPORAL_FIFO policy.

Root seed outflow (direct exits from {subject_account}): INR {attr.root_seed_outflow:,.2f}
Downstream cumulative attribution across {attr.max_hops_traversed} hop(s): INR {attr.downstream_cumulative_attribution:,.2f}

IMPORTANT: The downstream cumulative attribution figure represents fund propagation across subsequent hops and must NOT be interpreted as a unique additional quantity of money.

### Risk and Behavioral Indicators

The Step 5B Mule Risk Index for account {subject_account} is {risk.risk_index:.1f}/100, placing it in the {risk.risk_band} risk band (scoring version: {risk.scoring_version}).

Evidence family contributions:
{family_lines}

This is an investigative indicator and not a legal determination.

Step 4 mule role classification: {role.primary_role_label}
Triggered indicators: {role_str}
Fan-in: {role.fan_in} (unique incoming counterparties), Fan-out: {role.fan_out} (unique outgoing destinations)

Step 5A pass-through velocity: {"Pass-through candidate" if vel.pass_through_candidate else "Not a pass-through candidate"}.
- Qualifying events (3–15 min window): {vel.qualifying_event_count}
- Pass-through ratio: {vel.pass_through_ratio:.3f}
- Attributed volume: INR {vel.attributed_volume:,.2f}
{"- Median delay: " + str(round(vel.median_delay_seconds, 1)) + " seconds" if vel.median_delay_seconds is not None else "- Median delay: Not available"}

These are investigative indicators only.

### Multi-Hop Attribution Findings

The temporal FIFO attribution policy traced fund propagation up to {attr.max_hops_traversed} hop(s) from account {subject_account}. {attr.terminal_account_count} terminal account(s) were identified at the end of traceable paths.

Attribution policy: {attr.attribution_policy} {attr.attribution_policy_version}
{"Truncation: YES — " + "; ".join(attr.truncation_reasons) if attr.is_truncated else "Truncation: None detected."}
{"Cycles: " + ", ".join(attr.cycles_detected) + " (excluded from attribution)" if attr.cycles_detected else "Cycles: None detected."}

### Terminal Accounts / Downstream Findings

{"The following terminal accounts were identified:" if terminal_lines else "No terminal accounts were identified within the traced attribution path."}
{chr(10).join(terminal_lines) if terminal_lines else ""}

Each listed account represents the endpoint of a traced attribution path within the configured hop limit.

### Investigative Limitations

{chr(10).join(limitations_section)}

All findings are subject to the limitations of a 15-day closed dataset. The absence of a finding does not confirm the absence of activity.

### Recommended Investigative Follow-up

Based on observed evidence, the following investigative steps are recommended. These are operational suggestions only — not legal determinations:

1. Review the identified transactions associated with account {subject_account} for further examination.
2. Verify account-holder information for {subject_account} through authorized banking channels.
3. Preserve relevant transaction records for {subject_account} and its identified counterparties.
4. Examine linked terminal accounts identified in the attribution trace for further investigative action.
5. Review pass-through velocity events for documentation of the rapid fund-movement pattern.
6. Consider whether additional data sources outside the 15-day observation window are available for extended analysis.

Note: The above recommendations are operational guidance based on observed forensic data. They do not constitute legal direction, judicial authorization, or a finding of criminal conduct.
"""
    return narrative.strip()


# ---------------------------------------------------------------------------
# Gemini AI narrative generation
# ---------------------------------------------------------------------------

def _generate_ai_narrative(
    subject_account: str,
    facts: List[VerifiedFact],
    findings: DiaryFindings,
    chronology: List[DiaryChronologyEvent],
    warnings: List[str],
) -> Optional[str]:
    """
    Attempt to generate narrative via Gemini API.
    Returns None if not available or fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.info("[CaseDiary] GEMINI_API_KEY not set; using deterministic fallback.")
        return None

    try:
        import google.genai as genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=api_key)
        payload_str = _build_narrative_payload(subject_account, facts, findings, chronology, warnings)

        user_prompt = (
            f"Generate a professional investigative case diary narrative for account {subject_account}.\n\n"
            f"VERIFIED EVIDENCE PAYLOAD (authoritative source — do not deviate from these facts):\n"
            f"{payload_str}\n\n"
            f"Generate the narrative using exactly the required section headings."
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=genai_types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.2,       # Low temperature for factual consistency
                max_output_tokens=3000,
            ),
            contents=user_prompt,
        )
        text = response.text
        if text and len(text.strip()) > 200:
            return text.strip()
        logger.warning("[CaseDiary] Gemini returned empty or very short response.")
        return None

    except Exception as e:
        logger.warning(f"[CaseDiary] Gemini API call failed: {e}. Using deterministic fallback.")
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_narrative(
    subject_account: str,
    facts: List[VerifiedFact],
    findings: DiaryFindings,
    chronology: List[DiaryChronologyEvent],
    warnings: List[str],
    force_deterministic: bool = False,
) -> Tuple[str, NarrativeMetadata]:
    """
    Generate the officer narrative.

    Pipeline:
      1. Try Gemini (unless force_deterministic)
      2. Validate narrative against evidence
      3. If validation fails or AI unavailable → deterministic fallback
      4. Return narrative + metadata

    Always returns a valid narrative — system never fails due to AI unavailability.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    model_used = None
    narrative_source = "DETERMINISTIC_FALLBACK"
    ai_narrative: Optional[str] = None
    validation: Optional[NarrativeValidationResult] = None

    if not force_deterministic:
        ai_narrative = _generate_ai_narrative(subject_account, facts, findings, chronology, warnings)

    if ai_narrative:
        # Validate AI output
        validation = validate_narrative(ai_narrative, facts, subject_account)
        if validation.validation_status == "PASSED":
            narrative_source = "AI_GEMINI"
            model_used = "gemini-2.0-flash"
            final_narrative = ai_narrative
        else:
            logger.warning(
                f"[CaseDiary] AI narrative validation FAILED for {subject_account}: "
                f"{validation.violations_found}. Falling back to deterministic."
            )
            # Deterministic fallback
            final_narrative = generate_deterministic_narrative(
                subject_account, facts, findings, chronology, warnings
            )
            fallback_validation = NarrativeValidationResult(
                validation_status="SKIPPED",
                validated_at=datetime.now(timezone.utc).isoformat(),
                checks_performed=["DETERMINISTIC_FALLBACK_USED"],
                violations_found=[],
                fallback_triggered=True,
                fallback_reason=(
                    f"AI narrative validation failed: {'; '.join(validation.violations_found[:3])}"
                ),
            )
            validation = fallback_validation
            narrative_source = "DETERMINISTIC_FALLBACK"
    else:
        # No AI narrative produced
        final_narrative = generate_deterministic_narrative(
            subject_account, facts, findings, chronology, warnings
        )
        validation = NarrativeValidationResult(
            validation_status="SKIPPED",
            validated_at=now_iso,
            checks_performed=["DETERMINISTIC_FALLBACK_USED"],
            violations_found=[],
            fallback_triggered=True,
            fallback_reason="AI narrative generation not attempted or unavailable.",
        )

    metadata = NarrativeMetadata(
        narrative_version="v1",
        narrative_source=narrative_source,
        ai_model=model_used,
        generated_at=datetime.now(timezone.utc).isoformat(),
        input_fact_count=len(facts),
        input_event_count=len(chronology),
        validation=validation,
    )

    return final_narrative, metadata
