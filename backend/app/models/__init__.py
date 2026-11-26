"""Register all SQLAlchemy models on Base.metadata."""

from app.models.advisory import Advisory
from app.models.aqi_grid import AQIGrid
from app.models.reading import RawReading
from app.models.sensor import Sensor
from app.models.trust_log import TrustLog
from app.models.user import AuditLog, User

__all__ = ["User", "AuditLog", "Sensor", "RawReading", "TrustLog", "AQIGrid", "Advisory"]
