"""Unit tests for Trust-Weighted IDW and Trust-Aware Ordinary Kriging."""

import numpy as np

from app.engines.kriging_engine import interpolate_aqi_grid
from app.utils.geo_utils import build_city_grid, latlon_to_local_km


def test_kriging_and_idw_50x50_grid_performance_and_outlier_suppression():
    """Verify 50x50 Chikkamagaluru grid runs fast and suppresses untrusted +250 outlier."""
    grid_km, _, cfg = build_city_grid("chikkamagaluru", grid_size=50)

    # 1 official Kalyana Nagara + 7 healthy nodes (~30 ug/m3) + 1 quarantined outlier (280 ug/m3, weight=0.05)
    lats = np.array([13.3161, 13.3250, 13.3090, 13.3320, 13.2980, 13.3180, 13.3120, 13.3400, 13.3170])
    lons = np.array([75.7720, 75.7790, 75.7640, 75.7580, 75.7810, 75.7860, 75.7700, 75.7750, 75.7730])
    vals = np.array([30.0, 32.0, 28.0, 29.0, 31.0, 33.0, 27.0, 30.0, 280.0])
    weights = np.array([1.0, 0.85, 0.82, 0.80, 0.78, 0.84, 0.80, 0.76, 0.05])
    is_official = np.array([True, False, False, False, False, False, False, False, False])

    coords_km = latlon_to_local_km(lats, lons, cfg["center_lat"], cfg["center_lon"])

    idw_res = interpolate_aqi_grid(coords_km, vals, weights, is_official, grid_km, mode="idw")
    krig_res = interpolate_aqi_grid(coords_km, vals, weights, is_official, grid_km, mode="kriging")

    assert idw_res.mode_used == "idw"
    assert idw_res.pred_pm25.shape == (2500,)
    assert idw_res.std_dev is None
    assert idw_res.compute_ms < 50.0

    assert krig_res.mode_used == "kriging"
    assert krig_res.pred_pm25.shape == (2500,)
    assert krig_res.std_dev is not None
    assert krig_res.std_dev.shape == (2500,)
    assert krig_res.compute_ms < 100.0

    # Mean predicted field should stay close to true ~30 ug/m3 despite 280 ug/m3 outlier
    assert float(np.mean(krig_res.pred_pm25)) < 45.0
    assert float(np.mean(idw_res.pred_pm25)) < 45.0


def test_kriging_auto_fallback_below_5_sensors():
    """Kriging must automatically fall back to TW-IDW when fewer than 5 sensors are active."""
    grid_km, _, cfg = build_city_grid("chikkamagaluru", grid_size=20)
    coords_km = latlon_to_local_km(
        np.array([13.3161, 13.3250, 13.3090]),
        np.array([75.7720, 75.7790, 75.7640]),
        cfg["center_lat"],
        cfg["center_lon"],
    )
    res = interpolate_aqi_grid(
        coords_km,
        np.array([30.0, 35.0, 28.0]),
        np.array([1.0, 0.8, 0.75]),
        np.array([True, False, False]),
        grid_km,
        mode="kriging",
    )
    assert res.requested_mode == "kriging"
    assert res.mode_used == "idw"
    assert res.std_dev is None
