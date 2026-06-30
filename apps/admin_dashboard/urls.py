"""Admin dashboard URLs."""
from django.urls import path
from .views import (
    DashboardMetricsView, AdminUserListView, AdminUserActionView,
    AdminProductListView, AdminProductActionView,
)

urlpatterns = [
    path('metrics/', DashboardMetricsView.as_view(), name='admin-metrics'),
    path('users/', AdminUserListView.as_view(), name='admin-users'),
    path('users/<int:user_id>/action/', AdminUserActionView.as_view(), name='admin-user-action'),
    path('products/', AdminProductListView.as_view(), name='admin-products'),
    path('products/<uuid:product_id>/action/', AdminProductActionView.as_view(), name='admin-product-action'),
]
