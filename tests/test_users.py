"""
Unit tests for the users app.
"""
import pytest
from django.core.exceptions import ValidationError
from apps.users.models import User, OTPVerification, UserAuditLog
from apps.users.serializers import RegisterSerializer, validate_mobile


@pytest.mark.unit
@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self, db):
        user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            full_name='Test User',
            mobile_number='+919999999999',
        )
        assert user.email == 'test@example.com'
        assert user.check_password('TestPass123!')
        assert user.role == User.Role.USER
        assert user.is_buyer
        assert user.is_seller
        assert not user.email_verified
        assert not user.verified_seller

    def test_create_superuser(self, db):
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
            full_name='Admin',
            mobile_number='+918888888888',
        )
        assert user.is_staff
        assert user.is_superuser
        assert user.role == User.Role.ADMIN
        assert user.email_verified

    def test_email_unique(self, db, regular_user):
        with pytest.raises(Exception):
            User.objects.create_user(
                email='user@example.com',
                password='TestPass123!',
                full_name='Dup User',
                mobile_number='+915555555555',
            )

    def test_mobile_unique(self, db, regular_user):
        with pytest.raises(Exception):
            User.objects.create_user(
                email='other@example.com',
                password='TestPass123!',
                full_name='Other',
                mobile_number='+917777777777',
            )

    def test_can_post_listing_active_user(self, db, regular_user):
        assert regular_user.can_post_listing() is True

    def test_can_post_listing_banned_user(self, db, regular_user):
        regular_user.is_banned = True
        regular_user.save()
        assert regular_user.can_post_listing() is False

    def test_can_post_listing_suspended_user(self, db, regular_user):
        from django.utils import timezone
        regular_user.is_suspended = True
        regular_user.suspended_until = timezone.now() + timezone.timedelta(days=3)
        regular_user.save()
        assert regular_user.can_post_listing() is False

    def test_can_post_listing_expired_suspension(self, db, regular_user):
        from django.utils import timezone
        regular_user.is_suspended = True
        regular_user.suspended_until = timezone.now() - timezone.timedelta(days=1)
        regular_user.save()
        # Should be allowed (suspension expired)
        assert regular_user.can_post_listing() is True

    def test_display_whatsapp_falls_back_to_mobile(self, db):
        user = User.objects.create_user(
            email='wa@example.com', password='TestPass123!', full_name='WA User',
            mobile_number='+919999999999',
        )
        assert user.display_whatsapp == '+919999999999'


@pytest.mark.unit
@pytest.mark.django_db
class TestMobileValidation:
    def test_valid_mobile_indian(self):
        assert validate_mobile('+919876543210') == '+919876543210'

    def test_valid_mobile_10_digit(self):
        assert validate_mobile('9876543210') == '9876543210'

    def test_invalid_mobile_short(self):
        with pytest.raises(Exception):
            validate_mobile('123')

    def test_invalid_mobile_with_letters(self):
        with pytest.raises(Exception):
            validate_mobile('+91abc1234567')


@pytest.mark.unit
@pytest.mark.django_db
class TestRegisterSerializer:
    def test_password_mismatch(self, db, user_data):
        user_data['password2'] = 'Different123!'
        serializer = RegisterSerializer(data=user_data)
        assert not serializer.is_valid()
        assert 'password2' in serializer.errors

    def test_duplicate_email(self, db, regular_user, user_data):
        user_data['email'] = 'user@example.com'
        serializer = RegisterSerializer(data=user_data)
        assert not serializer.is_valid()
        assert 'email' in serializer.errors

    def test_weak_password(self, db, user_data):
        user_data['password'] = '123'
        user_data['password2'] = '123'
        serializer = RegisterSerializer(data=user_data)
        assert not serializer.is_valid()

    def test_creates_inactive_user(self, db, user_data):
        serializer = RegisterSerializer(data=user_data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert not user.is_active
        assert not user.email_verified
        assert user.check_password('TestPass123!')


@pytest.mark.unit
@pytest.mark.django_db
class TestOTPModel:
    def test_otp_valid_within_window(self, db, regular_user):
        from django.utils import timezone
        otp = OTPVerification.objects.create(
            user=regular_user, email=regular_user.email, code='123456',
            purpose=OTPVerification.Purpose.EMAIL_REGISTER,
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        assert otp.is_valid()

    def test_otp_invalid_after_expiry(self, db, regular_user):
        from django.utils import timezone
        otp = OTPVerification.objects.create(
            user=regular_user, email=regular_user.email, code='123456',
            purpose=OTPVerification.Purpose.EMAIL_REGISTER,
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        assert not otp.is_valid()

    def test_otp_invalid_after_use(self, db, regular_user):
        from django.utils import timezone
        otp = OTPVerification.objects.create(
            user=regular_user, email=regular_user.email, code='123456',
            purpose=OTPVerification.Purpose.EMAIL_REGISTER,
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            is_used=True,
        )
        assert not otp.is_valid()

    def test_otp_invalid_after_max_attempts(self, db, regular_user):
        from django.utils import timezone
        otp = OTPVerification.objects.create(
            user=regular_user, email=regular_user.email, code='123456',
            purpose=OTPVerification.Purpose.EMAIL_REGISTER,
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            attempts=5,
        )
        assert not otp.is_valid()
