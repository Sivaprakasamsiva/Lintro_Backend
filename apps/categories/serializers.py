"""Categories serializers."""
from rest_framework import serializers
from .models import Category, CategoryField
from apps.categories.models import Category


class CategoryFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryField
        fields = [
            'id', 'category', 'name', 'label', 'field_type',
            'is_required', 'is_filterable', 'choices', 'unit', 'display_order',
        ]
        read_only_fields = ['id', 'category']


class CategorySerializer(serializers.ModelSerializer):
    custom_fields = CategoryFieldSerializer(many=True, read_only=True)
    subcategories = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'parent',
            'is_active', 'display_order', 'custom_fields', 'subcategories',
            'product_count', 'created_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at']

    def get_subcategories(self, obj):
        if not obj.is_parent:
            return []
        return CategorySerializer(
            obj.subcategories.filter(is_active=True), many=True
        ).data

    def get_product_count(self, obj):
        if not hasattr(obj, 'product_set'):
            return 0
        return obj.product_set.filter(status='available').count()


class CategoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating categories (admin only)."""

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'parent',
            'is_active', 'display_order',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True},
            'icon': {'required': False, 'allow_blank': True},
        }

    def validate_name(self, value):
        qs = Category.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A category with this name already exists.')
        return value

    def create(self, validated_data):
        from django.utils.text import slugify
        if not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)


class CategoryFieldCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryField
        fields = [
            'id', 'name', 'label', 'field_type',
            'is_required', 'is_filterable', 'choices', 'unit', 'display_order',
        ]
        read_only_fields = ['id']

    def validate_name(self, value):
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', value):
            raise serializers.ValidationError(
                'Field name must be snake_case (lowercase letters, digits, underscore).'
            )
        return value

    def validate(self, attrs):
        if attrs.get('field_type') == Category.FieldType.CHOICE and not attrs.get('choices'):
            raise serializers.ValidationError({'choices': 'Choices are required for choice fields.'})
        return attrs
