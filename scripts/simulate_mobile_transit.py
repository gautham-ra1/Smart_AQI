"""Dedicated 4-Vehicle Moving Mobile IoT Transit Simulator across Chikkamagaluru -> Balehonnur -> Koppa -> Sringeri.

Drives 4 real-time travelling IoT sensors simultaneously:
  1. KSRTC Express Bus #14   : Chikkamagaluru <-> Aldur <-> Balehonnur <-> Sringeri
  2. Chikkamagaluru Auto #07 : Town Loop (Kalyana Nagara <-> MG Road <-> AIT <-> Coffee Belt)
  3. Sringeri-Koppa Bus #22  : Sringeri <-> Hariharapura <-> Koppa <-> Jayapura
  4. Ghat Delivery EV #09    : AIT Campus <-> Aldur <-> Sangameshwarapete <-> Balehonnur

Usage:
    python scripts/simulate_mobile_transit.py --url http://localhost:8000 --interval 6
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from pathlib import Path

import httpx

KEYS_FILE = Path(__file__).resolve().parent / ".iot_keys.json"

ROUTES_BY_TAG = {
    "mobile_bus": [
        ("Chikkamagaluru KSRTC Stand", 13.3150, 75.7795, 42.0, 64.0),
        ("IG Road Junction", 13.3105, 75.7640, 38.0, 66.0),
        ("Vastare Cross", 13.2950, 75.7360, 30.0, 70.0),
        ("Aldur Town", 13.2680, 75.7020, 25.0, 74.0),
        ("Sangameshwarapete", 13.3020, 75.6120, 21.0, 79.0),
        ("Magundi Coffee Estates", 13.3320, 75.5350, 19.0, 84.0),
        ("Balehonnur Bridge", 13.3560, 75.4620, 22.0, 88.0),
        ("Jayapura Ghat", 13.3880, 75.3820, 19.0, 90.0),
        ("Sringeri Entry Checkpost", 13.4090, 75.3020, 17.0, 86.0),
        ("Sringeri Sharada Peetham", 13.4198, 75.2528, 19.0, 82.0),
    ],
    "mobile_auto": [
        ("Kalyana Nagara", 13.3161, 75.7720, 28.0, 65.0),
        ("MG Road Market", 13.3208, 75.7705, 44.0, 63.0),
        ("District Hospital", 13.3185, 75.7755, 32.0, 64.0),
        ("AIT Campus Gate", 13.3442, 75.7890, 23.0, 66.0),
        ("Kadur Road Crossing", 13.3310, 75.7830, 37.0, 65.0),
        ("Coffee Curing Belt", 13.3060, 75.7620, 48.0, 67.0),
    ],
    "mobile_sringeri_bus": [
        ("Sringeri Sharada Peetham", 13.4198, 75.2528, 17.0, 82.0),
        ("Tunga Bridge", 13.4265, 75.2640, 18.0, 85.0),
        ("Hariharapura Matha", 13.4780, 75.2980, 15.0, 84.0),
        ("Koppa Town Bus Stand", 13.5360, 75.3570, 19.0, 79.0),
        ("Narve Forest Road", 13.4680, 75.3740, 15.0, 83.0),
        ("Jayapura Ghat", 13.3880, 75.3820, 18.0, 87.0),
    ],
    "mobile_delivery": [
        ("AIT Campus", 13.3442, 75.7890, 24.0, 66.0),
        ("Chikkamagaluru Bypass", 13.3080, 75.7580, 34.0, 67.0),
        ("Aldur Coffee Junction", 13.2680, 75.7420, 24.0, 74.0),
        ("Sangameshwarapete", 13.3020, 75.6120, 20.0, 80.0),
        ("Balehonnur Market", 13.3560, 75.4620, 23.0, 86.0),
    ],
}


def _expand_smooth_route(waypoints: list[tuple], substeps: int = 3) -> list[tuple]:
    forward = []
    for i in range(len(waypoints) - 1):
        name_a, lat_a, lon_a, pm_a, rh_a = waypoints[i]
        name_b, lat_b, lon_b, pm_b, rh_b = waypoints[i + 1]
        for s in range(substeps):
            t = s / substeps
            forward.append(
                (
                    name_a if t < 0.5 else name_b,
                    lat_a + (lat_b - lat_a) * t,
                    lon_a + (lon_b - lon_a) * t,
                    pm_a + (pm_b - pm_a) * t,
                    rh_a + (rh_b - rh_a) * t,
                )
            )
    forward.append(waypoints[-1])
    return forward + list(reversed(forward[1:-1]))


async def run_mobile_transit(base_url: str, interval_sec: float, ticks: int) -> None:
    if not KEYS_FILE.exists():
        raise FileNotFoundError(
            f"{KEYS_FILE} not found. Run 'python scripts/seed_official_stations.py' first."
        )

    devices = json.loads(KEYS_FILE.read_text())["devices"]
    active_fleet = []
    for tag, waypoints in ROUTES_BY_TAG.items():
        dev = next((d for d in devices if d["role_tag"] == tag), None)
        if dev:
            active_fleet.append((dev, _expand_smooth_route(waypoints, substeps=3)))

    if not active_fleet:
        raise RuntimeError("No mobile fleet devices found in .iot_keys.json. Re-run seed_official_stations.py.")

    url = f"{base_url.rstrip('/')}/api/v1/ingest"
    print(f"[VayuMesh 4-Vehicle Mobile Transit Simulator] Streaming {len(active_fleet)} vehicles -> {url}")
    for dev, path in active_fleet:
        print(f"  - {dev['name']} ({len(path)} GPS steps)")

    step = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        while ticks == 0 or step < ticks:
            step += 1
            for idx, (dev, path) in enumerate(active_fleet):
                # Offset each vehicle's starting step so trails spread nicely across the corridor
                label, lat, lon, pm_base, rh_base = path[(step + idx * 4) % len(path)]
                rh_now = round(min(96.0, max(45.0, rh_base + random.uniform(-2.0, 2.0))), 1)
                fog_mult = 1.0 + 0.008 * ((rh_now - 75.0) ** 1.5) if rh_now > 75.0 else 1.0
                pm_raw = round(max(6.0, (pm_base + random.uniform(-2.5, 4.0)) * fog_mult), 2)

                payload = {
                    "pm25": pm_raw,
                    "pm10": round(pm_raw * random.uniform(1.45, 1.7), 2),
                    "rh_pct": rh_now,
                    "temp_c": round(random.uniform(19.0, 25.5), 1),
                    "lat": round(lat + random.uniform(-0.0004, 0.0004), 5),
                    "lon": round(lon + random.uniform(-0.0004, 0.0004), 5),
                }
                try:
                    resp = await client.post(url, headers={"X-API-Key": dev["api_key"]}, json=payload)
                    if resp.status_code == 201:
                        d = resp.json()["data"]
                        print(
                            f"  [Step {step:03d}] {dev['name']:<37} @ {label:<24} "
                            f"raw={d['pm25_raw']:5.1f} corr={d['pm25_corrected']:5.1f} "
                            f"RH={rh_now:4.1f}% trust={d['new_trust']:.3f} [{d['tier_used']}]"
                        )
                    else:
                        print(f"  [HTTP {resp.status_code}] {dev['name']}: {resp.text[:100]}")
                except Exception as exc:
                    print(f"  [ERR] {dev['name']}: {exc}")

            if ticks == 0 or step < ticks:
                await asyncio.sleep(interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(description="VayuMesh 4-Vehicle Moving IoT Simulator")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--interval", type=float, default=6.0)
    parser.add_argument("--ticks", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(run_mobile_transit(args.url, args.interval, args.ticks))


if __name__ == "__main__":
    main()
