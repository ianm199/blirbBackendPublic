# Generated by Django 3.0.4 on 2020-04-23 00:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0009_userprofilepictures'),
    ]

    operations = [
        migrations.AddField(
            model_name='movie',
            name='posterS3Key',
            field=models.CharField(blank=True, default='', max_length=2048),
        ),
    ]