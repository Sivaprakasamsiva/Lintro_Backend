"""Inquiries admin."""
from django.contrib import admin
from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('product', 'asker_name', 'question', 'answered_at', 'is_public')
    list_filter = ('is_public',)
    search_fields = ('question', 'answer', 'product__title', 'asker_name')
