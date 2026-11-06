import logging
import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify

from .images import compress_image

logger = logging.getLogger(__name__)

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
    """
    A listing photo.

    New uploads (from the website or from Django admin) are resized and stored in the database
    (see PhotoBlob) and served from /api/photos/<id>. That is deliberate: hosts like Render wipe the
    server's disk on every deploy, so photos saved as files would disappear. Older rows that still
    point at a file, and the seed data's external image URLs, keep working.
    """

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to=photo_path, blank=True)
    external_url = models.URLField(max_length=500, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    # Content type of the picture stored in PhotoBlob; empty when the photo lives elsewhere.
    stored_type = models.CharField(max_length=40, blank=True, editable=False)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'Photo {self.position + 1} of {self.property_id}'

    def clean(self):
        if not self.image and not self.external_url and not self.stored_type:
            raise ValidationError('Upload an image or give an image URL.')

    def _read_upload(self):
        """Resizes a freshly uploaded file; returns (bytes, content_type) or None if unreadable."""
        try:
            file = self.image.file
            file.seek(0)
            return compress_image(file.read())
        except Exception:  # noqa: BLE001 - fall back to saving the file as uploaded
            logger.warning('Could not process the uploaded photo; keeping the original file.', exc_info=True)
            return None

    def save(self, *args, **kwargs):
        upload = self._read_upload() if self.image and not self.image._committed else None
        if upload:
            self.image = ''
            self.stored_type = upload[1]
        with transaction.atomic():
            super().save(*args, **kwargs)
            if upload:
                PhotoBlob.objects.update_or_create(photo=self, defaults={'data': upload[0]})


class PhotoBlob(models.Model):
    """The picture bytes for a PropertyPhoto, kept apart so listing queries never load them."""

    photo = models.OneToOneField(PropertyPhoto, on_delete=models.CASCADE, primary_key=True, related_name='blob')
    data = models.BinaryField()

    def __str__(self):
        return f'Picture data for photo {self.photo_id}'


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'property'], name='unique_favorite_per_user')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user_id} saved {self.property_id}'
