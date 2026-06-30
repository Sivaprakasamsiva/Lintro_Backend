# backend/apps/products/serializers.py
"""Product serializers."""
import os
import io
from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


from apps.categories.models import Category

from apps.categories.models import CategoryField
from apps.users.serializers import UserPublicSerializer

from .models import Product, ProductImage, Favorite


MAX_PRODUCT_IMAGES = getattr(settings, 'MAX_PRODUCT_IMAGES', 5)
MIN_PRODUCT_IMAGES = getattr(settings, 'MIN_PRODUCT_IMAGES', 1)
MAX_IMAGE_UPLOAD_MB = getattr(settings, 'MAX_IMAGE_UPLOAD_MB', 8)
ALLOWED_IMAGE_TYPES = getattr(settings, 'ALLOWED_IMAGE_TYPES', ['image/jpeg', 'image/png', 'image/webp'])


def validate_image_file(file):
    """Validate image type and size."""
    if file.size > MAX_IMAGE_UPLOAD_MB * 1024 * 1024:
        raise serializers.ValidationError(
            f'Image too large. Maximum {MAX_IMAGE_UPLOAD_MB}MB allowed.'
        )
    if hasattr(file, 'content_type') and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise serializers.ValidationError(
            f'Invalid image type. Allowed: JPEG, PNG, WebP.'
        )
    return file


# backend/apps/products/serializers.py

def process_and_compress_image(file):
    """Resize/compress the uploaded image to WebP format (max 1200px)."""
    try:
        # Get original file size
        original_size = file.size
        print(f"📊 Original file: {file.name}, size: {original_size} bytes ({original_size/1024:.1f} KB)")
        
        # Reset file pointer
        file.seek(0)
        
        # Open and convert image
        img = Image.open(file)
        original_dimensions = img.size
        print(f"📊 Original dimensions: {original_dimensions[0]}x{original_dimensions[1]}")
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Resize
        max_size = (1280, 1280)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        new_dimensions = img.size
        print(f"📊 New dimensions: {new_dimensions[0]}x{new_dimensions[1]}")
        
        # Save to buffer as WebP
        buffer = io.BytesIO()
        img.save(buffer, format='WEBP', quality=80, optimize=True)
        buffer.seek(0)
        
        # Get compressed size
        compressed_size = len(buffer.getvalue())
        print(f"📊 Compressed size: {compressed_size} bytes ({compressed_size/1024:.1f} KB)")
        print(f"📊 Compression ratio: {(compressed_size/original_size)*100:.1f}%")
        
        # Create new filename
        original_name = os.path.splitext(file.name)[0]
        new_name = f'{original_name}.webp'
        
        from django.core.files.base import ContentFile
        return ContentFile(buffer.getvalue(), name=new_name), img.size
        
    except Exception as e:
        print(f"❌ Error processing image: {e}")
        print(f"File: {file.name}, Size: {file.size}, Type: {type(file)}")
        raise serializers.ValidationError(f'Failed to process image: {str(e)}')


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'display_order', 'is_primary', 'uploaded_at']
        read_only_fields = ['id', 'image_url', 'uploaded_at']

    def get_image_url(self, obj):
        return obj.url


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight product serializer for list views / cards."""
    seller = UserPublicSerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_favorited = serializers.SerializerMethodField()  # <-- ADD THIS

    class Meta:
        model = Product
        fields = [
            'id', 'slug', 'title', 'price', 'price_display', 'condition',
            'category_name', 'district', 'state', 'status',
            'primary_image', 'seller', 'views_count', 'buy_request_count',
            'listed_at', 'negotiable',
            'is_favorited',  # <-- ADD THIS
        ]

    def get_primary_image(self, obj):
        primary = None
        if hasattr(obj, 'prefetched_primary_image'):
            primary = obj.prefetched_primary_image
        else:
            primary = obj.images.filter(is_primary=True).first()
            if not primary and obj.images.exists():
                primary = obj.images.first()
        return primary.url if primary else None

    def get_is_favorited(self, obj):  # <-- ADD THIS
        """Check if the current user has favorited this product."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Favorite.objects.filter(user=request.user, product=obj).exists()


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product serializer with images and custom fields."""
    seller = UserPublicSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=True)
    is_favorited = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'slug', 'title', 'description', 'price', 'price_display',
            'negotiable', 'condition', 'category_id', 'category_name',
            'seller', 'images', 'custom_fields',
            'location_name', 'district', 'state', 'country',
            'latitude', 'longitude', 'status', 'is_featured',
            'views_count', 'buy_request_count', 'is_favorited',
            'distance_km', 'listed_at', 'updated_at', 'expires_at',
        ]
        read_only_fields = [
            'id', 'slug', 'seller', 'status', 'is_featured',
            'views_count', 'buy_request_count', 'listed_at', 'updated_at',
            'expires_at',
        ]

    def get_is_favorited(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or not user.is_authenticated:
            return False
        return Favorite.objects.filter(user=user, product=obj).exists()

    def get_distance_km(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        if not (lat and lng and obj.latitude and obj.longitude):
            return None
        try:
            from geopy.distance import geodesic
            return round(
                geodesic(
                    (float(lat), float(lng)),
                    (float(obj.latitude), float(obj.longitude)),
                ).km, 2
            )
        except Exception:
            return None

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price must be greater than zero.')
        if value > 10000000:  # 1 crore cap
            raise serializers.ValidationError('Price exceeds maximum allowed value.')
        return value

    def validate_custom_fields(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('custom_fields must be an object.')
        return value

    def validate(self, attrs):
        category_id = attrs.get('category_id') or (self.instance.category_id if self.instance else None)
        if category_id:
            try:
                category = Category.objects.get(pk=category_id, is_active=True)
            except Category.DoesNotExist:
                raise serializers.ValidationError({'category_id': 'Invalid or inactive category.'})

            # Validate custom fields
            custom_fields = attrs.get('custom_fields', {})
            if self.instance and not custom_fields:
                custom_fields = self.instance.custom_fields or {}

            for field_def in category.custom_fields.all():
                value = custom_fields.get(field_def.name)
                try:
                    cleaned = field_def.validate_value(value)
                    if cleaned is not None:
                        custom_fields[field_def.name] = cleaned
                except ValueError as e:
                    raise serializers.ValidationError({'custom_fields': str(e)})

            attrs['custom_fields'] = custom_fields
            attrs['_category'] = category
        return attrs

    def create(self, validated_data):
        validated_data.pop('_category', None)
        seller = self.context['request'].user
        if not seller.can_post_listing():
            raise serializers.ValidationError({'detail': 'Your account cannot post listings.'})
        return super().create(validated_data)


# backend/apps/products/serializers.py

class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for create/update - handles image uploads separately."""

    category_id = serializers.UUIDField(write_only=True, required=True)
    images = serializers.ListField(
        child=serializers.ImageField(),
        min_length=1,  # At least 1 image required
        max_length=MAX_PRODUCT_IMAGES,
        write_only=True,
        required=True,  # Required for create
    )

    class Meta:
        model = Product
        fields = [
            'id', 'slug', 'title', 'description', 'price', 'negotiable',
            'condition', 'category_id', 'custom_fields',
            'location_name', 'district', 'state', 'country',
            'latitude', 'longitude', 'images',
        ]
        read_only_fields = ['id', 'slug']

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price must be greater than zero.')
        if value > 10000000:
            raise serializers.ValidationError('Price exceeds maximum (₹1,00,00,000).')
        return value

    def validate_images(self, value):
        if not value:
            raise serializers.ValidationError('At least 1 image is required.')
        if len(value) > MAX_PRODUCT_IMAGES:
            raise serializers.ValidationError(f'Maximum {MAX_PRODUCT_IMAGES} images allowed.')
        
        validated_images = []
        for img in value:
            try:
                # Validate the image
                validate_image_file(img)
                validated_images.append(img)
            except Exception as e:
                raise serializers.ValidationError(f'Invalid image: {str(e)}')
        return validated_images

    def validate(self, attrs):
        # Reuse logic from ProductDetailSerializer
        category_id = attrs.get('category_id')
        try:
            category = Category.objects.get(pk=category_id, is_active=True)
        except Category.DoesNotExist:
            raise serializers.ValidationError({'category_id': 'Invalid or inactive category.'})

        custom_fields = attrs.get('custom_fields', {})
        if not isinstance(custom_fields, dict):
            raise serializers.ValidationError({'custom_fields': 'Must be an object.'})
        for field_def in category.custom_fields.all():
            value = custom_fields.get(field_def.name)
            try:
                cleaned = field_def.validate_value(value)
                if cleaned is not None:
                    custom_fields[field_def.name] = cleaned
            except ValueError as e:
                raise serializers.ValidationError({'custom_fields': str(e)})
        attrs['custom_fields'] = custom_fields
        return attrs

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        seller = self.context['request'].user
        
        if not seller.can_post_listing():
            raise serializers.ValidationError({'detail': 'Your account cannot post listings.'})

        # Create the product first
        product = Product.objects.create(seller=seller, **validated_data)
        
        # Process and save images
        for idx, image_file in enumerate(images_data):
            try:
                # Log the image details for debugging
                print(f"Processing image {idx}: {image_file.name}, size: {image_file.size}")
                
                # Process the image
                processed_file, size = process_and_compress_image(image_file)
                
                # Create ProductImage
                ProductImage.objects.create(
                    product=product,
                    image=processed_file,
                    display_order=idx,
                    is_primary=(idx == 0),
                    width=size[0],
                    height=size[1],
                )
                print(f"✅ Image {idx} saved successfully")
            except Exception as e:
                print(f"❌ Error processing image {idx}: {e}")
                # Continue with other images, don't fail the entire creation
        
        return product

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle image updates
        if images_data is not None:
            # Delete existing images
            instance.images.all().delete()
            
            # Add new images
            for idx, image_file in enumerate(images_data):
                try:
                    processed_file, size = process_and_compress_image(image_file)
                    ProductImage.objects.create(
                        product=instance,
                        image=processed_file,
                        display_order=idx,
                        is_primary=(idx == 0),
                        width=size[0],
                        height=size[1],
                    )
                except Exception as e:
                    print(f"Error processing image {idx}: {e}")
                    
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'product', 'product_id', 'created_at']
        read_only_fields = ['id', 'created_at', 'product']

    def create(self, validated_data):
        from django.shortcuts import get_object_or_404
        product = get_object_or_404(Product, pk=validated_data['product_id'], status__in=[
            Product.Status.AVAILABLE, Product.Status.PENDING, Product.Status.RESERVED,
        ])
        favorite, created = Favorite.objects.get_or_create(
            user=self.context['request'].user, product=product
        )
        if not created:
            raise serializers.ValidationError({'detail': 'Already in favorites.'})
        return favorite


class ProductStatusUpdateSerializer(serializers.ModelSerializer):
    """Seller updates product status."""

    class Meta:
        model = Product
        fields = ['status']

    def validate_status(self, value):
        if value not in (Product.Status.RESERVED, Product.Status.SOLD, Product.Status.AVAILABLE):
            raise serializers.ValidationError('Invalid status. Use: available, reserved, or sold.')
        return value
