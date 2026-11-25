"""IoT Telemetry Ingestion Gatekeeper: HMAC-SHA256 key auth, Redis rate limit, Pydantic sanity checks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, success_response
from app.core.rate_limiter import rate_limiter
from app.core.security import hash_api_key
from app.database import get_db
from app.engines.ingestion_engine import process_sensor_reading
from app.models.sensor import Sensor
from app.schemas.auth_schema import SensorIngestPayload

router = APIRouter(prefix="/api/v1", tags=["Ingestion"])


@router.post("/ingest", status_code=201)
async def ingest_reading(
    payload: SensorIngestPayload,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a telemetry packet from a real or virtual IoT AQI sensor."""
    if not x_api_key:
        raise AppError(401, "MISSING_API_KEY", "Header 'X-API-Key' is required for sensor ingestion.")

    key_hash = hash_api_key(x_api_key.strip())

    # 1. Per-key sliding-window rate limit (Constraint 1: 12 req/min -> HTTP 429)
    rl_info = await rate_limiter.enforce_ingest_limit(key_hash)

    # 2. Authenticate hashed API key against sensors table
    res = await db.execute(select(Sensor).where(Sensor.api_key_hash == key_hash))
    sensor = res.scalar_one_or_none()
    if not sensor:
        raise AppError(401, "INVALID_API_KEY", "Unrecognized sensor API key.")
    if sensor.status == "revoked":
        raise AppError(403, "SENSOR_REVOKED", "This sensor API key has been revoked.")

    # 3. Process immutable raw write + RH correction + Two-Tier EWMA trust update
    result = await process_sensor_reading(
        db=db,
        sensor=sensor,
        pm25_raw=payload.pm25,
        pm10_raw=payload.pm10,
        rh_pct=payload.rh_pct,
        temp_c=payload.temp_c,
        lat=payload.lat,
        lon=payload.lon,
        recorded_at=payload.recorded_at,
        broadcast=True,
    )
    result["rate_limit"] = rl_info
    return success_response(result, status_code=201)
