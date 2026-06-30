"""
User views: registration, OTP, JWT auth, profile.
"""
import secrets
import string
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from .models import User, OTPVerification, UserAuditLog
from .serializers import (
    UserSerializer, UserPublicSerializer, RegisterSerializer,
    CustomTokenObtainPairSerializer, OTPRequestSerializer, OTPVerifySerializer,
    ProfileUpdateSerializer, PasswordChangeSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
)
from .utils import get_client_ip, log_audit


def generate_otp(length=6):
    """Generate numeric OTP code."""
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def send_otp_email(email, code, purpose):
    """Send OTP via email. Returns True on success, False on failure.
    BUG-015 fix: log failures instead of silently swallowing them.
    """
    import logging
    logger = logging.getLogger(__name__)

    purpose_text = dict(OTPVerification.Purpose.choices).get(purpose, purpose)
    subject = f'Lintro - Your {purpose_text} OTP'
    message = (
        f'Your One Time Password (OTP) for {purpose_text} is: {code}\n\n'
        f'This OTP is valid for {settings.OTP_EXPIRY_MINUTES} minutes.\n'
        f'If you did not request this, please ignore this email.\n\n'
        f'- Lintro Marketplace'
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f'Failed to send OTP email to {email} (purpose={purpose}): {e}')
        return False


@method_decorator(ratelimit(key='ip', rate=settings.RATE_LIMIT_REGISTER if hasattr(settings, 'RATE_LIMIT_REGISTER') else '3/h', method='all'), name='post')
class RegisterView(APIView):
    """Register a new user account - requires email OTP to activate."""

    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        otp = OTPVerification.objects.create(
            user=user,
            email=user.email,
            code=generate_otp(settings.OTP_LENGTH),
            purpose=OTPVerification.Purpose.EMAIL_REGISTER,
            expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
        )
        send_otp_email(user.email, otp.code, otp.purpose)

        log_audit(request, user, UserAuditLog.Action.REGISTER)
        log_audit(request, user, UserAuditLog.Action.OTP_REQUEST, {'purpose': otp.purpose})

        return Response({
            'message': 'Registration successful. Check your email for OTP to activate your account.',
            'email': user.email,
            'otp_sent': True,
        }, status=status.HTTP_201_CREATED)


class OTPRequestView(APIView):
    """Request a new OTP (registration or password reset)."""

    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='3/h', method='all'))
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = data.get('email')
        mobile = data.get('mobile')
        purpose = data.get('purpose')

        user = None
        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                if purpose == OTPVerification.Purpose.EMAIL_REGISTER:
                    return Response({'detail': 'Email not registered.'}, status=status.HTTP_404_NOT_FOUND)
                if purpose == OTPVerification.Purpose.PASSWORD_RESET:
                    return Response({'detail': 'If the email exists, an OTP has been sent.'})
            if user and purpose == OTPVerification.Purpose.EMAIL_REGISTER and user.email_verified:
                return Response({'detail': 'Email already verified.'}, status=status.HTTP_400_BAD_REQUEST)

        # Invalidate old OTPs for this target/purpose
        OTPVerification.objects.filter(
            email=email, mobile=mobile, purpose=purpose, is_used=False
        ).update(is_used=True)

        otp = OTPVerification.objects.create(
            user=user,
            email=email,
            mobile=mobile or '',
            code=generate_otp(settings.OTP_LENGTH),
            purpose=purpose,
            expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
        )

        if email:
            send_otp_email(email, otp.code, purpose)

        if user:
            log_audit(request, user, UserAuditLog.Action.OTP_REQUEST, {'purpose': purpose})
        return Response({'message': 'OTP sent successfully.', 'otp_sent': True})


class OTPVerifyView(APIView):
    """Verify OTP code."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data.get('email')
        mobile = data.get('mobile')
        code = data['code']
        purpose = data['purpose']

        otp_qs = OTPVerification.objects.filter(
            purpose=purpose, code=code, is_used=False,
        )
        if email:
            otp_qs = otp_qs.filter(email__iexact=email)
        elif mobile:
            otp_qs = otp_qs.filter(mobile=mobile)

        otp = otp_qs.order_by('-created_at').first()
        if not otp:
            # BUG-013 fix: increment attempts on the most-recent matching OTP if it exists,
            # so users cannot brute-force the code without hitting the 5-attempt cap.
            recent = OTPVerification.objects.filter(
                purpose=purpose, is_used=False,
            )
            if email:
                recent = recent.filter(email__iexact=email)
            elif mobile:
                recent = recent.filter(mobile=mobile)
            recent = recent.order_by('-created_at').first()
            if recent:
                recent.attempts = (recent.attempts or 0) + 1
                recent.save(update_fields=['attempts'])
                if recent.attempts >= 5:
                    return Response(
                        {'detail': 'Too many attempts. Please request a new OTP.'},
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                    )
            return Response({'detail': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        if otp.attempts >= 5:
            return Response({'detail': 'Too many attempts. Request a new OTP.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if otp.expires_at < timezone.now():
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            return Response({'detail': 'OTP expired. Request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        otp.is_verified = True
        otp.is_used = True
        otp.save(update_fields=['is_verified', 'is_used'])

        # Activate user if this was registration OTP
        if otp.user and purpose == OTPVerification.Purpose.EMAIL_REGISTER:
            otp.user.email_verified = True
            otp.user.is_active = True
            otp.user.save(update_fields=['email_verified', 'is_active'])
            log_audit(request, otp.user, UserAuditLog.Action.OTP_VERIFY, {'purpose': purpose})
            return Response({
                'message': 'Email verified. Account activated. You can now log in.',
                'activated': True,
            })

        if otp.user and purpose == OTPVerification.Purpose.MOBILE_VERIFY:
            otp.user.mobile_verified = True
            otp.user.save(update_fields=['mobile_verified'])
            log_audit(request, otp.user, UserAuditLog.Action.OTP_VERIFY, {'purpose': purpose})
            return Response({'message': 'Mobile number verified.'})

        if purpose == OTPVerification.Purpose.PASSWORD_RESET:
            return Response({
                'message': 'OTP verified. You can now reset your password.',
                'verified': True,
                'token': str(otp.id),
            })

        return Response({'message': 'OTP verified.', 'verified': True})


class LoginView(TokenObtainPairView):
    """JWT login using email + password."""
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            email = request.data.get('email') or request.data.get('username')
            try:
                user = User.objects.get(email__iexact=email)
                log_audit(request, user, UserAuditLog.Action.LOGIN)
            except User.DoesNotExist:
                pass
        else:
            email = request.data.get('email') or request.data.get('username')
            if email:
                try:
                    user = User.objects.get(email__iexact=email)
                    log_audit(request, user, UserAuditLog.Action.LOGIN_FAILED)
                except User.DoesNotExist:
                    pass
        return response


class LogoutView(APIView):
    """Logout by blacklisting the refresh token."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh = request.data.get('refresh')
            if not refresh:
                return Response({'detail': 'Refresh token required.'}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh)
            token.blacklist()
            log_audit(request, request.user, UserAuditLog.Action.LOGOUT)
            return Response({'message': 'Logged out.'})
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    """Get or update own profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_audit(request, request.user, UserAuditLog.Action.PROFILE_UPDATE)
        return Response(UserSerializer(request.user).data)


class PasswordChangeView(APIView):
    """Change password for authenticated user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        log_audit(request, request.user, UserAuditLog.Action.PASSWORD_CHANGE)
        return Response({'message': 'Password changed successfully.'})


class PasswordResetRequestView(APIView):
    """Request password reset OTP."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'message': 'If the email exists, an OTP has been sent.'})

        OTPVerification.objects.filter(
            email=email, purpose=OTPVerification.Purpose.PASSWORD_RESET, is_used=False
        ).update(is_used=True)

        otp = OTPVerification.objects.create(
            user=user,
            email=email,
            code=generate_otp(settings.OTP_LENGTH),
            purpose=OTPVerification.Purpose.PASSWORD_RESET,
            expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
        )
        send_otp_email(email, otp.code, otp.purpose)
        log_audit(request, user, UserAuditLog.Action.OTP_REQUEST, {'purpose': 'password_reset'})
        return Response({'message': 'If the email exists, an OTP has been sent.'})


class PasswordResetConfirmView(APIView):
    """Confirm password reset with OTP."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        otp = OTPVerification.objects.filter(
            email__iexact=data['email'],
            code=data['code'],
            purpose=OTPVerification.Purpose.PASSWORD_RESET,
            is_used=False,
            is_verified=True,
        ).order_by('-created_at').first()

        if not otp or otp.expires_at < timezone.now():
            return Response({'detail': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=data['email'])
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(data['new_password'])
        user.save()
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        log_audit(request, user, UserAuditLog.Action.PASSWORD_RESET)
        return Response({'message': 'Password reset successful. You can now log in.'})


class PublicUserView(APIView):
    """Public view of a user (e.g., seller info on product page).
    BUG-003 fix: banned and suspended users are hidden from public view.
    """

    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(
            User, pk=user_id, is_active=True, is_banned=False,
        )
        serializer = UserPublicSerializer(user)
        return Response(serializer.data)
