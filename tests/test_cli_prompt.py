"""Unit tests for interactive CLI prompt behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from iss_horizon.cli import _prompt_text


@patch("iss_horizon.cli.getpass.getpass", return_value="")
def test_prompt_text_masks_secret_default(mock_getpass: MagicMock) -> None:
    value = _prompt_text("SMTP password", "super-secret", secret=True)

    assert value == "super-secret"
    mock_getpass.assert_called_once_with("SMTP password [********]: ")


@patch("iss_horizon.cli.getpass.getpass", return_value="new-secret")
def test_prompt_text_secret_returns_typed_value(mock_getpass: MagicMock) -> None:
    value = _prompt_text("SMTP password", "super-secret", secret=True)

    assert value == "new-secret"
    mock_getpass.assert_called_once_with("SMTP password [********]: ")
