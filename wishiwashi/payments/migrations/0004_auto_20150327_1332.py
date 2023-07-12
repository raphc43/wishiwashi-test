# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0003_stripe_ipaddress'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='stripe',
            options={'verbose_name': 'Stripe Charge', 'verbose_name_plural': 'Stripe Charges'},
        ),
    ]
