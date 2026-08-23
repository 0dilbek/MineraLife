import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('couriers', '0002_courierlocation'),
    ]

    operations = [
        migrations.AddField(
            model_name='courierlocation',
            name='altitude',
            field=models.FloatField(blank=True, null=True, verbose_name='Balandlik (metr)'),
        ),
        migrations.AddField(
            model_name='courierlocation',
            name='bearing',
            field=models.FloatField(blank=True, null=True, verbose_name="Yo'nalish (gradus)"),
        ),
        migrations.AddField(
            model_name='courierlocation',
            name='captured_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Qurilmada olingan vaqti'),
        ),
        migrations.AddField(
            model_name='courierlocation',
            name='is_mocked',
            field=models.BooleanField(default=False, verbose_name='Soxta joylashuv'),
        ),
        migrations.AddField(
            model_name='courierlocation',
            name='speed',
            field=models.FloatField(blank=True, null=True, verbose_name='Tezlik (m/s)'),
        ),
    ]
