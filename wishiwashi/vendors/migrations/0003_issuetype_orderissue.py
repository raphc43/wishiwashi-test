# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bookings', '0011_item_vendor_friendly_name'),
        ('vendors', '0002_ordersawaitingrenderingandsending'),
    ]

    operations = [
        migrations.CreateModel(
            name='IssueType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Contact Details'), (1, b'Pick-up/Drop-off details'), (2, b'Item(s)')])),
                ('description', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OrderIssue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('is_other_issue', models.BooleanField(default=False)),
                ('other_issue_details', models.TextField(default=b'')),
                ('status', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Raised'), (1, b'Acknowledged by Customer Service'), (2, b'Resolved')])),
                ('issue', models.ForeignKey(to='vendors.IssueType')),
                ('issue_raised_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(to='bookings.Order')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
