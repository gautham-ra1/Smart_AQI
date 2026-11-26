"""Unit tests for India CPCB NAQI PM2.5 Sub-Index & MoHFW Health Advisory Engine."""

from app.engines.advisory_engine import get_health_advisory
from app.engines.aqi_engine import pm25_to_cpcb_subindex


def test_cpcb_pm25_breakpoints():
    assert pm25_to_cpcb_subindex(15.0).band == "Good"
    assert pm25_to_cpcb_subindex(30.0).aqi == 50
    assert pm25_to_cpcb_subindex(60.0).band == "Satisfactory"
    assert pm25_to_cpcb_subindex(60.0).aqi == 100
    assert pm25_to_cpcb_subindex(75.0).band == "Moderate"
    assert pm25_to_cpcb_subindex(105.0).band == "Poor"
    assert pm25_to_cpcb_subindex(180.0).band == "Very Poor"
    assert pm25_to_cpcb_subindex(300.0).band == "Severe"


def test_vulnerable_cohorts_trigger_earlier_than_general():
    """At Moderate PM2.5 (75 ug/m3), asthma cohort gets Limit Outdoor while general is Monitor."""
    asthma = get_health_advisory(75.0, "asthma")
    general = get_health_advisory(75.0, "general")
    worker = get_health_advisory(75.0, "outdoor_worker")

    assert asthma["cpcb_band"] == "Moderate"
    assert asthma["action_tier"] == "Limit Outdoor"
    assert general["action_tier"] == "Monitor"
    assert "hydrate" in worker["advisory"].lower()
    assert "consult a doctor" in asthma["disclaimer"].lower()


def test_n95_guidance_above_aqi_200():
    poor = get_health_advisory(105.0, "asthma")
    assert poor["cpcb_band"] == "Poor"
    assert "N95" in poor["advisory"]
    assert "cloth masks" in poor["advisory"].lower()
