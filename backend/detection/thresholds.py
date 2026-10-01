"""
Configurable Forensic Detection Thresholds for Operation 'ABHEDYA-CHAKRA'
Step 4: Deterministic Layer 1 / Layer 2 / Layer 3 Mule Role Candidate Generation.
Step 5A: 3–15 Minute Pass-Through Velocity Detection.

NOTE ON CALIBRATION:
Initial deterministic heuristic thresholds for investigative candidate generation;
not ground-truth-calibrated. There is currently no ground-truth mule label in the supplied dataset.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Layer1Thresholds:
    """
    Thresholds for Layer 1 — Collector Mule Candidate.
    Represents an account exhibiting collector-like inbound aggregation behavior.
    Initial deterministic heuristic thresholds for investigative candidate generation; not ground-truth-calibrated.
    """
    min_fan_in: int = 95
    min_incoming_txn_count: int = 95
    min_incoming_volume: float = 150000.0
    min_inflow_to_outflow_ratio: float = 1.0
    require_inbound_flow_dominance: bool = True
    min_signals_required: int = 3


@dataclass(frozen=True)
class Layer2Thresholds:
    """
    Thresholds for Layer 2 — Distributor Mule Candidate.
    Represents an account exhibiting outbound distribution behavior.
    Initial deterministic heuristic thresholds for investigative candidate generation; not ground-truth-calibrated.
    """
    min_fan_out: int = 95
    min_outgoing_txn_count: int = 95
    min_outgoing_volume: float = 150000.0
    min_outflow_to_inflow_ratio: float = 1.0
    require_outbound_flow_dominance: bool = True
    min_signals_required: int = 3


@dataclass(frozen=True)
class Layer3Thresholds:
    """
    Thresholds for Layer 3 — Terminal/Cash-Out Node Candidate.
    Represents an account exhibiting terminal absorption / sink behavior or automated exit cash-out.
    Initial deterministic heuristic thresholds for investigative candidate generation; not ground-truth-calibrated.
    """
    # Pattern A: Terminal Accumulation Sink (Inflow absorbed, 0 or near-zero outbound)
    min_terminal_sink_incoming_volume: float = 50000.0
    min_terminal_sink_incoming_tx: int = 2
    max_terminal_sink_outgoing_tx: int = 0
    
    # Pattern B: Automated Outflow Drain (Web_Emulator / Linux_Script + high outbound volume + flow dominance)
    min_automated_outgoing_volume: float = 100000.0
    min_automated_outgoing_tx: int = 2
    
    # Pattern C: Concentrated IP Sink Node (High single-IP concentration + inbound accumulation + 0 outbound)
    min_top_ip_ratio: float = 0.20
    min_ip_sink_incoming_volume: float = 50000.0
    max_ip_sink_outgoing_tx: int = 0


@dataclass(frozen=True)
class VelocityThresholds:
    """
    Thresholds for Step 5A — 3–15 Minute Pass-Through Velocity Detection.

    Window semantics (INCLUSIVE on both boundaries):
        QUALIFYING:     3 min 0 sec  <=  delay  <=  15 min 0 sec
        BEFORE_WINDOW:  delay  <  3 min 0 sec
        AFTER_WINDOW:   delay  >  15 min 0 sec

    Boundary behavior (exact):
        exactly 3:00 minutes  → INCLUDED in qualifying window
        exactly 15:00 minutes → INCLUDED in qualifying window
        2:59 minutes          → NOT included (BEFORE_WINDOW)
        15:01 minutes         → NOT included (AFTER_WINDOW)

    NOTE ON CALIBRATION:
    Not ground-truth-calibrated. The 90% threshold follows the official problem statement.
    """  # noqa: D205
    # Time window boundaries (seconds, INCLUSIVE)
    min_delay_seconds: int = 180    # 3 minutes exactly (inclusive lower bound)
    max_delay_seconds: int = 900    # 15 minutes exactly (inclusive upper bound)

    # Pass-through ratio threshold: qualifying_attributed_volume / total_incoming_volume >= this
    min_pass_through_ratio: float = 0.90

    # Minimum number of qualifying outgoing transactions required
    # "across multiple outgoing transfers" requirement from the problem statement
    min_pass_through_outgoing_tx: int = 2

    # Provenance
    velocity_version: str = "v1"
    provenance: str = "DERIVED"


@dataclass(frozen=True)
class RoleClassificationThresholds:
    """
    Unified configuration bundle for all role classification layers and velocity detection.
    Allows dynamic overriding and hyperparameter sensitivity evaluation without modifying code.
    """
    layer1: Layer1Thresholds = field(default_factory=Layer1Thresholds)
    layer2: Layer2Thresholds = field(default_factory=Layer2Thresholds)
    layer3: Layer3Thresholds = field(default_factory=Layer3Thresholds)
    velocity: VelocityThresholds = field(default_factory=VelocityThresholds)
    classification_version: str = "v1"
    provenance: str = "CANDIDATE_CLASSIFICATION"


DEFAULT_THRESHOLDS = RoleClassificationThresholds()
DEFAULT_VELOCITY_THRESHOLDS = VelocityThresholds()
