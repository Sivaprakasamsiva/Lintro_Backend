"""Complaints URLs."""
from django.urls import path
from .views import (
    ComplaintCreateView, MyComplaintsView,
    AdminComplaintListView, ComplaintReviewView,
)

urlpatterns = [
    path('create/', ComplaintCreateView.as_view(), name='complaint-create'),
    path('mine/', MyComplaintsView.as_view(), name='complaint-mine'),
    path('admin/', AdminComplaintListView.as_view(), name='complaint-admin-list'),
    path('admin/<uuid:pk>/review/', ComplaintReviewView.as_view(), name='complaint-review'),
]
