"""Complaints admin."""
from django.contrib import admin
from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('reported_user', 'complainant', 'category', 'status', 'created_at', 'handled_by')
    list_filter = ('status', 'category')
    search_fields = ('description', 'reported_user__email', 'complainant__email')
    readonly_fields = ('created_at', 'updated_at', 'handled_at')
