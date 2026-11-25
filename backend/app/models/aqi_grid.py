"""SQLAlchemy AQIGrid model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


class AQIGrid(Base):
    __tablename__ = "aqi_grids"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(64), nullable=False, default="chikkamagaluru")
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    grid_size: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    bounds: Mapped[dict] = mapped_column(JSONType, nullable=False)
    grid_pm25: Mapped[list] = mapped_column(JSONType, nullable=False)
    grid_std_dev: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    active_sensor_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compute_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
