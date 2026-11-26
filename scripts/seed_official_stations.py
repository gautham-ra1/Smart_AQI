"""Seed Chikkamagaluru official KSPCB station, demo users, and Virtual IoT Device fleet.

Saves the issued per-device raw API keys to scripts/.iot_keys.json (gitignored) so
generate_synthetic_sensors.py and simulate_faulty_sensor.py act as real HTTP IoT devices.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.security import generate_raw_api_key, hash_api_key, hash_password  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402
from app.engines.ingestion_engine import process_sensor_reading  # noqa: E402
from app.integrations.kspcb_client import CHIKKAMAGALURU_OFFICIAL_STATIONS  # noqa: E402
from app.models.sensor import Sensor  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.heatmap_service import compute_city_heatmap  # noqa: E402

KEYS_FILE = Path(__file__).resolve().parent / ".iot_keys.json"

CHIKKAMAGALURU_VIRTUAL_DEVICES = [
    # Tier 1: Within 5 km of Kalyana Nagara KSPCB CAAQMS (Reference-Anchored)
    {
        "name": "AIT Campus Institutional Anchor",
        "sensor_type": "institutional_node",
        "lat": 13.3442,
        "lon": 75.7890,
        "base_pm25": 24.0,
        "rh_pct": 66.0,
        "role_tag": "institutional",
        "model_meta": {"module": "PMS7003", "host": "Adichunchanagiri Institute of Technology"},
    },
    {
        "name": "District Hospital Anchor",
        "sensor_type": "institutional_node",
        "lat": 13.3185,
        "lon": 75.7755,
        "base_pm25": 31.0,
        "rh_pct": 64.0,
        "role_tag": "institutional",
        "model_meta": {"module": "SPS30", "host": "Chikkamagaluru District Hospital"},
    },
    {
        "name": "MG Road Commercial Corridor",
        "sensor_type": "citizen_fixed",
        "lat": 13.3208,
        "lon": 75.7705,
        "base_pm25": 42.0,
        "rh_pct": 62.0,
        "role_tag": "traffic",
        "model_meta": {"module": "PMS5003", "zone": "MG Road Traffic"},
    },
    {
        "name": "KSRTC Bus Stand Junction",
        "sensor_type": "institutional_node",
        "lat": 13.3150,
        "lon": 75.7795,
        "base_pm25": 48.0,
        "rh_pct": 63.0,
        "role_tag": "traffic",
        "model_meta": {"module": "PMS5003", "zone": "Bus Terminal"},
    },
    {
        "name": "Coffee Curing & Plywood Belt",
        "sensor_type": "institutional_node",
        "lat": 13.3060,
        "lon": 75.7620,
        "base_pm25": 54.0,
        "rh_pct": 67.0,
        "role_tag": "industrial",
        "model_meta": {"module": "PMS7003", "zone": "Industrial Estate"},
    },
    # High-RH Monsoon Fog Node (demonstrates hygrometric pre-calibration preserving ~0.81 trust)
    {
        "name": "Mullayanagiri Foothill Fog Node",
        "sensor_type": "citizen_fixed",
        "lat": 13.3360,
        "lon": 75.7610,
        "base_pm25": 45.0,  # Raw inflated by 90% RH -> corrects to ~30.7 ug/m3
        "rh_pct": 90.0,
        "role_tag": "monsoon_fog",
        "model_meta": {"module": "PMS5003", "zone": "Western Ghats Monsoon Fog"},
    },
    # Opportunistic Mobile Fleet Nodes (4 travelling vehicles across Chikkamagaluru -> Sringeri)
    {
        "name": "KSRTC Express Bus #14 (CKM-Sringeri)",
        "sensor_type": "mobile_fleet",
        "lat": 13.3240,
        "lon": 75.7760,
        "base_pm25": 36.0,
        "rh_pct": 68.0,
        "role_tag": "mobile_bus",
        "model_meta": {"module": "PMS7003", "vehicle": "KSRTC Express Bus", "route": "Chikkamagaluru-Balehonnur-Sringeri"},
    },
    {
        "name": "Chikkamagaluru Auto #07 (Town Loop)",
        "sensor_type": "mobile_fleet",
        "lat": 13.3120,
        "lon": 75.7680,
        "base_pm25": 40.0,
        "rh_pct": 64.0,
        "role_tag": "mobile_auto",
        "model_meta": {"module": "PMS5003", "vehicle": "Auto-Rickshaw", "route": "KalyanaNagara-MGRoad-AIT"},
    },
    {
        "name": "Sringeri-Koppa Shuttle #22 (Mobile)",
        "sensor_type": "mobile_fleet",
        "lat": 13.4198,
        "lon": 75.2528,
        "base_pm25": 18.0,
        "rh_pct": 82.0,
        "role_tag": "mobile_sringeri_bus",
        "model_meta": {"module": "PMS7003", "vehicle": "Hill Shuttle Bus", "route": "Sringeri-Hariharapura-Koppa"},
    },
    {
        "name": "Ghat Delivery EV #09 (CKM-Balehonnur)",
        "sensor_type": "mobile_fleet",
        "lat": 13.2950,
        "lon": 75.7360,
        "base_pm25": 28.0,
        "rh_pct": 74.0,
        "role_tag": "mobile_delivery",
        "model_meta": {"module": "SPS30", "vehicle": "Delivery EV", "route": "AIT-Aldur-Balehonnur"},
    },
    # Far-away Static Citizen / Institutional Nodes (30-55 km from Kalyana Nagara -> Cross-checked vs Open-Meteo CAMS)
    {
        "name": "Sringeri Sharada Peetham Citizen Node",
        "sensor_type": "citizen_fixed",
        "lat": 13.4198,
        "lon": 75.2528,
        "base_pm25": 16.5,
        "rh_pct": 80.0,
        "role_tag": "far_citizen",
        "model_meta": {"module": "PMS5003", "taluk": "Sringeri (55 km from CAAQMS)"},
    },
    {
        "name": "Sringeri Tunga Bridge Anchor",
        "sensor_type": "institutional_node",
        "lat": 13.4265,
        "lon": 75.2640,
        "base_pm25": 19.0,
        "rh_pct": 84.0,
        "role_tag": "far_citizen",
        "model_meta": {"module": "PMS7003", "taluk": "Sringeri Riverfront"},
    },
    {
        "name": "Balehonnur Bhadra Bridge Citizen Node",
        "sensor_type": "citizen_fixed",
        "lat": 13.3560,
        "lon": 75.4620,
        "base_pm25": 21.0,
        "rh_pct": 85.0,
        "role_tag": "far_citizen",
        "model_meta": {"module": "PMS5003", "taluk": "Balehonnur (34 km from CAAQMS)"},
    },
    {
        "name": "Koppa Town Bus Stand Citizen Node",
        "sensor_type": "citizen_fixed",
        "lat": 13.5360,
        "lon": 75.3570,
        "base_pm25": 17.5,
        "rh_pct": 79.0,
        "role_tag": "far_citizen",
        "model_meta": {"module": "PMS5003", "taluk": "Koppa (50 km from CAAQMS)"},
    },
    {
        "name": "Jayapura Ghat Citizen Node",
        "sensor_type": "citizen_fixed",
        "lat": 13.3880,
        "lon": 75.3820,
        "base_pm25": 18.0,
        "rh_pct": 86.0,
        "role_tag": "far_citizen",
        "model_meta": {"module": "PMS5003", "taluk": "Jayapura Ghat (42 km from CAAQMS)"},
    },
    # Tier 2: Outer Taluk Peer Cluster (> 5 km from Kalyana Nagara -> Peer-Consensus MAD Fallback)
    {
        "name": "Aldur Road Peer Node A",
        "sensor_type": "institutional_node",
        "lat": 13.2680,
        "lon": 75.7420,
        "base_pm25": 23.0,
        "rh_pct": 74.0,
        "role_tag": "outer_peer",
        "model_meta": {"module": "PMS5003", "taluk": "Aldur Corridor"},
    },
    {
        "name": "Aldur Road Peer Node B",
        "sensor_type": "citizen_fixed",
        "lat": 13.2720,
        "lon": 75.7480,
        "base_pm25": 25.0,
        "rh_pct": 73.0,
        "role_tag": "outer_peer",
        "model_meta": {"module": "PMS5003", "taluk": "Aldur Corridor"},
    },
    {
        "name": "Aldur Road Peer Node C",
        "sensor_type": "citizen_fixed",
        "lat": 13.2650,
        "lon": 75.7510,
        "base_pm25": 22.0,
        "rh_pct": 76.0,
        "role_tag": "outer_peer",
        "model_meta": {"module": "PMS5003", "taluk": "Aldur Corridor"},
    },
    {
        "name": "Aldur Road Peer Node D",
        "sensor_type": "citizen_fixed",
        "lat": 13.2750,
        "lon": 75.7380,
        "base_pm25": 24.0,
        "rh_pct": 75.0,
        "role_tag": "outer_peer",
        "model_meta": {"module": "PMS5003", "taluk": "Aldur Corridor"},
    },
]


async def _get_or_create_user(db, email: str, full_name: str, password: str, role: str, profile: str) -> User:
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if user:
        return user
    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        role=role,
        health_profile=profile,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def seed() -> None:
    issued_devices: list[dict] = []

    async with AsyncSessionLocal() as db:
        admin = await _get_or_create_user(
            db, "admin@vayumesh.in", "VayuMesh Admin", "Admin@123", "admin", "general"
        )
        owner = await _get_or_create_user(
            db, "owner@vayumesh.in", "AIT Campus Operator", "Owner@123", "sensor_owner", "outdoor_worker"
        )
        await _get_or_create_user(
            db, "citizen@vayumesh.in", "Chikkamagaluru Resident", "Citizen@123", "citizen", "asthma"
        )

        # 1. Seed Official KSPCB CAAQMS Station (Kalyana Nagara)
        for st in CHIKKAMAGALURU_OFFICIAL_STATIONS:
            res = await db.execute(select(Sensor).where(Sensor.name == st["name"]))
            sensor = res.scalar_one_or_none()
            raw_key = generate_raw_api_key()
            if sensor is None:
                sensor = Sensor(
                    owner_id=admin.id,
                    name=st["name"],
                    city=st["city"],
                    api_key_hash=hash_api_key(raw_key),
                    sensor_type="official",
                    status="active",
                    model_meta=st["model_meta"],
                    trust_weight=1.0,
                    lat=st["lat"],
                    lon=st["lon"],
                )
                db.add(sensor)
                await db.commit()
                await db.refresh(sensor)
            else:
                # Refresh key so local virtual official broadcaster can authenticate
                sensor.api_key_hash = hash_api_key(raw_key)
                sensor.trust_weight = 1.0
                sensor.status = "active"
                await db.commit()

            await process_sensor_reading(
                db=db,
                sensor=sensor,
                pm25_raw=26.5,
                pm10_raw=44.0,
                rh_pct=65.0,
                temp_c=23.5,
                lat=sensor.lat,
                lon=sensor.lon,
                broadcast=False,
            )
            issued_devices.append(
                {
                    "id": str(sensor.id),
                    "name": sensor.name,
                    "sensor_type": sensor.sensor_type,
                    "role_tag": "official",
                    "lat": sensor.lat,
                    "lon": sensor.lon,
                    "base_pm25": 26.5,
                    "rh_pct": 65.0,
                    "api_key": raw_key,
                }
            )

        # 2. Seed Chikkamagaluru Virtual IoT Fleet
        for dev in CHIKKAMAGALURU_VIRTUAL_DEVICES:
            res = await db.execute(select(Sensor).where(Sensor.name == dev["name"]))
            sensor = res.scalar_one_or_none()
            raw_key = generate_raw_api_key()
            if sensor is None:
                sensor = Sensor(
                    owner_id=owner.id,
                    name=dev["name"],
                    city="chikkamagaluru",
                    api_key_hash=hash_api_key(raw_key),
                    sensor_type=dev["sensor_type"],
                    status="active",
                    model_meta=dev["model_meta"],
                    trust_weight=0.75,
                    lat=dev["lat"],
                    lon=dev["lon"],
                )
                db.add(sensor)
                await db.commit()
                await db.refresh(sensor)
            else:
                sensor.api_key_hash = hash_api_key(raw_key)
                sensor.trust_weight = 0.75
                sensor.status = "active"
                await db.commit()

            await process_sensor_reading(
                db=db,
                sensor=sensor,
                pm25_raw=dev["base_pm25"],
                pm10_raw=round(dev["base_pm25"] * 1.6, 1),
                rh_pct=dev["rh_pct"],
                temp_c=22.5,
                lat=sensor.lat,
                lon=sensor.lon,
                broadcast=False,
            )
            issued_devices.append(
                {
                    "id": str(sensor.id),
                    "name": sensor.name,
                    "sensor_type": sensor.sensor_type,
                    "role_tag": dev["role_tag"],
                    "lat": sensor.lat,
                    "lon": sensor.lon,
                    "base_pm25": dev["base_pm25"],
                    "rh_pct": dev["rh_pct"],
                    "api_key": raw_key,
                }
            )

        # 3. Pre-compute initial Chikkamagaluru Kriging heatmap
        grid = await compute_city_heatmap(db=db, city="chikkamagaluru", mode="kriging", persist=True, broadcast=False)

    KEYS_FILE.write_text(json.dumps({"city": "chikkamagaluru", "devices": issued_devices}, indent=2))
    print(f"Seeded {len(issued_devices)} Chikkamagaluru devices (1 official + {len(issued_devices) - 1} virtual IoT).")
    print(f"Initial Kriging 50x50 grid computed in {grid['compute_ms']} ms (mean PM2.5={grid['summary']['mean_pm25']} ug/m3).")
    print(f"Saved virtual IoT device keys to {KEYS_FILE}")
    print("Demo accounts: admin@vayumesh.in / Admin@123 | owner@vayumesh.in / Owner@123 | citizen@vayumesh.in / Citizen@123")


if __name__ == "__main__":
    asyncio.run(seed())
