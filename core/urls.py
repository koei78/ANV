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
]
