import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='会社名')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '会社'
        verbose_name_plural = '会社'

    def __str__(self):
        return self.name


class CompanySettings(models.Model):
    ACCOUNT_TYPE_CHOICES = [('futsu', '普通'), ('toza', '当座')]

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='settings')
    company_name = models.CharField(max_length=200, verbose_name='会社名（請求書表示用）', blank=True)
    postal_code = models.CharField(max_length=10, verbose_name='郵便番号', blank=True)
    address = models.TextField(verbose_name='住所', blank=True)
    phone = models.CharField(max_length=20, verbose_name='電話番号', blank=True)
    bank_name = models.CharField(max_length=100, verbose_name='銀行名', blank=True)
    branch_name = models.CharField(max_length=100, verbose_name='支店名', blank=True)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES, default='futsu', verbose_name='口座種別')
    account_number = models.CharField(max_length=20, verbose_name='口座番号', blank=True)
    account_holder = models.CharField(max_length=100, verbose_name='口座名義', blank=True)
    invoice_footer_notes = models.TextField(verbose_name='請求書備考', blank=True)

    class Meta:
        verbose_name = '会社設定'
        verbose_name_plural = '会社設定'

    def __str__(self):
        return f'{self.company.name} - 設定'


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin',   '管理者（全機能）'),
        ('staff',   'スタッフ（稼働・請求）'),
        ('invoice', '請求書作成のみ'),
        ('viewer',  '閲覧のみ'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff', verbose_name='権限')

    class Meta:
        verbose_name = 'ユーザープロフィール'
        verbose_name_plural = 'ユーザープロフィール'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'

    @property
    def is_admin(self):
        return self.role == 'admin'


class SalesRep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='sales_reps')
    name = models.CharField(max_length=100, verbose_name='氏名')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '担当営業'
        verbose_name_plural = '担当営業'
        ordering = ['name']

    def __str__(self):
        return self.name


class Client(models.Model):
    INVOICE_METHOD_CHOICES = [('email', 'メール'), ('mail', '郵送')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=200, verbose_name='会社名')
    store_name = models.CharField(max_length=200, verbose_name='稼働店舗名', blank=True)
    contact_name = models.CharField(max_length=100, verbose_name='担当者名', blank=True)
    email = models.EmailField(verbose_name='請求書送付先メール', blank=True)
    daily_rate = models.DecimalField(
        max_digits=10, decimal_places=0, verbose_name='受け単価（日当）',
        validators=[MinValueValidator(Decimal('0'))]
    )
    sales_rep = models.ForeignKey(
        SalesRep, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='担当営業', related_name='clients'
    )
    payment_terms = models.CharField(max_length=100, verbose_name='支払いサイト', blank=True)
    invoice_method = models.CharField(
        max_length=10, choices=INVOICE_METHOD_CHOICES, default='email',
        verbose_name='請求書送付方法'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'クライアント先'
        verbose_name_plural = 'クライアント先'
        ordering = ['name', 'store_name']

    def __str__(self):
        if self.store_name:
            return f'{self.name}（{self.store_name}）'
        return self.name


class Partner(models.Model):
    ACCOUNT_TYPE_CHOICES = [('futsu', '普通'), ('toza', '当座')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='partners')
    name = models.CharField(max_length=200, verbose_name='会社名')
    contact_name = models.CharField(max_length=100, verbose_name='担当者名', blank=True)
    bank_name = models.CharField(max_length=100, verbose_name='銀行名', blank=True)
    branch_name = models.CharField(max_length=100, verbose_name='支店名', blank=True)
    account_type = models.CharField(
        max_length=10, choices=ACCOUNT_TYPE_CHOICES, default='futsu',
        verbose_name='口座種別'
    )
    account_number = models.CharField(max_length=20, verbose_name='口座番号', blank=True)
    account_holder = models.CharField(max_length=100, verbose_name='口座名義', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'パートナー企業'
        verbose_name_plural = 'パートナー企業'
        ordering = ['name']

    def __str__(self):
        return self.name


class Worker(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='workers')
    name = models.CharField(max_length=100, verbose_name='氏名')
    partner = models.ForeignKey(
        Partner, on_delete=models.CASCADE, related_name='workers',
        verbose_name='所属パートナー企業'
    )
    daily_rate = models.DecimalField(
        max_digits=10, decimal_places=0, verbose_name='パートナー単価（日当）',
        validators=[MinValueValidator(Decimal('0'))]
    )
    notes = models.TextField(verbose_name='備考', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '稼働者'
        verbose_name_plural = '稼働者'
        ordering = ['name']

    def __str__(self):
        return f'{self.name}（{self.partner.name}）'


class WorkRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', '未対応'),
        ('early_sent', '月初請求書 送付済'),
        ('late_sent', '月末請求書 送付済'),
        ('waiting_transfer', '振込待ち'),
        ('transferred', '振込完了'),
    ]
    STATUS_BADGE = {
        'pending': 'secondary',
        'early_sent': 'info',
        'late_sent': 'primary',
        'waiting_transfer': 'warning',
        'transferred': 'success',
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='work_records')
    target_year = models.IntegerField(verbose_name='対象年')
    target_month = models.IntegerField(verbose_name='対象月')
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='work_records',
        verbose_name='クライアント先'
    )
    store_name = models.CharField(max_length=200, verbose_name='稼働店舗', blank=True)
    worker = models.ForeignKey(
        Worker, on_delete=models.CASCADE, related_name='work_records',
        verbose_name='稼働者'
    )
    days_worked = models.DecimalField(
        max_digits=5, decimal_places=1, verbose_name='出勤数',
        validators=[MinValueValidator(Decimal('0'))]
    )
    transport_cost = models.DecimalField(
        max_digits=10, decimal_places=0, default=0, verbose_name='交通費',
        validators=[MinValueValidator(Decimal('0'))]
    )
    memo = models.TextField(verbose_name='メモ', blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='ステータス'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '稼働記録'
        verbose_name_plural = '稼働記録'
        ordering = ['-target_year', '-target_month', 'client__name']

    def __str__(self):
        return f'{self.target_year}年{self.target_month}月 {self.client.name} {self.worker.name}'

    @property
    def target_month_display(self):
        return f'{self.target_year}年{self.target_month}月'

    @property
    def early_invoice_amount(self):
        return self.days_worked * self.client.daily_rate

    @property
    def late_invoice_amount(self):
        return self.days_worked * self.client.daily_rate + self.transport_cost

    @property
    def partner_payment(self):
        return self.days_worked * self.worker.daily_rate + self.transport_cost

    @property
    def gross_profit_early(self):
        return self.early_invoice_amount - self.partner_payment

    @property
    def gross_profit_late(self):
        return self.late_invoice_amount - self.partner_payment

    @property
    def status_badge(self):
        return self.STATUS_BADGE.get(self.status, 'secondary')

    def get_next_status(self):
        statuses = [s[0] for s in self.STATUS_CHOICES]
        idx = statuses.index(self.status)
        if idx < len(statuses) - 1:
            return statuses[idx + 1]
        return None

    def get_next_status_label(self):
        next_s = self.get_next_status()
        if next_s:
            return dict(self.STATUS_CHOICES)[next_s]
        return None


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', '下書き'),
        ('issued', '発行済'),
        ('paid', '入金済'),
    ]
    STATUS_BADGE = {
        'draft': 'secondary',
        'issued': 'primary',
        'paid': 'success',
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, verbose_name='請求書番号')
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='invoices',
        verbose_name='クライアント'
    )
    issue_date = models.DateField(verbose_name='発行日')
    due_date = models.DateField(verbose_name='支払期限', blank=True, null=True)
    target_year = models.IntegerField(verbose_name='対象年')
    target_month = models.IntegerField(verbose_name='対象月')
    tax_rate = models.IntegerField(default=10, verbose_name='消費税率(%)')
    notes = models.TextField(blank=True, verbose_name='備考')
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name='ステータス'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '請求書'
        verbose_name_plural = '請求書'
        ordering = ['-issue_date', '-created_at']
        unique_together = [['company', 'invoice_number']]

    def __str__(self):
        return f'{self.invoice_number} - {self.client.name}'

    @property
    def target_month_display(self):
        return f'{self.target_year}年{self.target_month}月'

    def get_work_records(self):
        return WorkRecord.objects.filter(
            company=self.company,
            client=self.client,
            target_year=self.target_year,
            target_month=self.target_month,
        ).select_related('worker')

    @property
    def subtotal(self):
        return sum(r.late_invoice_amount for r in self.get_work_records())

    @property
    def tax_amount(self):
        from decimal import ROUND_HALF_UP
        return (self.subtotal * Decimal(self.tax_rate) / 100).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )

    @property
    def total_amount(self):
        return self.subtotal + self.tax_amount

    @property
    def status_badge(self):
        return self.STATUS_BADGE.get(self.status, 'secondary')
