from django.urls import path
from django.shortcuts import render
from . import views


def test_view(request):
    return render(request, 'core/test.html')


urlpatterns = [
    path('test/', test_view, name='test'),
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Work Records
    path('work/', views.WorkRecordListView.as_view(), name='work_list'),
    path('work/new/', views.WorkRecordCreateView.as_view(), name='work_create'),
    path('work/<uuid:pk>/edit/', views.WorkRecordUpdateView.as_view(), name='work_update'),
    path('work/<uuid:pk>/delete/', views.WorkRecordDeleteView.as_view(), name='work_delete'),
    path('work/<uuid:pk>/status/', views.update_work_status, name='work_update_status'),

    # Transfer List
    path('transfer/', views.TransferListView.as_view(), name='transfer_list'),

    # Sales Rep Report
    path('report/sales-rep/', views.SalesRepReportView.as_view(), name='sales_rep_report'),

    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/new/', views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<uuid:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<uuid:pk>/edit/', views.InvoiceUpdateView.as_view(), name='invoice_update'),
    path('invoices/<uuid:pk>/delete/', views.InvoiceDeleteView.as_view(), name='invoice_delete'),
    path('invoices/<uuid:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),

    # Master: SalesReps
    path('master/sales-reps/', views.SalesRepListView.as_view(), name='sales_rep_master_list'),
    path('master/sales-reps/new/', views.SalesRepCreateView.as_view(), name='sales_rep_create'),
    path('master/sales-reps/<uuid:pk>/edit/', views.SalesRepUpdateView.as_view(), name='sales_rep_update'),
    path('master/sales-reps/<uuid:pk>/delete/', views.SalesRepDeleteView.as_view(), name='sales_rep_delete'),

    # Master: Clients
    path('master/clients/', views.ClientListView.as_view(), name='client_list'),
    path('master/clients/new/', views.ClientCreateView.as_view(), name='client_create'),
    path('master/clients/<uuid:pk>/edit/', views.ClientUpdateView.as_view(), name='client_update'),
    path('master/clients/<uuid:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),

    # Master: Partners
    path('master/partners/', views.PartnerListView.as_view(), name='partner_list'),
    path('master/partners/new/', views.PartnerCreateView.as_view(), name='partner_create'),
    path('master/partners/<uuid:pk>/edit/', views.PartnerUpdateView.as_view(), name='partner_update'),
    path('master/partners/<uuid:pk>/delete/', views.PartnerDeleteView.as_view(), name='partner_delete'),

    # Master: Workers
    path('master/workers/', views.WorkerListView.as_view(), name='worker_list'),
    path('master/workers/new/', views.WorkerCreateView.as_view(), name='worker_create'),
    path('master/workers/<uuid:pk>/edit/', views.WorkerUpdateView.as_view(), name='worker_update'),
    path('master/workers/<uuid:pk>/delete/', views.WorkerDeleteView.as_view(), name='worker_delete'),

    # Company Settings
    path('settings/', views.CompanySettingsView.as_view(), name='company_settings'),

    # AJAX
    path('api/client-info/', views.api_client_info, name='api_client_info'),
    path('api/worker-info/', views.api_worker_info, name='api_worker_info'),
    path('api/invoice-preview/', views.api_invoice_preview, name='api_invoice_preview'),
]
