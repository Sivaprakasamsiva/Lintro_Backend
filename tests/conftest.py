"""
Pytest configuration for Lintro Marketplace.
"""
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pytest


def pytest_configure(config):
    settings.DEBUG = False
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    client = APIClient()
    return client


@pytest.fixture
def user_data():
    return {
        'email': 'test@example.com',
        'full_name': 'Test User',
        'mobile_number': '+919999999999',
        'password': 'TestPass123!',
        'password2': 'TestPass123!',
        'district': 'Tirupur',
        'state': 'TamilNadu',
    }


@pytest.fixture
def verified_user(db):
    from apps.users.models import User
    user = User.objects.create_user(
        email='verified@example.com',
        password='TestPass123!',
        full_name='Verified User',
        mobile_number='+918888888888',
        email_verified=True,
        is_active=True,
        verified_seller=True,
    )
    return user


@pytest.fixture
def regular_user(db):
    from apps.users.models import User
    user = User.objects.create_user(
        email='user@example.com',
        password='TestPass123!',
        full_name='Regular User',
        mobile_number='+917777777777',
        email_verified=True,
        is_active=True,
    )
    return user


@pytest.fixture
def admin_user(db):
    from apps.users.models import User
    user = User.objects.create_superuser(
        email='admin@example.com',
        password='AdminPass123!',
        full_name='Admin User',
        mobile_number='+916666666666',
    )
    return user


@pytest.fixture
def auth_client(regular_user):
    """A fresh API client authenticated as regular_user."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    refresh = RefreshToken.for_user(regular_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def admin_client(admin_user):
    """A fresh API client authenticated as admin_user."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def category(db):
    from apps.categories.models import Category, CategoryField
    cat = Category.objects.create(name='Mobile', slug='mobile', description='Mobile phones')
    CategoryField.objects.create(category=cat, name='brand', label='Brand', field_type='text', is_required=True, is_filterable=True)
    CategoryField.objects.create(category=cat, name='ram', label='RAM (GB)', field_type='number', is_filterable=True)
    return cat
