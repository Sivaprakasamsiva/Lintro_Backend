
# backend/apps/chat/models.py
"""
Chat models - buyer <-> seller messaging.

A conversation is tied to a specific product. Either participant can be the
initiator. Messages are stored in the database with read receipts.
"""
import uuid
from django.db import models
from django.conf import settings


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='conversations'
    )
    participant_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='conversations_as_a'
    )
    participant_b = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='conversations_as_b'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        # Ensure only one conversation per product between two users
        unique_together = ('product', 'participant_a', 'participant_b')
        ordering = ['-last_message_at', '-updated_at']
        indexes = [
            models.Index(fields=['participant_a', '-updated_at']),
            models.Index(fields=['participant_b', '-updated_at']),
        ]

    def __str__(self):
        return f'Conversation: {self.participant_a.email} <-> {self.participant_b.email} on {self.product.title}'

    def other_participant(self, user):
        return self.participant_b if user.id == self.participant_a_id else self.participant_a

class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages'
    )
    body = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['is_read', 'created_at']),
        ]

    def __str__(self):
        return f'{self.sender.email}: {self.body[:50]}'
