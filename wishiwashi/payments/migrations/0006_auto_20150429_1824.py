# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0005_stripe_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stripe',
            name='description',
            field=models.TextField(null=True, verbose_name=b'Error message', blank=True),
            preserve_default=True,
        ),
    ]
