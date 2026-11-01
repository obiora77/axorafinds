"""Serializers for the signed-in staff dashboard (``/api/staff/``)."""
from rest_framework import serializers

from accounts.models import User
from inspections.models import Inspection
from listings.models import Property
from listings.serializers import photo_url
from pages.models import ContactMessage, NewsletterSubscriber, Review, SiteSettings


class StaffPropertySerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    location = serializers.CharField(read_only=True)
    short_type = serializers.CharField(read_only=True)
    cover = serializers.SerializerMethodField()
    photos_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Property
        fields = [
            'id', 'slug', 'title', 'property_type', 'short_type', 'price', 'state', 'city',
            'location', 'bedrooms', 'bathrooms', 'inspection_fee', 'status', 'cover',
            'photos_count', 'owner_name', 'owner_email', 'created_at', 'published_at',
            'reviewed_at',
        ]
        read_only_fields = fields

    def get_owner_name(self, prop) -> str:
        return (prop.owner.get_full_name() or prop.owner.email).strip()

    def get_cover(self, prop):
        photos = list(prop.photos.all())  # prefetched and ordered by the queryset
        return photo_url(photos[0], self.context.get('request')) if photos else None


class StaffInspectionSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source='property.title', read_only=True)
    property_slug = serializers.SlugField(source='property.slug', read_only=True)
    payment_choice_display = serializers.CharField(source='get_payment_choice_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_verify_payment = serializers.SerializerMethodField()
    can_confirm = serializers.SerializerMethodField()
    can_reject = serializers.SerializerMethodField()

    class Meta:
        model = Inspection
        fields = [
            'id', 'reference', 'name', 'phone', 'email', 'property', 'property_title',
            'property_slug', 'preferred_date', 'note', 'payment_choice',
            'payment_choice_display', 'fee_amount', 'payment_status',
            'payment_status_display', 'status', 'status_display', 'staff_note',
            'created_at', 'decided_at', 'can_verify_payment', 'can_confirm', 'can_reject',
        ]
        read_only_fields = fields

    def get_can_verify_payment(self, inspection) -> bool:
        return (
            inspection.status == 'pending'
            and inspection.fee_amount > 0
            and inspection.payment_status != 'verified'
        )

    def get_can_confirm(self, inspection) -> bool:
        return inspection.status == 'pending' and inspection.payment_status in {'verified', 'not_required'}

    def get_can_reject(self, inspection) -> bool:
        return inspection.status == 'pending'


class StaffReviewSerializer(serializers.ModelSerializer):
    author_email = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'name', 'location', 'rating', 'text', 'is_published', 'author_email', 'created_at']
        read_only_fields = fields

    def get_author_email(self, review):
        return review.user.email if review.user_id else None


class StaffContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'message', 'created_at']
        read_only_fields = fields


class StaffSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ['id', 'email', 'created_at']
        read_only_fields = fields


class StaffUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'role', 'is_active', 'is_staff', 'date_joined', 'last_login']
        read_only_fields = fields

    def get_name(self, user) -> str:
        return (user.get_full_name() or user.email).strip()


class StaffSiteSettingsSerializer(serializers.ModelSerializer):
    has_account = serializers.BooleanField(read_only=True)

    class Meta:
        model = SiteSettings
        fields = ['bank_name', 'account_name', 'account_number', 'transfer_note', 'is_live', 'has_account']
