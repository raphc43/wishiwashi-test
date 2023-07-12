# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0006_auto_20150213_1207'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderstats',
            name='accepted_business_last_24_hours',
        ),
    ]
