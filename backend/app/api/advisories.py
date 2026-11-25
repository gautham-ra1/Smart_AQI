"""CPCB NAQI & MoHFW/NCDC Personalised Health Advisory endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import success_response
from app.database import get_db
from app.engines.advisory_engine import get_health_advisory
from app.engines.aqi_engine import get_cpcb_band_metadata
from app.services.heatmap_service import estimate_point_pm25

router = APIRouter(prefix="/api/v1/advisories", tags=["Health Advisories"])


@router.get("/bands")
async def cpcb_bands():
    return success_response(get_cpcb_band_metadata())


@router.get("")
async def get_advisory(
    profile: str = Query(default="general"),
    pm25: float | None = Query(default=None, ge=0.0, le=1000.0),
    lat: float | None = Query(default=None, ge=6.5, le=37.5),
    lon: float | None = Query(default=None, ge=68.0, le=97.5),
    city: str = Query(default="chikkamagaluru"),
    db: AsyncSession = Depends(get_db),
):
    point_info = None
    if pm25 is None:
        target_lat = lat if lat is not None else 13.3161
        target_lon = lon if lon is not None else 75.7720
        point_info = await estimate_point_pm25(db=db, lat=target_lat, lon=target_lon, city=city)
        pm25_val = point_info["pm25_equiv"]
    else:
        pm25_val = pm25

    advisory = get_health_advisory(pm25_val, profile=profile)
    if point_info:
        advisory["location"] = {"lat": point_info["lat"], "lon": point_info["lon"], "city": city}
    return success_response(advisory)
