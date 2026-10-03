#!/usr/bin/env python3
"""Render local share cards from publication metadata and original SVG motifs.

This explicit design command writes assets/share/*.png; ordinary site builds
only copy these reviewed images. No browser download, remote request or font
file distribution occurs here.
"""
from pathlib import Path
import argparse
from html import escape
from playwright.sync_api import sync_playwright
import publications as pub

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', type=Path, help='An already installed Playwright-compatible Chromium executable')
    args = parser.parse_args()
    target = ROOT / 'assets/share'
    target.mkdir(exist_ok=True)
    collection = pub.Collection(ROOT, pub.load(ROOT))
    cards = [('fieldbook', 'CF Fieldbook', 'Cloudflare 服务的用途、选择与实践参考', '持续编辑的独立参考', 'assets/motifs/cat-sunrise.svg')]
    for fam in collection.families():
        text = collection.text(pub.source_entry(fam))
        cards.append((fam['id'], fam['label'], pub.frontmatter_scalar(text, 'subtitle') or '',
                      '资料截至 ' + (pub.frontmatter_scalar(text, 'source_cutoff') or '未登记'),
                      fam.get('share_motif', 'assets/motifs/cat-sunrise.svg')))
    with sync_playwright() as p:
        options = {'headless': True}
        if args.browser:
            options['executable_path'] = str(args.browser)
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={'width':1200, 'height':630}, device_scale_factor=1)
        page.route('**/*', lambda route: route.abort())
        for ident, title, subtitle, note, motif in cards:
            svg = (ROOT / motif).read_text()
            page.set_content('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;width:1200px;height:630px;background:#fff;color:#183544;font-family:system-ui,sans-serif;border-top:9px solid #007f93}
main{padding:65px 66px;width:750px}.brand{color:#007f93;letter-spacing:.15em;font-size:20px;margin:0 0 55px}
h1{font-size:55px;line-height:1.27;margin:0 0 22px;max-width:690px}p{font-size:24px;line-height:1.6;max-width:650px}
.note{position:absolute;bottom:58px;font-size:19px;color:#566872}.art{position:absolute;right:25px;top:145px;width:380px;height:340px;display:grid;place-items:center}.art svg{width:100%;height:auto;max-height:340px}
.rule{position:absolute;bottom:62px;right:70px;width:210px;height:3px;background:#be4b13}
</style><main><p class="brand">CF FIELDBOOK / INDEPENDENT REFERENCE</p><h1>''' + escape(title) + '</h1><p>' + escape(subtitle) + '</p><p class="note">' + escape(note) + '</p></main><div class="art">' + svg + '</div><div class="rule"></div></html>')
            page.screenshot(path=str(target / f'{ident}.png'), animations='disabled')
        browser.close()
    print(f'Rendered {len(cards)} local 1200 × 630 share cards.')


if __name__ == '__main__':
    main()
