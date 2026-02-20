"""Configuration loading for ISS visibility prediction and reporting."""

from __future__ import annotations

import os
from dataclasses import dataclass

from iss_horizon.models import SMTPConfig


@dataclass(frozen=True)
class Config:
    """Application configuration with env-backed defaults."""

    tle_url: str = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
    tle_name: str = "ISS (ZARYA)"
    nominatim_user_agent: str = "iss-horizon/0.1 (contact: set-your-email)"
    min_elev_deg: float = 12.0
    twilight_deg: float = -10.0
    sample_seconds: int = 10
    min_window_seconds: int = 40
    project_url: str = ""

    @classmethod
    def from_env(cls) -> Config:
        """Load config using environment variables with safe defaults."""

        return cls(
            tle_url=os.getenv("ISS_TLE_URL", cls.tle_url),
            tle_name=os.getenv("ISS_TLE_NAME", cls.tle_name),
            nominatim_user_agent=os.getenv("NOMINATIM_USER_AGENT", cls.nominatim_user_agent),
            min_elev_deg=float(os.getenv("ISS_MIN_ELEV_DEG", str(cls.min_elev_deg))),
            twilight_deg=float(os.getenv("ISS_TWILIGHT_DEG", str(cls.twilight_deg))),
            sample_seconds=int(os.getenv("ISS_SAMPLE_SECONDS", str(cls.sample_seconds))),
            min_window_seconds=int(
                os.getenv("ISS_MIN_WINDOW_SECONDS", str(cls.min_window_seconds))
            ),
            project_url=os.getenv("ISS_PROJECT_URL", cls.project_url).strip(),
        )


def smtp_config_from_env() -> SMTPConfig:
    """Build SMTP configuration from environment variables."""

    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "465"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM") or (user or "iss-horizon@localhost")
    tls_mode = (os.getenv("SMTP_TLS_MODE") or ("ssl" if port == 465 else "starttls")).lower()

    return SMTPConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        from_addr=from_addr,
        tls_mode=tls_mode,
    )
