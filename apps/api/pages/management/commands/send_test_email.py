from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from config.emails import last_email_error, send_test_email


class Command(BaseCommand):
    help = 'Send the Axora Finds test email through the configured backend.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            required=True,
            help='Recipient address for the test message.',
        )

    def handle(self, *args, **options):
        recipient = options['to'].strip()
        if not recipient:
            raise CommandError('Give the recipient address with --to.')

        self.stdout.write(f'Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'SMTP host: {settings.EMAIL_HOST or "not set"} port {settings.EMAIL_PORT}')
        self.stdout.write(
            f'Encryption: TLS={settings.EMAIL_USE_TLS} SSL={settings.EMAIL_USE_SSL}'
        )
        self.stdout.write(f'From: {settings.DEFAULT_FROM_EMAIL}')

        try:
            sent = send_test_email(recipient, raise_errors=True)
        except Exception as exc:  # noqa: BLE001 - surface the real SMTP failure
            raise CommandError(
                f'The test email failed: {exc}\n'
                'For Gmail: use a 16-character App Password with no spaces, make sure 2-Step '
                'Verification is on, and keep EMAIL_PORT=587 with EMAIL_USE_TLS=1 and '
                'EMAIL_USE_SSL=0.'
            ) from exc

        if not sent:
            raise CommandError(
                f'The test email could not be sent: {last_email_error() or "unknown error"}'
            )

        self.stdout.write(self.style.SUCCESS(f'Test email sent to {recipient}.'))
