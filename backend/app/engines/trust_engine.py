"""Two-Tier Adaptive Trust Engine with Persistent EWMA Decay.

- Official CAAQMS stations hold fixed anchor weight = 1.0.
- Citizen / institutional / mobile nodes maintain persistent trust in [0.05, 0.90].
- Tier 1 (Reference-Anchored, <= 5 km from nearest CAAQMS): distance-relaxed Gaussian agreement.
- Tier 2 (Peer-Consensus MAD Fallback, > 5 km): robust Median Absolute Deviation z-score if >= 3 peers within 4 km.
- Isolated Fallback (< 3 peers and > 5 km): conservative 0.50 prior (+ optional CAMS background check).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from app.engines.humidity_correction import correct_pm25_humidity

OFFICIAL_TRUST_WEIGHT = 1.0
MIN_TRUST_WEIGHT = 0.05
MAX_TRUST_WEIGHT = 0.90
DEFAULT_ALPHA = 0.25
TIER1_RADIUS_KM = 5.0
TIER2_MIN_PEERS = 3


@dataclass(frozen=True)
class TrustEvaluation:
    pm25_corrected: float
    prev_trust: float
    new_trust: float
    agreement_score: float
    tier_used: str
    status: str


def derive_sensor_status(trust_weight: float, sensor_type: str) -> str:
    """Map trust weight to operational sensor lifecycle state."""
    if sensor_type == "official":
        return "active"
    if trust_weight < 0.20:
        return "quarantined"
    if trust_weight < 0.45:
        return "degraded"
    return "active"


def update_sensor_trust(
    prev_trust: float,
    raw_pm25: float,
    rh_pct: float,
    ref_pm25: float | None = None,
    dist_ref_km: float | None = None,
    peer_vals: list[float] | None = None,
    cams_prior_pm25: float | None = None,
    sensor_type: str = "citizen_fixed",
    alpha: float = DEFAULT_ALPHA,
    sigma_0: float = 20.0,
    beta: float = 4.0,
) -> TrustEvaluation:
    """Evaluate a single reading and return the updated persistent EWMA trust state."""
    if sensor_type == "official":
        return TrustEvaluation(
            pm25_corrected=round(max(0.0, raw_pm25), 2),
            prev_trust=OFFICIAL_TRUST_WEIGHT,
            new_trust=OFFICIAL_TRUST_WEIGHT,
            agreement_score=1.0,
            tier_used="official",
            status="active",
        )

    # 1. Hygrometric pre-correction (optical sensors in monsoon/hill fog)
    corrected = correct_pm25_humidity(raw_pm25, rh_pct)
    peers = peer_vals or []

    # 2. Tier 1: Reference-Anchored Mode (<= 5 km from nearest official CAAQMS)
    if (
        ref_pm25 is not None
        and dist_ref_km is not None
        and dist_ref_km <= TIER1_RADIUS_KM
    ):
        tol = sigma_0 + beta * dist_ref_km
        agreement = math.exp(-0.5 * (abs(corrected - ref_pm25) / tol) ** 2)
        tier_used = "reference_anchored"

    # 3. Tier 2: Peer-Consensus MAD Fallback (outer Chikkamagaluru taluks, > 5 km)
    elif len(peers) >= TIER2_MIN_PEERS:
        arr = np.asarray(peers, dtype=np.float64)
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med))) + 5.0
        z_rob = abs(corrected - med) / (1.4826 * mad)
        agreement = math.exp(-0.5 * (max(0.0, z_rob - 1.5) ** 2))
        tier_used = "peer_mad"

    # 4. Isolated node fallback (conservative 0.50 prior, soft-checked against CAMS prior if available)
    else:
        if cams_prior_pm25 is not None:
            # Plausibility band: wide tolerance (45 ug/m3) around coarse CAMS prior
            cams_agree = math.exp(-0.5 * (abs(corrected - cams_prior_pm25) / 45.0) ** 2)
            agreement = min(0.55, 0.25 + 0.30 * cams_agree)
        else:
            agreement = 0.50
        tier_used = "isolated_prior"

    # 5. Persistent EWMA update bounded in [0.05, 0.90]
    blended = (1.0 - alpha) * prev_trust + alpha * agreement
    new_trust = round(max(MIN_TRUST_WEIGHT, min(MAX_TRUST_WEIGHT, blended)), 4)
    status = derive_sensor_status(new_trust, sensor_type)

    return TrustEvaluation(
        pm25_corrected=corrected,
        prev_trust=round(prev_trust, 4),
        new_trust=new_trust,
        agreement_score=round(agreement, 4),
        tier_used=tier_used,
        status=status,
    )
