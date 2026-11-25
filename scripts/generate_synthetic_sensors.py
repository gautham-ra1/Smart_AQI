"""Virtual IoT Device Simulator — acts as real ESP32 + PMS5003/7003 hardware nodes.

Each virtual device authenticates over HTTP with its own per-device X-API-Key header
and posts live PM2.5, PM10, RH%, temperature, and GPS packets to POST /api/v1/ingest.

Usage:
    python scripts/generate_synthetic_sensors.py --url http://localhost:8000 --interval 6 --cycles 0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
from pathlib import Path

import httpx

KEYS_FILE = Path(__file__).resolve().parent / ".iot_keys.json"

# Realistic Chikkamagaluru mobile transit route loops
MOBILE_ROUTES = {
    "mobile_bus": [
        (13.3442, 75.7890),  # AIT Campus
        (13.3320, 75.7820),  # Kadur Road
        (13.3208, 75.7705),  # MG Road
        (13.3150, 75.7795),  # KSRTC Bus Stand
        (13.3185, 75.7755),  # District Hospital
    ],
    "mobile_auto": [
        (13.3161, 75.7720),  # Kalyana Nagara
        (13.3110, 75.7670),  # IG Road
        (13.3060, 75.7620),  # Coffee Curing Belt
        (13.3140, 75.7700),  # Town Center
    ],
}


async def run_virtual_iot_fleet(base_url: str, interval_sec: float, cycles: int) -> None:
    if not KEYS_FILE.exists():
        raise FileNotFoundError(
            f"{KEYS_FILE} not found. Run 'python scripts/seed_official_stations.py' first."
        )

    config = json.loads(KEYS_FILE.read_text())
    devices = config["devices"]
    step = 0

    print(f"[VayuMesh Virtual IoT Fleet] Streaming {len(devices)} Chikkamagaluru devices -> {base_url}/api/v1/ingest")
    async with httpx.AsyncClient(timeout=8.0) as client:
        while cycles == 0 or step < cycles:
            step += 1
            diurnal = 4.0 * math.sin(step / 5.0)
            print(f"\n--- Tick #{step} ---")

            for dev in devices:
                role = dev["role_tag"]
                lat, lon = dev["lat"], dev["lon"]

                # Move mobile fleet GPS along route waypoints each tick
                if role in MOBILE_ROUTES:
                    route = MOBILE_ROUTES[role]
                    lat, lon = route[step % len(route)]
                    lat += random.uniform(-0.0012, 0.0012)
                    lon += random.uniform(-0.0012, 0.0012)

                if role == "monsoon_fog":
                    # Healthy sensor in 88-92% RH Chikkamagaluru fog (raw inflated, pre-calibrated by backend)
                    rh_pct = round(random.uniform(88.0, 92.0), 1)
                    pm25_raw = round(max(10.0, 44.0 + random.uniform(-2.5, 2.5)), 2)
                else:
                    rh_pct = round(max(35.0, min(85.0, dev["rh_pct"] + random.uniform(-2.0, 2.0))), 1)
                    pm25_raw = round(max(5.0, dev["base_pm25"] + diurnal + random.uniform(-3.0, 3.0)), 2)

                payload = {
                    "pm25": pm25_raw,
                    "pm10": round(pm25_raw * random.uniform(1.45, 1.75), 2),
                    "rh_pct": rh_pct,
                    "temp_c": round(random.uniform(20.0, 26.0), 1),
                    "lat": round(lat, 5),
                    "lon": round(lon, 5),
                }

                try:
                    resp = await client.post(
                        f"{base_url.rstrip('/')}/api/v1/ingest",
                        headers={"X-API-Key": dev["api_key"]},
                        json=payload,
                    )
                    if resp.status_code == 201:
                        d = resp.json()["data"]
                        print(
                            f"  [OK] {dev['name']:<34} raw={d['pm25_raw']:5.1f} corr={d['pm25_corrected']:5.1f} "
                            f"RH={d['rh_pct']:4.1f}% trust={d['new_trust']:.3f} tier={d['tier_used']}"
                        )
                    else:
                        print(f"  [HTTP {resp.status_code}] {dev['name']}: {resp.text[:120]}")
                except Exception as exc:
                    print(f"  [ERR] {dev['name']}: {exc}")

            if cycles == 0 or step < cycles:
                await asyncio.sleep(interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(description="VayuMesh Chikkamagaluru Virtual IoT Fleet Simulator")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend API base URL")
    parser.add_argument("--interval", type=float, default=6.0, help="Seconds between telemetry ticks")
    parser.add_argument("--cycles", type=int, default=0, help="Number of cycles (0 = infinite)")
    args = parser.parse_args()
    asyncio.run(run_virtual_iot_fleet(args.url, args.interval, args.cycles))


if __name__ == "__main__":
    main()
