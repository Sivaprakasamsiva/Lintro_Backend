"""
User serializers for Lintro Marketplace.
"""
import re
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.db import transaction

from .models import User, OTPVerification


MOBILE_RE = re.compile(r'^\+?[0-9]{10,15}$')


def validate_mobile(value):
    if not MOBILE_RE.match(value):
        raise serializers.ValidationError('Enter a valid mobile number (10-15 digits).')
    return value


class UserSerializer(serializers.ModelSerializer):
    """Public-facing user serializer."""

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'mobile_number', 'whatsapp_number',
            'profile_image', 'bio', 'address', 'district', 'state', 'country',
            'latitude', 'longitude', 'email_verified', 'mobile_verified',
            'verified_seller', 'verified_seller_badge_date',
            'role', 'joined_date', 'is_active',
        ]
        read_only_fields = [
            'id', 'email_verified', 'mobile_verified', 'verified_seller',
            'verified_seller_badge_date', 'role', 'joined_date', 'is_active',
        ]


class UserPublicSerializer(serializers.ModelSerializer):
    """Limited public view of a user (shown to other users)."""

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'profile_image', 'district', 'state',
            'verified_seller', 'verified_seller_badge_date', 'joined_date',
        ]


class RegisterSerializer(serializers.ModelSerializer):
    """Registration serializer - email OTP required to activate account."""

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    mobile_number = serializers.CharField(validators=[validate_mobile])

    class Meta:
        model = User
        fields = [
            'email', 'full_name', 'mobile_number', 'password', 'password2',
            'whatsapp_number', 'district', 'state',
        ]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def validate_mobile_number(self, value):
        if User.objects.filter(mobile_number=value).exists():
            raise serializers.ValidationError('An account with this mobile number already exists.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': 'Passwords do not match.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = False  # Activate only after email OTP verification
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT token with extra user info."""

    username_field = User.EMAIL_FIELD

    def validate(self, attrs):
        email = attrs.get('username') or attrs.get('email')
        password = attrs.get('password')
        if not email or not password:
            raise serializers.ValidationError({'detail': 'Email and password required.'})

        try:
            user_obj = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            user_obj = None

        if user_obj is None:
            raise serializers.ValidationError({'detail': 'No active account found.'})

        if not user_obj.check_password(password):
            raise serializers.ValidationError({'detail': 'Invalid credentials.'})

        if not user_obj.is_active:
            raise serializers.ValidationError({'detail': 'Account not activated. Verify your email OTP.'})

        if user_obj.is_banned:
            raise serializers.ValidationError({'detail': 'Account banned. Contact support.'})

        if user_obj.is_suspended:
            if user_obj.suspended_until and user_obj.suspended_until > timezone.now():
                raise serializers.ValidationError({
                    'detail': f'Account suspended until {user_obj.suspended_until}.'
                })
            user_obj.is_suspended = False
            user_obj.suspended_until = None
            user_obj.save(update_fields=['is_suspended', 'suspended_until'])

        # Call parent with the correct field name expected by SimpleJWT
        data = super().validate({self.username_field: user_obj.email, 'password': password})
        data['user'] = UserSerializer(user_obj).data
        return data


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    mobile = serializers.CharField(required=False)
    purpose = serializers.ChoiceField(
        choices=OTPVerification.Purpose.choices,
        default=OTPVerification.Purpose.EMAIL_REGISTER,
    )

    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('mobile'):
            raise serializers.ValidationError('Either email or mobile is required.')
        return attrs


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    mobile = serializers.CharField(required=False)
    code = serializers.CharField(min_length=4, max_length=8)
    purpose = serializers.ChoiceField(
        choices=OTPVerification.Purpose.choices,
        default=OTPVerification.Purpose.EMAIL_REGISTER,
    )

    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('mobile'):
            raise serializers.ValidationError('Either email or mobile is required.')
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Profile update serializer."""

    class Meta:
        model = User
        fields = [
            'full_name', 'whatsapp_number', 'profile_image', 'bio',
            'address', 'district', 'state', 'country',
            'latitude', 'longitude', 'mobile_number',
        ]

    def validate_mobile_number(self, value):
        validate_mobile(value)
        qs = User.objects.filter(mobile_number=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Mobile number already in use.')
        return value


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=4, max_length=8)
    new_password = serializers.CharField(validators=[validate_password])
