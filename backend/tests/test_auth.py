"""API integration tests for JWT auth, RBAC 403 enforcement, and HMAC-SHA256 sensor keys."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import hash_api_key
from app.database import AsyncSessionLocal
from app.main import app
from app.models.sensor import Sensor


@pytest.mark.asyncio
async def test_register_login_rbac_and_hashed_api_key():
    email = f"citizen_{uuid.uuid4().hex[:8]}@vayumesh.in"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register citizen
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "full_name": "Chikkamagaluru Citizen",
                "password": "StrongPassword123",
                "health_profile": "asthma",
            },
        )
        assert reg.status_code == 201
        body = reg.json()
        assert body["success"] is True
        token = body["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. RBAC check: citizen must get 403 Forbidden on admin recompute
        forbidden = await client.post(
            "/api/v1/admin/recompute",
            json={"city": "chikkamagaluru", "mode": "kriging"},
            headers=headers,
        )
        assert forbidden.status_code == 403
        assert forbidden.json()["success"] is False
        assert forbidden.json()["error"]["code"] == "FORBIDDEN"

        # 3. Register sensor -> receive one-time raw API key; DB stores only 64-char HMAC hash
        s_reg = await client.post(
            "/api/v1/sensors/register",
            json={
                "name": "AIT Test PMS5003",
                "city": "chikkamagaluru",
                "sensor_type": "institutional_node",
                "lat": 13.3442,
                "lon": 75.7890,
            },
            headers=headers,
        )
        assert s_reg.status_code == 201
        raw_key = s_reg.json()["data"]["api_key"]
        sensor_id = uuid.UUID(s_reg.json()["data"]["sensor"]["id"])
        assert raw_key.startswith("vm_")

    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(Sensor).where(Sensor.id == sensor_id))).scalar_one()
        assert row.api_key_hash != raw_key
        assert len(row.api_key_hash) == 64
        assert row.api_key_hash == hash_api_key(raw_key)
