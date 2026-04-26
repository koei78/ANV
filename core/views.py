import json
from decimal import Decimal
from datetime import datetime
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages

from .models import Company, CompanySettings, Client, Partner, Worker, WorkRecord
from .forms import (ClientForm, PartnerForm, WorkerForm,
                    WorkRecordForm, WorkRecordUpdateForm, CompanySettingsForm)


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
            ).select_related('client', 'worker')
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


class WorkRecordCreateView(LoginRequiredMixin, CompanyMixin, CreateView):
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


class WorkRecordUpdateView(LoginRequiredMixin, CompanyMixin, UpdateView):
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


class WorkRecordDeleteView(LoginRequiredMixin, CompanyMixin, DeleteView):
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
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('dashboard')

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
            'client', 'worker', 'worker__partner'
        )
        if not all_period:
            qs = qs.filter(target_year=y, target_month=m)

        rep_map = {}
        for rec in qs:
            rep_name = rec.client.sales_rep or '（未設定）'
            if rep_name not in rep_map:
                rep_map[rep_name] = {}
            cid = str(rec.client_id)
            if cid not in rep_map[rep_name]:
                rep_map[rep_name][cid] = {
                    'client': rec.client,
                    'records': [],
                    'invoice': Decimal('0'),
                    'partner': Decimal('0'),
                    'gross': Decimal('0'),
                }
            entry = rep_map[rep_name][cid]
            entry['records'].append(rec)
            entry['invoice'] += rec.late_invoice_amount
            entry['partner'] += rec.partner_payment
            entry['gross'] += rec.gross_profit_late

        rep_list = []
        for rep_name in sorted(rep_map.keys()):
            clients = list(rep_map[rep_name].values())
            rep_list.append({
                'name': rep_name,
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

