#!/usr/bin/env python3
"""Read-only, offline content-index checks and maintenance queries."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse,unquote
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
STATUS={'draft','current','superseded','withdrawn','archived'}
TRACK={'maintained','edition'}

def digest(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def local_path(root:Path,value:str)->Path:
    if not isinstance(value,str) or not value or Path(value).is_absolute() or '..' in Path(value).parts:
        raise ValueError(f'not a contained relative path: {value!r}')
    p=(root/value).resolve()
    if not p.is_relative_to(root.resolve()):raise ValueError('path escapes root')
    return p

def load(root:Path)->dict:return json.loads((root/'catalog/entries.json').read_text())

def validate_entries(root:Path,catalog:dict)->list[str]:
    errors=[];entries=catalog.get('entries',[])
    if catalog.get('schema')!='fieldbook.entries/1':errors.append('unsupported entries schema')
    if not isinstance(entries,list):return errors+['entries must be an array']
    ids=[e.get('id') for e in entries];paths=[e.get('path') for e in entries]
    if len(set(ids))!=len(ids):errors.append('duplicate content ID')
    if len(set(paths))!=len(paths):errors.append('duplicate content owner path')
    for e in entries:
        ident=e.get('id','')
        if not re.fullmatch(r'[a-z][a-z0-9-]*(?:\.[a-z0-9-]+)+',ident):errors.append(f'bad ID: {ident}')
        try:
            if not local_path(root,e.get('path')).is_file():errors.append(f'{ident}: missing source file')
        except (ValueError,TypeError) as ex:errors.append(str(ex))
        if e.get('track') not in TRACK:errors.append(f'{ident}: invalid maintenance track')
        if e.get('status') not in STATUS:errors.append(f'{ident}: invalid content status')
        for key in ['depends_on','related']:
            values=e.get(key,[])
            if not isinstance(values,list) or any(not isinstance(v,str) for v in values):
                errors.append(f'{ident}: {key} must be ID strings');continue
            for value in values:
                if value not in ids:errors.append(f'{ident}: unresolved {key} {value}')
        review=e.get('review',{})
        if review.get('state') not in {'checked','inherited','needs-review','unreviewed'}:errors.append(f'{ident}: invalid review state')
        for key in ['checked_on','next_review_on']:
            value=review.get(key)
            if value is not None:
                try:date.fromisoformat(value)
                except (ValueError,TypeError):errors.append(f'{ident}: bad date {key}')
        if review.get('checked_on') and not review.get('scope'):errors.append(f'{ident}: checked date needs scope')
        for evidence in e.get('evidence',[]):
            if evidence.get('kind') not in {'prior-edition','source-reviewed','local-executed','cloud-executed','visual-reviewed'}:
                errors.append(f'{ident}: invalid evidence kind')
            try:
                if not local_path(root,evidence.get('ref')).is_file():errors.append(f'{ident}: missing evidence ref')
            except (ValueError,TypeError) as ex:errors.append(str(ex))
            if evidence.get('kind')=='cloud-executed' and not all(evidence.get(k) for k in ['run_id','observed_on','scope','data_kind']):
                errors.append(f'{ident}: cloud evidence lacks scoped receipt metadata')
    byid={e.get('id'):e for e in entries};visiting=set();done=set()
    def visit(i):
        if i in visiting:errors.append(f'dependency cycle at {i}');return
        if i in done or i not in byid:return
        visiting.add(i)
        for dep in byid[i].get('depends_on',[]):visit(dep)
        visiting.remove(i);done.add(i)
    for i in ids:visit(i)
    return errors

def impact(catalog:dict,changed:list[str])->dict:
    byid={e['id']:e for e in catalog['entries']}
    if not set(changed)<=byid.keys():raise ValueError('unknown changed ID')
    reached=set(changed);reasons={i:[] for i in changed}
    # Edition snapshots are terminals: produce erratum candidates but do not
    # propagate them as if they were mutable dependencies.
    propagate={i for i in changed if byid[i]['track']!='edition'}
    while True:
        additions={}
        for ident,e in byid.items():
            if ident in reached:continue
            causes=sorted(set(e.get('depends_on',[]))&propagate)
            if causes:additions[ident]=causes
        if not additions:break
        for ident,causes in additions.items():
            reached.add(ident);reasons[ident]=causes
            if byid[ident]['track']!='edition':propagate.add(ident)
    affected=reached-set(changed)
    maintained=sorted(i for i in affected if byid[i]['track']=='maintained' and byid[i]['status']=='current')
    editions=sorted(i for i in affected if byid[i]['track']=='edition')
    inactive=sorted(i for i in affected if byid[i]['track']=='maintained' and byid[i]['status']!='current')
    related=set()
    for i in reached:related.update(byid[i].get('related',[]))
    return {'changed':sorted(changed),'current_review_candidates':maintained,'edition_errata_candidates':editions,'inactive_candidates':inactive,'related_only':sorted(related-reached),'dependency_reasons':reasons,'note':'Candidates only. No text, dates, source facts or publications were changed.'}

def markdown_sources(text:str)->set[str]:
    """Read authored [Snn] citations, excluding code, notes and source appendices."""
    visible=[];fence=None;in_comment=False;frontmatter=False
    for number,line in enumerate(text.splitlines()):
        if number==0 and line=='---':frontmatter=True;continue
        if frontmatter:
            if line=='---':frontmatter=False
            continue
        if fence:
            if re.fullmatch(r' {0,3}'+re.escape(fence[0])+r'{'+str(fence[1])+r',}\s*',line):fence=None
            continue
        if not in_comment:
            opening=re.match(r'^ {0,3}(`{3,}|~{3,})',line)
            if opening:fence=(opening[1][0],len(opening[1]));continue
            if line.startswith(('    ','\t')):continue
        line=re.sub(r'(`+)(?!`)(.*?)\1(?!`)', '', line)
        if not in_comment and line.strip()=='<!-- SOURCES -->':break
        # Notes may span lines; a source boundary inside a note is not a boundary.
        clean='';remaining=line
        while remaining:
            if in_comment:
                end=remaining.find('-->')
                if end<0:break
                remaining=remaining[end+3:];in_comment=False
            else:
                start=remaining.find('<!--')
                if start<0:clean+=remaining;break
                clean+=remaining[:start];remaining=remaining[start+4:];in_comment=True
        if re.match(r'^ {0,3}\[S\d{2,3}\]:',clean):continue
        visible.append(clean)
    return set(re.findall(r'(?<![!\\])\[(S\d{2,3})\](?!:)', '\n'.join(visible)))

def entry_sources(root:Path,entry:dict)->set[str]:
    """Index only content owners and structured sources fields, never the bibliography."""
    if entry['path']=='catalog/sources.json':return set()
    path=local_path(root,entry['path'])
    if path.suffix=='.md':return markdown_sources(path.read_text(encoding='utf-8'))
    if path.suffix!='.json':return set()
    found=set()
    def visit(value):
        if isinstance(value,dict):
            refs=value.get('sources',[])
            if isinstance(refs,list):
                found.update(s for s in refs if isinstance(s,str) and re.fullmatch(r'S\d{2,3}',s))
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(json.loads(path.read_text(encoding='utf-8')))
    return found

def impact_source(root:Path,catalog:dict,changed:list[str])->dict:
    known={s['id'] for s in json.loads((root/'catalog/sources.json').read_text(encoding='utf-8'))}
    unknown=set(changed)-known
    if unknown:raise ValueError('unknown source ID: '+', '.join(sorted(unknown)))
    requested=set(changed);citations=[]
    for entry in catalog['entries']:
        matches=entry_sources(root,entry)&requested
        if matches:citations.append({'id':entry['id'],'path':entry['path'],'sources':sorted(matches)})
    citations.sort(key=lambda e:e['id'])
    roots=[e['id'] for e in citations]
    result=impact(catalog,roots)
    # Direct consumers need review too; ordinary impact excludes its changed roots.
    for entry in catalog['entries']:
        if entry['id'] not in roots:continue
        key='edition_errata_candidates' if entry['track']=='edition' else ('current_review_candidates' if entry['status']=='current' else 'inactive_candidates')
        result[key].append(entry['id'])
    for key in ('current_review_candidates','edition_errata_candidates','inactive_candidates'):
        result[key]=sorted(set(result[key]))
    return {'sources':sorted(requested),'direct_citations':citations,**result,
            'note':'Citation and dependency candidates only; applicability is unverified. No text, dates, project files or publications were changed.'}

def due(catalog:dict,asof:date)->list[dict]:
    result=[]
    for e in catalog['entries']:
        when=e.get('review',{}).get('next_review_on')
        if e['track']=='maintained' and e['status']=='current' and when and date.fromisoformat(when)<=asof:
            result.append({'id':e['id'],'path':e['path'],'next_review_on':when,'last_checked_on':e.get('review',{}).get('checked_on'),'scope':e.get('review',{}).get('scope')})
    return sorted(result,key=lambda e:(e['next_review_on'],e['id']))

def validate_diagrams(root:Path)->list[str]:
    errors=[];p=root/'assets/diagrams/manifest.json'
    if not p.is_file():return ['missing diagram manifest']
    m=json.loads(p.read_text())
    if digest(root/m['config'])!=m['config_sha256']:errors.append('diagram config drift')
    if m.get('font_files_distributed') is not False:errors.append('font distribution declaration missing')
    for d in m['diagrams']:
        for key,h in [('source','source_sha256'),('output','svg_sha256')]:
            p=local_path(root,d[key])
            if not p.is_file() or digest(p)!=d[h]:errors.append(f'{d["id"]}: {key} drift')
        svg=local_path(root,d['output'])
        if not svg.is_file():continue
        try:node=ET.fromstring(svg.read_text())
        except ET.ParseError:errors.append(f'{d["id"]}: invalid SVG');continue
        names=[n.tag.rsplit('}',1)[-1] for n in node.iter()]
        if 'title' not in names or 'desc' not in names:errors.append(f'{d["id"]}: title/description absent')
        if any(n in names for n in ['script','foreignObject','image']):errors.append(f'{d["id"]}: active or raster content')
        for n in node.iter():
            for key,value in n.attrib.items():
                if key.rsplit('}',1)[-1]=='href' and not value.startswith('#'):
                    errors.append(f'{d["id"]}: external href')
    return errors

def validate_example_meta(root:Path)->list[str]:
    errors=[]
    for p in (root/'examples').glob('*/example.meta.json'):
        e=json.loads(p.read_text())
        if e.get('schema')!='fieldbook.example/1':errors.append(f'{p.name}: unknown example schema')
        if e.get('default_mode')!='offline' or e.get('network_required') or e.get('credentials_required'):
            errors.append(f'{p.parent.name}: this edition must remain offline by default')
        if not e.get('check_command') or not isinstance(e['check_command'],list):errors.append(f'{p.parent.name}: command missing')
        if e.get('live_supported') is not False:errors.append(f'{p.parent.name}: live path requires independent implementation/review')
    return errors

def check(root:Path)->list[str]:
    errors=validate_entries(root,load(root))+validate_diagrams(root)+validate_example_meta(root)
    # Bound the link pass to authored repository-design documents, not arbitrary
    # private files, generated publications, or historical web URL reachability.
    paths=[root/'README.md',root/'SPEC.md',root/'AGENTS.md',root/'diagrams/README.md',root/'examples/README.md',*sorted((root/'docs').glob('*.md'))]
    for p in paths:
        if not p.is_file():errors.append(f'missing design document {p.relative_to(root)}');continue
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if urlparse(link).scheme or link.startswith('#'):continue
            target=(p.parent/unquote(link.split('#')[0])).resolve()
            if not target.is_relative_to(root.resolve()) or not target.exists():errors.append(f'{p.relative_to(root)}: bad local link {link}')
    for p in root.rglob('*'):
        if not set(p.relative_to(root).parts) & {'.venv', 'node_modules', '.build', '.git'} and p.suffix.lower() in {'.ttf','.otf','.ttc','.woff','.woff2'}:errors.append('font file in distributable tree')
    return errors

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=ROOT)
    sub=ap.add_subparsers(dest='command',required=True);sub.add_parser('check')
    im=sub.add_parser('impact');im.add_argument('ids',nargs='+')
    ims=sub.add_parser('impact-source');ims.add_argument('ids',nargs='+')
    du=sub.add_parser('due');du.add_argument('--as-of',type=date.fromisoformat,required=True)
    args=ap.parse_args();root=args.root.resolve()
    if args.command=='check':
        errors=check(root)
        if errors:print('\n'.join(errors),file=sys.stderr);return 1
        print('PASS: content index, scoped dates, dependency graph, diagram pairing, example metadata, design links.');print('Offline only: not source-fact truth, live cloud acceptance, or universal privacy scanning.');return 0
    cat=load(root);errors=validate_entries(root,cat)
    if errors:raise ValueError('\n'.join(errors))
    if args.command=='impact':obj=impact(cat,args.ids)
    elif args.command=='impact-source':obj=impact_source(root,cat,args.ids)
    else:obj=due(cat,args.as_of)
    print(json.dumps(obj,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError) as ex:print(str(ex),file=sys.stderr);sys.exit(2)
