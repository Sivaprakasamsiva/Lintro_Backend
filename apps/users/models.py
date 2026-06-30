"""
User models for Lintro Marketplace.

A single account per user - every user can buy, sell, send/receive inquiries.
"""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom manager using email as the unique identifier."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Primary user account - both buyer and seller."""

    class Role(models.TextChoices):
        USER = 'user', _('User')
        MODERATOR = 'moderator', _('Moderator')
        ADMIN = 'admin', _('Admin')

    # Remove username field (use email instead)
    username = None
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    full_name = models.CharField(_('full name'), max_length=255)
    mobile_number = models.CharField(_('mobile number'), max_length=15, unique=True, db_index=True)
    whatsapp_number = models.CharField(_('WhatsApp number'), max_length=15, blank=True)
    profile_image = models.ImageField(
        upload_to='profile_images/',
        blank=True,
        null=True,
    )
    bio = models.TextField(_('bio'), blank=True, max_length=500)

    # Location
    address = models.TextField(_('address'), blank=True)
    district = models.CharField(_('district'), max_length=100, blank=True, db_index=True)
    state = models.CharField(_('state'), max_length=100, blank=True, db_index=True)
    country = models.CharField(_('country'), max_length=100, default='India')
    latitude = models.DecimalField(
        _('latitude'), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _('longitude'), max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Verification
    email_verified = models.BooleanField(_('email verified'), default=False)
    mobile_verified = models.BooleanField(_('mobile verified'), default=False)
    verified_seller = models.BooleanField(_('verified seller'), default=False)
    verified_seller_badge_date = models.DateTimeField(null=True, blank=True)

    # Status
    is_suspended = models.BooleanField(_('suspended'), default=False)
    is_banned = models.BooleanField(_('banned'), default=False)
    suspended_until = models.DateTimeField(null=True, blank=True)

    # Metadata
    role = models.CharField(
        _('role'), max_length=20, choices=Role.choices, default=Role.USER, db_index=True
    )
    last_active = models.DateTimeField(_('last active'), null=True, blank=True)
    joined_date = models.DateTimeField(_('joined date'), auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'mobile_number']

    objects = UserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        indexes = [
            models.Index(fields=['district', 'state']),
            models.Index(fields=['verified_seller']),
            models.Index(fields=['is_suspended']),
        ]

    def __str__(self):
        return f'{self.full_name} <{self.email}>'

    @property
    def is_buyer(self):
        return True

    @property
    def is_seller(self):
        return True

    @property
    def display_whatsapp(self):
        return self.whatsapp_number or self.mobile_number

    def can_post_listing(self):
        return self.is_active and not self.is_banned and (
            not self.is_suspended or
            (self.suspended_until and self.suspended_until < timezone.now())
        )


class OTPVerification(models.Model):
    """OTP codes for email/mobile verification."""

    class Purpose(models.TextChoices):
        EMAIL_REGISTER = 'email_register', _('Email Registration')
        EMAIL_LOGIN = 'email_login', _('Email Login')
        MOBILE_VERIFY = 'mobile_verify', _('Mobile Verification')
        PASSWORD_RESET = 'password_reset', _('Password Reset')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='otp_codes', null=True, blank=True
    )
    email = models.EmailField(null=True, blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    code = models.CharField(max_length=6)
    purpose = models.CharField(
        max_length=30, choices=Purpose.choices, default=Purpose.EMAIL_REGISTER
    )
    is_used = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['code', 'purpose'])]

    def is_valid(self):
        return (
            not self.is_used
            and not self.is_verified
            and self.attempts < 5
            and self.expires_at > timezone.now()
        )

    def __str__(self):
        target = self.email or self.mobile
        return f'OTP {self.purpose} for {target}'


class UserAuditLog(models.Model):
    """Audit log for sensitive user actions."""

    class Action(models.TextChoices):
        LOGIN = 'login', _('Login')
        LOGOUT = 'logout', _('Logout')
        LOGIN_FAILED = 'login_failed', _('Login Failed')
        REGISTER = 'register', _('Register')
        PASSWORD_CHANGE = 'password_change', _('Password Change')
        PASSWORD_RESET = 'password_reset', _('Password Reset')
        OTP_REQUEST = 'otp_request', _('OTP Request')
        OTP_VERIFY = 'otp_verify', _('OTP Verify')
        PROFILE_UPDATE = 'profile_update', _('Profile Update')
        SUSPEND = 'suspend', _('Suspend')
        BAN = 'ban', _('Ban')

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'action'])]

    def __str__(self):
        return f'{self.user} - {self.action} @ {self.created_at}'
