"""Acquire pinned official references; never replace an existing PDF silently."""
import hashlib,json,urllib.request,datetime
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parent
FILES={
 'pcie':('PCIe-Transport-1.1.pdf','1.1','https://nvmexpress.org/wp-content/uploads/NVM-Express-PCI-Express-Transport-Specification-Revision-1.1-2024.08.05-Ratified.pdf'),
 'mi20':('NVMe-MI-2.0.pdf','2.0','https://nvmexpress.org/wp-content/uploads/NVM-Express-Management-Interface-Specification-Revision-2.0-2024.08.05-Ratified.pdf'),
 'mi12d':('NVMe-MI-1.2d.pdf','1.2d','https://nvmexpress.org/wp-content/uploads/NVM-Express-Management-Interface-Specification-1.2d-2024.01.10-Ratified.pdf'),
 'ieee':('IEEE-EUI-guidelines.pdf','snapshot','https://standards.ieee.org/wp-content/uploads/import/documents/tutorials/eui.pdf'),
}
manifest={}
for key,(filename,version,url) in FILES.items():
 p=ROOT/filename
 try:
  if not p.exists():
   request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
   raw=urllib.request.urlopen(request,timeout=45).read()
   assert raw.startswith(b'%PDF'),'Not a PDF'
   p.write_bytes(raw)
  reader=PdfReader(p)
  pages=[dict(pdf_page=i+1,page=i+1,text=pg.extract_text()) for i,pg in enumerate(reader.pages)]
  (ROOT/'source'/f'{key}_pages.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
  manifest[key]=dict(filename=filename,version=version,url=url,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pages=len(pages),retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='acquired')
  print(key,len(pages),'pages acquired')
 except Exception as e:
  manifest[key]=dict(filename=filename,version=version,url=url,status='unavailable',reason=str(e))
  print(key,'unavailable:',e)
url='https://standards-oui.ieee.org/oui/oui.csv'
try:
 p=ROOT/'source/ieee_oui.csv'
 if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=45).read())
 manifest['oui']=dict(filename='source/ieee_oui.csv',url=url,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='acquired')
 print('IEEE OUI registry snapshot acquired')
except Exception as e:manifest['oui']=dict(url=url,status='unavailable',reason=str(e))
(ROOT/'source/external_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
