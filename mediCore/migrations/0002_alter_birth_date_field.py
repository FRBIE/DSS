from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('mediCore', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='identity',
            name='birth_date',
            field=models.DateField(verbose_name='出生年月日'),
        ),
        migrations.AlterField(
            model_name='case',
            name='birth_date',
            field=models.DateField(verbose_name='出生年月日'),
        ),
    ]
