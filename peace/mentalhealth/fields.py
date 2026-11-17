from django.db import models

from .crypto import decrypt_text, encrypt_text


class EncryptedTextField(models.TextField):
    """
    Python側では普通の文字列として読み書きできるが、DBには暗号文(base64)だけが
    保存される TextField。学生の実名・連絡先メール・学籍番号など、
    「暗号化して保存する」ことが要件になっているフィールド専用。

    検索(filter/order_by)や一意制約には使えない — 暗号文は毎回変わるため。
    """

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_text(value)

    def from_db_value(self, value, expression, connection):
        return decrypt_text(value)
