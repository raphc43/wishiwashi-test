# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0014_auto_20150611_1005'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='cleanandcollectprices',
            unique_together=set([('vendor', 'item')]),
        ),
        migrations.AlterUniqueTogether(
            name='cleanonlyprices',
            unique_together=set([('vendor', 'item')]),
        ),
    ]
