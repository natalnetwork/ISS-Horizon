"""Utility functions for direction mapping and boolean span extraction."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta


def az_to_cardinal(az_deg: float, points: int = 16) -> str:
    """Convert azimuth in degrees to a compass direction label.

    Args:
        az_deg: Azimuth degrees where 0 is North and values increase clockwise.
        points: Compass resolution. Supported values are 4, 8, and 16.

    Returns:
        Compass label for the given azimuth.

    Raises:
        ValueError: If `points` is unsupported.
    """

    labels_map = {
        4: ["N", "E", "S", "W"],
        8: ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
        16: [
            "N",
            "NNE",
            "NE",
            "ENE",
            "E",
            "ESE",
            "SE",
            "SSE",
            "S",
            "SSW",
            "SW",
            "WSW",
            "W",
            "WNW",
            "NW",
            "NNW",
        ],
    }
    labels = labels_map.get(points)
    if labels is None:
        raise ValueError("points must be one of: 4, 8, 16")

    normalized = az_deg % 360.0
    bucket_size = 360.0 / points
    index = int((normalized + bucket_size / 2.0) // bucket_size) % points
    return labels[index]


def contiguous_true_spans(mask: Sequence[bool]) -> list[tuple[int, int]]:
    """Return inclusive index spans where mask values are contiguous True.

    Example:
        [False, True, True, False, True] -> [(1, 2), (4, 4)]
    """

    spans: list[tuple[int, int]] = []
    start: int | None = None

    for index, value in enumerate(mask):
        if value and start is None:
            start = index
        elif not value and start is not None:
            spans.append((start, index - 1))
            start = None

    if start is not None:
        spans.append((start, len(mask) - 1))

    return spans


def format_duration(duration: timedelta) -> str:
    """Format a timedelta as compact mm:ss or h:mm:ss."""

    total_seconds = int(duration.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def visibility_stars(peak_elevation_deg: float, duration_seconds: float) -> int:
    """Compute a qualitative 1..5 visibility score from peak elevation and duration.

    The score starts at 1 and increases with better geometry and longer visibility,
    capped at 5 stars.
    """

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


def stars_text(stars: int) -> str:
    """Return a fixed-width 5-star string representation."""

    if not 1 <= stars <= 5:
        raise ValueError("stars must be in 1..5")
    return "★" * stars + "☆" * (5 - stars)
