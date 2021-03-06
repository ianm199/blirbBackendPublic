# Generated by Django 3.0.4 on 2020-07-06 23:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0047_auto_20200706_1944'),
    ]

    operations = [
        migrations.AddField(
            model_name='rankingsitems',
            name='podcastID',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='podcast', to='catalogTemp.Podcast'),
        ),
        migrations.AlterField(
            model_name='rankingsitems',
            name='bookID',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='book', to='catalogTemp.Book'),
        ),
    ]
