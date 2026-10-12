"""Extract the supplied OCP 2.6 PDF and pin the text cache to its SHA-256."""
import hashlib,json
from pathlib import Path
from pypdf import PdfReader
root=Path(__file__).resolve().parent
pdf=root/'OCP2_6.pdf';reader=PdfReader(pdf)
pages=[dict(pdf_page=i+1,page=i+1,text=p.extract_text()) for i,p in enumerate(reader.pages)]
assert len(pages)==211 and '2.6' in pages[0]['text'],'Expected the supplied OCP 2.6 edition'
(root/'source/ocp_pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'source/ocp_manifest.json').write_text(json.dumps(dict(filename=pdf.name,sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),pages=len(pages),version='2.6',cover_date='2024-09-25'),indent=2),encoding='utf-8')
print('Extracted OCP 2.6: 211 pages; SHA-256 recorded.')
