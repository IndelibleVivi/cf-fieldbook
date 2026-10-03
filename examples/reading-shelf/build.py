#!/usr/bin/env python3
"""Build a fully offline reading shelf from three synthetic Markdown originals."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCUMENTS = ('welcome', 'notes', 'checklist')


def build() -> Path:
    cards = []
    for name in DOCUMENTS:
        path = ROOT / 'materials' / f'{name}.md'
        title, _, body = path.read_text(encoding='utf-8').partition('\n')
        paragraphs = ''.join(f'<p>{escape(block)}</p>' for block in body.strip().split('\n\n'))
        cards.append(f'<article id="{name}"><h2>{escape(title.removeprefix("# "))}</h2>'
                     f'{paragraphs}<a href="materials/{name}.md" download>下载原文 Markdown ↗</a></article>')
    page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>三份文档的小资料架 · CF Fieldbook 离线例子</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#fcfcfa;color:#243b3c;font:17px/1.8 system-ui,sans-serif}
main{max-width:760px;padding:40px 22px;margin:auto}h1{font-size:clamp(27px,5vw,40px);line-height:1.3}
.kicker{color:#187f80;font-size:12px;letter-spacing:.12em}a{color:#137d80;text-underline-offset:.2em}
nav{display:flex;gap:14px;flex-wrap:wrap;padding:12px 0}article{margin-top:28px;padding:24px;border:1px solid #cde1de;border-radius:16px;background:white}
h2{font-size:22px;line-height:1.4}p{white-space:pre-line}a:focus-visible{background:#d9ece8;outline:none}
footer{margin-top:32px;font-size:13px;color:#667a79}@media(max-width:420px){main{padding:26px 16px}article{padding:19px}}
</style></head><body><main><p class="kicker">CF FIELDBOOK / OFFLINE READING SHELF</p>
<h1>三份文档，一间小资料架。</h1><p>打开、读完、带走原文。所有材料均为合成输入；页面不连接任何云服务。</p>
<nav aria-label="文档目录"><a href="#welcome">01 资料架</a><a href="#notes">02 更新与撤下</a><a href="#checklist">03 检查单</a></nav>
''' + ''.join(cards) + '''<footer>原创内容 CC BY-NC-SA 4.0 · 功能代码 SUL-1.0<br>made by Faye &amp; Cove</footer></main></body></html>'''
    target = ROOT / 'index.html'
    target.write_text(page, encoding='utf-8')
    return target


if __name__ == '__main__':
    print(build())
