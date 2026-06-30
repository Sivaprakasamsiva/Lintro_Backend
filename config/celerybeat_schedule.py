"""
Celery beat schedule - registered via Django settings.

Schedule is also configurable through django_celery_beat database entries.
"""
from celery.schedules import crontab


BEAT_SCHEDULE = {
    'expire-buy-requests-every-15min': {
        'task': 'apps.products.tasks.expire_buy_requests',
        'schedule': crontab(minute='*/15'),
    },
    'unlist-missed-deadlines-every-15min': {
        'task': 'apps.products.tasks.unlist_products_with_missed_deadlines',
        'schedule': crontab(minute='*/15'),
    },
    'archive-old-unlisted-daily': {
        'task': 'apps.products.tasks.archive_old_unlisted_products',
        'schedule': crontab(hour=3, minute=0),
    },
    'expire-old-listings-hourly': {
        'task': 'apps.products.tasks.expire_old_listings',
        'schedule': crontab(minute=0),
    },
    'send-expiry-warnings-daily': {
        'task': 'apps.products.tasks.send_expiry_warnings',
        'schedule': crontab(hour=8, minute=0),
    },
    'send-24hr-reminders-hourly': {
        'task': 'apps.products.tasks.send_24hr_reminders',
        'schedule': crontab(minute=30),
    },
    'cleanup-old-notifications-weekly': {
        'task': 'apps.products.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
    },
    'cleanup-blacklisted-tokens-daily': {
        'task': 'apps.products.tasks.cleanup_blacklisted_tokens',
        'schedule': crontab(hour=5, minute=0),
    },
    # BUG-009 fix: cleanup old Axes brute-force attempt rows weekly.
    'cleanup-old-axes-attempts-weekly': {
        'task': 'apps.users.tasks.cleanup_old_axes_attempts',
        'schedule': crontab(hour=6, minute=0, day_of_week=0),
    },
}
