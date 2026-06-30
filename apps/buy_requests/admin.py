"""Buy requests admin."""
from django.contrib import admin
from .models import BuyRequest


@admin.register(BuyRequest)
class BuyRequestAdmin(admin.ModelAdmin):
    list_display = ('buyer_name', 'product', 'status', 'created_at', 'deadline_at', 'seller_responded_at')
    list_filter = ('status',)
    search_fields = ('buyer_name', 'buyer_phone', 'product__title', 'product__seller__email')
    readonly_fields = ('created_at', 'updated_at', 'deadline_at', 'seller_responded_at')
