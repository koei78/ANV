from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Company, CompanySettings, UserProfile


class Command(BaseCommand):
    help = '初期セットアップ: 会社と管理者ユーザーを作成します'

    def add_arguments(self, parser):
        parser.add_argument('company_name', type=str, help='会社名（例: ANV）')
        parser.add_argument('--username', type=str, default='admin', help='管理者ユーザー名')
        parser.add_argument('--email', type=str, default='', help='メールアドレス')
        parser.add_argument('--password', type=str, required=True, help='パスワード')

    def handle(self, *args, **options):
        company, created = Company.objects.get_or_create(name=options['company_name'])
        if created:
            CompanySettings.objects.create(company=company, company_name=options['company_name'])
            self.stdout.write(f'会社を作成: {company.name}')
        else:
            self.stdout.write(f'既存の会社を使用: {company.name}')

        username = options['username']
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'ユーザー "{username}" は既に存在します'))
            return

        user = User.objects.create_user(
            username=username,
            email=options['email'],
            password=options['password'],
            is_staff=True,
            is_superuser=True,
        )
        UserProfile.objects.create(user=user, company=company, role='admin')
        self.stdout.write(self.style.SUCCESS(
            f'セットアップ完了: 会社={company.name}, ユーザー={user.username}'
        ))
