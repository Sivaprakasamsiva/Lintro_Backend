"""Buy requests URLs."""
from django.urls import path
from .views import (
    BuyRequestCreateView, MyReceivedBuyRequestsView,
    MySentBuyRequestsView, BuyRequestDetailView,
    BuyRequestActionView, BuyRequestWithdrawView,
)

urlpatterns = [
    path('create/', BuyRequestCreateView.as_view(), name='buy-request-create'),
    path('received/', MyReceivedBuyRequestsView.as_view(), name='buy-requests-received'),
    path('sent/', MySentBuyRequestsView.as_view(), name='buy-requests-sent'),
    path('<uuid:pk>/', BuyRequestDetailView.as_view(), name='buy-request-detail'),
    path('<uuid:pk>/action/', BuyRequestActionView.as_view(), name='buy-request-action'),
    path('<uuid:pk>/withdraw/', BuyRequestWithdrawView.as_view(), name='buy-request-withdraw'),
]
