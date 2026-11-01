from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Role(models.TextChoices):
    SEEKER = 'seeker', 'Seeker'
    OWNER = 'owner', 'Owner'
    STAFF = 'staff', 'Staff'


STAFF_PERMISSIONS = {
    'listings': {'property': ('view', 'change')},
    'inspections': {'inspection': ('view', 'change')},
    'pages': {
        'review': ('view', 'change'),
        'sitesettings': ('view', 'change'),
        'contactmessage': ('view', 'delete'),
        'newslettersubscriber': ('view', 'delete'),
    },
}


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError('An email address is required.')
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role=Role.STAFF, is_active=True)
        return self._create(email, password, **extra)


class User(AbstractUser):
    """Email-login user with one of three roles: seeker, owner, staff."""

    username = None
    email = models.EmailField('email address', unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.SEEKER)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: list[str] = []
    objects = UserManager()

    def save(self, *args, **kwargs):
        if self.role == Role.STAFF:
            self.is_staff = True
        super().save(*args, **kwargs)
        if self.role == Role.STAFF and not self.is_superuser:
            self._grant_staff_permissions()

    def _grant_staff_permissions(self):
        from django.contrib.auth.models import Permission
        query = Q()
        for app_label, models_ in STAFF_PERMISSIONS.items():
            for model, actions in models_.items():
                for action in actions:
                    query |= Q(content_type__app_label=app_label, content_type__model=model, codename=f'{action}_{model}')
        permissions = Permission.objects.filter(query)
        if permissions:
            self.user_permissions.add(*permissions)

    def __str__(self):
        return self.email


class OtpChallenge(models.Model):
    SIGNUP = 'signup'
    PASSWORD_RESET = 'password_reset'
    PURPOSE_CHOICES = [(SIGNUP, 'Signup verification'), (PASSWORD_RESET, 'Password reset')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_challenges')
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'purpose', 'created_at'])]

    @property
    def is_valid(self):
        return self.consumed_at is None and self.expires_at > timezone.now() and self.attempts < 5
