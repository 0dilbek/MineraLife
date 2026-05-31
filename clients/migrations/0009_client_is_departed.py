from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0008_remove_clientphonenumber_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="is_departed",
            field=models.BooleanField(default=False, help_text="Mijoz endi bizdan buyurtma olmayaptimi?"),
        ),
    ]
