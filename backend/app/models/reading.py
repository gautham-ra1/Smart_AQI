"""SQLAlchemy immutable RawReading model (append-only, protected by DB trigger)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RawReading(Base):
    __tablename__ = "raw_readings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sensors.id"), nullable=False)
    pm25_raw: Mapped[float] = mapped_column(Float, nullable=False)
    pm10_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    rh_pct: Mapped[float] = mapped_column(Float, nullable=False, default=55.0)
    temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
