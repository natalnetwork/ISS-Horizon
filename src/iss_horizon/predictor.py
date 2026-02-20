"""ISS visibility prediction engine built on Skyfield."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from skyfield.api import EarthSatellite, Loader, Time, wgs84

from iss_horizon.config import Config
from iss_horizon.models import Location, PredictionError, VisibilityWindow
from iss_horizon.tle import fetch_tle

from .utils import az_to_cardinal, contiguous_true_spans


@dataclass
class ISSPredictor:
    """Predict visible ISS windows for a specific location and time range."""

    config: Config
    loader: Loader = Loader("~/.skyfield")

    def visible_windows_next_hours(self, loc: Location, hours: int) -> list[VisibilityWindow]:
        """Predict visible windows from now for a number of hours."""

        if hours <= 0:
            raise PredictionError("hours must be positive")
        start_utc = datetime.now(UTC)
        end_utc = start_utc + timedelta(hours=hours)
        return self.visible_windows_between(loc, start_utc, end_utc)

    def visible_windows_between(
        self, loc: Location, start_utc: datetime, end_utc: datetime
    ) -> list[VisibilityWindow]:
        """Predict visible windows between UTC timestamps."""

        if start_utc.tzinfo is None or end_utc.tzinfo is None:
            raise PredictionError("start_utc and end_utc must be timezone-aware")
        if end_utc <= start_utc:
            return []

        try:
            ts = self.loader.timescale()
            tle = fetch_tle(self.config.tle_name, self.config.tle_url)
            satellite = EarthSatellite(tle.line1, tle.line2, tle.name, ts)
            observer = wgs84.latlon(loc.latitude, loc.longitude)
            eph = self.loader("de421.bsp")
            earth = eph["earth"]
            sun = eph["sun"]

            t0 = ts.from_datetime(start_utc.astimezone(UTC))
            t1 = ts.from_datetime(end_utc.astimezone(UTC))
            event_times, event_types = satellite.find_events(
                observer,
                t0,
                t1,
                altitude_degrees=self.config.min_elev_deg,
            )

            rise_time: Time | None = None
            all_windows: list[VisibilityWindow] = []

            for event_time, event_type in zip(event_times, event_types, strict=True):
                if event_type == 0:
                    rise_time = event_time
                elif event_type == 2 and rise_time is not None:
                    pass_windows = self._predict_pass_windows(
                        loc=loc,
                        satellite=satellite,
                        observer=observer,
                        earth=earth,
                        sun=sun,
                        eph=eph,
                        ts=ts,
                        rise_time=rise_time,
                        set_time=event_time,
                    )
                    all_windows.extend(pass_windows)
                    rise_time = None

            return sorted(all_windows, key=lambda item: item.start_local)
        except Exception as exc:
            raise PredictionError(f"Failed to predict ISS visibility: {exc}") from exc

    def _predict_pass_windows(
        self,
        *,
        loc: Location,
        satellite: EarthSatellite,
        observer: Any,
        earth: Any,
        sun: Any,
        eph: Any,
        ts: Any,
        rise_time: Time,
        set_time: Time,
    ) -> list[VisibilityWindow]:
        """Predict visible segments within a single pass using fixed interval samples."""

        rise_dt = self._single_utc_datetime(rise_time)
        set_dt = self._single_utc_datetime(set_time)

        samples_utc: list[datetime] = []
        cursor = rise_dt
        step = timedelta(seconds=self.config.sample_seconds)
        while cursor <= set_dt:
            samples_utc.append(cursor)
            cursor += step
        if samples_utc[-1] != set_dt:
            samples_utc.append(set_dt)

        sample_times = ts.from_datetimes(samples_utc)

        topocentric = (satellite - observer).at(sample_times)
        iss_alt, iss_az, _ = topocentric.altaz()
        sun_alt, _, _ = (earth + observer).at(sample_times).observe(sun).apparent().altaz()
        iss_sunlit = satellite.at(sample_times).is_sunlit(eph)

        return self._windows_from_samples(
            loc=loc,
            sample_times_utc=samples_utc,
            iss_alt_deg=[float(v) for v in iss_alt.degrees],
            iss_az_deg=[float(v) for v in iss_az.degrees],
            sun_alt_deg=[float(v) for v in sun_alt.degrees],
            iss_sunlit=[bool(v) for v in iss_sunlit],
        )

    def _windows_from_samples(
        self,
        *,
        loc: Location,
        sample_times_utc: Sequence[datetime],
        iss_alt_deg: Sequence[float],
        iss_az_deg: Sequence[float],
        sun_alt_deg: Sequence[float],
        iss_sunlit: Sequence[bool],
    ) -> list[VisibilityWindow]:
        """Construct visibility windows from sampled pass arrays."""

        n = len(sample_times_utc)
        if not (n == len(iss_alt_deg) == len(iss_az_deg) == len(sun_alt_deg) == len(iss_sunlit)):
            raise PredictionError("Sample arrays must have the same length")
        if n == 0:
            return []

        mask = [
            (iss_alt_deg[i] >= self.config.min_elev_deg)
            and (sun_alt_deg[i] <= self.config.twilight_deg)
            and iss_sunlit[i]
            for i in range(n)
        ]

        windows: list[VisibilityWindow] = []
        for start_idx, end_idx in contiguous_true_spans(mask):
            start_utc = sample_times_utc[start_idx]
            end_utc = sample_times_utc[end_idx]
            duration = end_utc - start_utc
            if duration.total_seconds() < self.config.min_window_seconds:
                continue

            span_indices = range(start_idx, end_idx + 1)
            peak_idx = max(span_indices, key=lambda idx: iss_alt_deg[idx])

            start_local = start_utc.astimezone(loc.timezone)
            end_local = end_utc.astimezone(loc.timezone)
            peak_local = sample_times_utc[peak_idx].astimezone(loc.timezone)

            start_az = iss_az_deg[start_idx]
            peak_az = iss_az_deg[peak_idx]
            end_az = iss_az_deg[end_idx]

            windows.append(
                VisibilityWindow(
                    start_local=start_local,
                    end_local=end_local,
                    peak_local=peak_local,
                    duration=duration,
                    peak_elevation_deg=iss_alt_deg[peak_idx],
                    start_azimuth_deg=start_az,
                    peak_azimuth_deg=peak_az,
                    end_azimuth_deg=end_az,
                    start_direction=az_to_cardinal(start_az),
                    peak_direction=az_to_cardinal(peak_az),
                    end_direction=az_to_cardinal(end_az),
                    visibility_stars=self._visibility_stars(
                        peak_elevation_deg=iss_alt_deg[peak_idx],
                        duration_seconds=duration.total_seconds(),
                    ),
                )
            )

        return windows

    @staticmethod
    def _single_utc_datetime(time_value: Time) -> datetime:
        """Convert a Skyfield time object to a single timezone-aware UTC datetime."""

        raw_value: Any = time_value.utc_datetime()
        if isinstance(raw_value, datetime):
            dt_value = raw_value
        elif isinstance(raw_value, Sequence):
            if len(raw_value) != 1:
                raise PredictionError("Expected a single event time")
            first_item = raw_value[0]
            if not isinstance(first_item, datetime):
                raise PredictionError("Unsupported event time value")
            dt_value = first_item
        else:
            raise PredictionError("Unsupported event time representation")

        if dt_value.tzinfo is None:
            return dt_value.replace(tzinfo=UTC)
        return dt_value.astimezone(UTC)

    @staticmethod
    def _visibility_stars(peak_elevation_deg: float, duration_seconds: float) -> int:
        """Compute a qualitative 1..5 visibility score from peak elevation and duration."""

        score = 1

        if peak_elevation_deg >= 20:
            score += 1
        if peak_elevation_deg >= 40:
            score += 1
        if peak_elevation_deg >= 65:
            score += 1
        if duration_seconds >= 120:
            score += 1

        return max(1, min(score, 5))
