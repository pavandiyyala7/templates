# Generated by Django 5.0.4 on 2024-05-23 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0002_shift'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutoShift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('grace_period_before_start_time', models.DurationField()),
                ('grace_period_after_start_time', models.DurationField()),
                ('grace_period_before_end_time', models.DurationField()),
                ('grace_period_after_end_time', models.DurationField()),
                ('overtime_threshold', models.DurationField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'auto_shift',
            },
        ),
    ]
