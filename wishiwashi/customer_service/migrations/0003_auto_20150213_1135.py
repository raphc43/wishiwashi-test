# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customer_service', '0002_remove_userprofile_is_vendor'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderissue',
            name='issue',
        ),
        migrations.DeleteModel(
            name='Issue',
        ),
        migrations.RemoveField(
            model_name='orderissue',
            name='issue_raised_by',
        ),
        migrations.RemoveField(
            model_name='orderissue',
            name='item',
        ),
        migrations.RemoveField(
            model_name='orderissue',
            name='order',
        ),
        migrations.DeleteModel(
            name='OrderIssue',
        ),
    ]
