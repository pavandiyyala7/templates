# Generated by Django 5.0.7 on 2025-02-05 07:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resource', '0006_overtimeroundoffrules'),
    ]

    operations = [
        migrations.AlterField(
            model_name='overtimeroundoffrules',
            name='round_off_direction',
            field=models.CharField(choices=[('Up', 'Up'), ('Down', 'Down'), ('Nearest', 'Nearest')], default='nearest', max_length=50),
        ),
    ]
