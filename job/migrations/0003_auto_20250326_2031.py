# Generated by Django 3.1.12 on 2025-03-26 12:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0002_auto_20250326_2024'),
    ]

    operations = [
        migrations.AddField(
            model_name='sendlist',
            name='company',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='公司名称'),
        ),
        migrations.AddField(
            model_name='sendlist',
            name='company_size',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='公司规模'),
        ),
        migrations.AddField(
            model_name='sendlist',
            name='company_type',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='所属行业'),
        ),
        migrations.AddField(
            model_name='sendlist',
            name='job_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='职位名称'),
        ),
        migrations.AlterModelTable(
            name='sendlist',
            table='send_list',
        ),
    ]
