"""Team notifications. Email is sent only when EMAIL_HOST is configured."""
import logging

from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


def notify_team(subject: str, body: str, reply_to: str | None = None) -> bool:
    """Returns True if an email was sent. Never raises: the request is already stored in the database."""
    if not settings.EMAIL_HOST:
        return False
    try:
        EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.TEAM_EMAIL],
            reply_to=[reply_to] if reply_to else None,
        ).send(fail_silently=False)
    except Exception:  # noqa: BLE001 - email trouble must not fail a visitor's request
        logger.exception('Could not email the team: %s', subject)
        return False
    return True
