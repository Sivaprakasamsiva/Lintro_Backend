"""
Complaint models - users report fraud, fake products, abuse, spam.
"""
import uuid
from django.db import models
from django.conf import settings


class Complaint(models.Model):
    class Category(models.TextChoices):
        FRAUD = 'fraud', 'Fraud / Scam'
        FAKE_PRODUCT = 'fake_product', 'Fake Product'
        ABUSE = 'abuse', 'Abusive Behaviour'
        SPAM = 'spam', 'Spam Listing'
        PROHIBITED = 'prohibited', 'Prohibited Item'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        UNDER_REVIEW = 'under_review', 'Under Review'
        WARNED = 'warned', 'User Warned'
        SUSPENDED = 'suspended', 'User Suspended'
        BANNED = 'banned', 'User Banned'
        DISMISSED = 'dismissed', 'Dismissed'
        RESOLVED = 'resolved', 'Resolved'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complainant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='complaints_filed',
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='complaints_against',
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='complaints',
    )
    category = models.CharField(max_length=30, choices=Category.choices, db_index=True)
    description = models.TextField()
    evidence_image = models.ImageField(upload_to='complaints/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    admin_notes = models.TextField(blank=True)
    resolution = models.TextField(blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='complaints_handled',
    )
    handled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['reported_user']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return f'Complaint: {self.category} against {self.reported_user.email}'
