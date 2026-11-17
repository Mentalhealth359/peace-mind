from django.contrib import admin
# .models から必要なクラスをインポートします
from .models import Teacher, Consultation, StressTip, Conversation, Message, IdentityAccessLog


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'department', 'email', 'user')
    search_fields = ('name', 'department', 'email')


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender_role', 'content', 'is_read', 'timestamp')
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    # student は内部参照専用。ここでは匿名コードと先生だけを見せる。
    list_display = ('anonymous_code', 'teacher', 'status', 'created_at', 'last_message_at')
    list_filter = ('status', 'teacher')
    search_fields = ('anonymous_code',)
    # student は表示しない。本人特定は reveal_identity（監査ログ付き）経由に限定する。
    fields = ('anonymous_code', 'teacher', 'status', 'created_at', 'last_message_at')
    readonly_fields = ('anonymous_code', 'teacher', 'created_at', 'last_message_at')
    inlines = [MessageInline]

    def has_add_permission(self, request):
        return False


@admin.register(IdentityAccessLog)
class IdentityAccessLogAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'accessed_by', 'accessed_at', 'reason')
    readonly_fields = ('accessed_by', 'conversation', 'reason', 'accessed_at')
    ordering = ('-accessed_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# 管理画面に表示する設定
admin.site.register(Consultation)
admin.site.register(StressTip)
