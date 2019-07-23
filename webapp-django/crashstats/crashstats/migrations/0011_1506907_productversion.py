# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-15 17:59

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("crashstats", "0010_1506907_product_migration")]

    operations = [
        migrations.CreateModel(
            name="ProductVersion",
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
                    "product_name",
                    models.CharField(
                        help_text=b"ProductName of product as it appears in crash reports",
                        max_length=50,
                    ),
                ),
                (
                    "release_channel",
                    models.CharField(
                        help_text=b"release channel for this version", max_length=50
                    ),
                ),
                (
                    "release_version",
                    models.CharField(
                        help_text=b"version as it appears in crash reports",
                        max_length=50,
                    ),
                ),
                (
                    "version_string",
                    models.CharField(help_text=b"actual version", max_length=50),
                ),
                (
                    "build_id",
                    models.CharField(
                        help_text=b"the build id for this version", max_length=50
                    ),
                ),
                (
                    "archive_url",
                    models.TextField(
                        blank=True,
                        help_text=b"the url on archive.mozilla.org for data on this build",
                        null=True,
                    ),
                ),
            ],
        ),
        migrations.AlterModelOptions(name="product", options={"ordering": ["sort"]}),
        migrations.AlterUniqueTogether(
            name="productversion",
            unique_together=set(
                [("product_name", "release_channel", "build_id", "version_string")]
            ),
        ),
    ]
