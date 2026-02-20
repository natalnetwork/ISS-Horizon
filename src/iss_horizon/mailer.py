"""SMTP mailer for monthly ISS reports."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from iss_horizon.config import smtp_config_from_env
from iss_horizon.models import EmailSendError, SMTPConfig


def send_mail(
    subject: str,
    body: str,
    to_addr: str,
    *,
    html_body: str | None = None,
    smtp_config: SMTPConfig | None = None,
) -> None:
    """Send an email report using SMTP configuration.

    Args:
        subject: Message subject.
        body: Plain text body.
        to_addr: Recipient address.
        html_body: Optional HTML body for multipart/alternative messages.
        smtp_config: Optional explicit SMTP config. If omitted, values are loaded from env.

    Raises:
        EmailSendError: If config is invalid or sending fails.
    """

    cfg = smtp_config or smtp_config_from_env()
    if not cfg.host:
        raise EmailSendError("SMTP_HOST is required")
    if cfg.tls_mode not in {"ssl", "starttls"}:
        raise EmailSendError("SMTP_TLS_MODE must be 'ssl' or 'starttls'")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.from_addr
    msg["To"] = to_addr
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        if cfg.tls_mode == "ssl":
            with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=30) as client:
                if cfg.user and cfg.password:
                    client.login(cfg.user, cfg.password)
                client.send_message(msg)
        else:
            with smtplib.SMTP(cfg.host, cfg.port, timeout=30) as client:
                client.ehlo()
                client.starttls()
                client.ehlo()
                if cfg.user and cfg.password:
                    client.login(cfg.user, cfg.password)
                client.send_message(msg)
    except Exception as exc:  # pragma: no cover - covered via mocks
        raise EmailSendError(f"Failed to send email to {to_addr}: {exc}") from exc
