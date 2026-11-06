"""
Send email over HTTPS (port 443) instead of SMTP.

Why this exists: Render's free web services block outbound SMTP (ports 25, 465 and 587), so
Gmail/SMTP can never deliver from there. Brevo and Resend both accept a plain HTTPS request, which
works on every host. Only the standard library is used, so there is nothing extra to install.

Turn one on with environment variables (see config/settings.py):
    EMAIL_PROVIDER=brevo   BREVO_API_KEY=...
    EMAIL_PROVIDER=resend  RESEND_API_KEY=...
and set DEFAULT_FROM_EMAIL to an address (or domain) you verified in that provider's dashboard.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from email.message import MIMEPart
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

USER_AGENT = 'AxoraFinds/1.0'  # some providers sit behind Cloudflare and reject a missing/default agent
_CID = re.compile(r'cid:[\w.@-]+')


class EmailApiError(Exception):
    """The provider refused the message or could not be reached. ``hint`` says what to check."""

    def __init__(self, message: str, *, status: int | None = None, hint: str = ''):
        super().__init__(message)
        self.status = status
        self.hint = hint


def _address(value: str) -> dict:
    name, email = parseaddr(value)
    return {'email': email, **({'name': name} if name else {})}


def _error_text(raw: bytes) -> str:
    text = raw.decode('utf-8', errors='replace').strip()
    try:
        data = json.loads(text)
    except ValueError:
        return text[:300]
    if isinstance(data, dict):
        return str(data.get('message') or data.get('error') or data.get('name') or data)[:300]
    return text[:300]


class _HttpApiBackend(BaseEmailBackend):
    provider = ''
    default_url = ''
    key_setting = 'EMAIL_API_KEY'

    def __init__(self, fail_silently: bool = False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = getattr(settings, self.key_setting, '') or ''
        self.url = getattr(settings, 'EMAIL_API_URL', '') or self.default_url
        self.timeout = getattr(settings, 'EMAIL_API_TIMEOUT', 15)

    # -- to be provided by each provider ---------------------------------------------------
    def headers(self) -> dict[str, str]:
        raise NotImplementedError

    def payload(self, message, text: str, html: str) -> dict:
        raise NotImplementedError

    def hint(self, status: int | None, detail: str) -> str:
        return ''

    # -- shared ------------------------------------------------------------------------------
    def send_messages(self, email_messages) -> int:
        sent = 0
        for message in email_messages or []:
            try:
                self._deliver(message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception('Could not send an email through %s', self.provider)
        return sent

    @staticmethod
    def _html(message) -> str:
        for content, mimetype in getattr(message, 'alternatives', None) or []:
            if mimetype == 'text/html':
                # The inline logo (cid:...) only exists in an SMTP message; point it at a public URL.
                logo_url = getattr(settings, 'EMAIL_LOGO_URL', '')
                return _CID.sub(logo_url, content) if logo_url else _CID.sub('', content)
        return ''

    def _deliver(self, message) -> None:
        if not self.api_key:
            raise EmailApiError(
                f'The {self.provider} API key is not set.',
                hint=f'Set the {self.provider.upper()}_API_KEY environment variable.',
            )
        if not message.recipients():
            return
        body = self.payload(message, message.body or '', self._html(message))
        request = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode('utf-8'),
            headers={**self.headers(), 'User-Agent': USER_AGENT},
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - https URL
                response.read()
        except urllib.error.HTTPError as exc:
            detail = _error_text(exc.read())
            raise EmailApiError(
                f'{self.provider} rejected the message (HTTP {exc.code}): {detail}',
                status=exc.code,
                hint=self.hint(exc.code, detail),
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, 'reason', exc)
            raise EmailApiError(
                f'Could not reach {self.provider}: {reason}',
                hint='Check the server has internet access and raise EMAIL_API_TIMEOUT if it is slow.',
            ) from exc


class BrevoEmailBackend(_HttpApiBackend):
    provider = 'Brevo'
    default_url = 'https://api.brevo.com/v3/smtp/email'

    def headers(self) -> dict[str, str]:
        return {'api-key': self.api_key, 'accept': 'application/json', 'content-type': 'application/json'}

    def payload(self, message, text: str, html: str) -> dict:
        body: dict = {
            'sender': _address(message.from_email),
            'to': [_address(a) for a in message.to],
            'subject': message.subject,
        }
        if message.cc:
            body['cc'] = [_address(a) for a in message.cc]
        if message.bcc:
            body['bcc'] = [_address(a) for a in message.bcc]
        if html:
            body['htmlContent'] = html
            if text:
                body['textContent'] = text
        else:
            body['textContent'] = text or ' '
        if message.reply_to:
            body['replyTo'] = _address(message.reply_to[0])
        return body

    def hint(self, status: int | None, detail: str) -> str:
        lowered = detail.lower()
        if status == 401:
            return (
                'Brevo rejected the API key. Create a new key under SMTP & API > API Keys and set it as '
                'BREVO_API_KEY (no quotes or spaces). If you turned on "Authorised IPs" in Brevo, turn it '
                'off: Render\'s IP addresses change.'
            )
        if 'sender' in lowered:
            return (
                'The From address is not a verified Brevo sender. Add and verify it under Senders, '
                'Domains & Dedicated IPs, then set DEFAULT_FROM_EMAIL to exactly that address.'
            )
        if status == 429:
            return 'Brevo\'s sending limit was reached. Wait, or check your plan\'s daily limit.'
        return ''


class ResendEmailBackend(_HttpApiBackend):
    provider = 'Resend'
    default_url = 'https://api.resend.com/emails'

    def headers(self) -> dict[str, str]:
        return {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}

    def payload(self, message, text: str, html: str) -> dict:
        body: dict = {'from': message.from_email, 'to': list(message.to), 'subject': message.subject}
        if message.cc:
            body['cc'] = list(message.cc)
        if message.bcc:
            body['bcc'] = list(message.bcc)
        if html:
            body['html'] = html
        if text or not html:
            body['text'] = text or ' '
        if message.reply_to:
            body['reply_to'] = list(message.reply_to)
        return body

    def hint(self, status: int | None, detail: str) -> str:
        lowered = detail.lower()
        if status in (401, 403) and 'verif' not in lowered and 'domain' not in lowered:
            return 'Resend rejected the API key. Create a new one and set it as RESEND_API_KEY.'
        if 'verif' in lowered or 'domain' in lowered or status == 403:
            return (
                'The From address uses a domain that is not verified in Resend. Verify the domain, '
                'then set DEFAULT_FROM_EMAIL to an address on it. (Until a domain is verified, Resend '
                'only sends to your own account email.)'
            )
        if status == 429:
            return 'Resend\'s sending limit was reached. Wait, or check your plan\'s limit.'
        return ''


__all__ = ['BrevoEmailBackend', 'EmailApiError', 'ResendEmailBackend', 'MIMEPart']
