# Generated by Django 2.2 on 2021-02-21 22:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0054_auto_20210215_2037'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movie',
            name='tmdbID',
            field=models.IntegerField(blank=True, db_index=True, default=None, unique=True),
        ),
    ]
