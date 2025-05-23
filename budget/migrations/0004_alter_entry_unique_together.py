# Generated by Django 5.2 on 2025-04-28 01:30

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0003_alter_category_name_alter_entry_category'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='entry',
            unique_together={('user', 'title', 'date', 'category')},
        ),
    ]
