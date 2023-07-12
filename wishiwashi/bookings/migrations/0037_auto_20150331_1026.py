# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0036_auto_20150331_0949'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='charge_back_last_event_time',
        ),
        migrations.RemoveField(
            model_name='order',
            name='charge_back_time',
        ),
        migrations.RemoveField(
            model_name='order',
            name='last_charged_event_time',
        ),
        migrations.RemoveField(
            model_name='order',
            name='last_refund_event_time',
        ),
        migrations.RemoveField(
            model_name='order',
            name='refund_amount',
        ),
        migrations.RemoveField(
            model_name='order',
            name='refund_successful_time',
        ),
        migrations.RemoveField(
            model_name='order',
            name='successful_charged_time',
        ),
    ]
