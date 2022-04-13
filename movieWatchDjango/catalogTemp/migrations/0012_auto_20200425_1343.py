# Generated by Django 3.0.4 on 2020-04-25 17:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0011_tvshow'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tvshow',
            old_name='backDropPath',
            new_name='backdropPath',
        ),
        migrations.AddField(
            model_name='tvshow',
            name='originCountry',
            field=models.TextField(blank=True, default='', max_length=256),
        ),
    ]
