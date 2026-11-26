"""Fetch live official CPCB/OpenAQ/Open-Meteo readings and seed historical replay points."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import AsyncSessionLocal  # noqa: E402
from app.integrations.official_sync import sync_official_stations_live  # noqa: E402
from app.services.heatmap_service import compute_city_heatmap  # noqa: E402


async def run() -> None:
    async with AsyncSessionLocal() as db:
        synced = await sync_official_stations_live(db=db, city="chikkamagaluru")
        for s in synced:
            print(
                f"[LIVE OFFICIAL] {s['sensor_name']} | PM2.5={s['pm25_raw']} ug/m3 | "
                f"source={s['live_source']} | trust={s['new_trust']}"
            )
        grid = await compute_city_heatmap(
            db=db, city="chikkamagaluru", mode="kriging", fusion_mode="hybrid", grid_size=80, persist=True
        )
        print(
            f"[GRID] 80x80 Hybrid Kriging computed in {grid['compute_ms']} ms | "
            f"coverage={grid['coverage_pct']}% | satellite_anchors={grid['satellite_anchors_used']} | "
            f"mean_pm25={grid['summary']['mean_pm25']} ug/m3"
        )


if __name__ == "__main__":
    asyncio.run(run())
