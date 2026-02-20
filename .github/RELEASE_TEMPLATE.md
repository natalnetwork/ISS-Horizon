# ISS-Horizon vX.Y.Z

Short summary of the release in 1-2 sentences.

## Highlights

- 
- 
- 

## Changes

### Added

- 

### Changed

- 

### Fixed

- 

## Operational notes

- 

## Upgrade notes

- `pyproject.toml` version: `X.Y.Z`
- Environment/config changes (if any):
  - 

## CLI examples

```bash
iss-horizon next --location "Natal, RN, Brazil" --hours 48
iss-horizon month --location "Natal, RN, Brazil" --year 2026 --month 3 --html-out report.html
iss-horizon setup --env-file .env --test-email
```

## Limitations

- Predictions depend on TLE freshness/source availability.
- Local obstructions, weather, and light pollution are not modeled.

## Security reminder

- Never commit `.env` files or SMTP credentials.
- For unattended deployments, use `/etc/iss-horizon/iss-horizon.env`.
