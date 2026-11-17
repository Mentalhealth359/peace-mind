"""
CSS/JS のURLに「ファイルの更新時刻」をつけるテンプレートタグ。

ブラウザは一度読み込んだ CSS/JS をしばらく使い回すため、ファイルを更新しても
古いデザイン・古い動きのまま表示されることがある。URLに ?v=更新時刻 をつけると、
ファイルが変わったときだけURLも変わるので、必ず新しいファイルが読み込まれる。

使い方: {% load calm_static %} … <script src="{% static_v 'mentalhealth/js/peace.js' %}"></script>
"""
from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(path):
    url = static(path)
    found = finders.find(path)
    if not found:
        return url
    from os.path import getmtime
    return f"{url}?v={int(getmtime(found))}"
