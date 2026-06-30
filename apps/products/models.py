# backend/apps/products/models.py
"""
Product models.

Statuses flow:
  available -> pending (buyer sent request -> seller should act within 24h)
            -> reserved (seller marked reserved for a buyer)
            -> sold (final state)
  available -> expired (after listing_expiry_days)
  expired   -> archived (after 7 more days -> Cloudinary images deleted)

Also: deleted (soft delete by user), unlisted (auto, when seller missed 24h window).
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from apps.categories.models import Category


class Product(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        PENDING = 'pending', 'Pending'
        RESERVED = 'reserved', 'Reserved'
        SOLD = 'sold', 'Sold'
        EXPIRED = 'expired', 'Expired'
        UNLISTED = 'unlisted', 'Unlisted (24h Missed)'
        ARCHIVED = 'archived', 'Archived'
        DELETED = 'deleted', 'Deleted'

    class Condition(models.TextChoices):
        NEW = 'new', 'Brand New'
        LIKE_NEW = 'like_new', 'Like New'
        GOOD = 'good', 'Good'
        FAIR = 'fair', 'Fair'
        DEFECTIVE = 'defective', 'Defective'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=200, unique=True, db_index=True, blank=True)
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.RESTRICT, related_name='products'
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products'
    )

    price = models.DecimalField(
        max_digits=10, decimal_places=2, db_index=True,
        help_text='Price in Indian Rupees (₹)'
    )
    negotiable = models.BooleanField(default=True)

    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)

    # Location
    location_name = models.CharField(max_length=255, help_text='Human-readable address or area')
    district = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, db_index=True)
    country = models.CharField(max_length=100, default='India')
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Dynamic custom field values (per category)
    custom_fields = models.JSONField(default=dict, blank=True)

    # Status & lifecycle
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True
    )
    is_featured = models.BooleanField(default=False)
    views_count = models.IntegerField(default=0)
    buy_request_count = models.IntegerField(default=0)

    # Lifecycle timestamps
    listed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_buy_request_at = models.DateTimeField(null=True, blank=True)
    seller_action_deadline = models.DateTimeField(null=True, blank=True, help_text='24h deadline after a buy request')
    unlisted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text='When listing expires (configurable)')
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-listed_at']
        indexes = [
            models.Index(fields=['status', 'district', 'state']),
            models.Index(fields=['status', 'category']),
            models.Index(fields=['status', '-listed_at']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['price', 'status']),
        ]

    def __str__(self):
        return f'{self.title} - ₹{self.price}'

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:160]
            if not base:
                base = 'listing'
            suffix = str(self.id or uuid.uuid4())[:8]
            self.slug = f'{base}-{suffix}'
        if not self.expires_at and self.status == self.Status.AVAILABLE:
            from django.conf import settings as dj_settings
            days = getattr(dj_settings, 'DEFAULT_LISTING_EXPIRY_DAYS', 30)
            self.expires_at = timezone.now() + timezone.timedelta(days=days)
        super().save(*args, **kwargs)

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE

    @property
    def is_searchable(self):
        return self.status in (
            self.Status.AVAILABLE,
            self.Status.PENDING,
            self.Status.RESERVED,
        )

    @property
    def price_display(self):
        return f'₹{self.price:,.0f}'

    def increment_views(self):
        """Atomically increment view counter."""
        Product.objects.filter(pk=self.pk).update(views_count=models.F('views_count') + 1)

    def increment_buy_requests(self):
        """Atomically increment buy request counter."""
        Product.objects.filter(pk=self.pk).update(buy_request_count=models.F('buy_request_count') + 1)


class ProductImage(models.Model):
    """Product images stored in Cloudinary."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images'
    )
    image = models.ImageField(upload_to='products/')
    public_id = models.CharField(max_length=255, blank=True, help_text='Cloudinary public_id for deletion')
    display_order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'uploaded_at']
        indexes = [models.Index(fields=['product', 'display_order'])]

    def __str__(self):
        return f'Image for {self.product.title}'

    @property
    def url(self):
        try:
            return self.image.url
        except Exception:
            return ''


class Favorite(models.Model):
    """User favorites/wishlist."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites'
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        indexes = [models.Index(fields=['user', '-created_at'])]
