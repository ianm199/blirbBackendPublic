# Generated by Django 3.0.4 on 2020-04-19 03:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0004_remove_movie_belongstocollection'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movie',
            name='imdb_id',
            field=models.CharField(blank=True, default=None, max_length=512),
        ),
    ]
