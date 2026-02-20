"""Command-line interface for ISS visibility prediction."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import requests

from iss_horizon.config import Config
from iss_horizon.geo import LocationResolver
from iss_horizon.mailer import send_mail
from iss_horizon.models import ISSHorizonError, VisibilityWindow
from iss_horizon.predictor import ISSPredictor
from iss_horizon.report import format_monthly_report, format_monthly_report_html, month_range_for


def _stars_text(stars: int) -> str:
    if not 1 <= stars <= 5:
        raise ValueError("stars must be in 1..5")
    return "★" * stars + "☆" * (5 - stars)


def _window_to_dict(window: VisibilityWindow) -> dict[str, object]:
    return {
        "start_local": window.start_local.isoformat(),
        "end_local": window.end_local.isoformat(),
        "peak_local": window.peak_local.isoformat(),
        "duration_seconds": int(window.duration.total_seconds()),
        "peak_elevation_deg": round(window.peak_elevation_deg, 2),
        "start_azimuth_deg": round(window.start_azimuth_deg, 2),
        "peak_azimuth_deg": round(window.peak_azimuth_deg, 2),
        "end_azimuth_deg": round(window.end_azimuth_deg, 2),
        "start_direction": window.start_direction,
        "peak_direction": window.peak_direction,
        "end_direction": window.end_direction,
        "visibility_stars": window.visibility_stars,
        "visibility_label": _stars_text(window.visibility_stars),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="iss-horizon")
    sub = parser.add_subparsers(dest="command", required=True)

    next_parser = sub.add_parser("next", help="Predict ISS windows for next N hours")
    next_parser.add_argument("--location", required=True)
    next_parser.add_argument("--hours", type=int, default=48)
    next_parser.add_argument("--min-elev", type=float)
    next_parser.add_argument("--twilight", type=float)
    next_parser.add_argument("--sample", type=int)
    next_parser.add_argument("--json", action="store_true")

    month_parser = sub.add_parser("month", help="Generate ISS windows for a month")
    month_parser.add_argument("--location", required=True)
    month_parser.add_argument("--year", type=int, required=True)
    month_parser.add_argument("--month", type=int, required=True)
    month_parser.add_argument("--min-elev", type=float)
    month_parser.add_argument("--twilight", type=float)
    month_parser.add_argument("--sample", type=int)
    month_parser.add_argument("--send", action="store_true")
    month_parser.add_argument("--email-to")
    month_parser.add_argument("--html-out")

    sub.add_parser("config", help="Print effective non-secret config")

    setup_parser = sub.add_parser("setup", help="Interactively create/update env configuration")
    setup_parser.add_argument("--env-file", default=".env")
    setup_parser.add_argument("--test-email", action="store_true")
    return parser


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        clean = value.strip().strip('"').strip("'")
        values[key.strip()] = clean
    return values


def _location_from_ip_payload(payload: Mapping[str, object]) -> str | None:
    city = str(payload.get("city", "")).strip()
    region = str(payload.get("region") or payload.get("regionName") or "").strip()
    country = str(payload.get("country_name") or payload.get("country") or "").strip()

    parts = [part for part in (city, region, country) if part]
    if len(parts) >= 2:
        return ", ".join(parts)
    return None


def _detect_location_from_ip() -> str | None:
    headers = {"User-Agent": "iss-horizon-setup/0.1"}
    endpoints = [
        "https://ipapi.co/json/",
        "https://ipwho.is/",
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=3)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                suggestion = _location_from_ip_payload(payload)
                if suggestion:
                    return suggestion
        except (requests.RequestException, ValueError):
            continue

    return None


def _prompt_text(label: str, default: str | None = None, *, secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    prompt = f"{label}{suffix}: "
    raw = getpass.getpass(prompt) if secret else input(prompt)

    value = raw.strip()
    if value:
        return value
    return default or ""


def _env_line(key: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'{key}="{escaped}"'


def _beautify_html(html: str) -> str:
    """Pretty-print compact HTML for file output readability."""

    void_tags = {"meta", "br", "hr", "img", "input", "link"}
    tokens = html.replace("><", ">\n<").splitlines()
    indent = 0
    pretty_lines: list[str] = []

    for token in tokens:
        line = token.strip()
        if line.startswith("</"):
            indent = max(indent - 1, 0)

        pretty_lines.append(f"{'  ' * indent}{line}")

        if not line.startswith("<") or line.startswith("</"):
            continue
        if line.startswith("<!") or line.endswith("/>"):
            continue

        tag_name = line[1:].split()[0].split(">")[0].strip("/").lower()
        if tag_name in void_tags:
            continue
        if "</" in line[1:]:
            continue

        indent += 1

    return "\n".join(pretty_lines) + "\n"


def _run_setup(args: argparse.Namespace) -> int:
    env_path = Path(args.env_file)
    existing = _parse_env_file(env_path)
    cfg = Config.from_env()

    location_default = existing.get("ISS_LOCATION")
    if not location_default:
        location_default = _detect_location_from_ip() or "Natal, RN, Brazil"

    location = _prompt_text("ISS location", location_default)
    report_to = _prompt_text("Report recipient email", existing.get("REPORT_TO", ""))
    user_agent = _prompt_text(
        "Nominatim user agent",
        existing.get("NOMINATIM_USER_AGENT", cfg.nominatim_user_agent),
    )

    min_elev = _prompt_text("Minimum elevation degrees", existing.get("ISS_MIN_ELEV_DEG", "12"))
    twilight = _prompt_text("Twilight threshold degrees", existing.get("ISS_TWILIGHT_DEG", "-10"))
    sample_seconds = _prompt_text(
        "Sample interval seconds", existing.get("ISS_SAMPLE_SECONDS", str(cfg.sample_seconds))
    )
    min_window = _prompt_text(
        "Minimum window seconds",
        existing.get("ISS_MIN_WINDOW_SECONDS", str(cfg.min_window_seconds)),
    )
    project_url = _prompt_text(
        "Project URL (used in report footer)",
        existing.get("ISS_PROJECT_URL", cfg.project_url),
    )

    smtp_host = _prompt_text("SMTP host", existing.get("SMTP_HOST", ""))
    smtp_port = _prompt_text("SMTP port", existing.get("SMTP_PORT", "465"))
    smtp_user = _prompt_text("SMTP user", existing.get("SMTP_USER", ""))
    smtp_password = _prompt_text(
        "SMTP password (leave empty to keep existing)",
        existing.get("SMTP_PASSWORD", ""),
        secret=True,
    )
    smtp_from = _prompt_text(
        "SMTP from address",
        existing.get("SMTP_FROM", smtp_user or "iss-bot@example.com"),
    )
    smtp_tls_mode = _prompt_text(
        "SMTP TLS mode (ssl/starttls)",
        existing.get("SMTP_TLS_MODE", "ssl"),
    )

    resolver = LocationResolver(user_agent=user_agent)
    resolved = resolver.resolve(location)
    print(
        "Resolved location: "
        f"{resolved.resolved_name} ({resolved.latitude:.4f}, {resolved.longitude:.4f})"
    )

    env_lines = [
        "# Generated by: iss-horizon setup",
        "# Keep this file private (contains credentials).",
        "",
        _env_line("ISS_LOCATION", location),
        _env_line("REPORT_TO", report_to),
        "",
        _env_line("ISS_TLE_URL", existing.get("ISS_TLE_URL", cfg.tle_url)),
        _env_line("ISS_TLE_NAME", existing.get("ISS_TLE_NAME", cfg.tle_name)),
        _env_line("NOMINATIM_USER_AGENT", user_agent),
        _env_line("ISS_MIN_ELEV_DEG", min_elev),
        _env_line("ISS_TWILIGHT_DEG", twilight),
        _env_line("ISS_SAMPLE_SECONDS", sample_seconds),
        _env_line("ISS_MIN_WINDOW_SECONDS", min_window),
        _env_line("ISS_PROJECT_URL", project_url),
        "",
        _env_line("SMTP_HOST", smtp_host),
        _env_line("SMTP_PORT", smtp_port),
        _env_line("SMTP_USER", smtp_user),
        _env_line("SMTP_PASSWORD", smtp_password),
        _env_line("SMTP_FROM", smtp_from),
        _env_line("SMTP_TLS_MODE", smtp_tls_mode),
        "",
    ]

    env_path.write_text("\n".join(env_lines), encoding="utf-8")
    print(f"Wrote configuration to {env_path}")

    if args.test_email:
        if not report_to:
            raise ISSHorizonError("REPORT_TO must be set to send test email")
        send_mail(
            subject="ISS-Horizon setup test",
            body="This is a setup test email from ISS-Horizon.",
            to_addr=report_to,
        )
        print("SMTP test email sent successfully")

    print("Next step: load env vars and run 'iss-horizon next --location \"...\" --hours 48'.")
    return 0


def _config_with_overrides(base: Config, args: argparse.Namespace) -> Config:
    min_elev_deg = (
        args.min_elev if getattr(args, "min_elev", None) is not None else base.min_elev_deg
    )
    twilight_deg = (
        args.twilight if getattr(args, "twilight", None) is not None else base.twilight_deg
    )
    sample_seconds = (
        args.sample if getattr(args, "sample", None) is not None else base.sample_seconds
    )

    return Config(
        tle_url=base.tle_url,
        tle_name=base.tle_name,
        nominatim_user_agent=base.nominatim_user_agent,
        min_elev_deg=min_elev_deg,
        twilight_deg=twilight_deg,
        sample_seconds=sample_seconds,
        min_window_seconds=base.min_window_seconds,
        project_url=base.project_url,
    )


def _run_next(args: argparse.Namespace) -> int:
    base_config = Config.from_env()
    config = _config_with_overrides(base_config, args)
    resolver = LocationResolver(user_agent=config.nominatim_user_agent)
    loc = resolver.resolve(args.location)
    predictor = ISSPredictor(config=config)
    windows = predictor.visible_windows_next_hours(loc, args.hours)

    if args.json:
        payload = {
            "location": {
                "query": loc.query,
                "resolved_name": loc.resolved_name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "timezone": loc.timezone_name,
            },
            "count": len(windows),
            "windows": [_window_to_dict(window) for window in windows],
        }
        print(json.dumps(payload, indent=2))
        return 0

    month_label = datetime.now(loc.timezone).strftime("%Y-%m")
    print(
        format_monthly_report(
            loc,
            month_label,
            windows,
            min_elev_deg=config.min_elev_deg,
            twilight_deg=config.twilight_deg,
            sample_seconds=config.sample_seconds,
            min_window_seconds=config.min_window_seconds,
            project_url=config.project_url,
        )
    )
    return 0


def _run_month(args: argparse.Namespace) -> int:
    base_config = Config.from_env()
    config = _config_with_overrides(base_config, args)
    resolver = LocationResolver(user_agent=config.nominatim_user_agent)
    loc = resolver.resolve(args.location)

    month_range = month_range_for(loc.timezone, args.year, args.month)
    predictor = ISSPredictor(config=config)
    windows = predictor.visible_windows_between(
        loc,
        month_range.start_local.astimezone(UTC),
        month_range.end_local.astimezone(UTC),
    )

    month_label = f"{args.year:04d}-{args.month:02d}"
    report_text = format_monthly_report(
        loc,
        month_label,
        windows,
        min_elev_deg=config.min_elev_deg,
        twilight_deg=config.twilight_deg,
        sample_seconds=config.sample_seconds,
        min_window_seconds=config.min_window_seconds,
        project_url=config.project_url,
    )
    report_html = format_monthly_report_html(
        loc,
        month_label,
        windows,
        min_elev_deg=config.min_elev_deg,
        twilight_deg=config.twilight_deg,
        sample_seconds=config.sample_seconds,
        min_window_seconds=config.min_window_seconds,
        project_url=config.project_url,
    )
    print(report_text)

    if args.html_out:
        html_path = Path(args.html_out).expanduser()
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(_beautify_html(report_html), encoding="utf-8")
        print(f"HTML report written to {html_path}")

    if args.send:
        to_addr = args.email_to or os.getenv("REPORT_TO")
        if not to_addr:
            raise ISSHorizonError("Provide --email-to or set REPORT_TO for --send")
        send_mail(
            subject=f"ISS visibility report {month_label} - {loc.resolved_name}",
            body=report_text,
            to_addr=to_addr,
            html_body=report_html,
        )

    return 0


def _run_config() -> int:
    cfg = Config.from_env()
    data = {
        "ISS_TLE_URL": cfg.tle_url,
        "ISS_TLE_NAME": cfg.tle_name,
        "NOMINATIM_USER_AGENT": cfg.nominatim_user_agent,
        "ISS_MIN_ELEV_DEG": cfg.min_elev_deg,
        "ISS_TWILIGHT_DEG": cfg.twilight_deg,
        "ISS_SAMPLE_SECONDS": cfg.sample_seconds,
        "ISS_MIN_WINDOW_SECONDS": cfg.min_window_seconds,
        "ISS_PROJECT_URL": cfg.project_url or "unset",
        "SMTP_HOST": "set" if os.getenv("SMTP_HOST") else "unset",
        "SMTP_PORT": os.getenv("SMTP_PORT", "465"),
        "SMTP_USER": "set" if os.getenv("SMTP_USER") else "unset",
        "SMTP_PASSWORD": "set" if os.getenv("SMTP_PASSWORD") else "unset",
        "SMTP_FROM": os.getenv("SMTP_FROM", "(derived)"),
        "SMTP_TLS_MODE": os.getenv("SMTP_TLS_MODE", "(derived)"),
    }
    print(json.dumps(data, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run CLI entrypoint and return POSIX-like exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "next":
            return _run_next(args)
        if args.command == "month":
            return _run_month(args)
        if args.command == "config":
            return _run_config()
        if args.command == "setup":
            return _run_setup(args)
        parser.print_help(sys.stderr)
        return 2
    except ISSHorizonError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
