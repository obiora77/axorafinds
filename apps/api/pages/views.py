from django.db.models import Avg, Count
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.emails import (
    send_contact_received_email,
    send_contact_team_email,
    send_newsletter_team_email,
    send_newsletter_welcome_email,
    send_review_received_email,
    send_review_team_email,
)

from .models import ContactMessage, NewsletterSubscriber, Review


class NewsletterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class ContactSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=120)
    message = serializers.CharField(max_length=2000)

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'message']


class NewsletterView(APIView):
    """POST /api/newsletter. The reply is the same whether or not the address was already there."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'newsletter'

    def post(self, request):
        serializer = NewsletterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=serializer.validated_data['email'].strip().lower()
        )
        if created:
            send_newsletter_welcome_email(subscriber.email)
            send_newsletter_team_email(subscriber.email)
        return Response({'detail': 'Subscribed.'}, status=status.HTTP_201_CREATED)


class ContactView(APIView):
    """POST /api/contact. Stored in the database and shown in admin; emailed when email is configured."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'contact'

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        msg = serializer.save()
        send_contact_team_email(msg)
        send_contact_received_email(msg)
        return Response({'detail': 'Message received.'}, status=status.HTTP_201_CREATED)


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'name', 'location', 'rating', 'text', 'created_at']
        read_only_fields = fields


class ReviewSubmitSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(max_length=600)
    location = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate_text(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError('Write at least 10 characters.')
        return value

    def validate_location(self, value):
        return value.strip()


class ReviewListView(APIView):
    """
    GET  /api/reviews   public, published reviews plus the average rating
    POST /api/reviews   signed in, saved unpublished until staff approve it
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'reviews'

    def get_permissions(self):
        if self.request.method in {'GET', 'HEAD', 'OPTIONS'}:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_throttles(self):
        # Browsing reviews is unlimited; only submissions are rate limited.
        if self.request.method in {'GET', 'HEAD', 'OPTIONS'}:
            return []
        return super().get_throttles()

    def get(self, request):
        try:
            limit = max(1, min(int(request.query_params.get('limit', 6)), 24))
        except (TypeError, ValueError):
            limit = 6

        published = Review.objects.filter(is_published=True)
        stats = published.aggregate(count=Count('id'), average=Avg('rating'))
        average = stats['average']
        return Response(
            {
                'count': stats['count'],
                'average_rating': round(float(average), 1) if average is not None else None,
                'results': ReviewSerializer(published[:limit], many=True).data,
            }
        )

    def post(self, request):
        serializer = ReviewSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        review = Review.objects.create(
            user=user,
            # Registration allows a 150-character name; the review byline is 80.
            name=(user.get_full_name() or user.email)[:80],
            is_published=False,
            **serializer.validated_data,
        )
        send_review_team_email(review)
        send_review_received_email(review)
        return Response(
            {'detail': 'Thank you. Your review will appear once our team approves it.'},
            status=status.HTTP_201_CREATED,
        )
