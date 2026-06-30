"""Verification admin."""
from django.contrib import admin
from .models import VerificationRequest


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'id_type', 'status', 'submitted_at', 'reviewed_at', 'reviewed_by')
    list_filter = ('status', 'id_type')
    search_fields = ('user__email', 'user__full_name', 'whatsapp_number', 'district')
    readonly_fields = ('submitted_at', 'reviewed_at', 'reviewed_by')
