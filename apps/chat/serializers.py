# backend/apps/chat/serializers.py
"""Chat serializers."""
from rest_framework import serializers
from apps.users.serializers import UserPublicSerializer
from apps.products.serializers import ProductListSerializer
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'body', 'is_read', 'read_at', 'created_at']
        read_only_fields = ['id', 'sender', 'is_read', 'read_at', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id', 'product', 'other_participant', 'last_message',
            'unread_count', 'created_at', 'updated_at', 'last_message_at',
        ]

    def get_other_participant(self, obj):
        user = self.context['request'].user
        return UserPublicSerializer(obj.other_participant(user)).data

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if not last:
            return None
        return {
            'id': str(last.id),
            'body': last.body[:100],
            'sender_id': last.sender_id,
            'created_at': last.created_at,
        }

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()


class StartConversationSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    initial_message = serializers.CharField(min_length=1, max_length=2000)


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(min_length=1, max_length=2000)
