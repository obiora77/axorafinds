"""The staff API behind the signed-in dashboard.

Every view is staff-only. The same business rules as Django admin are reused from the
models (``Property.publish``/``reject`` and ``Inspection.verify_payment``/``confirm``/
``reject``), so the dashboard cannot skip the payment check or publish a listing with no
photo. Each decision returns ``email_sent`` and ``email_error`` so staff can see whether
the matching email actually left the server.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role, User
from accounts.permissions import IsStaffRole
from config.emails import (
    email_status,
    last_email_error,
    send_inspection_confirmed_email,
    send_inspection_rejected_email,
    send_listing_published_email,
    send_listing_rejected_email,
    send_payment_verified_email,
    send_review_published_email,
    send_test_email,
)
from inspections.models import Inspection, InspectionStatus, PaymentStatus
from listings.models import Property, PropertyPhoto, Status
from pages.models import ContactMessage, NewsletterSubscriber, Review, SiteSettings

from .serializers import (
    StaffContactMessageSerializer,
    StaffInspectionSerializer,
    StaffPropertySerializer,
    StaffReviewSerializer,
    StaffSiteSettingsSerializer,
    StaffSubscriberSerializer,
    StaffUserSerializer,
)


class StaffPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class StaffAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStaffRole]


def _page(request, queryset, serializer_class) -> Response:
    paginator = StaffPagination()
    objects = paginator.paginate_queryset(queryset, request)
    data = serializer_class(objects, many=True, context={'request': request}).data
    return paginator.get_paginated_response(data)


def _validation_error(exc: DjangoValidationError) -> Response:
    messages = getattr(exc, 'messages', None) or [str(exc)]
    return Response({'detail': ' '.join(str(message) for message in messages)}, status=status.HTTP_400_BAD_REQUEST)


def _decision_payload(
    data: dict, sent: bool, *, attempted: bool = True, note: str | None = None
) -> Response:
    if sent or not attempted:
        error = None
    else:
        error = last_email_error() or 'The email could not be sent.'
    return Response({
        **data,
        'email_sent': bool(sent),
        'email_error': error,
        'email_note': note or (None if attempted else 'This record has no account email.'),
    })


def _listings():
    return (
        Property.objects.select_related('owner')
        .annotate(photos_count=Count('photos'))
        .prefetch_related(Prefetch('photos', queryset=PropertyPhoto.objects.order_by('position', 'id')))
    )


def _inspections():
    return Inspection.objects.select_related('property')


def _reviews():
    return Review.objects.select_related('user')


def _text_param(request, name: str) -> str:
    return (request.query_params.get(name) or '').strip()


class OverviewView(StaffAPIView):
    """GET /api/staff/overview: queue counts, recent items and email health."""

    def get(self, request):
        listings = Property.objects
        inspections = Inspection.objects
        reviews = Review.objects
        users = User.objects

        counts = {
            'listings': {
                'total': listings.count(),
                'pending': listings.filter(status=Status.PENDING).count(),
                'published': listings.filter(status=Status.PUBLISHED).count(),
                'rejected': listings.filter(status=Status.REJECTED).count(),
            },
            'inspections': {
                'total': inspections.count(),
                'pending': inspections.filter(status=InspectionStatus.PENDING).count(),
                'confirmed': inspections.filter(status=InspectionStatus.CONFIRMED).count(),
                'rejected': inspections.filter(status=InspectionStatus.REJECTED).count(),
                'awaiting_payment': inspections.filter(
                    status=InspectionStatus.PENDING,
                    payment_status=PaymentStatus.UNPAID,
                    fee_amount__gt=0,
                ).count(),
                'ready_to_confirm': inspections.filter(
                    status=InspectionStatus.PENDING,
                    payment_status__in=[PaymentStatus.VERIFIED, PaymentStatus.NOT_REQUIRED],
                ).count(),
            },
            'reviews': {
                'total': reviews.count(),
                'pending': reviews.filter(is_published=False).count(),
                'published': reviews.filter(is_published=True).count(),
            },
            'contacts': ContactMessage.objects.count(),
            'subscribers': NewsletterSubscriber.objects.count(),
            'users': {'total': users.count(), 'active': users.filter(is_active=True).count()},
        }

        recent = {
            'listings': StaffPropertySerializer(
                _listings().filter(status=Status.PENDING).order_by('-created_at')[:5],
                many=True,
                context={'request': request},
            ).data,
            'inspections': StaffInspectionSerializer(
                _inspections().filter(status=InspectionStatus.PENDING).order_by('-created_at')[:5],
                many=True,
                context={'request': request},
            ).data,
            'reviews': StaffReviewSerializer(
                _reviews().filter(is_published=False).order_by('-created_at')[:5],
                many=True,
                context={'request': request},
            ).data,
        }

        return Response({'counts': counts, 'recent': recent, 'email': email_status()})


class ListingListView(StaffAPIView):
    """GET /api/staff/listings?status=pending&q=..."""

    def get(self, request):
        queryset = _listings()
        status_filter = _text_param(request, 'status')
        if status_filter in dict(Status.choices):
            queryset = queryset.filter(status=status_filter)
        query = _text_param(request, 'q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(city__icontains=query)
                | Q(state__icontains=query)
                | Q(owner__email__icontains=query)
            )
        return _page(request, queryset.order_by('-created_at', '-id'), StaffPropertySerializer)


class ListingDecisionView(StaffAPIView):
    """POST /api/staff/listings/:id/publish or /reject."""

    decision = ''

    def post(self, request, pk):
        prop = get_object_or_404(_listings(), pk=pk)
        try:
            if self.decision == 'publish':
                prop.publish(request.user)
                sent = send_listing_published_email(prop)
            else:
                prop.reject(request.user)
                sent = send_listing_rejected_email(prop)
        except DjangoValidationError as exc:
            return _validation_error(exc)

        prop = get_object_or_404(_listings(), pk=pk)
        data = StaffPropertySerializer(prop, context={'request': request}).data
        return _decision_payload(data, sent)


class ListingPublishView(ListingDecisionView):
    decision = 'publish'


class ListingRejectView(ListingDecisionView):
    decision = 'reject'


class ListingResendEmailView(StaffAPIView):
    """POST /api/staff/listings/:id/resend-email.

    A decision is saved even when the mail server is down. This sends the email for
    the listing's current status again, without changing that status.
    """

    def post(self, request, pk):
        prop = get_object_or_404(_listings(), pk=pk)
        if prop.status == Status.PUBLISHED:
            sent = send_listing_published_email(prop)
            note = 'The published email was sent again.'
        elif prop.status == Status.REJECTED:
            sent = send_listing_rejected_email(prop)
            note = 'The rejection email was sent again.'
        else:
            return Response(
                {'detail': 'This listing has no decision email yet. Publish or reject it first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = StaffPropertySerializer(prop, context={'request': request}).data
        return _decision_payload(data, sent, note=note)


class InspectionListView(StaffAPIView):
    """GET /api/staff/inspections?status=pending&payment_status=unpaid&q=..."""

    def get(self, request):
        queryset = _inspections()
        status_filter = _text_param(request, 'status')
        if status_filter in dict(InspectionStatus.choices):
            queryset = queryset.filter(status=status_filter)
        payment_filter = _text_param(request, 'payment_status')
        if payment_filter in dict(PaymentStatus.choices):
            queryset = queryset.filter(payment_status=payment_filter)
        query = _text_param(request, 'q')
        if query:
            queryset = queryset.filter(
                Q(reference__icontains=query)
                | Q(name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone__icontains=query)
                | Q(property__title__icontains=query)
            )
        return _page(request, queryset.order_by('-created_at'), StaffInspectionSerializer)


class InspectionDecisionView(StaffAPIView):
    """POST /api/staff/inspections/:id/verify-payment, /confirm or /reject."""

    decision = ''

    def post(self, request, pk):
        inspection = get_object_or_404(_inspections(), pk=pk)
        try:
            if self.decision == 'verify-payment':
                inspection.verify_payment(request.user)
                sent = send_payment_verified_email(inspection)
            elif self.decision == 'confirm':
                inspection.confirm(request.user)
                sent = send_inspection_confirmed_email(inspection)
            else:
                inspection.reject(request.user)
                sent = send_inspection_rejected_email(inspection)
        except DjangoValidationError as exc:
            return _validation_error(exc)

        inspection.refresh_from_db()
        data = StaffInspectionSerializer(inspection, context={'request': request}).data
        return _decision_payload(data, sent)


class InspectionVerifyPaymentView(InspectionDecisionView):
    decision = 'verify-payment'


class InspectionConfirmView(InspectionDecisionView):
    decision = 'confirm'


class InspectionRejectView(InspectionDecisionView):
    decision = 'reject'


class InspectionResendEmailView(StaffAPIView):
    """POST /api/staff/inspections/:id/resend-email.

    The inspection stays exactly as it is; only the email for its current state is
    sent again. Useful after a temporary mail outage.
    """

    def post(self, request, pk):
        inspection = get_object_or_404(_inspections(), pk=pk)
        if inspection.status == InspectionStatus.CONFIRMED:
            sent = send_inspection_confirmed_email(inspection)
            note = 'The confirmation email was sent again.'
        elif inspection.status == InspectionStatus.REJECTED:
            sent = send_inspection_rejected_email(inspection)
            note = 'The rejection email was sent again.'
        elif inspection.payment_status == PaymentStatus.VERIFIED and inspection.fee_amount > 0:
            sent = send_payment_verified_email(inspection)
            note = 'The payment-verified email was sent again.'
        else:
            return Response(
                {'detail': 'This inspection has no decision email yet. Verify, confirm or reject it first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = StaffInspectionSerializer(inspection, context={'request': request}).data
        return _decision_payload(data, sent, note=note)


class ReviewListView(StaffAPIView):
    """GET /api/staff/reviews?status=pending|published&q=..."""

    def get(self, request):
        queryset = _reviews()
        status_filter = _text_param(request, 'status')
        if status_filter == 'published':
            queryset = queryset.filter(is_published=True)
        elif status_filter == 'pending':
            queryset = queryset.filter(is_published=False)
        query = _text_param(request, 'q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(location__icontains=query)
                | Q(text__icontains=query)
                | Q(user__email__icontains=query)
            )
        return _page(request, queryset.order_by('-created_at'), StaffReviewSerializer)


class ReviewPublishView(StaffAPIView):
    """POST /api/staff/reviews/:id/publish (sends the author an email when linked)."""

    def post(self, request, pk):
        review = get_object_or_404(_reviews(), pk=pk)
        if review.is_published:
            data = StaffReviewSerializer(review, context={'request': request}).data
            return _decision_payload(
                data,
                False,
                attempted=False,
                note='This review is already published; no email was sent again.',
            )
        review.is_published = True
        review.save(update_fields=['is_published'])
        attempted = review.user_id is not None
        sent = send_review_published_email(review)
        data = StaffReviewSerializer(review, context={'request': request}).data
        return _decision_payload(data, sent, attempted=attempted)


class ReviewUnpublishView(StaffAPIView):
    """POST /api/staff/reviews/:id/unpublish."""

    def post(self, request, pk):
        review = get_object_or_404(_reviews(), pk=pk)
        review.is_published = False
        review.save(update_fields=['is_published'])
        data = StaffReviewSerializer(review, context={'request': request}).data
        return Response({**data, 'email_sent': False, 'email_error': None, 'email_note': None})


class ReviewResendEmailView(StaffAPIView):
    """POST /api/staff/reviews/:id/resend-email: resend the published-email notice."""

    def post(self, request, pk):
        review = get_object_or_404(_reviews(), pk=pk)
        if not review.is_published:
            return Response(
                {'detail': 'Publish the review before resending its email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not review.user_id:
            return Response(
                {'detail': 'This review has no linked account, so there is no address to email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sent = send_review_published_email(review)
        data = StaffReviewSerializer(review, context={'request': request}).data
        return _decision_payload(data, sent, note='The published email was sent again.')


class ContactMessageListView(StaffAPIView):
    """GET /api/staff/messages?q=..."""

    def get(self, request):
        queryset = ContactMessage.objects.all()
        query = _text_param(request, 'q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(email__icontains=query) | Q(message__icontains=query)
            )
        return _page(request, queryset.order_by('-created_at'), StaffContactMessageSerializer)


class ContactMessageDetailView(StaffAPIView):
    """DELETE /api/staff/messages/:id."""

    def delete(self, request, pk):
        get_object_or_404(ContactMessage, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriberListView(StaffAPIView):
    """GET /api/staff/subscribers?q=..."""

    def get(self, request):
        queryset = NewsletterSubscriber.objects.all()
        query = _text_param(request, 'q')
        if query:
            queryset = queryset.filter(email__icontains=query)
        return _page(request, queryset.order_by('-created_at'), StaffSubscriberSerializer)


class SubscriberDetailView(StaffAPIView):
    """DELETE /api/staff/subscribers/:id."""

    def delete(self, request, pk):
        get_object_or_404(NewsletterSubscriber, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SiteSettingsView(StaffAPIView):
    """GET/PUT /api/staff/settings: the official bank account, same row as Django admin."""

    def get(self, request):
        return Response(StaffSiteSettingsSerializer(SiteSettings.load()).data)

    def put(self, request):
        site = SiteSettings.load()
        serializer = StaffSiteSettingsSerializer(site, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserListView(StaffAPIView):
    """GET /api/staff/users?role=owner&q=...: read-only account overview."""

    def get(self, request):
        queryset = User.objects.all()
        role_filter = _text_param(request, 'role')
        if role_filter in dict(Role.choices):
            queryset = queryset.filter(role=role_filter)
        query = _text_param(request, 'q')
        if query:
            queryset = queryset.filter(
                Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
            )
        return _page(request, queryset.order_by('-date_joined'), StaffUserSerializer)


class EmailStatusView(StaffAPIView):
    """GET /api/staff/email: backend, from address and missing templates."""

    def get(self, request):
        return Response(email_status())


class EmailTestView(StaffAPIView):
    """POST /api/staff/email/test {to} -> sends a real message and returns the exact error."""

    def post(self, request):
        raw = (request.data.get('to') or request.user.email or '').strip()
        try:
            to = serializers.EmailField().run_validation(raw)
        except serializers.ValidationError:
            return Response({'detail': 'Enter a valid email address.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sent = send_test_email(to, raise_errors=True)
        except Exception as exc:  # noqa: BLE001 - the dashboard shows the exact cause
            return Response(
                {'sent': False, 'to': to, 'error': f'{type(exc).__name__}: {exc}', 'status': email_status()}
            )
        return Response(
            {'sent': bool(sent), 'to': to, 'error': None if sent else last_email_error(), 'status': email_status()}
        )
