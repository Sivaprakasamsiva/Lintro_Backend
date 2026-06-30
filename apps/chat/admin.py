"""Chat admin."""
from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'body', 'is_read', 'read_at', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('product', 'participant_a', 'participant_b', 'last_message_at', 'updated_at')
    search_fields = ('product__title', 'participant_a__email', 'participant_b__email')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('body', 'sender__email')
