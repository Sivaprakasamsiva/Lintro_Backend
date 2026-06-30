"""Notifications utilities."""
from .models import Notification


def create_notification(user, title, message, notification_type, related_id=None, related_type=None):
    """Create a notification for a user (if not duplicated within last hour)."""
    if not user:
        return None
    # De-duplicate within an hour
    from django.utils import timezone
    from datetime import timedelta
    recent = Notification.objects.filter(
        user=user,
        notification_type=notification_type,
        related_id=related_id or '',
        created_at__gte=timezone.now() - timedelta(hours=1),
    ).first()
    if recent:
        return recent
    return Notification.objects.create(
        user=user, 
        title=title, 
        message=message,
        notification_type=notification_type,
        related_id=related_id or '', 
        related_type=related_type or '',
    )