# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0052_cleanonlyorder'),
        ('vendors', '0010_auto_20150601_1542'),
    ]

    operations = [
        migrations.CreateModel(
            name='CleanAndCollectPrices',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('price', models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2)),
                ('item', models.ForeignKey(to='bookings.Item')),
                ('vendor', models.ForeignKey(to='bookings.Vendor')),
            ],
        ),
        migrations.CreateModel(
            name='CleanOnlyPrices',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('price', models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2)),
                ('item', models.ForeignKey(to='bookings.Item')),
                ('vendor', models.ForeignKey(to='bookings.Vendor')),
            ],
        ),
    ]
