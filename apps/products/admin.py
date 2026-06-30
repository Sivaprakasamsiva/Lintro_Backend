"""Products admin."""
from django.contrib import admin
from .models import Product, ProductImage, Favorite


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    readonly_fields = ('uploaded_at', 'public_id')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'price', 'status', 'district', 'state', 'listed_at')
    list_filter = ('status', 'condition', 'is_featured', 'category')
    search_fields = ('title', 'description', 'seller__email', 'district')
    readonly_fields = ('listed_at', 'updated_at', 'views_count', 'buy_request_count',
                       'last_buy_request_at', 'seller_action_deadline', 'unlisted_at',
                       'expires_at', 'archived_at')
    inlines = [ProductImageInline]
    actions = ['feature_products', 'unfeature_products', 'archive_products']

    def feature_products(self, request, queryset):
        queryset.update(is_featured=True)
    feature_products.short_description = 'Mark as featured'

    def unfeature_products(self, request, queryset):
        queryset.update(is_featured=False)
    unfeature_products.short_description = 'Remove featured'

    def archive_products(self, request, queryset):
        from django.utils import timezone
        queryset.update(status=Product.Status.ARCHIVED, archived_at=timezone.now())
    archive_products.short_description = 'Archive selected'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'display_order', 'is_primary', 'uploaded_at')
    list_filter = ('is_primary',)
    search_fields = ('product__title',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__email', 'product__title')
