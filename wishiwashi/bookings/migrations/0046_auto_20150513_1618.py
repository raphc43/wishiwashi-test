# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid
import bookings.models


def gen_uuid(apps, schema_editor):
    orderModel = apps.get_model('bookings', 'order')
    for order in orderModel.objects.all():
        order.ticket_id = str(uuid.uuid4())[:11]
        order.save()


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0045_auto_20150513_1513'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderPickUps',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField()),
                ('count', models.PositiveSmallIntegerField()),
            ],
            options={
                'verbose_name_plural': 'Order Pickups counter',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='order',
            name='ticket_id',
            field=models.CharField(default=bookings.models.ticket_id_uuid, null=True, max_length=11),
            preserve_default=True,
        ),
        migrations.RunPython(gen_uuid),
    ]
