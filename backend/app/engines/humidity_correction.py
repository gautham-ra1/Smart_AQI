"""Physics-informed hygrometric pre-calibration for optical PM2.5 sensors (PMS5003/7003/SPS30).

Addresses Western Ghats / Chikkamagaluru monsoon moisture scattering (RH > 75%),
preventing healthy low-cost optical sensors from being falsely penalized against
heated-inlet regulatory CAAQMS stations.
"""

from __future__ import annotations


def correct_pm25_humidity(
    raw_pm25: float,
    rh_pct: float,
    model: str = "nonlinear_deliquescence",
    gamma: float = 0.008,
    rh_threshold: float = 75.0,
) -> float:
    """Apply hygrometric pre-correction to raw optical PM2.5 readings.

    Args:
        raw_pm25: Raw PM2.5 reading in ug/m3.
        rh_pct: Ambient relative humidity percentage [0, 100].
        model: 'nonlinear_deliquescence' (default for Western Ghats / South Asia)
               or 'epa_barkjohn' (Barkjohn et al., 2021 linear-RH formula).
        gamma: Nonlinear deliquescence damping coefficient (default 0.008).
        rh_threshold: Humidity threshold above which moisture swelling dominates (75%).

    Returns:
        Humidity-corrected PM2.5 concentration in ug/m3 (non-negative).
    """
    raw = max(0.0, float(raw_pm25))
    rh = max(0.0, min(100.0, float(rh_pct)))

    if model == "epa_barkjohn":
        # Barkjohn et al. (2021) US EPA PurpleAir linear-RH equation
        corrected = 0.524 * raw - 0.0862 * rh + 5.75
        return round(max(0.0, corrected), 2)

    # Default: nonlinear deliquescence damping above 75% RH
    if rh > rh_threshold:
        damping = 1.0 + gamma * ((rh - rh_threshold) ** 1.5)
        corrected = raw / damping
    else:
        corrected = raw

    return round(max(0.0, corrected), 2)
