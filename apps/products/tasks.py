"""
Celery tasks for Lintro Marketplace.

- expire_buy_requests: mark buy requests whose 24h deadline has passed as expired
- unlist_products_with_missed_deadlines: move products from PENDING -> UNLISTED
- archive_old_unlisted_products: after 7 days, archive + delete Cloudinary images
- expire_old_listings: mark listings past expires_at as EXPIRED
- send_expiry_warnings: 2 days before expiry, warn sellers
- send_24hr_reminders: 4 hours before deadline, remind sellers
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging

from apps.products.models import Product
from apps.buy_requests.models import BuyRequest
from apps.notifications.utils import create_notification
from apps.notifications.emails import (
    send_listing_unlisted_email,
    send_listing_archived_email,
    send_listing_expiry_warning_email,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def expire_buy_requests(self):
    """Mark pending buy requests past their 24h deadline as expired."""
    now = timezone.now()
    expired_count = BuyRequest.objects.filter(
        status=BuyRequest.Status.PENDING,
        deadline_at__lt=now,
    ).update(
        status=BuyRequest.Status.EXPIRED,
        expired_notification_sent=True,
    )
    logger.info(f'Expired {expired_count} buy requests past their 24h deadline.')
    return expired_count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def unlist_products_with_missed_deadlines(self):
    """
    Move products from PENDING -> UNLISTED if all buy requests are
    expired/rejected and the seller never responded within 24h.
    """
    now = timezone.now()
    cutoff = now - timedelta(hours=getattr(settings, 'DEFAULT_24HR_ACTION_HOURS', 24))

    pending_products = Product.objects.filter(
        status=Product.Status.PENDING,
        seller_action_deadline__lt=now,
    ).select_related('seller')

    unlisted_count = 0
    for product in pending_products.iterator():
        # Check if any pending buy request still has time
        still_pending = BuyRequest.objects.filter(
            product=product, status=BuyRequest.Status.PENDING
        ).exists()
        if still_pending:
            continue
        product.status = Product.Status.UNLISTED
        product.unlisted_at = now
        product.seller_action_deadline = None
        product.save(update_fields=['status', 'unlisted_at', 'seller_action_deadline', 'updated_at'])

        create_notification(
            user=product.seller,
            title=f'Listing unlisted: {product.title}',
            message='You did not respond to a buy request within 24 hours. Update the listing status to relist it.',
            notification_type='listing_unlisted',
            related_id=str(product.id),
        )
        send_listing_unlisted_email(product.seller, product)
        unlisted_count += 1

    logger.info(f'Unlisted {unlisted_count} products past their 24h deadline.')
    return unlisted_count


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def archive_old_unlisted_products(self):
    """
    After 7 days of being UNLISTED, archive product and delete Cloudinary images.
    """
    now = timezone.now()
    cleanup_days = getattr(settings, 'DEFAULT_7DAY_CLEANUP_DAYS', 7)
    cutoff = now - timedelta(days=cleanup_days)

    old_unlisted = Product.objects.filter(
        status=Product.Status.UNLISTED,
        unlisted_at__lt=cutoff,
    ).select_related('seller')

    archived_count = 0
    for product in old_unlisted.iterator():
        # Delete Cloudinary images
        try:
            for img in product.images.all():
                try:
                    if img.public_id:
                        import cloudinary
                        cloudinary.uploader.destroy(img.public_id, invalidate=True)
                    elif img.image:
                        # Cloudinary storage auto-deletes on .delete() if configured
                        img.image.delete(save=False)
                except Exception as e:
                    logger.warning(f'Failed to delete image {img.id}: {e}')
                img.delete()
        except Exception as e:
            logger.error(f'Error deleting images for product {product.id}: {e}')

        product.status = Product.Status.ARCHIVED
        product.archived_at = now
        product.save(update_fields=['status', 'archived_at', 'updated_at'])

        create_notification(
            user=product.seller,
            title=f'Listing archived: {product.title}',
            message='Your listing has been archived after 7 days of being unlisted. You can create a new listing anytime.',
            notification_type='listing_archived',
            related_id=str(product.id),
        )
        send_listing_archived_email(product.seller, product)
        archived_count += 1

    logger.info(f'Archived {archived_count} old unlisted products.')
    return archived_count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def expire_old_listings(self):
    """Mark listings past their expires_at as EXPIRED."""
    now = timezone.now()
    expired = Product.objects.filter(
        status=Product.Status.AVAILABLE,
        expires_at__lt=now,
    )
    count = expired.count()
    for product in expired.iterator():
        product.status = Product.Status.EXPIRED
        product.save(update_fields=['status', 'updated_at'])
        create_notification(
            user=product.seller,
            title=f'Listing expired: {product.title}',
            message='Your listing has expired. You can renew it from your dashboard.',
            notification_type='listing_expired',
            related_id=str(product.id),
        )
    logger.info(f'Expired {count} listings past their expiry date.')
    return count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_expiry_warnings(self):
    """Send expiry warning emails 2 days before expiry."""
    now = timezone.now()
    soon = now + timedelta(days=2)
    soon_listings = Product.objects.filter(
        status=Product.Status.AVAILABLE,
        expires_at__lte=soon,
        expires_at__gt=now,
    ).select_related('seller')
    sent_count = 0
    for product in soon_listings.iterator():
        send_listing_expiry_warning_email(product.seller, product)
        sent_count += 1
    logger.info(f'Sent {sent_count} expiry warning emails.')
    return sent_count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_24hr_reminders(self):
    """Remind sellers 4 hours before their action deadline."""
    now = timezone.now()
    soon = now + timedelta(hours=4)
    soon_products = Product.objects.filter(
        status=Product.Status.PENDING,
        seller_action_deadline__lte=soon,
        seller_action_deadline__gt=now,
    ).select_related('seller')
    sent_count = 0
    for product in soon_products.iterator():
        create_notification(
            user=product.seller,
            title=f'4 hours left to respond: {product.title}',
            message='A buyer is waiting for your response. Respond within 4 hours or your listing will be unlisted automatically.',
            notification_type='listing_reminder',
            related_id=str(product.id),
        )
        sent_count += 1
    logger.info(f'Sent {sent_count} 24h reminders.')
    return sent_count


@shared_task
def cleanup_old_notifications():
    """Delete read notifications older than 90 days."""
    cutoff = timezone.now() - timedelta(days=90)
    from apps.notifications.models import Notification
    deleted_count, _ = Notification.objects.filter(
        is_read=True, created_at__lt=cutoff
    ).delete()
    logger.info(f'Deleted {deleted_count} old notifications.')
    return deleted_count


@shared_task
def cleanup_blacklisted_tokens():
    """Periodically clean expired blacklisted tokens."""
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    from rest_framework_simplejwt.utils import aware_utcnow
    deleted_count, _ = OutstandingToken.objects.filter(
        expires_at__lte=aware_utcnow()
    ).delete()
    logger.info(f'Cleaned {deleted_count} expired tokens.')
    return deleted_count
