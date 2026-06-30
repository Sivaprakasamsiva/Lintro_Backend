"""System config serializers."""
from rest_framework import serializers
from .models import SystemSetting, SiteBanner, ThemeConfiguration


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = [
            'key', 'value', 'value_type', 'description',
            'category', 'is_editable', 'updated_at',
        ]
        read_only_fields = ['key', 'value_type', 'updated_at']


class SiteBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteBanner
        fields = [
            'id', 'title', 'message', 'link', 'link_text',
            'background_color', 'text_color', 'is_active',
            'is_dismissible', 'display_order', 'starts_at', 'ends_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ThemeConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeConfiguration
        fields = [
            'primary_color', 'secondary_color', 'accent_color',
            'success_color', 'danger_color', 'background_color',
            'surface_color', 'text_primary_color', 'text_secondary_color',
            'dark_mode_background', 'dark_mode_surface',
            'dark_mode_text_primary', 'dark_mode_text_secondary',
            'homepage_layout', 'show_featured_section',
            'show_recent_section', 'show_categories_section', 'show_banner',
        ]
