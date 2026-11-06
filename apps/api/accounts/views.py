import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from config.emails import send_otp_email, send_welcome_email
from .models import OtpChallenge
from .serializers import AxoraTokenSerializer, RegisterSerializer, UserSerializer

logger = logging.getLogger(__name__)
User = get_user_model()
OTP_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


def _hash_code(code):
    # Keyed with SECRET_KEY, so a leaked database does not reveal codes by brute force.
    return hmac.new(settings.SECRET_KEY.encode('utf-8'), code.encode('utf-8'), hashlib.sha256).hexdigest()


def _issue_otp(user, purpose):
    code = f'{secrets.randbelow(1_000_000):06d}'
    # A new code replaces any earlier one. Expire the old ones (do not mark them used: "used"
    # means the person really verified, which is how a pending signup is told apart).
    OtpChallenge.objects.filter(user=user, purpose=purpose, consumed_at__isnull=True).update(expires_at=timezone.now())
    challenge = OtpChallenge.objects.create(
        user=user, purpose=purpose, code_hash=_hash_code(code),
        expires_at=timezone.now() + timedelta(minutes=OTP_MINUTES),
    )
    title = 'email verification' if purpose == OtpChallenge.SIGNUP else 'password reset'
    if not send_otp_email(user, code, title=title, expiry_minutes=OTP_MINUTES):
        challenge.delete()
        raise RuntimeError('We could not send the verification email. Please try again shortly.')


def _check_otp(email, code, purpose, *, consume=True):
    """Checks a code. Every check counts as an attempt; a correct one is used up only if ``consume``."""
    user = User.objects.filter(email__iexact=email.strip()).first()
    if not user:
        return None, None
    challenge = OtpChallenge.objects.filter(
        user=user, purpose=purpose, consumed_at__isnull=True,
    ).order_by('-created_at').first()
    if not challenge or not challenge.is_valid:
        return user, None
    challenge.attempts += 1
    challenge.save(update_fields=['attempts'])
    if secrets.compare_digest(challenge.code_hash, _hash_code(code.strip())):
        if consume:
            challenge.consumed_at = timezone.now()
            challenge.save(update_fields=['consumed_at'])
        return user, challenge
    return user, None


def _consume_otp(email, code, purpose):
    return _check_otp(email, code, purpose, consume=True)


class AuthThrottleMixin:
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class RegisterView(AuthThrottleMixin, APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            _issue_otp(user, OtpChallenge.SIGNUP)
        except RuntimeError as exc:
            if not serializer.pending_user:
                user.delete()  # nothing was sent, so do not leave a half-made account behind
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(
            {'detail': 'We sent a 6-digit verification code to your email.', 'email': user.email, 'purpose': 'signup'},
            status=status.HTTP_201_CREATED,
        )


class VerifyOtpView(AuthThrottleMixin, APIView):
    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        code = str(request.data.get('code', '')).strip()
        purpose = str(request.data.get('purpose', OtpChallenge.SIGNUP)).strip()
        if purpose not in (OtpChallenge.SIGNUP, OtpChallenge.PASSWORD_RESET) or not email or len(code) != 6 or not code.isdigit():
            return Response({'detail': 'Enter your email and the 6-digit code.'}, status=status.HTTP_400_BAD_REQUEST)
        invalid = Response({'detail': 'That code is invalid or expired. Request a new code and try again.'}, status=status.HTTP_400_BAD_REQUEST)
        if purpose == OtpChallenge.SIGNUP:
            candidate = User.objects.filter(email__iexact=email).first()
            if candidate and candidate.is_active:
                return Response({'detail': 'This account is already verified. You can log in.'}, status=status.HTTP_400_BAD_REQUEST)
            # Only a signup that is still waiting for its code can be activated this way. A
            # deactivated account can never switch itself back on with an emailed code.
            if not candidate or not candidate.is_pending_signup:
                return invalid
        # A password-reset code is only checked here; it is used up when the new password is set.
        user, challenge = _check_otp(email, code, purpose, consume=purpose == OtpChallenge.SIGNUP)
        if not challenge:
            return invalid
        if purpose == OtpChallenge.SIGNUP:
            user.is_active = True
            user.save(update_fields=['is_active'])
            try:
                send_welcome_email(user)
            except Exception:  # noqa: BLE001 - a welcome email must never undo a successful verification
                logger.exception('Could not send the welcome email to %s', user.email)
            refresh = RefreshToken.for_user(user)
            return Response({'detail': 'Email verified successfully.', 'access': str(refresh.access_token), 'refresh': str(refresh), 'user': UserSerializer(user).data})
        return Response({'detail': 'Code verified. You can now set a new password.'})


class ResendOtpView(AuthThrottleMixin, APIView):
    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        purpose = str(request.data.get('purpose', OtpChallenge.SIGNUP)).strip()
        if purpose not in (OtpChallenge.SIGNUP, OtpChallenge.PASSWORD_RESET):
            return Response({'detail': 'Invalid code purpose.'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(email__iexact=email).first()
        # Keep responses generic to avoid exposing account existence.
        if user and ((purpose == OtpChallenge.SIGNUP and user.is_pending_signup) or (purpose == OtpChallenge.PASSWORD_RESET and user.is_active)):
            try:
                _issue_otp(user, purpose)
            except RuntimeError:
                return Response({'detail': 'We could not send a code right now. Please try again shortly.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'detail': 'If the account is eligible, a new code has been sent.'})


class PasswordResetRequestView(AuthThrottleMixin, APIView):
    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            try:
                _issue_otp(user, OtpChallenge.PASSWORD_RESET)
            except RuntimeError:
                return Response({'detail': 'We could not send a code right now. Please try again shortly.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'detail': 'If an active account exists for that email, a password-reset code has been sent.'})


class PasswordResetConfirmView(AuthThrottleMixin, APIView):
    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        code = str(request.data.get('code', '')).strip()
        password = request.data.get('password', '')
        if not email or len(code) != 6 or not code.isdigit() or not isinstance(password, str):
            return Response({'detail': 'Enter your email, 6-digit code, and new password.'}, status=status.HTTP_400_BAD_REQUEST)
        # Check the code first but keep it alive: a too-weak password must not cost the person their code.
        user, challenge = _check_otp(email, code, OtpChallenge.PASSWORD_RESET, consume=False)
        if not user or not challenge or not user.is_active:
            return Response({'detail': 'That code is invalid or expired. Request a new code and try again.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(password, user=user)
        except DjangoValidationError as exc:
            return Response({'password': list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save(update_fields=['password'])
        OtpChallenge.objects.filter(user=user, purpose=OtpChallenge.PASSWORD_RESET, consumed_at__isnull=True).update(consumed_at=timezone.now())
        return Response({'detail': 'Your password has been reset. You can now log in.'})


class LoginView(TokenObtainPairView):
    serializer_class = AxoraTokenSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
