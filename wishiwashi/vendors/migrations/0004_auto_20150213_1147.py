# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0003_issuetype_orderissue'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderissue',
            name='issue',
            field=models.ForeignKey(to='vendors.IssueType', null=True),
            preserve_default=True,
        ),
    ]
