from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.notify import notify_team

from .models import ContactMessage, NewsletterSubscriber


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
        NewsletterSubscriber.objects.get_or_create(email=serializer.validated_data['email'].strip().lower())
        return Response({'detail': 'Subscribed.'}, status=status.HTTP_201_CREATED)


class ContactView(APIView):
    """POST /api/contact. Stored in the database and shown in admin; emailed only if EMAIL_HOST is set."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'contact'

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        msg = serializer.save()
        notify_team(
            subject='New contact message from the Axora Finds site',
            body=f'From: {msg.name} <{msg.email}>\n\n{msg.message}',
            reply_to=msg.email,
        )
        return Response({'detail': 'Message received.'}, status=status.HTTP_201_CREATED)
