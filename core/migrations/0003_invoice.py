import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_client_sales_rep'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('invoice_number', models.CharField(max_length=50, verbose_name='請求書番号')),
                ('issue_date', models.DateField(verbose_name='発行日')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='支払期限')),
                ('target_year', models.IntegerField(verbose_name='対象年')),
                ('target_month', models.IntegerField(verbose_name='対象月')),
                ('tax_rate', models.IntegerField(default=10, verbose_name='消費税率(%)')),
                ('notes', models.TextField(blank=True, verbose_name='備考')),
                ('status', models.CharField(
                    choices=[('draft', '下書き'), ('issued', '発行済'), ('paid', '入金済')],
                    default='draft', max_length=10, verbose_name='ステータス',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invoices', to='core.company',
                )),
                ('client', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invoices', to='core.client', verbose_name='クライアント',
                )),
            ],
            options={
                'verbose_name': '請求書',
                'verbose_name_plural': '請求書',
                'ordering': ['-issue_date', '-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='invoice',
            constraint=models.UniqueConstraint(
                fields=['company', 'invoice_number'], name='unique_invoice_number_per_company'
            ),
        ),
    ]
