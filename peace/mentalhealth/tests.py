from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Conversation, Message, PasswordResetToken, StudentProfile, Teacher
from .password_reset import RATE_LIMIT_PER_EMAIL, RATE_LIMIT_PER_IP, hash_token
from .services import post_student_message, post_teacher_message

User = get_user_model()

TEST_SETTINGS = dict(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='system@peace-mind.test',
    SITE_BASE_URL='https://peace.example',
    SEND_EMAIL_IN_BACKGROUND=False,
)


def extract_reset_path(body):
    base = 'https://peace.example'
    url = next(line for line in body.splitlines() if line.startswith(base + '/password-reset/'))
    return url[len(base):]


@override_settings(**TEST_SETTINGS)
class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('taro', 'taro@std.kiis.ac.jp', 'old-Passw0rd!')

    def request_reset(self, email, ip='10.0.0.1'):
        return self.client.post(reverse('mentalhealth:password_reset'), {'email': email}, REMOTE_ADDR=ip)

    def set_new_password(self, path, password='brand-New-pass-42'):
        self.client.get(path)
        return self.client.post(reverse('mentalhealth:password_reset_set'), {
            'new_password1': password, 'new_password2': password,
        })

    def test_login_page_has_forgot_password_link(self):
        response = self.client.get(reverse('mentalhealth:login'))
        self.assertContains(response, reverse('mentalhealth:password_reset'))

    def test_same_response_for_registered_and_unknown_email(self):
        known = self.request_reset('taro@std.kiis.ac.jp')
        unknown = self.request_reset('nobody@std.kiis.ac.jp')
        self.assertRedirects(known, reverse('mentalhealth:password_reset_sent'))
        self.assertRedirects(unknown, reverse('mentalhealth:password_reset_sent'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['taro@std.kiis.ac.jp'])
        self.assertEqual(mail.outbox[0].from_email, 'system@peace-mind.test')

    def test_only_token_hash_is_stored(self):
        self.request_reset('taro@std.kiis.ac.jp')
        raw = extract_reset_path(mail.outbox[0].body).strip('/').split('/')[-1]
        token = PasswordResetToken.objects.get()
        self.assertNotEqual(token.token_hash, raw)
        self.assertEqual(token.token_hash, hash_token(raw))
        self.assertAlmostEqual(token.expires_at - token.created_at, timedelta(minutes=30), delta=timedelta(seconds=5))

    def test_reset_flow_changes_password_and_link_works_only_once(self):
        self.request_reset('taro@std.kiis.ac.jp')
        path = extract_reset_path(mail.outbox[0].body)

        # トークン付きURLはすぐにトークンを含まないURLへリダイレクトする
        landing = self.client.get(path)
        self.assertRedirects(landing, reverse('mentalhealth:password_reset_set'))
        self.assertEqual(landing['Referrer-Policy'], 'no-referrer')

        response = self.set_new_password(path)
        self.assertRedirects(response, reverse('mentalhealth:password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('brand-New-pass-42'))

        # 2回目は使えない
        response = self.set_new_password(path, 'another-Pass-77')
        self.assertContains(response, 'このリンクは使えません')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('brand-New-pass-42'))

    def test_expired_link_is_rejected(self):
        self.request_reset('taro@std.kiis.ac.jp')
        path = extract_reset_path(mail.outbox[0].body)
        PasswordResetToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.set_new_password(path)
        self.assertContains(response, 'このリンクは使えません')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('old-Passw0rd!'))

    def test_bogus_token_is_rejected(self):
        response = self.set_new_password('/password-reset/not-a-real-token/')
        self.assertContains(response, 'このリンクは使えません')

    def test_using_one_link_invalidates_other_links(self):
        self.request_reset('taro@std.kiis.ac.jp')
        self.request_reset('taro@std.kiis.ac.jp')
        first, second = (extract_reset_path(m.body) for m in mail.outbox)
        self.set_new_password(second)
        response = self.set_new_password(first, 'another-Pass-77')
        self.assertContains(response, 'このリンクは使えません')

    def test_rate_limit_per_email_applies_to_unknown_emails_too(self):
        for email in ('taro@std.kiis.ac.jp', 'nobody@std.kiis.ac.jp'):
            for i in range(RATE_LIMIT_PER_EMAIL):
                self.request_reset(email, ip=f'10.0.1.{i}')
            response = self.request_reset(email, ip='10.0.2.1')
            self.assertEqual(response.status_code, 429)
        self.assertEqual(len(mail.outbox), RATE_LIMIT_PER_EMAIL)

    def test_rate_limit_per_ip(self):
        for i in range(RATE_LIMIT_PER_IP):
            self.request_reset(f'user{i}@std.kiis.ac.jp', ip='10.9.9.9')
        response = self.request_reset('taro@std.kiis.ac.jp', ip='10.9.9.9')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(mail.outbox), 0)


class PageRenderTests(TestCase):
    PUBLIC_PAGES = [
        'index_page', 'stress_page', 'depression_page', 'anxiety_page', 'resultanxiety_page',
        'takecare_page', 'aichat_page', 'login', 'signup_page', 'password_reset',
    ]

    def test_public_pages_render_with_login_link(self):
        for name in self.PUBLIC_PAGES:
            response = self.client.get(reverse(f'mentalhealth:{name}'))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'calm.css')
            self.assertContains(response, reverse('mentalhealth:login'))
            self.assertNotContains(response, 'ログアウト')

    def test_pages_show_account_menu_when_logged_in(self):
        self.client.force_login(User.objects.create_user('s', 's@example.com', 'pw-123456!'))
        for name in self.PUBLIC_PAGES[:7] + ['soudan_page']:
            response = self.client.get(reverse(f'mentalhealth:{name}'))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'ログアウト')

    def test_inner_pages_have_back_button(self):
        for name in self.PUBLIC_PAGES[1:]:
            self.assertContains(self.client.get(reverse(f'mentalhealth:{name}')), 'class="back-btn"')

    def test_static_files_are_versioned_to_avoid_stale_cache(self):
        html = self.client.get(reverse('mentalhealth:index_page')).content.decode()
        self.assertRegex(html, r'css/calm\.css\?v=\d+')
        self.assertRegex(html, r'js/peace\.js\?v=\d+')

    def test_home_explains_breathing_guide(self):
        response = self.client.get(reverse('mentalhealth:index_page'))
        self.assertContains(response, '1分間の呼吸ガイド')
        self.assertContains(response, 'breath-steps')
        self.assertContains(response, 'id="moodReply"')

    def test_ai_chat_uses_light_model_and_auto_clears(self):
        html = self.client.get(reverse('mentalhealth:aichat_page')).content.decode()
        self.assertIn('Qwen2.5-0.5B-Instruct', html)
        self.assertNotIn('Qwen3-4B', html)
        self.assertIn('id="endBtn"', html)
        self.assertIn('IDLE_LIMIT_MS = 5 * 60 * 1000', html)
        self.assertIn('"pagehide"', html)
        # 会話を localStorage などに保存していないこと
        self.assertNotRegex(html, r'(localStorage|sessionStorage)\.')
        self.assertNotIn('.setItem(', html)

    def test_reveal_identity_page_renders_for_staff(self):
        staff = User.objects.create_user('staff', 'staff@example.com', 'pw-123456!', is_staff=True)
        student = StudentProfile.objects.create(user=User.objects.create_user('x', 'x@example.com', 'pw-123456!'))
        teacher = Teacher.objects.create(name='T', email='t@example.com', department='')
        conversation = Conversation.objects.create(student=student, teacher=teacher)
        self.client.force_login(staff)
        response = self.client.get(reverse('mentalhealth:reveal_identity', args=[conversation.anonymous_code]))
        self.assertContains(response, conversation.student_label)


class SignupTests(TestCase):
    def signup(self, username, email):
        return self.client.post(reverse('mentalhealth:signup_page'), {
            'username': username, 'email': email,
            'password1': 'quiet-Forest-82', 'password2': 'quiet-Forest-82',
        })

    def test_any_email_domain_can_sign_up(self):
        response = self.signup('gmailuser', 'someone@gmail.com')
        # アカウントは相談のために作るので、登録後は相談ページへ
        self.assertRedirects(response, reverse('mentalhealth:soudan_page'))
        self.assertTrue(User.objects.filter(email='someone@gmail.com').exists())

    def test_signup_returns_to_next_but_never_to_external_site(self):
        data = {'username': 'u1', 'email': 'u1@gmail.com', 'password1': 'quiet-Forest-82', 'password2': 'quiet-Forest-82'}
        response = self.client.post(reverse('mentalhealth:signup_page'), {**data, 'next': '/takecare/'})
        self.assertRedirects(response, '/takecare/')
        self.client.logout()
        data.update(username='u2', email='u2@gmail.com')
        response = self.client.post(reverse('mentalhealth:signup_page'), {**data, 'next': 'https://evil.example/'})
        self.assertRedirects(response, reverse('mentalhealth:soudan_page'))

    def test_duplicate_email_is_rejected(self):
        self.signup('first', 'someone@gmail.com')
        response = self.signup('second', 'SOMEONE@gmail.com')
        self.assertContains(response, 'このメールアドレスは既に登録されています。')


class AccountRequirementTests(TestCase):
    def test_features_other_than_consultation_work_without_account(self):
        for name in ['index_page', 'stress_page', 'depression_page', 'anxiety_page', 'takecare_page', 'aichat_page']:
            response = self.client.get(reverse(f'mentalhealth:{name}'))
            self.assertEqual(response.status_code, 200, name)

    def test_consultation_asks_anonymous_user_to_create_account(self):
        response = self.client.get(reverse('mentalhealth:soudan_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mentalhealth/soudan_gate.html')
        self.assertContains(response, reverse('mentalhealth:signup_page') + '?next=/soudan/')
        self.assertContains(response, 'アカウントを作成して相談する')

    def test_anonymous_post_to_consultation_creates_nothing(self):
        teacher = Teacher.objects.create(name='T', email='t@example.com', department='')
        response = self.client.post(reverse('mentalhealth:soudan_page'), {'teacher_id': teacher.id, 'message': 'hi'})
        self.assertTemplateUsed(response, 'mentalhealth/soudan_gate.html')
        self.assertFalse(Message.objects.exists())


class AccountPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('hanako', 'hanako@gmail.com', 'old-Passw0rd!')

    def test_account_page_requires_login(self):
        response = self.client.get(reverse('mentalhealth:account'))
        self.assertRedirects(response, reverse('mentalhealth:login') + '?next=/account/')

    def test_account_page_shows_own_registered_info(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('mentalhealth:account'))
        self.assertContains(response, 'hanako')
        self.assertContains(response, 'hanako@gmail.com')
        self.assertContains(response, '学生')

    def test_password_change(self):
        self.client.login(username='hanako@gmail.com', password='old-Passw0rd!')
        response = self.client.post(reverse('mentalhealth:password_change'), {
            'old_password': 'old-Passw0rd!',
            'new_password1': 'brand-New-pass-42',
            'new_password2': 'brand-New-pass-42',
        })
        self.assertRedirects(response, reverse('mentalhealth:account') + '?changed=1')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('brand-New-pass-42'))
        # 変更後もログインしたまま、完了メッセージが出る
        self.assertContains(self.client.get(response.url), 'パスワードを変更しました')


@override_settings(**TEST_SETTINGS)
class StudentPrivacyTests(TestCase):
    STUDENT_EMAIL = 'hanako.yamada@std.kiis.ac.jp'
    STUDENT_USERNAME = 'HanakoYamada'
    TEACHER_EMAIL = 'counselor@gmail.com'

    def setUp(self):
        self.student_user = User.objects.create_user(
            self.STUDENT_USERNAME, self.STUDENT_EMAIL, 'pw-123456!', first_name='Hanako', last_name='Yamada',
        )
        self.student = StudentProfile.objects.create(user=self.student_user, real_name='山田花子', real_email=self.STUDENT_EMAIL)
        teacher_user = User.objects.create_user('counselor', self.TEACHER_EMAIL, 'pw-123456!')
        self.teacher = Teacher.objects.create(name='相談 先生', email=self.TEACHER_EMAIL, department='', user=teacher_user)
        self.conversation = Conversation.objects.create(student=self.student, teacher=self.teacher)
        Message.objects.create(conversation=self.conversation, sender_role=Message.SENDER_STUDENT, content='こんにちは')

    def assert_no_student_identity(self, text):
        for secret in (self.STUDENT_EMAIL, self.STUDENT_USERNAME, 'Hanako', 'Yamada', '山田花子'):
            self.assertNotIn(secret, text)

    def test_teacher_pages_never_contain_student_identity(self):
        self.client.force_login(self.teacher.user)
        inbox = self.client.get(reverse('mentalhealth:teacher_inbox'))
        thread = self.client.get(reverse('mentalhealth:teacher_thread', args=[self.conversation.anonymous_code]))
        for response in (inbox, thread):
            self.assertEqual(response.status_code, 200)
            self.assert_no_student_identity(response.content.decode())
            self.assertContains(response, self.conversation.student_label)

    def test_teacher_templates_receive_no_model_objects(self):
        # 画面に出さないだけでなく、テンプレートに渡すデータにも身元にたどれるものを含めない
        self.client.force_login(self.teacher.user)
        thread = self.client.get(reverse('mentalhealth:teacher_thread', args=[self.conversation.anonymous_code]))
        inbox = self.client.get(reverse('mentalhealth:teacher_inbox'))
        for value in (thread.context['thread'], *thread.context['messages_list'], *inbox.context['conversations']):
            self.assertIsInstance(value, dict)
            self.assert_no_student_identity(repr(value))
        self.assertNotIn('conversation', thread.context)

    def test_student_label_format(self):
        self.assertRegex(self.conversation.student_label, r'^学生 #[0-9A-F]{8}$')

    def test_teacher_notification_is_sent_by_system_without_student_identity(self):
        post_student_message(self.conversation, 'もう一通')
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [self.TEACHER_EMAIL])
        self.assertEqual(msg.from_email, 'system@peace-mind.test')
        self.assertEqual(msg.reply_to, [])
        self.assertEqual(msg.cc, [])
        self.assert_no_student_identity(msg.subject + msg.body)
        self.assertNotIn('もう一通', msg.body)

    def test_student_notification_is_sent_by_system_without_teacher_email(self):
        post_teacher_message(self.conversation, '返信です')
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [self.STUDENT_EMAIL])
        self.assertEqual(msg.from_email, 'system@peace-mind.test')
        self.assertEqual(msg.reply_to, [])
        self.assertNotIn(self.TEACHER_EMAIL, msg.subject + msg.body)
        self.assertNotIn('返信です', msg.body)

    def test_student_pages_never_contain_teacher_email(self):
        self.client.force_login(self.student_user)
        hub = self.client.get(reverse('mentalhealth:soudan_page'))
        thread = self.client.get(reverse('mentalhealth:soudan_thread', args=[self.conversation.anonymous_code]))
        for response in (hub, thread):
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, self.TEACHER_EMAIL)

    def test_notifications_are_throttled_per_conversation(self):
        post_student_message(self.conversation, '1')
        post_student_message(self.conversation, '2')
        self.assertEqual(len(mail.outbox), 1)
        Conversation.objects.filter(pk=self.conversation.pk).update(
            teacher_notified_at=timezone.now() - timedelta(minutes=16)
        )
        post_student_message(self.conversation, '3')
        self.assertEqual(len(mail.outbox), 2)

    def test_teacher_cannot_open_other_teachers_thread(self):
        other = Teacher.objects.create(
            name='別の先生', email='other@gmail.com', department='',
            user=User.objects.create_user('other', 'other@gmail.com', 'pw-123456!'),
        )
        self.client.force_login(other.user)
        response = self.client.get(reverse('mentalhealth:teacher_thread', args=[self.conversation.anonymous_code]))
        self.assertEqual(response.status_code, 404)
