# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0005_orderissue_item'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderissue',
            name='issue',
            field=models.ForeignKey(default=3, to='vendors.IssueType'),
            preserve_default=False,
        ),
    ]
