"""Buy request views."""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.utils import create_notification
from apps.notifications.emails import send_buy_request_email
from apps.products.models import Product

from .models import BuyRequest
from .serializers import (
    BuyRequestCreateSerializer, BuyRequestListSerializer, BuyRequestActionSerializer,
)


class BuyRequestCreateView(generics.CreateAPIView):
    """Create a buy request for a product."""

    serializer_class = BuyRequestCreateSerializer
    permission_classes = [AllowAny]  # Guests can also send requests

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        product = get_object_or_404(Product, pk=product_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        buy_request = serializer.save()

        # Update product status to pending + set seller action deadline
        hours = getattr(settings, 'DEFAULT_24HR_ACTION_HOURS', 24)
        Product.objects.filter(pk=product.pk).update(
            status=Product.Status.PENDING,
            last_buy_request_at=timezone.now(),
            seller_action_deadline=timezone.now() + timezone.timedelta(hours=hours),
        )
        product.refresh_from_db()
        product.increment_buy_requests()

        # Notify seller (in-app + email)
        create_notification(
            user=product.seller,
            title=f'New buy request for "{product.title}"',
            message=f'{buy_request.buyer_name} wants to buy your listing. Respond within 24 hours.',
            notification_type='buy_request_received',
            related_id=str(buy_request.id),
        )
        send_buy_request_email(product.seller, product, buy_request)

        return Response(
            BuyRequestListSerializer(buy_request).data,
            status=status.HTTP_201_CREATED,
        )


class MyReceivedBuyRequestsView(generics.ListAPIView):
    """Seller views buy requests received on their listings."""

    serializer_class = BuyRequestListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        status_param = self.request.query_params.get('status')
        qs = BuyRequest.objects.filter(
            product__seller=self.request.user
        ).select_related('product', 'buyer', 'product__seller', 'product__category').prefetch_related('product__images')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs


class MySentBuyRequestsView(generics.ListAPIView):
    """Buyer views buy requests they have sent (if logged in)."""

    serializer_class = BuyRequestListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BuyRequest.objects.filter(buyer=self.request.user).select_related(
            'product', 'product__seller'
        )


class BuyRequestDetailView(generics.RetrieveAPIView):
    """View a specific buy request (seller of the product or buyer themselves)."""

    serializer_class = BuyRequestListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return BuyRequest.objects.filter(
            Q(product__seller=user) | Q(buyer=user)
        )


class BuyRequestActionView(APIView):
    """Seller accepts/rejects a buy request."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        buy_request = get_object_or_404(BuyRequest, pk=pk, product__seller=request.user)
        if buy_request.status != BuyRequest.Status.PENDING:
            return Response(
                {'detail': f'Request already {buy_request.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BuyRequestActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']
        response_msg = serializer.validated_data.get('seller_response', '')

        buy_request.status = (
            BuyRequest.Status.ACCEPTED if action == 'accept' else BuyRequest.Status.REJECTED
        )
        buy_request.seller_response = response_msg
        buy_request.seller_responded_at = timezone.now()
        buy_request.save(update_fields=['status', 'seller_response', 'seller_responded_at', 'updated_at'])

        # Update product status: if accepted, mark reserved; if rejected and no pending requests, back to available
        product = buy_request.product
        if action == 'accept':
            product.status = Product.Status.RESERVED
            product.seller_action_deadline = None
            product.save(update_fields=['status', 'seller_action_deadline'])
        else:
            still_pending = BuyRequest.objects.filter(
                product=product, status=BuyRequest.Status.PENDING
            ).exists()
            if not still_pending:
                product.status = Product.Status.AVAILABLE
                product.seller_action_deadline = None
                product.save(update_fields=['status', 'seller_action_deadline'])

        # Notify buyer (if registered)
        if buy_request.buyer:
            title = f'Seller {action}ed your buy request' if action == 'accept' else 'Seller declined your buy request'
            create_notification(
                user=buy_request.buyer,
                title=title,
                message=(
                    f'The seller of "{product.title}" has {action}ed your buy request. '
                    f'{response_msg}'
                ).strip(),
                notification_type='buy_request_response',
                related_id=str(buy_request.id),
            )

        return Response({
            'message': f'Buy request {action}ed.',
            'status': buy_request.status,
        })


class BuyRequestWithdrawView(APIView):
    """Buyer withdraws their own buy request."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        buy_request = get_object_or_404(BuyRequest, pk=pk, buyer=request.user)
        if buy_request.status != BuyRequest.Status.PENDING:
            return Response({'detail': 'Cannot withdraw a request that has been responded to.'}, status=status.HTTP_400_BAD_REQUEST)
        buy_request.status = BuyRequest.Status.WITHDRAWN
        buy_request.save(update_fields=['status', 'updated_at'])
        return Response({'message': 'Buy request withdrawn.'})
