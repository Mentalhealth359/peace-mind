# Peace Mind

学生向けのメンタルヘルス支援 Web アプリです（Django 5.2）。

- **セルフチェック**：ストレス・うつ（PHQ-9）・不安（GAD-7）の質問に答えて、結果を確認できる
- **セルフケア**：呼吸ガイドなどのセルフケアページ
- **AI チャット**：ブラウザの中だけで動く AI（WebLLM / Qwen2.5-0.5B）。会話内容はサーバーに送られない
- **教員への匿名相談**：学生は匿名コード（例 `学生 #A3F9C2E1`）のまま先生とやり取りできる
- **多言語対応**：日本語・英語・ネパール語・ベトナム語・中国語（簡体）・韓国語・ミャンマー語・インドネシア語

アカウントが必要なのは匿名相談だけです。それ以外の機能はログインしなくても使えます。

---

## フォルダ構成（入れ子になっている理由）

`peace` という名前が 2 回続くので分かりにくいですが、これは Django の標準の作り方です。

```
peace-mind/                  ← Git リポジトリのいちばん上（この README がある場所）
├── README.md
├── .gitignore               ← 仮想環境（venv/ .venv/）を Git に入れない設定
├── old/                     ← 使っていないファイルの置き場（中身は old/README.md）
└── peace/                   ← ★ Django プロジェクトのフォルダ。コマンドはここで実行する
    ├── run.py               ← ★ 起動スクリプト（開発 / 本番の切り替え）
    ├── manage.py            ← マイグレーションなどの入口
    ├── requirements.txt     ← 必要なライブラリ
    ├── .env.example         ← 設定ファイルのひな形（コピーして .env を作る）
    ├── .gitignore
    ├── db.sqlite3           ← データベース（自動で作られる・Git には入れない）
    ├── field_encryption.key ← 開発用の暗号化キー（自動で作られる・Git には入れない）
    ├── staticfiles/         ← 本番用に集めた CSS/JS/画像（run.py prod が作る・Git には入れない）
    │
    ├── peace/               ← プロジェクト全体の「設定」パッケージ
    │   ├── settings.py      ← 設定（DB・言語・メール・暗号化キーなど）
    │   ├── urls.py          ← URL の入口（/admin/, /i18n/, /jsi18n/ 以外は mentalhealth へ）
    │   ├── wsgi.py / asgi.py
    │   └── __init__.py
    │
    └── mentalhealth/        ← アプリ本体（画面・機能はすべてここ）
        ├── urls.py          ← ページごとの URL
        ├── views.py         ← 各ページの処理
        ├── models.py        ← データベースの表
        ├── forms.py         ← 登録・ログイン・パスワード再設定のフォーム
        ├── services.py      ← 匿名相談の処理（送信回数の制限・通知メール）
        ├── password_reset.py← パスワード再設定の処理
        ├── questionnaires.py← セルフチェックの質問文と選択肢
        ├── auth_backends.py ← メールアドレスでログインするための仕組み
        ├── crypto.py        ← 暗号化・復号
        ├── fields.py        ← 暗号化して保存する DB フィールド
        ├── i18n_extract.py  ← 翻訳漏れチェック用（テストから使う）
        ├── admin.py         ← 管理画面（/admin/）の設定
        ├── tests.py         ← 自動テスト
        ├── management/commands/
        │   ├── compile_translations.py ← 翻訳ファイル .po → .mo の変換
        │   └── link_teacher_login.py   ← 教員のログインアカウント発行
        ├── migrations/      ← DB の変更履歴（0004・0005 は教員の初期データ）
        ├── templates/mentalhealth/  ← HTML（_ で始まるものは部品）
        ├── static/mentalhealth/     ← css/ js/ photo/
        ├── templatetags/calm_static.py ← CSS/JS の URL に更新時刻を付けるタグ
        └── locale/en/LC_MESSAGES/   ← 英語の翻訳ファイル
```

覚え方：

| フォルダ | 役割 |
|---|---|
| `peace-mind/` | リポジトリ全体 |
| `peace-mind/peace/` | Django プロジェクト。**`manage.py` があるのでコマンドはここで実行** |
| `peace-mind/peace/peace/` | 設定ファイル置き場（`settings.py`, `urls.py`） |
| `peace-mind/peace/mentalhealth/` | アプリ本体。**機能を直すときはほぼここ** |

---

## 動かし方

Python 3.11 以上で動きます（3.12 でテスト済み）。

```bash
cd peace-mind/peace

# 1. 仮想環境を作ってライブラリを入れる
python -m venv .venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate
pip install -r requirements.txt

# 2. 設定ファイルを作る（メールを送らないなら中身はそのままでもよい）
cp .env.example .env

# 3. 管理者アカウントを作る（/admin/ に入るため・最初の 1 回だけ）
python manage.py migrate
python manage.py createsuperuser

# 4. 開発サーバーを起動（データベースの更新も自動で行う）
python run.py dev
```

ブラウザで http://127.0.0.1:8000/ を開きます。`python manage.py runserver` でも今までどおり起動できます。

- 初めて起動したとき、`field_encryption.key` が自動で作られます。**消すと、保存済みの学生情報が読めなくなります。**
- `.env` にメールの設定がなければ、メールは送られずにターミナルに表示されます（開発中はこれで十分です）。

---

## 起動スクリプト `run.py`

`peace-mind/peace/` で実行します。

| コマンド | 内容 |
|---|---|
| `python run.py dev` | 開発サーバー。ファイルを保存すると自動で再起動。エラー画面に詳細が出る（`DEBUG=True`） |
| `python run.py prod` | 本番サーバー（waitress）。設定チェック → `migrate` → `collectstatic` → 起動 |
| `python run.py check` | 本番設定に問題がないか確認だけする |
| `python run.py genkey` | 本番用の `DJANGO_SECRET_KEY` と `FIELD_ENCRYPTION_KEY` を作って表示する |

よく使うオプション：

| オプション | 内容 |
|---|---|
| `--port 8000` | ポート番号（環境変数 `PORT` でも指定できる） |
| `--host 127.0.0.1` | 待ち受けるアドレス（既定 `127.0.0.1`。prod で変えると Cloudflare Tunnel を通さずにアクセスできてしまう） |
| `--threads 8` | prod のみ。同時に処理するリクエスト数 |
| `--trusted-proxy 127.0.0.1` | prod のみ。cloudflared が接続してくる IP（既定 `127.0.0.1`） |
| `--skip-setup` | `migrate` / `collectstatic` を実行せずに起動する |
| `--local` | prod のみ。本番設定を自分の PC で試す（http://localhost で開ける・HTTPS なし） |

開発と本番の違い：

| | 開発（`dev`） | 本番（`prod`） |
|---|---|---|
| `DEBUG` | True | False（エラーの詳細は画面に出さない） |
| `SECRET_KEY` | ファイルに書かれた開発用の値 | 環境変数 `DJANGO_SECRET_KEY`（必須） |
| 公開するドメイン | 制限なし（localhost） | 環境変数 `DJANGO_ALLOWED_HOSTS`（必須） |
| 暗号化キー | なければ `field_encryption.key` を自動作成 | 環境変数 `FIELD_ENCRYPTION_KEY`（必須） |
| CSS / JS の配信 | runserver | WhiteNoise（ファイル名にハッシュを付けて圧縮） |
| HTTPS | なし | HTTP → HTTPS へ転送、Cookie は HTTPS のみ、HSTS |

---

## 本番で公開する手順

```bash
cd peace-mind/peace
pip install -r requirements.txt

# 1. 鍵を作る
python run.py genkey

# 2. .env に本番用の値を書く（.env.example の「本番用」の欄を参照）
#    DJANGO_SECRET_KEY / DJANGO_ALLOWED_HOSTS / DJANGO_CSRF_TRUSTED_ORIGINS /
#    FIELD_ENCRYPTION_KEY / SITE_BASE_URL / メールの設定

# 3. 設定を確認する（ERROR が出なければ OK）
python run.py check

# 4. 起動
python run.py prod
```

- **暗号化キーに注意**：開発中に登録した学生のデータを本番でも使うなら、`FIELD_ENCRYPTION_KEY` は新しく作らず、`field_encryption.key` の中身をそのまま使います。鍵が違うと保存済みのデータを読めなくなります。
- **Cloudflare Tunnel で公開します。** HTTPS は Cloudflare が受け持ちます。
  - `run.py prod` は `127.0.0.1:8000` でだけ待ち受けます。同じマシンの cloudflared（トンネル）以外からは 8000 番に直接つながりません。
  - cloudflared の設定（`config.yml` の `ingress`）では、`service: http://127.0.0.1:8000` を指定します。
  - cloudflared（`127.0.0.1`）が付ける `X-Forwarded-For` と `X-Forwarded-Proto` だけを信用します。これで、本当の接続元 IP（レート制限に使う）と、HTTPS で来たかどうかを受け取れます。
  - cloudflared を別のマシンや Docker コンテナで動かす場合は、`.env` の `WAITRESS_TRUSTED_PROXY` にその IP を書き、`WAITRESS_HOST` を cloudflared から届くアドレスにします。この場合はファイアウォールで、その IP 以外から 8000 番へのアクセスを止めてください。
- **自分の PC で本番設定を試すとき**：`python run.py prod --local` で起動し、http://localhost:8000/ を開きます。localhost でのアクセスを許可し、HTTPS 用の設定を切ります。インターネットに公開するときは使わないでください。
- **`400 Bad Request` / `DisallowedHost` が出たら**：アクセスしたドメインが `DJANGO_ALLOWED_HOSTS` に入っていません。起動時に「アクセスできるドメイン」が表示されるので確認してください。手元で `localhost` を開くなら `--local` を付けます。
- **HSTS**：最初は 1 時間（`DJANGO_HSTS_SECONDS=3600`）にしてあります。問題がなければ 1 年（`31536000`）に上げます。
- `python run.py check` で出る `security.W005` と `security.W021`（HSTS のサブドメインと preload）は、わざと無効にしているものです。

---

## 主な URL

| URL | 内容 | ログイン |
|---|---|---|
| `/` | トップページ | 不要 |
| `/stress/` `/depression/` `/anxiety/` | セルフチェック | 不要 |
| `/takecare/` | セルフケア | 不要 |
| `/aichat/` | AI チャット（ブラウザ内で完結） | 不要 |
| `/signup/` `/login/` `/logout/` | 学生の登録・ログイン（メールアドレスで） | — |
| `/account/` | 自分の登録内容・パスワード変更 | 必要 |
| `/password-reset/` | パスワード再設定 | 不要 |
| `/soudan/` | 学生：相談の一覧と新規相談 | 必要 |
| `/soudan/thread/<匿名コード>/` | 学生：相談スレッド | 必要 |
| `/soudan/teacher/` | 教員：受信箱 | 教員のみ |
| `/soudan/teacher/<匿名コード>/` | 教員：スレッドと返信 | 教員のみ |
| `/soudan/reveal/<匿名コード>/` | 管理者：緊急時の本人確認（理由の入力と記録が必須） | スタッフのみ |
| `/admin/` | Django 管理画面 | スタッフのみ |

ログイン後は、教員なら受信箱へ、学生なら相談ページへ自動で移動します。

---

## 匿名相談のしくみ

```
学生 ──(匿名コードだけが見える)──▶ 教員
  │
  └─ 本名・連絡先・学籍番号は暗号化して保存（StudentProfile）
       └─ 見られるのは管理者が /soudan/reveal/ で理由を書いたときだけ
          → 誰がいつ見たかを IdentityAccessLog に記録（このログは消せない）
```

- 学生 1 人と先生 1 人の組み合わせにつき、スレッドは 1 本です（`Conversation`）。
- 先生側の画面とメールには、学生の身元につながる情報を渡さないように作られています（`services.teacher_inbox_items` など）。
- 学生の連続送信は 10 分間に 8 通まで。通知メールは同じスレッドで 15 分に 1 通までです（`services.py` の先頭で変更できます）。

### 教員アカウントの作り方

教員は自分で登録できません（誰でも先生を名乗れてしまうため）。管理者が次の手順で作ります。

1. `/admin/` の「先生・担当者」で教員を登録する（メールアドレスを入れる）
2. ログイン用アカウントを紐付ける

```bash
python manage.py link_teacher_login <教員のメールアドレス> <ユーザー名> [--password パスワード]
```

`--password` を省略すると、ランダムなパスワードが作られて表示されます。

---

## データベースの表（`models.py`）

| モデル | 内容 |
|---|---|
| `Teacher` | 相談先の先生。`user` でログインアカウントと紐付く |
| `StudentProfile` | 学生の本当の身元（本名・メール・学籍番号は暗号化）と表示言語 |
| `Conversation` | 相談スレッド。匿名コード（`STU-xxxxxxxx`）を持つ |
| `Message` | スレッド内のメッセージ |
| `IdentityAccessLog` | 本人確認をした記録 |
| `PasswordResetToken` | パスワード再設定リンク（DB にはハッシュだけを保存。30 分・1 回限り） |
| `PasswordResetAttempt` | 再設定のリクエスト回数の制限用 |
| `StressTip`, `Consultation` | 管理画面には出るが、現在の画面からは使われていない古い表 |

---

## 設定（`peace/.env`）

| 名前 | 内容 |
|---|---|
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Gmail のアカウントとアプリパスワード。両方あるときだけ実際にメールを送る |
| `DEFAULT_FROM_EMAIL` | 送信元アドレス（省略すると `EMAIL_HOST_USER`） |
| `SITE_BASE_URL` | メールに載せるリンクの URL（初期値 `http://127.0.0.1:8000`） |
| `FIELD_ENCRYPTION_KEY` | 学生情報の暗号化キー。開発中は省略可（`field_encryption.key` を自動で作る）。**本番では必須** |
| `DJANGO_ENV` | `production` で本番設定。`run.py` が自動で設定するので、普段は書かなくてよい |
| `DJANGO_SECRET_KEY` | 本番の秘密鍵（本番では必須） |
| `DJANGO_ALLOWED_HOSTS` | 公開するドメイン。カンマ区切り（本番では必須） |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://example.com` のようにスキーム付きで書く |
| `DJANGO_HTTPS` | 本番で HTTPS 用の設定を使うか（既定 `1`） |
| `DJANGO_HSTS_SECONDS` | HSTS の秒数（既定 `3600`） |
| `WAITRESS_TRUSTED_PROXY` | 前段のリバースプロキシの IP |

---

## 翻訳

- 翻訳する文は、テンプレートでは `{% translate %}`、Python では `_()`、JS では `gettext()` で書きます。
- 翻訳ファイルは `mentalhealth/locale/<言語>/LC_MESSAGES/django.po`（JS 用は `djangojs.po`）です。今あるのは英語だけです。
- `.po` を直したら、次のコマンドで `.mo` を作り直してからサーバーを再起動します。GNU gettext がなくても動きます。

```bash
python manage.py compile_translations
```

---

## テスト

```bash
cd peace-mind/peace
python manage.py test mentalhealth
```

パスワード再設定・ページ表示・登録・匿名相談のプライバシー・翻訳漏れなどを確認します。

---

## 注意

- **仮想環境は Git に入れません。** 各自のパソコンで `python -m venv .venv` を実行して作ってください（`.gitignore` で `venv/` と `.venv/` を除外しています）。
- **使っていないファイルは `old/` にあります。** 一覧と理由は `old/README.md` を見てください。
- データベースは SQLite です。利用者が少ないうちは問題ありませんが、同時に書き込む人が増えたら PostgreSQL などへの移行を考えてください。
