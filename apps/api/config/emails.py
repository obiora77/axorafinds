"""Transactional email for Axora Finds.

Every message is rendered from ``templates/emails/`` as both plain text and HTML.
Sending is best-effort: a broken mail server must never fail a visitor's request or a
staff action. When no SMTP host is configured, a console backend is used in development;
in production the send is refused with a clear, recorded error instead of silently
dropping the message into an in-memory outbox.

``email_status()`` reports the backend, the missing templates and the last error, so both
the staff dashboard and Django admin can show why a message did not arrive.
"""
from __future__ import annotations

import email.policy
import html
import logging
import re
import smtplib
import socket
import ssl
from decimal import Decimal
from email.message import EmailMessage as StdEmailMessage
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import get_template, render_to_string
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

_last_error: str | None = None

LOGO_CID = 'axora-finds-logo'
LOGO_PATH = Path(settings.BASE_DIR) / 'static' / 'img' / 'logo.png'

# Every sender in this module renders one of these templates in both formats.
EMAIL_TEMPLATES = (
    'welcome',
    'otp',
    'newsletter_welcome',
    'contact_received',
    'team_notification',
    'inspection_received',
    'inspection_confirmed',
    'inspection_rejected',
    'payment_verified',
    'listing_received',
    'listing_published',
    'listing_rejected',
    'review_received',
    'review_published',
    'test',
)


def last_email_error() -> str | None:
    """The most recent send failure, so a diagnostic screen can show the real cause."""
    return _last_error


@lru_cache(maxsize=1)
def _logo_bytes() -> bytes | None:
    """The white logo on transparent, embedded inline so it shows without a public URL."""
    try:
        return LOGO_PATH.read_bytes()
    except OSError:
        logger.warning('Email logo is missing at %s', LOGO_PATH)
        return None


class InlineLogoEmail(EmailMultiAlternatives):
    """A multipart/related message so the HTML can show the logo from a Content-ID.

    Django builds a multipart/mixed message when an attachment is present (alternative
    text + HTML, then the image). Re-typing the top level as multipart/related is exactly
    the structure mail clients expect for an inline image.
    """

    inline_logo = False

    def message(self, *, policy=email.policy.default):
        msg = super().message(policy=policy)
        if self.inline_logo and msg.get_content_type() == 'multipart/mixed':
            msg.set_type('multipart/related')
            msg.set_param('type', 'multipart/alternative')
        return msg


def _attach_logo(message: EmailMultiAlternatives, data: bytes) -> None:
    logo = StdEmailMessage()
    logo.set_content(
        data,
        maintype='image',
        subtype='png',
        disposition='inline',
        filename='logo.png',
    )
    logo['Content-ID'] = f'<{LOGO_CID}>'
    message.attach(logo)
    message.inline_logo = True


def email_enabled() -> bool:
    """True when the configured backend can actually deliver a message.

    Console, file and in-memory backends work without a mail server (used in development
    and tests). SMTP and any other backend need ``EMAIL_HOST``; without it we refuse to
    "send" rather than let a production deployment discard every message silently.
    """
    backend = (settings.EMAIL_BACKEND or '').lower()
    if any(marker in backend for marker in ('console', 'locmem', 'filebased')):
        return True
    if 'dummy' in backend:
        return False
    return bool(settings.EMAIL_HOST)


def _from_email() -> str:
    return settings.DEFAULT_FROM_EMAIL or settings.TEAM_EMAIL


def _money(value: Decimal | float | int) -> str:
    return f'N{Decimal(value):,.2f}'


def _site_url() -> str:
    return (settings.SITE_URL or '').rstrip('/')


def _recipients(to: str | Iterable[str]) -> list[str]:
    if isinstance(to, str):
        return [to.strip()] if to.strip() else []
    return [address.strip() for address in to if address and address.strip()]


def _reply_to(addresses: str | Iterable[str] | None) -> list[str]:
    if addresses is None:
        return _recipients(settings.TEAM_EMAIL)
    return _recipients(addresses)


def _html_to_text(markup: str) -> str:
    """Emergency plain-text fallback for a message whose .txt template is missing."""
    markup = re.sub(r'<(?:br|/p|/div|/tr|/h[1-6])\s*/?>', '\n', markup, flags=re.IGNORECASE)
    text = html.unescape(strip_tags(markup))
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return '\n'.join(line.strip() for line in text.splitlines()).strip()


def _render_parts(template: str, context: dict) -> tuple[str, str]:
    """Return (text, html). The HTML part is required; text falls back if it is absent."""
    html_body = render_to_string(f'emails/{template}.html', context)
    try:
        text_body = render_to_string(f'emails/{template}.txt', context)
    except TemplateDoesNotExist:
        logger.warning('Missing plain-text template emails/%s.txt; deriving it from HTML', template)
        text_body = _html_to_text(html_body)
    return text_body, html_body


def _smtp_guidance(exc: BaseException) -> str:
    """A short, actionable hint for the SMTP failures people actually hit."""
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return (
            'Gmail rejected the login. Turn on 2-Step Verification, create a new '
            '16-character App Password, and set EMAIL_HOST_USER to the full Gmail address.'
        )
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return (
            'The server refused the From address. DEFAULT_FROM_EMAIL must match the Gmail '
            'account in EMAIL_HOST_USER (or an alias that account is allowed to send as).'
        )
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return 'The server refused the recipient address.'
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        return (
            'The mail server closed the connection before accepting the message. Outbound '
            'SMTP is often blocked on home, office and mobile networks. Try port 465 with '
            'EMAIL_USE_SSL=1 and EMAIL_USE_TLS=0; if that also fails, turn off any VPN or '
            'antivirus mail shield, or use a mail provider that sends over HTTPS (port 443).'
        )
    if isinstance(exc, ssl.SSLError):
        return (
            'TLS negotiation failed. Use EMAIL_PORT=587 with EMAIL_USE_TLS=1, or '
            'EMAIL_PORT=465 with EMAIL_USE_SSL=1 (never both).'
        )
    if isinstance(exc, socket.gaierror):
        return 'The mail server name could not be resolved. Check EMAIL_HOST and your DNS.'
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return 'The mail server did not answer in time. Check the network or raise EMAIL_TIMEOUT.'
    if isinstance(exc, ConnectionRefusedError):
        return 'The connection was refused. The port is blocked or the host/port is wrong.'
    return ''


def _fail(message: str, *, raise_errors: bool, exc: BaseException | None = None) -> bool:
    global _last_error
    _last_error = message
    if exc is None:
        logger.warning('%s', message)
    else:
        logger.exception('%s', message, exc_info=exc)
    if raise_errors:
        raise RuntimeError(message) from exc
    return False


def _send(
    template: str,
    subject: str,
    to: str | Iterable[str],
    context: dict,
    reply_to: str | Iterable[str] | None = None,
    *,
    raise_errors: bool = False,
) -> bool:
    """Render and send one email. Returns True only when it left the process."""
    global _last_error
    recipients = _recipients(to)
    if not recipients:
        return _fail('No recipient address was given.', raise_errors=raise_errors)
    if not email_enabled():
        return _fail(
            'Email is not configured. Set EMAIL_HOST and the SMTP credentials in .env.',
            raise_errors=raise_errors,
        )

    logo = _logo_bytes()
    render_context = {
        'site_url': _site_url(),
        'team_email': settings.TEAM_EMAIL,
        'brand_name': 'Axora Finds',
        'logo_cid': LOGO_CID if logo else '',
        **context,
    }

    try:
        text_body, html_body = _render_parts(template, render_context)
    except Exception as exc:  # noqa: BLE001 - a missing template must not break the request
        return _fail(f'Could not render the {template} email: {exc}', raise_errors=raise_errors, exc=exc)

    try:
        message = InlineLogoEmail(
            subject=subject,
            body=text_body,
            from_email=_from_email(),
            to=recipients,
            reply_to=_reply_to(reply_to),
        )
        message.attach_alternative(html_body, 'text/html')
        if logo:
            _attach_logo(message, logo)
        message.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001 - email trouble must not fail the request
        detail = f'Could not send the {template} email: {exc}'
        hint = _smtp_guidance(exc)
        if hint:
            detail = f'{detail}. {hint}'
        return _fail(detail, raise_errors=raise_errors, exc=exc)

    _last_error = None
    logger.info('Sent the %s email to %s', template, ', '.join(recipients))
    return True


def email_status() -> dict:
    """Configuration and template health, for the staff dashboard and Django admin."""
    missing: list[str] = []
    for name in EMAIL_TEMPLATES:
        for extension in ('html', 'txt'):
            try:
                get_template(f'emails/{name}.{extension}')
            except TemplateDoesNotExist:
                missing.append(f'{name}.{extension}')
            except TemplateSyntaxError as exc:
                # A broken template must not take down the diagnostics screen.
                missing.append(f'{name}.{extension} ({exc})')

    return {
        'enabled': email_enabled(),
        'backend': settings.EMAIL_BACKEND,
        'host': settings.EMAIL_HOST or None,
        'port': settings.EMAIL_PORT if settings.EMAIL_HOST else None,
        'use_tls': settings.EMAIL_USE_TLS,
        'use_ssl': settings.EMAIL_USE_SSL,
        'from_email': _from_email(),
        'team_email': settings.TEAM_EMAIL,
        'site_url': _site_url(),
        'last_error': _last_error,
        'templates_ready': not missing,
        'missing_templates': missing,
        'message_count': len(EMAIL_TEMPLATES),
    }


def _user_name(user) -> str:
    return (user.get_full_name() or user.email).strip()


def _inspection_context(inspection) -> dict:
    prop = inspection.property
    has_fee = inspection.fee_amount > 0
    preferred_date = date_format(inspection.preferred_date, 'l, j F Y')
    fee_display = _money(inspection.fee_amount) if has_fee else 'No inspection fee'
    return {
        'reference': inspection.reference,
        'name': inspection.name,
        'email': inspection.email,
        'phone': inspection.phone,
        'property_title': prop.title,
        'property_location': prop.location,
        'property_url': f'{_site_url()}/properties/{prop.slug}',
        'property_address': prop.address,
        'preferred_date': inspection.preferred_date,
        'preferred_date_display': preferred_date,
        'fee_display': fee_display,
        'has_fee': has_fee,
        'is_transfer': inspection.payment_choice == 'transfer',
        'payment_choice': inspection.get_payment_choice_display(),
        'payment_status': inspection.get_payment_status_display(),
        'status': inspection.get_status_display(),
        'note': inspection.note,
        'details': [
            ('Reference', inspection.reference),
            ('Property', prop.title),
            ('Location', prop.location),
            ('Preferred date', preferred_date),
            ('Inspection fee', fee_display),
            ('Payment', f'{inspection.get_payment_choice_display()} ({inspection.get_payment_status_display()})'),
        ],
    }


def _listing_context(prop) -> dict:
    published = prop.status == 'published'
    price_display = _money(prop.price)
    inspection_fee_display = _money(prop.inspection_fee)
    return {
        'owner_name': _user_name(prop.owner),
        'owner_email': prop.owner.email,
        'title': prop.title,
        'location': prop.location,
        'price_display': price_display,
        'property_type': prop.short_type,
        'inspection_fee_display': inspection_fee_display,
        'status': prop.get_status_display(),
        'property_url': f'{_site_url()}/properties/{prop.slug}' if published else '',
        'details': [
            ('Listing', prop.title),
            ('Location', prop.location),
            ('Type', prop.short_type),
            ('Rent', price_display),
            ('Inspection fee', inspection_fee_display),
            ('Status', prop.get_status_display()),
        ],
    }


def _review_context(review) -> dict:
    return {
        'name': review.name,
        'rating': review.rating,
        'text': review.text,
        'location': review.location,
        'reviews_url': f'{_site_url()}/#reviews',
        'details': [
            ('Name', review.name),
            ('Rating', f'{review.rating} out of 5'),
            ('Location', review.location or 'Not given'),
        ],
    }


# --- Account -----------------------------------------------------------------


def send_welcome_email(user) -> bool:
    first_name = user.first_name.strip() or _user_name(user)
    return _send(
        'welcome',
    'otp',
        'Welcome to Axora Finds',
        user.email,
        {
            'first_name': first_name,
            'role': user.get_role_display(),
            'is_owner': user.role == 'owner',
            'browse_url': f'{_site_url()}/properties',
            'list_url': f'{_site_url()}/list-property',
        },
    )


def send_otp_email(user, otp_code: str, *, title: str, expiry_minutes: int = 10) -> bool:
    """Send an email-verification or password-reset one-time code."""
    name = (user.first_name or '').strip() or user.email
    return _send(
        'otp',
        f'Your Axora Finds {title} code',
        user.email,
        {'user_name': name, 'otp_code': otp_code, 'title': title, 'expiry_minutes': expiry_minutes},
    )


# --- Contact -----------------------------------------------------------------


def send_contact_received_email(message) -> bool:
    return _send(
        'contact_received',
        'We received your message',
        message.email,
        {'name': message.name, 'message': message.message},
    )


def send_contact_team_email(message) -> bool:
    return _send(
        'team_notification',
        'New contact message from the Axora Finds site',
        settings.TEAM_EMAIL,
        {
            'heading': 'New contact message',
            'intro': f'{message.name} sent a message through the website.',
            'details': [('Name', message.name), ('Email', message.email)],
            'message': message.message,
        },
        reply_to=[message.email],
    )


# --- Newsletter --------------------------------------------------------------


def send_newsletter_welcome_email(email: str) -> bool:
    return _send(
        'newsletter_welcome',
        'You are subscribed to Axora Finds',
        email,
        {
            'email': email,
            'browse_url': f'{_site_url()}/properties',
        },
    )


def send_newsletter_team_email(email: str) -> bool:
    return _send(
        'team_notification',
        'New newsletter subscriber',
        settings.TEAM_EMAIL,
        {
            'heading': 'New newsletter subscriber',
            'intro': f'{email} subscribed to Axora Finds updates.',
            'details': [('Email', email)],
            'message': '',
        },
    )


# --- Inspections -------------------------------------------------------------


def send_inspection_received_email(inspection) -> bool:
    return _send(
        'inspection_received',
        f'Inspection request {inspection.reference} received',
        inspection.email,
        _inspection_context(inspection),
    )


def send_inspection_team_email(inspection) -> bool:
    ctx = _inspection_context(inspection)
    return _send(
        'team_notification',
        f'New inspection request {inspection.reference}',
        settings.TEAM_EMAIL,
        {
            **ctx,
            'heading': 'New inspection request',
            'intro': f'{inspection.name} asked to inspect {inspection.property.title}.',
            'details': [
                ('Reference', inspection.reference),
                ('Visitor', inspection.name),
                ('Phone', inspection.phone),
                ('Email', inspection.email),
                ('Property', inspection.property.title),
                ('Location', inspection.property.location),
                ('Preferred date', inspection.preferred_date),
                ('Inspection fee', ctx['fee_display']),
                ('Payment choice', inspection.get_payment_choice_display()),
                ('Payment status', inspection.get_payment_status_display()),
            ],
            'message': inspection.note,
        },
        reply_to=[inspection.email],
    )


def send_payment_verified_email(inspection) -> bool:
    if inspection.fee_amount <= 0:
        return False
    return _send(
        'payment_verified',
        f'Payment verified for inspection {inspection.reference}',
        inspection.email,
        _inspection_context(inspection),
    )


def send_inspection_confirmed_email(inspection) -> bool:
    return _send(
        'inspection_confirmed',
        f'Inspection {inspection.reference} confirmed',
        inspection.email,
        _inspection_context(inspection),
    )


def send_inspection_rejected_email(inspection) -> bool:
    return _send(
        'inspection_rejected',
        f'Inspection {inspection.reference} could not be confirmed',
        inspection.email,
        _inspection_context(inspection),
    )


# --- Listings ----------------------------------------------------------------


def send_listing_received_email(prop) -> bool:
    return _send(
        'listing_received',
        'We received your listing',
        prop.owner.email,
        _listing_context(prop),
    )


def send_listing_team_email(prop) -> bool:
    ctx = _listing_context(prop)
    return _send(
        'team_notification',
        'New listing waiting for review',
        settings.TEAM_EMAIL,
        {
            **ctx,
            'heading': 'New listing waiting for review',
            'intro': f'{ctx["owner_name"]} submitted {prop.title} for review.',
            'details': [
                ('Owner', ctx['owner_name']),
                ('Owner email', prop.owner.email),
                ('Title', prop.title),
                ('Location', prop.location),
                ('Type', prop.short_type),
                ('Rent', ctx['price_display']),
                ('Inspection fee', ctx['inspection_fee_display']),
            ],
            'message': prop.description,
        },
        reply_to=[prop.owner.email],
    )


def send_listing_published_email(prop) -> bool:
    return _send(
        'listing_published',
        'Your listing is live on Axora Finds',
        prop.owner.email,
        _listing_context(prop),
    )


def send_listing_rejected_email(prop) -> bool:
    return _send(
        'listing_rejected',
        'Your listing was not approved',
        prop.owner.email,
        _listing_context(prop),
    )


# --- Reviews -----------------------------------------------------------------


def send_review_received_email(review) -> bool:
    if not review.user_id:
        return False
    return _send(
        'review_received',
        'Thanks for your review',
        review.user.email,
        _review_context(review),
    )


def send_review_team_email(review) -> bool:
    return _send(
        'team_notification',
        'New review waiting for moderation',
        settings.TEAM_EMAIL,
        {
            'heading': 'New review waiting for moderation',
            'intro': f'{review.name} submitted a review of the home page.',
            'details': [
                ('Name', review.name),
                ('Rating', f'{review.rating} out of 5'),
                ('Location', review.location or 'Not given'),
                ('Account', review.user.email if review.user_id else 'No linked account'),
            ],
            'message': review.text,
        },
        reply_to=[review.user.email] if review.user_id else None,
    )


def send_review_published_email(review) -> bool:
    if not review.user_id:
        return False
    return _send(
        'review_published',
        'Your review is live on Axora Finds',
        review.user.email,
        _review_context(review),
    )


# --- Diagnostics -------------------------------------------------------------


def send_test_email(to: str, *, raise_errors: bool = False) -> bool:
    """Used by ``manage.py send_test_email``, the staff dashboard and Django admin."""
    sent_at = date_format(timezone.localtime(timezone.now()), 'l, j F Y, H:i T')
    backend = settings.EMAIL_BACKEND
    host = settings.EMAIL_HOST or 'not set'
    return _send(
        'test',
        'Axora Finds email test',
        to,
        {
            'sent_at_display': sent_at,
            'backend': backend,
            'host': host,
            'details': [
                ('Sent', sent_at),
                ('Backend', backend),
                ('SMTP host', host),
            ],
        },
        raise_errors=raise_errors,
    )
