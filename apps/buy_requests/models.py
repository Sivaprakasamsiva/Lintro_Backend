"""
Buy request models.

NO PAYMENT is processed. The buyer submits contact info + message; the seller
is notified and must respond within 24 hours (else product auto-unlisted).
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class BuyRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
        EXPIRED = 'expired', 'Expired'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='buy_requests'
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='buy_requests_sent',
        null=True, blank=True,
        help_text='Null if buyer is not a registered user (guest).'
    )

    # Buyer contact info (also captured for guests)
    buyer_name = models.CharField(max_length=200)
    buyer_phone = models.CharField(max_length=15)
    buyer_whatsapp = models.CharField(max_length=15, blank=True)
    buyer_location = models.CharField(max_length=255, blank=True)
    buyer_message = models.TextField(blank=True)

    # Negotiated price (optional)
    offered_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    seller_response = models.TextField(blank=True)
    seller_responded_at = models.DateTimeField(null=True, blank=True)

    # 24-hour deadline tracking
    deadline_at = models.DateTimeField(help_text='24h deadline for seller response')
    expired_notification_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['buyer', '-created_at']),
            models.Index(fields=['status', 'deadline_at']),
            # BUG-008 fix: index for "list buy requests on a product, newest first"
            models.Index(fields=['product', '-created_at']),
        ]

    def __str__(self):
        return f'BuyRequest for {self.product.title} by {self.buyer_name}'

    def save(self, *args, **kwargs):
        if not self.deadline_at:
            from django.conf import settings as dj_settings
            hours = getattr(dj_settings, 'DEFAULT_24HR_ACTION_HOURS', 24)
            self.deadline_at = timezone.now() + timezone.timedelta(hours=hours)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return self.status == self.Status.PENDING and self.deadline_at < timezone.now()

    @property
    def time_remaining_seconds(self):
        if self.status != self.Status.PENDING:
            return 0
        delta = self.deadline_at - timezone.now()
        return max(0, int(delta.total_seconds()))
