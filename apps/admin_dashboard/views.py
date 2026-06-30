"""Admin dashboard views - metrics and admin actions."""
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User
from apps.products.models import Product
from apps.buy_requests.models import BuyRequest
from apps.complaints.models import Complaint
from apps.verification.models import VerificationRequest
from apps.categories.models import Category
from apps.users.serializers import UserSerializer
from apps.products.serializers import ProductListSerializer


class DashboardMetricsView(APIView):
    """Aggregate platform metrics for the admin dashboard."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)

        total_users = User.objects.filter(is_active=True).count()
        new_users_7d = User.objects.filter(joined_date__gte=last_7d).count()
        new_users_30d = User.objects.filter(joined_date__gte=last_30d).count()

        verified_sellers = User.objects.filter(verified_seller=True).count()
        suspended_users = User.objects.filter(is_suspended=True).count()
        banned_users = User.objects.filter(is_banned=True).count()

        total_products = Product.objects.exclude(status=Product.Status.DELETED).count()
        active_listings = Product.objects.filter(status=Product.Status.AVAILABLE).count()
        sold_count = Product.objects.filter(status=Product.Status.SOLD).count()
        archived_count = Product.objects.filter(status=Product.Status.ARCHIVED).count()
        unlisted_count = Product.objects.filter(status=Product.Status.UNLISTED).count()

        pending_verifications = VerificationRequest.objects.filter(
            status=VerificationRequest.Status.PENDING
        ).count()

        open_complaints = Complaint.objects.exclude(
            status__in=[Complaint.Status.DISMISSED, Complaint.Status.RESOLVED]
        ).count()

        total_buy_requests = BuyRequest.objects.count()
        pending_buy_requests = BuyRequest.objects.filter(status=BuyRequest.Status.PENDING).count()

        total_categories = Category.objects.filter(is_active=True).count()

        # Listings per category
        category_stats = list(
            Product.objects.exclude(status=Product.Status.DELETED)
            .values('category__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Buy requests per day (last 14 days)
        buy_request_trend = []
        for i in range(13, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            count = BuyRequest.objects.filter(created_at__gte=day_start, created_at__lt=day_end).count()
            buy_request_trend.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'count': count,
            })

        return Response({
            'users': {
                'total': total_users,
                'new_7d': new_users_7d,
                'new_30d': new_users_30d,
                'verified_sellers': verified_sellers,
                'suspended': suspended_users,
                'banned': banned_users,
            },
            'products': {
                'total': total_products,
                'active': active_listings,
                'sold': sold_count,
                'archived': archived_count,
                'unlisted': unlisted_count,
            },
            'verifications': {
                'pending': pending_verifications,
            },
            'complaints': {
                'open': open_complaints,
            },
            'buy_requests': {
                'total': total_buy_requests,
                'pending': pending_buy_requests,
            },
            'categories': {
                'total': total_categories,
                'top_categories': category_stats,
            },
            'trends': {
                'buy_requests_14d': buy_request_trend,
            },
        })


class AdminUserListView(generics.ListAPIView):
    """Admin: list/search/sort all users."""

    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = User.objects.all()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(full_name__icontains=search) |
                Q(mobile_number__icontains=search)
            )
        status_filter = self.request.query_params.get('status')
        if status_filter == 'suspended':
            qs = qs.filter(is_suspended=True)
        elif status_filter == 'banned':
            qs = qs.filter(is_banned=True)
        elif status_filter == 'verified':
            qs = qs.filter(verified_seller=True)
        return qs.order_by('-joined_date')


class AdminUserActionView(APIView):
    """Admin: suspend/ban/verify/unverify a user."""

    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        from django.shortcuts import get_object_or_404
        user = get_object_or_404(User, pk=user_id)
        action = request.data.get('action')
        duration_days = int(request.data.get('duration_days', 7))
        reason = request.data.get('reason', '')

        if action == 'suspend':
            user.is_suspended = True
            user.suspended_until = timezone.now() + timedelta(days=duration_days)
            user.save(update_fields=['is_suspended', 'suspended_until'])
        elif action == 'unsuspend':
            user.is_suspended = False
            user.suspended_until = None
            user.save(update_fields=['is_suspended', 'suspended_until'])
        elif action == 'ban':
            user.is_banned = True
            user.save(update_fields=['is_banned'])
        elif action == 'unban':
            user.is_banned = False
            user.save(update_fields=['is_banned'])
        elif action == 'verify':
            user.verified_seller = True
            user.verified_seller_badge_date = timezone.now()
            user.save(update_fields=['verified_seller', 'verified_seller_badge_date'])
        elif action == 'unverify':
            user.verified_seller = False
            user.verified_seller_badge_date = None
            user.save(update_fields=['verified_seller', 'verified_seller_badge_date'])
        else:
            return Response({'detail': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.notifications.utils import create_notification
        create_notification(
            user=user,
            title=f'Account action: {action}',
            message=f'Your account status has been updated by admin. Reason: {reason}' if reason else f'Your account status has been updated by admin.',
            notification_type='admin_action',
        )

        return Response({
            'message': f'Action {action} applied to {user.email}.',
            'user': UserSerializer(user).data,
        })


class AdminProductListView(generics.ListAPIView):
    """Admin: list/search all products."""

    serializer_class = ProductListSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = Product.objects.exclude(status=Product.Status.DELETED).select_related(
            'seller', 'category'
        ).prefetch_related('images')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(seller__email__icontains=search) |
                Q(district__icontains=search)
            )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-listed_at')


class AdminProductActionView(APIView):
    """Admin: feature/unfeature/archive/force-delete a product."""

    permission_classes = [IsAdminUser]

    def post(self, request, product_id):
        from django.shortcuts import get_object_or_404
        product = get_object_or_404(Product, pk=product_id)
        action = request.data.get('action')

        if action == 'feature':
            product.is_featured = True
            product.save(update_fields=['is_featured'])
        elif action == 'unfeature':
            product.is_featured = False
            product.save(update_fields=['is_featured'])
        elif action == 'archive':
            product.status = Product.Status.ARCHIVED
            product.archived_at = timezone.now()
            product.save(update_fields=['status', 'archived_at'])
        elif action == 'delete':
            product.status = Product.Status.DELETED
            product.save(update_fields=['status'])
        else:
            return Response({'detail': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'Action {action} applied to "{product.title}".'})
