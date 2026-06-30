# BUG-008 fix: add index on BuyRequest(product, -created_at) for efficient
# "list buy requests on a product, newest first" queries.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('buy_requests', '0002_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='buyrequest',
            index=models.Index(
                fields=['product', '-created_at'],
                name='buy_request_product_created_idx',
            ),
        ),
    ]
