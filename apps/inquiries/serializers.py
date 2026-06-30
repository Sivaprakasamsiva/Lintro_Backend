# backend/apps/inquiries/serializers.py

"""Inquiry serializers."""
from rest_framework import serializers
from .models import Inquiry


class InquirySerializer(serializers.ModelSerializer):
    asker_email = serializers.CharField(source='asker.email', read_only=True, default='')
    seller_name = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = [
            'id', 'product', 'asker_name', 'asker_email',
            'question', 'answer', 'answered_at', 'is_public', 'created_at',
            'seller_name',  # <-- ADD THIS LINE
        ]
        read_only_fields = ['id', 'answered_at', 'created_at', 'asker_email', 'seller_name']

    def get_seller_name(self, obj):
        return obj.product.seller.full_name if obj.product.seller else ''


class InquiryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = ['id', 'product', 'asker_name', 'question', 'is_public']
        read_only_fields = ['id']

    def validate_question(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError('Question is too short.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            product = attrs['product']
            if product.seller_id == request.user.id:
                raise serializers.ValidationError({'detail': 'You cannot ask a question on your own listing.'})
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['asker'] = request.user
            if not validated_data.get('asker_name'):
                validated_data['asker_name'] = request.user.full_name
        return super().create(validated_data)


class InquiryAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = ['answer']

    def validate_answer(self, value):
        value = value.strip()
        if len(value) < 1:
            raise serializers.ValidationError('Answer cannot be empty.')
        return value
