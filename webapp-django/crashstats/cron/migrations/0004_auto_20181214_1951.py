# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-14 19:51

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("cron", "0003_auto_20181116_1432")]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="app_name",
            field=models.CharField(
                help_text="the name of the crontabber app", max_length=100, unique=True
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="depends_on",
            field=models.TextField(
                blank=True,
                help_text="comma separated list of apps this app depends on",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="error_count",
            field=models.IntegerField(
                default=0, help_text="the number of consecutive error runs"
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="first_run",
            field=models.DateTimeField(
                blank=True,
                help_text="the datetime of the first time ever run",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="last_error",
            field=models.TextField(
                blank=True, help_text="JSON blob of the last error", null=True
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="last_run",
            field=models.DateTimeField(
                blank=True,
                help_text="the datetime of the last time this was run",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="last_success",
            field=models.DateTimeField(
                blank=True,
                help_text="the datetime of the last successful run",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="next_run",
            field=models.DateTimeField(
                blank=True, help_text="the datetime of the next time to run", null=True
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="ongoing",
            field=models.DateTimeField(
                blank=True,
                help_text="the datetime this job entry was locked",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="app_name",
            field=models.CharField(
                help_text="the crontabber app this log entry is for", max_length=100
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="duration",
            field=models.FloatField(help_text="duration in seconds"),
        ),
        migrations.AlterField(
            model_name="log",
            name="exc_traceback",
            field=models.TextField(
                blank=True, help_text="the exc traceback of an error if any", null=True
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="exc_type",
            field=models.TextField(
                blank=True, help_text="the exc type of an error if any", null=True
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="exc_value",
            field=models.TextField(
                blank=True, help_text="the exc value of an error if any", null=True
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="log_time",
            field=models.DateTimeField(
                auto_now_add=True, help_text="the datetime for this entry"
            ),
        ),
        migrations.AlterField(
            model_name="log",
            name="success",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
