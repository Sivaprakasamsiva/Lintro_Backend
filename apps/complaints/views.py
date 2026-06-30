"""Complaint views."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.utils import create_notification
from apps.users.models import User

from .models import Complaint
from .serializers import (
    ComplaintSerializer, ComplaintCreateSerializer, ComplaintReviewSerializer,
)


class ComplaintCreateView(generics.CreateAPIView):
    """File a complaint against a user (auth optional)."""

    serializer_class = ComplaintCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = serializer.save()
        # Notify all admins
        for admin in User.objects.filter(is_staff=True, is_active=True):
            create_notification(
                user=admin,
                title=f'New complaint: {complaint.get_category_display()}',
                message=complaint.description[:200],
                notification_type='complaint_filed',
                related_id=str(complaint.id),
            )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)


class MyComplaintsView(generics.ListAPIView):
    """List complaints filed by current user."""

    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Complaint.objects.filter(complainant=self.request.user)


class AdminComplaintListView(generics.ListAPIView):
    """Admin lists all complaints."""

    serializer_class = ComplaintSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = Complaint.objects.select_related('complainant', 'reported_user', 'product', 'handled_by')
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs


class ComplaintReviewView(APIView):
    """Admin reviews a complaint and takes action (warn/suspend/ban/dismiss/resolve)."""

    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        complaint = get_object_or_404(Complaint, pk=pk)
        serializer = ComplaintReviewSerializer(complaint, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data.pop('action', None)
        complaint.status = serializer.validated_data.get('status', complaint.status)
        complaint.admin_notes = serializer.validated_data.get('admin_notes', complaint.admin_notes)
        complaint.resolution = serializer.validated_data.get('resolution', complaint.resolution)
        complaint.handled_by = request.user
        complaint.handled_at = timezone.now()
        complaint.save()

        reported_user = complaint.reported_user
        if action == 'warn':
            create_notification(
                user=reported_user,
                title='Warning from Lintro',
                message=f'You have received a warning. Reason: {complaint.resolution or complaint.admin_notes}',
                notification_type='complaint_warning',
                related_id=str(complaint.id),
            )
            complaint.status = Complaint.Status.WARNED
            complaint.save(update_fields=['status'])
        elif action == 'suspend':
            reported_user.is_suspended = True
            reported_user.suspended_until = timezone.now() + timezone.timedelta(days=7)
            reported_user.save(update_fields=['is_suspended', 'suspended_until'])
            complaint.status = Complaint.Status.SUSPENDED
            complaint.save(update_fields=['status'])
            create_notification(
                user=reported_user,
                title='Account Suspended (7 days)',
                message=f'Your account has been suspended for 7 days. Reason: {complaint.resolution or complaint.admin_notes}',
                notification_type='complaint_suspended',
                related_id=str(complaint.id),
            )
        elif action == 'ban':
            reported_user.is_banned = True
            reported_user.save(update_fields=['is_banned'])
            complaint.status = Complaint.Status.BANNED
            complaint.save(update_fields=['status'])
        elif action == 'dismiss':
            complaint.status = Complaint.Status.DISMISSED
            complaint.save(update_fields=['status'])
        elif action == 'resolve':
            complaint.status = Complaint.Status.RESOLVED
            complaint.save(update_fields=['status'])

        if complaint.complainant:
            create_notification(
                user=complaint.complainant,
                title='Complaint Update',
                message=f'Your complaint has been updated to: {complaint.get_status_display()}',
                notification_type='complaint_update',
                related_id=str(complaint.id),
            )

        return Response(ComplaintSerializer(complaint).data)
