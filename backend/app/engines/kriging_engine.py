"""Trust-Aware Ordinary Kriging with Heteroscedastic Measurement Variance.

Adds per-sensor measurement error variance to the diagonal of the Kriging
covariance matrix: low for official CAAQMS (sigma^2 = 4.0) and inversely scaled
by squared trust weight (25.0 / max(w, 0.05)^2) for citizen/mobile nodes.

Automatically falls back to Trust-Weighted IDW whenever active sensors < 5
or when the Kriging linear system is numerically ill-conditioned.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from scipy.linalg import LinAlgError, solve
from scipy.spatial.distance import cdist

from app.engines.idw_engine import interpolate_tw_idw


@dataclass
class InterpolationResult:
    mode_used: str
    requested_mode: str
    pred_pm25: np.ndarray
    std_dev: np.ndarray | None
    compute_ms: float


def interpolate_aqi_grid(
    coords_km: np.ndarray,
    values: np.ndarray,
    weights: np.ndarray,
    is_official: np.ndarray,
    grid_pts_km: np.ndarray,
    mode: str = "kriging",
    sill: float = 400.0,
    vrange_km: float = 5.0,
) -> InterpolationResult:
    """Interpolate a 2D AQI grid using Trust-Aware Ordinary Kriging or TW-IDW."""
    t0 = time.perf_counter()
    requested = mode.lower() if mode.lower() in {"idw", "kriging"} else "kriging"

    coords = np.asarray(coords_km, dtype=np.float64)
    vals = np.asarray(values, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    official_mask = np.asarray(is_official, dtype=bool)

    # Automatic fallback to TW-IDW when mode is idw or active sensors < 5
    if requested == "idw" or len(vals) < 5:
        pred = interpolate_tw_idw(coords, vals, w, grid_pts_km)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return InterpolationResult(
            mode_used="idw",
            requested_mode=requested,
            pred_pm25=pred,
            std_dev=None,
            compute_ms=round(elapsed_ms, 2),
        )

    try:
        n = len(vals)
        c_ss = sill * np.exp(-cdist(coords, coords) / vrange_km)
        meas_var = np.where(
            official_mask,
            4.0,
            25.0 / (np.maximum(w, 0.05) ** 2),
        )
        c_ss[np.diag_indices(n)] += meas_var

        k_mat = np.ones((n + 1, n + 1), dtype=np.float64)
        k_mat[:n, :n] = c_ss
        k_mat[n, n] = 0.0

        c_gs = sill * np.exp(-cdist(grid_pts_km, coords) / vrange_km)
        rhs = np.vstack([c_gs.T, np.ones((1, len(grid_pts_km)), dtype=np.float64)])

        sol = solve(k_mat, rhs, assume_a="sym")
        pred = np.clip(sol[:n, :].T @ vals, 0.0, 1000.0)
        var = sill - np.sum(sol[:n, :] * c_gs.T, axis=0) - sol[n, :]
        std_dev = np.sqrt(np.maximum(0.0, var))

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return InterpolationResult(
            mode_used="kriging",
            requested_mode=requested,
            pred_pm25=pred,
            std_dev=std_dev,
            compute_ms=round(elapsed_ms, 2),
        )
    except (LinAlgError, ValueError):
        # Pure nugget / singular matrix fallback -> TW-IDW
        pred = interpolate_tw_idw(coords, vals, w, grid_pts_km)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return InterpolationResult(
            mode_used="idw",
            requested_mode=requested,
            pred_pm25=pred,
            std_dev=None,
            compute_ms=round(elapsed_ms, 2),
        )
