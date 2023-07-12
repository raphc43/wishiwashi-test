# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FAQCatagory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField()),
                ('order_priority', models.FloatField(default=1.0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='QuestionAnswer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order_priority', models.FloatField(default=1.0)),
                ('slug', models.CharField(max_length=75)),
                ('question', models.TextField(help_text=b'This is RST-formatted')),
                ('answer', models.TextField(help_text=b'This is RST-formatted')),
                ('category', models.ForeignKey(to='faq.FAQCatagory')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
