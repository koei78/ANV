from django.contrib import admin
from .models import Company, CompanySettings, UserProfile, Client, Partner, Worker, WorkRecord


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ['company', 'company_name', 'bank_name']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role']
    list_filter = ['role', 'company']


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'store_name', 'daily_rate', 'company']
    list_filter = ['company']
    search_fields = ['name', 'store_name']


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_name', 'company']
    list_filter = ['company']
    search_fields = ['name']


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ['name', 'partner', 'daily_rate', 'company']
    list_filter = ['company', 'partner']
    search_fields = ['name']


@admin.register(WorkRecord)
class WorkRecordAdmin(admin.ModelAdmin):
    list_display = ['target_year', 'target_month', 'client', 'worker', 'days_worked', 'status']
    list_filter = ['company', 'status', 'target_year', 'target_month']
    search_fields = ['client__name', 'worker__name']
