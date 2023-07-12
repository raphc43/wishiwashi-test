# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0023_pickuporderreminder'),
    ]

    operations = [
        migrations.CreateModel(
            name='DropoffOrderReminder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('order', models.ForeignKey(to='bookings.Order')),
            ],
            options={
                'verbose_name_plural': 'Drop off order reminders',
            },
            bases=(models.Model,),
        ),
    ]
