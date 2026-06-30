"""Notification serializers."""
from rest_framework import serializers
from .models import Notification, Announcement


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type',
            'related_id', 'related_type', 'is_read', 'read_at', 'created_at',
        ]
        read_only_fields = ['id', 'title', 'message', 'notification_type', 'related_id', 'related_type', 'read_at', 'created_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'body', 'is_active', 'created_at', 'expires_at']
        read_only_fields = ['id', 'created_at']
