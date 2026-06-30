# backend/apps/inquiries/models.py

"""
Inquiry models - Q&A on a product (separate from buy requests).
"""
import uuid
from django.db import models
from django.conf import settings


class Inquiry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='inquiries'
    )
    asker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inquiries_asked',
        null=True, blank=True,
    )
    asker_name = models.CharField(max_length=200, blank=True)
    question = models.TextField()
    answer = models.TextField(blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    is_public = models.BooleanField(default=True, help_text='Show on product page')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'is_public']),
            models.Index(fields=['asker', '-created_at']),
        ]

    def __str__(self):
        return f'Q: {self.question[:50]} on {self.product.title}'
