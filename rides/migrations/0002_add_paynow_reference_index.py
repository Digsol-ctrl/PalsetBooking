from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rides", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["paynow_reference"], name="rides_payment_paynow_ref_idx"),
        ),
    ]
