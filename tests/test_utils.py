"""Unit tests for utility helpers."""

from __future__ import annotations

import pytest

from iss_horizon.utils import az_to_cardinal, contiguous_true_spans, stars_text, visibility_stars


@pytest.mark.parametrize(
    ("azimuth", "expected"),
    [
        (0.0, "N"),
        (11.24, "N"),
        (11.25, "NNE"),
        (33.75, "NE"),
        (90.0, "E"),
        (180.0, "S"),
        (270.0, "W"),
        (348.75, "N"),
        (359.99, "N"),
        (-1.0, "N"),
        (721.0, "N"),
    ],
)
def test_az_to_cardinal_16_points(azimuth: float, expected: str) -> None:
    assert az_to_cardinal(azimuth) == expected


@pytest.mark.parametrize(
    ("azimuth", "points", "expected"),
    [
        (44.0, 4, "N"),
        (44.0, 8, "NE"),
    ],
)
def test_az_to_cardinal_supported_resolutions(azimuth: float, points: int, expected: str) -> None:
    assert az_to_cardinal(azimuth, points=points) == expected


def test_az_to_cardinal_invalid_resolution() -> None:
    with pytest.raises(ValueError, match="points"):
        az_to_cardinal(30.0, points=12)


@pytest.mark.parametrize(
    ("mask", "expected"),
    [
        ([], []),
        ([False, False], []),
        ([True], [(0, 0)]),
        ([True, True], [(0, 1)]),
        ([False, True, True, False, True], [(1, 2), (4, 4)]),
        ([True, False, True, False, True], [(0, 0), (2, 2), (4, 4)]),
        ([False, True, False], [(1, 1)]),
    ],
)
def test_contiguous_true_spans(mask: list[bool], expected: list[tuple[int, int]]) -> None:
    assert contiguous_true_spans(mask) == expected


@pytest.mark.parametrize(
    ("peak", "duration", "expected"),
    [
        (10.0, 30.0, 1),
        (25.0, 30.0, 2),
        (45.0, 30.0, 3),
        (70.0, 30.0, 4),
        (70.0, 240.0, 5),
    ],
)
def test_visibility_stars(peak: float, duration: float, expected: int) -> None:
    assert visibility_stars(peak, duration) == expected


def test_stars_text() -> None:
    assert stars_text(3) == "★★★☆☆"
