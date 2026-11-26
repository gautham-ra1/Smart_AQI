"""Vectorized Trust-Weighted Inverse Distance Weighting (TW-IDW) Spatial Interpolator."""

from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cdist


def interpolate_tw_idw(
    coords_km: np.ndarray,
    values: np.ndarray,
    weights: np.ndarray,
    grid_pts_km: np.ndarray,
    power: float = 2.0,
    smoothing_km2: float = 0.05,
) -> np.ndarray:
    """Compute vectorized Trust-Weighted IDW over grid points.

    Args:
        coords_km: Shape (N, 2) sensor coordinates in local km.
        values: Shape (N,) humidity-corrected PM2.5 values.
        weights: Shape (N,) dynamic trust weights in [0.05, 1.0].
        grid_pts_km: Shape (M, 2) target grid coordinates in local km.
        power: Distance decay exponent (default 2.0).
        smoothing_km2: Smoothing epsilon (0.05 km^2) to eliminate single-point bullseyes.

    Returns:
        Shape (M,) predicted PM2.5 values.
    """
    if len(values) == 0:
        return np.zeros(len(grid_pts_km), dtype=np.float64)

    coords = np.asarray(coords_km, dtype=np.float64)
    vals = np.asarray(values, dtype=np.float64)
    w = np.maximum(np.asarray(weights, dtype=np.float64), 0.05)

    dists = cdist(grid_pts_km, coords)
    inv_weights = w[None, :] / (np.power(dists, power) + smoothing_km2)
    denom = np.sum(inv_weights, axis=1)
    pred = (inv_weights @ vals) / np.maximum(denom, 1e-12)
    return np.clip(pred, 0.0, 1000.0)
