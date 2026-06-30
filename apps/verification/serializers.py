"""Verification serializers."""
import re
from rest_framework import serializers
from .models import VerificationRequest


PINCODE_RE = re.compile(r'^[1-9][0-9]{5}$')
MOBILE_RE = re.compile(r'^\+?[0-9]{10,15}$')


class VerificationRequestSerializer(serializers.ModelSerializer):
    """Serializer for submitting a verification request."""

    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'id_type', 'id_number',
            'id_front_image', 'id_back_image', 'selfie_image',
            'whatsapp_number', 'address_line1', 'address_line2',
            'district', 'state', 'pincode', 'country',
            'status', 'submitted_at', 'reviewed_at', 'admin_notes',
            'rejection_reason',
        ]
        read_only_fields = [
            'id', 'status', 'submitted_at', 'reviewed_at', 'admin_notes', 'rejection_reason',
        ]

    def validate_whatsapp_number(self, value):
        if not MOBILE_RE.match(value):
            raise serializers.ValidationError('Enter a valid WhatsApp number.')
        return value

    def validate_pincode(self, value):
        if not PINCODE_RE.match(value):
            raise serializers.ValidationError('Enter a valid 6-digit Indian pincode.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if request:
            pending = VerificationRequest.objects.filter(
                user=request.user,
                status=VerificationRequest.Status.PENDING,
            )
            if self.instance:
                pending = pending.exclude(pk=self.instance.pk)
            if pending.exists():
                raise serializers.ValidationError(
                    'You already have a pending verification request.'
                )
            if request.user.verified_seller:
                raise serializers.ValidationError('You are already a verified seller.')
        return attrs


class VerificationReviewSerializer(serializers.ModelSerializer):
    """Serializer for admin to approve/reject."""

    class Meta:
        model = VerificationRequest
        fields = ['status', 'admin_notes', 'rejection_reason']

    def validate(self, attrs):
        if attrs.get('status') == VerificationRequest.Status.REJECTED and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({'rejection_reason': 'Rejection reason is required when rejecting.'})
        return attrs


class VerificationRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'user_email', 'user_name', 'id_type', 'status',
            'submitted_at', 'reviewed_at',
        ]
