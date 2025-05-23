# Generated by Django 5.2 on 2025-04-27 20:11

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Budget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.DateField(help_text='First day of the month this budget applies to')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('category', models.ForeignKey(blank=True, help_text='Leave blank for a total budget', null=True, on_delete=django.db.models.deletion.CASCADE, to='budget.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-month',),
                'unique_together': {('user', 'category', 'month')},
            },
        ),
    ]
