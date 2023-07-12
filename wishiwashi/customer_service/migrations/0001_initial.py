# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerContactTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('communication_type', models.PositiveSmallIntegerField(default=0, choices=[(0, b'E-mail'), (1, b'SMS')])),
                ('body', models.TextField()),
                ('body_html', models.TextField()),
                ('subject', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Issue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('area_of_concern', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Contact details'), (1, b'Address details'), (2, b'Item(s)')])),
                ('description', models.TextField()),
                ('hide_issue_from_being_raised_again', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MessageToCustomer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('status', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Unsent'), (1, b'Sending'), (2, b'Rejected by Amazon SES'), (3, b'Sent'), (4, b'Stop attempting to send')])),
                ('resend_attempts', models.IntegerField(default=0)),
                ('ses_rejection_reason', models.TextField()),
                ('sent_by', models.ForeignKey(related_name='send_by', to=settings.AUTH_USER_MODEL)),
                ('sent_to', models.ForeignKey(related_name='send_to', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(to='customer_service.CustomerContactTemplate')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OrderIssue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('description_of_other_issue', models.TextField()),
                ('issue_resolved', models.BooleanField(default=False)),
                ('issue', models.ForeignKey(to='customer_service.Issue')),
                ('issue_raised_by', models.ForeignKey(to='bookings.Vendor')),
                ('item', models.ForeignKey(to='bookings.Item')),
                ('order', models.ForeignKey(to='bookings.Order')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('status', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Unacknowledged'), (1, b'Acknowledged'), (2, b'Resolved'), (3, b'Unable to resolve')])),
                ('customer_service_owners', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(to='bookings.Order')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_vendor', models.BooleanField(default=False)),
                ('is_customer_service_agent', models.BooleanField(default=False)),
                ('mobile_number', models.CharField(max_length=14)),
                ('sms_notifications_enabled', models.BooleanField(default=False)),
                ('email_notifications_enabled', models.BooleanField(default=False)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
