# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bookings', '0006_auto_20150126_1159'),
        ('vendors', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrdersAwaitingRenderingAndSending',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('render_service_job_uuid', models.CharField(max_length=16)),
                ('communicate_service_job_uuid', models.CharField(max_length=16)),
                ('pdf_url', models.CharField(max_length=255)),
                ('status', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Untouched'), (1, b'Requesting Render'), (2, b'Rendering'), (3, b'Rendered'), (4, b'Failed to render'), (5, b'Requesting sending'), (6, b'Sending'), (7, b'Sent'), (8, b'Failed to send')])),
                ('orders', models.ManyToManyField(to='bookings.Order')),
                ('recipients', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
