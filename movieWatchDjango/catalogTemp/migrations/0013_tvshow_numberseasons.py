# Generated by Django 3.0.4 on 2020-04-25 17:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0012_auto_20200425_1343'),
    ]

    operations = [
        migrations.AddField(
            model_name='tvshow',
            name='numberSeasons',
            field=models.IntegerField(blank=True, default=None),
        ),
    ]
