import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

# Keep in sync with NG_STATES in apps/web/src/lib/site.ts.
STATES = [
    'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue', 'Borno',
    'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'FCT', 'Gombe', 'Imo',
    'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos', 'Nasarawa',
    'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 'Sokoto', 'Taraba',
    'Yobe', 'Zamfara',
]


class Status(models.TextChoices):
    PENDING = 'pending', 'Pending review'
    PUBLISHED = 'published', 'Published'
    REJECTED = 'rejected', 'Rejected'


class PropertyType(models.TextChoices):
    ROOM_PARLOUR = 'room_parlour', 'Room and parlour'
    SELF_CONTAIN = 'self_contain', 'Self-contain'
    FLAT = 'flat', 'Flat'
    DUPLEX = 'duplex', 'Duplex'
    BUNGALOW = 'bungalow', 'Bungalow'
    LAND = 'land', 'Land'


def photo_path(instance, filename):
    """Uploaded files get a random name so user-supplied filenames never reach disk."""
    extension = Path(filename).suffix.lower()[:6]
    return f'properties/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{extension}'


class Property(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='properties')
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    price = models.DecimalField(
        'rent (NGN)', max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('1'))]
    )
    state = models.CharField(max_length=20, choices=[(s, s) for s in STATES])
    city = models.CharField(max_length=80)
    address = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    bedrooms = models.PositiveSmallIntegerField(default=1, help_text='Rooms for room and parlour; 0 for land.')
    bathrooms = models.PositiveSmallIntegerField(default=1)
    amenities = models.JSONField(default=list, blank=True)
    inspection_fee = models.DecimalField(
        'inspection fee (NGN)', max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))], help_text='0 means no inspection fee.',
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    published_at = models.DateTimeField(null=True, blank=True, editable=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='reviewed_properties', editable=False,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name_plural = 'properties'
        ordering = ['-published_at', '-id']

    def __str__(self):
        return f'{self.title} ({self.city})'

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f'{self.title} {self.city}')[:200] or 'property'
            slug, n = base, 2
            while Property.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        if self.status == Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def location(self) -> str:
        return f'{self.city}, FCT' if self.state == 'FCT' else f'{self.city}, {self.state} State'

    @property
    def short_type(self) -> str:
        n, kind = self.bedrooms, self.property_type
        if kind == PropertyType.ROOM_PARLOUR:
            return f'{n} Rooms and parlour' if n > 1 else 'Room and parlour'
        if kind == PropertyType.SELF_CONTAIN:
            return 'Self-contain'
        if kind == PropertyType.LAND:
            return 'Land'
        label = self.get_property_type_display().lower()
        return f'{n} Bedroom {label}' if n else label.capitalize()

    def publish(self, staff_user):
        if not self.photos.exists():
            raise ValidationError('Add at least one photo before publishing.')
        self.status = Status.PUBLISHED
        self.reviewed_by = staff_user
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self, staff_user):
        self.status = Status.REJECTED
        self.reviewed_by = staff_user
        self.reviewed_at = timezone.now()
        self.save()


class PropertyPhoto(models.Model):
    """A listing photo: an uploaded file, or an external image URL (used by the seed data)."""

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to=photo_path, blank=True)
    external_url = models.URLField(max_length=500, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'Photo {self.position + 1} of {self.property_id}'

    def clean(self):
        if not self.image and not self.external_url:
            raise ValidationError('Upload an image or give an image URL.')


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'property'], name='unique_favorite_per_user')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user_id} saved {self.property_id}'
