# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-09 21:11

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("crashstats", "0005_1463121-signature-data-migration")]

    operations = [
        migrations.CreateModel(
            name="BugAssociation",
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
                ("bug_id", models.IntegerField(help_text=b"Bugzilla bug id")),
                (
                    "signature",
                    models.TextField(help_text=b"Socorro-style crash report signature"),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="bugassociation", unique_together=set([("bug_id", "signature")])
        ),
    ]
