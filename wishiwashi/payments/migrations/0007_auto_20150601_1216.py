# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0006_auto_20150429_1824'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stripe',
            name='amount',
            field=models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='stripe',
            name='refund_amount',
            field=models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2),
        ),
    ]
