"""
Unit tests for the products app.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io

from apps.products.models import Product, ProductImage, Favorite
from apps.products.serializers import (
    ProductCreateSerializer, ProductDetailSerializer, validate_image_file,
)
from apps.categories.models import Category, CategoryField


@pytest.mark.unit
@pytest.mark.django_db
class TestProductModel:
    def test_create_product(self, db, regular_user, category):
        product = Product.objects.create(
            title='iPhone 13', description='Excellent condition',
            price=45000, category=category, seller=regular_user,
            location_name='Andheri', district='Tirupur', state='TamilNadu',
        )
        assert product.slug.startswith('iphone-13')
        assert product.status == Product.Status.AVAILABLE
        assert product.expires_at is not None

    def test_increment_views(self, db, regular_user, category):
        product = Product.objects.create(
            title='Test', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        initial = product.views_count
        product.increment_views()
        product.refresh_from_db()
        assert product.views_count == initial + 1

    def test_increment_buy_requests(self, db, regular_user, category):
        product = Product.objects.create(
            title='Test', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        product.increment_buy_requests()
        product.refresh_from_db()
        assert product.buy_request_count == 1

    def test_price_display(self, db, regular_user, category):
        product = Product.objects.create(
            title='Test', description='Desc', price=45000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        assert '₹' in product.price_display
        assert '45,000' in product.price_display

    def test_is_searchable_statuses(self, db, regular_user, category):
        product = Product.objects.create(
            title='Test', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        assert product.is_searchable
        product.status = Product.Status.SOLD
        assert not product.is_searchable
        product.status = Product.Status.ARCHIVED
        assert not product.is_searchable
        product.status = Product.Status.DELETED
        assert not product.is_searchable


@pytest.mark.unit
@pytest.mark.django_db
class TestCategoryModel:
    def test_category_creation(self, db):
        cat = Category.objects.create(name='Test Cat', slug='test-cat')
        assert cat.is_parent
        assert str(cat) == 'Test Cat'

    def test_subcategory(self, db):
        parent = Category.objects.create(name='Parent', slug='parent')
        child = Category.objects.create(name='Child', slug='child', parent=parent)
        assert not child.is_parent
        assert child in parent.subcategories.all()


@pytest.mark.unit
@pytest.mark.django_db
class TestCategoryFieldValidation:
    def test_required_field_missing(self, db):
        cat = Category.objects.create(name='Cat', slug='cat')
        field = CategoryField.objects.create(
            category=cat, name='brand', label='Brand',
            field_type=Category.FieldType.TEXT, is_required=True,
        )
        with pytest.raises(ValueError):
            field.validate_value(None)

    def test_number_field_valid(self, db):
        cat = Category.objects.create(name='Cat', slug='cat2')
        field = CategoryField.objects.create(
            category=cat, name='ram', label='RAM',
            field_type=Category.FieldType.NUMBER,
        )
        assert field.validate_value('8') == 8.0

    def test_number_field_invalid(self, db):
        cat = Category.objects.create(name='Cat3', slug='cat3')
        field = CategoryField.objects.create(
            category=cat, name='ram', label='RAM',
            field_type=Category.FieldType.NUMBER,
        )
        with pytest.raises(ValueError):
            field.validate_value('abc')

    def test_choice_field_valid(self, db):
        cat = Category.objects.create(name='Cat4', slug='cat4')
        field = CategoryField.objects.create(
            category=cat, name='color', label='Color',
            field_type=Category.FieldType.CHOICE,
            choices=['Red', 'Blue', 'Green'],
        )
        assert field.validate_value('Red') == 'Red'

    def test_choice_field_invalid(self, db):
        cat = Category.objects.create(name='Cat5', slug='cat5')
        field = CategoryField.objects.create(
            category=cat, name='color', label='Color',
            field_type=Category.FieldType.CHOICE,
            choices=['Red', 'Blue'],
        )
        with pytest.raises(ValueError):
            field.validate_value('Yellow')

    def test_boolean_field(self, db):
        cat = Category.objects.create(name='Cat6', slug='cat6')
        field = CategoryField.objects.create(
            category=cat, name='warranty', label='Warranty',
            field_type=Category.FieldType.BOOLEAN,
        )
        assert field.validate_value('true') is True
        assert field.validate_value('false') is False
        assert field.validate_value(True) is True


@pytest.mark.unit
@pytest.mark.django_db
class TestFavoriteModel:
    def test_unique_favorite(self, db, regular_user, category):
        product = Product.objects.create(
            title='Test', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        Favorite.objects.create(user=regular_user, product=product)
        with pytest.raises(Exception):
            Favorite.objects.create(user=regular_user, product=product)


@pytest.mark.unit
@pytest.mark.django_db
class TestImageValidation:
    def _make_image(self, format='JPEG', size=(100, 100)):
        img = Image.new('RGB', size)
        buf = io.BytesIO()
        img.save(buf, format=format)
        buf.seek(0)
        return SimpleUploadedFile('test.jpg', buf.getvalue(), content_type='image/jpeg')

    def test_valid_image(self):
        img = self._make_image()
        assert validate_image_file(img) is img

    def test_oversized_image(self):
        img = SimpleUploadedFile('big.jpg', b'x' * (9 * 1024 * 1024), content_type='image/jpeg')
        from rest_framework import serializers as drf
        with pytest.raises(drf.ValidationError):
            validate_image_file(img)
