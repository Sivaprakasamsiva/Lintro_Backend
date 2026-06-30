"""Verification URLs."""
from django.urls import path
from .views import (
    SubmitVerificationView,
    MyVerificationRequestsView,
    VerificationDetailView,
    AdminVerificationListView,
    AdminVerificationReviewView,
)

urlpatterns = [
    path('submit/', SubmitVerificationView.as_view(), name='submit-verification'),
    path('mine/', MyVerificationRequestsView.as_view(), name='my-verifications'),
    path('mine/<uuid:pk>/', VerificationDetailView.as_view(), name='my-verification-detail'),
    path('admin/', AdminVerificationListView.as_view(), name='admin-verifications'),
    path('admin/<uuid:pk>/review/', AdminVerificationReviewView.as_view(), name='admin-review-verification'),
]
