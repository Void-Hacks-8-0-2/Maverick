"""
Configuration and Policy Definitions for Temporal FIFO Attribution
Operation 'ABHEDYA-CHAKRA' -- Step 5C

Typed, immutable configuration. All defaults and thresholds centralized.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AttributionPolicyConfig:
    """
    Typed configuration for the Temporal FIFO Attribution Engine.
    """
    # Policy Identity
    policy_name: str = "TEMPORAL_FIFO"
    policy_version: str = "v1"

    # Attribution Horizon: Maximum elapsed seconds between source incoming tx and destination outgoing tx.
    # Default: None (unlimited within observation window).
    # Can be configured to e.g. 86400 (24h), 604800 (7d), or 1209600 (14d).
    horizon_seconds: Optional[int] = None

    # Multi-hop Trace Limits
    default_max_hops: int = 4
    max_hops_limit: int = 6
    max_branches_per_hop: int = 50
    max_trace_edges: int = 500

    # Minimum financial amount threshold to track (avoid float precision dust)
    min_attribution_threshold: float = 0.01

    # Provenance tag
    provenance: str = "ATTRIBUTION"
    disclaimer: str = (
        "INVESTIGATIVE ATTRIBUTION ONLY -- Deterministic accounting model based on chronological FIFO rules. "
        "Does not constitute legal proof of beneficial ownership or judicial determination of criminality."
    )


DEFAULT_ATTRIBUTION_CONFIG = AttributionPolicyConfig()
