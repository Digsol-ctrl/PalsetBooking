from django.db import migrations
from decimal import Decimal


def start_charging_hand_luggage(apps, schema_editor):
    """Turn on hand luggage charging on an existing site.

    Hand luggage shipped free, which does not hold up once a passenger arrives with
    a pile of bags they cannot actually carry. Sites that never set a fee move to
    the new allowance of 5 free items and $1.50 each after that; a site that already
    charges something is left exactly as its owner configured it.
    """
    SiteSettings = apps.get_model('rides', 'SiteSettings')
    for row in SiteSettings.objects.all():
        if not row.hand_luggage_fee or Decimal(str(row.hand_luggage_fee)) == Decimal('0'):
            row.hand_luggage_free = 5
            row.hand_luggage_fee = Decimal('1.50')
            row.save(update_fields=['hand_luggage_free', 'hand_luggage_fee'])


def keep_charging(apps, schema_editor):
    """Nothing to undo — the amounts stay editable in the dashboard."""


class Migration(migrations.Migration):

    dependencies = [
        ('rides', '0020_ridebooking_dropoff_point_detail_and_more'),
    ]

    operations = [
        migrations.RunPython(start_charging_hand_luggage, keep_charging),
    ]
