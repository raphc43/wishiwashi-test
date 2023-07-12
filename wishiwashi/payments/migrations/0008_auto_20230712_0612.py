# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0007_auto_20150601_1216'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stripe',
            name='authorisation_status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Yet to attempt authorisation'), (1, 'Authorising'), (2, 'Failed to authorise'), (3, 'Successfully authorised')]),
        ),
        migrations.AlterField(
            model_name='stripe',
            name='card_charged_status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Not charged'), (1, 'Charging'), (2, 'Failed to charge'), (3, 'Successfully Charged')]),
        ),
        migrations.AlterField(
            model_name='stripe',
            name='charge_back_status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Not charged back'), (1, 'Charged back'), (2, 'Dispute resolved in our favour'), (3, 'Dispute resolved in their favour')]),
        ),
        migrations.AlterField(
            model_name='stripe',
            name='description',
            field=models.TextField(verbose_name='Error message', blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='stripe',
            name='refund_status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Not refunded'), (1, 'Refunding'), (2, 'Full Refund'), (3, 'Partial Refund'), (4, 'Failed to refund')]),
        ),
    ]
