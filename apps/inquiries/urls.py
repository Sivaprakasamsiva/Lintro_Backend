"""Inquiries URLs."""
from django.urls import path
from .views import InquiryListView, InquiryCreateView, InquiryAnswerView

urlpatterns = [
    path('product/<uuid:product_id>/', InquiryListView.as_view(), name='inquiry-list'),
    path('create/', InquiryCreateView.as_view(), name='inquiry-create'),
    path('<uuid:pk>/answer/', InquiryAnswerView.as_view(), name='inquiry-answer'),
]
