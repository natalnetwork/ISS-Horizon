"""Unit tests for SMTP mail sending."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from iss_horizon.mailer import send_mail
from iss_horizon.models import EmailSendError, SMTPConfig


def test_send_mail_ssl_success() -> None:
    cfg = SMTPConfig(
        host="smtp.example.com",
        port=465,
        user="u",
        password="p",
        from_addr="from@example.com",
        tls_mode="ssl",
    )

    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance

    with patch("smtplib.SMTP_SSL", return_value=smtp_instance):
        send_mail(
            "sub",
            "body",
            "to@example.com",
            html_body="<html><body><p>Hello</p></body></html>",
            smtp_config=cfg,
        )

    smtp_instance.login.assert_called_once_with("u", "p")
    smtp_instance.send_message.assert_called_once()
    sent_msg = smtp_instance.send_message.call_args.args[0]
    html_part = sent_msg.get_body(preferencelist=("html",))
    assert html_part is not None


def test_send_mail_starttls_success() -> None:
    cfg = SMTPConfig(
        host="smtp.example.com",
        port=587,
        user=None,
        password=None,
        from_addr="from@example.com",
        tls_mode="starttls",
    )

    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance

    with patch("smtplib.SMTP", return_value=smtp_instance):
        send_mail("sub", "body", "to@example.com", smtp_config=cfg)

    smtp_instance.starttls.assert_called_once()
    smtp_instance.send_message.assert_called_once()


def test_send_mail_rejects_missing_host() -> None:
    cfg = SMTPConfig(host="", port=465, user=None, password=None, from_addr="f@x", tls_mode="ssl")
    with pytest.raises(EmailSendError, match="SMTP_HOST"):
        send_mail("s", "b", "t@example.com", smtp_config=cfg)
