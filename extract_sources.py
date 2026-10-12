"""Extract version-pinned Identify tables and source pages. Requires pdfplumber."""
import json, re, hashlib
from pathlib import Path
import pdfplumber
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'source'
OUT.mkdir(exist_ok=True)
FILES = {'base': next(ROOT.glob('*Base*.pdf')), 'nvm': next(ROOT.glob('*NVM-Command*.pdf'))}
fields, psd = [], []
old=json.loads((OUT/'extracted.json').read_text(encoding='utf-8')) if (OUT/'extracted.json').exists() else {}
hashes={k:hashlib.sha256(f.read_bytes()).hexdigest() for k,f in FILES.items()}
reuse={k:old.get('documents',{}).get(k,{}).get('sha256')==h for k,h in hashes.items()}

def flat(row):
    return [str(c).strip() for c in row if c is not None and str(c).strip()]

def source(doc, page, figure, section):
    return dict(doc=doc, pdf_page=page, page=page-22 if doc=='base' else page,
                figure=figure, section=section)

def clean(t):
    return re.sub(r'\s+', ' ', t).strip()

def name(t):
    m = re.match(r'(.+?)\s*\(([A-Za-z0-9_]+)\)\s*(?::|$)', clean(t))
    return (m[2], m[1]) if m else (None, clean(t).split(':')[0])

with pdfplumber.open(FILES['base']) as pdf:
    current = None
    for n in range(321, 354):
        page = pdf.pages[n-1]
        tables = page.find_tables()
        starts=[]
        if n <= 350:
            main=tables[0]
            skip = 1 if 'Bytes' in flat(main.extract()[0]) else 0
            for row, geometry in zip(main.extract()[skip:], main.rows[skip:]):
                cells=flat(row)
                if not cells: continue
                first=next((j for j,c in enumerate(row) if c and c.strip()), 999)
                if first<3 and re.fullmatch(r'\d+(?::\d+)?',cells[0]):
                    bounds=list(map(int,cells[0].split(':')))
                    hi,lo=(bounds[0],bounds[-1])
                    desc=cells[-1]
                    key,en=name(desc)
                    if not key: key=f'RESERVED_{lo}' if 'Reserved' in desc else f'PSD_RANGE_{lo}'
                    current=dict(id=key,name=en,start=lo,end=hi,availability=cells[1:-1],
                                 english=desc,sources=[source('base',n,312,'5.1.13.2.1')],bits=[])
                    fields.append(current)
                    starts.append((geometry.bbox[1],current))
                elif first>=12 and current:
                    current['english']+='\n'+' '.join(cells)
                    s=source('base',n,312,'5.1.13.2.1')
                    if s not in current['sources']:current['sources'].append(s)
                    numeric=next((j for j,c in enumerate(row) if j>=12 and c and re.fullmatch(r'\d+(?::\d+)?',c.strip())),None)
                    if numeric is not None:
                        current['bits'].append(dict(range=row[numeric].strip(),english=' '.join(flat(row[numeric+1:])),source=s))
            # Independent nested bit tables have reliable columns, unlike their containing text.
            for table in tables[1:]:
                rows=table.extract()
                if 'Bits' not in flat(rows[0]):continue
                if n==350 and table.bbox[1]>main.bbox[3]:continue
                owner=next((f for y,f in reversed(starts) if y<=table.bbox[1]),current)
                if owner:
                    for row in rows[1:]:
                        cells=flat(row)
                        if cells and re.fullmatch(r'\d+(?::\d+)?',cells[0]):
                            owner['bits'].append(dict(range=cells[0],english=' '.join(cells[1:]),
                                                      source=source('base',n,312,'5.1.13.2.1')))
        if n>=350:
            for table in tables:
                rows=table.extract()
                if 'Bits' not in flat(rows[0]):continue
                if n==350 and table.bbox[1]<=tables[0].bbox[3]:continue
                for row in rows[1:]:
                    cells=flat(row)
                    if cells and re.fullmatch(r'\d+(?::\d+)?',cells[0]):
                        key,en=name(' '.join(cells[1:]))
                        psd.append(dict(id=key or 'PSD_RESERVED_'+cells[0].replace(':','_'),name=en,
                                        range=cells[0],english=' '.join(cells[1:]),
                                        source=source('base',n,313,'5.1.13.2.1')))
    # Capture reference sections from the supplied PDF, not third-party interpretations.
    base_pages=json.loads((OUT/'base_pages.json').read_text(encoding='utf-8')) if reuse['base'] and (OUT/'base_pages.json').exists() else [dict(pdf_page=i+1,page=i-21,text=p.extract_text()) for i,p in enumerate(PdfReader(FILES['base']).pages)]
with pdfplumber.open(FILES['nvm']) as pdf:
    for n in [91,92]:
        for row in pdf.pages[n-1].extract_tables()[0][1:]:
            cells=flat(row)
            if not cells or not re.fullmatch(r'\d+:\d+',cells[0]):continue
            key,en=name(cells[-1])
            f=next(f for f in fields if f['id']==key)
            f['nvm_english']=cells[-1]
            f['sources'].append(source('nvm',n,117,'4.1.5.2'))
    nvm_pages=json.loads((OUT/'nvm_pages.json').read_text(encoding='utf-8')) if reuse['nvm'] and (OUT/'nvm_pages.json').exists() else [dict(pdf_page=i+1,page=i+1,text=p.extract_text()) for i,p in enumerate(PdfReader(FILES['nvm']).pages)]
template=next(f for f in fields if f['id']=='PSD2')
for i in range(3,31):
    fields.append(dict(template,id=f'PSD{i}',name=f'Power State {i} Descriptor',start=2048+32*i,end=2079+32*i,
                       english=f'Power State {i} Descriptor: Repeated 32-byte structure; see Figure 313. Derived from the ellipsis in Figure 312.',bits=[]))
fields.sort(key=lambda f:f['start'])
for f in fields:
    unique={b['range']:b for b in f['bits']}
    f['bits']=list(unique.values())
data=dict(fields=fields,psd=psd,documents={k:dict(filename=f.name,sha256=hashes[k]) for k,f in FILES.items()})
(OUT/'extracted.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
for doc,pages in [('base',base_pages),('nvm',nvm_pages)]:
    (OUT/(doc+'_pages.json')).write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
(OUT/'inventory.txt').write_text('\n'.join(f"{f['start']:4}:{f['end']:4} {f['id']} {f['name']} [{','.join(f['availability'])}]\n"+'\n'.join('  '+b['range']+' '+clean(b['english']) for b in f['bits']) for f in fields)+'\nPSD\n'+'\n'.join(b['range']+' '+b['id']+' '+b['english'] for b in psd),encoding='utf-8')
print(f'Extracted {len(fields)} byte ranges, {sum(len(f["bits"]) for f in fields)} bit ranges, {len(psd)} PSD bit ranges')
