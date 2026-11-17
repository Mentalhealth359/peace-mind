"""
翻訳ファイル（.po）から、Djangoが読み込む .mo ファイルを作る管理コマンド。

Django標準の `compilemessages` は GNU gettext（msgfmt）のインストールが必要で、
Windows では入っていないことが多いため、Python だけで動くこのコマンドを用意している。

使い方:
    python manage.py compile_translations

mentalhealth/locale/<言語>/LC_MESSAGES/*.po をすべて読み、同じ場所に .mo を書き出す。
.po を編集したら、必ずこのコマンドを実行してからサーバーを再起動すること。
"""
import ast
import struct
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def parse_po(path: Path) -> dict:
    """シンプルな .po パーサー（msgctxt・複数形は使っていないので扱わない）。"""
    catalog = {}
    msgid = msgstr = None
    current = None
    fuzzy = False

    def flush():
        nonlocal msgid, msgstr, fuzzy
        if msgid is not None and msgstr is not None and (msgstr or msgid == "") and not (fuzzy and msgid):
            catalog[msgid] = msgstr
        msgid = msgstr = None
        fuzzy = False

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            flush()
            current = None
            continue
        if line.startswith("#,") and "fuzzy" in line:
            fuzzy = True
            continue
        if line.startswith("#"):
            continue
        try:
            if line.startswith("msgid "):
                if msgid is not None and msgstr is not None:
                    flush()
                msgid = ast.literal_eval(line[6:])
                current = "msgid"
            elif line.startswith("msgstr "):
                msgstr = ast.literal_eval(line[7:])
                current = "msgstr"
            elif line.startswith('"'):
                value = ast.literal_eval(line)
                if current == "msgid":
                    msgid += value
                elif current == "msgstr":
                    msgstr += value
            else:
                raise ValueError("unexpected line")
        except (ValueError, SyntaxError) as e:
            raise CommandError(f"{path}:{lineno}: 読み取れない行です: {raw!r} ({e})")
    flush()
    return catalog


def write_mo(catalog: dict, path: Path):
    """GNU gettext の .mo 形式（リトルエンディアン）で書き出す。"""
    keys = sorted(catalog.keys())
    ids = b""
    strs = b""
    offsets = []
    for key in keys:
        k = key.encode("utf-8")
        v = catalog[key].encode("utf-8")
        offsets.append((len(ids), len(k), len(strs), len(v)))
        ids += k + b"\0"
        strs += v + b"\0"

    n = len(keys)
    key_table_start = 7 * 4
    value_table_start = key_table_start + n * 8
    ids_start = value_table_start + n * 8
    strs_start = ids_start + len(ids)

    key_table = b""
    value_table = b""
    for id_off, id_len, str_off, str_len in offsets:
        key_table += struct.pack("<II", id_len, ids_start + id_off)
        value_table += struct.pack("<II", str_len, strs_start + str_off)

    header = struct.pack("<7I", 0x950412DE, 0, n, key_table_start, value_table_start, 0, 0)
    path.write_bytes(header + key_table + value_table + ids + strs)


class Command(BaseCommand):
    help = "mentalhealth/locale 以下の .po ファイルを .mo にコンパイルする（GNU gettext 不要）"

    def handle(self, *args, **options):
        count = 0
        for locale_dir in settings.LOCALE_PATHS:
            for po in sorted(Path(locale_dir).glob("*/LC_MESSAGES/*.po")):
                catalog = parse_po(po)
                if "" not in catalog:
                    raise CommandError(f"{po}: ヘッダー（msgid \"\"）がありません。")
                write_mo(catalog, po.with_suffix(".mo"))
                self.stdout.write(f"  {po.parent.parent.name}/{po.name}: {len(catalog) - 1} 件")
                count += 1
        if not count:
            raise CommandError("コンパイルする .po ファイルが見つかりませんでした。")
        self.stdout.write(self.style.SUCCESS(f"{count} 個の翻訳ファイルをコンパイルしました。"))
