"""
Risk Models for Operation 'ABHEDYA-CHAKRA'
Step 5B: Explainable 0-100 Mule Risk Index Schema Contracts.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RiskReason(BaseModel):
    """Structured explainable evidence reason for risk points."""
    code: str = Field(..., description="Stable uppercase machine-readable reason code")
    family: str = Field(..., description="Evidence family: FLOW_STRUCTURE, VELOCITY, AUTOMATION, NETWORK_STRUCTURE, TRANSACTION_BEHAVIOR, ROLE_SUPPORT")
    points: float = Field(..., description="Risk score points contributed by this evidence item")
    observed_value: Any = Field(..., description="Actual observed metric value from dataset")
    threshold: Optional[Any] = Field(None, description="Configured heuristic threshold reference")
    description: str = Field(..., description="Factual explanatory description of observed evidence")


class MuleRiskScore(BaseModel):
    """
    Forensic Explainable 0-100 Mule Risk Index contract.
    Bounded multi-family evidence aggregation.
    INVESTIGATIVE CANDIDATE INDICATORS ONLY -- NOT A STATEMENT OF CRIMINALITY OR LEGAL DETERMINATION.
    """
    account_number: str = Field(..., description="Unique account entity identifier")
    risk_index: float = Field(..., description="Deterministic bounded 0-100 Mule Risk Index")
    risk_band: str = Field(..., description="Risk tier: LOW (0-24), MODERATE (25-49), HIGH (50-74), VERY_HIGH (75-100)")
    risk_model_version: str = Field("v1", description="Scoring model version")
    risk_provenance: str = Field("DERIVED", description="Provenance marker: DERIVED")
    risk_computed_at: Optional[datetime] = Field(None, description="Timestamp when risk score was calculated")
    risk_family_scores: Dict[str, float] = Field(default_factory=dict, description="Point contribution breakdown per evidence family")
    risk_reasons: List[RiskReason] = Field(default_factory=list, description="Ordered list of factual evidence reason items")
    risk_disclaimer: str = Field(
        "INVESTIGATIVE CANDIDATE INDICATORS ONLY -- Analytical risk prioritization score derived deterministically from transaction features. Not a declaration of criminality, guilt, or legal determination.",
        description="Mandatory forensic disclaimer"
    )
