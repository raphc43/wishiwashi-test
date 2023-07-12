# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0052_cleanonlyorder'),
        ('vendors', '0012_auto_20150608_1355'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderPayments',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('total_amount', models.DecimalField(default=Decimal('0.0'), max_digits=6, decimal_places=2)),
                ('order', models.OneToOneField(to='bookings.Order')),
            ],
            options={
                'verbose_name_plural': 'Payments due to Vendors',
            },
        ),
    ]
