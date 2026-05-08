from django import forms
from django.contrib.auth.models import User
from .models import Client, Partner, Worker, WorkRecord, CompanySettings, Invoice, SalesRep, UserProfile


def bootstrap_fields(form):
    for name, field in form.fields.items():
        w = field.widget
        if isinstance(w, forms.Select):
            w.attrs.setdefault('class', 'form-select')
        elif isinstance(w, forms.Textarea):
            w.attrs.setdefault('class', 'form-control')
            w.attrs.setdefault('rows', 3)
        elif isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault('class', 'form-check-input')
        else:
            w.attrs.setdefault('class', 'form-control')


class SalesRepForm(forms.ModelForm):
    class Meta:
        model = SalesRep
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrap_fields(self)


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'store_name', 'contact_name', 'email', 'daily_rate',
                  'sales_rep', 'payment_terms', 'invoice_method']

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['sales_rep'].queryset = SalesRep.objects.filter(company=company)
        bootstrap_fields(self)
        self.fields['daily_rate'].widget.attrs['min'] = '0'


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = ['name', 'contact_name', 'bank_name', 'branch_name',
                  'account_type', 'account_number', 'account_holder']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrap_fields(self)


class WorkerForm(forms.ModelForm):
    class Meta:
        model = Worker
        fields = ['name', 'partner', 'daily_rate', 'notes']

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['partner'].queryset = Partner.objects.filter(company=company)
        bootstrap_fields(self)
        self.fields['daily_rate'].widget.attrs['min'] = '0'


MONTH_CHOICES = [(i, f'{i}月') for i in range(1, 13)]
YEAR_CHOICES = [(y, f'{y}年') for y in range(2024, 2030)]


class WorkRecordForm(forms.ModelForm):
    target_year = forms.ChoiceField(choices=YEAR_CHOICES, label='対象年')
    target_month = forms.ChoiceField(choices=MONTH_CHOICES, label='対象月')

    class Meta:
        model = WorkRecord
        fields = ['target_year', 'target_month', 'client', 'store_name',
                  'worker', 'days_worked', 'transport_cost', 'memo']

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['client'].queryset = Client.objects.filter(company=company)
            self.fields['worker'].queryset = Worker.objects.filter(
                company=company
            ).select_related('partner')
        bootstrap_fields(self)
        self.fields['store_name'].widget.attrs['readonly'] = True
        self.fields['store_name'].required = False
        self.fields['days_worked'].widget.attrs.update({'min': '0', 'step': '0.5'})
        self.fields['transport_cost'].widget.attrs['min'] = '0'


class WorkRecordUpdateForm(WorkRecordForm):
    class Meta(WorkRecordForm.Meta):
        fields = WorkRecordForm.Meta.fields + ['status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['store_name'].widget.attrs.pop('readonly', None)


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['invoice_number', 'client', 'target_year', 'target_month',
                  'issue_date', 'due_date', 'tax_rate', 'notes', 'status']
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['client'].queryset = Client.objects.filter(company=company)
        self.fields['target_year'] = forms.ChoiceField(
            choices=YEAR_CHOICES, label='対象年', initial=2026
        )
        self.fields['target_month'] = forms.ChoiceField(
            choices=MONTH_CHOICES, label='対象月'
        )
        bootstrap_fields(self)
        self.fields['tax_rate'].widget.attrs.update({'min': '0', 'max': '30'})


class UserCreateForm(forms.Form):
    username = forms.CharField(max_length=150, label='ユーザー名')
    password = forms.CharField(
        widget=forms.PasswordInput(), label='パスワード',
        min_length=8, help_text='8文字以上'
    )
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, label='権限')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrap_fields(self)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('このユーザー名は既に使用されています。')
        return username


class UserUpdateForm(forms.Form):
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, label='権限')
    password = forms.CharField(
        widget=forms.PasswordInput(), label='新しいパスワード',
        required=False, help_text='変更する場合のみ入力'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrap_fields(self)


class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = CompanySettings
        exclude = ['company']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bootstrap_fields(self)
