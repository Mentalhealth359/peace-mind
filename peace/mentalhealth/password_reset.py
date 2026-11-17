"""
パスワード再設定（「パスワードをお忘れですか？」）のドメインロジック。

要件:
  - トークンは secrets で生成した推測不能な値。DBにはSHA-256ハッシュのみ保存する
  - 有効期限30分・1回限り
  - メールアドレスの登録有無を外部に一切漏らさない（画面の文言・レート制限・処理時間）
  - メールアドレス単位・IP単位でリクエスト数を制限する
"""
import hashlib
import hmac
import logging
import secrets
import threading
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from .models import PasswordResetAttempt, PasswordResetToken

logger = logging.getLogger(__name__)

TOKEN_TTL = timedelta(minutes=30)
RATE_LIMIT_WINDOW = timedelta(hours=1)
RATE_LIMIT_PER_EMAIL = 3
RATE_LIMIT_PER_IP = 10


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def hash_email(email: str) -> str:
    # 鍵付き(HMAC)にしておくことで、ハッシュ表から元のメールアドレスを総当たりで復元されにくくする
    return hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        email.strip().lower().encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def is_rate_limited(email: str, ip_address: str | None) -> bool:
    since = timezone.now() - RATE_LIMIT_WINDOW
    recent = PasswordResetAttempt.objects.filter(created_at__gte=since)
    if recent.filter(email_hash=hash_email(email)).count() >= RATE_LIMIT_PER_EMAIL:
        return True
    if ip_address and recent.filter(ip_address=ip_address).count() >= RATE_LIMIT_PER_IP:
        return True
    return False


def request_password_reset(email: str, ip_address: str | None) -> bool:
    """
    再設定メールを（該当ユーザーがいれば）送る。
    戻り値は「レート制限にかかったら False、それ以外は True」だけで、
    ユーザーが存在したかどうかは呼び出し側にも返さない。
    """
    if is_rate_limited(email, ip_address):
        return False

    PasswordResetAttempt.objects.create(email_hash=hash_email(email), ip_address=ip_address)

    users = list(get_user_model().objects.filter(email__iexact=email.strip(), is_active=True)[:2])
    # ログインと同じく、メールが一意に決まるユーザーだけを対象にする（EmailBackendと同じ扱い）
    if len(users) != 1 or not users[0].has_usable_password():
        return True
    user = users[0]

    raw_token = secrets.token_urlsafe(32)
    PasswordResetToken.objects.create(
        user=user,
        token_hash=hash_token(raw_token),
        expires_at=timezone.now() + TOKEN_TTL,
    )
    reset_url = settings.SITE_BASE_URL.rstrip('/') + reverse(
        'mentalhealth:password_reset_confirm', args=[raw_token]
    )
    # 別スレッドでは言語の設定が引き継がれないので、今の言語を渡しておく
    _send_in_background(_send_reset_email, user.email, reset_url, translation.get_language())
    return True


def _send_in_background(func, *args):
    # SMTP送信には数百ms〜数秒かかる。登録済みメールの時だけ応答が遅くなると、
    # 応答時間から登録有無がわかってしまうので、送信はレスポンスと切り離す。
    if getattr(settings, 'SEND_EMAIL_IN_BACKGROUND', True):
        threading.Thread(target=func, args=args, daemon=True).start()
    else:
        func(*args)


def _send_reset_email(to_email: str, reset_url: str, language: str | None = None):
    minutes = int(TOKEN_TTL.total_seconds() // 60)
    with translation.override(language or settings.LANGUAGE_CODE):
        subject = _("【Peace Mind】パスワード再設定のご案内")
        intro = _(
            "Peace Mind のパスワード再設定がリクエストされました。\n"
            "下のリンクから新しいパスワードを設定してください。"
        )
        outro = _(
            "このリンクの有効期限は%(minutes)s分で、1回だけ使えます。\n"
            "心当たりがない場合は、このメールを無視してください。パスワードは変更されません。"
        ) % {'minutes': minutes}
    try:
        send_mail(
            subject=subject,
            message=f"{intro}\n\n{reset_url}\n\n{outro}\n",
            from_email=None,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send password reset email")


def get_valid_token(raw_token: str | None):
    """未使用かつ期限内のトークンを返す。該当しなければ None。"""
    if not raw_token:
        return None
    return (
        PasswordResetToken.objects.select_related('user')
        .filter(
            token_hash=hash_token(raw_token),
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
            user__is_active=True,
        )
        .first()
    )


def consume_token_and_set_password(token: PasswordResetToken, set_password_form) -> bool:
    """
    トークンを「使用済み」にしてから新しいパスワードを保存する。
    条件付きUPDATEで使用済みにするので、同じリンクを同時に2回送信されても成功するのは1回だけ。
    """
    now = timezone.now()
    with transaction.atomic():
        claimed = PasswordResetToken.objects.filter(
            pk=token.pk, used_at__isnull=True, expires_at__gt=now,
        ).update(used_at=now)
        if not claimed:
            return False
        set_password_form.save()
        # 同じユーザー宛ての、まだ使われていない他のリンクもすべて無効化する
        PasswordResetToken.objects.filter(user=token.user, used_at__isnull=True).update(used_at=now)
    return True
