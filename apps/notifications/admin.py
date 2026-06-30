"""Notifications admin."""
from django.contrib import admin
from .models import Notification, Announcement


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type')
    search_fields = ('user__email', 'title', 'message')
    readonly_fields = ('created_at', 'read_at')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_by', 'created_at', 'expires_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'body')
