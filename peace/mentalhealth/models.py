import secrets

from django.conf import settings
from django.db import models
from django.utils.translation import gettext

from .fields import EncryptedTextField
import uuid

# ==========================================
# 1. ストレスヒント
# ==========================================
class StressTip(models.Model):
    title = models.CharField(max_length=200, verbose_name="ヒントのタイトル")
    content = models.TextField(verbose_name="ヒントの内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        verbose_name = "ストレスヒント"
        verbose_name_plural = "ストレスヒント"

    def __str__(self):
        return self.title

# ==========================================
# 2. 先生・担当者（★これを相談より先に書く必要があります！）
# ==========================================
class Teacher(models.Model):
    name = models.CharField("氏名", max_length=100)
    email = models.EmailField("メールアドレス")
    department = models.CharField("学部・所属", max_length=100)
    position = models.CharField("職名", max_length=50, blank=True, default='')
    degree = models.CharField("学位", max_length=100, blank=True, default='')
    # 匿名相談の受信箱にログインするためのアカウント（任意・後から紐付け可）
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teacher_profile',
        verbose_name="ログインアカウント",
    )

    class Meta:
        verbose_name = "先生・担当者"
        verbose_name_plural = "先生・担当者リスト"

    def __str__(self):
        return f"{self.name} ({self.department})"


def generate_anonymous_code() -> str:
    # secrets は暗号論的疑似乱数生成器(CSPRNG)。連番・推測可能なIDにしないための必須要件。
    return f"STU-{secrets.token_hex(4)}"


class StudentProfile(models.Model):
    """
    生徒の「本当の身元」を保持する唯一の場所。
    real_* フィールドはDBには暗号文でしか保存されない(EncryptedTextField)。
    ここへの到達経路（コード上のクエリ）は、危機対応時の本人特定フロー経由に限定し、
    アクセスは必ず IdentityAccessLog に記録すること。
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name="学生アカウント",
    )
    real_name = EncryptedTextField(verbose_name="氏名（暗号化）", blank=True, null=True)
    real_email = EncryptedTextField(verbose_name="連絡用メールアドレス（暗号化）", blank=True, null=True)
    student_number = EncryptedTextField(verbose_name="学籍番号（暗号化）", blank=True, null=True)
    # 最後に使っていた表示言語（返信通知メールをその言語で送るため）
    language = models.CharField("表示言語", max_length=10, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")

    class Meta:
        verbose_name = "学生プロフィール（匿名相談用・暗号化）"
        verbose_name_plural = "学生プロフィール一覧"

    def __str__(self):
        return f"StudentProfile(user_id={self.user_id})"


class Conversation(models.Model):
    """
    生徒1人 × 先生1人 の匿名相談スレッド。
    先生側のUI/メールには anonymous_code だけが出る。student への直リンクは
    アプリ内部でのみ使い、テンプレート/メール本文には絶対に渡さないこと。
    """
    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN, '対応中'),
        (STATUS_CLOSED, '終了'),
    ]

    anonymous_code = models.CharField(
        "匿名コード",
        max_length=20,
        unique=True,
        db_index=True,
        default=generate_anonymous_code,
        editable=False,
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name="学生（内部参照専用・教員には非公開）",
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name="相談先の先生",
    )
    status = models.CharField("状態", max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_at = models.DateTimeField("開始日時", auto_now_add=True)
    last_message_at = models.DateTimeField("最終メッセージ日時", auto_now_add=True)
    # 通知メールの送りすぎ防止用（最後に通知メールを送った日時）
    teacher_notified_at = models.DateTimeField("先生への最終通知日時", null=True, blank=True, editable=False)
    student_notified_at = models.DateTimeField("学生への最終通知日時", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "匿名相談スレッド"
        verbose_name_plural = "匿名相談スレッド一覧"
        indexes = [
            models.Index(fields=['teacher', '-last_message_at'], name='conv_teacher_recent_idx'),
            models.Index(fields=['student', '-last_message_at'], name='conv_student_recent_idx'),
        ]
        constraints = [
            # 生徒×先生のペアにつき、スレッドは常に1本だけ（継続相談として扱う）
            models.UniqueConstraint(fields=['student', 'teacher'], name='uniq_student_teacher_conversation'),
        ]

    def __str__(self):
        return self.anonymous_code

    @property
    def student_label(self) -> str:
        """先生側に表示する唯一の「生徒の呼び名」。匿名コードから作るので身元とは無関係。"""
        return student_label_for(self.anonymous_code)


def student_label_for(anonymous_code: str) -> str:
    # "STU-a3f9c2e1" -> "学生 #A3F9C2E1"（英語なら "Student #A3F9C2E1"）
    return gettext("学生 #%(code)s") % {'code': anonymous_code.removeprefix('STU-').upper()}


class Message(models.Model):
    SENDER_STUDENT = 'student'
    SENDER_TEACHER = 'teacher'
    SENDER_CHOICES = [
        (SENDER_STUDENT, '学生'),
        (SENDER_TEACHER, '先生'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="スレッド",
    )
    sender_role = models.CharField("送信者", max_length=10, choices=SENDER_CHOICES)
    content = models.TextField("本文")
    is_read = models.BooleanField("既読", default=False)
    timestamp = models.DateTimeField("送信日時", auto_now_add=True)

    class Meta:
        verbose_name = "相談メッセージ"
        verbose_name_plural = "相談メッセージ一覧"
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp'], name='msg_conv_time_idx'),
        ]

    def __str__(self):
        return f"[{self.sender_role}] {self.content[:20]}"


class IdentityAccessLog(models.Model):
    """
    管理者・カウンセラーが匿名コードから実名を照会した記録（監査ログ）。
    危機対応(クライシス・エスカレーション)以外での照会を抑止・追跡するために必須。
    accessed_by / conversation は on_delete=PROTECT にして、
    監査証跡そのものを消せないようにしている。
    """
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='identity_accesses',
        verbose_name="照会した管理者/カウンセラー",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.PROTECT,
        related_name='identity_access_logs',
        verbose_name="対象スレッド",
    )
    reason = models.TextField("照会理由")
    accessed_at = models.DateTimeField("照会日時", auto_now_add=True)

    class Meta:
        verbose_name = "本人特定アクセス監査ログ"
        verbose_name_plural = "本人特定アクセス監査ログ一覧"
        ordering = ['-accessed_at']

    def __str__(self):
        return f"{self.accessed_by} -> {self.conversation.anonymous_code} @ {self.accessed_at}"


# ==========================================
# パスワード再設定
# ==========================================
class PasswordResetToken(models.Model):
    """
    パスワード再設定リンク1本分。トークン本体はメールにだけ載せ、DBにはSHA-256ハッシュしか保存しない
    （DBが漏れてもリンクを再現できないようにするため）。
    有効期限つき・1回限り（used_at が入ったら二度と使えない）。
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
    )
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "パスワード再設定トークン"
        verbose_name_plural = "パスワード再設定トークン一覧"

    def __str__(self):
        return f"PasswordResetToken(user_id={self.user_id}, expires_at={self.expires_at})"


class PasswordResetAttempt(models.Model):
    """
    再設定リクエストのレート制限用ログ。登録されていないメールへのリクエストも同じように記録する
    （「制限にかかったかどうか」からメールの登録有無がわからないようにするため）。
    メールアドレスそのものは保存せず、鍵付きハッシュだけを持つ。
    """
    email_hash = models.CharField(max_length=64, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "パスワード再設定リクエスト履歴"
        verbose_name_plural = "パスワード再設定リクエスト履歴"

# ==========================================
# 3. 相談データ（Teacherを使ったあとに書く）
# ==========================================
class Consultation(models.Model):
    ticket_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    # ここで上の Teacher を使うので、Teacherより下に書かないといけません
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name="相談先の先生")
    
    student_name = models.CharField("学生氏名", max_length=100, blank=True, null=True)
    student_id = models.CharField("学籍番号", max_length=20, blank=True, null=True)
    student_email = models.EmailField("連絡用メールアドレス")
    
    is_anonymous = models.BooleanField("匿名希望", default=False)
    subject = models.CharField("件名", max_length=200)
    message = models.TextField("相談本文")
    
    created_at = models.DateTimeField("送信日時", auto_now_add=True)

    class Meta:
        verbose_name = "相談データ"
        verbose_name_plural = "相談データ一覧"

    def __str__(self):
        return self.subject