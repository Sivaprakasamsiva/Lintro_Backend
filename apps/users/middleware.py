"""Middleware for tracking user activity."""
from django.utils import timezone


class UserActivityMiddleware:
    """Update last_active timestamp on each authenticated request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            now = timezone.now()
            if not user.last_active or (now - user.last_active).total_seconds() > 60:
                User = user.__class__
                User.objects.filter(pk=user.pk).update(last_active=now)
        return response
