"""Faulty / Rogue Virtual IoT Device Simulator for Live Technical Interview Demos.

Modes:
  --mode drift      Sends +150 ug/m3 persistent bias over 10 ticks -> watch trust decay 0.75 -> 0.05.
  --mode burst      Fires 15 rapid requests -> proves Redis/sliding-window HTTP 429 rate limit.
  --mode malformed  Sends pm25=2500 and non-India GPS -> proves structured HTTP 422 sanity checks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import httpx

KEYS_FILE = Path(__file__).resolve().parent / ".iot_keys.json"


async def run_fault_demo(base_url: str, mode: str, ticks: int, bias: float) -> None:
    if not KEYS_FILE.exists():
        raise FileNotFoundError("Run 'python scripts/seed_official_stations.py' first.")

    devices = json.loads(KEYS_FILE.read_text())["devices"]
    target = next(d for d in devices if d["role_tag"] == "traffic")
    url = f"{base_url.rstrip('/')}/api/v1/ingest"
    headers = {"X-API-Key": target["api_key"]}

    async with httpx.AsyncClient(timeout=8.0) as client:
        if mode == "drift":
            print(f"[DRIFT MODE] Target virtual device: {target['name']} (+{bias} ug/m3 bias x {ticks} ticks)")
            for i in range(1, ticks + 1):
                resp = await client.post(
                    url,
                    headers=headers,
                    json={
                        "pm25": round(28.0 + bias, 2),
                        "pm10": round((28.0 + bias) * 1.5, 2),
                        "rh_pct": 58.0,
                        "lat": target["lat"],
                        "lon": target["lon"],
                    },
                )
                if resp.status_code == 201:
                    d = resp.json()["data"]
                    print(
                        f"  Tick {i:02d}: pm25={d['pm25_raw']} -> trust {d['prev_trust']:.3f} -> {d['new_trust']:.3f} "
                        f"[{d['status']}] (tier={d['tier_used']})"
                    )
                else:
                    print(f"  Tick {i:02d}: HTTP {resp.status_code} {resp.json()}")
                await asyncio.sleep(0.4)

        elif mode == "burst":
            print(f"[BURST MODE] Firing 15 rapid packets from {target['name']} (limit: 12/min)...")
            for i in range(1, 16):
                resp = await client.post(
                    url,
                    headers=headers,
                    json={"pm25": 35.0, "rh_pct": 60.0, "lat": target["lat"], "lon": target["lon"]},
                )
                print(f"  Req {i:02d}: HTTP {resp.status_code} -> {resp.json().get('error', {}).get('code', 'OK')}")

        elif mode == "malformed":
            print(f"[MALFORMED MODE] Testing physical sanity checks on {target['name']}...")
            for label, payload in [
                ("PM2.5=2500 (>1000 limit)", {"pm25": 2500.0, "rh_pct": 60.0, "lat": 13.3161, "lon": 75.7720}),
                ("Non-India GPS (London)", {"pm25": 30.0, "rh_pct": 60.0, "lat": 51.5074, "lon": -0.1278}),
                ("Humidity=140% (>100%)", {"pm25": 30.0, "rh_pct": 140.0, "lat": 13.3161, "lon": 75.7720}),
            ]:
                resp = await client.post(url, headers=headers, json=payload)
                print(f"  {label:<28} -> HTTP {resp.status_code}: {resp.json()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="VayuMesh Faulty / Rogue Virtual IoT Device Demo")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--mode", choices=["drift", "burst", "malformed"], default="drift")
    parser.add_argument("--ticks", type=int, default=10)
    parser.add_argument("--bias", type=float, default=150.0)
    args = parser.parse_args()
    asyncio.run(run_fault_demo(args.url, args.mode, args.ticks, args.bias))


if __name__ == "__main__":
    main()
