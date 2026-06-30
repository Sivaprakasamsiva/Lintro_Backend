"""Verification views."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.utils import create_notification
from apps.users.models import UserAuditLog
from apps.users.utils import log_audit

from .models import VerificationRequest
from .serializers import (
    VerificationRequestSerializer,
    VerificationReviewSerializer,
    VerificationRequestListSerializer,
)


class SubmitVerificationView(generics.CreateAPIView):
    """User submits a verification request."""

    serializer_class = VerificationRequestSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MyVerificationRequestsView(generics.ListAPIView):
    """User lists their own verification requests."""

    serializer_class = VerificationRequestListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VerificationRequest.objects.filter(user=self.request.user)


class VerificationDetailView(generics.RetrieveAPIView):
    """User views their own verification request details."""

    serializer_class = VerificationRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VerificationRequest.objects.filter(user=self.request.user)


class AdminVerificationListView(generics.ListAPIView):
    """Admin lists all pending/all verification requests."""

    serializer_class = VerificationRequestListSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = VerificationRequest.objects.select_related('user').all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class AdminVerificationReviewView(APIView):
    """Admin approves or rejects a verification request."""

    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        verification = get_object_or_404(VerificationRequest, pk=pk)
        if verification.status != VerificationRequest.Status.PENDING:
            return Response(
                {'detail': 'This verification has already been reviewed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = VerificationReviewSerializer(verification, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        verified = serializer.validated_data['status'] == VerificationRequest.Status.APPROVED

        verification.status = serializer.validated_data['status']
        verification.admin_notes = serializer.validated_data.get('admin_notes', '')
        verification.rejection_reason = serializer.validated_data.get('rejection_reason', '')
        verification.reviewed_at = timezone.now()
        verification.reviewed_by = request.user
        verification.save()

        if verified:
            verification.user.verified_seller = True
            verification.user.verified_seller_badge_date = timezone.now()
            verification.user.save(update_fields=['verified_seller', 'verified_seller_badge_date'])
            create_notification(
                user=verification.user,
                title='Seller Verification Approved!',
                message='Congratulations! Your account is now a Verified Seller. The verified badge will appear on your listings.',
                notification_type='verification_approved',
                related_id=str(verification.id),
            )
        else:
            create_notification(
                user=verification.user,
                title='Seller Verification Rejected',
                message=f'Your verification request was rejected. Reason: {verification.rejection_reason}',
                notification_type='verification_rejected',
                related_id=str(verification.id),
            )

        log_audit(request, verification.user, 'verify_approved' if verified else 'verify_rejected', {
            'verification_id': str(verification.id),
        })
        return Response(VerificationRequestSerializer(verification).data)
