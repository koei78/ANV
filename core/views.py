import csv
import json
from decimal import Decimal
from datetime import date, datetime
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages

from .models import Company, CompanySettings, Client, Partner, Worker, WorkRecord, Invoice, SalesRep, UserProfile
from .forms import (ClientForm, PartnerForm, WorkerForm, SalesRepForm,
                    WorkRecordForm, WorkRecordUpdateForm, CompanySettingsForm, InvoiceForm,
                    UserCreateForm, UserUpdateForm)

# 権限グループ
ROLES_STAFF_UP = {'admin', 'staff'}
ROLES_INVOICE_UP = {'admin', 'staff', 'invoice'}


class CompanyMixin:
    def get_company(self):
        return self.request.user.profile.company

    def get_queryset(self):
        return super().get_queryset().filter(company=self.get_company())

    def form_valid(self, form):
        form.instance.company = self.get_company()
        return super().form_valid(form)


class AdminRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.profile.is_admin:
            messages.error(request, '管理者権限が必要です。')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


class RoleRequiredMixin:
    """allowed_roles に含まれるロールのみアクセス可"""
    allowed_roles: set = set()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        role = getattr(getattr(request.user, 'profile', None), 'role', '')
        if self.allowed_roles and role not in self.allowed_roles:
            messages.error(request, 'この操作を行う権限がありません。')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


# ── Dashboard ──────────────────────────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = self.request.user.profile.company
        now = datetime.now()

        current_records = list(
            WorkRecord.objects.filter(
                company=company, target_year=now.year, target_month=now.month
            ).select_related('client', 'client__sales_rep', 'worker')
        )

        total_early = sum(r.early_invoice_amount for r in current_records)
        total_late = sum(r.late_invoice_amount for r in current_records)
        total_gross = sum(r.gross_profit_early for r in current_records)

        status_counts = {s: 0 for s, _ in WorkRecord.STATUS_CHOICES}
        for r in WorkRecord.objects.filter(company=company).values('status'):
            status_counts[r['status']] = status_counts.get(r['status'], 0) + 1

        chart_labels, chart_data = [], []
        for i in range(5, -1, -1):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            recs = list(
                WorkRecord.objects.filter(
                    company=company, target_year=y, target_month=m
                ).select_related('client', 'worker')
            )
            chart_labels.append(f'{y}/{m:02d}')
            chart_data.append(float(sum(r.gross_profit_early for r in recs)))

        client_profits = {}
        for r in current_records:
            key = r.client.name
            client_profits[key] = client_profits.get(key, 0) + float(r.gross_profit_early)
        client_ranking = sorted(client_profits.items(), key=lambda x: x[1], reverse=True)[:5]

        # 担当営業別集計
        rep_map = {}
        for r in current_records:
            rep = r.client.sales_rep
            key = str(rep.pk) if rep else '__unset__'
            if key not in rep_map:
                rep_map[key] = {
                    'name': rep.name if rep else '（未設定）',
                    'invoice': Decimal('0'),
                    'gross': Decimal('0'),
                    'count': 0,
                }
            rep_map[key]['invoice'] += r.late_invoice_amount
            rep_map[key]['gross'] += r.gross_profit_late
            rep_map[key]['count'] += 1
        sales_rep_summary = sorted(
            rep_map.values(), key=lambda x: x['invoice'], reverse=True
        )

        status_items = [
            (status, label, status_counts.get(status, 0))
            for status, label in WorkRecord.STATUS_CHOICES
        ]
        ctx.update({
            'current_year': now.year,
            'current_month': now.month,
            'current_records': current_records,
            'total_early': total_early,
            'total_late': total_late,
            'total_gross': total_gross,
            'status_items': status_items,
            'chart_labels': json.dumps(chart_labels),
            'chart_data': json.dumps(chart_data),
            'client_ranking': client_ranking,
            'sales_rep_summary': sales_rep_summary,
            'alert_pending': status_counts.get('pending', 0),
            'alert_waiting': status_counts.get('waiting_transfer', 0),
        })
        return ctx


# ── Work Records ───────────────────────────────────────────────────────────────

class WorkRecordListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = WorkRecord
    template_name = 'core/work_list.html'
    context_object_name = 'records'

    def get_queryset(self):
        qs = super().get_queryset().select_related('client', 'worker', 'worker__partner')
        p = self.request.GET
        if p.get('month'):
            try:
                y, m = p['month'].split('-')
                qs = qs.filter(target_year=int(y), target_month=int(m))
            except (ValueError, AttributeError):
                pass
        if p.get('client'):
            qs = qs.filter(client_id=p['client'])
        if p.get('partner'):
            qs = qs.filter(worker__partner_id=p['partner'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = self.get_company()
        records = list(ctx['records'])
        ctx.update({
            'clients': Client.objects.filter(company=company),
            'partners': Partner.objects.filter(company=company),
            'status_choices': WorkRecord.STATUS_CHOICES,
            'total_early': sum(r.early_invoice_amount for r in records),
            'total_late': sum(r.late_invoice_amount for r in records),
            'total_gross': sum(r.gross_profit_early for r in records),
            'total_partner': sum(r.partner_payment for r in records),
            'filters': {
                'month': self.request.GET.get('month', ''),
                'client': self.request.GET.get('client', ''),
                'partner': self.request.GET.get('partner', ''),
                'status': self.request.GET.get('status', ''),
            },
        })
        return ctx


class WorkRecordCreateView(LoginRequiredMixin, RoleRequiredMixin, CompanyMixin, CreateView):
    allowed_roles = ROLES_STAFF_UP
    model = WorkRecord
    template_name = 'core/work_form.html'
    success_url = reverse_lazy('work_list')

    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs()
        kwargs['company'] = self.get_company()
        return WorkRecordForm(**kwargs)

    def form_valid(self, form):
        form.instance.company = self.get_company()
        messages.success(self.request, '稼働を登録しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self._js_data())
        return ctx

    def _js_data(self):
        company = self.get_company()
        clients = [
            {'id': str(c.id), 'name': str(c), 'store_name': c.store_name, 'daily_rate': float(c.daily_rate)}
            for c in Client.objects.filter(company=company)
        ]
        workers = [
            {'id': str(w.id), 'name': w.name, 'partner_id': str(w.partner_id), 'daily_rate': float(w.daily_rate)}
            for w in Worker.objects.filter(company=company).select_related('partner')
        ]
        return {'clients_json': json.dumps(clients), 'workers_json': json.dumps(workers)}


class WorkRecordUpdateView(LoginRequiredMixin, RoleRequiredMixin, CompanyMixin, UpdateView):
    allowed_roles = ROLES_STAFF_UP
    model = WorkRecord
    template_name = 'core/work_form.html'
    success_url = reverse_lazy('work_list')

    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs()
        kwargs['company'] = self.get_company()
        return WorkRecordUpdateForm(**kwargs)

    def form_valid(self, form):
        messages.success(self.request, '稼働を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = self.get_company()
        clients = [
            {'id': str(c.id), 'name': str(c), 'store_name': c.store_name, 'daily_rate': float(c.daily_rate)}
            for c in Client.objects.filter(company=company)
        ]
        workers = [
            {'id': str(w.id), 'name': w.name, 'partner_id': str(w.partner_id), 'daily_rate': float(w.daily_rate)}
            for w in Worker.objects.filter(company=company).select_related('partner')
        ]
        ctx.update({'clients_json': json.dumps(clients), 'workers_json': json.dumps(workers)})
        return ctx


class WorkRecordDeleteView(LoginRequiredMixin, RoleRequiredMixin, CompanyMixin, DeleteView):
    allowed_roles = ROLES_STAFF_UP
    model = WorkRecord
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('work_list')

    def form_valid(self, form):
        messages.success(self.request, '稼働を削除しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cancel_url'] = reverse_lazy('work_list')
        ctx['object_name'] = str(self.get_object())
        return ctx


@login_required
def update_work_status(request, pk):
    if getattr(getattr(request.user, 'profile', None), 'role', '') not in ROLES_STAFF_UP:
        messages.error(request, 'この操作を行う権限がありません。')
        return redirect('work_list')
    record = get_object_or_404(WorkRecord, pk=pk, company=request.user.profile.company)
    new_status = request.POST.get('status')
    if new_status and new_status in dict(WorkRecord.STATUS_CHOICES):
        record.status = new_status
        record.save(update_fields=['status'])
        messages.success(request, 'ステータスを更新しました。')
    return redirect(request.POST.get('next', 'work_list'))


# ── Transfer List ──────────────────────────────────────────────────────────────

class TransferListView(LoginRequiredMixin, TemplateView):
    template_name = 'core/transfer_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = self.request.user.profile.company
        now = datetime.now()
        month_str = self.request.GET.get('month', '')
        try:
            y, m = map(int, month_str.split('-'))
        except (ValueError, AttributeError):
            y, m = now.year, now.month

        records = WorkRecord.objects.filter(
            company=company, target_year=y, target_month=m
        ).exclude(status='pending').select_related('worker', 'worker__partner', 'client')

        partner_data = {}
        for rec in records:
            partner = rec.worker.partner
            pid = str(partner.id)
            if pid not in partner_data:
                partner_data[pid] = {'partner': partner, 'records': [], 'total': Decimal('0')}
            partner_data[pid]['records'].append(rec)
            partner_data[pid]['total'] += rec.partner_payment

        ctx.update({
            'partner_data': list(partner_data.values()),
            'filter_year': y,
            'filter_month': m,
            'filter_month_str': f'{y}-{m:02d}',
            'grand_total': sum(d['total'] for d in partner_data.values()) if partner_data else Decimal('0'),
        })
        return ctx


# ── Master: Client ─────────────────────────────────────────────────────────────

class ClientListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = Client
    template_name = 'core/client_list.html'
    context_object_name = 'clients'


class ClientCreateView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('client_list')

    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs()
        kwargs['company'] = self.get_company()
        return ClientForm(**kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'クライアント先を登録しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'title': 'クライアント先 登録', 'cancel_url': reverse_lazy('client_list')})
        return ctx


class ClientUpdateView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('client_list')

    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs()
        kwargs['company'] = self.get_company()
        return ClientForm(**kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'クライアント先を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'title': 'クライアント先 編集', 'cancel_url': reverse_lazy('client_list')})
        return ctx


class ClientDeleteView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, DeleteView):
    model = Client
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('client_list')

    def form_valid(self, form):
        messages.success(self.request, 'クライアント先を削除しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'cancel_url': reverse_lazy('client_list'), 'object_name': str(self.get_object())})
        return ctx


# ── Master: SalesRep ───────────────────────────────────────────────────────────

class SalesRepListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = SalesRep
    template_name = 'core/sales_rep_list.html'
    context_object_name = 'sales_reps'


class SalesRepCreateView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, CreateView):
    model = SalesRep
    form_class = SalesRepForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('sales_rep_master_list')

    def form_valid(self, form):
        messages.success(self.request, '担当営業を登録しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'title': '担当営業 登録', 'cancel_url': reverse_lazy('sales_rep_master_list')})
        return ctx


class SalesRepUpdateView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, UpdateView):
    model = SalesRep
    form_class = SalesRepForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('sales_rep_master_list')

    def form_valid(self, form):
        messages.success(self.request, '担当営業を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'title': '担当営業 編集', 'cancel_url': reverse_lazy('sales_rep_master_list')})
        return ctx


class SalesRepDeleteView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, DeleteView):
    model = SalesRep
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('sales_rep_master_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'cancel_url': reverse_lazy('sales_rep_master_list'), 'object_name': str(self.get_object())})
        return ctx


# ── Master: Partner ────────────────────────────────────────────────────────────

class PartnerListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = Partner
    template_name = 'core/partner_list.html'
    context_object_name = 'partners'


class PartnerCreateView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, CreateView):
    model = Partner
    form_class = PartnerForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('partner_list')

    def form_valid(self, form):
        messages.success(self.request, 'パートナー企業を登録しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'title': 'パートナー企業 登録', 'cancel_url': reverse_lazy('partner_list')})
        return ctx


class PartnerUpdateView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, UpdateView):
    model = Partner
    form_class = PartnerForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('partner_list')

    def form_valid(self, form):
        messages.success(self.request, 'パートナー企業を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'title': 'パートナー企業 編集', 'cancel_url': reverse_lazy('partner_list')})
        return ctx


class PartnerDeleteView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, DeleteView):
    model = Partner
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('partner_list')

    def form_valid(self, form):
        messages.success(self.request, 'パートナー企業を削除しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'cancel_url': reverse_lazy('partner_list'), 'object_name': str(self.get_object())})
        return ctx


# ── Master: Worker ─────────────────────────────────────────────────────────────

class WorkerListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = Worker
    template_name = 'core/worker_list.html'
    context_object_name = 'workers'

    def get_queryset(self):
        return super().get_queryset().select_related('partner')


class WorkerCreateView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, CreateView):
    model = Worker
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('worker_list')

    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs()
        kwargs['company'] = self.get_company()
        return WorkerForm(**kwargs)

    def form_valid(self, form):
        form.instance.company = self.get_company()
        messages.success(self.request, '稼働者を登録しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'title': '稼働者 登録', 'cancel_url': reverse_lazy('worker_list')})
        return ctx


class WorkerUpdateView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, UpdateView):
    model = Worker
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('worker_list')

    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs()
        kwargs['company'] = self.get_company()
        return WorkerForm(**kwargs)

    def form_valid(self, form):
        messages.success(self.request, '稼働者を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'title': '稼働者 編集', 'cancel_url': reverse_lazy('worker_list')})
        return ctx


class WorkerDeleteView(LoginRequiredMixin, AdminRequiredMixin, CompanyMixin, DeleteView):
    model = Worker
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('worker_list')

    def form_valid(self, form):
        messages.success(self.request, '稼働者を削除しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'cancel_url': reverse_lazy('worker_list'), 'object_name': str(self.get_object())})
        return ctx


# ── Company Settings ───────────────────────────────────────────────────────────

class CompanySettingsView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = CompanySettings
    form_class = CompanySettingsForm
    template_name = 'core/company_settings.html'
    success_url = reverse_lazy('company_settings')

    def get_object(self, queryset=None):
        company = self.request.user.profile.company
        obj, _ = CompanySettings.objects.get_or_create(company=company)
        return obj

    def form_valid(self, form):
        messages.success(self.request, '会社設定を保存しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'title': '会社設定', 'cancel_url': reverse_lazy('dashboard')})
        return ctx


# ── User Management ────────────────────────────────────────────────────────────

class UserListView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'core/user_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profiles'] = UserProfile.objects.filter(
            company=self.request.user.profile.company
        ).select_related('user').order_by('user__username')
        return ctx


class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request):
        return render(request, 'core/user_form.html', {
            'form': UserCreateForm(), 'title': 'ユーザー追加',
        })

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            company = request.user.profile.company
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            UserProfile.objects.create(
                user=user, company=company, role=form.cleaned_data['role']
            )
            messages.success(request, f'ユーザー「{user.username}」を追加しました。')
            return redirect('user_list')
        return render(request, 'core/user_form.html', {'form': form, 'title': 'ユーザー追加'})


class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin, View):
    def _get_profile(self, request, pk):
        return get_object_or_404(
            UserProfile, pk=pk, company=request.user.profile.company
        )

    def get(self, request, pk):
        profile = self._get_profile(request, pk)
        form = UserUpdateForm(initial={'role': profile.role})
        return render(request, 'core/user_form.html', {
            'form': form, 'title': f'ユーザー編集（{profile.user.username}）',
            'editing': True, 'profile': profile,
        })

    def post(self, request, pk):
        profile = self._get_profile(request, pk)
        form = UserUpdateForm(request.POST)
        if form.is_valid():
            profile.role = form.cleaned_data['role']
            profile.save()
            if form.cleaned_data.get('password'):
                profile.user.set_password(form.cleaned_data['password'])
                profile.user.save()
            messages.success(request, '更新しました。')
            return redirect('user_list')
        return render(request, 'core/user_form.html', {
            'form': form, 'title': f'ユーザー編集（{profile.user.username}）',
            'editing': True, 'profile': profile,
        })


class UserDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, pk):
        profile = get_object_or_404(
            UserProfile, pk=pk, company=request.user.profile.company
        )
        if profile.user == request.user:
            messages.error(request, '自分自身は削除できません。')
        else:
            username = profile.user.username
            profile.user.delete()
            messages.success(request, f'ユーザー「{username}」を削除しました。')
        return redirect('user_list')


# ── CSV Export ──────────────────────────────────────────────────────────────────

@login_required
def export_bank_info_csv(request):
    if not request.user.profile.is_admin:
        messages.error(request, '管理者権限が必要です。')
        return redirect('dashboard')

    company = request.user.profile.company
    s = CompanySettings.objects.filter(company=company).first()

    def sanitize(val):
        val = str(val) if val else ''
        if val and val[0] in ('=', '+', '-', '@', '\t', '\r', '\n'):
            val = "'" + val
        return val

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="bank_info.csv"'
    writer = csv.writer(response)
    writer.writerow(['会社名', '銀行名', '支店名', '口座種別', '口座番号', '口座名義'])
    if s:
        account_type = dict(CompanySettings.ACCOUNT_TYPE_CHOICES).get(s.account_type, s.account_type)
        writer.writerow([
            sanitize(s.company_name or company.name),
            sanitize(s.bank_name),
            sanitize(s.branch_name),
            sanitize(account_type),
            sanitize(s.account_number),
            sanitize(s.account_holder),
        ])
    return response


# ── Sales Rep Report ───────────────────────────────────────────────────────────

class SalesRepReportView(LoginRequiredMixin, TemplateView):
    template_name = 'core/sales_rep_report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = self.request.user.profile.company
        now = datetime.now()

        month_str = self.request.GET.get('month', '')
        all_period = self.request.GET.get('all', '') == '1'
        try:
            y, m = map(int, month_str.split('-'))
        except (ValueError, AttributeError):
            y, m = now.year, now.month

        qs = WorkRecord.objects.filter(company=company).select_related(
            'client', 'client__sales_rep', 'worker', 'worker__partner'
        )
        if not all_period:
            qs = qs.filter(target_year=y, target_month=m)

        rep_map = {}
        for rec in qs:
            rep_obj = rec.client.sales_rep
            rep_key = str(rep_obj.pk) if rep_obj else '__unset__'
            if rep_key not in rep_map:
                rep_map[rep_key] = {
                    'name': rep_obj.name if rep_obj else '（未設定）',
                    'clients': {},
                }
            cid = str(rec.client_id)
            if cid not in rep_map[rep_key]['clients']:
                rep_map[rep_key]['clients'][cid] = {
                    'client': rec.client,
                    'records': [],
                    'invoice': Decimal('0'),
                    'partner': Decimal('0'),
                    'gross': Decimal('0'),
                }
            entry = rep_map[rep_key]['clients'][cid]
            entry['records'].append(rec)
            entry['invoice'] += rec.late_invoice_amount
            entry['partner'] += rec.partner_payment
            entry['gross'] += rec.gross_profit_late

        rep_list = []
        for rep_key in sorted(rep_map.keys(), key=lambda k: rep_map[k]['name']):
            clients = list(rep_map[rep_key]['clients'].values())
            rep_list.append({
                'name': rep_map[rep_key]['name'],
                'clients': clients,
                'invoice': sum(c['invoice'] for c in clients),
                'partner': sum(c['partner'] for c in clients),
                'gross': sum(c['gross'] for c in clients),
            })

        ctx.update({
            'rep_list': rep_list,
            'filter_year': y,
            'filter_month': m,
            'filter_month_str': f'{y}-{m:02d}',
            'all_period': all_period,
            'grand_invoice': sum(r['invoice'] for r in rep_list),
            'grand_gross': sum(r['gross'] for r in rep_list),
        })
        return ctx


# ── Invoices ───────────────────────────────────────────────────────────────────

def _next_invoice_number(company, year, month):
    prefix = f'{year}{month:02d}'
    count = Invoice.objects.filter(
        company=company, invoice_number__startswith=prefix
    ).count()
    return f'{prefix}-{count + 1:03d}'


class InvoiceListView(LoginRequiredMixin, CompanyMixin, ListView):
    model = Invoice
    template_name = 'core/invoice_list.html'
    context_object_name = 'invoices'

    def get_queryset(self):
        qs = super().get_queryset().select_related('client')
        if self.request.GET.get('status'):
            qs = qs.filter(status=self.request.GET['status'])
        if self.request.GET.get('client'):
            qs = qs.filter(client_id=self.request.GET['client'])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'clients': Client.objects.filter(company=self.get_company()),
            'status_choices': Invoice.STATUS_CHOICES,
            'filters': {
                'status': self.request.GET.get('status', ''),
                'client': self.request.GET.get('client', ''),
            },
        })
        return ctx


class InvoiceDetailView(LoginRequiredMixin, CompanyMixin, DetailView):
    model = Invoice
    template_name = 'core/invoice_detail.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoice = self.get_object()
        ctx['records'] = invoice.get_work_records()
        ctx['settings'] = CompanySettings.objects.filter(company=self.get_company()).first()
        return ctx


class InvoiceCreateView(LoginRequiredMixin, RoleRequiredMixin, CompanyMixin, CreateView):
    allowed_roles = ROLES_INVOICE_UP
    model = Invoice
    template_name = 'core/invoice_form.html'
    success_url = reverse_lazy('invoice_list')

    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs()
        kwargs['company'] = self.get_company()
        form = InvoiceForm(**kwargs)
        if self.request.method == 'GET':
            now = datetime.now()
            form.initial.setdefault('issue_date', date.today().isoformat())
            form.initial.setdefault('target_year', now.year)
            form.initial.setdefault('target_month', now.month)
            form.initial.setdefault(
                'invoice_number',
                _next_invoice_number(self.get_company(), now.year, now.month)
            )
        return form

    def form_valid(self, form):
        form.instance.company = self.get_company()
        messages.success(self.request, '請求書を作成しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = '請求書 新規作成'
        return ctx


class InvoiceUpdateView(LoginRequiredMixin, RoleRequiredMixin, CompanyMixin, UpdateView):
    allowed_roles = ROLES_INVOICE_UP
    model = Invoice
    template_name = 'core/invoice_form.html'
    success_url = reverse_lazy('invoice_list')

    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs()
        kwargs['company'] = self.get_company()
        return InvoiceForm(**kwargs)

    def form_valid(self, form):
        messages.success(self.request, '請求書を更新しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = '請求書 編集'
        return ctx


class InvoiceDeleteView(LoginRequiredMixin, RoleRequiredMixin, CompanyMixin, DeleteView):
    allowed_roles = ROLES_INVOICE_UP
    model = Invoice
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('invoice_list')

    def form_valid(self, form):
        messages.success(self.request, '請求書を削除しました。')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({'cancel_url': reverse_lazy('invoice_list'), 'object_name': str(self.get_object())})
        return ctx


@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, company=request.user.profile.company)
    settings_obj = CompanySettings.objects.filter(company=invoice.company).first()
    records = list(invoice.get_work_records())

    html = render_to_string('core/invoice_pdf.html', {
        'invoice': invoice,
        'settings': settings_obj,
        'records': records,
    }, request=request)

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = (
            f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        )
        return resp
    except Exception:
        return HttpResponse(html, content_type='text/html')


# ── AJAX ───────────────────────────────────────────────────────────────────────

@login_required
def api_client_info(request):
    cid = request.GET.get('client_id')
    client = get_object_or_404(Client, id=cid, company=request.user.profile.company)
    return JsonResponse({'store_name': client.store_name, 'daily_rate': float(client.daily_rate)})


@login_required
def api_worker_info(request):
    wid = request.GET.get('worker_id')
    worker = get_object_or_404(Worker, id=wid, company=request.user.profile.company)
    return JsonResponse({'daily_rate': float(worker.daily_rate), 'partner_name': worker.partner.name})


@login_required
def api_invoice_preview(request):
    company = request.user.profile.company
    client_id = request.GET.get('client')
    year = request.GET.get('year')
    month = request.GET.get('month')
    if not (client_id and year and month):
        return JsonResponse({'records': [], 'subtotal': 0})
    try:
        client = Client.objects.get(pk=client_id, company=company)
    except Client.DoesNotExist:
        return JsonResponse({'records': [], 'subtotal': 0})
    records = WorkRecord.objects.filter(
        company=company, client=client,
        target_year=int(year), target_month=int(month)
    ).select_related('worker')
    items = [
        {
            'worker': r.worker.name,
            'days': float(r.days_worked),
            'amount': float(r.late_invoice_amount),
        }
        for r in records
    ]
    subtotal = float(sum(r.late_invoice_amount for r in records))
    return JsonResponse({'records': items, 'subtotal': subtotal})

