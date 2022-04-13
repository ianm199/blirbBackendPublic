# Generated by Django 3.0.4 on 2020-04-30 21:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('catalogTemp', '0015_auto_20200428_1520'),
    ]

    operations = [
        
        migrations.CreateModel(
            name='UserNotifications',
            fields=[
                ('notificationID', models.AutoField(primary_key=True, serialize=False)),
                ('notificationDescription', models.TextField(default=None, max_length=8192)),
                ('notificationSeen', models.BooleanField(default=False)),
                ('groupRecID', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='catalogTemp.MovieRecommendationWithinGroup')),
                ('userID', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]