# ISS-Horizon v0.1.0

First public release of ISS-Horizon: a CLI-first Python project that predicts ISS pass windows and supports monthly email reporting.

## Highlights

- Location resolution from human-readable query to coordinates + IANA timezone.
- ISS visibility prediction with configurable constraints:
  - minimum elevation
  - local darkness threshold (twilight)
  - ISS sunlit condition
  - minimum window duration
- Directional output with azimuth and 16-point cardinal labels.
- Qualitative 1–5 visibility star rating per window.
- Monthly report generation:
  - plain-text grouped by local day
  - HTML report with readable layout and browser export (`--html-out`)
- Email delivery via SMTP:
  - multipart email (HTML + plain-text fallback)
  - monthly runner module for unattended execution
- Interactive setup command (`iss-horizon setup`) to create/update env configuration.
- Systemd service + timer files and Debian 12 LXC install script.
- CI/tooling baseline:
  - Ruff, mypy, pytest
  - pre-commit config
  - GitHub Actions workflow

## Notable operational improvements

- CelesTrak fetch hardening in restricted environments:
  - resilient endpoint handling
  - explicit HTTP headers
  - fallback behavior for ISS TLE retrieval

## CLI examples

```bash
iss-horizon next --location "Natal, RN, Brazil" --hours 48
iss-horizon month --location "Natal, RN, Brazil" --year 2026 --month 3 --html-out report.html
iss-horizon setup --env-file .env --test-email
```

## Limitations

- Predictions depend on TLE freshness and source availability.
- Local obstructions, weather, and light pollution are not modeled.

## Upgrade notes

- If you already have an env file, ensure these fields are set as needed:
  - `ISS_PROJECT_URL`
  - `ISS_TLE_URL` (recommended CelesTrak GP endpoint)

## Naming migration

- Product and CLI naming are standardized on ISS-Horizon / `iss-horizon`.
- Python package namespace is `iss_horizon`.
- Domain terms such as `VisibilityWindow` and `visibility_stars` remain unchanged by design.

## Thanks

If you find this project useful, consider supporting development via GitHub Sponsors / Open Collective / Patreon (see repository README and funding config).
