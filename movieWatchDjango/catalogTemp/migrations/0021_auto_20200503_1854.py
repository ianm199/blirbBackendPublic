# Generated by Django 3.0.4 on 2020-05-03 22:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalogTemp', '0020_auto_20200503_1718'),
    ]

    operations = [
        migrations.RenameField(
            model_name='castofmovies',
            old_name='order',
            new_name='orderOfCast',
        ),
    ]
