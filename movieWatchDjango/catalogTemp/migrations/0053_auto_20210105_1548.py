# Generated by Django 2.2 on 2021-01-05 20:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('catalogTemp', '0052_auto_20210105_1515'),
    ]

    operations = [

        migrations.AddField(
            model_name='tvshow',
            name='homepage_link',
            field=models.CharField(blank=True, default=None, max_length=2048),
        )
    ]
