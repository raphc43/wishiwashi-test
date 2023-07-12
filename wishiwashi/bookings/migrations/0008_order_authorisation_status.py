# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0007_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='authorisation_status',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b'Yet to attempt authorisation'), (1, b'Authorising'), (2, b'Failed to authorise'), (3, b'Successfully authorised')]),
            preserve_default=True,
        ),
    ]
