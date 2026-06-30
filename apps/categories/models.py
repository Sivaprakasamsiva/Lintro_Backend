"""
Category models - dynamic categories with custom fields per category.

Admin can add categories and define custom field schemas (text, number, choice, etc.).
Product instances store custom field values as JSON.
"""
import uuid
from django.db import models
from django.conf import settings
from django.db.models import JSONField



class Category(models.Model):
    """A product category (e.g., Mobile, Laptop, Vehicle)."""

    class FieldType(models.TextChoices):
        TEXT = 'text', 'Text'
        NUMBER = 'number', 'Number'
        CHOICE = 'choice', 'Choice'
        BOOLEAN = 'boolean', 'Boolean (Yes/No)'
        DATE = 'date', 'Date'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='Icon name or emoji')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='subcategories',
    )
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']
        indexes = [models.Index(fields=['is_active', 'parent'])]

    def __str__(self):
        return self.name

    @property
    def is_parent(self):
        return self.parent is None


class CategoryField(models.Model):
    """Custom field definition for a category."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='custom_fields'
    )
    name = models.CharField(max_length=100, help_text='Machine name (snake_case)')
    label = models.CharField(max_length=150, help_text='Display label')
    field_type = models.CharField(max_length=20, choices=Category.FieldType.choices)
    is_required = models.BooleanField(default=False)
    is_filterable = models.BooleanField(default=False, help_text='Show in filter sidebar')
    choices = models.JSONField(
        default=list, blank=True,
        help_text='For choice fields: ["option1", "option2", ...]'
    )
    unit = models.CharField(max_length=20, blank=True, help_text='e.g., GB, inches, km')
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'name']
        unique_together = ('category', 'name')
        indexes = [models.Index(fields=['category', 'is_filterable'])]

    def __str__(self):
        return f'{self.category.name} -> {self.label}'

    def validate_value(self, value):
        """Validate a value against this field's rules. Returns cleaned value or raises ValueError."""
        if value is None or value == '':
            if self.is_required:
                raise ValueError(f'{self.label} is required.')
            return None

        if self.field_type == Category.FieldType.NUMBER:
            try:
                return float(value)
            except (TypeError, ValueError):
                raise ValueError(f'{self.label} must be a number.')

        if self.field_type == Category.FieldType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if str(value).lower() in ('true', '1', 'yes'):
                return True
            if str(value).lower() in ('false', '0', 'no'):
                return False
            raise ValueError(f'{self.label} must be a boolean.')

        if self.field_type == Category.FieldType.CHOICE:
            if value not in self.choices:
                raise ValueError(f'{self.label} must be one of: {", ".join(map(str, self.choices))}')
            return value

        return str(value)
