# C:\Users\Mouse\python\peace\mentalhealth\forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm # Djangoの組み込みユーザー作成フォームをインポート

class CustomUserCreationForm(UserCreationForm):
    # DjangoのUserCreationFormを拡張する必要がなければ、
    # このクラスは単に UserCreationForm を継承するだけでOKです。
    # 追加のフィールドが必要な場合はここに追加します。
    class Meta(UserCreationForm.Meta):
        # 使用するUserモデルと表示するフィールドを指定します。
        # UserCreationForm.Meta を継承しているので、ほとんどの設定は引き継がれます。
        # デフォルトでは username, password (2回) が表示されます。
        fields = UserCreationForm.Meta.fields + ('email',) # 例: emailフィールドも追加で表示する場合