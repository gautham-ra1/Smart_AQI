"""SQLAlchemy TrustLog model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrustLog(Base):
    __tablename__ = "trust_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sensors.id"), nullable=False)
    reading_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("raw_readings.id"), nullable=False)
    pm25_corrected: Mapped[float] = mapped_column(Float, nullable=False)
    prev_trust: Mapped[float] = mapped_column(Float, nullable=False)
    new_trust: Mapped[float] = mapped_column(Float, nullable=False)
    agreement_score: Mapped[float] = mapped_column(Float, nullable=False)
    tier_used: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_pm25: Mapped[float | None] = mapped_column(Float, nullable=True)
    dist_ref_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
