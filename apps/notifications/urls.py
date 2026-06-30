"""Notifications URLs."""
from django.urls import path
from .views import (
    NotificationListView, UnreadNotificationCountView,
    NotificationMarkReadView, NotificationMarkAllReadView,
    ActiveAnnouncementsView, AnnouncementCreateView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', UnreadNotificationCountView.as_view(), name='notification-unread-count'),
    path('<uuid:pk>/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('announcements/', ActiveAnnouncementsView.as_view(), name='announcements'),
    path('announcements/create/', AnnouncementCreateView.as_view(), name='announcement-create'),
]
