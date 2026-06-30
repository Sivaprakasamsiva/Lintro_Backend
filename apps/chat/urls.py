"""Chat URLs."""
from django.urls import path
from .views import (
    ConversationListView, StartConversationView, ConversationDetailView,
    MessageListView, SendMessageView, UnreadMessageCountView,
)

urlpatterns = [
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/start/', StartConversationView.as_view(), name='conversation-start'),
    path('conversations/<uuid:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<uuid:conversation_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('conversations/<uuid:conversation_id>/send/', SendMessageView.as_view(), name='message-send'),
    path('unread-count/', UnreadMessageCountView.as_view(), name='unread-count'),
]
