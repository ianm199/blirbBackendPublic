# Generated by Django 3.0.4 on 2020-04-30 22:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('catalogTemp', '0016_auto_20200430_1737'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernotifications',
            name='receiverUserID',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='receiverUserID', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='usernotifications',
            name='userID',
            field=models.ForeignKey(blank=True, default=None, on_delete=django.db.models.deletion.CASCADE, related_name='senderUserID', to=settings.AUTH_USER_MODEL),
        ),
    ]
