"""Final editorial review: separate interpretation from independently observable checks.

Bit tables remain authoritative explanations. Copying their paragraphs into a check
does not create a test, even when the paragraph contains the word SHALL.
"""
import re

GUIDANCE={
 ('FGUID','FGUID를 해석할 때'),('RAB','Arbitration burst를 비교할 때'),
 ('RTD3R','PCIe의 RTD3 진입·복귀 지연을 확인할 때'),('RTD3E','PCIe의 RTD3 진입·복귀 지연을 확인할 때'),
 ('NSSL','NVM subsystem shutdown 시간과 비교할 때'),('MEGCAP','보고된 최대 entity capacity를 확인할 때'),
 ('OAQD','Controller 전체 outstanding I/O 수를 확인할 때'),
 ('ACL','0 기반 개수 한계를 사용하는 경우'),('AERL','0 기반 개수 한계를 사용하는 경우'),('ELPE','0 기반 개수 한계를 사용하는 경우'),
 ('AWUN','Atomic parameter=FFFFh인 Copy를 처리할 때'),('AWUPF','Atomic parameter=FFFFh인 Copy를 처리할 때'),
 ('LPA','SMARTS를 확인할 때'),('ONCS','Verify/Write Zeroes/Write Uncorrectable variant 비트=0'),
 ('MTFA','FRMW.FAWR=1일 때'),
 ('CRDT1','Completion.DNR=0이고 CRD=01b일 때'),
 ('CRDT2','Completion.DNR=0이고 CRD=10b일 때'),
 ('CRDT3','Completion.DNR=0이고 CRD=11b일 때'),
}
# Explicit constraints formerly buried in copied bit paragraphs.
EXPLICIT=[
 ('MEC','PCIe port의 Management Endpoint 구성을 확인한 경우','실제 PCIe port Management Endpoint 존재 여부, MEC.PCIEME','PCIe port에 하나 이상의 Management Endpoint가 있으면 PCIEME=1, 없으면 0이어야 합니다.'),
 ('MEC','2-Wire port의 Management Endpoint 구성을 확인한 경우','실제 2-Wire port Management Endpoint 존재 여부, MEC.TWPME','2-Wire port에 하나 이상의 Management Endpoint가 있으면 TWPME=1, 없으면 0이어야 합니다.'),
 ('OACS','DIRS=1을 보고하는 경우','OACS.DIRS, Directive Send 및 Directive Receive 명령 지원','Directive Send와 Directive Receive 명령을 모두 지원해야 합니다.'),
 ('ONCS','Write Zeroes 명령을 지원하지 않는 경우','CNS 06h 및 ONCS로 확인한 Write Zeroes 지원 여부, ONCS.NSZS','NSZS=0이어야 합니다. ONCS의 variant 비트 0만으로 명령 미지원을 단정하지 않습니다.'),
 ('ONCS','RESERVS=1을 보고하는 경우','ONCS.RESERVS, Reservation Report/Register/Acquire/Release 명령 지원','네 Reservation 명령을 모두 지원해야 합니다.'),
 ('NWPC','NWPWPS=1을 보고하는 경우','NWPC.NWPWPS, FID 84h의 지원 상태 및 Write Protection Control','No Write Protect와 Write Protect 상태를 지원해야 합니다. Until Power Cycle 및 Permanent 상태 지원은 별도 비트로 판단합니다.'),
 ('NWPC','WPUPCS=1 또는 PWPS=1을 보고하는 경우','NWPC.WPUPCS/PWPS, FID 84h Write Protection Control 지원 상태','WPUPCS=1이면 Write Protect Until Power Cycle 상태, PWPS=1이면 Permanent Write Protect 상태를 지원해야 합니다.'),
 ('FNA','정상 처리된 Format NVM의 영향 범위를 확인하는 경우','Format NSID/SES, FNA.FNS/SENS, 실제 영향을 받은 namespace 목록','NSID=FFFFFFFFh이면 FNS/SENS와 관계없이 모든 namespace에 적용합니다. 그 외 NSID에서 FNS=1이면 format은 전체 namespace에, SENS=1이면 secure erase는 전체 namespace에 적용합니다. 0이면 지정 namespace에 적용합니다. 지원하지 않는 NSID로 중단된 명령에는 이 성공 동작을 요구하지 않습니다.'),
 ('SGLS','SGL을 사용하는 명령에서 LLDTS=0인 경우','SGLS.LLDTS, 명령의 data/metadata 전송량 및 각 SGL 총 길이','data SGL과 metadata SGL의 각 길이가 해당 전송량과 같아야 합니다. LLDTS=1은 더 긴 SGL 지원을 나타내며 더 짧은 SGL까지 허용한다는 뜻은 아닙니다.'),
 ('TMPTHHA','Temperature Threshold Hysteresis 속성을 지원하지 않는 경우','속성 지원 여부, TMPTHHA.TMPTHMH','TMPTHMH=000b이어야 합니다.'),
 ('SANICAP','NODAS=1로 시작한 Sanitize의 추가 media modification을 확인하는 경우','SANICAP.NODMMAS, Sanitize의 NODAS, 실제 추가 media modification','NODMMAS=01b이면 추가 media modification을 수행하면 안 됩니다. 10b이면 해당 sanitize processing의 일부로 추가 media modification을 수행해야 합니다.'),
]

def review(data):
    fields={f['id']:f for f in data['fields']};removed=[];added=[];rewritten=[]
    for f in fields.values():
        f['interpretation_notes']=[];kept=[]
        for r in f['rules']:
            copied=r['condition'].startswith('비트 ')
            guidance=(f['id'],r['condition']) in GUIDANCE
            if copied or guidance:
                removed.append(dict(field=f['id'],old_id=r['id'],condition=r['condition'],expected=r['expected'],sources=r['sources'],reason='비트 정의 중복' if copied else '값 해석·주의사항'))
                if guidance:f['interpretation_notes'].append(dict(text=r['expected'],sources=r['sources']))
            else:kept.append(r)
        f['rules']=kept
    def new(key,condition,observe,expected):
        f=fields[key]
        r=dict(id=key+'-review-'+str(len(f['rules'])+1),condition=condition,observe=observe,expected=expected,
               level='필드 정의에 따른 조건',standard='nvme',sources=f['sources'],categories=['필드 간 관계'],
               field_applicability='',related_fields=[],related_refs=[],review_action='복사한 비트 설명에서 구체적 제약 분리')
        f['rules'].append(r);added.append(dict(field=key,**r))
    for row in EXPLICIT:new(*row)
    for f in fields.values():
        for r in f['rules']:
            old=r['expected']
            if r.get('standard')=='nvme':
                # Field and bit definitions often span pages. Do not cite only
                # the first page of Figure 312 for an obligation on a later page.
                cited={(s['doc'],s['section'],s['pdf_page'],s.get('figure')) for s in r['sources']}
                for evidence in f['sources']:
                    marker=(evidence['doc'],evidence['section'],evidence['pdf_page'],evidence.get('figure'))
                    if marker not in cited:r['sources'].append(evidence);cited.add(marker)
                r['level']=r['level'].replace('정의 확인','필드 정의에 따른 조건')
                if 'psd_index' not in f:r['field_applicability']=''
                if r['condition']=='HMB descriptor 제한을 적용할 때':
                    r['expected']='BSIZE=0인 entry는 무시합니다. HMMINDS≠0이면 사용하는 각 descriptor의 BSIZE×2^(12+CC.MPS)가 HMMINDS×4096 bytes 이상이어야 합니다. HMMAXD≠0이면 usable descriptor entry 수가 HMMAXD 이하인지 대조합니다. 0인 한계 값에는 제한을 임의로 추가하지 않습니다.'
                if r['condition']=='HMB 지원 및 할당 크기를 확인할 때':
                    f['interpretation_notes'].append(dict(text=old,sources=r['sources']))
                    r['condition']='HMPRE=0을 보고하는 경우'
                    r['observe']='HMPRE 및 Host Memory Buffer Feature 지원 여부'
                    r['expected']='Host Memory Buffer Feature를 지원하지 않아야 합니다. 실제 HMB 할당량과 권장 HMPRE가 같아야 한다는 조건은 아닙니다.'
                if r['condition']=='SGL을 사용하는 명령을 처리할 때':
                    f['interpretation_notes'].append(dict(text=old,sources=r['sources']))
                    r['condition']='SGLS[1:0]=10b인 controller에서 SGL Data Block을 사용하는 경우'
                    r['observe']='SGLS[1:0], 각 Data Block의 address 및 length'
                    r['expected']='Data Block은 dword alignment 및 granularity 요구를 만족해야 합니다. SDT는 권장 최대 개수이므로 그 수치 초과 자체를 필수 위반으로 판단하지 않습니다.'
                if r['condition']=='지원하는 power state의 PSD 값을 확인할 때':
                    r['expected']='APS/IPS=11b, APW=011b~111b, PLS scale=Dh~Fh, PLS 시간값=100~255(10진수)는 예약값이므로 사용하면 안 됩니다. MXPS는 별도의 1-bit scale입니다. 시간값 0의 미보고 의미는 비트 정의에서 확인합니다.'
                if '허용 버전' in old or '이전 구현' in old:
                    r['expected']=r['expected'].replace('Base 2.0 이전','Base 2.0 이하').replace('Base 1.3 이전','Base 1.3 이하')
                if r['expected']!=old:rewritten.append(dict(field=f['id'],id=r['id'],before=old,after=r['expected']))
            r['check_kind']='동작 허용' if r['level'].startswith('MAY') else '권고' if r['level'].startswith('SHOULD') else '도출한 관계' if '도출' in r['level'] or r.get('interpretation') in ['관계','환산'] else '규격의 제약'
            if not r.get('related_fields'):
                text=r['observe']+' '+r['expected']
                r['related_fields']=[k for k in fields if k!=f['id'] and re.search(r'(?<![A-Za-z0-9_])'+re.escape(k)+r'(?![A-Za-z0-9_])',text)]
        # Do not manufacture a check to make the coverage chart look complete.
        f['check_categories']=list(dict.fromkeys(c for r in f['rules'] for c in r['categories']))
        if not f['rules'] and f['id']!='VS':
            f['overview_status']='별도 조건 없음'
            f['overview_note']='이 자료에 정리된 별도 정합성 조건이 없습니다. 값의 정의와 해석은 필드 설명을 확인하세요.'
        elif f['overview_status']=='별도 조건 없음':f['overview_status']='조건 정리'
    nvme=sum(r['standard']=='nvme' for f in fields.values() for r in f['rules'])
    a=data['consistency_audit'];a['nvme_checks']=nvme;a['after_checks']=sum(len(f['rules']) for f in fields.values());a['fields_with_checks']=sum(bool(f['rules']) for f in fields.values())
    retained_additions=[]
    for entry in a['additions']:
        rule=next((x for x in fields[entry['field']]['rules'] if x['condition']==entry['condition']),None)
        if rule:
            retained_additions.append(dict(entry,expected=rule['expected'],sources=rule['sources']))
    a['additions']=retained_additions
    data['editorial_audit']=dict(scope='CNS 01h 전체 152개 byte 범위와 비트 정의의 자동 복사 항목, 수동 조건 및 OCP 적용 조건의 편집 재검토',
        removed=removed,added=added,rewritten=rewritten,
        fields=[dict(id=f['id'],checks=len(f['rules']),guidance=len(f['interpretation_notes']),status=f['overview_status'],sources=f['sources']) for f in fields.values()],
        limitations=['추출 원문에 근거한 편집·조건 분류 재검토이며 실제 장치 적합성 판정은 아니다.','NVMe-MI·PCIe·IEEE·외부 Command Set 및 고객 자료가 필요한 항목과 원문 불일치는 여전히 확인이 필요하다.'])
    return data
