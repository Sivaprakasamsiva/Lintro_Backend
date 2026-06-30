"""Inquiry views."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.utils import create_notification

from .models import Inquiry
from .serializers import InquirySerializer, InquiryCreateSerializer, InquiryAnswerSerializer


class InquiryListView(generics.ListAPIView):
    """List public inquiries for a product."""

    serializer_class = InquirySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        from django.shortcuts import get_object_or_404
        from apps.products.models import Product
        product_id = self.kwargs['product_id']
        product = get_object_or_404(Product, pk=product_id)
        user = self.request.user
        
        # Show ALL public inquiries (both answered and unanswered)
        queryset = Inquiry.objects.filter(product=product, is_public=True)
        
        # If user is the seller, also show non-public inquiries
        if user.is_authenticated and product.seller_id == user.id:
            return Inquiry.objects.filter(product=product)
        
        return queryset


class InquiryCreateView(generics.CreateAPIView):
    """Ask a question on a product (registered or guest)."""

    serializer_class = InquiryCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = serializer.save()

        # Get the asker name
        asker_name = inquiry.asker_name or (inquiry.asker.full_name if inquiry.asker else 'Guest')

        # Create notification WITHOUT the 'data' parameter
        create_notification(
            user=inquiry.product.seller,
            title=f'New question on "{inquiry.product.title}"',
            message=f'{asker_name}: {inquiry.question[:200]}',
            notification_type='inquiry_received',
            related_id=str(inquiry.id),
            # REMOVED: data={...}  <- This was causing the error
        )
        return Response(InquirySerializer(inquiry).data, status=status.HTTP_201_CREATED)


class InquiryAnswerView(APIView):
    """Seller answers an inquiry."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        inquiry = get_object_or_404(Inquiry, pk=pk, product__seller=request.user)
        serializer = InquiryAnswerSerializer(inquiry, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(answered_at=timezone.now())

        if inquiry.asker:
            create_notification(
                user=inquiry.asker,
                title=f'Seller answered your question on "{inquiry.product.title}"',
                message=inquiry.answer[:200],
                notification_type='inquiry_answered',
                related_id=str(inquiry.id),
                # REMOVED: data={...}  <- This was causing the error
            )

        return Response(InquirySerializer(inquiry).data)