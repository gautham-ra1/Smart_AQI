"""Geospatial utilities for the Chikkamagaluru – Balehonnur – Sringeri Western Ghats corridor."""

from __future__ import annotations

import math
from typing import TypedDict

import numpy as np


class CityBounds(TypedDict):
    name: str
    center_lat: float
    center_lon: float
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    zoom: int


# Full Chikkamagaluru District Corridor: Chikkamagaluru Town -> Aldur -> Balehonnur -> Koppa -> Sringeri
CITY_CONFIGS: dict[str, CityBounds] = {
    "chikkamagaluru": {
        "name": "Chikkamagaluru – Sringeri Corridor",
        "center_lat": 13.3600,
        "center_lon": 75.5300,
        "min_lat": 13.1800,
        "max_lat": 13.5600,
        "min_lon": 75.2000,
        "max_lon": 75.8600,
        "zoom": 10,
    },
}

QUICK_ZONES: list[dict] = [
    {"id": "corridor", "label": "Full Corridor (CKM–Sringeri)", "lat": 13.3600, "lon": 75.5300, "zoom": 10},
    {"id": "ckm", "label": "Chikkamagaluru Town", "lat": 13.3161, "lon": 75.7720, "zoom": 13},
    {"id": "balehonnur", "label": "Balehonnur Ghat", "lat": 13.3560, "lon": 75.4620, "zoom": 12},
    {"id": "sringeri", "label": "Sringeri Town", "lat": 13.4198, "lon": 75.2528, "zoom": 13},
    {"id": "koppa", "label": "Koppa Hills", "lat": 13.5360, "lon": 75.3570, "zoom": 12},
]

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers between two WGS84 coordinates."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def latlon_to_local_km(
    lats: np.ndarray, lons: np.ndarray, origin_lat: float, origin_lon: float
) -> np.ndarray:
    """Project (lat, lon) arrays into local tangent-plane kilometers for fast vectorized cdist."""
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * math.cos(math.radians(origin_lat))
    y_km = (np.asarray(lats, dtype=np.float64) - origin_lat) * km_per_deg_lat
    x_km = (np.asarray(lons, dtype=np.float64) - origin_lon) * km_per_deg_lon
    return np.column_stack([x_km, y_km])


def build_city_grid(city: str = "chikkamagaluru", grid_size: int = 80) -> tuple[np.ndarray, np.ndarray, CityBounds]:
    """Build a high-resolution (grid_size x grid_size) meshgrid of (lat, lon) and local km coords."""
    cfg = CITY_CONFIGS.get(city.lower(), CITY_CONFIGS["chikkamagaluru"])
    lat_axis = np.linspace(cfg["max_lat"], cfg["min_lat"], grid_size)
    lon_axis = np.linspace(cfg["min_lon"], cfg["max_lon"], grid_size)
    lon_grid, lat_grid = np.meshgrid(lon_axis, lat_axis)
    flat_lats = lat_grid.ravel()
    flat_lons = lon_grid.ravel()
    grid_km = latlon_to_local_km(flat_lats, flat_lons, cfg["center_lat"], cfg["center_lon"])
    latlon_pairs = np.column_stack([flat_lats, flat_lons])
    return grid_km, latlon_pairs, cfg
