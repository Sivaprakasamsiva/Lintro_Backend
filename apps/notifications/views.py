"""Notification views."""
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, Announcement
from .serializers import NotificationSerializer, AnnouncementSerializer


class NotificationListView(generics.ListAPIView):
    """List user's notifications (paginated)."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        unread_only = self.request.query_params.get('unread') == 'true'
        if unread_only:
            qs = qs.filter(is_read=False)
        return qs


class UnreadNotificationCountView(APIView):
    """Get total unread notification count."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})


class NotificationMarkReadView(APIView):
    """Mark a specific notification as read."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notif = Notification.objects.filter(pk=pk, user=request.user).first()
        if not notif:
            return Response({'detail': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
        notif.mark_as_read()
        return Response({'message': 'Marked as read.'})


class NotificationMarkAllReadView(APIView):
    """Mark all notifications as read."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({'message': 'All notifications marked as read.'})


class ActiveAnnouncementsView(generics.ListAPIView):
    """List active announcements (public)."""

    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.utils import timezone
        qs = Announcement.objects.filter(is_active=True)
        return qs.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )


class AnnouncementCreateView(generics.CreateAPIView):
    """Admin: create announcement."""

    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        announcement = serializer.save(created_by=self.request.user)
        # Optionally broadcast notifications to all users (skip for large user base)
        return announcement
