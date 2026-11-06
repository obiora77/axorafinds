from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Role

User = get_user_model()


class EmailNotVerified(APIException):
    """Correct email + password, but the emailed code was never entered."""

    status_code = 403
    default_code = 'email_not_verified'


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'role', 'is_staff']
        read_only_fields = fields

    def get_name(self, user) -> str:
        return user.get_full_name() or user.email


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    # Staff accounts are created by staff in admin, never through sign-up.
    role = serializers.ChoiceField(choices=[Role.SEEKER, Role.OWNER], default=Role.SEEKER)

    pending_user = None  # an earlier signup with this email that was never verified

    def validate_email(self, value):
        value = value.strip().lower()
        existing = User.objects.filter(email__iexact=value).first()
        if existing and not existing.is_pending_signup:
            raise serializers.ValidationError('An account with this email already exists.')
        # Someone who started signing up but never entered the code can simply start again,
        # instead of being locked out of their own address.
        self.pending_user = existing
        return value

    def validate(self, attrs):
        first, _, last = attrs['name'].strip().partition(' ')
        candidate = User(email=attrs['email'], first_name=first, last_name=last)
        try:
            validate_password(attrs['password'], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        first, _, last = validated_data['name'].strip().partition(' ')
        if self.pending_user:
            user = self.pending_user
            user.first_name, user.last_name = first, last.strip()
            user.phone = validated_data.get('phone', '')
            user.role = validated_data['role']
            user.set_password(validated_data['password'])
            user.is_active = False
            user.save()
            return user
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=first,
            last_name=last.strip(),
            phone=validated_data.get('phone', ''),
            role=validated_data['role'],
            is_active=False,
        )


class AxoraTokenSerializer(TokenObtainPairSerializer):
    """Login by email (any capitalisation) and return the user alongside the tokens."""

    def validate(self, attrs):
        attrs[self.username_field] = str(attrs[self.username_field]).strip().lower()
        pending = User.objects.filter(email__iexact=attrs[self.username_field]).first()
        if pending and pending.is_pending_signup and pending.check_password(attrs.get('password', '')):
            raise EmailNotVerified(
                {
                    'detail': 'Please verify your email address first. We can send you a new code.',
                    'code': 'email_not_verified',
                    'email': pending.email,
                }
            )
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
