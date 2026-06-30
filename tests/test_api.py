"""
API tests for the users, products, buy_requests endpoints.
"""
import pytest
from django.urls import reverse
from apps.users.models import User, OTPVerification
from apps.products.models import Product


@pytest.mark.api
@pytest.mark.django_db
class TestAuthAPI:
    def test_register_endpoint(self, api_client, user_data):
        response = api_client.post('/api/auth/register/', user_data, format='json')
        assert response.status_code == 201
        assert 'OTP' in response.data['message'] or 'otp' in response.data
        assert User.objects.filter(email='test@example.com').exists()

    def test_register_duplicate_email(self, api_client, regular_user, user_data):
        user_data['email'] = 'user@example.com'
        response = api_client.post('/api/auth/register/', user_data, format='json')
        assert response.status_code == 400

    def test_login_inactive_user(self, api_client, user_data):
        # Register but don't verify OTP -> account inactive
        api_client.post('/api/auth/register/', user_data, format='json')
        response = api_client.post('/api/auth/login/', {
            'email': user_data['email'], 'password': user_data['password'],
        }, format='json')
        assert response.status_code == 400

    def test_login_verified_user(self, api_client, regular_user):
        response = api_client.post('/api/auth/login/', {
            'email': 'user@example.com', 'password': 'TestPass123!',
        }, format='json')
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data

    def test_login_wrong_password(self, api_client, regular_user):
        response = api_client.post('/api/auth/login/', {
            'email': 'user@example.com', 'password': 'WrongPass',
        }, format='json')
        assert response.status_code == 400

    def test_otp_verify_activates_account(self, api_client, user_data):
        api_client.post('/api/auth/register/', user_data, format='json')
        user = User.objects.get(email='test@example.com')
        otp = OTPVerification.objects.filter(user=user).first()
        response = api_client.post('/api/auth/otp/verify/', {
            'email': user.email, 'code': otp.code, 'purpose': 'email_register',
        }, format='json')
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active
        assert user.email_verified

    def test_profile_requires_auth(self, api_client):
        response = api_client.get('/api/users/me/')
        assert response.status_code == 401

    def test_profile_authenticated(self, auth_client, regular_user):
        response = auth_client.get('/api/users/me/')
        assert response.status_code == 200
        assert response.data['email'] == regular_user.email

    def test_token_refresh(self, api_client, regular_user):
        login_res = api_client.post('/api/auth/login/', {
            'email': 'user@example.com', 'password': 'TestPass123!',
        }, format='json')
        refresh = login_res.data['refresh']
        response = api_client.post('/api/auth/token/refresh/', {'refresh': refresh}, format='json')
        assert response.status_code == 200
        assert 'access' in response.data


@pytest.mark.api
@pytest.mark.django_db
class TestProductAPI:
    def test_search_public(self, api_client, regular_user, category):
        Product.objects.create(
            title='Public Listing', description='Test', price=5000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        response = api_client.get('/api/products/')
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_create_requires_auth(self, api_client, category):
        response = api_client.post('/api/products/create/', {}, format='json')
        assert response.status_code == 401

    def test_search_with_filter(self, api_client, regular_user, category):
        Product.objects.create(
            title='Cheap Item', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        Product.objects.create(
            title='Expensive Item', description='Desc', price=100000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        response = api_client.get('/api/products/?min_price=50000')
        assert response.status_code == 200
        assert all(p['price'] >= '50000' or float(p['price']) >= 50000 for p in response.data['results'])

    def test_my_listings(self, auth_client, regular_user, category):
        Product.objects.create(
            title='My Item', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        response = auth_client.get('/api/products/mine/')
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_product_detail_increments_views(self, api_client, regular_user, category):
        from django.utils import timezone
        product = Product.objects.create(
            title='Detail Test', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        initial_views = product.views_count
        response = api_client.get(f'/api/products/{product.slug}/')
        assert response.status_code == 200
        product.refresh_from_db()
        assert product.views_count == initial_views + 1

    def test_product_status_update_by_owner(self, auth_client, regular_user, category):
        product = Product.objects.create(
            title='Status Update', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        response = auth_client.patch(f'/api/products/{product.slug}/status/', {'status': 'sold'}, format='json')
        assert response.status_code == 200
        product.refresh_from_db()
        assert product.status == 'sold'

    def test_product_status_update_by_non_owner(self, api_client, regular_user, verified_user, category):
        product = Product.objects.create(
            title='Other Owner', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        # login as verified_user (different)
        login_res = api_client.post('/api/auth/login/', {
            'email': 'verified@example.com', 'password': 'TestPass123!',
        }, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_res.data["access"]}')
        response = api_client.patch(f'/api/products/{product.slug}/status/', {'status': 'sold'}, format='json')
        assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
class TestBuyRequestAPI:
    def test_create_buy_request_guest(self, api_client, regular_user, category):
        product = Product.objects.create(
            title='Buy Test', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        response = api_client.post('/api/buy-requests/create/', {
            'product': product.id,
            'buyer_name': 'Buyer',
            'buyer_phone': '+919999999999',
            'buyer_message': 'Interested',
        }, format='json')
        assert response.status_code == 201
        product.refresh_from_db()
        assert product.status == 'pending'
        assert product.buy_request_count == 1
        assert product.seller_action_deadline is not None

    def test_cannot_buy_own_product(self, auth_client, regular_user, category):
        product = Product.objects.create(
            title='Own Buy', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        response = auth_client.post('/api/buy-requests/create/', {
            'product': product.id,
            'buyer_name': regular_user.full_name,
            'buyer_phone': regular_user.mobile_number,
        }, format='json')
        assert response.status_code == 400

    def test_seller_accepts_request(self, api_client, regular_user, verified_user, category):
        # verified_user owns the product
        product = Product.objects.create(
            title='Accept Test', description='Desc', price=1000,
            category=category, seller=verified_user,
            location_name='X', district='Y', state='Z',
        )
        # regular_user sends a buy request (as guest)
        create_res = api_client.post('/api/buy-requests/create/', {
            'product': product.id,
            'buyer_name': 'Buyer',
            'buyer_phone': '+919999999999',
        }, format='json')
        buy_request_id = create_res.data['id']

        # Login as seller (verified_user)
        login_res = api_client.post('/api/auth/login/', {
            'email': 'verified@example.com', 'password': 'TestPass123!',
        }, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_res.data["access"]}')

        response = api_client.post(f'/api/buy-requests/{buy_request_id}/action/', {
            'action': 'accept', 'seller_response': 'OK',
        }, format='json')
        assert response.status_code == 200
        product.refresh_from_db()
        assert product.status == 'reserved'


@pytest.mark.api
@pytest.mark.django_db
class TestCategoryAPI:
    def test_list_categories_public(self, api_client, category):
        response = api_client.get('/api/categories/')
        assert response.status_code == 200
        # Response may be a list or paginated; handle both
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            data = data['results']
        assert any(c['name'] == 'Mobile' for c in data)

    def test_create_category_admin_only(self, api_client, admin_client):
        # Non-admin unauthenticated: should be 401 or 403
        response = api_client.post('/api/categories/admin/create/', {'name': 'XYZTest', 'slug': 'xyztest'}, format='json')
        assert response.status_code in (401, 403), f'Expected 401/403, got {response.status_code}'
        # Admin: allowed (provide slug explicitly)
        response = admin_client.post('/api/categories/admin/create/', {
            'name': 'New Cat XYZ', 'slug': 'new-cat-xyz', 'description': 'Test',
        }, format='json')
        assert response.status_code == 201, f'Expected 201, got {response.status_code}: {response.data}'
