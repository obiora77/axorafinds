import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class PaymentChoice(models.TextChoices):
    TRANSFER = 'transfer', 'Bank transfer'
    IN_PERSON = 'in_person', 'Pay in person'


class PaymentStatus(models.TextChoices):
    NOT_REQUIRED = 'not_required', 'No fee'
    UNPAID = 'unpaid', 'Unpaid'
    VERIFIED = 'verified', 'Payment verified'


class InspectionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    REJECTED = 'rejected', 'Rejected'


# An inspection may only be confirmed once there is nothing left to pay or the payment is verified.
CONFIRMABLE_PAYMENT_STATES = [PaymentStatus.VERIFIED, PaymentStatus.NOT_REQUIRED]


def new_reference() -> str:
    return f'AX-{secrets.token_hex(3).upper()}'


class Inspection(models.Model):
    reference = models.CharField(max_length=12, unique=True, editable=False)
    property = models.ForeignKey('listings.Property', on_delete=models.PROTECT, related_name='inspections')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='inspections'
    )

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    preferred_date = models.DateField()
    note = models.TextField(blank=True, max_length=500)

    payment_choice = models.CharField(max_length=10, choices=PaymentChoice.choices, default=PaymentChoice.IN_PERSON)
    fee_amount = models.DecimalField(
        'inspection fee (NGN)', max_digits=10, decimal_places=2, default=0,
        help_text='Copied from the property when the request was made.',
    )
    payment_status = models.CharField(max_length=12, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    status = models.CharField(max_length=10, choices=InspectionStatus.choices, default=InspectionStatus.PENDING)

    payment_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', editable=False,
    )
    payment_verified_at = models.DateTimeField(null=True, blank=True, editable=False)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', editable=False,
    )
    decided_at = models.DateTimeField(null=True, blank=True, editable=False)
    staff_note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # Database-level guard: nothing can be marked confirmed while its payment is unverified.
            models.CheckConstraint(
                condition=~models.Q(status='confirmed') | models.Q(payment_status__in=['verified', 'not_required']),
                name='confirmed_requires_verified_payment',
            ),
            models.CheckConstraint(condition=models.Q(fee_amount__gte=0), name='inspection_fee_not_negative'),
        ]

    def __str__(self):
        return f'{self.reference} - {self.name}'

    def save(self, *args, **kwargs):
        if not self.reference:
            reference = new_reference()
            while Inspection.objects.filter(reference=reference).exists():
                reference = new_reference()
            self.reference = reference
        super().save(*args, **kwargs)

    def clean(self):
        if self.status == InspectionStatus.CONFIRMED and self.payment_status not in CONFIRMABLE_PAYMENT_STATES:
            raise ValidationError('Verify the payment before confirming this inspection.')

    # --- staff actions (used by Django admin) ---

    def verify_payment(self, staff_user):
        if self.status != InspectionStatus.PENDING:
            raise ValidationError('Only pending inspections can have their payment verified.')
        if self.fee_amount <= 0:
            raise ValidationError('This inspection has no fee to verify.')
        if self.payment_status == PaymentStatus.VERIFIED:
            raise ValidationError('Payment is already verified.')
        self.payment_status = PaymentStatus.VERIFIED
        self.payment_verified_by = staff_user
        self.payment_verified_at = timezone.now()
        self.save(update_fields=['payment_status', 'payment_verified_by', 'payment_verified_at'])

    def confirm(self, staff_user):
        if self.status != InspectionStatus.PENDING:
            raise ValidationError('Only pending inspections can be confirmed.')
        if self.payment_status not in CONFIRMABLE_PAYMENT_STATES:
            raise ValidationError('Verify the payment before confirming this inspection.')
        self.status = InspectionStatus.CONFIRMED
        self.decided_by = staff_user
        self.decided_at = timezone.now()
        self.save(update_fields=['status', 'decided_by', 'decided_at'])

    def reject(self, staff_user):
        if self.status != InspectionStatus.PENDING:
            raise ValidationError('Only pending inspections can be rejected.')
        self.status = InspectionStatus.REJECTED
        self.decided_by = staff_user
        self.decided_at = timezone.now()
        self.save(update_fields=['status', 'decided_by', 'decided_at'])
