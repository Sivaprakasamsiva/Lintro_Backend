"""
System configuration models - allow admin to change platform-wide settings
without code changes (listing expiry days, max images, theme colors, banner).
"""
import uuid
from django.db import models
from django.conf import settings


class SystemSetting(models.Model):
    """Key-value system settings."""

    class Type(models.TextChoices):
        STRING = 'string', 'String'
        INTEGER = 'integer', 'Integer'
        BOOLEAN = 'boolean', 'Boolean'
        JSON = 'json', 'JSON'

    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.TextField()
    value_type = models.CharField(max_length=20, choices=Type.choices, default=Type.STRING)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default='general', db_index=True)
    is_editable = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='system_settings_updated',
    )

    class Meta:
        ordering = ['category', 'key']

    def __str__(self):
        return f'{self.key} = {self.value[:50]}'

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).typed_value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value, user=None, **kwargs):
        if isinstance(value, bool):
            value_type = cls.Type.BOOLEAN
            value_str = 'true' if value else 'false'
        elif isinstance(value, int):
            value_type = cls.Type.INTEGER
            value_str = str(value)
        elif isinstance(value, (dict, list)):
            import json
            value_type = cls.Type.JSON
            value_str = json.dumps(value)
        else:
            value_type = cls.Type.STRING
            value_str = str(value)
        obj, _ = cls.objects.update_or_create(
            key=key, defaults={
                'value': value_str,
                'value_type': value_type,
                'updated_by': user,
                **kwargs,
            }
        )
        return obj

    @property
    def typed_value(self):
        if self.value_type == self.Type.INTEGER:
            try:
                return int(self.value)
            except ValueError:
                return None
        if self.value_type == self.Type.BOOLEAN:
            return self.value.lower() in ('true', '1', 'yes')
        if self.value_type == self.Type.JSON:
            import json
            try:
                return json.loads(self.value)
            except Exception:
                return None
        return self.value


class SiteBanner(models.Model):
    """Site-wide banner displayed on homepage."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.URLField(blank=True)
    link_text = models.CharField(max_length=100, default='Learn More')
    background_color = models.CharField(max_length=20, default='#0EA5E9')
    text_color = models.CharField(max_length=20, default='#FFFFFF')
    is_active = models.BooleanField(default=True)
    is_dismissible = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return self.title


class ThemeConfiguration(models.Model):
    """Theme colors and styling (one row, singleton)."""

    primary_color = models.CharField(max_length=20, default='#0EA5E9')
    secondary_color = models.CharField(max_length=20, default='#6366F1')
    accent_color = models.CharField(max_length=20, default='#F59E0B')
    success_color = models.CharField(max_length=20, default='#10B981')
    danger_color = models.CharField(max_length=20, default='#EF4444')
    background_color = models.CharField(max_length=20, default='#F8FAFC')
    surface_color = models.CharField(max_length=20, default='#FFFFFF')
    text_primary_color = models.CharField(max_length=20, default='#0F172A')
    text_secondary_color = models.CharField(max_length=20, default='#64748B')
    dark_mode_background = models.CharField(max_length=20, default='#0F172A')
    dark_mode_surface = models.CharField(max_length=20, default='#1E293B')
    dark_mode_text_primary = models.CharField(max_length=20, default='#F8FAFC')
    dark_mode_text_secondary = models.CharField(max_length=20, default='#94A3B8')
    homepage_layout = models.CharField(max_length=50, default='default', help_text='default | compact | grid')
    show_featured_section = models.BooleanField(default=True)
    show_recent_section = models.BooleanField(default=True)
    show_categories_section = models.BooleanField(default=True)
    show_banner = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Theme Configuration'
        verbose_name_plural = 'Theme Configuration'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
