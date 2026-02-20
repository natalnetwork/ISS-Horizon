"""Deterministic smoke tests for predictor logic without real ephemeris."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from iss_horizon.config import Config
from iss_horizon.models import Location
from iss_horizon.predictor import ISSPredictor


def _location() -> Location:
    tz = ZoneInfo("America/Fortaleza")
    return Location(
        query="Natal",
        resolved_name="Natal, RN, Brazil",
        latitude=-5.79,
        longitude=-35.2,
        timezone_name="America/Fortaleza",
        timezone=tz,
    )


def test_windows_from_samples_builds_visible_span() -> None:
    predictor = ISSPredictor(
        config=Config(
            min_elev_deg=15.0,
            twilight_deg=-12.0,
            sample_seconds=10,
            min_window_seconds=20,
        )
    )
    start = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    samples = [start + timedelta(seconds=i * 10) for i in range(6)]

    windows = predictor._windows_from_samples(
        loc=_location(),
        sample_times_utc=samples,
        iss_alt_deg=[5.0, 16.0, 24.0, 23.0, 12.0, 4.0],
        iss_az_deg=[200.0, 220.0, 250.0, 280.0, 300.0, 320.0],
        sun_alt_deg=[-15.0, -15.0, -16.0, -16.0, -16.0, -16.0],
        iss_sunlit=[True, True, True, True, True, True],
    )

    assert len(windows) == 1
    win = windows[0]
    assert int(win.duration.total_seconds()) == 20
    assert win.peak_elevation_deg == 24.0
    assert win.start_direction == "SW"
    assert win.visibility_stars == 2


def test_windows_from_samples_filters_short_spans() -> None:
    predictor = ISSPredictor(
        config=Config(
            min_elev_deg=15.0,
            twilight_deg=-12.0,
            sample_seconds=10,
            min_window_seconds=40,
        )
    )
    start = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    samples = [start + timedelta(seconds=i * 10) for i in range(4)]

    windows = predictor._windows_from_samples(
        loc=_location(),
        sample_times_utc=samples,
        iss_alt_deg=[5.0, 16.0, 18.0, 4.0],
        iss_az_deg=[200.0, 220.0, 250.0, 280.0],
        sun_alt_deg=[-15.0, -15.0, -15.0, -15.0],
        iss_sunlit=[True, True, True, True],
    )

    assert windows == []
