# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0053_auto_20150612_0901'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpectedBackCleanOnlyOrder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('expected_back', models.DateTimeField()),
                ('confirmed_back', models.BooleanField(default=False)),
                ('clean_only_order', models.OneToOneField(to='bookings.CleanOnlyOrder')),
            ],
            options={
                'verbose_name_plural': 'Expected back clean only orders',
            },
        ),
    ]
