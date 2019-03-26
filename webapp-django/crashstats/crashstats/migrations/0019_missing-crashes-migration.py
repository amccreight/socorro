# Generated by Django 2.1.7 on 2019-03-26 18:15

"""Migrate data from MissingProcessedCrashes to MissingProcessedCrash."""

from django.db import migrations


def copy_data(apps, schema_editor):
    """Copy data from MissingProcessedCrashes to MissingProcessedCrash."""
    MissingProcessedCrashes = apps.get_model('crashstats', 'MissingProcessedCrashes')
    MissingProcessedCrash = apps.get_model('crashstats', 'MissingProcessedCrash')

    insert_count = 0
    for obj in MissingProcessedCrashes.objects.order_by('id'):
        MissingProcessedCrash.objects.create(
            crash_id=obj.crash_id,
            is_processed=False,
            created=obj.created
        )
        insert_count += 1
    print('(inserted: %s)' % insert_count, end='')


def delete_data(apps, schema_editor):
    """Delete data in MissingProcessedCrash table."""
    MissingProcessedCrash = apps.get_model('crashstats', 'MissingProcessedCrash')
    MissingProcessedCrash.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('crashstats', '0018_missingprocessedcrash'),
    ]

    operations = [
        migrations.RunPython(copy_data, delete_data),
    ]
