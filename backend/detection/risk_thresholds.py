"""
Deterministic Forensic Risk Scoring Thresholds and Weights for Operation 'ABHEDYA-CHAKRA'
Step 5B: Explainable 0-100 Mule Risk Index Model.

All weights and thresholds are centralized and immutable.
Total Max = 100 points across 6 independent evidence families.
Non-duplicative, bounded evidence model.

INVESTIGATIVE CANDIDATE INDICATORS ONLY -- NOT A STATEMENT OF CRIMINALITY OR LEGAL DETERMINATION.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class FlowStructureThresholds:
    """Family A: Flow Structure & Volume Scale (Max 20 pts)."""
    max_family_points: float = 20.0
    
    # Volume scale thresholds
    vol_tier1: float = 1000000.0  # >= 1M: 10 pts
    vol_tier2: float = 500000.0   # >= 500k: 7 pts
    vol_tier3: float = 150000.0   # >= 150k: 4 pts
    vol_tier4: float = 50000.0    # >= 50k: 2 pts
    
    # Flow parity / Transit balance thresholds (min_flow / max_flow)
    balanced_transit_ratio_high: float = 0.85  # >= 0.85: 10 pts
    balanced_transit_ratio_mod: float = 0.70   # >= 0.70: 6 pts
    one_sided_sink_inflow: float = 50000.0     # zero out, >= 50k in: 8 pts


@dataclass(frozen=True)
class VelocityRiskThresholds:
    """Family B: 3-15 Minute Pass-Through Velocity (Max 25 pts)."""
    max_family_points: float = 25.0
    
    # Deterministic pass-through ratio bands (requiring >= 2 qualifying outgoing transactions)
    ratio_band_critical: float = 0.95  # >= 0.95: 25 pts
    ratio_band_high: float = 0.85      # >= 0.85: 20 pts
    ratio_band_elevated: float = 0.70  # >= 0.70: 15 pts
    ratio_band_moderate: float = 0.50  # >= 0.50: 8 pts
    
    # Capped points for single outgoing transaction (to avoid single-event skew)
    single_event_high: float = 10.0
    single_event_mod: float = 5.0
    min_qualifying_tx_for_full_bands: int = 2


@dataclass(frozen=True)
class AutomationRiskThresholds:
    """Family C: Automation / Device / IP Infrastructure Behavior (Max 20 pts)."""
    max_family_points: float = 20.0
    
    # Automated execution device counts (Web_Emulator / Linux_Script)
    heavy_automated_tx_count: int = 5     # >= 5 txs or >= 50% ratio: 14 pts
    heavy_automated_ratio: float = 0.50
    detected_automated_tx_count: int = 1  # >= 1 tx: 8 pts
    
    # IP concentration thresholds
    top_ip_ratio_high: float = 0.80       # >= 80%: 6 pts
    top_ip_ratio_mod: float = 0.50        # >= 50%: 3 pts
    min_tx_for_ip_eval: int = 3


@dataclass(frozen=True)
class NetworkRiskThresholds:
    """Family D: Counterparty & Graph Network Structure (Max 15 pts)."""
    max_family_points: float = 15.0
    
    # High-degree connectivity thresholds max(fan_in, fan_out)
    degree_tier1: int = 100  # >= 100: 10 pts
    degree_tier2: int = 50   # >= 50: 7 pts
    degree_tier3: int = 20   # >= 20: 4 pts
    degree_tier4: int = 10   # >= 10: 2 pts
    
    # Asymmetric structure thresholds (fan-in / fan-out imbalance)
    asymmetry_major_min: int = 10
    asymmetry_minor_max: int = 2
    asymmetry_points: float = 5.0
    multi_hop_connectivity_degree: int = 5
    multi_hop_points: float = 3.0


@dataclass(frozen=True)
class TransactionBehaviorThresholds:
    """Family E: Transaction Behavior & Anomaly Profile (Max 10 pts)."""
    max_family_points: float = 10.0
    
    # Temporal anomalies: night activity (00:00 - 05:59)
    night_tx_heavy_count: int = 5
    night_tx_heavy_ratio: float = 0.30
    night_heavy_points: float = 5.0
    night_detected_count: int = 2
    night_detected_points: float = 2.0
    
    # Frequency burst rate (txs per active day)
    burst_rate_high: float = 20.0
    burst_points_high: float = 5.0
    burst_rate_mod: float = 10.0
    burst_points_mod: float = 3.0


@dataclass(frozen=True)
class RoleSupportThresholds:
    """Family F: Step 4 Role Classification Support (Max 10 pts)."""
    max_family_points: float = 10.0
    
    points_per_candidate_role: float = 4.0  # L1: 4, L2: 4, L3: 4 (capped at 10)


@dataclass(frozen=True)
class MuleRiskModelConfig:
    """Consolidated Configuration for Mule Risk Model v1."""
    version: str = "v1"
    provenance: str = "DERIVED"
    
    flow: FlowStructureThresholds = field(default_factory=FlowStructureThresholds)
    velocity: VelocityRiskThresholds = field(default_factory=VelocityRiskThresholds)
    automation: AutomationRiskThresholds = field(default_factory=AutomationRiskThresholds)
    network: NetworkRiskThresholds = field(default_factory=NetworkRiskThresholds)
    transaction: TransactionBehaviorThresholds = field(default_factory=TransactionBehaviorThresholds)
    role_support: RoleSupportThresholds = field(default_factory=RoleSupportThresholds)
    
    # Risk Bands
    band_low_max: float = 24.99
    band_mod_max: float = 49.99
    band_high_max: float = 74.99
    
    def get_band(self, score: float) -> str:
        if score <= self.band_low_max:
            return "LOW"
        elif score <= self.band_mod_max:
            return "MODERATE"
        elif score <= self.band_high_max:
            return "HIGH"
        else:
            return "VERY_HIGH"


DEFAULT_RISK_CONFIG = MuleRiskModelConfig()
