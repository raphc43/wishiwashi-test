# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customer_service', '0004_auto_20150304_0755'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customercontacttemplate',
            name='communication_type',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'E-mail'), (1, 'SMS')]),
        ),
        migrations.AlterField(
            model_name='messagetocustomer',
            name='status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Unsent'), (1, 'Sending'), (2, 'Rejected by Amazon SES'), (3, 'Sent'), (4, 'Stop attempting to send')]),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Unacknowledged'), (1, 'Acknowledged'), (2, 'Resolved'), (3, 'Unable to resolve')]),
        ),
    ]
