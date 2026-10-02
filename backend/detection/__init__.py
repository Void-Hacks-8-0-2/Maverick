"""
Detection & Forensic Role Classification Engine for Operation 'ABHEDYA-CHAKRA'
Step 4: Deterministic Layer 1 / Layer 2 / Layer 3 Mule Role Candidate Generation.
Step 5A: 3-15 Minute Pass-Through Velocity Detection.
"""

from backend.detection.thresholds import (
    RoleClassificationThresholds,
    Layer1Thresholds,
    Layer2Thresholds,
    Layer3Thresholds,
    VelocityThresholds,
    DEFAULT_THRESHOLDS,
    DEFAULT_VELOCITY_THRESHOLDS,
)
from backend.detection.role_classifier import classify_account_roles, get_account_role, AccountRoleResult
from backend.detection.velocity_detector import compute_velocity_features, get_velocity_events

__all__ = [
    "RoleClassificationThresholds",
    "Layer1Thresholds",
    "Layer2Thresholds",
    "Layer3Thresholds",
    "VelocityThresholds",
    "DEFAULT_THRESHOLDS",
    "DEFAULT_VELOCITY_THRESHOLDS",
    "classify_account_roles",
    "get_account_role",
    "AccountRoleResult",
    "compute_velocity_features",
    "get_velocity_events",
]
