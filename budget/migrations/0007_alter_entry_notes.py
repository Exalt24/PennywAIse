# Generated by Django 4.2.20 on 2025-05-03 08:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0006_emailverificationtoken'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='notes',
            field=models.TextField(blank=True, max_length=80),
        ),
    ]
