from django.db import transaction
from rest_framework import serializers

from .models import Property, PropertyPhoto, Status

MAX_PHOTOS = 8
MAX_PHOTO_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def photo_url(photo: PropertyPhoto, request) -> str:
    if photo.image:
        url = photo.image.url
        return request.build_absolute_uri(url) if request else url
    return photo.external_url


class PhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyPhoto
        fields = ['id', 'url']

    def get_url(self, photo) -> str:
        return photo_url(photo, self.context.get('request'))


class PropertyCardSerializer(serializers.ModelSerializer):
    location = serializers.CharField(read_only=True)
    short_type = serializers.CharField(read_only=True)
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'slug', 'title', 'price', 'state', 'city', 'location',
            'bedrooms', 'property_type', 'short_type', 'cover',
        ]
        read_only_fields = fields

    def get_cover(self, prop):
        photos = list(prop.photos.all())  # prefetched and ordered by the view
        return photo_url(photos[0], self.context.get('request')) if photos else None


class PropertyDetailSerializer(PropertyCardSerializer):
    photos = PhotoSerializer(many=True, read_only=True)

    class Meta(PropertyCardSerializer.Meta):
        fields = PropertyCardSerializer.Meta.fields + [
            'address', 'bathrooms', 'description', 'amenities', 'inspection_fee', 'status', 'photos',
        ]
        read_only_fields = fields


class PropertyCreateSerializer(serializers.ModelSerializer):
    amenities = serializers.ListField(
        child=serializers.CharField(max_length=60), required=False, max_length=15
    )
    photos = serializers.ListField(
        child=serializers.ImageField(), write_only=True, min_length=1, max_length=MAX_PHOTOS
    )

    class Meta:
        model = Property
        fields = [
            'title', 'property_type', 'price', 'state', 'city', 'address', 'description',
            'bedrooms', 'bathrooms', 'amenities', 'inspection_fee', 'photos',
        ]

    def validate_photos(self, photos):
        for photo in photos:
            if photo.size > MAX_PHOTO_BYTES:
                raise serializers.ValidationError(f'{photo.name} is larger than 5 MB.')
            if getattr(photo, 'content_type', None) not in ALLOWED_IMAGE_TYPES:
                raise serializers.ValidationError('Photos must be JPEG, PNG or WebP images.')
        return photos

    def validate_amenities(self, items):
        return [item.strip() for item in items if item.strip()]

    @transaction.atomic
    def create(self, validated_data):
        photos = validated_data.pop('photos')
        # Owner submissions are always pending. Only staff can publish, in Django admin.
        prop = Property.objects.create(
            owner=self.context['request'].user, status=Status.PENDING, **validated_data
        )
        for position, image in enumerate(photos):
            PropertyPhoto.objects.create(property=prop, image=image, position=position)
        return prop
