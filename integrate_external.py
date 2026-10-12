"""One-time editorial integration of acquired official, version-pinned references."""
import json
from pathlib import Path
from catalog import digest
ROOT=Path(__file__).resolve().parent
p=ROOT/'source/catalog.json';d=json.loads(p.read_text(encoding='utf-8'))
m=json.loads((ROOT/'source/external_manifest.json').read_text(encoding='utf-8'))
for key in ['pcie','mi20','mi12d','ieee']:
 if m[key]['status']=='acquired':d['documents'][key]=dict(m[key],title={'pcie':'PCIe Transport 1.1','mi20':'NVMe-MI 2.0','mi12d':'NVMe-MI 1.2d','ieee':'IEEE EUI/OUI 지침 (2017-08-03)'}[key])
items=[
 ('pcie','3.8.1.1',17,11,'PCI Header Vendor ID','PCI Configuration Space의 offset 00h ID register bits 15:0이 VID이다. Identify.VID와 이 값을 대조한다.','VID','15:00 Vendor ID (VID)'),
 ('pcie','3.8.1.17',20,24,'PCI Header Subsystem Vendor ID','offset 2Ch SS register bits 15:0이 SSVID이다. bits 31:16의 Subsystem ID와 혼동하지 않는다.','SSVID','15:00 RO HwInit Subsystem Vendor ID (SSVID)'),
 ('mi20','1.5',15,None,'FGUID의 FRU 범위','FGUID가 가리키는 FRU는 교체 가능한 NVMe Storage Device이다. controller 개수와 FRU 개수를 같다고 가정하지 않는다.','FGUID','The FRU referenced by the FRU Globally Unique Identifier (FGUID) field'),
 ('mi20','1.4',13,None,'NVMSR와 관리 endpoint','Storage Device의 NVMESD, Enclosure의 NVMEE를 보고하며 적어도 하나가 1이어야 한다. PCIe·2-Wire port에는 관리 endpoint가 없거나 여러 개일 수 있다. 실제 구성을 수집하여 MEC 비트와 대조한다.','NVMSR MEC',''),
 ('mi20','1.3.1.2 / 1.8.48',12,None,'VPD 접근과 저장 위치','VPD는 FRU Information Device에 저장된다. 접근 경로·동작은 VPD Read/Write와 SMBus/I2C를 구분한다. VWCI의 잔여 쓰기량과 Serial Number 등 VPD 내용은 서로 다른 관측값이다.','VWCI SN',''),
 ('mi12d','Annex A',159,None,'OCP의 Basic Management 기준 문서','OCP가 지정한 MI 1.2d는 MI 2.0과 별도 근거로 관리한다. Basic Management 지원은 DP-CFG-4 선택을 먼저 확인하고 OCP §11.2의 확장 데이터 형식을 함께 대조한다.','MN TNVMCAP NPSS',''),
 ('ieee','EUI Structure and Representation',9,None,'OUI 구성 및 등록 확인','OUI 구성과 할당 유효성은 별도 확인이다. 공개 등록 조회에서 소유자 이름이 없거나 결과를 확보하지 못해도 미할당으로 단정하지 않는다. 실제 조직의 할당 자료와 조회 날짜가 필요하다.','IEEE FGUID','private listing option'),
]
for doc,section,page,figure,title,ko,keys,quote in items:
 if doc not in d['documents']:continue
 source=dict(doc=doc,section=section,pdf_page=page,page=page,figure=figure)
 sid='ext-'+digest([doc,section,title])[:20]
 if not any(e['id']==sid for e in d['excerpts']):d['excerpts'].append(dict(id=sid,text=quote or '대응 페이지는 원문 PDF에서 확인하세요. 원문 전체는 내장하지 않습니다.',source=source,owner=title,kind='관련 규정',status='원문 대조 완료' if doc in ['pcie','mi20','ieee'] else '해석 확인 필요',reason='지정 페이지의 역할·정의 대조'))
 refid=doc+':'+section
 if not any(n['id']==refid for n in d['references']):d['references'].append(dict(id=refid,name=title,title=title,ko=ko,topic='외부 근거',sources=[dict(source,english=quote or '')],excerpt_ids=[sid],rules=[],edges=[],incoming=[],notes=[],external=[],kind='reference'))
 ref=next(n for n in d['references'] if n['id']==refid)
 for f in d['fields']:
  if f['id'] not in keys.split():continue
  if not any(e['target']==refid for e in f['edges']):
   f['edges'].append(dict(id='rel-'+digest([f['id'],refid])[:20],target=refid,type='참조 규정',text=ko));ref['incoming'].append(dict(target=f['id'],type='참조 규정',text=ko))
  for c in d['conditions']:
   if f['id'] in c['fields'] and c['standard']=='nvme':
    if source not in c['sources']:c['sources'].append(source)
    if sid not in c['excerpt_ids']:c['excerpt_ids'].append(sid)
    if f['id'] in ['VID','SSVID']:
     c['content_status']='원문 대조 완료';c['observe']+=' (PCI config offset '+('00h' if f['id']=='VID' else '2Ch')+', bits 15:0)'
  if f['id'] in ['VID','SSVID']:
   f['content_status']='원문 대조 완료'
   next(x for x in d['coverage'] if x['field']==f['id'])['status']='원문 대조 완료'
d['external_acquisition']=m
d['copyright_notice']='외부 원문: © NVM Express, Inc. ALL RIGHTS RESERVED. IEEE 지침 및 등록 자료의 권리는 IEEE에 있습니다. 짧은 인용과 출처 링크를 제공합니다.'
d['workflows']=[
 dict(id='identity',title='식별 정보 대조',fields='VID SSVID SN MN FR FGUID IEEE MEC NVMSR VWCI'.split(),steps=['제품·controller·FRU의 동일성 확인','Identify와 PCI Header·라벨·VPD 관측값 수집','동일성·수명·할당 조건 대조'],materials=['Identify CNS 01h','PCI config offset 00h/2Ch','제품 라벨·Barcode·VPD·FRU 구성','IEEE 할당 기록']),
 dict(id='firmware',title='펌웨어 업데이트',fields='FR FRMW FWUG MTFA MPTFAWR OAES OACS'.split(),steps=['활성 slot과 RW/RO slot 구성 확인','download 크기·offset·granularity 대조','activation 전후 revision·Feature·시간 기록'],materials=['Firmware Slot Log 03h','Firmware Commit/Download 인자와 completion','업데이트 전후 Identify·Feature·전원 상태']),
 dict(id='power',title='전원 관리',fields='NPSS APSTA CTRATT HMPRE HMMIN'.split()+['PSD'+str(i) for i in range(32)],steps=['지원 PS와 PSD 단위 확인','현재·저장된 Power Management/APST 설정 수집','전환 대상·시간·소비전력 조건 대조'],materials=['FID 02h/0Ch/11h','전체 지원 PSD','현재 PS 및 power cycle·전환 기록','OCP 전력 측정 및 PCIe Slot Power Limit']),
 dict(id='atomicity',title='쓰기 원자성',fields='AWUN AWUPF ACWU FUSES ONCS VWC'.split(),steps=['controller baseline과 namespace 상속 조건 확인','LBA 크기·NAWUN/NAWUPF/NACWU·boundary 수집','DN 및 요청 크기·경계·실패 조건별 보장 비교'],materials=['CNS 01h / CNS 00h','FID 0Ah / FID 06h','LBA format·NABSN/NABSPF/NABO','Write/Copy/Fused 요청 및 오류 조건']),
 dict(id='transfer',title='전송 크기',fields='MDTS CTRATT SGLS SQES CQES ONCS'.split(),steps=['단위 기준과 0 특수값 확인','data·metadata·SGL 및 명령별 제한 수집','bytes로 환산하여 적용되는 한도 대조'],materials=['CAP.MPSMIN / CC.MPS','CNS 06h 명령별 한도','metadata 배치·SGL 및 요청 크기']),
 dict(id='ocp',title='OCP 요구 검토',fields=[],steps=['OCP 적용 여부와 항목별 DP-CFG A/B 선택 확인','OCP 추가 요구·금지·override와 NVMe 기준 비교','고객 면제·보안 인증·미확인 자료 기록'],materials=['OCP 2.6','고객 DP-CFG-1~11 선택','라벨·firmware·Log·성능·전력 관측값','고객 면제 및 인증 자료'])]
for w in d['workflows']:w['condition_ids']=[c['id'] for c in d['conditions'] if (c['standard']=='ocp' if w['id']=='ocp' else bool(set(c['fields'])&set(w['fields'])))]
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print('Integrated external reference nodes and six workflows.')
