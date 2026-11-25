"""SQLAlchemy Advisory model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Advisory(Base):
    __tablename__ = "advisories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    city: Mapped[str] = mapped_column(String(64), nullable=False, default="chikkamagaluru")
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    pm25_equiv: Mapped[float] = mapped_column(Float, nullable=False)
    aqi_pm25_equiv: Mapped[int] = mapped_column(Integer, nullable=False)
    cpcb_band: Mapped[str] = mapped_column(String(32), nullable=False)
    health_profile: Mapped[str] = mapped_column(String(32), nullable=False)
    advisory_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
