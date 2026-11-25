"""Personalised Health Advisory Engine grounded in CPCB NAQI & MoHFW/NCDC NPCCHH (2022 / Oct 2025)."""

from __future__ import annotations

from app.engines.aqi_engine import MAP_LAYER_LABEL, pm25_to_cpcb_subindex

VALID_PROFILES = {"general", "asthma", "children", "elderly", "pregnant", "outdoor_worker"}
SENSITIVE_PROFILES = {"asthma", "children", "elderly", "pregnant"}

MEDICAL_DISCLAIMER = (
    "Informational advisory grounded in CPCB NAQI and MoHFW/NCDC NPCCHH guidelines. "
    "If you experience breathlessness, wheezing, or chest discomfort, consult a doctor immediately."
)


def get_health_advisory(pm25: float, profile: str = "general") -> dict:
    """Generate cohort-specific India health advisory from PM2.5 concentration."""
    normalized_profile = profile.lower() if profile.lower() in VALID_PROFILES else "general"
    sub = pm25_to_cpcb_subindex(pm25)
    sensitive = normalized_profile in SENSITIVE_PROFILES
    outdoor = normalized_profile == "outdoor_worker"

    checklist: list[str] = []
    if sub.aqi <= 50:
        tier = "Normal"
        action = "Safe for normal outdoor activity."
        checklist = [
            "Normal outdoor exercise and commuting are safe.",
            "Note: WHO 2021 24-hour guideline is 15 ug/m3." if sub.exceeds_who_24h else "Meets both India NAAQS and WHO 2021 24-hour targets.",
        ]
    elif sub.aqi <= 100:
        if sensitive:
            tier = "Caution"
            action = "Keep rescue inhaler/medications handy; watch for mild respiratory irritation."
            checklist = [
                "Keep prescribed inhalers or cardiac medicines accessible.",
                "Prefer low-traffic streets over major arterial roads.",
            ]
        else:
            tier = "Normal"
            action = "Acceptable air quality for general public and outdoor workers."
            checklist = ["Normal activity is acceptable; stay hydrated."]
    elif sub.aqi <= 200:
        if sensitive:
            tier = "Limit Outdoor"
            action = "Limit strenuous outdoor exertion; avoid major traffic corridors and dust zones."
            checklist = [
                "Move workouts indoors or choose lighter activity.",
                "Use vehicle and room AC in 're-circulate' mode to block outside air.",
                "Practice wet mopping indoors instead of dry sweeping.",
                "Keep prescribed inhalers and respiratory medicines on hand.",
            ]
        elif outdoor:
            tier = "Caution"
            action = "Outdoor workers: hydrate frequently, take shaded breaks, and avoid idling traffic zones."
            checklist = [
                "Avoid standing directly downwind of diesel exhaust or road dust.",
                "Rotate high-exertion tasks during peak traffic hours.",
            ]
        else:
            tier = "Monitor"
            action = "Normal activity okay; monitor local street-level spikes."
            checklist = ["Use vehicle AC recirculation in heavy traffic."]
    elif sub.aqi <= 300:
        if sensitive:
            tier = "Stay Indoors + N95"
            action = (
                "Move indoors; wear a close-fitting N95/N99 respirator if stepping out "
                "(cloth masks, scarves, and paper masks do not filter PM2.5)."
            )
            checklist = [
                "Avoid early-morning and late-evening walks.",
                "Wear a close-fitting N95 or N99 mask outdoors; avoid cloth/paper masks.",
                "Run AC in recirculation mode and avoid ozone-generating air purifiers.",
                "Wet mop floors instead of dry sweeping.",
            ]
        elif outdoor:
            tier = "Fitted N95 + Rotate Shifts"
            action = "Wear a close-fitting N95/N99 respirator and rotate outdoor shifts frequently."
            checklist = [
                "Use certified N95/N99 masks (cloth/handkerchiefs are ineffective).",
                "Shorten continuous roadside exposure shifts and hydrate.",
            ]
        else:
            tier = "Reduce Prolonged Exertion"
            action = "Reduce prolonged outdoor exertion; wear a fitted N95 mask along polluted corridors."
            checklist = [
                "Avoid early-morning and late-evening outdoor jogging.",
                "Use vehicle AC in recirculation mode.",
            ]
    elif sub.aqi <= 400:
        if sensitive:
            tier = "Strictly Indoors"
            action = "Stay strictly indoors with windows closed; use N95/N99 only for essential travel."
            checklist = [
                "Keep windows and doors closed during peak pollution hours.",
                "Avoid ozone-generating purifiers; use HEPA filtration if available.",
                "Seek medical advice early if symptoms worsen.",
            ]
        elif outdoor:
            tier = "Mandatory N95 / Shorten Shifts"
            action = "Mandatory fitted N95/N99 respirator; shorten outdoor shifts and reschedule non-essential work."
            checklist = [
                "Enforce fitted N95/N99 usage for traffic, construction, and street workers.",
                "Take frequent indoor recovery breaks.",
            ]
        else:
            tier = "Avoid Workouts + N95"
            action = "Avoid outdoor workouts; wear a close-fitting N95/N99 mask when outdoors."
            checklist = [
                "Switch AC to recirculation mode.",
                "Practice wet mopping indoors instead of dry sweeping.",
            ]
    else:
        tier = "Medical Alert / Stay Indoors"
        action = (
            "Severe air quality: stay indoors, close windows, switch AC to recirculate, "
            "halt non-essential outdoor work, and consult a doctor for breathlessness or chest discomfort."
        )
        checklist = [
            "Halt all non-essential outdoor activity and construction/road work.",
            "Wear a close-fitting N95/N99 respirator if stepping outside is unavoidable.",
            "Consult a physician immediately for chest tightness, wheezing, or dizziness.",
        ]

    return {
        "pm25_equiv": sub.pm25,
        "aqi_pm25_equiv": sub.aqi,
        "cpcb_band": sub.band,
        "band_color": sub.color,
        "layer_label": MAP_LAYER_LABEL,
        "profile": normalized_profile,
        "action_tier": tier,
        "advisory": action,
        "checklist": checklist,
        "exceeds_who_24h": sub.exceeds_who_24h,
        "exceeds_india_naaqs": sub.exceeds_india_naaqs,
        "disclaimer": MEDICAL_DISCLAIMER,
    }
