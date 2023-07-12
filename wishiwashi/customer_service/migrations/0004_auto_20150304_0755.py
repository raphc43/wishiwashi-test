# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customer_service', '0003_auto_20150213_1135'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customercontacttemplate',
            name='communication_type',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'E-mail'), (1, b'SMS')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='messagetocustomer',
            name='status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Unsent'), (1, b'Sending'), (2, b'Rejected by Amazon SES'), (3, b'Sent'), (4, b'Stop attempting to send')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Unacknowledged'), (1, b'Acknowledged'), (2, b'Resolved'), (3, b'Unable to resolve')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='mobile_number',
            field=models.CharField(max_length=14, db_index=True),
            preserve_default=True,
        ),
    ]
