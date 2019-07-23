# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-18 02:55

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("crashstats", "0011_1506907_productversion")]

    operations = [
        migrations.AddField(
            model_name="productversion",
            name="major_version",
            field=models.IntegerField(
                default=0,
                help_text=b'major version of this version; for example "63.0b4" would be 63',
            ),
            preserve_default=False,
        )
    ]
