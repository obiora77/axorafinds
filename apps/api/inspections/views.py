from django.core import signing
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.notify import notify_team
from pages.models import SiteSettings

from .models import Inspection, InspectionStatus, PaymentChoice, PaymentStatus
from .serializers import InspectionCreateSerializer

TOKEN_SALT = 'axora.inspection.payment-account'
TOKEN_MAX_AGE_SECONDS = 30 * 60


class InspectionCreateView(CreateAPIView):
    """
    POST /api/inspections. Public. The request is stored as pending and is never confirmed here.
    For a bank-transfer request the response carries a short-lived signed token; only the holder
    of that token can later ask GET /api/payments/account for the bank details.
    """

    serializer_class = InspectionCreateSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'inspections'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inspection = serializer.save()

        data = dict(serializer.data)
        if inspection.payment_choice == PaymentChoice.TRANSFER and inspection.fee_amount > 0:
            data['payment_token'] = signing.dumps({'i': inspection.pk}, salt=TOKEN_SALT)

        notify_team(
            subject=f'New inspection request {inspection.reference}',
            body=(
                f'{inspection.name} ({inspection.phone}, {inspection.email}) asked to inspect '
                f'"{inspection.property.title}" on {inspection.preferred_date}.\n'
                f'Fee: NGN {inspection.fee_amount} - {inspection.get_payment_choice_display()} - '
                f'{inspection.get_payment_status_display()}.\n'
                'Verify the payment in Django admin, then confirm or reject the inspection.'
            ),
            reply_to=inspection.email,
        )
        return Response(data, status=status.HTTP_201_CREATED)


class PaymentAccountView(APIView):
    """
    GET /api/payments/account. Returns the official bank account only to whoever just created a
    bank-transfer inspection (proved by the signed token from the create response), and only while
    that inspection is still pending and unpaid.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'payments'

    def get(self, request):
        denied = Response(
            {'detail': 'Payment details are not available for this request.'}, status=status.HTTP_403_FORBIDDEN
        )
        denied['Cache-Control'] = 'no-store'

        token = request.headers.get('X-Inspection-Token', '')
        try:
            payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE_SECONDS)
        except signing.BadSignature:  # includes expired tokens
            return denied

        inspection = get_object_or_404(Inspection, pk=payload.get('i'))
        if (
            inspection.payment_choice != PaymentChoice.TRANSFER
            or inspection.fee_amount <= 0
            or inspection.status != InspectionStatus.PENDING
            or inspection.payment_status != PaymentStatus.UNPAID
        ):
            return denied
        # If the request was made while signed in, only that same account may see the details.
        if inspection.user_id and (not request.user.is_authenticated or request.user.pk != inspection.user_id):
            return denied

        site = SiteSettings.load()
        if not site.has_account or not (site.is_live or settings.DEBUG):
            unavailable = Response(
                {'detail': 'Payment details are not available yet. Our team will contact you.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
            unavailable['Cache-Control'] = 'no-store'
            return unavailable

        response = Response(
            {
                'reference': inspection.reference,
                'amount': str(inspection.fee_amount),
                'bank_name': site.bank_name,
                'account_name': site.account_name,
                'account_number': site.account_number,
                'note': site.transfer_note,
            }
        )
        response['Cache-Control'] = 'no-store'
        return response
