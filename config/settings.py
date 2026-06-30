"""
Django settings for Lintro Marketplace.
"""
import os
import environ
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
)

SECRET_KEY = env('SECRET_KEY', default='dev-insecure-secret-key-change-in-production')
DEBUG = env('DEBUG', default=True)

# FIXED: Hardcode ALLOWED_HOSTS for Render
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '*.onrender.com',
    '.vercel.app',
    'sivaprakasamlintofrontend.vercel.app',
    'lintro-backend.onrender.com',
]
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='dev-insecure-secret-key-change-in-production')
DEBUG = env('DEBUG', default=True)


# Applications
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'allauth',
    'allauth.account',
    'axes',
    'django_filters',
    'django_celery_beat',
    'django_celery_results',
    'cloudinary',
    'cloudinary_storage',
    # Local apps
    'apps.users',
    'apps.verification',
    'apps.categories',
    'apps.products',
    'apps.buy_requests',
    'apps.inquiries',
    'apps.chat',
    'apps.notifications',
    'apps.complaints',
    'apps.system_config',
    'apps.admin_dashboard',
]

SITE_ID = 1

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_UNIQUE_EMAIL = True


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'apps.users.middleware.UserActivityMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DATABASES = {
    'default': env.db_url('DATABASE_URL', default='sqlite:///db.sqlite3')
}

# Auth
AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-in'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# Media - use Cloudinary in production, local filesystem in development.
# BUG-004 fix: explicitly set DEFAULT_FILE_STORAGE in both branches so behavior
# does not depend on cloudinary_storage's app-ready side effect.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

if env('CLOUDINARY_CLOUD_NAME', default=''):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME'),
        'API_KEY': env('CLOUDINARY_API_KEY'),
        'API_SECRET': env('CLOUDINARY_API_SECRET'),
    }
    CLOUDINARY = {
        'cloud_name': env('CLOUDINARY_CLOUD_NAME'),
        'api_key': env('CLOUDINARY_API_KEY'),
        'api_secret': env('CLOUDINARY_API_SECRET'),
    }
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/min',
        'user': '240/min',
        'otp': '3/hour',
        'register': '3/hour',
        'login': '5/hour',
    },
}

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env.int('JWT_ACCESS_LIFETIME_MINUTES', 60)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_LIFETIME_DAYS', 7)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:5173', 'http://127.0.0.1:5173', 'http://10.218.122.44:5173'],
)
CORS_ALLOW_CREDENTIALS = True

# BUG-016 fix: CSRF trusted origins for production (Django admin, session auth)
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=['http://localhost:5173', 'http://127.0.0.1:5173'],
)

# Axes - brute force protection
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_PARAMETERS = ['ip_address', 'username']
AXES_USERNAME_FORM_FIELD = 'email'

# Security
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', True)
    CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', True)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CSP
SECURE_CONTENT_TYPE_NOSNIFF = True
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", 'https://fonts.googleapis.com')
CSP_SCRIPT_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", 'data:', 'https://res.cloudinary.com')
CSP_FONT_SRC = ("'self'", 'https://fonts.gstatic.com')
CSP_CONNECT_SRC = ("'self'", 'https://api.cloudinary.com')

# Email
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@Lintro.in')

# Celery
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Beat schedule
from config.celerybeat_schedule import BEAT_SCHEDULE  # noqa: E402
CELERY_BEAT_SCHEDULE = BEAT_SCHEDULE

# OTP
OTP_LENGTH = env.int('OTP_LENGTH', 6)
OTP_EXPIRY_MINUTES = env.int('OTP_EXPIRY_MINUTES', 10)

# Twilio (optional)
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = env('TWILIO_PHONE_NUMBER', default='')

# Frontend
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:5173')

# System Defaults
DEFAULT_LISTING_EXPIRY_DAYS = env.int('DEFAULT_LISTING_EXPIRY_DAYS', 30)
DEFAULT_MAX_IMAGES = env.int('DEFAULT_MAX_IMAGES', 5)
DEFAULT_24HR_ACTION_HOURS = env.int('DEFAULT_24HR_ACTION_HOURS', 24)
DEFAULT_7DAY_CLEANUP_DAYS = env.int('DEFAULT_7DAY_CLEANUP_DAYS', 7)

# Rate limits (used by @ratelimit decorators in apps/users/views.py)
RATE_LIMIT_LOGIN = env('RATE_LIMIT_LOGIN', default='5/h')
RATE_LIMIT_REGISTER = env('RATE_LIMIT_REGISTER', default='3/h')
RATE_LIMIT_OTP = env('RATE_LIMIT_OTP', default='3/h')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Image upload limits
MAX_IMAGE_UPLOAD_MB = 8
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
MAX_PRODUCT_IMAGES = 5
MIN_PRODUCT_IMAGES = 1
