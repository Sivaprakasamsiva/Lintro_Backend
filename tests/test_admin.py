"""
Admin tests - admin dashboard endpoints and actions.
"""
import pytest
from apps.users.models import User
from apps.products.models import Product


@pytest.mark.admin
@pytest.mark.django_db
class TestAdminDashboard:
    def test_metrics_endpoint(self, admin_client):
        response = admin_client.get('/api/admin/metrics/')
        assert response.status_code == 200
        assert 'users' in response.data
        assert 'products' in response.data
        assert 'complaints' in response.data

    def test_metrics_require_admin(self, auth_client):
        response = auth_client.get('/api/admin/metrics/')
        assert response.status_code == 403


@pytest.mark.admin
@pytest.mark.django_db
class TestAdminUserActions:
    def test_suspend_user(self, admin_client, regular_user):
        response = admin_client.post(f'/api/admin/users/{regular_user.id}/action/', {
            'action': 'suspend', 'reason': 'Spam', 'duration_days': 7,
        }, format='json')
        assert response.status_code == 200
        regular_user.refresh_from_db()
        assert regular_user.is_suspended
        assert regular_user.suspended_until is not None

    def test_ban_user(self, admin_client, regular_user):
        response = admin_client.post(f'/api/admin/users/{regular_user.id}/action/', {
            'action': 'ban', 'reason': 'Repeat fraud',
        }, format='json')
        assert response.status_code == 200
        regular_user.refresh_from_db()
        assert regular_user.is_banned

    def test_verify_user(self, admin_client, regular_user):
        response = admin_client.post(f'/api/admin/users/{regular_user.id}/action/', {
            'action': 'verify',
        }, format='json')
        assert response.status_code == 200
        regular_user.refresh_from_db()
        assert regular_user.verified_seller

    def test_unsuspend_user(self, admin_client, regular_user):
        from django.utils import timezone
        regular_user.is_suspended = True
        regular_user.suspended_until = timezone.now() + timezone.timedelta(days=3)
        regular_user.save()
        response = admin_client.post(f'/api/admin/users/{regular_user.id}/action/', {
            'action': 'unsuspend',
        }, format='json')
        assert response.status_code == 200
        regular_user.refresh_from_db()
        assert not regular_user.is_suspended


@pytest.mark.admin
@pytest.mark.django_db
class TestAdminProductActions:
    def test_feature_product(self, admin_client, regular_user, category):
        product = Product.objects.create(
            title='Feature Test', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        response = admin_client.post(f'/api/admin/products/{product.id}/action/', {
            'action': 'feature',
        }, format='json')
        assert response.status_code == 200
        product.refresh_from_db()
        assert product.is_featured

    def test_archive_product(self, admin_client, regular_user, category):
        product = Product.objects.create(
            title='Archive Test', description='Desc', price=1000,
            category=category, seller=regular_user,
            location_name='X', district='Y', state='Z',
        )
        response = admin_client.post(f'/api/admin/products/{product.id}/action/', {
            'action': 'archive',
        }, format='json')
        assert response.status_code == 200
        product.refresh_from_db()
        assert product.status == Product.Status.ARCHIVED


@pytest.mark.admin
@pytest.mark.django_db
class TestAdminComplaintReview:
    def test_warn_user(self, admin_client, regular_user, verified_user):
        from apps.complaints.models import Complaint
        complaint = Complaint.objects.create(
            reported_user=regular_user, complainant=verified_user,
            category='spam', description='User keeps posting spam listings',
        )
        response = admin_client.patch(f'/api/complaints/admin/{complaint.id}/review/', {
            'action': 'warn', 'resolution': 'User warned via notification',
        }, format='json')
        assert response.status_code == 200
        complaint.refresh_from_db()
        assert complaint.status == 'warned'
        assert complaint.handled_by is not None
