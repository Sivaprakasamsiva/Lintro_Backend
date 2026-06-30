"""Categories views."""
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, CategoryField
from .serializers import (
    CategorySerializer, CategoryCreateSerializer,
    CategoryFieldSerializer, CategoryFieldCreateSerializer,
)


class CategoryListView(generics.ListAPIView):
    """List all active categories (public)."""

    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related(
            'custom_fields', 'subcategories__custom_fields'
        )


class CategoryDetailView(generics.RetrieveAPIView):
    """Get a single category by slug (public)."""

    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    queryset = Category.objects.filter(is_active=True)


class CategoryCreateView(generics.CreateAPIView):
    """Admin: create a new category."""

    serializer_class = CategoryCreateSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        from django.utils.text import slugify
        name = serializer.validated_data.get('name')
        slug = serializer.validated_data.get('slug') or slugify(name)
        serializer.save(slug=slug)


class CategoryUpdateView(generics.UpdateAPIView):
    """Admin: update a category."""

    serializer_class = CategoryCreateSerializer
    permission_classes = [IsAdminUser]
    queryset = Category.objects.all()
    lookup_field = 'pk'


class CategoryDeleteView(generics.DestroyAPIView):
    """Admin: delete (soft-delete) a category."""

    permission_classes = [IsAdminUser]
    queryset = Category.objects.all()
    lookup_field = 'pk'

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


class CategoryFieldListView(generics.ListCreateAPIView):
    """List and create custom fields for a category."""

    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return CategoryField.objects.filter(category_id=self.kwargs['category_pk'])

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CategoryFieldCreateSerializer
        return CategoryFieldSerializer

    def perform_create(self, serializer):
        category = get_object_or_404(Category, pk=self.kwargs['category_pk'])
        serializer.save(category=category)


class CategoryFieldDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a custom field."""

    serializer_class = CategoryFieldCreateSerializer
    permission_classes = [IsAdminUser]
    queryset = CategoryField.objects.all()
    lookup_field = 'pk'
