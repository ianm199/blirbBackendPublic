# Generated by Django 3.0.4 on 2020-06-08 00:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0035_groupchatpictures'),
    ]

    operations = [
        migrations.AddField(
            model_name='userrankings',
            name='ordered',
            field=models.BooleanField(default=False),
        ),
    ]