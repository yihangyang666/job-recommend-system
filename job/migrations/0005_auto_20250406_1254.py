# Generated by Django 3.1.12 on 2025-04-06 04:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0004_auto_20250331_1603'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sendlist',
            options={'ordering': ['-created_at'], 'verbose_name': '投递记录', 'verbose_name_plural': '投递记录'},
        ),
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
        migrations.AlterField(
            model_name='sendlist',
            name='job_id',
            field=models.CharField(max_length=255, verbose_name='职位ID'),
        ),
    ]
