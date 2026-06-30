from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPVerification, UserAuditLog


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):

    list_display = (
        'email',
        'full_name',
        'mobile_number',
        'email_verified',
        'verified_seller',
        'is_active',
        'is_banned',
        'role',
    )

    list_filter = (
        'email_verified',
        'mobile_verified',
        'verified_seller',
        'is_active',
        'is_banned',
        'role',
    )

    search_fields = (
        'email',
        'full_name',
        'mobile_number',
        'district',
        'state',
    )

    ordering = ('-joined_date',)

    filter_horizontal = (
        'groups',
        'user_permissions',
    )

    # THIS IS THE IMPORTANT PART
    readonly_fields = (
        'joined_date',
        'last_login',
        'last_active',
    )

    fieldsets = (
        (None, {
            'fields': (
                'email',
                'password',
            )
        }),

        ('Personal', {
            'fields': (
                'full_name',
                'mobile_number',
                'whatsapp_number',
                'profile_image',
                'bio',
            )
        }),

        ('Location', {
            'fields': (
                'address',
                'district',
                'state',
                'country',
                'latitude',
                'longitude',
            )
        }),

        ('Verification', {
            'fields': (
                'email_verified',
                'mobile_verified',
                'verified_seller',
                'verified_seller_badge_date',
            )
        }),

        ('Status', {
            'fields': (
                'is_active',
                'is_suspended',
                'suspended_until',
                'is_banned',
                'role',
            )
        }),

        ('Permissions', {
            'fields': (
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),

        ('Important dates', {
            'fields': (
                'joined_date',
                'last_login',
                'last_active',
            )
        }),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'full_name',
                    'mobile_number',
                    'password1',
                    'password2',
                ),
            },
        ),
    )