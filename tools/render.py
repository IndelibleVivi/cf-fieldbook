#!/usr/bin/env python3
"""Build the reader editions from Markdown. Offline, no remote assets.

Family selection, cover copy, chapter configuration and product reading targets
come from `catalog/publications.json` through the shared `publications` helper;
chapter IDs come from the Markdown `<!-- chapter: -->` markers. Nothing here
hardcodes a date, a file stem or a chapter position.

Source dates are scoped per entry. Exported HTML embeds CSS and SVG, never fonts.
"""
from __future__ import annotations
import argparse
import html
import json
from pathlib import Path
import re
from urllib.parse import urlparse, unquote, quote

from bs4 import BeautifulSoup, Comment
from markdown_it import MarkdownIt
import yaml
from content import project_markdown
import publications as pub
from build_site import PUBLIC_DOCS, PUBLIC_REPOSITORY_PATHS, REPOSITORY_URL

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_SITE='https://indeliblevivi.github.io/cf-fieldbook/'
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
    # Rendering returns a projection; it must never rewrite the source manuscript.
    return '\n'.join(lines).strip()+'\n'

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
    missing=[key for key in keys if key not in definitions]
    if missing:
        raise ValueError(f'glossary links without definitions: {sorted(missing)}')
    return [(key,*definitions[key]) for key in keys]

def markdown_with_glossary(text,definitions):
    if not definitions:return text
    for key,_,_ in definitions:
        text=text.replace(f'../docs/glossary.md#{key}',f'#{key}')
    text=text.replace('](../docs/glossary.md)','](#术语小词表)')
    appendix='\n## 术语小词表\n\n'+ '\n\n'.join(
        f'### {label}\n\n{definition}' for key,label,definition in definitions)+'\n'
    return text.replace('<!-- SOURCES -->',appendix+'\n<!-- SOURCES -->',1)

def chapter_plan(collection,fam,body):
    return pub.parse_chapters(body, pub.chapter_config(fam))

def edition_stem(fam,ident):
    if fam['kind']=='report':return f"cf-{ident['token']}-{ident['date']}"
    if fam['kind']=='handbook':return f"cf-practical-handbook-{ident['date']}"
    return f"cf-clef-vs-jev-{ident['date']}"

def render_one(collection,fam,sources,dist,edition,formats):
    path=collection.entry_path(pub.source_entry(fam))
    if not path:raise ValueError(f'{fam["id"]}: missing source entry {pub.source_entry(fam)}')
    text=project_markdown(ROOT,path)
    cover=fam.get('cover',{})
    meta_match=re.match(r'^---\n(.*?)\n---\n(.*)$',text,re.S)
    if not meta_match:raise ValueError('Missing YAML frontmatter')
    meta,body=yaml.safe_load(meta_match[1]),meta_match[2]
    # Per-family source inventory: own definitions win; the frozen sources.json fills gaps.
    own={key:{'url':url,'title':title} for key,url,title in
         re.findall(r'^\[(S\d{2,3})\]:\s+(\S+)\s+"([^"]+)"\s*$', text, re.M)}
    if own:
        used=set(re.findall(r'\[(S\d{2,3})\]', text.split('<!-- SOURCES -->',1)[0]))
        missing=used-own.keys()
        if missing:
            unknown=missing-sources.keys()
            if unknown:raise ValueError(f'{fam["id"]}: unknown source IDs {sorted(unknown)}')
            own={**{k:sources[k] for k in missing},**own}
        sources=own
    else:
        text=update_sources(ROOT/path,sources,text)
    definitions=glossary_for(text)
    # Report identity (stem, date, title) is read from the manuscript, never hardcoded.
    ident=pub.report_identity(text, pub.source_entry(fam))
    stem=edition_stem(fam,ident)
    if 'md' in formats:
        (dist/(stem+'.md')).write_text(markdown_with_glossary(text,definitions),encoding='utf-8')
    if set(formats)=={'md'}:return
    cutoff=str(meta['source_cutoff'])
    corebody=body.split('<!-- SOURCES -->',1)[0]
    soup=BeautifulSoup(MarkdownIt('default',{'html':True}).enable('table').render(body),'html.parser')
    h1=soup.find('h1')
    if h1:h1.decompose()
    first=soup.find('p')
    if first and ('IndelibleVivi' in first.get_text() or 'Faye & Cove' in first.get_text()):first.decompose()
    for h in list(soup.find_all('h2')):
        if h.get_text() in {'来源索引','关于这一版'}:
            node=h
            while node:
                nxt=node.next_sibling;node.extract();node=nxt
            break
    reader_paths = {item['path'] for item in pub.entry_map(ROOT).values()} | set(PUBLIC_DOCS)
    for a in soup.find_all('a'):
        if re.fullmatch(r'S\d{2,3}',a.get_text()):a['class']=['source-ref']
        href=a.get('href','')
        if href.startswith('../docs/glossary.md#'):
            a['href']='#glossary-'+href.split('#',1)[1]
        elif href == '../docs/glossary.md' and definitions:
            a['href']='#glossary'
        elif not href.startswith(('#','http://','https://','mailto:')) and href:
            # Same-edition manuscript links become in-book anchors; every other
            # repository-relative link points at the public reading site rather
            # than leaking a build-machine file URI.
            target,frag=(href.split('#',1)+[''])[:2]
            fragment=('#'+quote(unquote(frag), safe='-')) if frag else ''
            local=(ROOT / Path(path).parent / unquote(target)).resolve()
            landing=local.relative_to(ROOT).as_posix()
            if landing == path:
                a['href']=fragment or '#contents'
            elif landing in PUBLIC_REPOSITORY_PATHS:
                a['href']=REPOSITORY_URL+quote(landing, safe='/')+fragment
            else:
                if landing in reader_paths and landing.endswith('.md'):
                    landing=str(Path(landing).with_suffix('.html'))
                a['href']=PUBLIC_SITE+quote(landing, safe='/')+fragment
    for image in list(soup.find_all('img')):
        local=(ROOT / Path(path).parent / unquote(image['src'])).resolve()
        local.relative_to(ROOT)
        if local.suffix != '.svg':
            raise ValueError('Publication body images currently require local SVG')
        figure=tag(soup,'figure',{'class':'figure'})
        figure.append(BeautifulSoup(local.read_text(), 'html.parser').svg)
        figure.append(tag(soup,'figcaption',{},image.get('alt','')))
        if image.parent.name == 'p' and len(image.parent.contents)==1:
            image.parent.replace_with(figure)
        else:
            image.replace_with(figure)
    for comment in list(soup.find_all(string=lambda t:isinstance(t,Comment))):
        m=re.search(r'figure:\s*([\w-]+)',str(comment))
        if not m:comment.extract();continue
        key=m[1]
        fig=tag(soup,'figure',{'class':'figure'})
        fig.append(BeautifulSoup((ROOT/'assets'/f'{key}.svg').read_text(), 'html.parser').svg)
        caption=tag(soup,'figcaption');caption.append(tag(soup,'span',{'class':'fig-no'},'FIG.'))
        caption.append(FIGCAP[key]);fig.append(caption);comment.replace_with(fig)
    for table in soup.find_all('table'):
        content=table.get_text()
        if '2026-10-14' in content:table['class']=['date-table']
        if len(table.find_all('tr'))>8:table['class']=table.get('class',[])+['compact']
        elif len(table.find_all('tr'))<=7:table['class']=table.get('class',[])+['keep-table']
    plan=chapter_plan(collection,fam,body)
    # Meaningful wrappers preserve heading-following-text while allowing long sections to flow.
    content=BeautifulSoup('<main></main>','html.parser')
    main=content.main;opening=tag(content,'section',{'class':'opening'});main.append(opening)
    section=opening;heads=[];count=0
    for node in list(soup.contents):
        if getattr(node,'name',None)=='h2':
            if count>=len(plan):raise ValueError(f'{fam["id"]}: more h2 chapters than markers')
            chapter=plan[count];count+=1
            label=chapter['number'] or f'{count:02d}'
            heads.append((chapter['id'],chapter['title'],label))
            cls='chapter'+(' first' if count==1 else '')
            section=tag(content,'section',{'class':cls,'id':chapter['id']});main.append(section)
            header=tag(content,'header',{'class':'chapter-head'})
            strip=tag(content,'div',{'class':'chapter-meta'})
            strip.append(tag(content,'span',{'class':'chapter-number'},label))
            strip.append(tag(content,'span',{'class':'chapter-type'},chapter['type']))
            header.append(strip);header.append(tag(content,'h2',{},chapter['title']));section.append(header)
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
    if fam.get('front_matter', {}).get('update_note'):
        col.append(tag(content,'p',{'class':'smallprint'},fam['front_matter']['update_note']))
    profile=tag(content,'div',{'class':'author-line'});profile.append('GitHub · ');profile.append(tag(content,'a',{'href':'https://github.com/IndelibleVivi'},'github.com/IndelibleVivi'));col.append(profile)
    col.append(tag(content,'div',{'class':'signature'},'made by Faye & Cove'))
    main.append(col)
    # The version/update page lives on the public reading site; the edition footer
    # carries a light edition line for print.
    update_url=f'{PUBLIC_SITE}publications-{fam["id"]}.html'
    footer=tag(content,'footer',{'class':'edition-footer'})
    footer.append(tag(content,'span',{'class':'edition-foot-id'},f'{cover.get("short",fam["label"])} · {edition}'))
    links=tag(content,'span',{'class':'edition-foot-links'})
    links.append(tag(content,'a',{'href':PUBLIC_SITE+str(Path(path).with_suffix('.html'))},'当前阅读 →'))
    links.append(' · ')
    links.append(tag(content,'a',{'href':update_url},'本册版本与更新页 →'))
    footer.append(links)
    main.append(footer)
    art=(ROOT/'assets/motifs/cat-sunrise.svg').read_text()
    cover_html=f'''<section class="cover {fam['kind']}" aria-label="封面">
    <div class="cover-top"><span class="publisher">{html.escape(cover.get('publisher','INDEPENDENT REFERENCE'))}</span><span class="cover-series">{html.escape(cover.get('series','CLOUDFLARE / FIELD EDITIONS'))}</span></div>
    <div class="cover-kicker">{html.escape(cover.get('kicker',''))}</div><div class="cover-brand">CF Fieldbook</div>
    <div class="cover-title">{cover.get('title',html.escape(fam['label']))}</div><div class="cover-subtitle">{cover.get('deck','')}</div>
    <div class="cover-art">{art}</div><div class="cover-bottom"><div><b>{html.escape(edition)}</b><br>资料截至 {html.escape(cutoff)}</div><div class="edition-note">BOOK {html.escape(cover.get('book',''))} · 本地候选版次<br>独立参考 · <a class="cover-update" href="{update_url}">本册版本与更新页 →</a></div></div></section>'''
    toc='<nav class="toc" id="contents" aria-label="目录"><div class="eyebrow">CONTENTS / READING PATH</div><h2>从这里翻开</h2><p class="toc-intro">'+cover.get('toc_intro','')+'</p><ol>'
    for anchor,title,label in heads:
        toc+=f'<li><a href="#{anchor}"><span class="toc-no">{label}</span>{html.escape(title)}</a></li>'
    if definitions:toc+='<li><a href="#glossary"><span class="toc-no">G</span>术语小词表</a></li>'
    toc+='<li><a href="#sources"><span class="toc-no">S</span>来源索引与署名</a></li></ol><p class="toc-foot">来源编号可点击。开放状态与生效日期按资料截止日记录；实施代码与详细状态约束另放仓库的技术参考。</p></nav>'
    css=(ROOT/'styles/report.css').read_text()
    final=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(str(meta['title']))} · Faye &amp; Cove</title><meta name="author" content="Faye &amp; Cove"><meta name="description" content="{html.escape(str(meta['subtitle']))}"><style>{css}</style></head><body class="{fam['kind']}"><div class="document-name">{html.escape(cover.get('short',fam['label']))}</div><span class="document-edition">{html.escape(edition)}</span>{cover_html}<div class="screen-nav"><b>{html.escape(cover.get('short',fam['label']))}</b><span><a href="#contents">目录</a><a href="#sources">来源</a></span></div>{toc}{content}</body></html>'''
    target=dist/stem
    if 'html' in formats:
        target.with_suffix('.html').write_text(final,encoding='utf-8')
    if 'pdf' in formats:
        from weasyprint import HTML
        # Every link is already an in-book anchor or a public https URL; no
        # repository-relative href survives, so no file URI can leak.
        doc=HTML(string=final,base_url=str(ROOT),url_fetcher=no_network_fetcher)
        doc.write_pdf(str(target.with_suffix('.pdf')),pdf_tags=True)
    print('Built',target.name,','.join(formats),flush=True)

def main():
    global ROOT
    parser=argparse.ArgumentParser(description='Internal frozen-edition renderer; use tools/editions.py freeze/build.')
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--edition',required=True)
    parser.add_argument('--family',default=None)
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
    data=pub.load(ROOT)
    collection=pub.Collection(ROOT,data)
    key=args.family or data.get('default_family')
    fam=collection.family(key)
    render_one(collection,fam,sources,args.output,args.edition,args.formats)

if __name__=='__main__':main()
