# Generated by Django 3.0.4 on 2020-06-26 01:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0043_book'),
    ]

    operations = [
        migrations.AddField(
            model_name='movierecommendation',
            name='bookID',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='book', to='catalogTemp.Book'),
        ),
    ]
