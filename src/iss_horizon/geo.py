"""Location resolver using Nominatim and timezone lookup."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from iss_horizon.models import Location, LocationResolutionError


@dataclass
class LocationResolver:
    """Resolve human-readable locations into coordinates and timezone metadata."""

    user_agent: str
    _cache: dict[str, Location] = field(default_factory=dict)

    def resolve(self, query: str) -> Location:
        """Resolve a location query to immutable location data.

        Raises:
            LocationResolutionError: If geocoding or timezone mapping fails.
        """

        normalized_query = query.strip()
        if not normalized_query:
            raise LocationResolutionError("Location query must not be empty")

        if normalized_query in self._cache:
            return self._cache[normalized_query]

        geocoder = Nominatim(user_agent=self.user_agent)
        geocoded_raw: Any = geocoder.geocode(normalized_query, exactly_one=True)
        if inspect.isawaitable(geocoded_raw):
            raise LocationResolutionError("Async geocoding result is not supported")
        if geocoded_raw is None:
            raise LocationResolutionError(f"Location not found: {normalized_query}")

        lat_value = getattr(geocoded_raw, "latitude", None)
        lon_value = getattr(geocoded_raw, "longitude", None)
        address_value = getattr(geocoded_raw, "address", normalized_query)
        if lat_value is None or lon_value is None:
            raise LocationResolutionError("Geocoding response is missing coordinates")

        lat = float(lat_value)
        lon = float(lon_value)

        tz_finder = TimezoneFinder()
        tz_name = tz_finder.timezone_at(lng=lon, lat=lat)
        if tz_name is None:
            raise LocationResolutionError(
                f"Timezone could not be resolved for coordinates ({lat}, {lon})"
            )

        try:
            from zoneinfo import ZoneInfo

            zone = ZoneInfo(tz_name)
        except Exception as exc:
            raise LocationResolutionError(
                f"Invalid timezone '{tz_name}' for {normalized_query}"
            ) from exc

        result = Location(
            query=normalized_query,
            resolved_name=str(address_value),
            latitude=lat,
            longitude=lon,
            timezone_name=tz_name,
            timezone=zone,
        )
        self._cache[normalized_query] = result
        return result
