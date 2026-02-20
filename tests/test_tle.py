"""Unit tests for TLE fetching without network access."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from iss_horizon.models import TLEFetchError
from iss_horizon.tle import fetch_tle


@patch("iss_horizon.tle.requests.get")
def test_fetch_tle_success(get_mock: MagicMock) -> None:
    response = MagicMock()
    response.text = """ISS (ZARYA)
1 25544U 98067A   26051.50000000  .00010000  00000+0  18277-3 0  9991
2 25544  51.6417 200.0000 0005825 100.0000 300.0000 15.50000000000000
"""
    response.raise_for_status.return_value = None
    get_mock.return_value = response

    tle = fetch_tle("ISS (ZARYA)", "https://example.test/success.txt")

    assert tle.name == "ISS (ZARYA)"
    assert tle.line1.startswith("1 ")
    assert tle.line2.startswith("2 ")


@patch("iss_horizon.tle.requests.get")
def test_fetch_tle_not_found(get_mock: MagicMock) -> None:
    response = MagicMock()
    response.text = """OTHER SAT
1 00000U 00000A   26051.50000000  .00000000  00000+0  00000-0 0  9991
2 00000  00.0000 000.0000 0000000 000.0000 000.0000 01.00000000000000
"""
    response.raise_for_status.return_value = None
    get_mock.return_value = response

    with pytest.raises(TLEFetchError, match="not found"):
        fetch_tle("ISS (ZARYA)", "https://example.test/not-found.txt")


@patch("iss_horizon.tle.requests.get")
def test_fetch_tle_request_error(get_mock: MagicMock) -> None:
    get_mock.side_effect = requests.RequestException("boom")
    tle = fetch_tle("ISS (ZARYA)", "https://example.test/error.txt")
    assert tle.name == "ISS (ZARYA)"


@patch("iss_horizon.tle.requests.get")
def test_fetch_tle_request_error_non_iss_still_fails(get_mock: MagicMock) -> None:
    get_mock.side_effect = requests.RequestException("boom")
    with pytest.raises(TLEFetchError, match="Failed to fetch"):
        fetch_tle("NOT-ISS", "https://example.test/error-non-iss.txt")


@patch("iss_horizon.tle.requests.get")
def test_fetch_tle_fallback_from_stations_403_to_gp(get_mock: MagicMock) -> None:
    forbidden_response = MagicMock()
    forbidden_response.status_code = 403
    forbidden_error = requests.HTTPError("403", response=forbidden_response)

    first_response = MagicMock()
    first_response.raise_for_status.side_effect = forbidden_error

    second_response = MagicMock()
    second_response.raise_for_status.return_value = None
    second_response.text = """ISS (ZARYA)
1 25544U 98067A   26051.50000000  .00010000  00000+0  18277-3 0  9991
2 25544  51.6417 200.0000 0005825 100.0000 300.0000 15.50000000000000
"""

    get_mock.side_effect = [first_response, second_response]

    tle = fetch_tle("ISS (ZARYA)", "https://celestrak.org/NORAD/elements/stations.txt")

    assert tle.name == "ISS (ZARYA)"
    assert get_mock.call_count == 2
