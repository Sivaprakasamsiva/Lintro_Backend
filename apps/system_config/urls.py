"""System config URLs."""
from django.urls import path
from .views import DeleteImageView, StorageStatsView, ClearCacheView
from .views import (
    PublicSiteConfigView, SystemSettingListView, SystemSettingDetailView,
    SiteBannerListView, SiteBannerDetailView, ThemeConfigurationView,
)

urlpatterns = [
    path('public-config/', PublicSiteConfigView.as_view(), name='public-config'),
    # Admin
    path('settings/', SystemSettingListView.as_view(), name='setting-list'),
    path('settings/<str:key>/', SystemSettingDetailView.as_view(), name='setting-detail'),
    path('banners/', SiteBannerListView.as_view(), name='banner-list'),
    path('banners/<uuid:pk>/', SiteBannerDetailView.as_view(), name='banner-detail'),
    path('theme/', ThemeConfigurationView.as_view(), name='theme-config'),
    path('storage/stats/', StorageStatsView.as_view(), name='storage-stats'),
    path('storage/clear-cache/', ClearCacheView.as_view(), name='clear-cache'),
    # backend/apps/system_config/urls.py
    path('storage/delete/<path:public_id>/', DeleteImageView.as_view(), name='delete-image'),
]
