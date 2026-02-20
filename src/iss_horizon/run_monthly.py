"""Monthly runner module for systemd timer execution."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from iss_horizon.config import Config
from iss_horizon.geo import LocationResolver
from iss_horizon.mailer import send_mail
from iss_horizon.models import ISSHorizonError
from iss_horizon.predictor import ISSPredictor
from iss_horizon.report import format_monthly_report, format_monthly_report_html, month_range_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    """Run monthly report generation and email dispatch for next local month."""

    location_query = os.getenv("ISS_LOCATION", "").strip()
    report_to = os.getenv("REPORT_TO", "").strip()
    if not location_query:
        raise ISSHorizonError("ISS_LOCATION environment variable is required")
    if not report_to:
        raise ISSHorizonError("REPORT_TO environment variable is required")

    config = Config.from_env()
    resolver = LocationResolver(user_agent=config.nominatim_user_agent)
    loc = resolver.resolve(location_query)

    now_local = datetime.now(loc.timezone)
    if now_local.month == 12:
        year, month = now_local.year + 1, 1
    else:
        year, month = now_local.year, now_local.month + 1

    month_range = month_range_for(loc.timezone, year, month)
    predictor = ISSPredictor(config=config)
    windows = predictor.visible_windows_between(
        loc,
        month_range.start_local.astimezone(UTC),
        month_range.end_local.astimezone(UTC),
    )

    month_label = f"{year:04d}-{month:02d}"
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

    subject = f"ISS visibility report {month_label} - {loc.resolved_name}"
    send_mail(subject=subject, body=report_text, to_addr=report_to, html_body=report_html)
    logger.info(
        "Monthly ISS report sent to %s for %s (%d windows)",
        report_to,
        month_label,
        len(windows),
    )


def main() -> int:
    """Run monthly workflow with stable exit code handling."""

    try:
        run()
        return 0
    except ISSHorizonError as exc:
        logger.error("Expected failure: %s", exc)
        return 1
    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected failure: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
