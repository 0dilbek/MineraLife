from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_replace_payment_method_with_amount_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="price",
            field=models.DecimalField(
                decimal_places=2,
                default=19000.0,
                help_text="Bir dona uchun narx",
                max_digits=10,
            ),
        ),
    ]
