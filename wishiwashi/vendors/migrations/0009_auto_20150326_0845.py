# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0008_auto_20150304_0755'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='issuetype',
            options={'verbose_name_plural': 'Types of Issues'},
        ),
        migrations.AlterModelOptions(
            name='orderissue',
            options={'verbose_name_plural': 'Vendor Order Issues'},
        ),
    ]
