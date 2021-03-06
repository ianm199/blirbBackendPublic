# Generated by Django 3.0.4 on 2020-04-19 19:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0005_auto_20200418_2354'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='movie',
            options={'ordering': ['popularity']},
        ),
        migrations.AlterField(
            model_name='movie',
            name='popularity',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=10, default=0.0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='movierecommendation',
            name='createdAt',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='movierecommendationwithingroup',
            name='createdAt',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
