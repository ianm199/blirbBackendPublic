# Generated by Django 3.0.4 on 2020-05-03 22:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0021_auto_20200503_1854'),
    ]

    operations = [
        migrations.AlterField(
            model_name='castofmovies',
            name='movieID',
            field=models.ForeignKey(blank=True, default=None, on_delete=django.db.models.deletion.CASCADE, to='catalogTemp.Movie'),
        ),
    ]
