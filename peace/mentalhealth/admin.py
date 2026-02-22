from django.contrib import admin
# .models から 3つのクラスをインポートします
from .models import Teacher, Consultation, StressTip

# 管理画面に表示する設定
admin.site.register(Teacher)
admin.site.register(Consultation)
admin.site.register(StressTip)