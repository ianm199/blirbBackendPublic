# Generated by Django 3.0.4 on 2020-07-11 04:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0049_podcastepisode'),
    ]

    operations = [
        migrations.AddField(
            model_name='podcastepisode',
            name='podcastID',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='catalogTemp.Podcast'),
        ),
    ]