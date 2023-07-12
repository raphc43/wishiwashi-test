# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('faq', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='questionanswer',
            name='slug',
            field=models.CharField(unique=True, max_length=75),
            preserve_default=True,
        ),
    ]
