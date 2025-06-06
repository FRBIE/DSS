from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('mediCore', '0003_alter_archive_options_alter_archivecase_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datatable',
            name='check_time',
            field=models.DateField(help_text='检查时间'),
        ),
    ]
