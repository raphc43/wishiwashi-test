# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('faq', '0003_auto_20150225_1039'),
    ]

    operations = [
        migrations.AlterField(
            model_name='faqcatagory',
            name='order_priority',
            field=models.FloatField(default=1.0, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='questionanswer',
            name='order_priority',
            field=models.FloatField(default=1.0, db_index=True),
            preserve_default=True,
        ),
    ]
