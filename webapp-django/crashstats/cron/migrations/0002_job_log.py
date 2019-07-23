# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-26 19:07

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("cron", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "app_name",
                    models.CharField(
                        help_text=b"the name of the crontabber app",
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "next_run",
                    models.DateTimeField(
                        help_text=b"the datetime of the next time to run", null=True
                    ),
                ),
                (
                    "first_run",
                    models.DateTimeField(
                        help_text=b"the datetime of the first time ever run", null=True
                    ),
                ),
                (
                    "last_run",
                    models.DateTimeField(
                        help_text=b"the datetime of the last time this was run",
                        null=True,
                    ),
                ),
                (
                    "last_success",
                    models.DateTimeField(
                        help_text=b"the datetime of the last successful run", null=True
                    ),
                ),
                (
                    "error_count",
                    models.IntegerField(
                        default=0, help_text=b"the number of consecutive error runs"
                    ),
                ),
                (
                    "depends_on",
                    models.TextField(
                        help_text=b"comma separated list of apps this app depends on",
                        null=True,
                    ),
                ),
                (
                    "last_error",
                    models.TextField(
                        help_text=b"JSON blob of the last error", null=True
                    ),
                ),
                (
                    "ongoing",
                    models.DateTimeField(
                        help_text=b"the datetime this job entry was locked", null=True
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Log",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "app_name",
                    models.CharField(
                        help_text=b"the crontabber app this log entry is for",
                        max_length=100,
                    ),
                ),
                (
                    "log_time",
                    models.DateTimeField(
                        auto_now_add=True, help_text=b"the datetime for this entry"
                    ),
                ),
                ("duration", models.FloatField(help_text=b"duration in seconds")),
                ("success", models.DateTimeField(blank=True, help_text=b"", null=True)),
                (
                    "exc_type",
                    models.TextField(
                        blank=True,
                        help_text=b"the exc type of an error if any",
                        null=True,
                    ),
                ),
                (
                    "exc_value",
                    models.TextField(
                        blank=True,
                        help_text=b"the exc value of an error if any",
                        null=True,
                    ),
                ),
                (
                    "exc_traceback",
                    models.TextField(
                        blank=True,
                        help_text=b"the exc traceback of an error if any",
                        null=True,
                    ),
                ),
            ],
        ),
    ]
