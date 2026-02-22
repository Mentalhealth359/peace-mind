from django.db import models
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

    class Meta:
        verbose_name = "先生・担当者"
        verbose_name_plural = "先生・担当者リスト"

    def __str__(self):
        return f"{self.name} ({self.department})"

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