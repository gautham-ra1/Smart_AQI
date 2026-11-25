"""Pydantic v2 schemas for authentication, users, sensors, ingestion, and admin actions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

HealthProfile = Literal["general", "asthma", "children", "elderly", "pregnant", "outdoor_worker"]
UserRole = Literal["citizen", "sensor_owner", "admin"]
SensorType = Literal["official", "citizen_fixed", "institutional_node", "mobile_fleet"]


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=6, max_length=128)
    health_profile: HealthProfile = "general"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=120)
    health_profile: HealthProfile | None = None


class SensorRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    city: str = Field("chikkamagaluru", min_length=2, max_length=64)
    sensor_type: Literal["citizen_fixed", "institutional_node", "mobile_fleet"] = "citizen_fixed"
    lat: float = Field(..., ge=6.5, le=37.5, description="India latitude bounding box")
    lon: float = Field(..., ge=68.0, le=97.5, description="India longitude bounding box")
    model_meta: dict = Field(default_factory=lambda: {"module": "PMS5003", "calibrated": False})


class OfficialStationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    city: str = Field("chikkamagaluru", min_length=2, max_length=64)
    lat: float = Field(..., ge=6.5, le=37.5)
    lon: float = Field(..., ge=68.0, le=97.5)
    model_meta: dict = Field(default_factory=lambda: {"authority": "KSPCB", "station_class": "CAAQMS"})


class SensorIngestPayload(BaseModel):
    """Physical sanity-checked telemetry payload for virtual or physical IoT devices."""

    pm25: float = Field(..., ge=0.0, le=1000.0, description="Physical PM2.5 range (ug/m3)")
    pm10: float | None = Field(None, ge=0.0, le=2000.0, description="Physical PM10 range (ug/m3)")
    rh_pct: float = Field(55.0, ge=0.0, le=100.0, description="Relative Humidity (%)")
    temp_c: float | None = Field(None, ge=-20.0, le=65.0, description="Ambient Temperature (C)")
    lat: float = Field(..., ge=6.5, le=37.5, description="India latitude bounding box")
    lon: float = Field(..., ge=68.0, le=97.5, description="India longitude bounding box")
    recorded_at: datetime | None = None


class FaultInjectionRequest(BaseModel):
    sensor_id: str | None = None
    city: str = "chikkamagaluru"
    bias_pm25: float = Field(150.0, ge=20.0, le=500.0)
    ticks: int = Field(10, ge=1, le=20)
    rh_pct: float = Field(55.0, ge=0.0, le=100.0)


class RecomputeGridRequest(BaseModel):
    city: str = "chikkamagaluru"
    mode: Literal["idw", "kriging"] = "kriging"
    timestamp: datetime | None = None
    grid_size: int = Field(50, ge=15, le=80)
