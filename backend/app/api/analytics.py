"""Analytics endpoints for system telemetry, tier breakdown, and trust distributions."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import success_response
from app.database import get_db
from app.models.reading import RawReading
from app.models.sensor import Sensor
from app.models.trust_log import TrustLog

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/summary")
async def analytics_summary(db: AsyncSession = Depends(get_db)):
    total_sensors = (await db.execute(select(func.count(Sensor.id)))).scalar_one()
    total_readings = (await db.execute(select(func.count(RawReading.id)))).scalar_one()
    avg_trust = (await db.execute(select(func.avg(Sensor.trust_weight)))).scalar_one() or 0.0

    by_type_res = await db.execute(
        select(Sensor.sensor_type, func.count(Sensor.id)).group_by(Sensor.sensor_type)
    )
    by_status_res = await db.execute(
        select(Sensor.status, func.count(Sensor.id)).group_by(Sensor.status)
    )
    by_tier_res = await db.execute(
        select(TrustLog.tier_used, func.count(TrustLog.id)).group_by(TrustLog.tier_used)
    )

    recent_readings_res = await db.execute(
        select(TrustLog).order_by(desc(TrustLog.evaluated_at)).limit(30)
    )
    recent = list(reversed(recent_readings_res.scalars().all()))

    return success_response(
        {
            "total_sensors": total_sensors,
            "immutable_raw_readings": total_readings,
            "mean_trust_weight": round(float(avg_trust), 3),
            "sensors_by_type": {row[0]: row[1] for row in by_type_res.all()},
            "sensors_by_status": {row[0]: row[1] for row in by_status_res.all()},
            "evaluations_by_tier": {row[0]: row[1] for row in by_tier_res.all()},
            "recent_trend": [
                {
                    "id": tl.id,
                    "pm25_corrected": tl.pm25_corrected,
                    "new_trust": tl.new_trust,
                    "tier_used": tl.tier_used,
                    "evaluated_at": tl.evaluated_at.isoformat(),
                }
                for tl in recent
            ],
        }
    )
