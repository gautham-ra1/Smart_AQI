"""API integration tests for /ingest sanity checks (422), rate limits (429), and immutable trigger."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.rate_limiter import rate_limiter
from app.database import AsyncSessionLocal
from app.main import app


@pytest.mark.asyncio
async def test_ingest_validation_rate_limit_and_immutable_trigger():
    rate_limiter.reset_memory()
    email = f"iot_owner_{uuid.uuid4().hex[:8]}@vayumesh.in"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "full_name": "IoT Owner",
                "password": "StrongPassword123",
                "health_profile": "general",
            },
        )
        token = reg.json()["data"]["access_token"]
        s_reg = await client.post(
            "/api/v1/sensors/register",
            json={
                "name": "MG Road Virtual Device",
                "city": "chikkamagaluru",
                "sensor_type": "citizen_fixed",
                "lat": 13.3208,
                "lon": 75.7705,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        api_key = s_reg.json()["data"]["api_key"]

        # 1. Sanity check: pm25 = 2500 -> structured 422
        bad_pm = await client.post(
            "/api/v1/ingest",
            headers={"X-API-Key": api_key},
            json={"pm25": 2500.0, "rh_pct": 60.0, "lat": 13.3208, "lon": 75.7705},
        )
        assert bad_pm.status_code == 422
        assert bad_pm.json()["success"] is False
        assert bad_pm.json()["error"]["code"] == "VALIDATION_ERROR"

        # 2. Sanity check: non-India GPS -> structured 422
        bad_gps = await client.post(
            "/api/v1/ingest",
            headers={"X-API-Key": api_key},
            json={"pm25": 35.0, "rh_pct": 60.0, "lat": 51.5074, "lon": -0.1278},
        )
        assert bad_gps.status_code == 422

        # 3. Valid ingest succeeds (201) and stores immutable raw_reading
        ok = await client.post(
            "/api/v1/ingest",
            headers={"X-API-Key": api_key},
            json={"pm25": 32.5, "pm10": 54.0, "rh_pct": 68.0, "lat": 13.3208, "lon": 75.7705},
        )
        assert ok.status_code == 201
        reading_id = ok.json()["data"]["reading_id"]

        # 4. Burst 12 more requests -> 13th within 60s must return 429 RATE_LIMIT_EXCEEDED
        statuses = []
        for _ in range(12):
            resp = await client.post(
                "/api/v1/ingest",
                headers={"X-API-Key": api_key},
                json={"pm25": 33.0, "rh_pct": 68.0, "lat": 13.3208, "lon": 75.7705},
            )
            statuses.append(resp.status_code)
        assert 429 in statuses

    # 5. Verify PostgreSQL trigger blocks UPDATE on raw_readings (Constraint 3)
    async with AsyncSessionLocal() as db:
        with pytest.raises(DBAPIError):
            await db.execute(
                text("UPDATE raw_readings SET pm25_raw = 999 WHERE id = :rid"),
                {"rid": reading_id},
            )
            await db.commit()
        await db.rollback()
