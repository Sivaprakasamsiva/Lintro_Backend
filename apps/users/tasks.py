"""
Celery tasks for the users app.

BUG-009 fix: cleanup old Axes brute-force attempt records so the
axes_attempts table does not grow unbounded.
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_axes_attempts():
    """Delete Axes AccessAttempt rows older than 30 days.

    Returns the number of deleted rows.
    """
    try:
        from axes.models import AccessAttempt
    except ImportError:
        # axes not installed - nothing to do
        logger.warning('axes not installed; skipping cleanup_old_axes_attempts')
        return 0

    cutoff = timezone.now() - timedelta(days=30)
    deleted, _ = AccessAttempt.objects.filter(updated_at__lt=cutoff).delete()
    logger.info(f'Cleaned up {deleted} old axes attempt rows')
    return deleted
