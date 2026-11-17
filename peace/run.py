#!/usr/bin/env python
"""
Peace Mind の起動スクリプト（開発用・本番用の切り替え）。

使い方（manage.py と同じフォルダで実行）:
    python run.py dev                 開発サーバー（自動リロード・DEBUG=True）
    python run.py prod                本番サーバー（waitress・DEBUG=False）
    python run.py check               本番設定に問題がないか確認だけする
    python run.py genkey              本番用の DJANGO_SECRET_KEY と FIELD_ENCRYPTION_KEY を作って表示する

オプション:
    --host 0.0.0.0 --port 8000        待ち受けるアドレスとポート
    --threads 8                       （prod のみ）同時に処理するリクエスト数
    --trusted-proxy 127.0.0.1         （prod のみ）前段に nginx などを置くときのプロキシのIP
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
    setup_django('production')
    from django.core.management import call_command

    call_command('check', deploy=True, fail_level='ERROR')
    if not args.skip_setup:
        call_command('migrate', interactive=False)
        call_command('collectstatic', interactive=False, verbosity=0)
        print("静的ファイルを staticfiles/ に集めました。")

    from waitress import serve
    from peace.wsgi import application

    host = args.host or '0.0.0.0'
    options = {'host': host, 'port': args.port, 'threads': args.threads}
    trusted_proxy = args.trusted_proxy or os.environ.get('WAITRESS_TRUSTED_PROXY')
    if trusted_proxy:
        # プロキシから来た X-Forwarded-For / -Proto だけを信用し、
        # 本当の接続元IP（REMOTE_ADDR）と https かどうかを正しく受け取る
        options.update(
            trusted_proxy=trusted_proxy,
            trusted_proxy_headers='x-forwarded-for x-forwarded-proto',
            clear_untrusted_proxy_headers=True,
        )
    print(f"本番サーバーを起動します: http://{host}:{args.port}/  （止めるには Ctrl+C）")
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
        p.add_argument('--host', default=None, help='待ち受けるアドレス（dev: 127.0.0.1 / prod: 0.0.0.0）')
        p.add_argument('--port', type=int, default=int(os.environ.get('PORT', default_port)))
        p.add_argument('--skip-setup', action='store_true', help='migrate / collectstatic を実行しない')

    p_dev = sub.add_parser('dev', help='開発サーバーを起動する')
    add_server_options(p_dev)
    p_dev.set_defaults(func=cmd_dev)

    p_prod = sub.add_parser('prod', help='本番サーバーを起動する')
    add_server_options(p_prod)
    p_prod.add_argument('--threads', type=int, default=8)
    p_prod.add_argument('--trusted-proxy', default=None, help='前段のリバースプロキシのIP（例: 127.0.0.1）')
    p_prod.set_defaults(func=cmd_prod)

    p_check = sub.add_parser('check', help='本番設定を確認する')
    p_check.set_defaults(func=cmd_check)

    p_genkey = sub.add_parser('genkey', help='本番用の秘密鍵を作る')
    p_genkey.set_defaults(func=cmd_genkey)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
