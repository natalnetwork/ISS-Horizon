"""Unit tests for monthly report formatting."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from iss_horizon.models import Location, VisibilityWindow
from iss_horizon.report import format_monthly_report, format_monthly_report_html, month_range_for


def _loc() -> Location:
    tz = ZoneInfo("America/Fortaleza")
    return Location(
        query="Natal, RN, Brazil",
        resolved_name="Natal, Rio Grande do Norte, Brazil",
        latitude=-5.795,
        longitude=-35.208,
        timezone_name="America/Fortaleza",
        timezone=tz,
    )


def _window(day: int, start_h: int, peak_h: int, end_h: int) -> VisibilityWindow:
    tz = ZoneInfo("America/Fortaleza")
    return VisibilityWindow(
        start_local=datetime(2026, 3, day, start_h, 0, 0, tzinfo=tz),
        peak_local=datetime(2026, 3, day, peak_h, 0, 30, tzinfo=tz),
        end_local=datetime(2026, 3, day, end_h, 1, 0, tzinfo=tz),
        duration=timedelta(minutes=1, seconds=0),
        peak_elevation_deg=42.3,
        start_azimuth_deg=250.1,
        peak_azimuth_deg=270.5,
        end_azimuth_deg=290.3,
        start_direction="WSW",
        peak_direction="W",
        end_direction="WNW",
    )


def test_month_range_for_regular_month() -> None:
    rng = month_range_for(ZoneInfo("UTC"), 2026, 3)
    assert rng.start_local.isoformat() == "2026-03-01T00:00:00+00:00"
    assert rng.end_local.isoformat() == "2026-04-01T00:00:00+00:00"


def test_month_range_for_december_rollover() -> None:
    rng = month_range_for(ZoneInfo("UTC"), 2026, 12)
    assert rng.end_local.isoformat() == "2027-01-01T00:00:00+00:00"


def test_report_groups_by_day() -> None:
    report = format_monthly_report(
        _loc(),
        "2026-03",
        [
            _window(day=2, start_h=19, peak_h=19, end_h=19),
            _window(day=2, start_h=21, peak_h=21, end_h=21),
            _window(day=3, start_h=20, peak_h=20, end_h=20),
        ],
    )

    assert "2026-03-02" in report
    assert "2026-03-03" in report
    assert report.count("2026-03-02") == 1
    assert report.count("->") == 3
    assert "peak 42.3°" in report
    assert "visibility ★☆☆☆☆" in report


def test_report_empty_message() -> None:
    report = format_monthly_report(_loc(), "2026-03", [])
    assert "No ISS windows found" in report
    assert "minimum elevation" in report.lower()


def test_html_report_contains_table_and_stars() -> None:
    html = format_monthly_report_html(
        _loc(),
        "2026-03",
        [_window(day=2, start_h=19, peak_h=19, end_h=19)],
    )
    assert "<table" in html
    assert "visibility" in html.lower()
    assert "★☆☆☆☆" in html


def test_html_report_empty_message() -> None:
    html = format_monthly_report_html(_loc(), "2026-03", [])
    assert "No ISS windows found" in html
    assert "<html" in html.lower()


def test_report_includes_generated_timestamp_when_provided() -> None:
    tz = ZoneInfo("America/Fortaleza")
    generated_at = datetime(2026, 2, 20, 10, 15, 0, tzinfo=tz)

    text_report = format_monthly_report(
        _loc(),
        "2026-03",
        [_window(day=2, start_h=19, peak_h=19, end_h=19)],
        generated_at=generated_at,
    )
    html_report = format_monthly_report_html(
        _loc(),
        "2026-03",
        [_window(day=2, start_h=19, peak_h=19, end_h=19)],
        generated_at=generated_at,
    )

    assert "Generated: 2026-02-20 10:15:00 -03" in text_report
    assert "Generated: 2026-02-20 10:15:00 -03" in html_report


def test_report_includes_settings_when_provided() -> None:
    text_report = format_monthly_report(
        _loc(),
        "2026-03",
        [_window(day=2, start_h=19, peak_h=19, end_h=19)],
        min_elev_deg=12.0,
        twilight_deg=-10.0,
        sample_seconds=10,
        min_window_seconds=40,
    )
    html_report = format_monthly_report_html(
        _loc(),
        "2026-03",
        [_window(day=2, start_h=19, peak_h=19, end_h=19)],
        min_elev_deg=12.0,
        twilight_deg=-10.0,
        sample_seconds=10,
        min_window_seconds=40,
    )

    expected = "min_elev=12.0°, twilight=-10.0°, sample=10s, min_window=40s"
    assert f"Settings: {expected}" in text_report
    assert f"Settings: {expected}" in html_report


def test_report_includes_project_url_when_provided() -> None:
    project_url = "https://github.com/example/ISS-Horizon"
    text_report = format_monthly_report(
        _loc(),
        "2026-03",
        [_window(day=2, start_h=19, peak_h=19, end_h=19)],
        project_url=project_url,
    )
    html_report = format_monthly_report_html(
        _loc(),
        "2026-03",
        [_window(day=2, start_h=19, peak_h=19, end_h=19)],
        project_url=project_url,
    )

    assert f"Project: {project_url}" in text_report
    assert f"href='{project_url}'" in html_report
