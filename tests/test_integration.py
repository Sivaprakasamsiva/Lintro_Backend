"""
Integration tests - workflows across multiple components.
"""
import pytest
from django.utils import timezone
from django.test import override_settings
from django.core import mail

from apps.users.models import User
from apps.products.models import Product
from apps.buy_requests.models import BuyRequest as BR
from apps.notifications.models import Notification
from apps.products.tasks import (
    expire_buy_requests, unlist_products_with_missed_deadlines,
    archive_old_unlisted_products, expire_old_listings,
)


@pytest.mark.integration
@pytest.mark.django_db
class TestBuyRequestWorkflow:
    def test_full_buy_request_lifecycle(self, api_client, regular_user, verified_user, category):
        """Test: buyer sends request -> seller accepts -> product marked reserved."""
        # 1. verified_user lists a product
        product = Product.objects.create(
            title='Lifecycle Test', description='Desc', price=10000,
            category=category, seller=verified_user,
            location_name='X', district='Y', state='Z',
        )
        assert product.status == 'available'

        # 2. regular_user sends buy request
        login_res = api_client.post('/api/auth/login/', {
            'email': 'user@example.com', 'password': 'TestPass123!',
        }, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_res.data["access"]}')

        create_res = api_client.post('/api/buy-requests/create/', {
            'product': product.id,
            'buyer_name': regular_user.full_name,
            'buyer_phone': regular_user.mobile_number,
            'buyer_message': 'I want to buy this',
        }, format='json')
        assert create_res.status_code == 201

        product.refresh_from_db()
        assert product.status == 'pending'
        assert product.buy_request_count == 1

        # 3. Seller receives notification
        notifs = Notification.objects.filter(user=verified_user, notification_type='buy_request_received')
        assert notifs.exists()

        # 4. Seller accepts
        login_seller = api_client.post('/api/auth/login/', {
            'email': 'verified@example.com', 'password': 'TestPass123!',
        }, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_seller.data["access"]}')

        accept_res = api_client.post(f'/api/buy-requests/{create_res.data["id"]}/action/', {
            'action': 'accept', 'seller_response': 'OK, call me',
        }, format='json')
        assert accept_res.status_code == 200

        product.refresh_from_db()
        assert product.status == 'reserved'

        # 5. Buyer receives response notification
        notifs = Notification.objects.filter(user=regular_user, notification_type='buy_request_response')
        assert notifs.exists()


@pytest.mark.integration
@pytest.mark.django_db
class Test24HourRule:
    def test_expired_buy_request_unlists_product(self, db, regular_user, verified_user, category):
        """Test: 24h after buy request with no seller action -> product unlisted."""
        product = Product.objects.create(
            title='24h Test', description='Desc', price=1000,
            category=category, seller=verified_user,
            location_name='X', district='Y', state='Z',
        )
        # Create buy request with deadline already passed
        br = BR.objects.create(
            product=product, buyer=regular_user,
            buyer_name='Buyer', buyer_phone='+919999999999',
            deadline_at=timezone.now() - timezone.timedelta(hours=25),
        )
        product.status = Product.Status.PENDING
        product.seller_action_deadline = timezone.now() - timezone.timedelta(hours=25)
        product.save()

        # Run task
        expired_count = expire_buy_requests.apply().get()
        assert expired_count >= 1

        br.refresh_from_db()
        assert br.status == BR.Status.EXPIRED

        # Run unlist task
        unlisted_count = unlist_products_with_missed_deadlines.apply().get()
        assert unlisted_count >= 1

        product.refresh_from_db()
        assert product.status == Product.Status.UNLISTED
        assert product.unlisted_at is not None

        # Seller should be notified
        notifs = Notification.objects.filter(user=verified_user, notification_type='listing_unlisted')
        assert notifs.exists()


@pytest.mark.integration
@pytest.mark.django_db
class Test7DayRule:
    def test_old_unlisted_product_archived(self, db, regular_user, verified_user, category):
        """Test: 7 days after unlisted -> product archived + images deleted."""
        from PIL import Image
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings

        with override_settings(DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage'):
            product = Product.objects.create(
                title='7day Test', description='Desc', price=1000,
                category=category, seller=verified_user,
                location_name='X', district='Y', state='Z',
                status=Product.Status.UNLISTED,
                unlisted_at=timezone.now() - timezone.timedelta(days=8),
            )
            # Add an image
            img = Image.new('RGB', (100, 100))
            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            product_image = product.images.create(
                image=SimpleUploadedFile('test.jpg', buf.getvalue(), content_type='image/jpeg'),
                display_order=0, is_primary=True,
            )

            # Run archive task
            archived_count = archive_old_unlisted_products.apply().get()
            assert archived_count >= 1

            product.refresh_from_db()
            assert product.status == Product.Status.ARCHIVED
            assert product.archived_at is not None

            # Image should be deleted
            assert not product.images.exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestListingExpiry:
    def test_expired_listing_marked(self, db, regular_user, category):
        product = Product.objects.create(
            title='Expiry Test', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        count = expire_old_listings.apply().get()
        assert count >= 1
        product.refresh_from_db()
        assert product.status == Product.Status.EXPIRED


@pytest.mark.integration
@pytest.mark.django_db
class TestVerificationWorkflow:
    def test_admin_approves_verification_grants_badge(self, api_client, admin_user, regular_user):
        from apps.verification.models import VerificationRequest
        from PIL import Image
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile

        with override_settings(DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage'):
            img = Image.new('RGB', (100, 100))
            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            image_file = SimpleUploadedFile('id.jpg', buf.getvalue(), content_type='image/jpeg')

            # User submits verification
            login_res = api_client.post('/api/auth/login/', {
                'email': 'user@example.com', 'password': 'TestPass123!',
            }, format='json')
            api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_res.data["access"]}')
            submit_res = api_client.post('/api/verification/submit/', {
                'id_type': 'aadhaar', 'id_number': '1234',
                'whatsapp_number': '+919999999999',
                'address_line1': 'Addr', 'district': 'M', 'state': 'S', 'pincode': '400001',
                'id_front_image': image_file,
            }, format='multipart')
            assert submit_res.status_code == 201

            verification_id = submit_res.data['id']

            # Admin approves
            login_admin = api_client.post('/api/auth/login/', {
                'email': 'admin@example.com', 'password': 'AdminPass123!',
            }, format='json')
            api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_admin.data["access"]}')

            approve_res = api_client.patch(f'/api/verification/admin/{verification_id}/review/', {
                'status': 'approved', 'admin_notes': 'Looks legit',
            }, format='json')
            assert approve_res.status_code == 200

            regular_user.refresh_from_db()
            assert regular_user.verified_seller
            assert regular_user.verified_seller_badge_date is not None

            # User notified
            notifs = Notification.objects.filter(user=regular_user, notification_type='verification_approved')
            assert notifs.exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestChatWorkflow:
    def test_start_conversation_and_send_message(self, api_client, regular_user, verified_user, category):
        product = Product.objects.create(
            title='Chat Test', description='Desc', price=1000,
            category=category, seller=verified_user,
            location_name='X', district='Y', state='Z',
        )
        # regular_user starts conversation
        login_res = api_client.post('/api/auth/login/', {
            'email': 'user@example.com', 'password': 'TestPass123!',
        }, format='json')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_res.data["access"]}')

        start_res = api_client.post('/api/chat/conversations/start/', {
            'product_id': product.id,
            'initial_message': 'Hi, is this available?',
        }, format='json')
        assert start_res.status_code == 201
        conv_id = start_res.data['id']

        # Send another message
        send_res = api_client.post(f'/api/chat/conversations/{conv_id}/send/', {
            'body': 'Are you negotiable?',
        }, format='json')
        assert send_res.status_code == 201

        # List messages
        list_res = api_client.get(f'/api/chat/conversations/{conv_id}/messages/')
        assert list_res.status_code == 200
        # Should have at least 2 messages (initial + follow-up)
        assert len(list_res.data) >= 2

        # Seller notified (at least once; notifications deduplicate within an hour)
        notifs = Notification.objects.filter(user=verified_user, notification_type='chat_message')
        assert notifs.count() >= 1
