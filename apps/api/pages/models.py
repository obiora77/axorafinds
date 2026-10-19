from django.db import models
from django.utils import timezone


class SiteSettings(models.Model):
    """
    One row, edited in Django admin. The official bank account lives here and nowhere else:
    it is never hardcoded in the frontend and is only revealed by GET /api/payments/account.
    """

    bank_name = models.CharField(max_length=80, blank=True)
    account_name = models.CharField(max_length=120, blank=True)
    account_number = models.CharField(max_length=20, blank=True)
    transfer_note = models.TextField(
        blank=True, help_text='Shown under the account details, e.g. "Use your reference as the narration."'
    )
    is_live = models.BooleanField(
        default=False,
        help_text=(
            'Tick this once the real bank details above are entered. '
            'While unticked, the account is only shown when DJANGO_DEBUG is on (demo data).'
        ),
    )

    class Meta:
        verbose_name = 'site settings'
        verbose_name_plural = 'site settings'

    def __str__(self):
        return 'Site settings'

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return (0, {})

    @classmethod
    def load(cls) -> 'SiteSettings':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def has_account(self) -> bool:
        return bool(self.bank_name and self.account_name and self.account_number)


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField(max_length=2000)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} <{self.email}>'
