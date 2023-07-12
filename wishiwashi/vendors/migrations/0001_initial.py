# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OrderStats',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('business_last_24_hours', models.FloatField(default=0.0)),
                ('avg_delta_to_acceptance', models.FloatField(default=0.0)),
                ('accepted_business_last_24_hours', models.FloatField(default=0.0)),
                ('other_vendors_viewing', models.IntegerField(default=0)),
                ('top_out_code_percentage', models.FloatField(default=0.0)),
                ('top_out_code', models.CharField(default=b'', max_length=4)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
