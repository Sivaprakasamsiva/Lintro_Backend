"""Buy requests app config."""
from django.apps import AppConfig


class BuyRequestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.buy_requests'
    verbose_name = 'Buy Requests'
