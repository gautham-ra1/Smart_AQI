"""India CPCB National Air Quality Index (NAQI) PM2.5 Sub-Index Engine.

Strictly uses India's CPCB 2014 NAQI PM2.5 breakpoints (NOT US EPA).
"""

from __future__ import annotations

from dataclasses import dataclass

# (c_lo, c_hi, i_lo, i_hi, band_name, hex_color)
CPCB_PM25_BREAKPOINTS: list[tuple[float, float, int, int, str, str]] = [
    (0.0, 30.0, 0, 50, "Good", "#00B050"),
    (30.0, 60.0, 51, 100, "Satisfactory", "#92D050"),
    (60.0, 90.0, 101, 200, "Moderate", "#FFFF00"),
    (90.0, 120.0, 201, 300, "Poor", "#FF9900"),
    (120.0, 250.0, 301, 400, "Very Poor", "#FF0000"),
    (250.0, 500.0, 401, 500, "Severe", "#C00000"),
]

MAP_LAYER_LABEL = "Hyperlocal PM2.5-Equivalent AQI (Real-Time Sub-Index)"


@dataclass(frozen=True)
class CPCBSubIndex:
    pm25: float
    aqi: int
    band: str
    color: str
    exceeds_who_24h: bool
    exceeds_india_naaqs: bool


def pm25_to_cpcb_subindex(pm25: float) -> CPCBSubIndex:
    """Convert PM2.5 concentration (ug/m3) to India CPCB NAQI sub-index."""
    c = max(0.0, float(pm25))
    for c_lo, c_hi, i_lo, i_hi, band, color in CPCB_PM25_BREAKPOINTS:
        if c <= c_hi:
            aqi = round(i_lo + ((c - c_lo) / (c_hi - c_lo)) * (i_hi - i_lo))
            return CPCBSubIndex(
                pm25=round(c, 2),
                aqi=aqi,
                band=band,
                color=color,
                exceeds_who_24h=c > 15.0,
                exceeds_india_naaqs=c > 60.0,
            )
    return CPCBSubIndex(
        pm25=round(c, 2),
        aqi=500,
        band="Severe",
        color="#C00000",
        exceeds_who_24h=True,
        exceeds_india_naaqs=True,
    )


def get_cpcb_band_metadata() -> list[dict]:
    """Return CPCB NAQI band metadata for legends and API consumers."""
    return [
        {
            "pm25_min": c_lo,
            "pm25_max": c_hi,
            "aqi_min": i_lo,
            "aqi_max": i_hi,
            "band": band,
            "color": color,
        }
        for c_lo, c_hi, i_lo, i_hi, band, color in CPCB_PM25_BREAKPOINTS
    ]
