"""Unit tests for Hygrometric Pre-Calibration & Two-Tier Adaptive Trust Engine."""

from app.engines.humidity_correction import correct_pm25_humidity
from app.engines.trust_engine import update_sensor_trust


def test_monsoon_fog_90pct_rh_preserves_trust():
    """Chikkamagaluru 90% RH monsoon fog: raw 45 ug/m3 vs 25 ug/m3 ref -> corrected ~30.72, trust ~0.81."""
    corrected = correct_pm25_humidity(raw_pm25=45.0, rh_pct=90.0)
    assert 29.0 <= corrected <= 32.0

    # Simulate 10 steady ticks in 90% RH fog near Kalyana Nagara (1.5 km)
    trust = 0.75
    for _ in range(10):
        res = update_sensor_trust(
            prev_trust=trust,
            raw_pm25=45.0,
            rh_pct=90.0,
            ref_pm25=25.0,
            dist_ref_km=1.5,
        )
        trust = res.new_trust
        assert res.tier_used == "reference_anchored"

    assert trust >= 0.80, f"Healthy monsoon sensor was wrongly penalized: {trust}"
    assert res.status == "active"


def test_persistent_faulty_sensor_decays_to_floor_in_10_ticks():
    """Persistent +150 ug/m3 bias decays smoothly from 0.75 to 0.05 floor within 10 ticks."""
    trust = 0.75
    for _ in range(10):
        res = update_sensor_trust(
            prev_trust=trust,
            raw_pm25=180.0,
            rh_pct=55.0,
            ref_pm25=30.0,
            dist_ref_km=2.0,
        )
        trust = res.new_trust

    assert trust <= 0.06, f"Expected decay near 0.05 floor, got {trust}"
    assert res.status == "quarantined"


def test_transient_spike_barely_lowers_trust():
    """Single brief plume (idling bus) should not quarantine a healthy sensor."""
    res = update_sensor_trust(
        prev_trust=0.80,
        raw_pm25=140.0,
        rh_pct=55.0,
        ref_pm25=30.0,
        dist_ref_km=3.0,
    )
    assert res.new_trust >= 0.58
    assert res.status == "active"


def test_tier2_peer_mad_fallback_outer_chikkamagaluru():
    """Beyond 5 km from Kalyana Nagara CAAQMS, Tier 2 Peer-MAD evaluates outliers."""
    # Healthy peer matches cluster [28, 30, 32, 29]
    healthy = update_sensor_trust(
        prev_trust=0.70,
        raw_pm25=31.0,
        rh_pct=60.0,
        ref_pm25=30.0,
        dist_ref_km=8.5,
        peer_vals=[28.0, 30.0, 32.0, 29.0],
    )
    assert healthy.tier_used == "peer_mad"
    assert healthy.new_trust > 0.70

    # Outlier deviates sharply from peer cluster
    trust = 0.75
    for _ in range(10):
        outlier = update_sensor_trust(
            prev_trust=trust,
            raw_pm25=220.0,
            rh_pct=60.0,
            ref_pm25=30.0,
            dist_ref_km=8.5,
            peer_vals=[28.0, 30.0, 32.0, 29.0],
        )
        trust = outlier.new_trust
    assert outlier.tier_used == "peer_mad"
    assert trust <= 0.06


def test_official_station_always_fixed_1_0():
    res = update_sensor_trust(
        prev_trust=1.0,
        raw_pm25=95.0,
        rh_pct=85.0,
        sensor_type="official",
    )
    assert res.new_trust == 1.0
    assert res.tier_used == "official"
    assert res.pm25_corrected == 95.0


def test_adaptive_fleet_rate_limiter_scaling():
    """Verify per-device rate limit scales from 12/min (sparse fleet) down to 1/min (dense fleet)."""
    from app.core.rate_limiter import RateLimiter

    assert RateLimiter.compute_dynamic_limit(active_devices=10, global_budget=180) == 12
    assert RateLimiter.compute_dynamic_limit(active_devices=30, global_budget=180) == 6
    assert RateLimiter.compute_dynamic_limit(active_devices=60, global_budget=180) == 3
    assert RateLimiter.compute_dynamic_limit(active_devices=250, global_budget=180) == 1
