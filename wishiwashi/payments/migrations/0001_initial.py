# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0031_auto_20150326_0845'),
    ]

    operations = [
        migrations.CreateModel(
            name='Stripe',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('token', models.CharField(max_length=255)),
                ('amount', models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)])),
                ('refund_amount', models.FloatField(default=0.0, null=True, blank=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('cvv2_code_check_passed', models.BooleanField(default=False)),
                ('postcode_check_passed', models.BooleanField(default=False)),
                ('authorisation_status', models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Yet to attempt authorisation'), (1, b'Authorising'), (2, b'Failed to authorise'), (3, b'Successfully authorised')])),
                ('last_authorised_charge_time', models.DateTimeField(null=True, blank=True)),
                ('successful_authorised_charge_time', models.DateTimeField(null=True, blank=True)),
                ('card_charged_status', models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Not charged'), (1, b'Charging'), (2, b'Failed to charge'), (3, b'Successfully Charged')])),
                ('last_charged_event_time', models.DateTimeField(null=True, blank=True)),
                ('successful_charged_time', models.DateTimeField(null=True, blank=True)),
                ('charge_back_status', models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Not charged back'), (1, b'Charged back'), (2, b'Dispute resolved in our favour'), (3, b'Dispute resolved in their favour')])),
                ('charge_back_time', models.DateTimeField(null=True, blank=True)),
                ('charge_back_last_event_time', models.DateTimeField(null=True, blank=True)),
                ('refund_status', models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Not refunded'), (1, b'Refunding'), (2, b'Full Refund'), (3, b'Partial Refund'), (4, b'Failed to refund')])),
                ('refund_successful_time', models.DateTimeField(null=True, blank=True)),
                ('last_refund_event_time', models.DateTimeField(null=True, blank=True)),
                ('order', models.ForeignKey(to='bookings.Order')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
