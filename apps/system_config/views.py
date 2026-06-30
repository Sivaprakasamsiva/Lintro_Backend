"""System config views."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SystemSetting, SiteBanner, ThemeConfiguration
from .serializers import (
    SystemSettingSerializer, SiteBannerSerializer, ThemeConfigurationSerializer,
)

DEFAULT_PLATFORM_NOTICE = (
    'Buyers must verify the seller before making any payment. '
    'The platform only connects users and is not responsible for offline transactions.'
)


class PublicSiteConfigView(APIView):
    """Public endpoint returning active banners + theme for the frontend.

    BUG-022 fix: platform_notice is now read from SystemSetting so admins
    can change it without code edits. Falls back to the default if not set.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        now = timezone.now()
        banners = SiteBanner.objects.filter(
            is_active=True
        ).filter(
            starts_at__isnull=True
        ) | SiteBanner.objects.filter(
            is_active=True, starts_at__lte=now
        ).filter(
            ends_at__isnull=True
        ) | SiteBanner.objects.filter(
            is_active=True, starts_at__lte=now, ends_at__gt=now
        )
        theme = ThemeConfiguration.get_solo()
        # BUG-022 fix: read platform_notice from SystemSetting (editable by admin)
        platform_notice = SystemSetting.get(
            'platform_notice', default=DEFAULT_PLATFORM_NOTICE
        )
        return Response({
            'banners': SiteBannerSerializer(banners, many=True).data,
            'theme': ThemeConfigurationSerializer(theme).data,
            'platform_notice': platform_notice,
        })


class SystemSettingListView(generics.ListCreateAPIView):
    """Admin: list/create system settings."""

    serializer_class = SystemSettingSerializer
    permission_classes = [IsAdminUser]
    queryset = SystemSetting.objects.all()


class SystemSettingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: update/delete a setting."""

    serializer_class = SystemSettingSerializer
    permission_classes = [IsAdminUser]
    queryset = SystemSetting.objects.all()
    lookup_field = 'key'

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class SiteBannerListView(generics.ListCreateAPIView):
    serializer_class = SiteBannerSerializer
    permission_classes = [IsAdminUser]
    queryset = SiteBanner.objects.all()


class SiteBannerDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SiteBannerSerializer
    permission_classes = [IsAdminUser]
    queryset = SiteBanner.objects.all()


class ThemeConfigurationView(generics.RetrieveUpdateAPIView):
    """Admin: get/update theme configuration (singleton)."""

    serializer_class = ThemeConfigurationSerializer
    permission_classes = [IsAdminUser]

    def get_object(self):
        return ThemeConfiguration.get_solo()


# backend/apps/system_config/views.py
"""
System config views including storage monitoring.
"""
import cloudinary
import cloudinary.api
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView


class StorageStatsView(APIView):
    """Admin view to get Cloudinary storage statistics."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            # Get usage statistics
            usage = cloudinary.api.usage()
            
            # Get recent uploads
            resources = cloudinary.api.resources(
                max_results=50,
                sort_by='uploaded_at',
                sort_order='desc'
            )
            
            # Calculate total storage by file type
            storage_by_type = {}
            total_size = 0
            total_images = 0
            recent_uploads = []
            
            for resource in resources.get('resources', []):
                resource_type = resource.get('resource_type', 'image')
                bytes_size = resource.get('bytes', 0)
                total_size += bytes_size
                total_images += 1
                
                storage_by_type[resource_type] = storage_by_type.get(resource_type, 0) + bytes_size
                
                # Get recent uploads
                recent_uploads.append({
                    'public_id': resource.get('public_id'),
                    'url': resource.get('secure_url'),
                    'bytes': resource.get('bytes'),
                    'format': resource.get('format'),
                    'width': resource.get('width'),
                    'height': resource.get('height'),
                    'uploaded_at': resource.get('created_at'),
                    'resource_type': resource_type,
                })
            
            # Get folder breakdown
            folders = cloudinary.api.root_foldures(max_results=50) if hasattr(cloudinary.api, 'root_foldures') else {'folders': []}
            
            return Response({
                'usage': {
                    'storage_used': usage.get('storage_used', 0),
                    'storage_limit': usage.get('storage_limit', 0),
                    'bandwidth_used': usage.get('bandwidth_used', 0),
                    'bandwidth_limit': usage.get('bandwidth_limit', 0),
                    'transformations_used': usage.get('transformations_used', 0),
                    'transformations_limit': usage.get('transformations_limit', 0),
                    'credits_used': usage.get('credits_used', 0),
                    'credits_limit': usage.get('credits_limit', 0),
                },
                'total_images': total_images,
                'total_storage_mb': total_size / (1024 * 1024),
                'storage_by_type': {
                    k: v / (1024 * 1024) for k, v in storage_by_type.items()
                },
                'recent_uploads': recent_uploads[:20],
                'folders': [f.get('name') for f in folders.get('folders', [])],
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed to fetch storage statistics. Please check Cloudinary configuration.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClearCacheView(APIView):
    """Admin view to purge Cloudinary cache."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            cloudinary.api.purge_cache()
            return Response({
                'message': 'Cache purge initiated successfully.'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class DeleteImageView(APIView):
    """Admin view to delete an image from Cloudinary."""
    permission_classes = [IsAdminUser]

    def delete(self, request, public_id):
        try:
            result = cloudinary.uploader.destroy(public_id, invalidate=True)
            return Response({
                'message': f'Image {public_id} deleted successfully.',
                'result': result
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)        