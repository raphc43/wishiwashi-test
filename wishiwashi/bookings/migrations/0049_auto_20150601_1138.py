# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0048_auto_20150515_1115'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='price',
            field=models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='itemandquantity',
            name='price',
            field=models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='order',
            name='price_excluding_vat_charge',
            field=models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='order',
            name='total_price_of_order',
            field=models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='order',
            name='transportation_charge',
            field=models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='order',
            name='vat_charge',
            field=models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2),
        ),
    ]
