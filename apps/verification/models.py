"""
Seller verification models.

Workflow:
1. User submits Government ID + WhatsApp + Address.
2. Admin reviews.
3. Admin approves -> user gets verified_seller=True badge.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class VerificationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        RESUBMITTED = 'resubmitted', 'Resubmitted'

    class IDType(models.TextChoices):
        AADHAAR = 'aadhaar', 'Aadhaar'
        PAN = 'pan', 'PAN Card'
        DRIVING_LICENSE = 'driving_license', 'Driving License'
        VOTER_ID = 'voter_id', 'Voter ID'
        PASSPORT = 'passport', 'Passport'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification_requests',
    )
    id_type = models.CharField(max_length=30, choices=IDType.choices)
    id_number = models.CharField(max_length=100, blank=True)
    id_front_image = models.ImageField(upload_to='verification/')
    id_back_image = models.ImageField(upload_to='verification/', blank=True, null=True)
    selfie_image = models.ImageField(upload_to='verification/', blank=True, null=True)

    # Contact & address at the time of submission
    whatsapp_number = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_verifications',
    )
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f'Verification {self.user.email} - {self.status}'

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING
