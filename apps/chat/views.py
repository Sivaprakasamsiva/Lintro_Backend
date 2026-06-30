"""Chat views."""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.utils import create_notification
from apps.products.models import Product

from .models import Conversation, Message
from .serializers import (
    ConversationSerializer, MessageSerializer,
    StartConversationSerializer, SendMessageSerializer,
)


class ConversationListView(generics.ListAPIView):
    """List user's conversations."""

    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(participant_a=user) | Q(participant_b=user)
        ).select_related('product', 'participant_a', 'participant_b', 'product__seller').prefetch_related('messages')


class StartConversationView(APIView):
    """Start a new conversation about a product."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StartConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data['product_id']
        body = serializer.validated_data['initial_message']

        product = get_object_or_404(Product, pk=product_id)
        if product.seller_id == request.user.id:
            return Response({'detail': 'Cannot start a conversation with yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        # Sort participants to keep unique_together consistent
        user_a, user_b = sorted([request.user, product.seller], key=lambda u: u.id)
        conversation, created = Conversation.objects.get_or_create(
            product=product, participant_a=user_a, participant_b=user_b,
        )

        message = Message.objects.create(
            conversation=conversation, sender=request.user, body=body,
        )
        conversation.last_message_at = timezone.now()
        conversation.save(update_fields=['last_message_at', 'updated_at'])

        recipient = conversation.other_participant(request.user)
        create_notification(
            user=recipient,
            title=f'New message from {request.user.full_name}',
            message=body[:100],
            notification_type='chat_message',
            related_id=str(conversation.id),
        )

        return Response(
            ConversationSerializer(conversation, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailView(generics.RetrieveAPIView):
    """Get a conversation with messages."""

    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(Q(participant_a=user) | Q(participant_b=user))


class MessageListView(generics.ListAPIView):
    """List messages in a conversation, mark unread as read."""

    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        user = self.request.user
        conversation = get_object_or_404(
            Conversation,
            Q(pk=conversation_id) & (Q(participant_a=user) | Q(participant_b=user))
        )
        # Mark unread messages from other user as read
        Message.objects.filter(
            conversation=conversation, is_read=False
        ).exclude(sender=user).update(is_read=True, read_at=timezone.now())
        return conversation.messages.select_related('sender')


class SendMessageView(APIView):
    """Send a message in an existing conversation."""

    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation,
            Q(pk=conversation_id) & (Q(participant_a=request.user) | Q(participant_b=request.user))
        )
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = Message.objects.create(
            conversation=conversation, sender=request.user,
            body=serializer.validated_data['body'],
        )
        conversation.last_message_at = timezone.now()
        conversation.save(update_fields=['last_message_at', 'updated_at'])

        recipient = conversation.other_participant(request.user)
        create_notification(
            user=recipient,
            title=f'New message from {request.user.full_name}',
            message=message.body[:100],
            notification_type='chat_message',
            related_id=str(conversation.id),
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class UnreadMessageCountView(APIView):
    """Get total unread message count."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        convs = Conversation.objects.filter(Q(participant_a=user) | Q(participant_b=user))
        count = Message.objects.filter(
            conversation__in=convs, is_read=False
        ).exclude(sender=user).count()
        return Response({'unread_count': count})
