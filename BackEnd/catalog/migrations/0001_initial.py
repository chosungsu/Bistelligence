# Generated by Django 4.1 on 2023-02-23 02:51

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Data',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Score', models.FloatField()),
                ('Key', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Xai',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('summary_plot', models.ImageField(upload_to='')),
                ('force_plot', models.ImageField(upload_to='')),
            ],
        ),
    ]