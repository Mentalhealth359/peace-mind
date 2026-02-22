
# C:\Users\Mouse\python\peace\mentalhealth\urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ... other url patterns
    path('', views.index, name='index_page'), # メインページ
    path('stress/', views.stress_view, name='stress_page'), # ストレスページ
    path('depression/', views.depression_view, name='depression_page'), # うつ病ページ
    path('anxiety/', views.anxiety_view, name='anxiety_page'), # 不安ページ
    path('soudan/', views.soudan_view, name='soudan_page'), # 教員への相談ページ
    path('takecare/', views.takecare_view, name='takecare_page'), # セルフケアページ (新しく追加)
    path('anxiety/result/', views.anxiety_result_view, name='anxiety_result_page')
]

app_name = 'mentalhealth'
