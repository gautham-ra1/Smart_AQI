"""Heatmap, hyperlocal point AQI, and city history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import success_response
from app.database import get_db
from app.models.aqi_grid import AQIGrid
from app.services.heatmap_service import compute_city_heatmap, estimate_point_pm25
from app.utils.geo_utils import CITY_CONFIGS

router = APIRouter(prefix="/api/v1", tags=["Heatmap & AQI"])


@router.get("/cities")
async def list_cities():
    return success_response(
        [
            {"key": key, **cfg}
            for key, cfg in CITY_CONFIGS.items()
        ]
    )


@router.get("/heatmap")
async def get_heatmap(
    city: str = Query(default="chikkamagaluru"),
    mode: str = Query(default="kriging", pattern="^(idw|kriging)$"),
    grid_size: int = Query(default=50, ge=15, le=80),
    db: AsyncSession = Depends(get_db),
):
    data = await compute_city_heatmap(
        db=db,
        city=city,
        mode=mode,
        grid_size=grid_size,
        persist=False,
        broadcast=False,
    )
    return success_response(data)


@router.get("/aqi/point")
async def get_point_aqi(
    lat: float = Query(..., ge=6.5, le=37.5),
    lon: float = Query(..., ge=68.0, le=97.5),
    city: str = Query(default="chikkamagaluru"),
    db: AsyncSession = Depends(get_db),
):
    data = await estimate_point_pm25(db=db, lat=lat, lon=lon, city=city)
    return success_response(data)


@router.get("/aqi/history")
async def get_aqi_history(
    city: str = Query(default="chikkamagaluru"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(AQIGrid)
        .where(AQIGrid.city == city.lower())
        .order_by(desc(AQIGrid.computed_at))
        .limit(limit)
    )
    grids = res.scalars().all()
    return success_response(
        [
            {
                "id": g.id,
                "city": g.city,
                "mode": g.mode,
                "requested_mode": g.requested_mode,
                "active_sensor_count": g.active_sensor_count,
                "compute_ms": g.compute_ms,
                "source_timestamp": g.source_timestamp.isoformat(),
                "computed_at": g.computed_at.isoformat(),
            }
            for g in grids
        ]
    )
