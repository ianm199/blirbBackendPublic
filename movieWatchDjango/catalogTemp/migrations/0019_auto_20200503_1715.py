# Generated by Django 3.0.4 on 2020-05-03 21:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0018_auto_20200501_1952'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movie',
            name='tmdbID',
            field=models.IntegerField(blank=True, default=None, unique=True),
        ),
    ]