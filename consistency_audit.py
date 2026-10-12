"""Source-backed additions and per-field inventory for the consistency overview.

The inventory describes specification checks, never a device's pass/fail status.
"""
import re

CATEGORIES=['필드 간 관계','Feature·명령','Log·이벤트','상태·적용 조건','형식·예약값']

def extend_checks(data):
    fields={f['id']:f for f in data['fields']}
    refs={n['id']:n for n in data['references']}
    additions=[]
    before=sum(len(f['rules']) for f in fields.values())

    def add(keys,category,condition,observe,expected,ref=None,level='정의 확인',reason='설명에만 있던 조건을 검토 항목으로 추가'):
        for key in keys.split():
            f=fields[key]
            if ref:
                evidence=[{k:v for k,v in s.items() if k!='english'} for s in refs[ref]['sources']]
            elif 'psd_index' in f:
                evidence=[s for s in f['sources'] if s.get('figure')==313]
            else:evidence=f['sources'][:]
            r=dict(condition=condition,observe=observe,expected=expected,level=level,sources=evidence,
                   categories=[category],audit_added=True)
            f['rules'].append(r)
            additions.append(dict(field=key,category=category,condition=condition,expected=expected,
                                  sources=evidence,reason=reason))

    # Direct field definitions and explicit obligations missing from the earlier rules list.
    add('VID','필드 간 관계','PCIe controller의 VID를 대조할 때','Identify.VID, PCI Header.ID의 Vendor ID','두 값이 같아야 합니다. PCI 레지스터 위치·접근 방법은 PCIe Transport 스펙을 추가 확인합니다.')
    add('SSVID','필드 간 관계','PCIe controller의 SSVID를 대조할 때','Identify.SSVID, PCI Header.SS의 Subsystem Vendor ID','두 값이 같아야 합니다. VID와 SSVID 자체가 서로 같아야 한다는 요구는 아닙니다.')
    add('IEEE','형식·예약값','IEEE OUI를 보고할 때','IEEE.OUI, IEEE/RAC 할당 기록','유효한 IEEE/RAC 할당 OUI이어야 합니다. 실제 할당 유효성은 외부 등록 자료로 확인합니다.',level='SHALL')
    add('CNTLID','필드 간 관계','동일 subsystem의 controller들을 비교할 때','각 controller의 CNTLID, subsystem 식별 정보','CNTLID가 subsystem 내에서 controller를 고유하게 식별하는지 확인합니다. 다른 subsystem의 ID와 단순 비교하지 않습니다.')
    add('OAES','Log·이벤트','선택적 비동기 이벤트를 Host에 보낼 때','OAES 지원 비트, FID 0Bh enable, AER completion','Host가 해당 이벤트를 활성화하기 전에는 선택적 이벤트를 보내면 안 됩니다. 지원 비트와 enable은 별도입니다.',level='SHALL')
    add('OAES','Log·이벤트','OAES의 이벤트와 Log 지원을 대조할 때','OAES의 각 비트, 해당 이벤트 및 연결된 Log','비트별 지원 정의를 적용합니다. RGCNS는 두 종류의 Reachability 통지에 연결되며 TTHR·NNSS에는 연결된 Log가 없습니다. 비트 위치를 FID 0Bh와 단순 대입하지 않습니다.','base:5.1.25.1.5')
    add('FGUID','필드 간 관계','같은 FRU에 속한 controller들을 비교할 때','FRU 구성 정보, 각 FGUID','같은 FRU의 모든 controller가 같은 FGUID를 보고해야 합니다. FGUID는 FRU 수명 동안 고정되며, 미구현은 0입니다. FRU 정의는 NVMe-MI에서 추가 확인합니다.',level='SHALL')
    add('FGUID','형식·예약값','FGUID를 해석할 때','112~127바이트, OUI와 extension identifier','Big endian의 EUI-64 기반 16바이트 형식을 적용합니다. 일반 수치 필드의 little endian 변환을 적용하지 않습니다.')
    add('NVMSR','상태·적용 조건','NVMe-MI 지원 여부에 따라 NVMSR를 확인할 때','MI 지원 여부, NVMSR.NVMEE/NVMESD','Subsystem이 MI를 지원하지 않으면 NVMSR=0이어야 합니다. MI compliant controller에서는 정의된 비트 중 적어도 하나가 1이어야 합니다.',level='SHALL')
    add('LPA','Log·이벤트','MLPS=1일 때','LPA.MLPS, LID 00h/12h/13h 지원, LID 05h.CSP','세 Log를 지원하고 Commands Supported and Effects에서 command scope를 보고해야 합니다. MLPS=0이어도 세 Log는 선택적으로 지원할 수 있습니다.')
    add('LPA','Log·이벤트','SMARTS를 확인할 때','LPA.SMARTS, SMART 조회 NSID','SMARTS는 namespace별 SMART 보고 지원입니다. 0이라고 controller 전체 SMART Log 미지원으로 판단하면 안 됩니다.')
    add('LPA PELS','Log·이벤트','Persistent Event Log를 확인할 때','LPA.PES, PELS, Log의 실제 길이','PES=0이면 PELS는 Reserved입니다. 지원하는 경우 PELS×64 KiB는 최대 보고 크기이며 현재 Log 길이와 구분합니다.')
    add('MTFA','상태·적용 조건','FRMW.FAWR=1일 때','FAWR, MTFA, MPTFAWR','MTFA는 유효해야 합니다. MTFA=0은 최대 중지 시간이 정의되지 않았다는 뜻이며 비영 값을 강제하지 않습니다. MPTFAWR의 Commit 처리 시간과 구분합니다.',level='SHALL')
    add('TNVMCAP UNVMCAP','상태·적용 조건','Namespace Management 또는 Capacity Management를 지원할 때','OACS.NMS, CTRATT.FCM/VCM 및 capacity 지원, TNVMCAP/UNVMCAP','두 capacity 필드를 지원해야 합니다. 필드 지원 요구가 두 값 모두 0이 아니어야 한다는 뜻은 아닙니다.',level='SHALL')
    add('SANICAP','상태·적용 조건','Sanitize 명령 지원 여부를 확인할 때','Sanitize 지원, SANICAP','지원하면 SANICAP≠0, 지원하지 않으면 SANICAP=0이어야 합니다.',level='SHALL')
    add('SANICAP','형식·예약값','NODMMAS=00b를 보고할 때','VER, Sanitize 지원 여부, SANICAP.NODMMAS','00b는 Base 1.3 이하를 따르는 구현 또는 Sanitize 명령 미지원 controller만 보고할 수 있습니다. Sanitize를 지원하는 Base 2.1 구현에서 일반적인 미보고 값으로 사용하지 않습니다.')
    add('BPCAP','형식·예약값','RPMBBPWPS=00b를 보고할 때','VER, BPCAP.RPMBBPWPS','00b의 지원 미지정 표기는 Base 2.0 이하 구현에만 허용됩니다. Base 2.1 구현에 적용할 때는 이 버전 예외를 혼동하지 않습니다.')
    add('MAXCMD','상태·적용 조건','Transport에 따른 필수 여부를 확인할 때','Transport, MAXCMD 사용 여부','Fabrics에서는 필수, PCIe에서는 선택입니다. 필드를 사용하지 않으면 MAXCMD=0이어야 합니다. Queue 크기와 반드시 같은 값은 아닙니다.',level='SHALL')
    add('SUBNQN','형식·예약값','SUBNQN을 확인할 때','VER, SUBNQN, Discovery Service NQN 존재 여부','Base 1.2.1 이상에서는 지원이 필수입니다. UTF-8 NUL 종료와 NQN 형식을 적용합니다. Discovery는 고유 Service NQN이 있으면 이를 사용하고 없으면 well-known Discovery NQN을 사용해야 합니다.',level='SHALL')
    add('ICDOFF','상태·적용 조건','Capsule data offset을 적용할 때','Queue 유형, ICDOFF, capsule data 시작 주소','ICDOFF는 I/O Queue에 적용합니다. Admin Queue는 offset 0을 사용해야 합니다. I/O data 시작은 64바이트 SQ entry 끝에서 ICDOFF×16바이트를 더한 위치입니다.',level='SHALL')
    add('AWUN AWUPF ACWU','상태·적용 조건','Logical block을 정의하지 않는 command set의 namespace인 경우','Command Set Identifier, AWUN/AWUPF/ACWU','해당 atomic 필드는 0h로 보고해야 합니다. CSI 00h·02h의 논리 블록 정의 조건과 다른 command set 조건을 구분합니다.',level='SHALL')
    add('AWUN AWUPF ACWU','필드 간 관계','NVM controller atomic baseline을 여러 format·namespace에서 확인할 때','AWUN/AWUPF/ACWU, namespace와 format 변경 전후 값','Controller baseline은 모든 namespace·지원 format에 유효하며 변경되지 않는 보장입니다. Format별로 달라질 수 있는 namespace 값과 구분합니다.','nvm:2.1.4')
    add('AWUN AWUPF ACWU','Feature·명령','Atomic boundary를 넘는 write에 controller baseline 보장을 적용할 때','Controller atomic 값, NABSN/NABSPF/NABO, boundary 교차 여부','Controller baseline은 boundary를 넘어도 지원되어야 합니다. 이를 보장하지 못하면 AWUN/AWUPF/ACWU=0h(1 LBA)이어야 합니다. Namespace별 보장은 boundary 조건을 별도로 적용합니다.','nvm:2.1.4.4',level='SHALL')
    add('ACWU','Feature·명령','Fused Compare+Write의 요청 크기가 ACWU를 넘을 때','FCWS, ACWU/NACWU, 요청 logical block 수','Atomic Write Unit Exceeded로 중단할 수 있습니다. MAY 요구이므로 해당 status가 없다는 이유만으로 위반이라고 단정하지 않습니다.','nvm:2.1.4.1',level='MAY')
    # Correct evidence: the command/status permission is in NVM Figure 117, not the mode overview.
    fields['ACWU']['rules'][-1]['sources']=fields['ACWU']['sources'][:]
    additions[-1]['sources']=fields['ACWU']['sources'][:]

    # Limits are compared after conversion to bytes; a preferred value is not a hard maximum.
    add('HMPRE HMMIN','Feature·명령','HMB 지원 및 할당 크기를 확인할 때','HMPRE, HMMIN, FID 0Dh.HSIZE, CC.MPS','HMPRE=0은 HMB 미지원입니다. HMPRE/HMMIN은 4 KiB 단위이고 HSIZE는 CC.MPS 페이지 단위입니다. Byte 크기로 변환하여 비교합니다. HMPRE는 권장 크기이며 항상 강제 상한이라고 해석하지 않습니다.','base:5.1.25.2.4')
    add('HMMINDS HMMAXD','Feature·명령','HMB descriptor 제한을 적용할 때','HMMINDS/HMMAXD, HMDLEC, 각 BSIZE, CC.MPS','활성 descriptor의 byte 크기를 HMMINDS×4 KiB와 비교하고 사용 가능한 descriptor 수를 HMMAXD와 비교합니다. 한계 값 0은 해당 제한 미보고이며, BSIZE=0 descriptor는 무시합니다. 서로 다른 페이지 단위를 그대로 비교하지 않습니다.','base:5.1.25.2.4')
    add('CTRATT','Feature·명령','HMBR=0인 상태에서 HMNARE=1을 요청할 때','CTRATT.HMBR, FID 0Dh.HMNARE, completion status','Invalid Field in Command로 중단해야 합니다. HMB 접근 제한의 지원 여부·enable·현재 restricted 상태는 서로 다른 값입니다.','base:5.1.25.2.4',level='SHALL')
    add('CTRATT','Feature·명령','RHII=1이고 Host가 reservation을 사용할 때','CTRATT.RHII, FID 81h Host Identifier, reservation 명령','Host Identifier를 먼저 0이 아닌 값으로 설정해야 합니다. HIDS는 128비트 지원 여부이며 0이 Host Identifier 전체 미지원을 뜻하지 않습니다.','base:8.1.22')
    add('FWUG','Feature·명령','FWUG가 01h~FEh인 Firmware Image Download','FWUG, NUMD, OFST','길이=(NUMD+1)×4바이트와 offset=OFST×4바이트가 FWUG×4 KiB granularity·alignment를 따라야 합니다. 위반 요청은 Invalid Field in Command로 중단될 수 있습니다. 00h는 정보 미제공, FFh는 추가 제한 없음입니다.','base:5.1.9',level='정의 확인 · MAY')
    add('KAS','Feature·명령','KATO를 설정·조회할 때','KAS, FID 0Fh.KATO','KATO는 ms 단위이며 controller는 KAS×100 ms granularity로 올림합니다. KATO=0은 타이머 비활성, KAS=0은 Feature 미지원입니다.','base:5.1.25.1.8')
    add('TRATTR MINMRTG MAXMRTG','Feature·명령','Host memory tracking 요청을 처리할 때','THMCS, MRTLL, MINMRTG/MAXMRTG, 요청 RMRTG와 Length','THMCS 지원을 먼저 확인합니다. RMRTG는 보고된 지원 범위에 있어야 하며 MRTLL=1이면 표현되는 길이는 2의 거듭제곱이어야 합니다. Raw RMRTG를 byte 길이로 바로 취급하지 않습니다.','base:5.1.27.1.2')
    add('MCMR NMCMR MCDQPC','Feature·명령','Controller Data Queue의 보고된 한계를 사용할 때','각 CDQ memory range 수·PRP 수, MCMR/NMCMR/MCDQPC','0이 아닌 한계 값에는 각각의 controller·subsystem 범위를 적용합니다. 0은 최대 미보고입니다. Controller별 값과 subsystem 합계를 혼동하지 않습니다.')
    add('MSDBD','Feature·명령','Fabrics I/O capsule에 SGL descriptor를 넣을 때','MSDBD, SGL Data Block/Keyed SGL Data Block descriptor 수','MSDBD≠0이면 해당 descriptor 수가 MSDBD를 넘으면 안 됩니다. MSDBD=0이면 이 필드로 제한하지 않습니다.')
    add('SGLS','Feature·명령','SGL을 사용하는 명령을 처리할 때','SGLS의 지원·alignment·descriptor 비트, PSDT, MPTR, SGL lengths','SGLS[1:0]의 지원과 정렬 조건, 사용 descriptor 종류, LLDTS 길이 조건을 확인합니다. SDT는 권장 최대 개수이며 강제 한계로 사용하지 않습니다.','base:4.3.2')
    add('CDFS','Feature·명령','Copy descriptor format 2h 또는 3h를 요청할 때','CDFS.CDF2S/CDF3S, FID 16h Host Behavior Support의 해당 format enable, Copy.DF','지원 비트가 1이어도 Host가 해당 format을 활성화하지 않았다면 미지원처럼 처리하고 Invalid Field in Command로 중단해야 합니다. 지원하는 0h·1h format은 항상 enable입니다.','nvm:3.3.2',level='SHALL')
    add('CDFS','Feature·명령','Copy의 descriptor format과 목적지 PI format을 확인할 때','CDFS, Copy.DF, 목적지 namespace PI format','미지원 DF는 Invalid Field in Command로 중단합니다. 16b Guard PI 목적지는 DF 0h/2h, 32b 또는 64b Guard PI 목적지는 DF 1h/3h를 사용합니다. 맞지 않으면 Invalid Namespace or Format으로 중단합니다. Format 4h의 SLM 정의는 외부 Command Set 스펙이 필요합니다.','nvm:3.3.2',level='SHALL')
    add('ONCS','Feature·명령','Copy 지원 controller에 NVM 1.0 이후 또는 Base 2.0 이후 규격을 적용하거나 descriptor format 2h/3h를 지원할 때','ONCS.NVMCPYS/NVMCSA, 규격 리비전, CDFS','NVMCSA=1이어야 하며 write 부분에 하나의 write 명령에 대한 atomicity 규정을 적용합니다. 이 자료의 Base 2.1·NVM 1.1 조건에서는 SHOULD로만 취급하면 안 됩니다. Multiple Atomicity Mode의 subrange 보장과 Copy 전체 atomic 보장은 구분합니다.','nvm:3.3.2.2',level='SHALL')
    add('ONCS','필드 간 관계','NVMDSMSV=0에서 DSM 한계 필드의 지원 의미를 대조할 때','ONCS.NVMDSMSV, CNS 06h.DMRL/DMSL/DMRSL','각 필드의 정의는 0이면 DSM 미지원, 0이 아니면 지원과 최대 한계를 나타냅니다. 따라서 세 필드가 서로 다른 지원 여부를 나타내지 않는지 확인합니다. 이 비교는 세 정의로부터 도출한 정합성 확인이며 별도의 SHALL 문장을 인용한 것은 아닙니다.','nvm:4.1.5.4',level='정의에서 도출')
    add('AWUN AWUPF','Feature·명령','Atomic parameter=FFFFh인 Copy를 처리할 때','AWUN/AWUPF, Copy 총 logical block 수, atomicity mode','FFFFh는 10000h logical blocks의 보장입니다. Copy에서는 이것이 모든 명령 크기의 atomicity를 보장하는 값이 아닙니다.','nvm:3.3.2.2')
    add('FUSES','Feature·명령','Fused Compare+Write를 사용할 때','FCWS, fused flags, 두 명령의 순서, ACWU/NACWU','Compare가 첫 번째, Write가 다음이어야 합니다. FCWS 지원과 atomic 한계를 함께 확인합니다. FUSES 15:8의 원문 정의 공백은 임의로 보완하지 않습니다.','base:3.4.2')
    add('CMIC ANACAP','필드 간 관계','ANA 및 namespace attach 관계를 확인할 때','CMIC.ANARS, ANACAP, namespace ANAGRPID, ANA Log','ANA 지원 여부를 먼저 확인합니다. ANAGIDLWAS=1이면 어느 controller에라도 attach된 동안 ANAGRPID가 바뀌면 안 됩니다. RANAOS의 원문 문구 불일치는 확정 판정에서 제외합니다.','base:8.1.1.2')
    add('CRCAP','필드 간 관계','Reachability group ID를 attach 전후에 비교할 때','CRCAP.RGIDC/RRSUP, namespace.RGRPID, attach 상태','RGIDC=1이면 어느 controller에라도 attach된 동안 RGRPID가 바뀌지 않아야 합니다. 비트 이름만 보고 1을 변경 가능으로 해석하지 않습니다.')
    add('NN MNAN','필드 간 관계','Namespace 수와 ID를 비교할 때','NN, MNAN, namespace 목록','NN은 유효 NSID의 상한이고 MNAN은 지원 개수입니다. MNAN=0이면 지원 개수≤NN입니다. 현재 active/allocated 개수를 NN과 무조건 같다고 요구하지 않습니다.')
    add('NSETIDMAX ENDGIDMAX','필드 간 관계','NVM Set/Endurance Group ID 목록을 확인할 때','ID 목록, NSETIDMAX/ENDGIDMAX','유효 ID와 지원 개수는 보고된 ID 상한을 넘지 않아야 합니다. ID 상한이 실제 현재 개수와 반드시 같거나 ID가 연속이어야 한다고 가정하지 않습니다.')
    add('RAB','Feature·명령','Arbitration burst를 비교할 때','RAB, FID 01h.AB','RAB는 권장 burst이고 AB는 현재 설정입니다. 같은 지수 단위를 사용하더라도 필수 일치 조건은 아닙니다. AB=111b의 제한 없음 의미도 별도로 적용합니다.','base:5.1.25.1.1',level='SHOULD · 해석 안내')
    add('ACL AERL ELPE','상태·적용 조건','0 기반 개수 한계를 사용하는 경우','각 raw 값, 동시 Abort/AER 수 또는 Error Log entry 수','실제 개수 한계는 raw 값+1입니다. ACL은 실행 중인 Abort 수, AERL은 outstanding AER 수, ELPE는 보관 가능한 Error Log entry 수입니다.')
    add('ACL AERL','상태·적용 조건','구현의 권고 수준을 검토할 때','ACL+1, AERL+1','Abort와 outstanding AER을 각각 최소 4개 지원하는 것이 권고됩니다. SHOULD이므로 4개 미만이라는 이유만으로 필수 요구 위반이라고 판단하지 않습니다.',level='SHOULD')
    add('CQT','상태·적용 조건','Keep Alive Timeout 또는 통신 손실 후 명령을 quiesce할 때','CQT, outstanding 명령, Immediate Abort 동작','Immediate Abort 요구사항을 충족해야 합니다. CQT=0은 시간 미보고입니다. 시간이 필요 없더라도 1h를 보고하는 것이 권고이며, 이를 0 금지로 해석하지 않습니다.','base:5.1.1.1',level='SHALL · SHOULD')
    for i in range(1,4):
        add(f'CRDT{i}','Feature·명령',f'Completion.DNR=0이고 CRD={i:02b}b일 때',f'CQE.DNR/CRD, CRDT{i}',f'재시도 지연은 CRDT{i}×100 ms입니다. DNR=1이면 이 값을 이유로 재시도하지 않습니다.')
    add('RTD3R RTD3E','상태·적용 조건','PCIe의 RTD3 진입·복귀 지연을 확인할 때','RTD3R/RTD3E, 정상 shutdown 및 초기화 조건','0은 해당 지연 미보고입니다. μs 단위를 적용하고 일반적인 진입 지연과 예상 복귀 지연을 확정 timeout이나 PSD entry/exit 지연으로 바꾸어 해석하지 않습니다.','base:8.1.17.4')
    add('NSSL','상태·적용 조건','NVM subsystem shutdown 시간과 비교할 때','NSSL, subsystem shutdown 과정','NSSL은 μs 단위의 일반적인 완료 지연입니다. 0은 미보고이며 controller shutdown 시간 또는 항상 만족해야 하는 최대 timeout과 동일하지 않습니다.')
    add('EDSTT','상태·적용 조건','Device Self-test 지원 여부와 보고 시간을 확인할 때','OACS.DSTS, EDSTT, power state','미지원이면 EDSTT는 Reserved입니다. 지원 시 PS0의 extended self-test 예상 소요 시간(분)을 나타내며 모든 power state에서의 강제 완료 상한이 아닙니다.')
    add('MEGCAP','상태·적용 조건','보고된 최대 entity capacity를 확인할 때','MEGCAP, domain 구성, 생성하려는 entity','MEGCAP=0은 최대 값 미보고입니다. Single-domain의 생성 가능한 최대 entity 의미와 multi-domain의 Domain List capacity를 구분합니다. Figure 312에 명시되지 않은 단위는 확정 보완하지 않습니다.','base:3.8.3')
    add('OAQD','Feature·명령','Controller 전체 outstanding I/O 수를 확인할 때','OAQD, 모든 I/O Queue의 outstanding 합계','OAQD는 최적 동작을 위한 권장 합계 queue depth입니다. 0은 미보고이며 권장값 초과를 그 자체로 필수 요구 위반이라고 판단하지 않습니다.',level='SHOULD · 해석 안내')
    fields['SUBNQN']['notes'].append('원문 적용 조건 불일치: Figure 312의 SUBNQN 행은 Discovery 열을 R로 표시하지만, 같은 행 본문에는 Discovery controller의 NQN 보고 요구가 있습니다. Discovery에 대해서는 표와 본문을 임의로 하나로 확정하지 않고 Transport 규정 또는 정오표를 추가 확인합니다.')
    refs['nvm:3.3.2.2']['notes'].append('원문 예시의 값 불일치: p.38은 atomic write size 8 LBA 예시에 NAWUN=8h를 사용하지만, Figure 114의 비영 NAWUN은 0 기반이므로 8h는 9 LBA입니다. 이 자료는 예시 숫자를 정합성 수식으로 사용하지 않습니다.')

    # Domain checks are deliberately separate from cross-field equations.
    for f in fields.values():
        key=f['id']
        if key=='VS':
            f['overview_status']='Vendor 정의'
            f['overview_note']='두 PDF에는 내부 형식과 정합성 조건이 없습니다. Vendor 문서가 필요합니다.'
            continue
        f['overview_status']='원문 주의' if f['notes'] else '외부 확인 포함' if f['external'] else '조건 정리'
        f['overview_note']='명령·Feature·상태의 적용 조건을 확인한 뒤 비교합니다.'
        if key.startswith('RESERVED_'):
            add(key,'형식·예약값','이 자료의 두 버전에서 예약 영역을 해석할 때','해당 byte 범위, 적용 중인 규격 확장','예약 영역은 0h 또는 적용되는 향후 확장 규정의 값을 사용합니다. 정의된 기능으로 해석하지 않습니다. NVMe-MI용 예약 영역은 MI 규정이 필요할 수 있습니다.','base:1.4.1',level='SHALL')
            continue
        if 'psd_index' in f:
            add(key,'형식·예약값','지원하는 power state의 PSD 값을 확인할 때','MP/MXPS, ACTP/APS, IDLP/IPS, APW, PLS 시간과 scale','Power scale 11b, APW 011b~111b, PLS scale Dh~Fh, PLS 시간 100~255는 Reserved입니다. PLS 시간 0은 미보고이고 대응 scale은 0입니다. ENLAT/EXLAT=0도 지연 0이 아니라 미보고입니다.')
            add(key,'형식·예약값','PSD의 예약 비트를 확인할 때','Figure 313의 Reserved bit ranges','정의된 모든 예약 비트 범위를 0h 또는 적용 중인 확장 규정과 대조합니다. 아직 지원하지 않는 state의 PSD를 지원 상태의 값처럼 판단하지 않습니다.','base:1.4.1',level='SHALL')
            continue
        if key in ['SN','MN','FR']:
            add(key,'형식·예약값','필드가 고정 길이 ASCII 문자열을 보고하는 경우',f'{key}의 전체 byte 배열','ASCII 20h~7Eh만 사용하며 왼쪽 정렬하고 남는 오른쪽 공간은 ASCII 20h로 채웁니다. NUL 종료 문자열처럼 해석하지 않습니다. SN/MN의 Discovery null 반환은 Figure 312 각주 5의 적용 조건을 먼저 확인합니다.','base:1.4.2',level='SHALL')
        # Byte order, size, and units are already shown in field metadata.
        # They explain decoding; they are not independent consistency checks.
        reserved=[b['range'] for b in f['bits'] if b['english'].strip()=='Reserved']
        if reserved:
            add(key,'형식·예약값','예약 비트를 확인할 때',key+' Reserved bits '+', '.join(reserved),'정의된 예약 비트는 0h 또는 적용 중인 확장 규정의 값을 사용합니다. Reserved enum 값과 예약 bit 범위를 구분합니다.','base:1.4.1',level='SHALL')
        for b in f['bits']:
            if b['english'].strip()=='Reserved':continue
            existing=next((r for r in f['rules'] if r['condition'].startswith('비트 '+b['range']+' / ')),None)
            if existing:
                existing.update(categories=['형식·예약값'],level='정의 확인 · SHALL 포함')
                continue
            add(key,'형식·예약값',f"비트 {b['range']} ({b['title']})를 해석하거나 관련 기능을 사용할 때",f"{key}.{b['title']} 및 관련 값",b['ko'],level='정의 확인',reason='SHALL이라는 단어가 없는 지원 정의·enum 조건도 검토 목록에 포함')
            f['rules'][-1]['sources']=[b['source']];additions[-1]['sources']=[b['source']]

    # Every remaining check has a stable classification and precise navigation targets.
    for f in fields.values():
        for i,r in enumerate(f['rules']):
            r['id']=f"{f['id']}-check-{i+1}"
            r['field_applicability']=(f"I/O 또는 Administrative controller에서 PS{f['psd_index']}가 지원되는 경우(NPSS≥{f['psd_index']})" if 'psd_index' in f else '해당 controller·transport에서 필드가 정의되는 경우에 적용합니다. 필수·선택·예약 분류와 각주를 먼저 확인하세요.')
            if 'categories' not in r:
                t=r['condition']+' '+r['observe']+' '+r['expected']
                if any(w in t for w in ['Log','로그','AER','이벤트','event']):cat='Log·이벤트'
                elif any(w in t for w in ['Feature','FID','명령','Set ','Get ','Write','Flush']):cat='Feature·명령'
                elif any(w in t for w in ['≤','≥','같아야','baseline','동일','모든 controller']):cat='필드 간 관계'
                else:cat='상태·적용 조건'
                r['categories']=[cat]
            code=r['condition']+' '+r['observe']+' '+r['expected']
            r['related_fields']=[k for k in fields if k!=f['id'] and not k.startswith('RESERVED_') and re.search(r'(?<![A-Za-z0-9_])'+re.escape(k)+r'(?![A-Za-z0-9_])',code)]
            r['related_refs']=list(dict.fromkeys(s['doc']+':'+s['section'] for s in r['sources'] if s['doc']+':'+s['section'] in refs))
        f['check_categories']=list(dict.fromkeys(c for r in f['rules'] for c in r['categories']))
        if not f['rules'] and f['id']!='VS':
            f['overview_status']='별도 조건 없음'
            f['overview_note']='이 자료에 정리된 별도 정합성 조건이 없습니다. 위치·단위·값의 의미는 필드 설명에서 확인하세요.'
    for f in fields.values():
        referenced={target for r in f['rules'] for target in r['related_refs']}
        for target in referenced:
            if not any(e['target']==target for e in f['edges']):
                f['edges'].append(dict(target=target,type='정합성 근거',text='정합성 조건에 적용되는 관련 규정을 확인합니다.'))
                refs[target]['incoming'].append(dict(target=f['id'],type='정합성 근거',text='이 필드의 정합성 조건에서 참조합니다.'))
    ext=next(e for e in data['external'] if e['id']=='other_cs')
    if 'CDFS' not in ext['fields']:ext['fields'].append('CDFS')
    if 'other_cs' not in fields['CDFS']['external']:fields['CDFS']['external'].append('other_cs')
    ext['needed']+=' Copy descriptor format 4h의 SLM source namespace 규정도 추가 확인이 필요합니다.'
    if fields['CDFS']['overview_status']=='조건 정리':fields['CDFS']['overview_status']='외부 확인 포함'
    data['consistency_audit']=dict(
        scope='제공된 Base 2.1·NVM Command Set 1.1의 CNS 01h 필드/비트 정의, Figure 313/314 및 연결된 관련 절',
        before_checks=before,after_checks=sum(len(f['rules']) for f in fields.values()),
        additions=additions,categories=CATEGORIES,
        field_count=len(fields),fields_with_checks=sum(bool(f['rules']) for f in fields.values()),
        limitations=['실제 장치의 값이나 동작을 수집한 판정 결과가 아닙니다.',
                     '바이트 순서·크기·단위의 일반 해석 안내는 필드 정의에 표시하며 정합성 조건 수에 포함하지 않습니다.',
                     '외부 Transport·NVMe-MI·IEEE·다른 Command Set 규정은 확인 대상으로 유지합니다.',
                     'FUSES의 정의 공백과 ANACAP·KPIOC·AWUPF의 원문 불일치는 확정 보정하지 않습니다.',
                     '형식·예약값 확인은 교차 필드 관계와 별도로 표시합니다. 조건 수가 많다는 것이 검증 완료를 의미하지 않습니다.'])
    return data
