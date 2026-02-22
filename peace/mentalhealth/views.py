from django.shortcuts import render
from django.http import Http404

def index(request):
    return render(request, 'mentalhealth/index.html')

def stress_view(request):
    return render(request, 'mentalhealth/stress.html')

def depression_view(request):
    return render(request, 'mentalhealth/depression.html')

def anxiety_view(request):
    return render(request, 'mentalhealth/anxiety.html')

def soudan_view(request):
    return render(request, 'mentalhealth/soudan.html')

def takecare_view(request): 
    return render(request, 'mentalhealth/takecare.html')



from django.shortcuts import render, redirect # redirect をインポート
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login # ユーザーログインのためのlogin関数をインポート
from .forms import CustomUserCreationForm # ★先ほど作成したフォームをインポート
# from .models import StressTip # もしモデルを使用している場合

def homepage(request):
    return render(request, 'mentalhealth/index.html')

@login_required
def soudan_page(request):
    return render(request, 'mentalhealth/soudan.html', {'message': 'ようこそ、相談ページへ！'})

# ★ユーザー登録ビュー関数を追加
def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save() # ユーザーを保存
            login(request, user) # ユーザーをログインさせる (任意)
            return redirect('mentalhealth:homepage') # 登録成功後にホームページにリダイレクト
    else:
        form = CustomUserCreationForm() # GETリクエストの場合は空のフォームを表示
# ↓ この関数をまるごと追加
def anxiety_result_view(request):
    try:
        # URLからscoreパラメータを取得し、整数に変換
        score = int(request.GET.get('score', -1))
        if not (0 <= score <= 21):
            raise ValueError("Invalid score")
    except (TypeError, ValueError):
        # scoreが不正な場合は404エラーページを表示
        raise Http404("Score parameter is invalid or missing.")

    # スコアに応じて表示する内容を決定（JSからロジックを移動）
    if score <= 4:
        result_text = "不安は最小レベルです"
        advice_text = "現在の状態は良好です。この調子で、日々のリフレッシュを大切にしましょう。"
        icon = "sentiment_very_satisfied"
        result_class = "result-minimal"
    elif score <= 9:
        result_text = "軽度の不安"
        advice_text = "軽度の不安を感じているようです。深呼吸や散歩など、簡単なリラクゼーションを試してみましょう。"
        icon = "sentiment_satisfied"
        result_class = "result-mild"
    elif score <= 14:
        result_text = "中等度の不安"
        advice_text = "不安が日常生活に影響を与え始めているかもしれません。一人で抱え込まず、相談を検討することをお勧めします。"
        icon = "sentiment_dissatisfied"
        result_class = "result-moderate"
    else:
        result_text = "重度の不安"
        advice_text = "専門的なサポートが必要なレベルの不安かもしれません。できるだけ早く、専門医に相談してください。"
        icon = "sentiment_very_dissatisfied"
        result_class = "result-severe"

    context = {
        'score': score,
        'result_text': result_text,
        'advice_text': advice_text,
        'icon': icon,
        'result_class': result_class,
    }
    
    return render(request, 'mentalhealth/anxiety_result.html', context)


from django.shortcuts import render, redirect
from django.core.mail import send_mail  # メール送信機能
from .models import Teacher # 先生のデータベース

# トップページなど他のビューはそのまま...

# ★相談フォームのビュー（ここを修正）
def soudan_page(request):
    # データベースに登録されている先生リストを取得
    teachers = Teacher.objects.all()

    # 「送信」ボタンが押されたときの処理
    if request.method == 'POST':
        # 1. HTMLからデータを取得
        teacher_id = request.POST.get('recipient') # 先生のID
        student_id = request.POST.get('studentId')
        student_name = request.POST.get('name')
        student_email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        # チェックボックスがONなら 'on' が返ってくる
        is_anonymous = request.POST.get('isAnonymous') == 'on' 

        # 2. 宛先の先生を特定
        try:
            target_teacher = Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            # 万が一先生が見つからない場合
            return render(request, 'mentalhealth/soudan.html', {'teachers': teachers, 'error': '先生を選んでください'})

        # 3. メール本文の作成
        if is_anonymous:
            # 匿名の場合：先生には学生の名前を伏せる
            sender_info = "匿名希望の学生"
            reply_notice = "※このメールはシステムからの転送です。"
        else:
            # 実名の場合
            sender_info = f"{student_name} (学籍番号: {student_id})"
            reply_notice = f"返信先: {student_email}"

        email_body = f"""
{target_teacher.name} 先生へ

{sender_info} から相談が届きました。

【件名】
{subject}

【本文】
{message}

--------------------------------------------------
{reply_notice}
"""

        # 4. メールの送信実行
        send_mail(
            subject=f"【相談】{subject}",
            message=email_body,
            from_email="system@peace-mind.com", # 送信元
            recipient_list=[target_teacher.email], # 宛先（先生）
            fail_silently=False,
        )

        # 5. 送信完了画面へ（とりあえずトップへ戻す）
        # 本来は '送信完了しました' ページを作ると親切です
        return redirect('mentalhealth:index')

    # 最初にページを開いたとき
    return render(request, 'mentalhealth/soudan.html', {'teachers': teachers})