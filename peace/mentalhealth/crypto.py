"""
匿名相談機能で使う、DB保存時のフィールド暗号化まわり。

学生の本名・連絡先メールなどは、DBファイル(db.sqlite3)やバックアップが
そのまま流出しても内容が読めないよう、アプリ層で暗号化してから保存する。
鍵は settings.FIELD_ENCRYPTION_KEY (通常は環境変数 FIELD_ENCRYPTION_KEY 経由) から取得する。
"""
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
    if not key:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY が設定されていません。"
            "学生の実名・連絡先を暗号化保存するために必須の設定です。"
            "本番環境では環境変数などのシークレット管理を使い、リポジトリにはコミットしないでください。"
        )
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_text(plaintext: str) -> str:
    if plaintext is None:
        return None
    return get_fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')


def decrypt_text(ciphertext: str) -> str:
    if ciphertext is None:
        return None
    try:
        return get_fernet().decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except InvalidToken:
        # 鍵が変わった/データが壊れている場合。中身を推測させず、はっきり失敗させる。
        raise ImproperlyConfigured(
            "保存されている暗号化データを復号できませんでした。FIELD_ENCRYPTION_KEY が"
            "書き込み時と異なっている可能性があります。"
        )
