#!/usr/bin/env python3
"""Render local Mermaid definitions to SVG without remote requests.

Uses the local npm dependency locked in package-lock.json and Mermaid's render API.
"""
from __future__ import annotations
import argparse, hashlib, json, mimetypes, re, sys, tempfile
from pathlib import Path
from urllib.parse import urlparse, unquote
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
NS='http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
def sha(b: bytes)->str:return hashlib.sha256(b).hexdigest()

def normalize(svg:str, source_hash:str)->str:
    node=ET.fromstring(svg)
    if node.tag != f'{{{NS}}}svg':raise ValueError('Not SVG')
    for child in node.iter():
        if child.tag.rsplit('}',1)[-1] in {'script','foreignObject'}:
            raise ValueError('Unexpected active/HTML SVG content')
    # Mermaid splits plain labels into nested word tspans. Collapse only
    # identically styled word spans into one line for Cairo/SVG print parity.
    # Text and line coordinates remain those produced by Mermaid.
    for line in node.iter(f'{{{NS}}}tspan'):
        if line.attrib.get('class') == 'text-outer-tspan' and len(line):
            plain=''.join(line.itertext())
            for child in list(line):
                if child.attrib.get('font-weight','normal')!='normal' or child.attrib.get('font-style','normal')!='normal':
                    raise ValueError('Styled word spans need explicit export review')
                line.remove(child)
            line.text=plain
    v=list(map(float,node.attrib['viewBox'].split()))
    bg=ET.Element(f'{{{NS}}}rect',{'x':str(v[0]),'y':str(v[1]),'width':str(v[2]),'height':str(v[3]),'fill':'#FFFFFF','aria-hidden':'true'})
    node.insert(0,bg)
    meta=ET.Element(f'{{{NS}}}metadata');meta.text='Mermaid source sha256: '+source_hash;node.append(meta)
    return ET.tostring(node,encoding='unicode')+'\n'

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--module-file',type=Path)
    ap.add_argument('--browser',type=Path)
    ap.add_argument('--check',action='store_true',help='Re-render in memory; never overwrite outputs')
    args=ap.parse_args();root=args.root.resolve()
    bundle_name='npm-mermaid'
    module=(args.module_file or root/'node_modules/mermaid/dist/mermaid.esm.min.mjs').resolve()
    if not module.is_file():ap.error('Run npm ci --ignore-scripts, or pass --module-file')
    base=module.parent;export='default'
    package=base.parent/'package.json'
    version=json.loads(package.read_text()).get('version','unknown') if package.is_file() else 'unknown'
    expected=json.loads((root/'package.json').read_text())['devDependencies']['mermaid']
    if version!=expected:ap.error(f'Mermaid version {version}; expected {expected}. Review an upgrade explicitly.')
    from playwright.sync_api import sync_playwright
    confpath=root/'diagrams/mermaid.config.json';conf=json.loads(confpath.read_text())
    diagrams=json.loads((root/'diagrams/index.json').read_text());outputs={};loaded={};blocked=[]
    with sync_playwright() as p:
        opts={'headless':True}
        if args.browser:opts.update(executable_path=str(args.browser),args=['--no-sandbox'])
        browser=p.chromium.launch(**opts)
        page=browser.new_page(viewport={'width':1600,'height':1200})
        def route(route):
            u=urlparse(route.request.url);rel=unquote(u.path).lstrip('/')
            file=(base/rel).resolve()
            if u.hostname=='fieldbook.invalid' and file.is_relative_to(base.resolve()) and file.is_file() and file.suffix in {'.js','.mjs','.css','.map'}:
                data=file.read_bytes();loaded[rel]=sha(data)
                route.fulfill(status=200,body=data,headers={'Content-Type':mimetypes.guess_type(file.name)[0] or 'application/javascript','Access-Control-Allow-Origin':'*'})
            else:
                blocked.append(u.scheme+'://'+str(u.hostname)+u.path)
                route.fulfill(status=404,body='offline renderer: unavailable',headers={'Access-Control-Allow-Origin':'*'})
        page.route('**/*',route)
        page.set_content('<!doctype html><html><head><meta charset="utf-8"></head><body></body></html>')
        page.evaluate('''async ({name,key})=>{const mod=await import('https://fieldbook.invalid/'+name);window.fbMermaid=key==='default'?mod.default:mod[key].default;}''',{'name':module.name,'key':export})
        for d in diagrams:
            raw=(root/d['source']).read_bytes();h=sha(raw);cfg={**conf,'deterministicIDSeed':d['id']}
            svg=page.evaluate('''async ({source,cfg,id})=>{fbMermaid.initialize(cfg);return (await fbMermaid.render('fb_'+id.replaceAll('-','_'),source)).svg;}''',{'source':raw.decode(),'cfg':cfg,'id':d['id']})
            outputs[d['output']]=normalize(svg,h).encode()
            d.update(source_sha256=h,svg_sha256=sha(outputs[d['output']]))
        browser.close()
    if blocked:raise RuntimeError('Unexpected module requests: '+repr(sorted(set(blocked))))
    manifest={'schema':'fieldbook.diagrams/1','engine':{'name':'mermaid','version':version,'loader':bundle_name,'module_sha256':sha(module.read_bytes())},'config':'diagrams/mermaid.config.json','config_sha256':sha(confpath.read_bytes()),'font_family':conf['fontFamily'],'font_files_distributed':False,'local_module_hashes':loaded,'diagrams':diagrams}
    if args.check:
        failed=[f for f,b in outputs.items() if not (root/f).is_file() or (root/f).read_bytes()!=b]
        if failed:print('DIFF: '+', '.join(failed));return 1
        print(f'PASS: {len(outputs)} actual Mermaid renders are byte-identical.');return 0
    for f,b in outputs.items():
        dest=root/f;dest.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=dest.parent,delete=False) as out:out.write(b);tmp=Path(out.name)
        tmp.replace(dest)
    (root/'assets/diagrams/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(f'Wrote {len(outputs)} Mermaid {version} SVGs; no remote requests or embedded font files.');return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,RuntimeError) as ex:print(str(ex),file=sys.stderr);sys.exit(1)
