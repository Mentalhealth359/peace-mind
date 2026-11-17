# C:\Users\Mouse\python\peace\mentalhealth\forms.py

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm # Djangoの組み込みユーザー作成フォームをインポート
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label=_("メールアドレス"))

    class Meta(UserCreationForm.Meta):
        # 使用するUserモデルと表示するフィールドを指定します。
        # UserCreationForm.Meta を継承しているので、ほとんどの設定は引き継がれます。
        # デフォルトでは username, password (2回) が表示されます。
        fields = UserCreationForm.Meta.fields + ('email',) # 例: emailフィールドも追加で表示する場合

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        # メールアドレスでログインするため、他ユーザーと重複していないことを保証する
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError(_('このメールアドレスは既に登録されています。'))
        return email


class EmailAuthenticationForm(AuthenticationForm):
    """ログインを「ユーザー名」ではなく「登録メールアドレス」で行わせるためのフォーム。"""
    username = forms.EmailField(
        label=_("メールアドレス"),
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label=_("登録しているメールアドレス"),
        max_length=254,
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )