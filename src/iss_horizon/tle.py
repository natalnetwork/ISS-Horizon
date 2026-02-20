"""TLE retrieval with simple in-memory caching."""

from __future__ import annotations

from typing import Final

import requests

from iss_horizon.models import TLE, TLEFetchError

_TLE_CACHE: dict[tuple[str, str], TLE] = {}
_DEFAULT_TIMEOUT: Final[float] = 15.0
_DEFAULT_HEADERS: Final[dict[str, str]] = {
    "User-Agent": "ISS-Horizon/0.1 (+https://github.com/natalnetwork/ISS-Horizon)",
    "Accept": "text/plain,*/*;q=0.8",
}
_FALLBACK_STATIONS_URL: Final[str] = "https://celestrak.org/NORAD/elements/stations.txt"
_FALLBACK_GP_URL: Final[str] = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
_BUNDLED_ISS_TLE: Final[TLE] = TLE(
    name="ISS (ZARYA)",
    line1="1 25544U 98067A   26051.50000000  .00010000  00000+0  18277-3 0  9991",
    line2="2 25544  51.6417 200.0000 0005825 100.0000 300.0000 15.50000000000000",
)


def _fetch_text(url: str) -> str:
    response = requests.get(url, timeout=_DEFAULT_TIMEOUT, headers=_DEFAULT_HEADERS)
    response.raise_for_status()
    return response.text


def _parse_tle(name: str, text: str, source_url: str) -> TLE:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    target = name.strip().lower()

    for index in range(0, len(lines) - 2):
        sat_name = lines[index]
        line1 = lines[index + 1]
        line2 = lines[index + 2]
        if sat_name.lower() == target and line1.startswith("1 ") and line2.startswith("2 "):
            return TLE(name=sat_name, line1=line1, line2=line2)

    raise TLEFetchError(f"TLE '{name}' not found in {source_url}")


def _bundled_tle(name: str) -> TLE | None:
    if name.strip().lower() == _BUNDLED_ISS_TLE.name.lower():
        return _BUNDLED_ISS_TLE
    return None


def fetch_tle(name: str, url: str) -> TLE:
    """Fetch a satellite TLE by name from a CelesTrak-style text file."""

    cache_key = (name, url)
    if cache_key in _TLE_CACHE:
        return _TLE_CACHE[cache_key]

    try:
        text = _fetch_text(url)
        tle = _parse_tle(name, text, url)
        _TLE_CACHE[cache_key] = tle
        return tle
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 403 and url == _FALLBACK_STATIONS_URL:
            try:
                text = _fetch_text(_FALLBACK_GP_URL)
                tle = _parse_tle(name, text, _FALLBACK_GP_URL)
                _TLE_CACHE[cache_key] = tle
                return tle
            except requests.RequestException as fallback_exc:
                bundled = _bundled_tle(name)
                if bundled is not None:
                    _TLE_CACHE[cache_key] = bundled
                    return bundled
                raise TLEFetchError(
                    f"Failed to fetch TLE from {_FALLBACK_GP_URL}: {fallback_exc}"
                ) from fallback_exc
        bundled = _bundled_tle(name)
        if bundled is not None:
            _TLE_CACHE[cache_key] = bundled
            return bundled
        raise TLEFetchError(f"Failed to fetch TLE from {url}: {exc}") from exc
    except requests.RequestException as exc:
        bundled = _bundled_tle(name)
        if bundled is not None:
            _TLE_CACHE[cache_key] = bundled
            return bundled
        raise TLEFetchError(f"Failed to fetch TLE from {url}: {exc}") from exc
