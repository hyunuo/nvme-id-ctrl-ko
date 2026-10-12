"""Retry IEEE's official public listing using a browser user agent."""
import urllib.request,json,hashlib,datetime
from pathlib import Path
root=Path(__file__).resolve().parent
p=root/'source/external_manifest.json';manifest=json.loads(p.read_text(encoding='utf-8'))
for url in ['https://standards-oui.ieee.org/oui/oui.csv','https://standards-oui.ieee.org/oui.csv']:
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'text/csv,*/*'})
  raw=urllib.request.urlopen(req,timeout=25).read()
  assert b'Organization Name' in raw[:500],'Unexpected registry format'
  (root/'source/ieee_oui.csv').write_bytes(raw)
  manifest['oui']=dict(filename='source/ieee_oui.csv',url=url,sha256=hashlib.sha256(raw).hexdigest(),retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='acquired')
  print('IEEE public registry snapshot acquired:',len(raw),'bytes');break
 except Exception as e:print('Registry unavailable:',e)
p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
