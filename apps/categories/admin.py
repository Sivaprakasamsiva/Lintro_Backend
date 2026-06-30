"""Categories admin."""
from django.contrib import admin
from .models import Category, CategoryField


class CategoryFieldInline(admin.TabularInline):
    model = CategoryField
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active', 'display_order')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CategoryFieldInline]


@admin.register(CategoryField)
class CategoryFieldAdmin(admin.ModelAdmin):
    list_display = ('category', 'name', 'label', 'field_type', 'is_required', 'is_filterable')
    list_filter = ('field_type', 'is_required', 'is_filterable')
    search_fields = ('name', 'label', 'category__name')
