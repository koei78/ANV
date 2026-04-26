from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_invoice'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='sales_rep',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='担当営業'),
        ),
    ]
