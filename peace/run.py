#!/usr/bin/env python
"""
Peace Mind の起動スクリプト（開発用・本番用の切り替え）。

使い方（manage.py と同じフォルダで実行）:
    python run.py dev                 開発サーバー（自動リロード・DEBUG=True）
    python run.py prod                本番サーバー（waitress・DEBUG=False）
    python run.py prod --local        本番設定を自分のPCで試す（http://localhost:8000 で開ける）
    python run.py check               本番設定に問題がないか確認だけする
    python run.py genkey              本番用の DJANGO_SECRET_KEY と FIELD_ENCRYPTION_KEY を作って表示する

オプション:
    --host 127.0.0.1 --port 8000      待ち受けるアドレスとポート（既定 127.0.0.1:8000）
    --threads 8                       （prod のみ）同時に処理するリクエスト数
    --trusted-proxy 127.0.0.1         （prod のみ）cloudflared が接続してくるIP（既定 127.0.0.1）

本番は Cloudflare Tunnel 経由でだけ公開する前提。127.0.0.1 でだけ待ち受けるので、
トンネル（同じマシンの cloudflared）以外から 8000 番へ直接つなぐことはできない。
    --skip-setup                      migrate / collectstatic を実行せずに起動する

本番に必要な環境変数は .env.example を参照。
"""
import argparse
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def setup_django(env_name):
    # .env より先に決めるため、ここで上書きする（コマンドで選んだ方を必ず使う）
    os.environ['DJANGO_ENV'] = env_name
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'peace.settings')
    sys.path.insert(0, str(BASE_DIR))
    os.chdir(BASE_DIR)
    import django
    try:
        django.setup()
    except RuntimeError as e:
        # 本番の必須設定が足りないとき（settings.py が RuntimeError を出す）
        sys.exit(f"[エラー] {e}")


def cmd_dev(args):
    setup_django('development')
    from django.core.management import call_command

    # 自動リロードの子プロセス（RUN_MAIN=true）では、migrate を二重に実行しない
    if not args.skip_setup and os.environ.get('RUN_MAIN') != 'true':
        call_command('migrate', interactive=False)
    call_command('runserver', f"{args.host or '127.0.0.1'}:{args.port}")


def cmd_check(args):
    setup_django('production')
    from django.core.management import call_command
    call_command('check', deploy=True, fail_level='ERROR')
    print("本番設定のチェックが終わりました（WARNING は内容を確認してください）。")


def cmd_prod(args):
    if args.local:
        # settings.py が読み込まれる前に設定する（localhost を許可し、HTTPS 設定を切る）
        os.environ['DJANGO_LOCAL'] = '1'
    setup_django('production')
    from django.conf import settings
    from django.core.management import call_command

    call_command('check', deploy=True, fail_level='ERROR')
    if not args.skip_setup:
        call_command('migrate', interactive=False)
        call_command('collectstatic', interactive=False, verbosity=0)
        print("静的ファイルを staticfiles/ に集めました。")

    from waitress import serve
    from peace.wsgi import application

    # 本番は Cloudflare Tunnel 経由でだけ公開する。
    # cloudflared は同じマシンから 127.0.0.1:8000 へ接続してくるので、127.0.0.1 でだけ待ち受ければ
    # インターネットや LAN から 8000 番へ直接つなぐことはできない（＝トンネル以外は拒否）。
    host = args.host or os.environ.get('WAITRESS_HOST') or '127.0.0.1'
    options = {'host': host, 'port': args.port, 'threads': args.threads}

    if not args.local:
        # cloudflared（127.0.0.1）が付ける X-Forwarded-For / -Proto だけを信用し、
        # 本当の接続元IP（REMOTE_ADDR）と https で来たかどうかを受け取る。
        # これが無いと HTTPS への転送がループし、レート制限もすべて 127.0.0.1 扱いになる。
        trusted_proxy = args.trusted_proxy or os.environ.get('WAITRESS_TRUSTED_PROXY') or '127.0.0.1'
        options.update(
            trusted_proxy=trusted_proxy,
            trusted_proxy_count=1,
            trusted_proxy_headers='x-forwarded-for x-forwarded-proto',
            clear_untrusted_proxy_headers=True,
        )

    if args.local:
        print("【ローカル確認モード】本番設定を HTTPS なしで動かしています。公開には使わないでください。")
        print(f"本番サーバーを起動します: http://localhost:{args.port}/  （止めるには Ctrl+C）")
    else:
        print(f"本番サーバーを起動します: http://{host}:{args.port}/  （止めるには Ctrl+C）")
        print(f"信用するプロキシ（Cloudflare Tunnel）: {options['trusted_proxy']}")
        if host not in ('127.0.0.1', 'localhost', '::1'):
            print(f"[警告] {host} で待ち受けています。Cloudflare Tunnel を通さずに直接アクセスできてしまいます。")
    # ここに無いドメインでアクセスすると 400 Bad Request（DisallowedHost）になる
    print(f"アクセスできるドメイン: {', '.join(settings.ALLOWED_HOSTS)}")
    if any(h.endswith('example.com') for h in settings.ALLOWED_HOSTS):
        print("[警告] DJANGO_ALLOWED_HOSTS が .env.example の例（example.com）のままです。公開するドメインに書き換えてください。")
    serve(application, **options)


def cmd_genkey(args):
    import secrets
    from cryptography.fernet import Fernet

    print("# .env（または本番サーバーの環境変数）に貼り付けてください。誰にも見せないこと。")
    print(f"DJANGO_SECRET_KEY={secrets.token_urlsafe(50)}")
    print(f"FIELD_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
    print()
    print("# 注意: 開発中に保存した学生情報を本番でも使う場合、FIELD_ENCRYPTION_KEY は新しく作らず、")
    print("#       field_encryption.key の中身をそのまま使うこと（鍵が違うと復号できなくなる）。")


def main():
    parser = argparse.ArgumentParser(description="Peace Mind の起動（開発 / 本番）")
    sub = parser.add_subparsers(dest='command', required=True)

    def add_server_options(p, default_port=8000):
        p.add_argument('--host', default=None,
                       help='待ち受けるアドレス（既定 127.0.0.1。prod で変えると Cloudflare Tunnel を通さず直接アクセスできてしまう）')
        p.add_argument('--port', type=int, default=int(os.environ.get('PORT', default_port)))
        p.add_argument('--skip-setup', action='store_true', help='migrate / collectstatic を実行しない')

    p_dev = sub.add_parser('dev', help='開発サーバーを起動する')
    add_server_options(p_dev)
    p_dev.set_defaults(func=cmd_dev)

    p_prod = sub.add_parser('prod', help='本番サーバーを起動する')
    add_server_options(p_prod)
    p_prod.add_argument('--threads', type=int, default=8)
    p_prod.add_argument('--trusted-proxy', default=None,
                        help='cloudflared が接続してくるIP（既定 127.0.0.1。別マシン/コンテナで動かすときだけ変える）')
    p_prod.add_argument('--local', action='store_true',
                        help='本番設定を自分のPCで試す（http://localhost で開ける・HTTPS なし）')
    p_prod.set_defaults(func=cmd_prod)

    p_check = sub.add_parser('check', help='本番設定を確認する')
    p_check.set_defaults(func=cmd_check)

    p_genkey = sub.add_parser('genkey', help='本番用の秘密鍵を作る')
    p_genkey.set_defaults(func=cmd_genkey)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
