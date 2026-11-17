"""
既存の Teacher レコードにログインアカウントを紐付ける（または新規作成する）管理コマンド。

生徒はセルフサインアップできるが、教員アカウントは「誰でも先生を名乗って登録できる」
事態を避けるため、管理者がこのコマンド経由で発行する運用にしている。

使い方:
    python manage.py link_teacher_login <teacher_email> <username> [--password PASSWORD]

--password を省略すると、ランダムなパスワードを生成して表示する。
"""
import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from mentalhealth.models import Teacher


class Command(BaseCommand):
    help = "Teacherレコードにログインアカウントを紐付ける（受信箱にログインできるようにする）"

    def add_arguments(self, parser):
        parser.add_argument('teacher_email', type=str, help='Teacher.email に登録済みのメールアドレス')
        parser.add_argument('username', type=str, help='ログインに使うユーザー名')
        parser.add_argument('--password', type=str, default=None, help='省略時はランダム生成して表示')

    def handle(self, *args, **options):
        User = get_user_model()
        teacher_email = options['teacher_email']
        username = options['username']
        password = options['password'] or secrets.token_urlsafe(10)

        try:
            teacher = Teacher.objects.get(email=teacher_email)
        except Teacher.DoesNotExist:
            raise CommandError(f"Teacher.email='{teacher_email}' が見つかりません。先にTeacherレコードを作成してください。")

        if teacher.user_id:
            raise CommandError(f"{teacher.name} には既にログインアカウント（{teacher.user.username}）が紐付いています。")

        user, created = User.objects.get_or_create(username=username, defaults={'email': teacher_email})
        if not created and hasattr(user, 'teacher_profile'):
            raise CommandError(f"ユーザー '{username}' は既に別のTeacherに紐付いています。")

        user.set_password(password)
        user.email = teacher_email
        user.save()

        teacher.user = user
        teacher.save(update_fields=['user'])

        self.stdout.write(self.style.SUCCESS(
            f"OK: linked login '{username}' to teacher record (email: {teacher_email})."
        ))
        if user.is_staff or user.is_superuser:
            self.stdout.write(self.style.WARNING(
                "WARNING: this account has admin (staff) access. Teacher accounts should not be staff — "
                "the admin site can show student account details. Use a separate account for admin work."
            ))
        if not options['password']:
            self.stdout.write(self.style.WARNING(
                f"Generated password: {password}\nShare this with the teacher through a secure channel."
            ))
