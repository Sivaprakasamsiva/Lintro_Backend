"""Products views."""
import math
from django.db.models import Q, F, Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters import rest_framework as filters

from apps.notifications.utils import create_notification

from .models import Product, ProductImage, Favorite
from .serializers import (
    ProductListSerializer, ProductDetailSerializer,
    ProductCreateSerializer, FavoriteSerializer,
    ProductStatusUpdateSerializer,
)


class ProductFilter(filters.FilterSet):
    """Filters for product search."""
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = filters.UUIDFilter(field_name='category_id')
    category_slug = filters.CharFilter(field_name='category__slug')
    condition = filters.CharFilter(field_name='condition')
    district = filters.CharFilter(field_name='district', lookup_expr='iexact')
    state = filters.CharFilter(field_name='state', lookup_expr='iexact')
    verified_seller = filters.BooleanFilter(field_name='seller__verified_seller')
    negotiable = filters.BooleanFilter(field_name='negotiable')
    q = filters.CharFilter(method='filter_query', help_text='Search query')

    class Meta:
        model = Product
        fields = ['min_price', 'max_price', 'category', 'category_slug',
                  'condition', 'district', 'state', 'verified_seller',
                  'negotiable', 'q']

    def filter_query(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(district__icontains=value) |
            Q(state__icontains=value) |
            Q(category__name__icontains=value)
        )


class ProductSearchView(generics.ListAPIView):
    """Search/list products with filters, sorting, and pagination."""

    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ProductFilter
    ordering_fields = ['price', 'listed_at', 'views_count', 'buy_request_count']

    def get_queryset(self):
        qs = Product.objects.filter(
            status__in=[Product.Status.AVAILABLE, Product.Status.PENDING, Product.Status.RESERVED]
        ).select_related('seller', 'category').prefetch_related('images')

        # Sort
        sort = self.request.query_params.get('sort', 'newest')
        if sort == 'price_low':
            qs = qs.order_by('price')
        elif sort == 'price_high':
            qs = qs.order_by('-price')
        elif sort == 'oldest':
            qs = qs.order_by('listed_at')
        elif sort == 'popular':
            qs = qs.order_by('-views_count')
        elif sort == 'demanded':
            qs = qs.order_by('-buy_request_count')
        elif sort == 'verified':
            qs = qs.order_by('-seller__verified_seller', '-listed_at')
        else:  # newest
            qs = qs.order_by('-listed_at')

        # Nearby sort handled in list()
        return qs

    def list(self, request, *args, **kwargs):
        sort = request.query_params.get('sort', 'newest')
        if sort == 'nearby':
            lat = request.query_params.get('lat')
            lng = request.query_params.get('lng')
            if lat and lng:
                try:
                    lat_f, lng_f = float(lat), float(lng)
                    from geopy.distance import geodesic
                    qs = self.get_queryset().filter(latitude__isnull=False, longitude__isnull=False)
                    products = list(qs)
                    products.sort(
                        key=lambda p: geodesic(
                            (lat_f, lng_f), (float(p.latitude), float(p.longitude))
                        ).km
                    )
                    page = self.paginate_queryset(products)
                    if page is not None:
                        serializer = self.get_serializer(page, many=True)
                        return self.get_paginated_response(serializer.data)
                    serializer = self.get_serializer(products, many=True)
                    return Response(serializer.data)
                except (ValueError, TypeError, ImportError):
                    pass
        return super().list(request, *args, **kwargs)


class ProductDetailView(generics.RetrieveAPIView):
    """Get product detail; increments views."""

    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    queryset = Product.objects.exclude(status=Product.Status.DELETED).select_related('seller', 'category').prefetch_related('images')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Don't increment views for own products
        if not (request.user.is_authenticated and instance.seller_id == request.user.id):
            instance.increment_views()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ProductCreateView(generics.CreateAPIView):
    """Seller creates a new listing."""

    serializer_class = ProductCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        product = serializer.save()
        create_notification(
            user=product.seller,
            title='Listing Published',
            message=f'Your listing "{product.title}" is now live.',
            notification_type='listing_published',
            related_id=str(product.id),
        )


class ProductUpdateView(generics.UpdateAPIView):
    """Seller updates their own listing."""

    serializer_class = ProductCreateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user).exclude(
            status=Product.Status.DELETED
        )


class ProductDeleteView(APIView):
    """Soft delete own listing."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, slug):
        product = get_object_or_404(Product, slug=slug, seller=request.user)
        product.status = Product.Status.DELETED
        product.save(update_fields=['status'])
        return Response({'message': 'Listing deleted.'}, status=status.HTTP_200_OK)


class MyListingsView(generics.ListAPIView):
    """Seller's own listings (any status)."""

    serializer_class = ProductListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        status_param = self.request.query_params.get('status')
        qs = Product.objects.filter(seller=self.request.user).exclude(
            status=Product.Status.DELETED
        ).select_related('seller', 'category').prefetch_related('images')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs


class ProductStatusUpdateView(APIView):
    """Seller updates status (available/reserved/sold) of own product."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, slug):
        product = get_object_or_404(Product, slug=slug, seller=request.user)
        old_status = product.status
        serializer = ProductStatusUpdateSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        product.status = new_status
        # Clear 24h deadline if seller acts
        product.seller_action_deadline = None
        product.save(update_fields=['status', 'seller_action_deadline', 'updated_at'])

        if new_status == Product.Status.SOLD:
            create_notification(
                user=product.seller,
                title='Listing Marked as Sold',
                message=f'Your listing "{product.title}" has been marked as sold.',
                notification_type='listing_sold',
                related_id=str(product.id),
            )

        return Response({
            'message': f'Status updated from {old_status} to {new_status}.',
            'status': new_status,
        })


class FeaturedProductsView(generics.ListAPIView):
    """Featured listings on homepage."""

    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Product.objects.filter(
            status=Product.Status.AVAILABLE, is_featured=True
        ).select_related('seller', 'category').prefetch_related('images')[:12]


class RecentProductsView(generics.ListAPIView):
    """Recent listings on homepage."""

    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Product.objects.filter(
            status=Product.Status.AVAILABLE
        ).select_related('seller', 'category').prefetch_related('images').order_by('-listed_at')[:24]


class FavoriteListView(generics.ListAPIView):
    """User's favorites/wishlist."""

    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related(
            'product__seller', 'product__category'
        ).prefetch_related('product__images')


class FavoriteToggleView(APIView):
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)
        if created:
            return Response({'message': 'Added to favorites.', 'is_favorited': True}, status=status.HTTP_201_CREATED)
        favorite.delete()
        return Response({'message': 'Removed from favorites.', 'is_favorited': False}, status=status.HTTP_200_OK)