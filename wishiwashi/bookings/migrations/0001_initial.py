# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import model_utils.fields
import django.utils.timezone
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AbandonedOrders',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('flat_number_house_number_building_name', models.CharField(max_length=75)),
                ('address_line_1', models.CharField(max_length=75)),
                ('address_line_2', models.CharField(max_length=75)),
                ('town_or_city', models.CharField(max_length=75)),
                ('postcode', models.CharField(max_length=7)),
                ('instructions_for_delivery', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=75)),
                ('description', models.TextField()),
                ('visible', models.BooleanField(default=False)),
                ('order_priority', models.FloatField(default=1.0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField()),
                ('price', models.FloatField(default=0.0)),
                ('image', models.TextField()),
                ('description', models.TextField()),
                ('visible', models.BooleanField(default=False)),
                ('order_priority', models.FloatField(default=1.0)),
                ('category', models.ForeignKey(to='bookings.Address')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OperatingTimeRange',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('day_of_week', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Monday'), (1, b'Tuesday'), (2, b'Wednesday'), (3, b'Thursday'), (4, b'Friday')])),
                ('start_hour', models.PositiveSmallIntegerField(validators=[django.core.validators.MaxValueValidator(24), django.core.validators.MinValueValidator(0)])),
                ('end_hour', models.PositiveSmallIntegerField(validators=[django.core.validators.MaxValueValidator(24), django.core.validators.MinValueValidator(0)])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('uuid', models.CharField(max_length=8)),
                ('total_price_of_order', models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)])),
                ('pick_up_time', models.DateTimeField()),
                ('drop_off_time', models.DateTimeField()),
                ('cvv2_code_check_passed', models.BooleanField(default=False)),
                ('postcode_check_passed', models.BooleanField(default=False)),
                ('stripe_charge_token', models.CharField(max_length=75)),
                ('card_charged_status', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Not charged'), (1, b'Charging'), (2, b'Failed to charge'), (3, b'Successfully Charged')])),
                ('last_charged_event_time', models.DateTimeField()),
                ('successful_charged_time', models.DateTimeField()),
                ('charge_back_status', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Not charged back'), (1, b'Charged back'), (2, b'Dispute resolved in our favour'), (3, b'Dispute resolved in their favour')])),
                ('charge_back_time', models.DateTimeField()),
                ('charge_back_last_event_time', models.DateTimeField()),
                ('refund_status', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Not refunded'), (1, b'Refunding'), (2, b'Refunded'), (3, b'Failed to refund')])),
                ('refund_successful_time', models.DateTimeField()),
                ('last_refund_event_time', models.DateTimeField()),
                ('order_status', models.PositiveSmallIntegerField(default=0, choices=[(0, b''), (1, b''), (2, b''), (3, b''), (4, b''), (5, b''), (6, b''), (7, b''), (8, b'')])),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OutCodeNotServed',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('out_code', models.CharField(max_length=4)),
                ('email_address', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OutCodes',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('out_code', models.CharField(unique=True, max_length=4)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('company_name', models.CharField(max_length=75)),
                ('capacity_per_hour', models.PositiveSmallIntegerField(default=0)),
                ('address', models.ForeignKey(to='bookings.Address')),
                ('catchment_area', models.ManyToManyField(to='bookings.OutCodes')),
                ('hours_of_operation', models.ManyToManyField(to='bookings.OperatingTimeRange')),
                ('staff', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Voucher',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('percentage_off', models.FloatField(default=0.0, validators=[django.core.validators.MaxValueValidator(100), django.core.validators.MinValueValidator(0)])),
                ('voucher_code', models.CharField(max_length=75)),
                ('valid_until', models.DateTimeField()),
                ('use_limit', models.PositiveIntegerField(default=0)),
                ('use_count', models.PositiveIntegerField(default=0)),
                ('issued_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='order',
            name='assigned_to_vendor',
            field=models.ForeignKey(to='bookings.Vendor'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='order',
            name='billing_address',
            field=models.ForeignKey(related_name='billing_address', to='bookings.Vendor'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='order',
            name='items',
            field=models.ManyToManyField(to='bookings.Item'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='order',
            name='pick_up_and_delivery_address',
            field=models.ForeignKey(related_name='pick_up_and_delivery', to='bookings.Address'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='order',
            name='user',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='order',
            name='voucher',
            field=models.ForeignKey(to='bookings.Voucher'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='abandonedorders',
            name='order',
            field=models.ForeignKey(to='bookings.Order'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='abandonedorders',
            name='vendor',
            field=models.ForeignKey(to='bookings.Vendor'),
            preserve_default=True,
        ),
    ]
