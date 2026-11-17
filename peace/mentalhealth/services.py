"""
匿名相談機能のドメインロジック（レート制限・通知メール・スレッド取得）。
ビュー関数を薄く保つためにここへ集約する。
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from .models import Conversation, Message, StudentProfile, student_label_for

logger = logging.getLogger(__name__)

# 乱用防止：この時間内に送れるメッセージ数の上限（生徒からの新規メッセージのみ対象）
RATE_LIMIT_WINDOW = timedelta(minutes=10)
RATE_LIMIT_MAX_MESSAGES = 8

# 通知メールは同じスレッドにつき、この間隔で最大1通まで（受信箱をメールで埋めないため）
NOTIFY_COOLDOWN = timedelta(minutes=15)


class RateLimited(Exception):
    """短時間に送りすぎたときに送信をブロックするための例外。"""
    pass


def get_or_create_student_profile(user):
    profile, _ = StudentProfile.objects.get_or_create(user=user)
    return profile


def get_or_create_conversation(student_profile, teacher):
    conversation, _ = Conversation.objects.get_or_create(student=student_profile, teacher=teacher)
    return conversation


def check_student_rate_limit(student_profile):
    window_start = timezone.now() - RATE_LIMIT_WINDOW
    recent_count = Message.objects.filter(
        conversation__student=student_profile,
        sender_role=Message.SENDER_STUDENT,
        timestamp__gte=window_start,
    ).count()
    if recent_count >= RATE_LIMIT_MAX_MESSAGES:
        raise RateLimited(
            _("短時間に送信できるメッセージ数の上限（%(max)s件/%(minutes)s分）に達しました。"
              "しばらく待ってから再度お試しください。") % {
                'max': RATE_LIMIT_MAX_MESSAGES,
                'minutes': int(RATE_LIMIT_WINDOW.total_seconds() // 60),
            }
        )


def remember_language(student_profile, request):
    """生徒が今使っている言語を覚えておく（先生からの返信通知メールをその言語で送るため）。"""
    language = translation.get_language() or settings.LANGUAGE_CODE
    if student_profile.language != language:
        student_profile.language = language
        student_profile.save(update_fields=['language'])


def post_student_message(conversation, content):
    """生徒からの新規メッセージを保存し、先生に通知メールを送る。"""
    message = Message.objects.create(
        conversation=conversation,
        sender_role=Message.SENDER_STUDENT,
        content=content,
    )
    conversation.last_message_at = message.timestamp
    conversation.save(update_fields=['last_message_at'])

    notify_teacher_new_message(conversation)

    return message


def post_teacher_message(conversation, content):
    """先生からの返信を保存し、生徒に通知メールを送る。"""
    message = Message.objects.create(
        conversation=conversation,
        sender_role=Message.SENDER_TEACHER,
        content=content,
    )
    conversation.last_message_at = message.timestamp
    conversation.save(update_fields=['last_message_at'])

    notify_student_new_reply(conversation)

    return message


# ==========================================
# 通知メール
# ==========================================
# 通知メールは必ずシステムのアドレス(DEFAULT_FROM_EMAIL)から、宛先1人だけに送る。
# Reply-To/CC は付けず、本文にも相手のメールアドレス・氏名・匿名コード・相談内容を入れない。
# （メール自体が漏洩・誤送信されても何もわからないようにするため）

def _absolute_url(url_name):
    # リクエストのHostヘッダではなく設定値からURLを組み立てる（Hostヘッダ偽装対策）
    return settings.SITE_BASE_URL.rstrip('/') + reverse(url_name)


def _claim_notification_slot(conversation, field):
    """クールダウン中でなければ通知日時を記録して True を返す。同時実行でも1回だけ True になる。"""
    now = timezone.now()
    cutoff = now - NOTIFY_COOLDOWN
    claimed = (
        Conversation.objects.filter(pk=conversation.pk)
        .filter(Q(**{f'{field}__isnull': True}) | Q(**{f'{field}__lt': cutoff}))
        .update(**{field: now})
    )
    return bool(claimed)


def _send_notification(to_email, subject, body, log_context):
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=None,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception:
        # 通知メールの失敗で「メッセージを送れない」事態は避けたいので落とさないが、
        # 原因調査ができるよう必ずログに残す（fail_silently=Trueだと何も残らず追えなくなる）。
        logger.exception("Failed to send notification email (%s)", log_context)


def notify_teacher_new_message(conversation):
    teacher = conversation.teacher
    if not teacher.email or not _claim_notification_slot(conversation, 'teacher_notified_at'):
        return
    # 先生向けのメールは、サイトの標準言語（日本語）で送る
    with translation.override(settings.LANGUAGE_CODE):
        subject = _("【Peace Mind】新しい匿名相談メッセージがあります")
        body = _(
            "学内匿名相談システムに新しいメッセージが届いています。\n"
            "内容はメールには記載されません。アプリにログインしてご確認ください。"
        )
    _send_notification(
        teacher.email,
        subject,
        f"{body}\n\n{_absolute_url('mentalhealth:teacher_inbox')}\n",
        f"teacher_id={teacher.id}",
    )


def notify_student_new_reply(conversation):
    student = conversation.student
    to_email = student.user.email
    if not to_email or not _claim_notification_slot(conversation, 'student_notified_at'):
        return
    # 生徒向けのメールは、その生徒が最後に使っていた言語で送る
    with translation.override(student.language or settings.LANGUAGE_CODE):
        subject = _("【Peace Mind】先生から返信が届いています")
        body = _(
            "Peace Mind の相談に、先生から返信が届いています。\n"
            "内容はメールには記載されません。アプリにログインしてご確認ください。"
        )
    _send_notification(
        to_email,
        subject,
        f"{body}\n\n{_absolute_url('mentalhealth:soudan_page')}\n",
        f"conversation_id={conversation.id}",
    )


# ==========================================
# 先生側の画面に渡すデータ
# ==========================================
# 先生側のテンプレートには、モデルオブジェクト（Conversation など）を渡さない。
# モデルを渡すと conversation.student.user.email のようにテンプレートから
# 生徒の身元までたどれてしまうため、表示に必要な値だけを持つ dict を作って渡す。

def teacher_inbox_items(teacher):
    rows = (
        Conversation.objects.filter(teacher=teacher)
        .annotate(
            unread_count=Count(
                'messages', filter=Q(messages__sender_role=Message.SENDER_STUDENT, messages__is_read=False)
            )
        )
        .order_by('-last_message_at')
        .values('anonymous_code', 'unread_count', 'last_message_at')
    )
    return [
        {
            'anonymous_code': row['anonymous_code'],
            'student_label': student_label_for(row['anonymous_code']),
            'unread_count': row['unread_count'],
            'last_message_at': row['last_message_at'],
        }
        for row in rows
    ]


def teacher_thread_data(conversation):
    return {
        'anonymous_code': conversation.anonymous_code,
        'student_label': conversation.student_label,
    }


def thread_messages(conversation, viewer_role):
    """どちらの側の画面にも使える、メッセージ表示用の最小限のデータ。"""
    return [
        {
            'is_mine': row['sender_role'] == viewer_role,
            'content': row['content'],
            'timestamp': row['timestamp'],
        }
        for row in conversation.messages.order_by('timestamp').values('sender_role', 'content', 'timestamp')
    ]
