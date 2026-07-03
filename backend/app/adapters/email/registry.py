from __future__ import annotations

from app.adapters.email.interfaces import EmailSender
from app.adapters.email.resend_adapter import ResendEmailSender
from app.adapters.email.sendgrid_adapter import SendGridEmailSender
from app.adapters.email.ses_adapter import SesEmailSender
from app.adapters.email.smtp_adapter import SmtpEmailSender
from app.core.config import Settings, get_settings
from app.core.exceptions import ProviderError


def get_email_sender(settings: Settings | None = None) -> EmailSender:
    settings = settings or get_settings()
    match settings.EMAIL_PROVIDER:
        case "smtp":
            if not settings.SMTP_HOST:
                raise ProviderError("SMTP_HOST is not configured.")
            return SmtpEmailSender(
                settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USERNAME,
                settings.SMTP_PASSWORD.get_secret_value() if settings.SMTP_PASSWORD else None,
            )
        case "resend":
            if not settings.RESEND_API_KEY:
                raise ProviderError("RESEND_API_KEY is not configured.")
            return ResendEmailSender(settings.RESEND_API_KEY.get_secret_value())
        case "sendgrid":
            if not settings.SENDGRID_API_KEY:
                raise ProviderError("SENDGRID_API_KEY is not configured.")
            return SendGridEmailSender(settings.SENDGRID_API_KEY.get_secret_value())
        case "ses":
            if not settings.AWS_SES_REGION:
                raise ProviderError("AWS_SES_REGION is not configured.")
            return SesEmailSender(settings.AWS_SES_REGION)
        case _:
            raise ProviderError(f"Unknown email provider '{settings.EMAIL_PROVIDER}'.")
