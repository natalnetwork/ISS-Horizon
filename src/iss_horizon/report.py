"""Monthly report range and formatting utilities."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from iss_horizon.models import Location, MonthRange, VisibilityWindow

from .utils import format_duration


def _stars_text(stars: int) -> str:
    if not 1 <= stars <= 5:
        raise ValueError("stars must be in 1..5")
    return "★" * stars + "☆" * (5 - stars)


def _group_windows_by_day(windows: list[VisibilityWindow]) -> dict[str, list[VisibilityWindow]]:
    by_day: dict[str, list[VisibilityWindow]] = defaultdict(list)
    for window in sorted(windows, key=lambda item: item.start_local):
        by_day[window.start_local.date().isoformat()].append(window)
    return by_day


def _generated_label(loc: Location, generated_at: datetime | None = None) -> str:
    timestamp = generated_at or datetime.now(loc.timezone)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=loc.timezone)
    else:
        timestamp = timestamp.astimezone(loc.timezone)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")


def _settings_label(
    *,
    min_elev_deg: float | None,
    twilight_deg: float | None,
    sample_seconds: int | None,
    min_window_seconds: int | None,
) -> str | None:
    if (
        min_elev_deg is None
        or twilight_deg is None
        or sample_seconds is None
        or min_window_seconds is None
    ):
        return None
    return (
        f"min_elev={min_elev_deg:.1f}°, twilight={twilight_deg:.1f}°, "
        f"sample={sample_seconds}s, min_window={min_window_seconds}s"
    )


def month_range_for(tz: ZoneInfo, year: int, month: int) -> MonthRange:
    """Return timezone-aware local month boundaries [start, end)."""

    if not 1 <= month <= 12:
        raise ValueError("month must be in 1..12")

    start_local = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    if month == 12:
        end_local = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
    else:
        end_local = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=tz)

    return MonthRange(start_local=start_local, end_local=end_local)


def format_monthly_report(
    loc: Location,
    month_label: str,
    windows: list[VisibilityWindow],
    *,
    generated_at: datetime | None = None,
    min_elev_deg: float | None = None,
    twilight_deg: float | None = None,
    sample_seconds: int | None = None,
    min_window_seconds: int | None = None,
    project_url: str | None = None,
) -> str:
    """Format a plain-text monthly ISS visibility report grouped by local day."""

    settings = _settings_label(
        min_elev_deg=min_elev_deg,
        twilight_deg=twilight_deg,
        sample_seconds=sample_seconds,
        min_window_seconds=min_window_seconds,
    )
    header = [
        f"ISS visibility report for {loc.resolved_name}",
        f"Month: {month_label}",
        f"Timezone: {loc.timezone_name}",
        f"Generated: {_generated_label(loc, generated_at)}",
        *([f"Settings: {settings}"] if settings else []),
        *([f"Project: {project_url}"] if project_url else []),
        "",
    ]

    if not windows:
        return "\n".join(
            [
                *header,
                "No ISS windows found for this period.",
                "Check minimum elevation, twilight threshold, and window duration settings.",
            ]
        )

    by_day = _group_windows_by_day(windows)

    lines = header
    for day in sorted(by_day):
        lines.append(day)
        for item in by_day[day]:
            start = item.start_local.strftime("%H:%M:%S")
            end = item.end_local.strftime("%H:%M:%S")
            peak_time = item.peak_local.strftime("%H:%M:%S")
            duration = format_duration(item.duration)
            lines.append(
                "  "
                f"{start} -> {end} ({duration}) | "
                f"visibility {_stars_text(item.visibility_stars)} | "
                f"start {item.start_azimuth_deg:.1f}° {item.start_direction} | "
                "peak "
                f"{item.peak_elevation_deg:.1f}° @ {item.peak_azimuth_deg:.1f}° "
                f"{item.peak_direction} "
                f"at {peak_time} | "
                f"end {item.end_azimuth_deg:.1f}° {item.end_direction}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def format_monthly_report_html(
    loc: Location,
    month_label: str,
    windows: list[VisibilityWindow],
    *,
    generated_at: datetime | None = None,
    min_elev_deg: float | None = None,
    twilight_deg: float | None = None,
    sample_seconds: int | None = None,
    min_window_seconds: int | None = None,
    project_url: str | None = None,
) -> str:
    """Format an HTML monthly ISS visibility report with a plain email-friendly layout."""

    title = f"ISS visibility report for {loc.resolved_name}"
    escaped_title = escape(title)
    escaped_month = escape(month_label)
    escaped_tz = escape(loc.timezone_name)
    generated_label = escape(_generated_label(loc, generated_at))
    settings = _settings_label(
        min_elev_deg=min_elev_deg,
        twilight_deg=twilight_deg,
        sample_seconds=sample_seconds,
        min_window_seconds=min_window_seconds,
    )
    escaped_settings = escape(settings) if settings else None
    escaped_project_url = escape(project_url) if project_url else None
    body_style = (
        "body{font-family:Arial,sans-serif;color:#1f2937;margin:0;"
        "padding:24px;background:#f8fafc;}"
    )
    main_empty_style = (
        "main{max-width:920px;margin:0 auto;background:#ffffff;"
        "padding:20px;border:1px solid #e5e7eb;}"
    )
    main_style = (
        "main{max-width:980px;margin:0 auto;background:#ffffff;"
        "padding:20px;border:1px solid #e5e7eb;}"
    )
    common_style = (
        "h1{font-size:20px;margin:0;}"
        "p{margin:4px 0 0;}"
        ".hero{background:#0f172a;color:#f8fafc;padding:16px;border-radius:8px;}"
        ".hero-meta{font-size:13px;color:#cbd5e1;margin-top:8px;}"
        ".pill{display:inline-block;background:#e2e8f0;color:#1e293b;padding:4px 8px;"
        "border-radius:999px;font-size:12px;margin-right:8px;margin-top:10px;}"
        ".day-title{font-size:16px;margin:0 0 8px;color:#111827;}"
        "table{width:100%;border-collapse:collapse;font-size:13px;}"
        "thead tr{background:#f3f4f6;text-align:left;}"
        "th{padding:8px;border:1px solid #e5e7eb;color:#374151;}"
        "td{padding:8px;border:1px solid #e5e7eb;vertical-align:top;}"
        ".stars{font-weight:700;color:#b45309;}"
        ".footer{font-size:12px;color:#6b7280;margin-top:16px;}"
    )

    if not windows:
        return (
            "<!doctype html>"
            "<html><head><meta charset='utf-8'>"
            "<style>"
            f"{body_style}"
            f"{main_empty_style}"
            f"{common_style}"
            "</style></head><body><main>"
            "<header class='hero'>"
            f"<h1>{escaped_title}</h1>"
            "<div class='hero-meta'>"
            f"Month: {escaped_month} · Timezone: {escaped_tz} · Generated: {generated_label}"
            "</div></header>"
            + (
                f"<p class='footer'>Settings: {escaped_settings}</p>" if escaped_settings else ""
            )
            + (
                "<p class='footer'>"
                f"Project: <a href='{escaped_project_url}'>{escaped_project_url}</a>"
                "</p>"
                if escaped_project_url
                else ""
            )
            +
            "<p style='margin-top:16px;'>No ISS windows found for this period.<br>"
            "Check minimum elevation, twilight threshold, and window duration settings.</p>"
            "</main></body></html>"
        )

    by_day = _group_windows_by_day(windows)
    sections: list[str] = []
    total_windows = sum(len(day_windows) for day_windows in by_day.values())

    for day in sorted(by_day):
        rows: list[str] = []
        for item in by_day[day]:
            start = item.start_local.strftime("%H:%M:%S")
            end = item.end_local.strftime("%H:%M:%S")
            peak_time = item.peak_local.strftime("%H:%M:%S")
            duration = format_duration(item.duration)
            rows.append(
                "<tr>"
                f"<td>{escape(start)} → {escape(end)}</td>"
                f"<td>{escape(duration)}</td>"
                f"<td><span class='stars'>{escape(_stars_text(item.visibility_stars))}</span></td>"
                f"<td>{item.start_azimuth_deg:.1f}° {escape(item.start_direction)}</td>"
                "<td>"
                f"{item.peak_elevation_deg:.1f}° @ {item.peak_azimuth_deg:.1f}° "
                f"{escape(item.peak_direction)} at {escape(peak_time)}"
                "</td>"
                f"<td>{item.end_azimuth_deg:.1f}° {escape(item.end_direction)}</td>"
                "</tr>"
            )

        sections.append(
            "<section style='margin-top:18px;'>"
            f"<h2 class='day-title'>{escape(day)}</h2>"
            "<table>"
            "<thead><tr>"
            "<th>Window</th>"
            "<th>Duration</th>"
            "<th>Visibility</th>"
            "<th>Start az/dir</th>"
            "<th>Peak</th>"
            "<th>End az/dir</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></section>"
        )

    return (
        "<!doctype html>"
        "<html><head><meta charset='utf-8'>"
        "<style>"
        f"{body_style}"
        f"{main_style}"
        f"{common_style}"
        "</style></head><body><main>"
        "<header class='hero'>"
        f"<h1>{escaped_title}</h1>"
        "<div class='hero-meta'>"
        f"Month: {escaped_month} · Timezone: {escaped_tz} · Generated: {generated_label}"
        "</div>"
        f"<span class='pill'>{total_windows} windows</span>"
        f"<span class='pill'>{len(by_day)} days</span>"
        "</header>"
        + "".join(sections)
        + (
            f"<p class='footer'>Settings: {escaped_settings}</p>" if escaped_settings else ""
        )
        + (
            "<p class='footer'>"
            f"Project: <a href='{escaped_project_url}'>{escaped_project_url}</a>"
            "</p>"
            if escaped_project_url
            else ""
        )
        + f"<p class='footer'>Generated by ISS-Horizon at {generated_label}</p>"
        + "</main></body></html>"
    )
