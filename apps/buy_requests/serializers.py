"""Buy request serializers."""
import re
from rest_framework import serializers
from apps.products.serializers import ProductListSerializer
from .models import BuyRequest


PHONE_RE = re.compile(r'^\+?[0-9]{10,15}$')


class BuyRequestCreateSerializer(serializers.ModelSerializer):
    """Buyer submits a buy request (guest or registered)."""

    class Meta:
        model = BuyRequest
        fields = [
            'id', 'product', 'buyer_name', 'buyer_phone', 'buyer_whatsapp',
            'buyer_location', 'buyer_message', 'offered_price',
        ]
        read_only_fields = ['id']

    def validate_buyer_phone(self, value):
        if not PHONE_RE.match(value):
            raise serializers.ValidationError('Enter a valid phone number (10-15 digits).')
        return value

    def validate_buyer_whatsapp(self, value):
        if value and not PHONE_RE.match(value):
            raise serializers.ValidationError('Enter a valid WhatsApp number.')
        return value

    def validate(self, attrs):
        # Disallow buying own product
        request = self.context.get('request')
        product = attrs['product']
        if request and request.user.is_authenticated and product.seller_id == request.user.id:
            raise serializers.ValidationError({'detail': 'You cannot send a buy request for your own listing.'})
        if product.status not in ('available', 'pending', 'reserved'):
            raise serializers.ValidationError({'detail': 'This product is not available for buy requests.'})
        if attrs.get('offered_price') is not None and attrs['offered_price'] <= 0:
            raise serializers.ValidationError({'offered_price': 'Offered price must be greater than zero.'})
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['buyer'] = request.user
        return super().create(validated_data)


class BuyRequestListSerializer(serializers.ModelSerializer):
    """For seller's dashboard / buyer's sent list."""
    product = ProductListSerializer(read_only=True)
    buyer_email = serializers.CharField(source='buyer.email', read_only=True, default='')

    class Meta:
        model = BuyRequest
        fields = [
            'id', 'product', 'buyer_name', 'buyer_phone', 'buyer_whatsapp',
            'buyer_location', 'buyer_message', 'offered_price',
            'status', 'seller_response', 'deadline_at', 'time_remaining_seconds',
            'seller_responded_at', 'buyer_email', 'created_at',
        ]


class BuyRequestActionSerializer(serializers.Serializer):
    """Seller accepts/rejects with optional message."""
    action = serializers.ChoiceField(choices=['accept', 'reject'])
    seller_response = serializers.CharField(required=False, allow_blank=True)
