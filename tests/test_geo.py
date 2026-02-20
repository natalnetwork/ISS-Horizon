"""Unit tests for location resolver with mocked providers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from iss_horizon.geo import LocationResolver
from iss_horizon.models import LocationResolutionError


@patch("iss_horizon.geo.TimezoneFinder")
@patch("iss_horizon.geo.Nominatim")
def test_resolve_success(nominatim_cls: MagicMock, timezonefinder_cls: MagicMock) -> None:
    geocoder = MagicMock()
    geocoder.geocode.return_value = SimpleNamespace(
        latitude=-5.79,
        longitude=-35.2,
        address="Natal, Rio Grande do Norte, Brazil",
    )
    nominatim_cls.return_value = geocoder

    finder = MagicMock()
    finder.timezone_at.return_value = "America/Fortaleza"
    timezonefinder_cls.return_value = finder

    resolver = LocationResolver(user_agent="iss-horizon-test")
    result = resolver.resolve("Natal, RN, Brazil")

    assert result.latitude == -5.79
    assert result.longitude == -35.2
    assert result.timezone_name == "America/Fortaleza"


@patch("iss_horizon.geo.TimezoneFinder")
@patch("iss_horizon.geo.Nominatim")
def test_resolve_not_found(nominatim_cls: MagicMock, timezonefinder_cls: MagicMock) -> None:
    geocoder = MagicMock()
    geocoder.geocode.return_value = None
    nominatim_cls.return_value = geocoder
    timezonefinder_cls.return_value = MagicMock()

    resolver = LocationResolver(user_agent="iss-horizon-test")
    with pytest.raises(LocationResolutionError, match="not found"):
        resolver.resolve("unknown")


@patch("iss_horizon.geo.TimezoneFinder")
@patch("iss_horizon.geo.Nominatim")
def test_resolve_timezone_failure(nominatim_cls: MagicMock, timezonefinder_cls: MagicMock) -> None:
    geocoder = MagicMock()
    geocoder.geocode.return_value = SimpleNamespace(latitude=1.0, longitude=2.0, address="X")
    nominatim_cls.return_value = geocoder

    finder = MagicMock()
    finder.timezone_at.return_value = None
    timezonefinder_cls.return_value = finder

    resolver = LocationResolver(user_agent="iss-horizon-test")
    with pytest.raises(LocationResolutionError, match="Timezone"):
        resolver.resolve("X")


@patch("iss_horizon.geo.TimezoneFinder")
@patch("iss_horizon.geo.Nominatim")
def test_resolve_uses_cache(nominatim_cls: MagicMock, timezonefinder_cls: MagicMock) -> None:
    geocoder = MagicMock()
    geocoder.geocode.return_value = SimpleNamespace(
        latitude=48.13,
        longitude=11.58,
        address="Munich, Bavaria, Germany",
    )
    nominatim_cls.return_value = geocoder

    finder = MagicMock()
    finder.timezone_at.return_value = "Europe/Berlin"
    timezonefinder_cls.return_value = finder

    resolver = LocationResolver(user_agent="iss-horizon-test")
    first = resolver.resolve("Munich")
    second = resolver.resolve("Munich")

    assert first == second
    geocoder.geocode.assert_called_once()
