#!/usr/bin/env python3
"""Build the reader editions from Markdown. Offline, no remote assets.

Source dates are scoped per entry. Revision 3 refreshes decision-model evidence
only; other existing launch facts are not claimed as rechecked. Exported HTML embeds CSS and SVG, never fonts.
"""
from __future__ import annotations
import argparse
import html
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment
from markdown_it import MarkdownIt
import yaml
from content import project_markdown

ROOT=Path(__file__).resolve().parents[1]
DOCS=[
    dict(path='reports/2026-10-02.md',stem='cf-launches-individuals-2026-10-02-cyan-orange',kind='report',number='01',
         short='新发布观察',cover='新发布观察',kicker='NEW LAUNCHES / FOR INDIVIDUALS',
         deck='运行环境、检索与维护工具的新变化。<br>现在可以用什么，又适合放在哪里。',
         toc='先读感兴趣的方向，费用与开放状态可随时回查。每个章节和来源编号都能点击。',
         types=['THE SHIFT','WORKSPACE','OPERATIONS','SEARCH','MODELS','BROWSER & CREATION','DATA','ECONOMICS','RELEASE INDEX','PROGRAMMES','USE CASES'],
         breaks={2},
         partner='cf-practical-handbook-2026-10-02-cyan-orange.html'),
    dict(path='guides/handbook.md',stem='cf-practical-handbook-2026-10-02-cyan-orange',kind='handbook',number='02',
         short='个人基础设施实践手册',cover='个人基础设施<br>实践手册',kicker='A PRACTICAL HANDBOOK',
         deck='从一个入口到可恢复的应用与自动化。<br>按需要阅读，按自己的环境实践。',
         toc='不必顺着所有章节施工。选一件手边的事，沿着它的入口、状态、结果与维护读下去。',
         types=['START HERE','ROUTES','FIRST WORKER','ACCESS','CONTENT','JOBS','RETRIEVAL','MODELS','WORKSPACE','RELEASE','OBSERVABILITY','ECONOMICS','RECOVERY','EDITION NOTES'],
         breaks={2},
         partner='cf-launches-individuals-2026-10-02-cyan-orange.html')
]
DOCS.append(dict(path='comparisons/clef-vs-jev.md',stem='cf-clef-vs-jev-2026-10-02',kind='comparison',art='report',number='03',
    short='Clef 与 Jev',cover='Clef 与 Jev',kicker='A COMPARISON / DECISION MODELS',
    deck='模型、供应路径与判断成本。<br>从接得上，到值得放进工作流。',
    toc='先确定正在比较的是模型还是入口，再读价格、限制和试验方法。',
    types=['MODELS','PROVIDERS','COST','CONTRACTS','EVIDENCE','EXPERIMENT','MAINTENANCE'],
    breaks=set(),partner='cf-launches-individuals-2026-10-02-cyan-orange.html'))

FIGCAP={
 'workspace':'文件系统可以复用；进程与任务状态另行接续。示意的是一种工作方式，不是自动合并。',
 'runtime-cost':'同一任务数与配置，条长按每次运行分钟数绘制。费用依据 S06；详细假设见正文。',
 'two-routes':'两种常见路线，不要求同时采用。Tunnel 不替原设备运行程序。',
 'task-state':'接收、执行与完成分开记录。示意主线，不是完整状态机；其他分支见下表。'
}


def no_network_fetcher(url: str, **kwargs):
    if url.startswith(('http:','https:','ftp:')):
        raise ValueError('Network assets disabled for deterministic publishing')
    from weasyprint import default_url_fetcher
    return default_url_fetcher(url,**kwargs)


def update_sources(path:Path,sources:dict,text=None)->str:
    if text is None:text=path.read_text(encoding='utf-8')
    core=text.split('<!-- SOURCES -->',1)[0].rstrip()
    used=sorted(set(re.findall(r'\[(S\d{2,3})\]',core)))
    unknown=set(used)-sources.keys()
    if unknown:raise ValueError(f'Unknown source IDs: {unknown}')
    lines=[core,'\n<!-- SOURCES -->\n','## 来源索引',
       '\n本版沿用来源记录中的核验日期与范围；重新构建不代表重新核验。资料核验不等于账户或模型实测。\n']
    for key in used: lines.append(f"- **[{key}]** · {sources[key]['title']}")
    lines.extend(['\n## 关于这一版\n',
       '这是面向个人使用的独立参考资料，不是 Cloudflare 官方出版物。产品事实保留来源，场景与判断属于编辑分析。本次未进行账户操作或云端部署。',
       '\nGitHub：[github.com/IndelibleVivi](https://github.com/IndelibleVivi)  \n*made by Faye & Cove*\n'])
    lines.extend(f"[{key}]: {sources[key]['url']} \"{sources[key]['title']}\"" for key in used)
    result='\n'.join(lines).strip()+'\n'
    # Rendering returns a projection; it must never rewrite the source manuscript.
    return result


def tag(soup,name,attrs=None,text=None):
    out=soup.new_tag(name,attrs=attrs or {})
    if text is not None:out.string=text
    return out


def glossary_for(text):
    """Only definitions linked by this manuscript become its frozen appendix."""
    keys=list(dict.fromkeys(re.findall(r'\]\(\.\./docs/glossary\.md#([\w-]+)\)',text)))
    if not keys:return []
    source=(ROOT/'docs/glossary.md').read_text(encoding='utf-8')
    definitions={}
    for match in re.finditer(r'^## ([\w-]+) / (.+)\n\n([^\n]+)',source,re.M):
        label=f'{match[1]} / {match[2]}'
        ident=re.sub(r'[^\w\s-]', '', label.lower()).replace(' ', '-')
        definitions[ident]=(label,match[3])
    return [(key,*definitions[key]) for key in keys]


def markdown_with_glossary(text,definitions):
    if not definitions:return text
    for key,_,_ in definitions:
        text=text.replace(f'../docs/glossary.md#{key}',f'#{key}')
    text=text.replace('](../docs/glossary.md)','](#术语小词表)')
    appendix='\n## 术语小词表\n\n'+ '\n\n'.join(
        f'### {label}\n\n{definition}' for key,label,definition in definitions)+'\n'
    return text.replace('<!-- SOURCES -->',appendix+'\n<!-- SOURCES -->',1)


def render_one(cfg,sources,dist,edition,formats):
    text=project_markdown(ROOT,cfg['path'])
    if cfg['path'].startswith('reports/'):
        sources={key: {'url':url, 'title':title} for key,url,title in
                 re.findall(r'^\[(S\d{2,3})\]:\s+(\S+)\s+"([^"]+)"\s*$', text, re.M)}
        used=set(re.findall(r'\[(S\d{2,3})\]', text.split('<!-- SOURCES -->',1)[0]))
        if used-sources.keys():raise ValueError('Historical report is missing source definitions')
    else:
        text=update_sources(ROOT/cfg['path'],sources,text)
    definitions=glossary_for(text)
    if 'md' in formats:
        (dist/(cfg['stem']+'.md')).write_text(markdown_with_glossary(text,definitions),encoding='utf-8')
    match=re.match(r'^---\n(.*?)\n---\n(.*)$',text,re.S)
    if not match:raise ValueError('Missing YAML frontmatter')
    meta,body=yaml.safe_load(match[1]),match[2]
    if set(formats)=={'md'}:return
    cutoff=str(meta['source_cutoff'])
    corebody=body.split('<!-- SOURCES -->',1)[0]
    soup=BeautifulSoup(MarkdownIt('default',{'html':True}).enable('table').render(body),'html.parser')
    # A single source manuscript; the cover replaces the repeated main heading.
    h1=soup.find('h1')
    if h1:h1.decompose()
    first=soup.find('p')
    if first and ('IndelibleVivi' in first.get_text() or 'Faye & Cove' in first.get_text()):first.decompose()
    # The Markdown source appendix is compact and readable. Print uses a linked index.
    for h in list(soup.find_all('h2')):
        if h.get_text() in {'来源索引','关于这一版'}:
            node=h
            while node:
                nxt=node.next_sibling;node.extract();node=nxt
            break
    for a in soup.find_all('a'):
        if re.fullmatch(r'S\d{2,3}',a.get_text()):a['class']=['source-ref']
        href=a.get('href','')
        if href.startswith('../docs/glossary.md#'):
            a['href']='#glossary-'+href.split('#',1)[1]
        elif href == '../docs/glossary.md' and definitions:
            a['href']='#glossary'
    # SVGs add a second visual way in, without removing the adjacent MD table.
    for comment in list(soup.find_all(string=lambda t:isinstance(t,Comment))):
        m=re.search(r'figure:\s*([\w-]+)',str(comment))
        if not m:comment.extract();continue
        key=m[1];fig=tag(soup,'figure',{'class':'figure'})
        fig.append(BeautifulSoup((ROOT/'assets'/f'{key}.svg').read_text(), 'html.parser').svg)
        caption=tag(soup,'figcaption');caption.append(tag(soup,'span',{'class':'fig-no'},'FIG.'))
        caption.append(FIGCAP[key]);fig.append(caption);comment.replace_with(fig)
    for table in soup.find_all('table'):
        content=table.get_text()
        if '2026-10-14' in content:table['class']=['date-table']
        if len(table.find_all('tr'))>8:table['class']=table.get('class',[])+['compact']
        elif len(table.find_all('tr'))<=7:table['class']=table.get('class',[])+['keep-table']
    # Meaningful wrappers preserve heading-following-text while allowing long sections to flow.
    content=BeautifulSoup('<main></main>','html.parser')
    main=content.main;opening=tag(content,'section',{'class':'opening'});main.append(opening)
    section=opening;heads=[];count=0
    for node in list(soup.contents):
        if getattr(node,'name',None)=='h2':
            count+=1
            title=re.sub(r'^\d+\s*/\s*','',node.get_text())
            ident=f'chapter-{count:02d}'
            heads.append((ident,title,f'{count:02d}'))
            cls='chapter'+(' first' if count==1 else '')+(' jump-page' if count in cfg['breaks'] else '')
            section=tag(content,'section',{'class':cls,'id':ident});main.append(section)
            header=tag(content,'header',{'class':'chapter-head'})
            strip=tag(content,'div',{'class':'chapter-meta'})
            strip.append(tag(content,'span',{'class':'chapter-number'},f'{count:02d}'))
            strip.append(tag(content,'span',{'class':'chapter-type'},cfg['types'][count-1]))
            header.append(strip);header.append(tag(content,'h2',{},title));section.append(header)
        else:section.append(node.extract())
    used=sorted(set(re.findall(r'\[(S\d{2,3})\]',corebody)))
    if definitions:
        glossary=tag(content,'section',{'class':'chapter','id':'glossary'})
        glossary.append(tag(content,'h2',text='术语小词表'))
        for key,label,definition in definitions:
            glossary.append(tag(content,'h3',{'id':'glossary-'+key},label))
            rendered=BeautifulSoup(MarkdownIt('commonmark').render(definition),'html.parser')
            glossary.append(rendered.p)
        main.append(glossary)
    bibliography=tag(content,'section',{'class':'sources','id':'sources'})
    bibliography.append(tag(content,'h2',{},'来源索引'))
    bibliography.append(tag(content,'p',{'class':'source-note'},'本版沿用来源记录中的核验日期与范围；重新构建不代表重新核验。资料核验不等于账户或模型实测。'))
    listing=tag(content,'div',{'class':'source-list'})
    columns=[tag(content,'div',{'class':'source-col'}) for _ in range(2)]
    for c in columns: listing.append(c)
    split=(len(used)+1)//2
    for entry_index,key in enumerate(used):
        item=sources[key];entry=tag(content,'div',{'class':'source-entry','id':key})
        entry.append(tag(content,'span',{'class':'source-id'},key))
        entry.append(tag(content,'a',{'href':item['url']},item['title']))
        entry.append(tag(content,'small',{},urlparse(item['url']).hostname))
        columns[0 if entry_index < split else 1].append(entry)
    bibliography.append(listing);main.append(bibliography)
    col=tag(content,'section',{'class':'colophon','id':'colophon'})
    col.append(tag(content,'div',{'class':'closing-title'},'关于这一版'))
    col.append(tag(content,'p',{'class':'smallprint'},'面向个人使用的独立参考资料，不是 Cloudflare 官方出版物。产品事实保留来源，场景与判断属于编辑分析。本次未进行账户操作或云端部署。'))
    profile=tag(content,'div',{'class':'author-line'});profile.append('GitHub · ');profile.append(tag(content,'a',{'href':'https://github.com/IndelibleVivi'},'github.com/IndelibleVivi'));col.append(profile)
    col.append(tag(content,'div',{'class':'signature'},'made by Faye & Cove'))
    main.append(col)
    art=(ROOT/'assets/motifs/cat-sunrise.svg').read_text()
    cover=f'''<section class="cover {cfg['kind']}" aria-label="封面">
    <div class="cover-top"><span class="publisher">INDEPENDENT REFERENCE</span><span class="cover-series">CLOUDFLARE / FIELD EDITIONS</span></div>
    <div class="cover-kicker">{cfg['kicker']}</div><div class="cover-brand">CF Fieldbook</div>
    <div class="cover-title">{cfg['cover']}</div><div class="cover-subtitle">{cfg['deck']}</div>
    <div class="cover-art">{art}</div><div class="cover-bottom"><div><b>{html.escape(edition)}</b><br>资料截至 {html.escape(cutoff)}</div><div class="edition-note">BOOK {cfg['number']} · 本地候选版次<br>独立参考 · 可点击来源索引</div></div></section>'''
    toc='<nav class="toc" id="contents" aria-label="目录"><div class="eyebrow">CONTENTS / READING PATH</div><h2>从这里翻开</h2><p class="toc-intro">'+cfg['toc']+'</p><ol>'
    for ident,title,number in heads:
        toc+=f'<li><a href="#{ident}"><span class="toc-no">{number}</span>{html.escape(title)}</a></li>'
    if definitions:toc+='<li><a href="#glossary"><span class="toc-no">G</span>术语小词表</a></li>'
    toc+='<li><a href="#sources"><span class="toc-no">S</span>来源索引与署名</a></li></ol><p class="toc-foot">来源编号可点击。开放状态与生效日期按资料截止日记录；实施代码与详细状态约束另放仓库的技术参考。</p></nav>'
    css=(ROOT/'styles/report.css').read_text()
    final=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(meta['title'])} · Faye &amp; Cove</title><meta name="author" content="Faye &amp; Cove"><meta name="description" content="{html.escape(meta['subtitle'])}"><style>{css}</style></head><body class="{cfg['kind']}"><div class="document-name">{cfg['short']}</div>{cover}<div class="screen-nav"><b>{cfg['short']}</b><span><a href="#contents">目录</a><a href="#sources">来源</a><a href="{cfg['partner']}">相关读物</a></span></div>{toc}{content}</body></html>'''
    target=dist/cfg['stem']
    if 'html' in formats:
        target.with_suffix('.html').write_text(final,encoding='utf-8')
    if 'pdf' in formats:
        from weasyprint import HTML
        # PDF is portable: repository-relative links must not leak a build-machine file URI.
        print_soup=BeautifulSoup(final, 'html.parser')
        for link in print_soup.find_all('a', href=True):
            href=link['href']
            if not href.startswith('#') and not urlparse(href).scheme:
                del link['href']
        doc=HTML(string=str(print_soup),base_url=str(ROOT),url_fetcher=no_network_fetcher)
        doc.write_pdf(str(target.with_suffix('.pdf')),pdf_tags=True)
    print('Built',target.name,','.join(formats),flush=True)


def main():
    global ROOT
    parser=argparse.ArgumentParser(description='Internal frozen-edition renderer; use tools/editions.py freeze/build.')
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--edition',required=True)
    parser.add_argument('--formats',nargs='+',choices=['md','html','pdf'],required=True)
    args=parser.parse_args()
    ROOT=args.snapshot.resolve()
    # The only rendering destination is this frozen candidate's adjacent output directory.
    if ROOT.name!='inputs' or args.output.resolve()!=ROOT.parent/'outputs':
        parser.error('renderer requires a frozen inputs/ and sibling outputs/')
    from editions import verify_inputs
    manifest=verify_inputs(ROOT.parent)
    if manifest['id']!=args.edition:parser.error('edition identity mismatch')
    args.output.mkdir(exist_ok=False)
    sources={s['id']:s for s in json.loads((ROOT/'catalog/sources.json').read_text())}
    for cfg in DOCS:render_one(cfg,sources,args.output,args.edition,args.formats)

if __name__=='__main__':main()
