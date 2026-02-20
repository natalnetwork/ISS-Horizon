"""Unit tests for IP-based setup location suggestion."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from iss_horizon.cli import _detect_location_from_ip, _location_from_ip_payload


def test_location_from_ip_payload_ipapi_style() -> None:
    payload = {
        "city": "Natal",
        "region": "Rio Grande do Norte",
        "country_name": "Brazil",
    }

    assert _location_from_ip_payload(payload) == "Natal, Rio Grande do Norte, Brazil"


def test_location_from_ip_payload_requires_at_least_two_parts() -> None:
    payload = {
        "city": "",
        "region": "",
        "country_name": "Brazil",
    }

    assert _location_from_ip_payload(payload) is None


@patch("iss_horizon.cli.requests.get")
def test_detect_location_from_ip_first_provider_success(mock_get: MagicMock) -> None:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "city": "Recife",
        "region": "Pernambuco",
        "country_name": "Brazil",
    }
    mock_get.return_value = response

    assert _detect_location_from_ip() == "Recife, Pernambuco, Brazil"


@patch("iss_horizon.cli.requests.get")
def test_detect_location_from_ip_falls_back_to_second_provider(mock_get: MagicMock) -> None:
    first_error = requests.RequestException("primary provider unavailable")

    second_response = MagicMock()
    second_response.raise_for_status.return_value = None
    second_response.json.return_value = {
        "city": "Curitiba",
        "region": "Parana",
        "country": "Brazil",
    }

    mock_get.side_effect = [first_error, second_response]

    assert _detect_location_from_ip() == "Curitiba, Parana, Brazil"


@patch("iss_horizon.cli.requests.get")
def test_detect_location_from_ip_returns_none_if_no_provider_works(mock_get: MagicMock) -> None:
    mock_get.side_effect = requests.RequestException("all providers unavailable")

    assert _detect_location_from_ip() is None
