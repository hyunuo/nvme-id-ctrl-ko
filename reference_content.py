"""Integrated related clauses, bidirectional relationships and manual checks."""
import json,re
from pathlib import Path
from pypdf import PdfReader
from author_content import ROOT,DATA,make_fields

# Referenced clauses are intentionally bounded to the context needed by Identify.
SUMMARY=r'''
base|1.4.1|필수·권고·허용의 구분과 예약값 처리|SHALL은 반드시 따라야 하는 요구사항, SHOULD는 권고사항, MAY는 허용되는 동작을 뜻합니다. Reserved bit·byte·field·property·register는 0h 또는 향후 규격 확장에 따른 값이어야 합니다. 수신자가 모든 Reserved bit를 검사해야 한다는 요구와는 다릅니다. 정의된 필드의 Reserved coded value도 구분합니다.
base|1.4.2|숫자·문자열 표현|0 기반 값은 실제 값보다 1 작습니다. 별도 정의가 없으면 1 기반입니다. ASCII는 20h~7Eh만 허용하고 왼쪽 정렬·오른쪽 공백 padding을 사용합니다. NUL 종료로 지정된 문자열은 별도 규칙입니다. KiB와 kB 등 이진·십진 단위를 구분합니다.
base|1.5.44|호스트 접근 가능 메모리|Controller와 host가 command data를 교환하는 host-accessible memory의 정의입니다. MDTS는 이 메모리와 controller 사이의 전송에 적용하며 매체 내부 작업 크기 전부에 자동 적용하지 않습니다.
base|2.4.1|여러 controller를 가진 subsystem|여러 host의 접근 또는 한 host의 여러 경로에 사용될 수 있습니다. CMIC.MCTRS는 가능성을 나타내며 실제 경로 사용 상태와 구분합니다.
base|3.1.3|명령·로그·Feature 지원 요구|Controller 유형에 따라 mandatory·optional·prohibited 지원 요구가 다릅니다. OACS/ONCS의 optional 지원 비트만으로 mandatory 명령의 지원을 판정하지 않습니다. 여러 command set의 합산 지원과 특정 command set의 실제 지원도 구분합니다.
base|3.1.4.2|Version property|VS의 major/minor/tertiary 버전을 Identify.VER가 그대로 보고합니다. VER 비교 시 raw 정수를 임의의 소수점 버전으로 해석하지 않습니다.
base|3.1.4.1|Controller Capabilities property|CAP.MPSMIN은 최소 메모리 페이지 크기 지수이며 실제 최소 크기는 2^(12+MPSMIN) 바이트입니다. MDTS의 기준 단위입니다. Host가 선택한 CC.MPS와 구분합니다.
base|3.1.4.5|Controller Configuration|CC.IOSQES와 CC.IOCQES는 I/O queue entry 크기의 지수입니다. Identify의 최소·최대 범위 안에서 설정합니다. CC.MPS는 host의 선택 페이지 크기로 MDTS의 최소 페이지 기준과 다릅니다.
base|3.2.2|NVM Set|Namespace 구성과 자원 분리를 위한 NVM Set의 개념입니다. CTRATT.NSETS는 지원 여부이며 NSETIDMAX는 ID 상한입니다. ID의 연속성과 현재 개수를 가정하지 않습니다.
base|3.2.3|Endurance Group|Endurance 관리 대상 group의 개념입니다. CTRATT.EGS·ENDGIDMAX·MEGCAP와 관련 로그·이벤트 설정을 연결해 확인합니다.
base|3.2.5|Domain과 Division|하나의 subsystem에 여러 domain을 둘 수 있습니다. CTRATT.MDS와 DID로 구분하며 firmware 및 attachment 값을 비교할 때 같은 domain인지 확인합니다.
base|3.2.5.3|Domain ID 사용|Domain 식별자 사용에 대한 informative 설명입니다. Controller 간 값을 비교할 때 DID를 함께 기록합니다. Informative 설명 자체를 새로운 필수 요구로 사용하지 않습니다.
base|3.4.2|Fused operation|두 연속 명령을 하나의 fused operation으로 처리합니다. NVM Compare가 먼저이고 Write가 다음입니다. 지원 여부는 FUSES.FCWS, atomic 한계는 ACWU와 namespace NACWU를 확인합니다.
base|3.4.4|명령 중재|Controller가 SQ에서 명령을 선택하는 방식입니다. RAB는 권장 burst, FID 01h의 AB는 설정 burst입니다. 둘이 같아야 하는 관계는 아닙니다.
base|3.6.3|NVM subsystem shutdown|Subsystem shutdown과 controller shutdown은 적용 범위가 다릅니다. NSSL은 subsystem shutdown의 일반적인 지연 시간이며 completion 또는 상태 관측과 같은 의미가 아닙니다.
base|3.8|NVM 용량 모델|TNVMCAP/UNVMCAP는 controller가 접근 가능한 총·미할당 용량입니다. Namespace 용량과 할당 방식, 해당 group과 domain을 함께 확인합니다. Metadata·overprovisioning 등의 용량 산정 조건을 고려하지 않고 namespace LBA 크기의 합과 raw byte 용량을 동일시하지 않습니다.
base|3.8.3|용량 보고와 재조회 조건|Single-domain에서는 TNVMCAP/UNVMCAP가 subsystem 용량을 나타내고, multi-domain에서는 명령 처리 controller가 접근 가능한 용량을 나타냅니다. MEGCAP가 0이 아닌 single-domain subsystem에서는 생성 가능한 최대 entity(Endurance Group·NVM Set·formatted namespace 등)를 나타냅니다. Entity가 생성되거나 삭제되면 미할당 용량이 달라질 수 있습니다. Capacity 구성 변경과 firmware 활성화 등 규정에 따라 capacity 정보를 재조회합니다.
base|3.9|Keep Alive|활성 Keep Alive Timer의 만료는 통신 단절 처리로 이어질 수 있습니다. KAS는 설정 granularity, KATO는 timeout, CQT는 명령 quiesce 시간입니다. 서로 다른 시간값입니다.
base|3.9.4.1|Traffic Based Keep Alive|CTRATT.TBKAS로 traffic based 동작을 식별합니다. Keep Alive 명령만으로 상태를 판단하지 않고 host/controller traffic과 타이머 갱신 조건을 확인합니다.
base|3.11|펌웨어 업데이트 과정|이미지 다운로드·slot 지정·Commit Action·활성화를 구분합니다. FR은 현재 활성 리비전입니다. Reset 없는 활성화 지원은 FRMW.FAWR이며 처리 시간 MPTFAWR와 명령 처리 중지 시간 MTFA를 구분합니다.
base|4.3.2|SGL 정의와 제약|Descriptor 종류와 Data Block의 주소·길이·정렬은 SGLS 능력에 맞아야 합니다. SDT는 권장 개수, MSDBD는 Fabrics capsule에 넣는 descriptor 제한입니다. SGL 길이와 실제 전송 크기를 비교할 때 LLDTS와 metadata 조건을 봅니다.
base|4.5.4|Endian 규칙|일반적으로 여러 바이트로 이루어진 숫자 필드는 little endian으로 해석합니다. FGUID처럼 별도로 big endian인 필드는 해당 정의를 우선합니다. 문자열은 바이트 순서대로 읽으며, 숫자처럼 endian 변환을 적용하지 않습니다.
base|4.7|NVMe Qualified Name|SUBNQN의 namespace-independent subsystem 이름 규칙입니다. UTF-8 NUL 종료와 NQN 형식을 적용합니다. Discovery의 well-known NQN과 일반 subsystem의 고유 NQN을 구분합니다.
base|4.7.1|고유 식별자|SN/MN과 subsystem 고유 식별의 관계를 확인하는 규정입니다. Discovery의 SN/MN을 고유 식별자로 사용하지 않는 권고와 혼동하지 않습니다.
base|5.1|공통 Admin 명령|Admin Queue 명령의 지원 여부와 공통 처리 요구사항을 설명합니다. ACL은 동시에 실행 중인 Abort 수, AERL은 동시에 outstanding인 AER 요청 수이며 각각 0 기반입니다.
base|5.1.1.1|Immediate Abort|Immediate Abort의 완료 요건과 아직 완료되지 않은 명령의 처리 방법을 설명합니다. CQT는 Keep Alive 만료 또는 통신 손실 후 이 요건들을 만족시키는 예상 최악 시간입니다.
base|5.1.2|Asynchronous Event Request|AER 요청이 outstanding 상태일 때 비동기 이벤트 completion을 받을 수 있습니다. AERL은 outstanding 요청 한계, OAES는 지원 능력, FID 0Bh는 이벤트 enable 설정입니다. Get Log Page의 event 유지/해제 처리도 구분합니다.
base|5.1.9|Firmware Image Download|NUMD는 0 기반 dword 길이이고 OFST는 dword offset입니다. FWUG가 01h~FEh이면 byte 길이·offset을 FWUG×4 KiB 조건과 대조합니다. 00h는 정보 미제공, FFh는 추가 granularity 제한 없음입니다.
base|5.1.11|Get Features|Select에 따라 current/default/saved/supported capabilities를 구분하여 조회합니다. 지원 능력 조회와 현재 상태 조회를 혼동하지 않습니다. ONCS.SSFS는 non-zero Select 지원 여부이며 Feature별 saveable·namespace-specific·changeable 특성도 확인합니다.
base|5.1.12.1.1|Supported Log Pages / LID 00h|Log별 지원을 확인하는 목록입니다. LPA.MLPS=1이면 이 로그 지원이 필요합니다. MLPS=0이어도 선택적으로 지원할 수 있으므로 미지원으로 단정하지 않습니다.
base|5.1.12.1.2|Error Information / LID 01h|보관 가능한 최대 entry 수는 ELPE+1입니다. 실제 기록 수와 최대 보관 수를 구분합니다. 개별 오류의 NSID·command·status 정보를 동일한 controller에서 얻은 정보인지 확인합니다.
base|5.1.12.1.3|SMART / Health / LID 02h|Composite Temperature·센서 온도·Critical Warning 등 현재 상태를 보고합니다. 온도는 Kelvin입니다. WCTEMP/CCTEMP는 Identify의 기준이고 FID 04h는 설정 threshold입니다. Namespace별 조회 능력은 LPA.SMARTS로 확인합니다.
base|5.1.12.1.4|Firmware Slot Information / LID 03h|AFI는 현재 활성 slot과 다음 활성화 slot을 구분하며 slot별 firmware revision을 담습니다. FR은 현재 활성 slot의 리비전과 대조합니다. FRMW.NOFS로 slot 수, FFSRO로 slot 1 보호 여부를 확인합니다.
base|5.1.12.1.6|Commands Supported and Effects / LID 05h|특정 I/O Command Set의 명령 지원은 CSUPP로 확인합니다. CCC=1은 controller capability, NIC=1은 namespace inventory, NCC=1은 namespace capability, LBCC=1은 user data content를 변경할 수 있음을 나타냅니다. 효과가 가능하다는 보고는 매번 실제로 변경됨을 뜻하지 않습니다. Aggregate ONCS를 특정 command set 지원으로 바로 확정하지 않습니다. LPA.MLPS는 CSP의 scope 보고와 연결됩니다.
base|5.1.12.1.7|Device Self-test / LID 06h|현재 self-test operation과 completion 및 결과 entry를 보고합니다. OACS.DSTS는 지원, DSTO는 동시 실행 scope, EDSTT는 PS0의 extended 예상 시간입니다. 결과와 능력·예상 시간을 구분합니다.
base|5.1.12.1.8|Host-Initiated Telemetry / LID 07h|Host가 요청한 telemetry 데이터입니다. LPA.TS는 log 지원, DA4S는 Data Area 4 지원을 나타냅니다. 수집 상태와 능력 비트를 구분합니다.
base|5.1.12.1.9|Controller-Initiated Telemetry / LID 08h|Controller가 시작한 telemetry와 data availability를 보고합니다. LPA.TS와 DA4S, FID 0Bh.TLN enable을 함께 봅니다. Data Available의 0→1 전이가 통지 조건과 연결됩니다.
base|5.1.12.1.10|Endurance Group Information / LID 09h|Endurance Group별 상태와 capacity 정보를 보고합니다. ENDGIDMAX는 ID 상한이고 로그는 선택한 group에서 조회한 정보입니다. 조회 대상 group·domain·controller가 서로 일치하는지 확인합니다.
base|5.1.12.1.11|Predictable Latency Per NVM Set / LID 0Ah|NVM Set별 Predictable Latency 상태를 보고합니다. CTRATT.PLM/NSETS는 능력이고 FID 13h/14h 및 로그는 현재 구성을 설명합니다.
base|5.1.12.1.12|Predictable Latency Event Aggregate / LID 0Bh|NVM Set별 pending event를 모아 보고합니다. OAES.PLEAN은 통지 능력, FID 0Bh.PLEALCN은 통지 enable입니다.
base|5.1.12.1.15|Endurance Group Event Aggregate / LID 0Fh|Endurance Group별 pending event를 모아 보고합니다. OAES.EGEAN과 FID 0Bh.EGEALCN을 연결합니다. Endurance Group 미지원 상태에서 해당 enable 요청은 Invalid Field in Command로 중단해야 합니다.
base|5.1.12.1.18|Feature Identifiers Supported and Effects / LID 12h|Feature별 지원과 효과를 확인하는 로그입니다. LPA.MLPS=1이면 지원이 필요하고 0이어도 선택적으로 지원할 수 있습니다. Feature 현재값은 Get Features로 별도 확인합니다. 지원·scope·effect가 현재 enable과 같은 뜻은 아닙니다.
base|5.1.12.1.25|Reachability Groups / LID 1Ah|Reachability group 구성 정보를 보고합니다. CRCAP.RRSUP는 능력, OAES.RGCNS는 통지 지원, FID 0Bh.RGRP0는 해당 log 변경 통지 enable입니다.
base|5.1.12.1.26|Reachability Associations / LID 1Bh|Reachability association 구성 정보를 보고합니다. OAES.RGCNS 지원은 FID 0Bh의 RASSN과 RGRP0 두 enable에 연결됩니다. 하나의 비트를 단순히 복사하여 비교하지 않습니다.
base|5.1.12.1.28|FDP Configurations / LID 20h|Endurance Group의 FDP configuration을 보고합니다. CTRATT.FDPS는 subsystem의 지원 능력이며 현재 configuration·enable은 이 로그와 FID 1Dh에서 동일한 group을 대상으로 확인합니다.
base|5.1.12.1.13|ANA / LID 0Ch|ANA group별 현재 접근 상태를 보고합니다. ANACAP는 보고 가능한 상태, ANAGRPMAX는 ID 상한, NANAGRPID는 지원 group 수입니다. CMIC.ANARS·OAES.ANACN·FID 0Bh를 함께 확인합니다.
base|5.1.12.1.14|Persistent Event / LID 0Dh|Persistent Event Log의 실제 길이와 최대 보고 크기 PELS×64 KiB를 구분합니다. 조회할 때는 동일한 Context와 generation을 유지해야 합니다. 지원 여부는 LPA.PES입니다.
base|5.1.12.1.33|Sanitize Status / LID 81h|진행·완료·실패·검증 등의 sanitize 상태를 보고합니다. SANICAP는 지원 능력이며 현재 sanitize 진행 중이라고 지원 비트가 달라진다고 가정하지 않습니다.
base|5.1.13.2.13|Namespace Granularity / CNS 16h|Namespace 구성 granularity 정보를 반환합니다. CTRATT.NG로 지원을 확인하며 Namespace Management 미지원이면 NG=0입니다.
base|5.1.25|Set Features|Feature별 scope·save·reset 동작 및 validation을 적용합니다. Set으로 바뀌는 Feature 현재값과 Identify의 능력 값을 구분합니다. ONCS.SSFS만으로 모든 Feature가 저장 가능한 것은 아닙니다.
base|5.1.25.1.1|Arbitration / FID 01h|AB=000b~110b는 2^AB 명령이며 111b는 제한 없음입니다. Priority Weight는 0 기반입니다. RAB는 같은 단위의 권장값이므로 AB와 반드시 같을 필요는 없습니다.
base|5.1.25.1.2|Power Management / FID 02h|PS는 0~NPSS의 지원 상태여야 합니다. Set 성공 시 요청 상태에 있어야 하며 APST가 enable이면 그 상태에서도 자동 전환이 계속됩니다. Get의 PS는 현재 상태 또는 전환 중인 목적 상태입니다.
base|5.1.25.1.3|Temperature Threshold / FID 04h|Composite/센서별 over·under threshold를 설정합니다. Over는 온도≥threshold, Under는 온도≤threshold일 때 SMART Critical Warning의 TTC를 설정합니다. Sensor 선택과 threshold 종류를 함께 기록합니다. Composite over threshold의 default는 WCTEMP와 연관되지만 current 설정을 항상 WCTEMP와 같다고 가정하지 않습니다.
base|5.1.25.1.3.1|온도 hysteresis|온도 이벤트의 종료 판정에 hysteresis를 적용합니다. TMPTHH=0이면 이 Feature의 hysteresis를 적용하지 않습니다. Identify.TMPTHMH=0이면 Feature.TMPTHH도 0이어야 합니다. 회복 통지는 OAES.TTHR와 FID 0Bh.TTHRY 조건을 함께 확인합니다.
base|5.1.25.1.4|Volatile Write Cache / FID 06h|VWCP=1이면 이 Feature를 지원해야 합니다. WCE=1은 enable, 0은 disable입니다. 캐시가 없으면 Get/Set 모두 Invalid Field in Command로 중단해야 합니다. 캐시가 있고 disable이면 namespace에 쓴 user data가 persistent이어야 합니다. 전원 손실에도 비휘발 매체 기록을 보장하는 cache는 비휘발성으로 간주하여 이 Feature가 적용되지 않습니다.
base|5.1.25.1.5|Asynchronous Event Configuration / FID 0Bh|이벤트별 통지 enable을 설정합니다. OAES 지원 비트와 위치가 항상 1:1은 아닙니다. 예: OAES.RGCNS 하나가 Feature의 Reachability Group과 Association 두 enable에 연결됩니다. LPA.TS는 Feature.TLN에 연결됩니다. 이벤트 조건·enable·outstanding AER·관련 log 조회를 함께 확인합니다.
base|5.1.25.1.6|Autonomous Power State Transition / FID 0Ch|APSTE와 32-entry 전환 표를 설정·조회합니다. APTS=0이면 APST Feature Get/Set이 Invalid Field in Command로 중단됩니다. APTS=1이면 Feature 지원과 표 내용을 확인합니다. 사용되는 entry의 ITPS는 지원되는 non-operational 상태여야 합니다. ITPT=0인 entry는 자동 전환 비활성입니다. Identify의 NPSS·PSD와 현재 APSTE를 별도로 봅니다.
base|5.1.25.1.7|Timestamp / FID 0Eh|Timestamp 기능을 설정·조회합니다. 지원 여부는 ONCS.TSS입니다. 현재 timestamp의 유효성·단위·동기화 속성은 Feature 반환 구조의 규칙을 적용합니다.
base|5.1.25.1.8|Keep Alive Timer / FID 0Fh|KATO를 설정·조회합니다. KAS가 보고하는 100 ms granularity와 timeout 단위를 구분합니다. KAS=0은 미지원입니다. Traffic Based 동작은 CTRATT.TBKAS 및 Keep Alive 동작 규정을 적용합니다.
base|5.1.25.1.9|Host Controlled Thermal Management / FID 10h|TMT1/TMT2는 Kelvin입니다. 0은 해당 부분 비활성화입니다. 0이 아닌 임계값은 MNTMT~MXTMT 안에 있어야 하며 두 값이 모두 0이 아니면 TMT1<TMT2이어야 합니다. 두 값이 모두 0이 아닌 경우, 값이 같거나 순서가 뒤바뀐 요청 또는 지원 범위를 벗어난 요청은 Invalid Field in Command로 중단합니다. 지원은 HCTMA.HCTMS로 확인합니다.
base|5.1.25.1.10|Non-Operational Power State Config / FID 11h|NOPPME로 non-operational 상태의 background 동작을 위한 일시 전력 초과 허용을 제어합니다. 지원 능력은 CTRATT.NOPSPM이고 현재 설정은 Feature 값입니다.
base|5.1.25.1.11|Read Recovery Level Config / FID 12h|현재 Read Recovery Level을 설정·조회합니다. 선택 레벨이 RRLS에서 지원되는지 확인합니다. Default 4와 Fast Fail 15를 필수 지원하며 Error Recovery/TLER가 동작에 미치는 영향도 함께 확인합니다.
base|5.1.25.1.12|Predictable Latency Mode Config / FID 13h|Predictable Latency Mode의 enable과 구성을 설정합니다. CTRATT.PLM은 지원 능력이며 현재 모드는 Feature에서, 동작 상태는 관련 Log에서 별도로 확인합니다.
base|5.1.25.1.14|Host Behavior Support / FID 16h|Host가 기대하는 동작 속성을 알리는 Feature입니다. ELBAS와 extended LBA format 호환성 등 관련 능력 및 host 설정을 함께 확인합니다.
base|5.1.25.1.15|Sanitize Config / FID 17h|No-Deallocate Response Mode와 sanitize 동작을 설정합니다. SANICAP.NDI 및 Sanitize 명령의 No-Deallocate After Sanitize와 조합하여 승인·거부 및 media deallocation 동작을 결정합니다.
base|5.1.25.1.19|Power Loss Signaling Config / FID 1Bh|Power Loss Signaling 구성을 설정합니다. PLSI는 처리 능력, PSD의 시간값은 해당 처리·복구 시간이며 현재 구성과 구분합니다.
base|5.1.25.1.20|Flexible Data Placement / FID 1Dh|Endurance Group별 FDP enable·구성을 설정합니다. CTRATT.FDPS는 능력이며 enable 상태와 같지 않습니다. FCM과 FDPS는 동시에 1일 수 없습니다.
base|5.1.25.1.28|Host Identifier / FID 81h|64비트/128비트 Host Identifier의 현재값을 관리합니다. CTRATT.HIDS는 128비트 지원 여부입니다. CTRATT.RHII=1이면 reservation 사용 전에 0이 아닌 Host Identifier가 필요합니다.
base|5.1.25.1.31|Namespace Write Protection / FID 84h|현재 namespace 보호 상태를 설정·조회합니다. NWPC가 허용한 상태만 적용하며 Permanent 및 Until Power Cycle의 수명·전환 제약을 따릅니다.
base|5.1.25.1.32|Boot Partition Write Protection / FID 85h|Boot Partition 보호 상태를 제어합니다. BPCAP.SFBPWPS로 이 경로 지원을 확인합니다. RPMB 경로 지원은 BPCAP.RPMBBPWPS로 별도 확인합니다.
base|5.1.25.2.4|Host Memory Buffer / FID 0Dh|EHM은 enable, HSIZE는 할당 크기, HMDLEC는 descriptor 개수입니다. HMPRE/HMMIN은 요청 크기, HMMINDS/HMMAXD는 descriptor 제약입니다. Host descriptor별 크기와 전체 크기를 별도로 비교합니다. HMBR는 non-operational 접근 제한 능력입니다.
base|5.1.26.1.1|Track Send 동작 유형|Host memory와 user data changes 추적을 구분합니다. TRATTR.THMCS/TUDCS는 각각의 지원 능력입니다. 지원하지 않는 유형의 한계 필드를 무시하는 조건을 적용합니다.
base|5.1.27.1.2|Track Memory Changes|Memory Range Tracking Descriptor와 RMRTG의 요청값을 정의합니다. CMMRTD/NMMRTD·MINMRTG/MAXMRTG·MRTLL 제약을 적용합니다. RMRTG 자체의 인코딩과 실제 byte 길이를 구분합니다.
base|6.3|Fabrics Connect|Fabrics association을 만드는 명령입니다. FCATT.NZNSETIDS가 Connect의 non-zero NVMSETID 사용 여부에 연결됩니다. Dynamic/static 모델은 FCATT.DCMS의 값 정의를 따릅니다.
base|7.2|Flush|Namespace의 관련 data·metadata를 비휘발 상태로 commit하도록 요청합니다. NSID=FFFFFFFFh 지원은 VWC.FB에서 확인합니다. WCE=0 또는 비휘발 cache인 경우도 명령 지원·완료 규정을 별도로 적용합니다. Read/Write의 FUA와 Flush를 같은 명령으로 취급하지 않습니다.
base|8.1.1|ANA Reporting|지원 능력은 CMIC.ANARS, 실제 경로 상태는 ANA Log입니다. ANACAP의 상태 보고·group ID 능력과 namespace ANAGRPID를 연결합니다.
base|8.1.1.2|ANA Group|Namespace는 ANA group과 연결되고 controller별 접근 상태를 보고합니다. ANAGIDLWAS=1이면 어떤 controller에라도 attach된 동안 namespace ANAGRPID가 변경되지 않습니다.
base|8.1.1.4|ANA Optimized|최적화된 접근 경로 상태입니다. ANACAP.RANAOS 본문의 Inaccessible 표기와 이름·참조가 불일치하므로 주의사항을 확인합니다.
base|8.1.1.5|ANA Non-Optimized|접근할 수 있지만 최적화되지 않은 경로 상태입니다. ANACAP.RANANOS로 보고 가능 여부를 확인합니다.
base|8.1.1.6|ANA Inaccessible|해당 경로로 namespace 접근이 불가능한 상태입니다. ANACAP.RANAIS로 보고 가능 여부를 확인합니다.
base|8.1.1.7|ANA Persistent Loss|경로의 지속적 손실 상태입니다. ANACAP.RANAPLS로 보고 가능 여부를 확인합니다.
base|8.1.1.8|ANA Change|ANA 상태 변경 중임을 나타냅니다. ANATT는 최대 변경 시간 또는 Change 보고 시간입니다.
base|8.1.2.4|Host의 ANA Change 처리|ANA Change 통지 뒤 로그 재조회와 상태 전환 처리를 설명하는 informative 절입니다. Host의 운용 지침을 Identify의 새로운 필수 값 관계로 바꾸지 않습니다.
base|8.1.3.2|Boot Partition 쓰기|Firmware Image Download/Commit를 통한 boot image 업데이트 절차를 설명합니다. FRMW.SMUD의 중첩 update 감지 여부를 확인합니다.
base|8.1.3.3|Boot Partition 보호|Set Features 및 RPMB 보호 경로와 상호작용을 정의합니다. BPCAP에서 두 경로 능력을 각각 확인합니다.
base|8.1.3.3.1|Feature 경로 Boot 보호|BPCAP.SFBPWPS=1이면 Boot Partition Write Protection Config Feature 경로를 사용할 수 있습니다. 지원 여부와 현재 보호 상태를 구분합니다.
base|8.1.3.3.2|RPMB 경로 Boot 보호|BPCAP.RPMBBPWPS에서 RPMB 경로 지원을 확인합니다. 00b의 버전 제한과 Reserved 11b를 구분합니다.
base|8.1.4|Capacity Management|용량 구성과 NVM Set·Endurance Group을 변경하는 방법을 설명합니다. CTRATT.FCM/VCM·DNVMS/DEG와 총·미할당 용량을 함께 확인합니다.
base|8.1.4.2|Fixed Capacity Management|고정 capacity 관리 방식입니다. CTRATT.FCM=1이면 FDPS=0이어야 합니다.
base|8.1.4.3|Variable Capacity Management|가변 용량 관리 및 NVM Set/Endurance Group 삭제 동작을 설명합니다. CTRATT의 각각의 지원 비트를 확인합니다.
base|8.1.5|Command/Feature Lockdown|명령·Feature의 사용을 잠그는 capability입니다. OACS.CFLS는 지원 여부이며 현재 lock 상태는 별도입니다. CFLS는 subsystem controller 사이에 같아야 합니다.
base|8.1.8|Directives|Directive Send/Receive와 I/O command의 Directive 정보를 정의합니다. OACS.DIRS=1이면 두 Admin 명령을 지원해야 합니다.
base|8.1.10|Flexible Data Placement|FDPS는 지원 여부이고 Endurance Group별 enable·configuration은 Feature와 FDP Log에서 확인합니다. FDPS와 FCM의 상호 배제를 적용합니다.
base|8.1.11|Host-Initiated Refresh|DSTO.HIRS와 RHIRI/HIRT가 관련됩니다. Key Per I/O 필드가 이 절을 참조하는 것은 원문 번호 불일치이며 실제 Key Per I/O 절은 §8.1.13입니다.
base|8.1.12|Host Managed Live Migration|Controller migration과 host memory/user data 변경 추적을 설명합니다. Secondary controller의 HMLMS=0 및 subsystem에 HMLMS=1이 있으면 HMPRE=0 조건을 적용합니다.
base|8.1.13|Key Per I/O|I/O별 key 사용 능력입니다. KPIOC.KPIOS와 KPIOSC로 지원·enable scope를 구분합니다. Figure 312의 §8.1.11 참조 번호와 구분합니다.
base|8.1.15|Namespace Management|생성·삭제·attach 상태와 지원 namespace 수는 서로 다릅니다. OACS.NMS 및 TNVMCAP/UNVMCAP·NN/MNAN·attachment 한계를 함께 확인합니다.
base|8.1.16|Namespace 쓰기 보호|지원 상태는 NWPC, 현재 상태는 FID 84h입니다. 보호 상태에 따라 Write·Format 등의 명령 처리가 달라집니다. 지원 능력 자체가 현재 보호 여부를 나타내지는 않습니다.
base|8.1.16.1|쓰기 보호 전환 규정|No Write Protect·Write Protect·Until Power Cycle·Permanent 상태 전환과 Write Protection Control 지원 조건을 적용합니다. NWPWPS=0이면 PWPS/WPUPCS도 0입니다.
base|8.1.17|전원 관리|PS0부터 NPSS까지의 지원 전원 상태를 PSD로 보고합니다. 이후 state의 최대 전력은 이전 state 이하이어야 합니다. Default state는 구현별이며 PS0이라고 가정하지 않습니다. Non-operational state는 APS/APW/ACTP=0이어야 합니다. 상태 전환의 최대 시간은 이전 state EXLAT+다음 state ENLAT입니다. 상대 성능값은 순서가 반복·생략될 수 있어 state 번호에 따라 단조 증가한다고 가정하지 않습니다.
base|8.1.17.1|Non-operational power state|NOPS=1 상태에서는 I/O를 처리하지 않습니다. Background 작업과 일시 전력 초과 조건은 Non-Operational Power State Config 및 HMB 제한과 연결됩니다.
base|8.1.17.2|자동 전원 전환|Idle 시간과 APST table의 대상 상태에 따라 자동 전환합니다. APTS는 지원, APSTE는 enable, ITPT/ITPS는 전환 정책입니다. Host의 명시적 power state 변경과 자동 전환을 구분합니다.
base|8.1.17.3|전력 측정 workload|APW 000b=No Workload, 001b=Extended Idle Period With Burst Of Random Writes, 010b=Heavy Sequential Writes, 011b~111b=Reserved입니다. APW를 보고하면 APS도 보고해야 하며 ACTP≠0이면 No Workload를 사용하면 안 됩니다.
base|8.1.17.4|Runtime D3 전환|PCIe에서 RTD3에 진입하고 복귀하는 과정을 설명합니다. RTD3E/RTD3R는 μs 지연이며 PSD.ENLAT/EXLAT 및 shutdown 지연과 구분합니다.
base|8.1.17.5|Host thermal management|TMT1/TMT2 threshold에 따른 thermal management와 상태 계수를 정의합니다. HCTMA는 능력, MNTMT/MXTMT는 지원 요청 범위, SMART은 관측 상태입니다.
base|8.1.18|Predictable Latency Mode|지원 여부 CTRATT.PLM과 현재 enable·window 설정·관련 로그를 구분합니다. Deterministic 동작은 host 운용 조건도 충족해야 합니다.
base|8.1.19|Reachability Reporting|Reachability group·association과 namespace RGRPID를 정의합니다. CRCAP.RRSUP 및 RGIDC, OAES.RGCNS와 이벤트 enable을 함께 봅니다.
base|8.1.20|Read Recovery Level|Read 복구 노력·시간의 레벨입니다. RRLS의 지원 비트와 FID 12h 선택값을 비교합니다. Read Recovery Level과 PSD.Relative Read Latency를 혼동하지 않습니다.
base|8.1.21|RPMB|인증된 읽기·쓰기와 replay 방지 동작입니다. RPMBS가 target·크기·접근 단위·인증 능력을 보고합니다. Target이 있으면 Security Send/Receive 지원이 필수입니다.
base|8.1.22|Reservations|Host Identifier와 reservation 등록·획득·해제·보고를 연결합니다. ONCS.RESERVS=1이면 관련 네 명령이 필수입니다. CTRATT.RHII=1이면 0이 아닌 Host Identifier를 먼저 설정합니다.
base|8.1.24|Sanitize|Sanitize 능력·명령 action·현재 상태를 구분합니다. SANICAP와 FID 17h 및 LID 81h를 함께 확인합니다. Format의 secure erase와 Sanitize는 별도 절차입니다.
base|8.1.24.3|Sanitize 상태 머신|Restricted/Unrestricted Processing·Idle·Failure·Media Verification·Post-Verification Deallocation 전이를 정의합니다. NDI/NODRM/NODAS 조합과 VERS 지원을 적용합니다.
base|8.1.25|SQ Association|Submission Queue 사이의 association 능력입니다. CTRATT.SQA는 지원을 나타내며 실제 queue 설정과 구분합니다.
base|8.1.26|표준 vendor 명령 형식|AVSCC.VSCF와 ICSVSCC.SNVSCF가 1이면 각각 vendor Admin/I/O 명령이 Figure 93 형식을 사용합니다. 0은 vendor-defined 형식입니다.
base|8.1.28|Vendor 정보 UUID|UUID List 및 UUID Index를 통해 vendor 정보의 어떤 vendor 정보인지 구분합니다. CTRATT.ULIST로 List 지원을 확인합니다.
base|8.2.5.2|PLS Forced Quiescence|PLSFQ가 지원하는 전원 손실 신호 처리입니다. PSD.FQVT/FQVTS는 실패가 없을 때 완료까지의 최악 시간입니다.
base|8.2.5.3|PLS Emergency Power Fail|PLSEPF가 지원하는 처리입니다. EPFVT는 처리 시간, EPFRT는 power loss 전 처리 완료 후 첫 initialization 시간입니다. 두 시간과 scale을 구분합니다.
base|9.6|통신 손실 처리|통신이 끊겼을 때 아직 완료되지 않은 명령을 종료하는 방법을 설명합니다. CQT의 적용 조건을 Keep Alive Timeout과 함께 확인합니다.
nvm|2.1.4|NVM atomic operation|Controller AWUN/AWUPF/ACWU는 모든 namespace·format에 유효한 불변 baseline입니다. Namespace별 값은 baseline 이상이어야 합니다. Namespace format 변경으로 namespace atomicity·boundary 값은 달라질 수 있습니다. 정상 동작과 전원 실패 보장을 구분합니다.
nvm|2.1.4.1|Single Atomicity Mode|명령당 최대 하나의 atomic write입니다. 지원되는 namespace 값은 NAWUN≥AWUN, NAWUPF≥AWUPF 및 NAWUPF≤NAWUN, NACWU≥ACWU 조건을 적용합니다. Boundary가 있으면 크기·offset 제약을 함께 확인합니다.
nvm|2.1.4.2|AWUN/NAWUN 동작|정상 동작의 명령 간 write serialization을 보장합니다. Namespace별 보장에는 write 길이와 boundary 교차 여부가 중요합니다. FID 0Ah.DN=1이면 host가 정상 atomicity를 요구하지 않음을 알립니다. 이것이 Identify baseline 변경을 요구하는 것은 아닙니다.
nvm|2.1.4.3|AWUPF/NAWUPF 동작|길이가 유효 한계 이하이고 boundary를 넘지 않는 power fail/error interrupted write는 torn mix가 아닌 all-old 또는 all-new 데이터가 반환되는 보장입니다. Figure 117 AWUPF의 이전 write 반환 문구와 차이가 있으므로 원문 불일치 주의사항을 함께 봅니다.
nvm|2.1.4.3.2|비휘발성 요구|성공한 write 뒤에는 최신 데이터를 반환해야 하지만, volatile cache enable·FUA=0·관련 Flush 미완료·정상 shutdown 미완료 후 전원 손실 등 나열된 모든 조건이 맞으면 cache의 미영속 데이터 대신 이전 데이터가 반환될 수 있습니다. Atomicity와 persistence는 별개입니다.
nvm|2.1.4.4|Atomic boundary|Boundary는 namespace별입니다. Controller baseline은 boundary를 넘는 write에도 지원되어야 하며 보장하지 못하면 AWUN/AWUPF/ACWU를 0h(1 LBA)로 설정합니다. 지원 boundary size는 관련 atomic unit 이상이고 NABO는 NABSN/NABSPF 이하입니다. 0 기반 unit 수와 boundary size 표현을 각각 해석합니다.
nvm|2.1.4.5|Multiple Atomicity Mode|Boundary를 넘는 write를 atomic LBA subrange로 나누며 각 subrange에 별도로 보장합니다. Namespace 값을 보고하면 NABSN=NAWUN=NABSPF=NAWUPF, 미보고이면 NABSN=AWUN=NABSPF=AWUPF 조건입니다. Fused operation은 이 모드와 무관하게 Single Atomicity Mode를 사용합니다.
nvm|3.3.2|Copy|Copy의 descriptor format·크기·namespace 조건과 write atomicity를 확인합니다. ONCS.NVMCPYS/NVMCSA/NVMAFC와 CDFS를 함께 봅니다. AWUN=FFFFh도 Copy 전체를 무조건 atomic하게 만드는 것은 아닙니다.
nvm|3.3.2.2|Copy atomicity|NVM Command Set 1.0 이후 또는 Base 2.0 이후 규격을 따르거나, Copy와 descriptor format 2h/3h를 지원하는 경우 NVMCSA=1 요구를 적용합니다. Copy의 write 부분을 하나의 write 명령처럼 처리하여 §2.1.4의 atomicity 규정을 적용합니다. 이것이 Copy 전체가 항상 하나의 atomic operation이라는 뜻은 아니며 Multiple Atomicity Mode에서는 subrange별 보장을 적용합니다.
nvm|4.1.3.3|Write Atomicity Normal / FID 0Ah|DN=1이면 AWUN/NAWUN은 요구하지 않고 AWUPF/NAWUPF에 따른 보장만 지켜야 합니다. DN=0이면 네 가지에 따른 보장을 모두 지켜야 합니다. Identify 값을 다시 쓰는 Feature로 설명하지 않습니다.
nvm|4.1.5.1|Identify Namespace / CNS 00h|NSFEAT.NSABP(bit 1)=0이면 NAWUN/NAWUPF/NACWU는 Reserved이며 host는 controller AWUN/AWUPF/ACWU를 사용하는 것이 권고됩니다. NSABP=1인 경우 namespace 값 0은 해당 controller baseline과 같은 크기라는 뜻이며, 0이 아닌 값만 0 기반 block 수(값+1)입니다. NSFEAT.MAM(bit 6)=1은 Multiple, 0은 Single Atomicity Mode입니다. NABSN/NABSPF=0은 해당 boundary 없음이고 0이 아닌 값은 0 기반입니다. 두 boundary가 0이면 NABO도 0이어야 합니다. 현재 LBA format과 유효한 namespace 값을 적용한 뒤 비교합니다.
nvm|4.1.5.4|NVM specific Identify Controller / CNS 06h, CSI 00h|CNS 01h와 별도 응답입니다. VSL/WZSL/WUSL 및 DSM 한계는 ONCS의 variant 비트와 조합해 지원·권장 한계·강제 한계를 결정합니다. MAXWZD=1이면 WZDSL은 WZSL보다 큰 0이 아닌 최대값이어야 합니다. MEM은 metadata 계산에도 적용합니다.
'''
SUMMARIES={}
for line in SUMMARY.strip().splitlines():
    d,s,title,ko=line.split('|',3);SUMMARIES[d+':'+s]=(title,ko)

def bookmarks(doc):
    r=PdfReader(ROOT/DATA['documents'][doc]['filename']);out=[]
    def walk(items):
        for v in items:
            if isinstance(v,list):walk(v)
            else:
                m=re.match(r'^(\d+(?:\.\d+)*)(?:\s+)(.*)',v.title)
                if m:out.append(dict(section=m[1],title=m[2],pdf_page=r.get_destination_page_number(v)+1))
    walk(r.outline);return out

def assemble():
    make_fields()
    fields={f['id']:f for f in DATA['fields']}
    pages={d:json.loads((ROOT/f'source/{d}_pages.json').read_text(encoding='utf-8')) for d in ['base','nvm']}
    outlines={d:bookmarks(d) for d in ['base','nvm']}
    nodes={}
    for key,(title,ko) in SUMMARIES.items():
        doc,sec=key.split(':');bm=next((b for b in outlines[doc] if b['section']==sec),None)
        assert bm, f'No source bookmark: {key}'
        start=bm['pdf_page'];idx=outlines[doc].index(bm)
        nxt=outlines[doc][idx+1] if idx+1<len(outlines[doc]) else None
        end=nxt['pdf_page'] if nxt else start
        source_pages=[]
        for n in range(start,end+1):
            t=pages[doc][n-1]['text']
            # Excerpts are identified as page context; never pretend cropped text is a full clause.
            figs=[int(v) for v in re.findall(r'^Figure\s+(\d+):',t,re.M)]
            source_pages.append(dict(doc=doc,section=sec,pdf_page=n,page=n-22 if doc=='base' else n,figure=None,figures=figs,english=t))
        nodes[key]=dict(id=key,title=title,name=bm['title'],ko=ko,sources=source_pages,
                        topic='관련 규정',rules=[],edges=[],notes=[],external=[],kind='reference')
    # Resolve every direct numbered section reference. A wrong reference stays visible with an annotation.
    for f in fields.values():
        refs=set()
        for doc,text in [('base',f['english']),('nvm',f.get('nvm_english',''))]:
            refs.update(doc+':'+s for s in re.findall(r'section\s+(\d+(?:\.\d+)+)',text,re.I))
        for key in sorted(refs):
            assert key in nodes,f'Unintegrated section {f["id"]} -> {key}'
            f['edges'].append(dict(target=key,type='참조 규정',text=nodes[key]['ko']))
    def edge(a,b,kind,text):
        assert a in fields or a in nodes,a
        assert b in fields or b in nodes,b
        (fields.get(a) or nodes[a])['edges'].append(dict(target=b,type=kind,text=text))
    def group(keys,ref,kind,text):
        for k in keys.split():edge(k,ref,kind,text)
    for f in fields.values():
        if f['id'].startswith('RESERVED_') or any(b['english'].strip()=='Reserved' for b in f['bits']):
            edge(f['id'],'base:1.4.1','값 사이의 제약','Reserved 비트·바이트는 0h 또는 향후 확장 규정에 따른 값을 사용합니다. 이 자료의 두 버전에 없는 확장을 임의로 적용하지 않습니다.')
    group('SN MN','base:1.4.2','값 형식','ASCII 허용 범위·왼쪽 정렬·오른쪽 공백 padding을 적용합니다.')
    group('RAB','base:5.1.25.1.1','현재 설정/상태','RAB는 권장값, Feature.AB는 설정값입니다. 필수 일치 관계가 아닙니다.')
    group('MDTS','base:3.1.4.1','값 사이의 제약','CAP.MPSMIN과 MDTS로 byte 한계를 계산합니다.')
    edge('MDTS','CTRATT','명령 동작 영향','MEM에 따라 interleaved metadata 포함 여부가 달라집니다.')
    group('FR FRMW MTFA MPTFAWR FWUG','base:5.1.12.1.4','현재 설정/상태','같은 controller/domain의 현재 활성 slot·리비전·다음 활성 slot을 구분합니다.')
    group('NPSS APSTA','base:5.1.25.1.6','현재 설정/상태','지원 능력과 APSTE 및 32-entry ITPT/ITPS 전환 표를 분리합니다.')
    group('NPSS APSTA','base:5.1.25.1.2','명령 동작 영향','PS는 0~NPSS의 지원 상태여야 합니다. APST enable이면 명시 전환 후에도 자동 전환이 계속됩니다.')
    group('NPSS','APSTA','지원 능력','NPSS가 지원 state 범위, APSTA가 자동 전환 지원을 나타냅니다.')
    for i in range(32):
        k=f'PSD{i}'
        edge('NPSS',k,'지원 능력',f'NPSS≥{i}이면 이 descriptor가 지원 state {i}를 설명합니다.')
        group(k,'base:8.1.17','명령 동작 영향','전력·entry/exit latency·NOPS를 전원 전환과 함께 확인합니다.')
        group(k,'base:8.1.17.3','값 사이의 제약','APW workload와 APS 및 ACTP 측정 조건을 확인합니다.')
        edge(k,'PLSI','지원 능력','PLSFQ/PLSEPF 미지원 시 관련 시간값은 0이어야 합니다.')
    group('WCTEMP CCTEMP TMPTHHA','base:5.1.12.1.3','현재 설정/상태','온도 기준·설정 threshold·현재 측정 온도와 Critical Warning을 구분합니다.')
    group('WCTEMP CCTEMP TMPTHHA','base:5.1.25.1.3','현재 설정/상태','FID 04h의 sensor·threshold type·current/default를 구분하여 비교합니다.')
    group('HCTMA MNTMT MXTMT','base:5.1.25.1.9','명령 동작 영향','Feature의 TMT1/TMT2 유효 범위를 결정합니다.')
    group('OAES AERL LPA','base:5.1.25.1.5','현재 설정/상태','지원 이벤트와 enable 및 outstanding AER를 별도로 확인합니다. 비트 위치를 단순 대입하지 않습니다.')
    group('ELPE','base:5.1.12.1.2','값 사이의 제약','최대 entry 수는 ELPE+1입니다.')
    group('LPA','base:5.1.12.1.1','지원 능력','MLPS=1이면 지원 필수이고 0이어도 선택 지원 가능합니다.')
    group('LPA PELS','base:5.1.12.1.14','값 사이의 제약','PES 지원과 PELS 최대 크기를 실제 로그 길이와 구분합니다.')
    group('OACS EDSTT DSTO','base:5.1.12.1.7','현재 설정/상태','Self-test 지원·동시 실행 범위·예상 시간과 현재 진행/결과를 구분합니다.')
    group('LPA','base:5.1.12.1.8','지원 능력','TS와 DA4S는 Host-Initiated Telemetry 및 Data Area 4 지원을 나타냅니다.')
    group('LPA','base:5.1.12.1.9','현재 설정/상태','Controller-Initiated data availability·통지 enable과 TS 능력을 구분합니다.')
    group('LPA ONCS','base:5.1.12.1.18','지원 능력','Feature별 지원·효과와 Get Features 현재값을 별도로 확인합니다.')
    group('OAES ENDGIDMAX','base:5.1.12.1.15','현재 설정/상태','Endurance Group event 지원과 pending event·enable을 구분합니다.')
    group('CTRATT ENDGIDMAX MEGCAP','base:5.1.12.1.10','현재 설정/상태','지원 능력·ID 상한과 특정 group의 상태·capacity를 구분합니다.')
    group('CTRATT OAES','base:5.1.12.1.11','현재 설정/상태','Predictable Latency의 capability와 현재 NVM Set별 상태를 구분합니다.')
    group('CTRATT OAES','base:5.1.12.1.12','현재 설정/상태','Pending event aggregate와 통지 enable·지원 비트를 함께 확인합니다.')
    group('CRCAP OAES','base:5.1.12.1.25','현재 설정/상태','Reachability Group Log 변경은 FID 0Bh.RGRP0에 연결됩니다.')
    group('CRCAP OAES','base:5.1.12.1.26','현재 설정/상태','Reachability Association Log 변경은 FID 0Bh.RASSN에 연결됩니다.')
    group('CTRATT','base:5.1.12.1.28','현재 설정/상태','FDPS와 Endurance Group별 FDP configuration·enable을 구분합니다.')
    group('HMPRE HMMIN HMMINDS HMMAXD','base:5.1.25.2.4','현재 설정/상태','요청/한계 값과 실제 HSIZE·HMDLEC·descriptor 크기·EHM을 구분합니다.')
    edge('HMPRE','OACS','값 사이의 제약','Subsystem controller 중 하나라도 HMLMS=1이면 HMPRE=0이어야 합니다.')
    group('RRLS','base:5.1.25.1.11','현재 설정/상태','선택된 Read Recovery Level이 RRLS에서 지원되는지 확인합니다.')
    group('NWPC','base:5.1.25.1.31','현재 설정/상태','현재 쓰기 보호 상태는 FID 84h, 가능한 상태는 NWPC입니다.')
    group('BPCAP','base:5.1.25.1.32','현재 설정/상태','현재 Boot Partition 쓰기 보호 상태와 지원 경로를 구분합니다.')
    group('DSTO EDSTT RHIRI HIRT','OACS','지원 능력','DSTS가 self-test 지원의 조건이며 HIRS 미지원 시 refresh 시간값은 0입니다.')
    group('SANICAP','base:5.1.12.1.33','현재 설정/상태','지원 능력과 현재 sanitize 상태·진행률을 구분합니다.')
    group('KPIOC','base:8.1.13','명령 동작 영향','Key Per I/O의 실제 절을 연결합니다. Figure 312의 §8.1.11 번호 불일치는 주의사항으로 유지합니다.')
    group('KAS CQT','base:5.1.25.1.8','현재 설정/상태','granularity·현재 KATO·quiesce 시간은 서로 다른 값입니다.')
    group('CMIC ANATT ANACAP ANAGRPMAX NANAGRPID MNAN','base:5.1.12.1.13','현재 설정/상태','ANA 지원 능력·group 한계와 현재 log의 경로 상태를 구분합니다.')
    group('NN MNAN MAXDNA MAXCNA','base:8.1.15','값 사이의 제약','ID 상한·지원 수·현재 allocated/active 수·attachment 수를 각각 비교합니다.')
    group('TNVMCAP UNVMCAP','base:8.1.15','값 변경 조건','Namespace 또는 용량 구성이 바뀌면 같은 controller에서 다시 조회합니다. 용량 산정은 capacity 모델을 적용합니다.')
    group('TNVMCAP UNVMCAP MEGCAP','base:3.8.3','값 변경 조건','Single-/multi-domain의 보고 범위와 entity 생성/삭제에 따른 capacity 재조회 조건을 적용합니다.')
    group('FR FRMW OACS CTRATT ONCS TNVMCAP UNVMCAP NN','base:5.1.12.1.6','값 변경 조건','CCC/NIC/NCC 등 명령 effect와 실제 명령·scope에 따라 재조회할 대상을 판단합니다. 효과 가능성과 실제 변경을 구분합니다.')
    group('AWUN AWUPF ACWU','nvm:4.1.5.1','값 사이의 제약','NSFEAT의 적용 조건과 namespace atomic 값·boundary·현재 LBA format을 함께 확인합니다.')
    group('AWUN AWUPF ACWU','nvm:2.1.4.4','명령 동작 영향','Baseline은 atomic boundary를 넘는 경우도 보장하도록 정해야 합니다. Namespace별 값은 boundary 교차 조건을 별도로 적용합니다.')
    group('AWUN AWUPF','nvm:2.1.4.5','명령 동작 영향','Multiple Atomicity Mode는 명령 전체가 아닌 atomic LBA subrange별 보장을 적용합니다.')
    group('AWUN','nvm:4.1.3.3','현재 설정/상태','DN=1이면 정상 atomicity는 요구하지 않지만 전원 실패 시 atomicity 보장은 지켜야 합니다. Identify baseline 변경 조건이 아닙니다.')
    edge('AWUPF','AWUN','값 사이의 제약','AWUPF≤AWUN이어야 합니다.')
    edge('ACWU','FUSES','지원 능력','FCWS=0이면 ACWU=0, FCWS=1이면 ACWU 지원이 필수입니다.')
    group('VWC AWUPF','nvm:2.1.4.3.2','명령 동작 영향','Write atomicity와 cache persistence를 구분하며 WCE/FUA/Flush/shutdown 조건을 함께 봅니다.')
    group('ONCS CDFS AWUN','nvm:3.3.2','명령 동작 영향','Copy support·format·atomicity·fast copy 능력을 각각 확인합니다.')
    group('ONCS MDTS CTRATT','nvm:4.1.5.4','명령 동작 영향','CNS 06h variant size limits를 확인합니다. CNS 01h 응답에 섞어 해석하지 않습니다.')
    group('ONCS','base:5.1.11','현재 설정/상태','SSFS와 Select 및 Feature별 supported capabilities를 함께 확인합니다.')
    group('ONCS CTRATT','base:5.1.25.1.28','현재 설정/상태','Reservation을 사용할 때 Host Identifier와 RHII 조건을 확인합니다.')
    group('SQES CQES','base:3.1.4.5','값 사이의 제약','CC의 entry 지수가 Identify 최소·최대 범위 안인지 확인합니다.')
    group('TRATTR CMMRTD NMMRTD MINMRTG MAXMRTG MCUDMQ MNSUDMQ MCMR NMCMR MCDQPC','base:8.1.12','지원 능력','Tracking 유형 지원과 controller/subsystem 한계를 분리하여 확인합니다.')
    group('IOCCSZ IORCSZ ICDOFF FCATT MSDBD OFCS','base:6.3','명령 동작 영향','Message-based transport의 capsule·Connect·controller 모델 조건을 적용합니다.')
    # Hand-authored checks: applicability, observations, required relation, and exact evidence.
    def rule(keys,condition,observe,expected,ref=None,level='SHALL'):
        for k in keys.split():
            node=fields.get(k) or nodes.get(k);assert node,k
            evidence=[{k:v for k,v in s.items() if k!='english'} for s in nodes[ref]['sources']] if ref else node['sources'][:1]
            if not ref and 'psd_index' in node:evidence=[s for s in node['sources'] if s['figure']==313]
            node['rules'].append(dict(condition=condition,observe=observe,expected=expected,level=level,sources=evidence))
    rule('VER','Base 1.2 이상 구현','VER, VS property','VER=VS이며 VER≠0이어야 합니다.')
    rule('CNTRLTYPE','Base 1.4 이상 구현','VER, CNTRLTYPE','CNTRLTYPE은 1h/2h/3h 중 실제 유형이며 0h를 사용하면 안 됩니다.')
    rule('SN MN','Discovery가 SN 또는 MN 중 하나에 non-null 값을 보고','SN, MN, controller 유형','둘 모두 non-null이어야 합니다. 문자열 공백 padding 규칙도 적용합니다.')
    rule('MDTS','MDTS≠0이고 host-accessible memory를 전송하는 명령','MDTS, CAP.MPSMIN, CTRATT.MEM, data/metadata 배치, SGL 길이','한계=2^MDTS×2^(12+CAP.MPSMIN) B. MEM과 SGL Bit Bucket 규칙에 따라 합산하여 초과 명령은 Invalid Field in Command로 중단합니다.')
    rule('CTRATT','FCM 또는 FDPS=1','CTRATT.FCM, CTRATT.FDPS','FCM과 FDPS가 동시에 1이면 안 됩니다.')
    rule('CTRATT','Namespace Management 미지원','OACS.NMS, CTRATT.NG','NG=0이어야 합니다.')
    rule('RRLS','Read Recovery Level 지원','CTRATT.RRLVLS, RRLS','Level 4와 15 지원 비트는 반드시 1입니다.')
    rule('VWCI','VWCRV=0','VWCI.VWCRV/VWCR','VWCR=0이어야 합니다.')
    rule('OACS','Secondary controller','controller 유형·primary/secondary 관계, HMLMS','HMLMS=0이어야 합니다.')
    rule('OACS','Subsystem 내 controller들을 비교','동일 subsystem의 OACS.CFLS','모든 controller의 CFLS가 같아야 합니다.')
    rule('FRMW','Firmware slot 보고','NOFS','1≤NOFS≤7이어야 합니다.')
    rule('FR','같은 domain의 현재 활성 firmware 확인','FR, Firmware Slot Log.AFI, 활성 slot의 revision','FR은 현재 활성 revision과 같아야 합니다. 다음 활성 slot과 비교하지 않습니다.','base:5.1.12.1.4')
    rule('NPSS','I/O 또는 Administrative controller의 전원 상태','NPSS, 지원 PSD','0≤NPSS≤31이며 지원 상태는 PS0~PSNPSS입니다.')
    rule('APSTA','APTS=0','APSTA.APTS, FID 0Ch Get/Set 결과','APST Feature Get/Set을 Invalid Field in Command로 중단해야 합니다.','base:5.1.25.1.6')
    rule('APSTA','APSTE=1이고 ITPT≠0인 전환 entry','NPSS, ITPS, 목적지 PSD.NOPS','ITPS는 지원하는 non-operational state를 가리켜야 합니다.','base:5.1.25.1.6')
    rule('NPSS','FID 02h Set Features','Feature.PS, NPSS','PS는 지원 state여야 합니다. 미지원 요청은 명령을 중단해야 하고 Invalid Field in Command 반환은 권고입니다.','base:5.1.25.1.2')
    rule('WCTEMP CCTEMP','Base 1.2 이상 구현','VER, WCTEMP, CCTEMP','두 온도 모두 0이 아닌 값을 보고해야 합니다. 현재 Feature threshold와 반드시 같은 값이라는 요구는 아닙니다.')
    rule('HMPRE HMMIN','HMB 크기 보고','HMPRE, HMMIN','HMPRE≥HMMIN이어야 합니다.')
    rule('HMPRE','Subsystem의 controller 하나 이상에서 HMLMS=1','Subsystem의 모든 관련 OACS.HMLMS, HMPRE','HMPRE=0이어야 합니다. 단일 controller 정보만으로 subsystem 전체 조건을 확정하지 않습니다.')
    rule('RPMBS','NRPMBU>0','RPMBS, OACS.SSRS, 각 RPMB 능력','Security Send/Receive를 지원하고 모든 RPMB target의 능력이 같아야 합니다.')
    rule('DSTO RHIRI HIRT','OACS.DSTS=0 또는 DSTO.HIRS=0','DSTS, HIRS, RHIRI, HIRT','DSTS=0이면 HIRS=0. HIRS=0이면 RHIRI=HIRT=0이어야 합니다.')
    rule('HCTMA','HCTMS=1','HCTMS, FID 10h Get/Set 지원','FID 10h Get Features와 Set Features를 지원해야 합니다.')
    rule('MNTMT MXTMT','FID 10h에 0이 아닌 온도 임계값을 요청할 때','TMT1, TMT2, MNTMT, MXTMT','0이 아닌 온도 값은 지원 범위 안에 있어야 합니다. 두 값이 모두 0이 아니면 TMT1<TMT2여야 합니다. 값이 같거나 순서가 뒤바뀐 요청, 지원 범위를 벗어난 요청은 Invalid Field in Command로 중단합니다. 0은 해당 기능을 비활성화한다는 뜻입니다.','base:5.1.25.1.9')
    rule('SANICAP','BES=0이고 CES=0','SANICAP.BES/CES/VERS','VERS=0이어야 합니다.')
    rule('SANICAP','NDI=1이고 NODAS=1 요청','SANICAP.NDI, FID 17h 지원·NODRM, 명령.NODAS','NODRM=0 또는 Feature 미지원이면 Invalid Field in Command로 중단. NODRM=1이면 해당 Idle 전이 전 deallocate해야 합니다.','base:5.1.25.1.15')
    rule('ANATT ANAGRPMAX NANAGRPID','ANA Reporting 지원 여부','CMIC.ANARS, ANATT, ANAGRPMAX, NANAGRPID','지원 시 ANATT·ANAGRPMAX는 0이 아닌 값, 0<NANAGRPID≤ANAGRPMAX. 미지원이면 세 필드 모두 0이어야 합니다.')
    rule('ANACAP','Namespace Management 미지원','OACS.NMS, ANACAP.ANAGIDS','ANAGIDS=0이어야 합니다.')
    rule('DID','Domain 수 보고','CTRATT.MDS, DID','MDS=1이면 DID≠0; single domain이면 DID=0이어야 합니다.')
    rule('MPTFAWR','Reset 없는 활성화 지원 여부','FRMW.FAWR, VER, MPTFAWR','FAWR=0이면 0. Base 2.1 이상이고 FAWR=1이면 0이 아닌 값을 보고해야 합니다.')
    rule('TMPTHHA','TMPTHMH=0','TMPTHHA, FID 04h.TMPTHH','Feature.TMPTHH도 0이어야 합니다.','base:5.1.25.1.3.1')
    rule('SQES CQES','I/O queue entry 설정','MINSQES/MAXSQES, MINCQES/MAXCQES, CC.IOSQES/IOCQES','MINSQES=6, MINCQES=4; 최대 지수≥최소 지수. CC의 지수는 해당 최소~최대 범위에 있어야 합니다.','base:3.1.4.5')
    rule('VWC','VWCP=0','Identify.VWCP, FID 06h Get/Set 결과','Get/Set 모두 Invalid Field in Command로 중단해야 합니다.','base:5.1.25.1.4')
    rule('VWC','VWCP=1','Identify.VWCP, FID 06h 지원·WCE','FID 06h 지원 필수. WCE=0이면 namespace에 쓰는 user data는 persistent이어야 합니다. VWCP와 WCE를 같은 상태 비트로 취급하지 않습니다.','base:5.1.25.1.4')
    rule('VWC','Flush에 NSID=FFFFFFFFh 지정','VWC.FB, Flush NSID·status','FB=10b이면 Invalid Namespace or Format으로 중단, FB=11b이면 broadcast 지원입니다.')
    rule('AWUN AWUPF','Logical block command set의 atomic baseline','AWUN, AWUPF','AWUPF≤AWUN이어야 합니다. Raw 0 기반 값 비교와 실제 block 수 비교는 같은 순서를 갖습니다.','nvm:2.1.4.1')
    rule('AWUN AWUPF ACWU','NSABP와 namespace 0 상속 규칙을 적용한 뒤 유효 namespace atomic 값 비교','NSFEAT.NSABP, NAWUN, NAWUPF, NACWU, AWUN, AWUPF, ACWU','NSABP=0이면 controller baseline 사용 권고. NSABP=1에서 namespace 값 0은 해당 baseline을 상속합니다. 이를 먼저 치환한 유효 값으로 NAWUN≥AWUN, NAWUPF≥AWUPF 및 NAWUPF≤NAWUN, NACWU≥ACWU를 비교합니다.','nvm:4.1.5.1')
    rule('AWUN AWUPF','FID 0Ah 설정','DN, AWUN/NAWUN, AWUPF/NAWUPF','DN=1이면 정상 단위는 요구하지 않지만 전원 실패 시 atomicity 보장은 지켜야 합니다. DN=0이면 네 단위에 따른 보장을 모두 지켜야 합니다.','nvm:4.1.3.3')
    rule('ACWU','Fused Compare+Write 지원 여부','FUSES.FCWS, ACWU','FCWS=1이면 ACWU 필드 지원 필수, FCWS=0이면 ACWU=0이어야 합니다.')
    rule('NWPC','NWPWPS=0','NWPC.NWPWPS/WPUPCS/PWPS','WPUPCS=PWPS=0이어야 합니다.')
    rule('MNAN','ANA Reporting 지원','CMIC.ANARS, MNAN, NN','0<MNAN≤NN이어야 합니다.')
    rule('MAXDNA','동일 domain I/O controller 비교','DID, 각 controller.MAXDNA','Domain의 모든 I/O controller 값이 같아야 합니다.')
    rule('MAXCNA','최대 attachment 값 사용','MAXCNA, MNAN 및 NN에 따른 지원 개수','최대 attachment 수는 subsystem 지원 namespace 수 이하입니다. 0의 미지정 의미를 먼저 적용합니다.')
    rule('CMMRTD NMMRTD MINMRTG MAXMRTG','THMCS=0','TRATTR.THMCS, 해당 tracking 한계','해당 필드는 모두 0이어야 하며 host는 무시하는 것이 권고됩니다.')
    rule('MCUDMQ MNSUDMQ','TUDCS=0','TRATTR.TUDCS, queue 한계','두 필드는 0이어야 하며 host는 무시하는 것이 권고됩니다.')
    rule('NMCMR MCMR','CDQ memory range 한계 보고','NMCMR, MCMR','NMCMR≥MCMR이어야 합니다.')
    rule('IOCCSZ IORCSZ','Message-based I/O controller','IOCCSZ, IORCSZ','IOCCSZ≥4, IORCSZ≥1이어야 합니다. Memory-based에서는 Reserved입니다.')
    rule('ONCS','Verify/Write Zeroes/Write Uncorrectable variant 비트=0','ONCS 비트와 CNS 06h의 VSL/WZSL/WUSL','한계 값이 0이 아니면 명령을 지원한다는 뜻입니다. 따라서 지원 비트가 0이라는 이유만으로 미지원이라고 판단하지 않습니다.','nvm:4.1.5.4',level='해석 안내')
    rule('ONCS','MAXWZD=1','WZSL, WZDSL, Write Zeroes 지원','WZSL과 WZDSL이 모두 0이 아니고 WZDSL>WZSL이어야 합니다. 미지원 또는 WZSL=0이면 MAXWZD=0입니다.','nvm:4.1.5.4')
    # Per-bit obligations retain source-level wording and conditional context.
    for f in fields.values():
        for b in f['bits']:
            if 'shall' in b['english'].lower():
                f['rules'].append(dict(condition=f"비트 {b['range']} / {b['title']} 정의의 조건에 해당할 때",observe=f"{f['id']}.{b['title']} 및 아래 정의에 등장하는 관련 값",expected=b['ko'],level='SHALL (비트 정의)',sources=[b['source']]))
    for i in range(32):
        k=f'PSD{i}'
        rule(k,f'PS{i}가 지원 state인 경우','NPSS, RWL/RWT/RRL/RRT','각 상대값은 지원 state 수(NPSS+1)보다 작아야 합니다. 물리적인 시간·throughput 단위가 아닙니다.',level='SHALL')
        rule(k,'PLSFQ=0 또는 PLSEPF=0','PLSI, FQVT, EPFVT, EPFRT','PLSFQ=0이면 FQVT=0. PLSEPF=0이면 EPFVT=EPFRT=0이어야 합니다.')
        rule(k,'PLS 관련 시간값이 0','EPFVT/FQVT/EPFRT 및 대응 scale','각 시간값이 0이면 대응 scale도 0이어야 하고 host는 무시합니다.')
        rule(k,'NOPS=1','PSD.NOPS/APS/APW/ACTP','Non-operational state의 APS=APW=ACTP=0이어야 합니다.','base:8.1.17')
        rule(k,'APW workload 보고 또는 ACTP가 0이 아닌 경우','PSD.APW/APS/ACTP','APW를 보고하면 APS도 보고해야 합니다. ACTP≠0이면 APW=No Workload를 사용하면 안 됩니다.')
    rule('NPSS','지원 PSD의 최대 전력을 비교','각 PSD.MP, MXPS, NPSS','Scale을 적용한 이후 state의 최대 전력은 이전 state 이하이어야 합니다. 미보고 전력은 추가 근거 없이 수치 비교하지 않습니다.','base:8.1.17')
    rule('APSTA','지원하지 않는 power state의 APST table entry','NPSS, APST 32-entry 표','미지원 state의 entry는 모두 0이어야 합니다. ITPT=0일 때 ITPS도 0을 쓰는 것이 권고됩니다.','base:5.1.25.1.6')
    # Explicit source ambiguities; no fabricated resolution.
    fields['ANACAP']['notes'].append('원문 불일치: RANAOS 이름·§8.1.1.4 참조는 Optimized지만 bit 0 설명은 Inaccessible입니다. 확정 정합성 판정에서 제외하고 원문/정오표를 확인하세요.')
    fields['FUSES']['notes'].append('원문 정의 공백: 필드 크기는 16비트(523:522)인데 Figure 312의 비트 표는 7:1 Reserved, 0 FCWS만 제공합니다. 15:8은 이 표에서 명시되지 않아 임의로 Reserved 정의를 추가하지 않았습니다.')
    fields['KPIOC']['notes'].append('원문 참조 번호 불일치: Figure 312는 §8.1.11을 가리키지만 해당 절은 Host-Initiated Refresh입니다. Key Per I/O 절은 §8.1.13이며 두 참조를 모두 보존했습니다.')
    fields['AWUPF']['notes'].append('원문 문구 차이: Figure 117(p.91)은 실패 후 이전 성공 write 데이터를 반환한다고 적지만 §2.1.4.3(p.16)은 interrupted write에 all-old 또는 all-new를 허용합니다. 실패/중단 조건을 구분하며 이 자료만으로 문구 충돌을 확정 해소하지 않습니다.')
    for k in ['MINMRTG','MAXMRTG','CMMRTD','NMMRTD']:
        fields[k]['notes'].append('Figure 312 일부 문구는 Track Memory Ranges, Figure 469의 제목은 Track Memory Changes입니다. Figure 469와 §5.1.27.1.2의 실제 요청 구조를 기준으로 확인합니다.')
    # Global source caveats belong on related reference pages too.
    nodes['base:8.1.11']['notes'].extend(fields['KPIOC']['notes'])
    nodes['nvm:2.1.4.3']['notes'].extend(fields['AWUPF']['notes'])
    # Evidence for field-specific numeric rule uses the supplemental NVM table when applicable.
    for k in ['AWUN','AWUPF','ACWU']:
        for r in fields[k]['rules']:
            if len(r['sources'])==1 and r['sources'][0]==fields[k]['sources'][0]:r['sources']=fields[k]['sources'][:]
    EXTERNAL=[
        dict(id='pcie',title='NVMe over PCIe Transport Specification',fields=['VID','SSVID'],needed='PCI Header ID/SS 레지스터 배치·읽기 방법. 두 PDF에는 값 일치 관계만 있습니다.'),
        dict(id='mi',title='NVM Express Management Interface Specification',fields=['FGUID','NVMSR','VWCI','MEC','RESERVED_240','MPTFAWR'],needed='FRU·VPD·관리 endpoint·MI 예약 바이트·out-of-band firmware 절차의 상세 정의.'),
        dict(id='zns',title='Zoned Namespace Command Set Specification',fields=['OAES','ONCS','AWUN','AWUPF','ACWU'],needed='ZNS event/log 및 CSI 02h의 command set별 atomicity·명령 정의. NVM SSD를 기본으로 하며 ZNS 의미를 대신 정의하지 않습니다.'),
        dict(id='ieee',title='IEEE OUI / EUI-64 등록·구성 자료',fields=['IEEE','FGUID'],needed='실제 OUI 할당 유효성 및 조직별 식별자 할당 확인.'),
        dict(id='other_cs',title='기타 I/O Command Set 규격',fields=['CTRATT','ONCS'],needed='다른 command set의 extended LBA format·aggregate 명령 지원을 판정하는 추가 근거.')]
    for ext in EXTERNAL:
        for k in ext['fields']:fields[k]['external'].append(ext['id'])
    # Reverse links are generated from explicit outgoing edges rather than guessed relationships.
    allnodes={**fields,**nodes}
    for n in allnodes.values():n['incoming']=[]
    for n in allnodes.values():
        seen=set();unique=[]
        for e in n['edges']:
            marker=(e['target'],e['type'])
            if marker in seen:continue
            seen.add(marker);unique.append(e)
            allnodes[e['target']]['incoming'].append(dict(target=n['id'],type=e['type'],text=e['text']))
        n['edges']=unique
    DATA.update(references=list(nodes.values()),external=EXTERNAL,
                time_scales=[dict(value=format(i,'X')+'h',microseconds=10**i) for i in range(13)],
                notes=['Base 인쇄 페이지는 PDF 페이지보다 22 작습니다. NVM 파일은 인쇄 페이지와 PDF 페이지 번호가 같습니다.',
                       '영문은 제공된 PDF에서 추출한 해당 표 또는 페이지의 내용입니다. 표의 줄 순서·각주 번호가 텍스트 추출 과정에서 달라질 수 있으므로 출처 위치도 함께 제공합니다.',
                       '관련 절의 한국어는 CNS 01h 검토에 필요한 내용을 재구성한 설명입니다. 영문 펼치기는 해당 절이 있는 페이지의 내용이며 전체 규격의 번역은 아닙니다.'])
    from consistency_audit import extend_checks
    from ocp_content import extend_ocp
    from editorial_audit import review
    return review(extend_ocp(extend_checks(DATA)))

if __name__=='__main__':
    data=assemble()
    (ROOT/'content.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"Authored {len(data['fields'])} byte ranges, {len(data['references'])} related clauses")
