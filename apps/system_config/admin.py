"""System config admin."""
from django.contrib import admin
from .models import SystemSetting, SiteBanner, ThemeConfiguration


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'value_type', 'category', 'is_editable', 'updated_at')
    list_filter = ('value_type', 'category', 'is_editable')
    search_fields = ('key', 'description', 'value')


@admin.register(SiteBanner)
class SiteBannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'display_order', 'starts_at', 'ends_at')
    list_filter = ('is_active',)


@admin.register(ThemeConfiguration)
class ThemeConfigurationAdmin(admin.ModelAdmin):
    list_display = ('pk', 'primary_color', 'homepage_layout', 'updated_at')
