import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Creates the first staff login from DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD. '
        'Safe to run on every deploy: it does nothing when the variables are missing or the account exists.'
    )

    def handle(self, *args, **options):
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', '').strip().lower()
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '')
        if not email or not password:
            self.stdout.write('DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD not set: skipping.')
            return

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(f'Staff login {email} already exists: nothing to do.')
            return

        try:
            validate_password(password, user=User(email=email))
        except ValidationError as exc:
            raise CommandError(
                'DJANGO_SUPERUSER_PASSWORD is too weak: ' + ' '.join(exc.messages)
                + ' Choose a stronger password and deploy again.'
            ) from exc

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Staff login {email} created.'))
