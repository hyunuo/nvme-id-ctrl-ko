"""Authoritative catalog migration and deterministic compilation (stdlib only)."""
import copy,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def canonical(text):return re.sub(r'PS\d+', 'PS{index}', text)
def migrate():
    path=ROOT/'source/catalog.json'
    if path.exists():raise SystemExit('Catalog already exists; edit it instead of repeating migration.')
    data=json.loads((ROOT/'content.json').read_text(encoding='utf-8'));conditions={};excerpts={};coverage=[]
    def excerpt(text,source,owner,kind):
        sid='src-'+digest([source['doc'],source['pdf_page'],owner,text])[:20]
        if sid not in excerpts:
            excerpts[sid]=dict(id=sid,text=text,source={k:v for k,v in source.items() if k!='english'},owner=owner,kind=kind,status='미검토',reason='원문과의 대응 등록; 의미 대조는 별도 확인')
        return sid
    for f in data['fields']:
        f['definition_id']='def-'+f['id'];f['excerpt_ids']=[]
        for doc,text in [('base',f['english']),('nvm',f.get('nvm_english',''))]:
            if not text:continue
            source=next(s for s in f['sources'] if s['doc']==doc)
            # Each sentence retains a link to its enclosing field paragraph.
            for i,part in enumerate(re.split(r'(?<=[.!?])\s+(?=[A-Z])',text)):
                f['excerpt_ids'].append(excerpt(part,source,f['id']+':paragraph:'+str(i),'정의'))
        for b in f['bits']:
            b['id']='bit-'+f['id']+'-'+b['range'].replace(':','-')
            b['excerpt_ids']=[excerpt(b['english'],b['source'],b['id'],'정의')]
        for i,n in enumerate(f.get('interpretation_notes',[])):n['id']='guide-'+f['id']+'-'+digest(n['text'])[:12]
        bindings=[]
        for r in f.pop('rules'):
            signature=[r.get('standard','nvme'),canonical(r['condition']),canonical(r['observe']),canonical(r['expected']),r['level']]
            cid='check-'+digest(signature)[:20]
            if cid not in conditions:
                c=copy.deepcopy(r);c.update(id=cid,condition=signature[1],observe=signature[2],expected=signature[3],fields=[],sources=[],excerpt_ids=[],exceptions='개별 조건·원문에 명시된 예외를 확인합니다.',content_status='해석 확인 필요',profile_scope=r.get('profile_scope','해당 필드의 controller·transport 적용 조건'),legacy_ids=[])
                conditions[cid]=c
            c=conditions[cid];c['fields'].append(f['id']);c['legacy_ids'].append(r['id'])
            for s in r['sources']:
                citation={k:v for k,v in s.items() if k!='english'}
                if citation not in c['sources']:c['sources'].append(citation)
            c['excerpt_ids']+=f['excerpt_ids']+[x for b in f['bits'] for x in b.get('excerpt_ids',[])]
            bindings.append(dict(condition_id=cid,instance=f['id'] if 'psd_index' in f else '',legacy_id=r['id']))
        f['check_bindings']=bindings;f['content_status']='원문 불일치' if f['notes'] else '외부 근거 필요' if f['external'] else '해석 확인 필요'
        if f['overview_status']=='별도 조건 없음':f['overview_status']='등록된 조건 없음'
        coverage.append(dict(field=f['id'],definition_id=f['definition_id'],excerpt_ids=f['excerpt_ids'],bit_ids=[b['id'] for b in f['bits']],check_ids=list(dict.fromkeys(b['condition_id'] for b in bindings)),status=f['content_status'],disposition='대응 등록',reason='조건 미등록은 조건이 없다는 확인과 구분합니다.'))
    for b in data['psd']:
        b['definition_id']='psd-bit-'+b['id'];b['excerpt_ids']=[excerpt(b['english'],b['source'],b['definition_id'],'정의')]
    for n in data['references']:
        n['excerpt_ids']=[]
        for s in n['sources']:
            if s.get('english'):n['excerpt_ids'].append(excerpt(s['english'],s,n['id'],'관련 규정'))
    # Capture Figure 312 footnotes independently rather than silently losing them.
    pages=json.loads((ROOT/'source/base_pages.json').read_text(encoding='utf-8'))
    footnotes=[]
    for pg in pages[320:354]:
        t=pg['text'];m=re.search(r'(?im)^Notes?\s*:',t)
        if m:
            src=dict(doc='base',section='5.1.13.2.1',figure=312,pdf_page=pg['pdf_page'],page=pg['pdf_page']-22)
            footnotes.append(excerpt(t[m.start():],src,'figure312-footnotes-'+str(pg['pdf_page']),'적용 조건·예외'))
    for c in conditions.values():
        c['fields']=list(dict.fromkeys(c['fields']));c['excerpt_ids']=list(dict.fromkeys(c['excerpt_ids']))
    data.update(schema_version=2,conditions=list(conditions.values()),excerpts=list(excerpts.values()),coverage=coverage,footnote_excerpt_ids=footnotes,revision_history=[],legacy_authoring='Python 편집 모듈은 이관 전 기록으로만 보관합니다.')
    for f in data['fields']:
        for e in f['edges']:e['id']='rel-'+digest([f['id'],e['target'],e['type']])[:20]
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Migrated',len(conditions),'unique conditions,',len(excerpts),'source items.')
def compile_catalog(catalog=None):
    d=copy.deepcopy(catalog) if catalog is not None else json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'));assert d['schema_version']==2
    cond={c['id']:c for c in d['conditions']};excerpts={e['id']:e for e in d['excerpts']}
    assert len(cond)==len(d['conditions']) and len(excerpts)==len(d['excerpts']),'Duplicate stable ID'
    assert len({c['field'] for c in d['coverage']})==len(d['fields'])
    for c in cond.values():
        assert all(c.get(k) for k in ['condition','observe','expected','exceptions','level','profile_scope','content_status'])
        assert c['content_status'] in ['미검토','원문 대조 완료','해석 확인 필요','원문 불일치','외부 근거 필요']
    for c in cond.values():
        assert c['excerpt_ids'] and all(e in excerpts for e in c['excerpt_ids']),c['id']
        c['revision']=digest([ {k:c[k] for k in ['condition','observe','expected','exceptions','profile_scope','level','standard','check_kind']},sorted(c['sources'],key=digest),sorted((e,excerpts[e]['text']) for e in c['excerpt_ids']),sorted({d['documents'][s['doc']]['sha256'] for s in c['sources']}) ])
    for f in d['fields']:
        f['rules']=[]
        for b in f['check_bindings']:
            c=copy.deepcopy(cond[b['condition_id']]);c['canonical_id']=c['id'];c['instance']=b['instance'];c['id']=c['id']+('@'+b['instance'] if b['instance'] else '')
            if 'psd_index' in f:
                for key in ['condition','observe','expected']:c[key]=c[key].replace('{index}',str(f['psd_index']))
                c['field_applicability']=f"NPSS≥{f['psd_index']}인 지원 power state"+(' / OCP PCIe DSSD 적용' if c['standard']=='ocp' else '')
            f['rules'].append(c)
    d['catalog_revision']=digest(d['conditions'])
    d['coverage_summary']=dict(registered=len(d['coverage']),field_count=len(d['fields']),confirmed=sum(x['status']=='원문 대조 완료' for x in d['coverage']),source_items=len(d['excerpts']),source_confirmed=sum(x['status']=='원문 대조 완료' for x in d['excerpts']),unique_conditions=len(cond),instances=len({r['id'] for f in d['fields'] for r in f['rules']}),field_links=sum(len(f['rules']) for f in d['fields']))
    return d
if __name__=='__main__':migrate()
