"""
Root URL configuration for Lintro Marketplace.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponse


def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'service': 'Lintro-backend'
    })


def home(request):
    return HttpResponse("Lintro Backend Running")


urlpatterns = [
    path('', home),

    path('admin/', admin.site.urls),

    path('health/', health_check, name='health-check'),

    path('api/auth/', include('apps.users.urls')),
    path('api/users/', include('apps.users.urls_profile')),
    path('api/verification/', include('apps.verification.urls')),
    path('api/categories/', include('apps.categories.urls')),
    path('api/products/', include('apps.products.urls')),
    path('api/buy-requests/', include('apps.buy_requests.urls')),
    path('api/inquiries/', include('apps.inquiries.urls')),
    path('api/chat/', include('apps.chat.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/complaints/', include('apps.complaints.urls')),
    path('api/system/', include('apps.system_config.urls')),
    path('api/admin/', include('apps.admin_dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )