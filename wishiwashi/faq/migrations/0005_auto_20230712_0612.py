# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('faq', '0004_auto_20150304_0755'),
    ]

    operations = [
        migrations.AlterField(
            model_name='questionanswer',
            name='answer',
            field=models.TextField(help_text='This is RST-formatted'),
        ),
        migrations.AlterField(
            model_name='questionanswer',
            name='question',
            field=models.TextField(help_text='This is RST-formatted'),
        ),
    ]
