"""Core immutable domain models for ISS visibility prediction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class ISSHorizonError(Exception):
    """Base exception for domain and application errors."""


class LocationResolutionError(ISSHorizonError):
    """Raised when a location cannot be resolved to coordinates and timezone."""


class TLEFetchError(ISSHorizonError):
    """Raised when a TLE cannot be fetched or parsed."""


class PredictionError(ISSHorizonError):
    """Raised when ISS visibility prediction fails."""


class EmailSendError(ISSHorizonError):
    """Raised when sending a mail report fails."""


@dataclass(frozen=True)
class Location:
    """Resolved observer location with coordinates and timezone information."""

    query: str
    resolved_name: str
    latitude: float
    longitude: float
    timezone_name: str
    timezone: ZoneInfo


@dataclass(frozen=True)
class TLE:
    """Two-line element set for a satellite."""

    name: str
    line1: str
    line2: str


@dataclass(frozen=True)
class VisibilityWindow:
    """Single local-time visibility segment for ISS observations."""

    start_local: datetime
    end_local: datetime
    peak_local: datetime
    duration: timedelta
    peak_elevation_deg: float
    start_azimuth_deg: float
    peak_azimuth_deg: float
    end_azimuth_deg: float
    start_direction: str
    peak_direction: str
    end_direction: str
    visibility_stars: int = 1

    def __post_init__(self) -> None:
        for field_name in ("start_local", "end_local", "peak_local"):
            value = getattr(self, field_name)
            if value.tzinfo is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        if self.end_local < self.start_local:
            raise ValueError("end_local must not be before start_local")
        if self.duration.total_seconds() < 0:
            raise ValueError("duration must not be negative")
        if not 1 <= self.visibility_stars <= 5:
            raise ValueError("visibility_stars must be in 1..5")


@dataclass(frozen=True)
class MonthRange:
    """Timezone-aware local month boundaries."""

    start_local: datetime
    end_local: datetime


@dataclass(frozen=True)
class SMTPConfig:
    """SMTP transport configuration for report delivery."""

    host: str
    port: int
    user: str | None
    password: str | None
    from_addr: str
    tls_mode: str
