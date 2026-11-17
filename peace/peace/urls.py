"""
URL configuration for peace project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# peace/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path('admin/', admin.site.urls),
    # 言語の切り替え（言語メニューのフォームの送信先）
    path('i18n/', include('django.conf.urls.i18n')),
    # JavaScript 用の翻訳（JSの中で gettext("…") が使えるようになる）
    path('jsi18n/', JavaScriptCatalog.as_view(packages=['mentalhealth']), name='javascript-catalog'),
    path('', include('mentalhealth.urls')), # ★この行が重要

]
