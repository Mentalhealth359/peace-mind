
# C:\Users\Mouse\python\peace\mentalhealth\urls.py

from django.urls import path, reverse_lazy
from django.utils.text import format_lazy
from django.contrib.auth import views as auth_views
from . import views
from .forms import EmailAuthenticationForm

urlpatterns = [
    # ... other url patterns
    path('', views.index, name='index_page'), # メインページ
    path('stress/', views.stress_view, name='stress_page'), # ストレスページ
    path('depression/', views.depression_view, name='depression_page'), # うつ病ページ
    path('anxiety/', views.anxiety_view, name='anxiety_page'), # 不安ページ
    path('takecare/', views.takecare_view, name='takecare_page'), # セルフケアページ (新しく追加)
    path('anxiety/result/', views.anxiety_result_view, name='resultanxiety_page'),
    path('aichat/', views.aichat_view, name='aichat_page'), # AIチャット（ブラウザ内完結・WebLLM）

    # 認証
    path('signup/', views.signup_view, name='signup_page'),
    path('login/', auth_views.LoginView.as_view(template_name='mentalhealth/login.html', authentication_form=EmailAuthenticationForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='mentalhealth:index_page'), name='logout'),
    path('login/redirect/', views.post_login_redirect_view, name='post_login_redirect'),

    # アカウント情報
    path('account/', views.account_view, name='account'),
    path('account/password/', auth_views.PasswordChangeView.as_view(
        template_name='mentalhealth/password_change.html',
        success_url=format_lazy('{}?changed=1', reverse_lazy('mentalhealth:account')),
    ), name='password_change'),

    # パスワード再設定
    path('password-reset/', views.password_reset_request_view, name='password_reset'),
    path('password-reset/sent/', views.password_reset_sent_view, name='password_reset_sent'),
    path('password-reset/new/', views.password_reset_set_view, name='password_reset_set'),
    path('password-reset/done/', views.password_reset_complete_view, name='password_reset_complete'),
    path('password-reset/<str:token>/', views.password_reset_confirm_view, name='password_reset_confirm'),

    # 教員への匿名相談（学生側）
    path('soudan/', views.soudan_page, name='soudan_page'),
    path('soudan/thread/<str:anonymous_code>/', views.soudan_thread_view, name='soudan_thread'),

    # 教員側：受信箱・返信
    path('soudan/teacher/', views.teacher_inbox_view, name='teacher_inbox'),
    path('soudan/teacher/<str:anonymous_code>/', views.teacher_thread_view, name='teacher_thread'),

    # 管理者・カウンセラー専用：危機対応時の本人特定
    path('soudan/reveal/<str:anonymous_code>/', views.reveal_identity_view, name='reveal_identity'),
]

app_name = 'mentalhealth'
