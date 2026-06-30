"""Complaint serializers."""
from rest_framework import serializers
from apps.users.serializers import UserPublicSerializer
from .models import Complaint


class ComplaintSerializer(serializers.ModelSerializer):
    complainant_email = serializers.CharField(source='complainant.email', read_only=True, default='Anonymous')
    reported_user_email = serializers.CharField(source='reported_user.email', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True, default='')
    handled_by_email = serializers.CharField(source='handled_by.email', read_only=True, default='')

    class Meta:
        model = Complaint
        fields = [
            'id', 'complainant_email', 'reported_user_email', 'product',
            'product_title', 'category', 'description', 'evidence_image',
            'status', 'admin_notes', 'resolution', 'handled_by_email',
            'handled_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'admin_notes', 'resolution', 'handled_by_email',
            'handled_at', 'created_at', 'updated_at',
        ]


class ComplaintCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = ['id', 'reported_user', 'product', 'category', 'description', 'evidence_image']
        read_only_fields = ['id']

    def validate_description(self, value):
        value = value.strip()
        if len(value) < 20:
            raise serializers.ValidationError('Please describe the issue in at least 20 characters.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user.is_authenticated and attrs.get('reported_user') == request.user:
            raise serializers.ValidationError({'detail': 'You cannot report yourself.'})
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['complainant'] = request.user
        return super().create(validated_data)


class ComplaintReviewSerializer(serializers.ModelSerializer):
    """Admin updates complaint status and takes action."""
    action = serializers.ChoiceField(
        choices=['warn', 'suspend', 'ban', 'dismiss', 'resolve'],
        write_only=True,
        required=False,
    )

    class Meta:
        model = Complaint
        fields = ['status', 'admin_notes', 'resolution', 'action']
