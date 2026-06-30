"""User utility helpers."""
from .models import UserAuditLog


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def log_audit(request, user, action, metadata=None):
    """Create an audit log entry."""
    if metadata is None:
        metadata = {}
    UserAuditLog.objects.create(
        user=user,
        action=action,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        metadata=metadata,
    )
