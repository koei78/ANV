import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_fix_client_sales_rep_column'),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesRep',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='氏名')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sales_reps', to='core.company')),
            ],
            options={'verbose_name': '担当営業', 'verbose_name_plural': '担当営業', 'ordering': ['name']},
        ),
        migrations.RemoveField(
            model_name='client',
            name='sales_rep',
        ),
        migrations.AddField(
            model_name='client',
            name='sales_rep',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='clients', to='core.salesrep', verbose_name='担当営業'),
        ),
    ]
