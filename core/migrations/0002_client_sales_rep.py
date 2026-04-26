from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='sales_rep',
            field=models.CharField(blank=True, max_length=100, verbose_name='担当営業'),
        ),
    ]
