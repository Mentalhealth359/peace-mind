"""
メールアドレス＋パスワードでログインするための認証バックエンド。

DjangoのAuthenticationFormは入力値を常に `username` というキー名で
authenticate()に渡してくる（内部の名称であり、実際に何を入力させるかは
フォーム・バックエンド側の自由）。ここではその値をメールアドレスとして扱う。
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email__iexact=username)
        except (UserModel.DoesNotExist, UserModel.MultipleObjectsReturned):
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
