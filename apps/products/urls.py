"""Products URLs."""
from django.urls import path
from .views import (
    ProductSearchView, ProductDetailView, ProductCreateView,
    ProductUpdateView, ProductDeleteView, MyListingsView,
    ProductStatusUpdateView, FeaturedProductsView, RecentProductsView,
    FavoriteListView, FavoriteToggleView,
)

urlpatterns = [
    # ===== FAVORITES - MUST COME BEFORE SLUG PATTERNS =====
    path('favorites/', FavoriteListView.as_view(), name='favorite-list'),
    path('favorites/<uuid:product_id>/toggle/', FavoriteToggleView.as_view(), name='favorite-toggle'),
    
    # ===== PRODUCT ENDPOINTS =====
    path('', ProductSearchView.as_view(), name='product-search'),
    path('featured/', FeaturedProductsView.as_view(), name='product-featured'),
    path('recent/', RecentProductsView.as_view(), name='product-recent'),
    path('create/', ProductCreateView.as_view(), name='product-create'),
    path('mine/', MyListingsView.as_view(), name='my-listings'),
    
    # ===== PRODUCT SLUG PATTERNS - MUST COME LAST =====
    # These patterns match any string, so they should be at the end
    path('<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
    path('<slug:slug>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('<slug:slug>/delete/', ProductDeleteView.as_view(), name='product-delete'),
    path('<slug:slug>/status/', ProductStatusUpdateView.as_view(), name='product-status'),
]