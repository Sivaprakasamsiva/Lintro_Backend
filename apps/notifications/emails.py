"""Email notifications.

BUG-015 fix: log all email send failures so they are visible in the
backend logs (instead of being silently swallowed).
"""
import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _safe_send(subject, body, recipient):
    """Send an email, logging any failure. Returns True on success."""
    try:
        send_mail(
            subject, body, settings.DEFAULT_FROM_EMAIL, [recipient],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f'Failed to send email to {recipient} (subject={subject!r}): {e}')
        return False


def send_buy_request_email(seller, product, buy_request):
    """Notify seller via email about a new buy request."""
    subject = f'[Lintro] New buy request for "{product.title}"'
    body = f"""
Hello {seller.full_name},

You have received a new buy request on your listing.

Listing: {product.title}
Price: {product.price_display}

Buyer Details:
  Name: {buy_request.buyer_name}
  Phone: {buy_request.buyer_phone}
  WhatsApp: {buy_request.buyer_whatsapp or 'N/A'}
  Location: {buy_request.buyer_location or 'N/A'}
  Message: {buy_request.buyer_message or 'N/A'}

IMPORTANT: Respond within 24 hours, otherwise the listing will be automatically unlisted.

Reminder: Buyers must verify the seller before making any payment. Lintro only connects users and is not responsible for offline transactions.

- Lintro Marketplace
"""
    _safe_send(subject, body, seller.email)


def send_listing_unlisted_email(seller, product):
    subject = f'[Lintro] Your listing "{product.title}" has been unlisted'
    body = f"""
Hello {seller.full_name},

Your listing "{product.title}" has been automatically unlisted because you did not respond to a buy request within 24 hours.

To relist, log in and update the product status. If no action is taken within 7 days, the listing will be archived and its images will be deleted.

- Lintro Marketplace
"""
    _safe_send(subject, body, seller.email)


def send_listing_archived_email(seller, product):
    subject = f'[Lintro] Your listing "{product.title}" has been archived'
    body = f"""
Hello {seller.full_name},

Your listing "{product.title}" has been archived after being unlisted for 7 days without action. All associated images have been deleted.

You may create a new listing anytime.

- Lintro Marketplace
"""
    _safe_send(subject, body, seller.email)


def send_listing_expiry_warning_email(seller, product):
    subject = f'[Lintro] Your listing "{product.title}" will expire soon'
    body = f"""
Hello {seller.full_name},

Your listing "{product.title}" will expire in 2 days. Consider refreshing it or marking it sold.

- Lintro Marketplace
"""
    _safe_send(subject, body, seller.email)
