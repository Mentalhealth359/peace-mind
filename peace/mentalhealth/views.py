from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables

from .forms import CustomUserCreationForm, PasswordResetRequestForm
from .models import Conversation, IdentityAccessLog, Message, Teacher
from .questionnaires import (
    ANXIETY_QUESTIONS,
    DEPRESSION_QUESTIONS,
    FREQUENCY_OPTIONS,
    STRESS_QUESTIONS,
    YES_NO_OPTIONS,
)
from .password_reset import consume_token_and_set_password, get_valid_token, request_password_reset
from .services import (
    RateLimited,
    check_student_rate_limit,
    get_or_create_conversation,
    get_or_create_student_profile,
    remember_language,
    post_student_message,
    post_teacher_message,
    teacher_inbox_items,
    teacher_thread_data,
    thread_messages,
)

# パスワード再設定トークンを一時的に置いておくセッションキー
RESET_TOKEN_SESSION_KEY = 'password_reset_token'


def index(request):
    return render(request, 'mentalhealth/index.html')


def stress_view(request):
    return render(request, 'mentalhealth/stress.html', {
        'questions': STRESS_QUESTIONS, 'options': YES_NO_OPTIONS, 'name_prefix': 'q',
    })


def depression_view(request):
    return render(request, 'mentalhealth/depression.html', {
        'questions': DEPRESSION_QUESTIONS, 'options': FREQUENCY_OPTIONS, 'name_prefix': 'q',
    })


def anxiety_view(request):
    return render(request, 'mentalhealth/anxiety.html', {
        'questions': ANXIETY_QUESTIONS, 'options': FREQUENCY_OPTIONS, 'name_prefix': 'gad7_q',
    })


def anxiety_result_view(request):
    return render(request, 'mentalhealth/anxietyresult.html')


def takecare_view(request):
    return render(request, 'mentalhealth/takecare.html')


def aichat_view(request):
    """ブラウザ内完結のAIチャット（WebLLM）。サーバーには会話内容を一切送受信しない。"""
    return render(request, 'mentalhealth/aichat.html')


def _safe_next(request):
    """?next= の移動先が自サイト内のURLのときだけ返す（外部サイトへ飛ばされるのを防ぐ）。"""
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return ''


# ★ユーザー登録ビュー関数
def signup_view(request):
    next_url = _safe_next(request)
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # ユーザーを保存
            # 登録直後の自動ログイン。メールアドレスでの認証を行うEmailBackendを明示する
            # （AUTHENTICATION_BACKENDSが複数あるため、backendを指定しないとログインできない）
            login(request, user, backend='mentalhealth.auth_backends.EmailBackend')
            # アカウントは相談のために作るものなので、登録後はそのまま相談ページへ
            return redirect(next_url or 'mentalhealth:soudan_page')
    else:
        form = CustomUserCreationForm()  # GETリクエストの場合は空のフォームを表示
    return render(request, 'mentalhealth/signup.html', {'form': form, 'next': next_url})


# ==========================================
# アカウント情報（自分が登録した内容の確認・パスワード変更）
# ==========================================
@login_required
def account_view(request):
    user = request.user
    teacher = getattr(user, 'teacher_profile', None)
    conversation_count = 0
    if teacher is None and hasattr(user, 'student_profile'):
        conversation_count = user.student_profile.conversations.count()
    return render(request, 'mentalhealth/account.html', {
        'account_user': user,
        'teacher': teacher,
        'conversation_count': conversation_count,
        'password_changed': request.GET.get('changed') == '1',
    })


@login_required
def post_login_redirect_view(request):
    """ログイン直後、教員なら受信箱へ、学生なら相談ページへ振り分ける。"""
    if hasattr(request.user, 'teacher_profile'):
        return redirect('mentalhealth:teacher_inbox')
    return redirect('mentalhealth:soudan_page')


# ==========================================
# 学生側：匿名相談
# ==========================================
def soudan_page(request):
    """学生の相談ハブ：既存スレッド一覧 ＋ 新規相談の開始フォーム。"""
    # 相談だけはアカウントが必要。未ログインならログイン画面に飛ばさず、
    # なぜ必要か（返信を受け取るため・匿名のまま）を説明する案内ページを出す。
    if not request.user.is_authenticated:
        return render(request, 'mentalhealth/soudan_gate.html', {'next': request.path})

    student = get_or_create_student_profile(request.user)
    remember_language(student, request)
    # 生徒側にも先生のメールアドレスは渡さない（表示に必要な項目だけ）
    teachers = Teacher.objects.order_by('name').values('id', 'name', 'position', 'department')
    error = None

    if request.method == 'POST':
        teacher_id = request.POST.get('teacher_id')
        message_text = (request.POST.get('message') or '').strip()

        teacher = Teacher.objects.filter(id=teacher_id).first()
        if not teacher:
            error = _('相談したい先生を選んでください。')
        elif not message_text:
            error = _('メッセージを入力してください。')
        else:
            try:
                check_student_rate_limit(student)
            except RateLimited as e:
                error = str(e)
            else:
                conversation = get_or_create_conversation(student, teacher)
                post_student_message(conversation, message_text)
                return redirect('mentalhealth:soudan_thread', anonymous_code=conversation.anonymous_code)

    conversations = (
        Conversation.objects.filter(student=student)
        .annotate(
            unread_count=Count(
                'messages', filter=Q(messages__sender_role=Message.SENDER_TEACHER, messages__is_read=False)
            )
        )
        .order_by('-last_message_at')
        .values('anonymous_code', 'unread_count', 'last_message_at',
                'teacher__name', 'teacher__position')
    )

    return render(request, 'mentalhealth/soudan.html', {
        'teachers': teachers,
        'conversations': conversations,
        'error': error,
    })


@login_required
def soudan_thread_view(request, anonymous_code):
    """学生から見た、1つの相談スレッド（先生とのやり取り）。"""
    conversation = get_object_or_404(
        Conversation.objects.select_related('teacher', 'student'),
        anonymous_code=anonymous_code,
    )
    if conversation.student.user_id != request.user.id:
        raise Http404("スレッドが見つかりません。")

    error = None
    if request.method == 'POST':
        message_text = (request.POST.get('message') or '').strip()
        if not message_text:
            error = _('メッセージを入力してください。')
        else:
            try:
                check_student_rate_limit(conversation.student)
            except RateLimited as e:
                error = str(e)
            else:
                post_student_message(conversation, message_text)
                return redirect('mentalhealth:soudan_thread', anonymous_code=conversation.anonymous_code)

    # 先生からの未読メッセージを既読にする
    conversation.messages.filter(sender_role=Message.SENDER_TEACHER, is_read=False).update(is_read=True)

    teacher = conversation.teacher
    return render(request, 'mentalhealth/soudan_thread.html', {
        'thread': {
            'anonymous_code': conversation.anonymous_code,
            'teacher_name': teacher.name,
            'teacher_position': teacher.position,
        },
        'messages_list': thread_messages(conversation, Message.SENDER_STUDENT),
        'error': error,
    })


# ==========================================
# 教員側：受信箱・返信
# ==========================================
@login_required
def teacher_inbox_view(request):
    if not hasattr(request.user, 'teacher_profile'):
        raise Http404("このページは教員アカウント専用です。")

    teacher = request.user.teacher_profile
    # テンプレートには生徒の身元にたどり着けない dict だけを渡す（services.teacher_inbox_items 参照）
    return render(request, 'mentalhealth/teacher_inbox.html', {
        'teacher_name': teacher.name,
        'teacher_position': teacher.position,
        'conversations': teacher_inbox_items(teacher),
    })


@login_required
def teacher_thread_view(request, anonymous_code):
    if not hasattr(request.user, 'teacher_profile'):
        raise Http404("このページは教員アカウント専用です。")

    teacher = request.user.teacher_profile
    conversation = get_object_or_404(Conversation, anonymous_code=anonymous_code, teacher=teacher)

    error = None
    if request.method == 'POST':
        message_text = (request.POST.get('message') or '').strip()
        if not message_text:
            error = _('メッセージを入力してください。')
        else:
            post_teacher_message(conversation, message_text)
            return redirect('mentalhealth:teacher_thread', anonymous_code=conversation.anonymous_code)

    # 学生からの未読メッセージを既読にする
    conversation.messages.filter(sender_role=Message.SENDER_STUDENT, is_read=False).update(is_read=True)

    # Conversation オブジェクトそのものは渡さない（テンプレートから生徒の身元をたどれないように）
    return render(request, 'mentalhealth/teacher_thread.html', {
        'thread': teacher_thread_data(conversation),
        'messages_list': thread_messages(conversation, Message.SENDER_TEACHER),
        'error': error,
    })


# ==========================================
# 管理者・カウンセラー専用：危機対応時の本人特定（監査ログ付き）
# ==========================================
@staff_member_required
def reveal_identity_view(request, anonymous_code):
    conversation = get_object_or_404(Conversation.objects.select_related('student', 'teacher'), anonymous_code=anonymous_code)
    revealed = None

    if request.method == 'POST':
        reason = (request.POST.get('reason') or '').strip()
        if not reason:
            error = _('照会理由の入力は必須です（監査ログに記録されます）。')
        else:
            IdentityAccessLog.objects.create(accessed_by=request.user, conversation=conversation, reason=reason)
            student = conversation.student
            revealed = {
                'real_name': student.real_name,
                'real_email': student.real_email,
                'student_number': student.student_number,
            }
            error = None
    else:
        error = None

    return render(request, 'mentalhealth/reveal_identity.html', {
        'conversation': conversation,
        'revealed': revealed,
        'error': error,
    })


# ==========================================
# パスワード再設定
# ==========================================
def _client_ip(request):
    # X-Forwarded-For はクライアントが自由に偽装できるので使わない。
    # リバースプロキシの裏で動かす場合は、プロキシ側で REMOTE_ADDR を正しく設定すること。
    return request.META.get('REMOTE_ADDR') or None


@never_cache
def password_reset_request_view(request):
    rate_limited = False
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            if request_password_reset(form.cleaned_data['email'], _client_ip(request)):
                # 登録の有無にかかわらず、常に同じ画面へ
                return redirect('mentalhealth:password_reset_sent')
            rate_limited = True
    else:
        form = PasswordResetRequestForm()

    response = render(request, 'mentalhealth/password_reset_request.html', {
        'form': form,
        'rate_limited': rate_limited,
    })
    if rate_limited:
        response.status_code = 429
    return response


def password_reset_sent_view(request):
    return render(request, 'mentalhealth/password_reset_sent.html')


@never_cache
@sensitive_variables('token')
def password_reset_confirm_view(request, token):
    """
    メールのリンクの着地点。トークンをセッションへ移してから、トークンを含まないURLへすぐ移動する。
    （URLにトークンが残ると、ブラウザ履歴やRefererヘッダ経由で外部に漏れるおそれがあるため）
    """
    request.session[RESET_TOKEN_SESSION_KEY] = token
    response = redirect('mentalhealth:password_reset_set')
    response['Referrer-Policy'] = 'no-referrer'
    return response


@never_cache
@sensitive_post_parameters('new_password1', 'new_password2')
def password_reset_set_view(request):
    token = get_valid_token(request.session.get(RESET_TOKEN_SESSION_KEY))
    if token is None:
        request.session.pop(RESET_TOKEN_SESSION_KEY, None)
        return render(request, 'mentalhealth/password_reset_set.html', {'invalid_link': True})

    if request.method == 'POST':
        form = SetPasswordForm(token.user, request.POST)
        if form.is_valid():
            succeeded = consume_token_and_set_password(token, form)
            request.session.pop(RESET_TOKEN_SESSION_KEY, None)
            if succeeded:
                return redirect('mentalhealth:password_reset_complete')
            return render(request, 'mentalhealth/password_reset_set.html', {'invalid_link': True})
    else:
        form = SetPasswordForm(token.user)

    return render(request, 'mentalhealth/password_reset_set.html', {'form': form})


def password_reset_complete_view(request):
    return render(request, 'mentalhealth/password_reset_complete.html')

