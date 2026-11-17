"""
翻訳対象の文章（msgid）をソースコードから集める。

Django標準の `makemessages` は GNU gettext（xgettext）が必要で Windows では動かないことが多いため、
このプロジェクトで使っている書き方だけに対応した、簡易版の抽出処理を用意している。
テスト（tests.py）から呼び出して「翻訳漏れがないか」の確認にも使う。

対応している書き方:
  テンプレート : {% translate '…' %} / {% blocktranslate … %}…{% endblocktranslate %} /
                 {% include '…_back.html' with … label='…' %}
  Python       : _('…') / gettext('…') / gettext_lazy('…')
  JavaScript   : gettext("…")（"…" + "…" の連結も可）
"""
import ast
import json
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent

TRANSLATE_RE = re.compile(r"""\{%\s*translate\s+(?P<q>['"])(?P<text>.*?)(?P=q)(?:\s+as\s+\w+)?\s*%\}""")
BLOCK_RE = re.compile(r"\{%\s*blocktranslate(?P<args>[^%]*)%\}(?P<body>.*?)\{%\s*endblocktranslate\s*%\}", re.S)
BACK_LABEL_RE = re.compile(r"""_back\.html'[^%]*?label=(?P<q>['"])(?P<text>.*?)(?P=q)""")
JS_CALL_RE = re.compile(r"""gettext\(\s*((?:"(?:[^"\\]|\\.)*"\s*\+?\s*)+)\)""")
JS_STR_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _blocktranslate_msgid(args, body):
    body = re.sub(r"\{\{\s*(\w+)\s*\}\}", r"%(\1)s", body.replace("%", "%%").replace("%%(", "%("))
    # 上の置換で "%(" が "%%(" にならないよう戻している（{{ var }} → %(var)s のため）
    if "trimmed" in args:
        lines = [line.strip() for line in body.strip("\n").splitlines()]
        body = " ".join(line for line in lines if line)
    return body


def extract_templates():
    found = {}
    for path in sorted((APP_DIR / "templates").rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        text_no_comments = re.sub(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", "", text, flags=re.S)
        rel = path.relative_to(APP_DIR).as_posix()
        for m in TRANSLATE_RE.finditer(text_no_comments):
            found.setdefault(m.group("text"), rel)
        for m in BLOCK_RE.finditer(text_no_comments):
            found.setdefault(_blocktranslate_msgid(m.group("args"), m.group("body")), rel)
        for m in BACK_LABEL_RE.finditer(text_no_comments):
            found.setdefault(m.group("text"), rel)
    return found


def extract_python():
    found = {}
    names = {"_", "gettext", "gettext_lazy", "pgettext"}
    for path in sorted(APP_DIR.glob("*.py")):
        if path.name in {"i18n_extract.py", "tests.py"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in names
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                found.setdefault(node.args[0].value, path.name)
    return found


def _js_strings(text, rel, found):
    for m in JS_CALL_RE.finditer(text):
        parts = [json.loads('"' + s + '"') for s in JS_STR_RE.findall(m.group(1))]
        found.setdefault("".join(parts), rel)


def extract_js():
    found = {}
    for path in sorted((APP_DIR / "static").rglob("*.js")):
        _js_strings(path.read_text(encoding="utf-8"), path.relative_to(APP_DIR).as_posix(), found)
    # テンプレートの中の <script> で使っている gettext("…") も JS 側の辞書に入れる
    for path in sorted((APP_DIR / "templates").rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for script in re.findall(r"<script\b[^>]*>(.*?)</script>", text, flags=re.S):
            _js_strings(script, path.relative_to(APP_DIR).as_posix(), found)
    return found


def extract_all():
    django = {}
    django.update(extract_templates())
    for k, v in extract_python().items():
        django.setdefault(k, v)
    return {"django": django, "djangojs": extract_js()}


if __name__ == "__main__":
    import sys
    data = extract_all()
    out = sys.argv[1] if len(sys.argv) > 1 else None
    payload = json.dumps({d: list(v.keys()) for d, v in data.items()}, ensure_ascii=False, indent=1)
    if out:
        Path(out).write_text(payload, encoding="utf-8")
    for domain, msgs in data.items():
        print(domain, len(msgs))
