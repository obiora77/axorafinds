from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Role

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'role']
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

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
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
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=first,
            last_name=last.strip(),
            phone=validated_data.get('phone', ''),
            role=validated_data['role'],
        )


class AxoraTokenSerializer(TokenObtainPairSerializer):
    """Login by email (any capitalisation) and return the user alongside the tokens."""

    def validate(self, attrs):
        attrs[self.username_field] = str(attrs[self.username_field]).strip().lower()
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
