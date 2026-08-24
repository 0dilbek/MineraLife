from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0012_set_order_default_price_to_19000'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='is_debt',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Buyurtma yopilmagan qarz sifatida belgilanganmi?',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='debt_marked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='debt_marked_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='marked_debt_orders',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='debt_closed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='debt_closed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='closed_debt_orders',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
