"""Korean editorial source; PDF definitions take precedence over nvme.h."""
import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/'source/extracted.json').read_text(encoding='utf-8'))

# id | Korean title | representation/unit | Korean explanation
FIELD_TEXT=r'''
VID|PCI 공급업체 ID|16비트 식별자|PCI SIG가 할당한 공급업체 식별자입니다. PCIe transport의 PCI Header ID 레지스터 값과 같아야 합니다. PCIe 레지스터의 세부 배치는 외부 Transport 스펙 확인이 필요합니다.
SSVID|PCI 서브시스템 공급업체 ID|16비트 식별자|PCI SIG가 할당한 서브시스템 공급업체 식별자입니다. PCI Header SS 레지스터 값과 같습니다. VID와 SSVID가 반드시 같다는 규정은 아닙니다.
SN|시리얼 번호|20바이트 ASCII|공급업체가 NVM subsystem에 부여한 문자열입니다. 사용하지 않는 뒤쪽 문자는 공백으로 채우는 ASCII 규칙을 적용합니다. 일반 C 문자열처럼 NUL 종료를 가정하지 않습니다. Discovery subsystem에서는 이 값을 고유 식별자 구성에 사용하지 않는 것이 권고됩니다.
MN|모델 번호|40바이트 ASCII|공급업체가 NVM subsystem에 부여한 모델 문자열입니다. ASCII와 뒤쪽 공백 규칙을 적용합니다. Discovery가 아닌 subsystem의 고유 식별 요구는 SN·MN과 NQN의 관계를 함께 확인합니다.
FR|현재 활성 펌웨어 리비전|8바이트 ASCII|이 controller가 속한 domain에서 현재 활성화된 펌웨어 리비전입니다. Firmware Slot Information Log로 얻는 활성 리비전 정보와 같습니다. 다운로드하거나 다음 활성화 대상으로 지정한 이미지가 곧바로 FR이 되는 것은 아닙니다.
RAB|권장 중재 버스트|2^값 명령|권장 Arbitration Burst 크기입니다. Arbitration Feature의 AB와 같은 지수 단위를 사용합니다. 권장값이며 현재 AB 설정과 반드시 같아야 하는 값은 아닙니다.
IEEE|IEEE OUI|24비트 OUI|Controller 공급업체의 IEEE/RAC 할당 조직 식별자입니다. 유효한 할당 OUI이어야 합니다. 등록 정보 확인에는 외부 IEEE 자료가 필요합니다.
CMIC|다중 경로·namespace 공유 능력|비트맵|Subsystem의 다중 port·controller 및 SR-IOV function과 ANA 지원 여부를 표시합니다. 다중 경로를 실제 사용하는지와 지원 능력은 구분합니다.
MDTS|최대 데이터 전송 크기|2^값 × 최소 메모리 페이지|호스트가 접근할 수 있는 메모리와 controller 사이에서 한 명령으로 전송할 수 있는 데이터 크기의 한계입니다. MDTS=0이면 이 필드에 따른 최대 크기 제한이 없습니다. MDTS가 0이 아니면 최대 전송 크기는 2^MDTS × 2^(12+CAP.MPSMIN) 바이트입니다. 계산에는 CC.MPS가 아니라 CAP.MPSMIN을 사용합니다. 한계를 초과한 명령은 Invalid Field in Command로 중단합니다. CTRATT.MEM=0이면 interleaved metadata를 전송 크기에 포함하고, MEM=1이면 제외합니다. 호스트 메모리와 데이터를 전송하지 않는 Verify·Write Uncorrectable·Write Zeroes에는 직접 적용되지 않습니다. 목적지의 SGL Bit Bucket 길이는 계산에 포함하고, 소스의 길이는 제외합니다.
CNTLID|Controller 식별자|16비트 식별자|명령을 처리하는 controller에 연결된 NVM subsystem 내 고유 식별자입니다. 다른 controller 데이터나 로그를 대조할 때 동일한 subsystem·controller를 관측했는지 확인하는 기준입니다.
VER|Base 규격 버전|VS property와 동일한 32비트 버전|Version property의 값을 보고합니다. Base 1.2 이상을 따르는 구현은 0이 아닌 값을 보고해야 합니다. 이 값만으로 NVM Command Set 규격 리비전을 결정하지 않습니다.
RTD3R|Runtime D3 복귀 지연|μs|Runtime D3에서 복귀하는 예상 지연입니다. 0은 지연 시간을 보고하지 않는다는 뜻이며 즉시 복귀한다는 의미가 아닙니다.
RTD3E|Runtime D3 진입 지연|μs|Runtime D3로 진입하는 일반적인 지연 시간입니다. 0은 지연 시간을 보고하지 않는다는 뜻입니다. 전원 관리 상태 전환과 shutdown 지연을 혼동하지 않습니다.
OAES|선택적 비동기 이벤트 지원|32비트 비트맵|지원하는 선택적 AER 이벤트를 표시합니다. Host가 이벤트를 활성화하기 전에는 controller가 선택적 이벤트를 보내면 안 됩니다. 지원 비트와 Asynchronous Event Configuration의 현재 enable 비트를 별도로 확인합니다.
CTRATT|Controller 속성|32비트 비트맵|Host Identifier, 전원 관리, namespace 구성, capacity 및 metadata 한계 계산에 관련된 능력입니다. 각 비트의 적용 조건을 확인해야 하며 하나의 전역 enable 상태가 아닙니다.
RRLS|지원하는 읽기 복구 레벨|16비트 비트맵|비트 n=1이면 Read Recovery Level n을 지원합니다. RRL 기능을 지원하면 이 필드도 지원해야 합니다. Level 4(Default)와 15(Fast Fail)는 반드시 지원합니다. 현재 선택된 레벨은 Read Recovery Level Feature에서 확인합니다.
BPCAP|Boot Partition 능력|8비트 비트맵|Set Features 및 RPMB 경로의 Boot Partition 쓰기 보호 능력을 각각 나타냅니다. PCIe I/O controller용 필드이며 현재 보호 상태와 지원 여부를 구분합니다.
NSSL|Subsystem shutdown 지연|μs|NVM Subsystem Shutdown이 완료되는 일반적인 지연 시간입니다. 0은 값을 보고하지 않는다는 뜻입니다. Controller shutdown과 subsystem shutdown을 구분합니다.
PLSI|전원 손실 신호 처리 능력|8비트 비트맵|Power Loss Signaling의 Forced Quiescence와 Emergency Power Fail 처리 지원 여부입니다. PSD의 관련 시간·scale 값과 조건부로 연결됩니다.
CNTRLTYPE|Controller 유형|8비트 열거값|1h=I/O, 2h=Discovery, 3h=Administrative controller입니다. Base 1.4 이상에서는 0h를 사용할 수 없습니다. 4h~FFh는 Reserved입니다. 이전 규격에서는 0h가 유형 미보고였으므로 버전 조건을 함께 봅니다.
FGUID|FRU 전역 고유 식별자|128비트 big endian|FRU 수명 동안 고정되는 EUI-64 기반 16바이트 식별자입니다. 같은 FRU의 모든 controller가 같은 값을 보고해야 합니다. 미구현은 0입니다. 바이트 120~122가 OUI, 123~127이 조직이 부여한 확장 식별자, 112~119가 vendor 확장입니다. 일반 수치 필드와 달리 big endian입니다. FRU의 정의는 NVMe-MI 스펙에 있습니다.
CRDT1|명령 재시도 지연 1|값 × 100 ms|Completion의 DNR=0, CRD=01b인 경우 호스트가 재시도할 지연 시간입니다. DNR=1이면 이 필드를 이유로 재시도하지 않습니다.
CRDT2|명령 재시도 지연 2|값 × 100 ms|Completion의 DNR=0, CRD=10b인 경우에 적용되는 재시도 지연입니다.
CRDT3|명령 재시도 지연 3|값 × 100 ms|Completion의 DNR=0, CRD=11b인 경우에 적용되는 재시도 지연입니다.
CRCAP|Controller 도달성 능력|8비트 비트맵|Reachability Reporting과 namespace가 attach된 동안 RGRPID가 고정되는 조건을 표시합니다. RGIDC라는 비트 이름만 보고 의미를 추정하면 반대로 해석할 수 있습니다.
NVMSR|NVM subsystem 보고 정보|8비트 비트맵|NVMe-MI 기준으로 subsystem이 Enclosure 또는 Storage Device의 일부인지 나타냅니다. NVMe-MI를 지원하지 않으면 0이어야 하며, compliant controller에서는 적어도 한 비트가 1입니다.
VWCI|VPD 쓰기 수명 정보|8비트 복합값|VPD Write로 갱신 가능한 잔여량을 나타냅니다. Valid 비트가 0이면 잔여량도 0이어야 합니다. 실제 VPD 내용·명령의 정의는 NVMe-MI 스펙 확인이 필요합니다.
MEC|관리 endpoint 능력|8비트 비트맵|PCIe port 또는 2-Wire port에 관리 endpoint가 존재하는지 나타냅니다. 실제 endpoint 존재 여부에 따라 해당 비트를 설정해야 합니다.
OACS|선택적 Admin 명령 지원|16비트 비트맵|Admin 명령과 관련 capability 지원을 보고합니다. 명령 실행 상태와 지원 능력을 구분합니다. Namespace Management, Device Self-test, Firmware 및 Live Migration의 종속 필드를 함께 확인합니다.
ACL|동시 Abort 명령 한계|0 기반 개수: 값+1|Admin Queue에서 동시에 실행 가능한 Abort 명령 수입니다. 최소 4개 동시 실행을 지원하는 것이 권고되며, 필수 조건과 구분해야 합니다.
AERL|동시 AER 요청 한계|0 기반 개수: 값+1|동시에 outstanding 상태로 둘 수 있는 Asynchronous Event Request 명령 수입니다. 최소 4개 outstanding을 지원하는 것이 권고됩니다. Explicit persistent connection 미지원 Discovery controller에서는 Reserved입니다.
FRMW|펌웨어 업데이트 능력|8비트 복합값|펌웨어 slot 개수, slot 1의 쓰기 가능 여부, reset 없는 활성화와 중첩 업데이트 감지 능력입니다. Firmware Slot Log, Firmware Commit와 관련 시간을 함께 확인합니다.
LPA|Log Page 속성|8비트 비트맵|Get Log Page의 선택적 능력과 일부 로그 지원을 표시합니다. SMARTS=0이 전체 SMART 로그 미지원이라는 뜻은 아닙니다. MLPS=0도 해당 선택 로그 전체 미지원을 뜻하지 않습니다.
ELPE|Error Log entry 한계|0 기반 개수: 값+1|Controller가 보관하는 Error Information Log entry의 최대 개수입니다. 로그를 읽을 때 entry 크기와 함께 필요한 길이를 계산합니다.
NPSS|지원 전원 상태 수|0 기반 개수: 값+1|Power State 0부터 NPSS까지 연속된 상태를 지원합니다. 최소 1개, 최대 32개이므로 유효한 NPSS는 0~31입니다. NPSS=0도 PS0을 지원합니다. 해당 PSD들을 전원 관리와 APST 표의 대상 상태와 함께 확인합니다.
AVSCC|Vendor Admin 명령 형식|8비트 비트맵|Vendor Admin 명령이 공통 vendor 명령 형식을 사용하는지 나타냅니다. 0은 vendor 명령 미지원이 아니라 형식이 vendor specific임을 뜻합니다.
APSTA|자동 전원 상태 전환 능력|8비트 비트맵|APST를 지원하는지를 보고합니다. 실제 APST 활성화와 전환 표는 FID 0Ch에서 설정·조회합니다. Feature의 APSTE를 변경하는 것과 Identify.APTS 값을 변경하는 것은 구분합니다.
WCTEMP|경고 composite 온도|Kelvin|SMART/Health의 Composite Temperature가 과열 경고에 도달하는 최소 온도입니다. 동작은 계속되지만 냉각 개선·부하 감소가 권고됩니다. 0은 값을 보고하지 않는다는 뜻이며 Base 1.2 이상에서는 0이 아닌 값을 보고해야 합니다. 권고값 0157h는 343 K입니다. 현재 Temperature Threshold Feature 설정과 동일한 값이라고 단정하지 않습니다.
CCTEMP|위험 composite 온도|Kelvin|정상 동작 지속이 어려워질 수 있는 위험 과열 온도입니다. 데이터 손실·shutdown·심한 throttling 등의 위험 기준입니다. 0은 값을 보고하지 않는다는 뜻이며 Base 1.2 이상에서는 0이 아닌 값을 보고해야 합니다.
MTFA|펌웨어 활성화 중 명령 중지 시간|값 × 100 ms|펌웨어 활성화를 위해 controller가 명령 처리를 일시 중지하는 최대 시간입니다. Reset 없는 활성화를 지원할 때 유효해야 합니다. 0은 최대 시간 미정의입니다. Firmware Commit 전체 처리 시간을 나타내는 MPTFAWR와 다릅니다.
HMPRE|권장 HMB 크기|값 × 4 KiB|Host에 요청하는 권장 Host Memory Buffer 크기입니다. HMPRE≥HMMIN이어야 합니다. 0이면 HMB 미지원입니다. Subsystem의 controller 하나라도 OACS.HMLMS=1이면 0이어야 합니다. 실제 할당·enable 상태는 FID 0Dh에서 확인합니다.
HMMIN|최소 HMB 크기|값 × 4 KiB|Host에 요청하는 최소 HMB 크기입니다. 0이면 HMPRE까지 가능한 메모리를 할당하도록 요청한다는 뜻이며 HMB 미지원 자체를 뜻하지 않습니다.
TNVMCAP|총 NVM 용량|128비트 정수, 바이트|Controller가 접근할 수 있는 총 NVM 용량입니다. Namespace Management 또는 Capacity Management 지원 시 필수입니다. Namespace 생성·삭제 및 용량 구성과 함께 확인합니다. Namespace 크기 합을 단순히 이 값과 같다고 가정하지 않습니다.
UNVMCAP|미할당 NVM 용량|128비트 정수, 바이트|Controller가 접근할 수 있는 미할당 NVM 용량입니다. Namespace Management 또는 Capacity Management 지원 시 필수입니다. Namespace나 capacity 할당 변화에 따라 재조회가 필요한 값입니다.
RPMBS|Replay Protected Memory Block 능력|32비트 복합값|RPMB target 개수·인증 방식·크기·접근 크기를 보고합니다. Target이 없으면 크기 정보는 host가 무시해야 합니다. Target이 있으면 Security Send/Receive를 지원해야 하고 모든 target은 동일한 능력을 가집니다.
EDSTT|확장 self-test 예상 시간|분|Device Self-test를 지원할 때 PS0에서 extended self-test를 완료하는 예상 소요 시간입니다. Self-test 미지원이면 Reserved입니다.
DSTO|Device Self-test 옵션|8비트 비트맵|동시 self-test 동작의 범위와 Host-Initiated Refresh 지원 여부를 나타냅니다. 현재 self-test 진행 상태는 Device Self-test Log에서 확인합니다.
FWUG|펌웨어 다운로드 정렬 단위|값 × 4 KiB; 특수값 00h/FFh|Firmware Image Download의 길이(NUMD)와 offset(OFST)이 따라야 할 granularity와 alignment입니다. 0은 정보 미제공, FFh는 dword 단위 외 추가 제한 없음입니다. 나머지 값은 4 KiB 단위입니다. 요구를 어기면 Invalid Field in Command로 중단될 수 있습니다(MAY).
KAS|Keep Alive 타이머 단위|값 × 100 ms|KATO의 granularity입니다. 0이면 Keep Alive Timer Feature 미지원입니다. 현재 타임아웃과 traffic based 동작은 Keep Alive Feature 및 CTRATT.TBKAS와 함께 확인합니다.
HCTMA|Host 열 관리 능력|16비트 비트맵|Host Controlled Thermal Management를 지원하는지 보고합니다. HCTMS=1이면 FID 10h의 Get/Set Features를 지원해야 합니다. 현재 TMT1/TMT2 설정은 Feature 값입니다.
MNTMT|최소 열 관리 온도|Kelvin|Host가 FID 10h의 TMT1/TMT2로 요청할 수 있는 최소 온도입니다. 0은 이 값을 미보고하거나 HCTM 미지원입니다.
MXTMT|최대 열 관리 온도|Kelvin|Host가 FID 10h의 TMT1/TMT2로 요청할 수 있는 최대 온도입니다. 0은 이 값을 미보고하거나 HCTM 미지원입니다. 온도 임계값을 비활성화하는 0 설정은 Feature 규정을 별도로 적용합니다.
SANICAP|Sanitize 능력|32비트 복합값|지원하는 sanitize 방식과 No-Deallocate·검증 동작을 보고합니다. Sanitize 지원 시 0이 아닌 값, 미지원 시 0이어야 합니다. 현재 sanitize 상태·진행률은 Sanitize Status Log로 확인합니다.
HMMINDS|최소 HMB descriptor 크기|값 × 4 KiB|사용 가능한 HMB Descriptor Entry의 최소 크기입니다. 0은 entry 크기 제한 미보고입니다. HMB 자체의 최소 크기 HMMIN과 구분합니다.
HMMAXD|최대 HMB descriptor 개수|개수|사용 가능한 HMB Descriptor Entry 수입니다. 0은 최대 개수 미지정입니다.
NSETIDMAX|최대 유효 NVM Set ID|16비트 식별자 상한|Subsystem의 유효 NVM Set Identifier 최대 값입니다. 지원하는 NVM Set 개수는 이 값 이하이지만 반드시 같은 개수는 아닙니다.
ENDGIDMAX|최대 유효 Endurance Group ID|16비트 식별자 상한|Subsystem의 유효 Endurance Group Identifier 최대 값입니다. ID 상한과 실제 group 개수를 구분합니다.
ANATT|ANA 전환 최대 시간|초|ANA 상태 전환 또는 ANA Change 상태를 보고하는 최대 시간입니다. CMIC.ANARS=1이면 0이 아닌 값을 보고해야 하며, 미지원이면 0이어야 합니다.
ANACAP|ANA 능력|8비트 비트맵|보고 가능한 ANA 상태와 Group ID 설정·attach 중 변경 조건입니다. 실제 경로 상태는 ANA Log의 group descriptor로 확인합니다.
ANAGRPMAX|최대 ANA Group ID|32비트 식별자 상한|유효 ANA Group Identifier의 최대 값입니다. ANA 지원 시 0이 아닌 값, 미지원 시 0이어야 합니다.
NANAGRPID|지원 ANA group 수|개수|Controller가 지원하는 ANA group 개수입니다. ANA 지원 시 0<NANAGRPID≤ANAGRPMAX이어야 합니다. 미지원이면 0입니다.
PELS|Persistent Event Log 최대 크기|값 × 64 KiB|보고 가능한 Persistent Event Log의 최대 크기입니다. 해당 로그 미지원이면 Reserved입니다. 실제 로그 길이와 최대 크기를 구분합니다.
DID|Domain 식별자|16비트 식별자|Controller가 속한 domain을 나타냅니다. CTRATT.MDS=1이면 0이 아닌 값을 사용하며 single domain subsystem이면 0입니다.
KPIOC|Key Per I/O 능력|8비트 비트맵|Key Per I/O 지원과 enable 적용 범위를 보고합니다. Namespace별 enable 여부 또는 subsystem 전체 적용 여부는 KPIOSC에 따라 구분합니다.
MPTFAWR|Reset 없는 활성화 명령 최대 처리 시간|값 × 100 ms|Commit Action=011b Firmware Commit를 처리하는 예상 최대 시간입니다. Admin Queue와 MI 경로에 적용합니다. Reset 없는 활성화 미지원이면 0이어야 합니다. 이를 지원하는 Base 2.1 이상 구현은 0을 보고하면 안 됩니다. MTFA의 명령 중지 시간과 다릅니다.
MEGCAP|최대 Endurance Group 용량|128비트 용량 값 · Figure 312에 단위가 명시되어 있지 않음|한 Endurance Group의 최대 용량입니다. 0이면 최대 값을 미보고합니다. Single-domain의 Capacity Reporting 절에서는 생성 가능한 최대 entity(Endurance Group·NVM Set·formatted namespace 등)로 설명합니다. 단위와 용량 처리 조건은 관련 Capacity Reporting 규정을 함께 확인하며 이 필드 표에 없는 단위를 임의로 덧붙이지 않습니다.
TMPTHHA|온도 threshold hysteresis 속성|8비트 복합값|Temperature Threshold hysteresis로 지원하는 최대 온도 차의 절댓값입니다. FID 04h 설정 및 OAES.TTHR 이벤트와 관련됩니다. 미지원 속성은 000b입니다.
CQT|명령 quiesce 시간|ms|Keep Alive Timeout 또는 통신 손실 후 outstanding 명령들의 Immediate Abort 요건을 만족시키는 예상 최악 시간입니다. 0은 시간 미보고입니다. 시간이 필요 없더라도 1h를 보고하는 것이 권고됩니다.
SQES|I/O Submission Queue entry 크기|각 nibble을 2^값 바이트로 해석|필수 최소 및 지원 최대 I/O SQ entry 크기입니다. 최소 지수는 6(64바이트)이어야 하고 최대 지수는 최소 이상입니다. 실제 CC.IOSQES가 이 범위에 있어야 합니다.
CQES|I/O Completion Queue entry 크기|각 nibble을 2^값 바이트로 해석|필수 최소 및 지원 최대 I/O CQ entry 크기입니다. 최소 지수는 4(16바이트)이어야 하고 최대 지수는 최소 이상입니다. 실제 CC.IOCQES 설정과 함께 확인합니다.
MAXCMD|Queue별 동시 처리 명령 수|개수|특정 queue에서 동시에 처리하는 최대 명령 수입니다. SQ 크기보다 클 수 있습니다. Fabrics에서는 필수, PCIe에서는 선택입니다. 사용하지 않으면 0이어야 합니다.
NN|최대 유효 Namespace ID|32비트 NSID 상한|NVM subsystem에서 유효한 NSID의 최대 값입니다. 이름만 보고 현재 namespace 개수라고 해석하면 안 됩니다. 지원 namespace 개수는 MNAN과 namespace 목록을 함께 확인합니다.
ONCS|선택적 I/O 명령·Feature 지원|16비트 비트맵|이름은 역사적으로 유지되었지만 모든 I/O Command Set에 적용됩니다. 여러 command set에서는 지원 능력의 합집합을 나타내므로 특정 command set 지원은 Commands Supported and Effects Log로 확인합니다. Base 2.1의 Verify·Write Zeroes·DSM·Write Uncorrectable은 비트 0만으로 미지원이라고 판단할 수 없습니다. CNS 06h 한계 필드도 확인합니다.
FUSES|Fused operation 지원|16비트 필드|Compare와 Write fused operation 지원을 보고합니다. Compare가 첫 번째 명령이어야 합니다. ACWU 및 namespace NACWU와 함께 atomic 한계를 확인합니다.
FNA|Format NVM 속성|8비트 비트맵|Format·secure erase의 namespace 적용 범위와 cryptographic erase 지원을 나타냅니다. Broadcast 지원 비트는 1이 미지원이라는 역방향 의미입니다.
VWC|휘발성 쓰기 캐시 속성|8비트 복합값|캐시 존재와 Flush broadcast 동작을 나타냅니다. VWCP는 존재 여부이며 현재 WCE enable 상태는 FID 06h입니다. 캐시를 disable한다고 VWCP가 0으로 바뀐다고 해석하지 않습니다. Flush는 캐시 내용을 비휘발성 상태로 만들도록 요청합니다.
AWUN|정상 동작 atomic write 단위|0 기반 logical block 수: 값+1|모든 namespace와 지원 format에서 보장되는 정상 동작 write atomicity의 baseline입니다. Namespace가 더 큰 값을 보장하면 NAWUN으로 보고합니다. 전원 실패 atomicity는 AWUPF를 봅니다. FFFFh는 Copy 외 명령의 최대 크기까지 atomic임을 뜻하고 Copy에서는 10000h logical blocks입니다. 128 KiB 이상 지원은 권고입니다. Multiple Atomicity Mode에서는 전체 명령의 보장과 부분 보장을 구분합니다.
AWUPF|전원 실패·오류 atomic write 단위|0 기반 logical block 수: 값+1|모든 namespace와 지원 format에 대한 전원 실패 또는 오류 상황의 atomicity baseline입니다. AWUPF≤AWUN이어야 합니다. Namespace별 더 큰 보장은 NAWUPF로 보고합니다. 이 한계 이하 write가 실패하면 해당 LBA의 후속 read는 이전에 성공한 write의 데이터를 반환해야 합니다. 한계를 넘으면 전체 atomicity·후속 데이터 보장을 가정하지 않습니다.
ICSVSCC|Vendor I/O 명령 형식|8비트 비트맵|Vendor I/O 명령이 공통 vendor 명령 형식을 사용하는지 나타냅니다. 0은 미지원이 아니라 vendor specific 형식입니다. nvme.h의 nvscc 명칭과 대응합니다.
NWPC|Namespace 쓰기 보호 능력|8비트 비트맵|지원하는 namespace write protection 상태를 나타냅니다. 실제 보호 상태는 FID 84h의 설정값으로 확인합니다. 기본 No Write Protect/Write Protect 미지원이면 나머지 보호 지원 비트도 0이어야 합니다.
ACWU|Atomic Compare & Write 단위|0 기반 logical block 수: 값+1|모든 namespace·지원 format에서 Compare+Write fused operation을 atomic하게 처리하는 baseline입니다. Namespace별 더 큰 보장은 NACWU입니다. Fused Compare+Write 지원 시 이 필드를 지원해야 하며 미지원 시 0이어야 합니다. 한계를 넘으면 Atomic Write Unit Exceeded로 중단할 수 있습니다(MAY). 0을 해석할 때 지원 여부를 먼저 확인합니다.
CDFS|Copy descriptor format 지원|16비트 비트맵|지원하는 Copy Source Range Entry descriptor format 0h~4h를 표시합니다. Format 2h·3h는 추가 cross-namespace Copy 규정으로 한정됩니다. 선택한 format과 명령의 layout을 함께 확인합니다.
SGLS|SGL 지원과 제약|32비트 복합값|SGL 지원, descriptor 종류, 정렬·길이·offset 조건과 권장 descriptor 개수를 나타냅니다. 명령의 PSDT 및 MPTR 형태, MDTS 계산과 함께 확인합니다.
MNAN|지원 namespace 최대 개수|개수|Subsystem이 지원하는 최대 namespace 개수입니다. 0이면 지원 개수가 NN 이하라는 뜻입니다. ANA 지원 시 0<MNAN≤NN이어야 합니다. 현재 생성되거나 attach된 개수와 다릅니다.
MAXDNA|Domain namespace attachment 한계|128비트 개수|Domain 내 각 I/O controller에 attach된 namespace 수의 합에 대한 최대 값입니다. 0이면 최대 미지정입니다. Domain의 모든 I/O controller에서 같아야 합니다. 같은 namespace를 여러 controller에 attach하면 각 controller의 attachment 수에 포함됩니다.
MAXCNA|Controller namespace attachment 한계|개수|이 I/O controller에 attach할 수 있는 최대 namespace 수입니다. 0이면 최대 미지정입니다. 유효한 한계는 subsystem 지원 namespace 수를 넘지 않아야 합니다(MNAN 정의 참조).
OAQD|권장 합계 queue depth|개수|최적 동작을 위해 모든 I/O queue에 걸쳐 권장하는 outstanding I/O 명령 총량의 최대 값입니다. 0은 값을 보고하지 않는다는 뜻입니다. MAXCMD와 달리 성능을 위한 권장값입니다.
RHIRI|Host-Initiated Refresh 권장 간격|일|DSTO.HIRS=1이면 마지막 power down부터 host가 refresh를 시작하는 것이 권고되는 시간입니다. 0은 값을 보고하지 않는다는 뜻입니다. HIRS=0이면 0이어야 합니다.
HIRT|Host-Initiated Refresh 예상 시간|분|Refresh 완료의 예상 소요 시간입니다. 0은 값을 보고하지 않는다는 뜻입니다. HIRS=0이면 0이어야 합니다.
CMMRTD|Controller memory tracking descriptor 한계|개수|Controller가 지원하는 Memory Range Tracking Descriptor 최대 수입니다. TRATTR.THMCS=0이면 0이어야 하고 host는 무시하는 것이 권고됩니다.
NMMRTD|Subsystem memory tracking descriptor 한계|개수|Subsystem이 지원하는 Memory Range Tracking Descriptor 최대 수입니다. THMCS=0이면 0이어야 하고 host는 무시하는 것이 권고됩니다.
MINMRTG|최소 memory tracking granularity|RMRTG 인코딩 값|Track Memory Ranges 구조의 RMRTG에 설정 가능한 최소 값입니다. THMCS=0이면 0이어야 하고 host는 무시하는 것이 권고됩니다. 이 값을 직접 바이트 수라고 가정하지 않습니다.
MAXMRTG|최대 memory tracking granularity|RMRTG 인코딩 값|RMRTG에 설정 가능한 최대 값입니다. THMCS=0이면 0이어야 하고 host는 무시하는 것이 권고됩니다.
TRATTR|Tracking 속성|8비트 비트맵|Host memory와 user data 변경 추적 지원 및 길이 표현 제약입니다. Track Send/Receive와 관련 한계 필드의 적용 조건입니다.
MCUDMQ|Controller user data migration queue 한계|개수|이 controller에 생성할 수 있는 User Data Migration Queue의 최대 수입니다. TRATTR.TUDCS=0이면 0이어야 하고 host는 무시하는 것이 권고됩니다.
MNSUDMQ|Subsystem user data migration queue 한계|개수|Subsystem 전체에 생성할 수 있는 User Data Migration Queue 최대 수입니다. TUDCS=0이면 0이어야 하고 host는 무시하는 것이 권고됩니다.
MCMR|CDQ memory range 한계|개수|Controller Data Queue 명령의 PRP1로 지정할 수 있는 memory range 최대 수입니다. 0은 최대 미보고입니다.
NMCMR|Subsystem CDQ memory range 한계|개수|Subsystem의 모든 Controller Data Queue에 대한 memory range 최대 수입니다. 0은 최대 미보고입니다. NMCMR≥MCMR이어야 합니다.
MCDQPC|CDQ PRP 개수 한계|개수|Controller Data Queue 명령의 PRP list에 지정할 수 있는 PRP 최대 수입니다. 0은 최대 미보고입니다.
SUBNQN|Subsystem NVMe Qualified Name|256바이트 UTF-8, NUL 종료|NVM Subsystem NQN입니다. Base 1.2.1 이상에서는 필수입니다. SN/MN의 고정 길이 ASCII와 달리 UTF-8 NUL 종료 규칙입니다. Discovery subsystem에 고유 Discovery Service NQN이 있으면 이를 보고하고, 없으면 nqn.2014-08.org.nvmexpress.discovery를 보고합니다.
IOCCSZ|I/O command capsule 최대 크기|값 × 16바이트|최대 I/O command capsule 크기입니다. 최소 값 4는 64바이트입니다. Message-based I/O controller에서 필수이며 memory-based controller에서는 Reserved입니다.
IORCSZ|I/O response capsule 최대 크기|값 × 16바이트|최대 I/O response capsule 크기입니다. 최소 값 1은 16바이트입니다. Message-based I/O controller에서 필수이며 memory-based controller에서는 Reserved입니다.
ICDOFF|Capsule data 시작 offset|값 × 16바이트|Command capsule의 64바이트 SQ entry 끝을 기준으로 data가 시작하는 offset입니다. I/O Queue에만 적용하며 Admin Queue는 0을 사용합니다. 값 범위는 0~FFFFh입니다.
FCATT|Fabrics controller 속성|8비트 비트맵|Connect의 non-zero NVM Set ID 지원과 controller의 dynamic/static 모델을 나타냅니다. DCMS 비트의 실제 값 정의를 따라야 합니다.
MSDBD|Capsule SGL descriptor 한계|개수|한 capsule에 host가 넣을 수 있는 SGL Data Block 또는 Keyed SGL Data Block descriptor 최대 수입니다. 0이면 제한 없음입니다.
OFCS|선택적 Fabrics 명령 지원|16비트 비트맵|Disconnect command 및 개별 I/O Queue 삭제 지원 여부를 나타냅니다. Memory-based controller에서는 Reserved입니다.
DCTYPE|Discovery controller 유형|8비트 열거값|0h=유형 미보고, 1h=DDC, 2h=CDC, 3h~FFh=Reserved입니다. I/O·Administrative controller에서는 Reserved입니다.
VS|Vendor Specific 영역|1024바이트 vendor 정의 데이터|바이트 3072~4095는 vendor가 정의하는 영역입니다. 두 스펙에는 내부 layout이 정의되어 있지 않으므로 범용 비트 의미나 정합성 규칙을 만들어 적용하지 않습니다.
'''
EDITOR={}
for line in FIELD_TEXT.strip().splitlines():
    key,title,unit,ko=line.split('|',3)
    EDITOR[key]=dict(title=title,unit=unit,ko=ko)

# Bit-level Korean definitions keyed by the field and normalized source bit range.
BIT_TEXT=r'''
CMIC|3|ANARS: 1=ANA Reporting 지원, 0=미지원. ANA Log 및 ANATT·ANACAP·MNAN의 적용 조건입니다.
CMIC|2|FT: 1=SR-IOV Virtual Function, 0=PCI Function 또는 Fabrics connection입니다.
CMIC|1|MCTRS: 1=subsystem에 controller가 2개 이상 있을 수 있음, 0=controller 하나입니다.
CMIC|0|MPORTS: 1=subsystem port가 여러 개 있을 수 있음, 0=port 하나입니다.
OAES|31|DLPCN: 1=Discovery Log 변경 통지 지원, 0=미지원입니다.
OAES|27|ZDCN: 1=Zone Descriptor Changed 이벤트와 Changed Zone List Log 지원, 0=둘 다 미지원입니다. 상세 구조는 외부 ZNS 스펙이 필요합니다.
OAES|19|ANSAN: 1=Allocated Namespace Attribute 통지와 Changed Allocated Namespace List Log 지원, 0=둘 다 미지원입니다.
OAES|17|RGCNS: 1=Reachability Groups Change 및 Reachability Association Change 통지 지원, 0=둘 다 미지원입니다.
OAES|16|TTHR: 1=온도 threshold hysteresis 복구 이벤트 지원, 0=미지원입니다. 연결된 Log Page는 없습니다.
OAES|15|NNSS: 1=Normal NVM Subsystem Shutdown 이벤트 지원, 0=미지원입니다. 연결된 Log Page는 없습니다.
OAES|14|EGEAN: 1=Endurance Group Event Aggregate Log 변경 통지 지원, 0=미지원입니다.
OAES|13|LSIAN: 1=LBA Status Information Alert 통지 지원, 0=미지원입니다. NVM Command Set 규정을 함께 봅니다.
OAES|12|PLEAN: 1=Predictable Latency Event Aggregate Log 변경 통지 지원, 0=미지원입니다.
OAES|11|ANACN: 1=ANA Change 통지 지원, 0=미지원입니다.
OAES|9|FAN: 1=Firmware Activation 통지 지원, 0=미지원입니다.
OAES|8|NSAN: 1=Attached Namespace Attribute 통지와 Changed Attached Namespace List Log 지원, 0=둘 다 미지원입니다.
CTRATT|19|FDPS: 1=Flexible Data Placement 지원, 0=미지원입니다. FCM=1이면 FDPS는 0이어야 합니다.
CTRATT|18|RHII: 0b=상호작용 규칙을 보고하지 않음, 1b=reservation 사용 전에 host가 Host Identifier를 0이 아닌 값으로 설정해야 합니다.
CTRATT|17|HMBR: 1=non-operational power state에서 HMB 접근 제한 지원, 0=해당 제한 기능 미지원입니다.
CTRATT|16|MEM: 1=MDTS와 CNS 06h의 VSL/WZSL/WUSL 계산에서 interleaved metadata 제외, 0=포함입니다.
CTRATT|15|ELBAS: 1=command set별 extended protection information format 지원, 0=미지원입니다. NVM의 Protection Information Formats 규정과 연결됩니다.
CTRATT|14|DNVMS: 1=Delete NVM Set 동작 지원, 0=미지원입니다.
CTRATT|13|DEG: 1=Delete Endurance Group 동작 지원, 0=미지원입니다.
CTRATT|12|VCM: 1=Variable Capacity Management 지원, 0=미지원입니다.
CTRATT|11|FCM: 1=Fixed Capacity Management 지원, 0=미지원입니다. FDPS=1이면 FCM은 0이어야 합니다.
CTRATT|10|MDS: 1=multiple domain 지원, 0=single domain이며 multiple domain 보고 미지원입니다.
CTRATT|9|ULIST: 1=UUID List 보고 지원, 0=미지원입니다.
CTRATT|8|SQA: 1=SQ Association 지원, 0=미지원입니다.
CTRATT|7|NG: 1=Namespace Granularity 보고 지원, 0=미지원입니다. Namespace Management 미지원이면 0이어야 합니다.
CTRATT|6|TBKAS: 1=Traffic Based Keep Alive 사용, 0=사용하지 않습니다.
CTRATT|5|PLM: 1=Predictable Latency Mode 지원, 0=미지원입니다.
CTRATT|4|EGS: 1=Endurance Group 지원, 0=미지원입니다.
CTRATT|3|RRLVLS: 1=Read Recovery Level 지원, 0=미지원입니다. RRLS와 RRL Feature를 함께 확인합니다.
CTRATT|2|NSETS: 1=NVM Set 지원, 0=미지원입니다.
CTRATT|1|NOPSPM: 1=non-operational state에서 background 동작을 위해 전력 초과를 허용할지 host가 제어할 수 있음, 0=host 제어 미지원입니다. 현재 허용 여부는 Feature 설정입니다.
CTRATT|0|HIDS: 1=128비트 Host Identifier 지원, 0=128비트 미지원입니다. 0이 Host Identifier 전체 미지원이라는 뜻은 아닙니다.
BPCAP|2|SFBPWPS: 1=Set Features를 통한 Boot Partition Write Protection 지원, 0=미지원입니다.
BPCAP|1:0|RPMBBPWPS: 00b=지원 여부 미지정(Base 2.0 이하 구현에 한정), 01b=RPMB 경로 쓰기 보호 미지원, 10b=지원, 11b=Reserved입니다.
PLSI|1|PLSFQ: 1=Forced Quiescence PLS 지원, 0=미지원입니다. PSD.FQVT/FQVTS와 연결됩니다.
PLSI|0|PLSEPF: 1=Emergency Power Fail PLS 지원, 0=미지원입니다. PSD.EPFVT/EPFRT와 연결됩니다.
CRCAP|1|RGIDC: 1=namespace가 어떤 controller에라도 attach된 동안 RGRPID가 변경되지 않음, 0=attach 중에도 변경 가능입니다. 비트 이름과 직관이 반대일 수 있으므로 값 정의를 따릅니다.
CRCAP|0|RRSUP: 1=Reachability Reporting 지원, 0=미지원입니다.
NVMSR|1|NVMEE: 1=subsystem이 NVMe Enclosure 일부, 0=아닙니다.
NVMSR|0|NVMESD: 1=subsystem이 NVMe Storage Device 일부, 0=아닙니다.
VWCI|7|VWCRV: 1=잔여 VPD 쓰기량 유효, 0=무효이며 VWCR도 0입니다.
VWCI|6:0|VWCR: 유효할 때 256바이트 갱신 단위의 잔여량입니다. 예: 1 KiB 장치를 8회 갱신 가능하면 32. 7Fh는 7Fh 이상을 뜻합니다. VWCRV=0이면 0이어야 합니다.
MEC|1|PCIEME: PCIe port에 관리 endpoint가 하나 이상 있으면 1, 없으면 0이어야 합니다.
MEC|0|TWPME: 2-Wire port에 관리 endpoint가 하나 이상 있으면 1, 없으면 0이어야 합니다. 이전 명칭은 SMBUSME입니다.
OACS|11|HMLMS: 1=Host Managed Live Migration 지원, 0=미지원입니다. Secondary controller는 이 비트를 0으로 해야 합니다.
OACS|10|CFLS: 1=Command/Feature Lockdown 지원, 0=미지원입니다. Subsystem 내 모든 controller에서 같아야 합니다.
OACS|9|GLSS: 1=Action Type 10h/11h의 Get LBA Status 능력 지원, 0=해당 능력 미지원입니다.
OACS|8|DBCS: 1=Doorbell Buffer Config 명령 지원, 0=미지원입니다.
OACS|7|VMS: 1=Virtualization Management 명령 지원, 0=미지원입니다.
OACS|6|NSRS: 1=NVMe-MI Send/Receive 명령 지원, 0=둘 다 미지원입니다.
OACS|5|DIRS: 1=Directives 지원, 0=미지원입니다. 지원 시 Directive Send/Receive 명령을 지원해야 합니다.
OACS|4|DSTS: 1=Device Self-test 명령 지원, 0=미지원입니다.
OACS|3|NMS: 1=Namespace Management 지원, 0=미지원입니다. TNVMCAP·UNVMCAP와 namespace 구성 규정을 함께 봅니다.
OACS|2|FWDS: 1=Firmware Commit/Image Download 지원, 0=둘 다 미지원입니다.
OACS|1|FNVMS: 1=Format NVM 명령 지원, 0=미지원입니다.
OACS|0|SSRS: 1=Security Send/Receive 지원, 0=둘 다 미지원입니다.
FRMW|5|SMUD: 1=중첩 firmware/boot image 업데이트 sequence 감지 가능, 0=불가능합니다.
FRMW|4|FAWR: 1=reset 없이 firmware 활성화 지원, 0=활성화에 reset 필요입니다.
FRMW|3:1|NOFS: domain이 지원하는 firmware slot 수는 1~7이어야 합니다. 실제 slot 번호는 1~7이며 0 기반 수가 아닙니다.
FRMW|0|FFSRO: 1=slot 1 읽기 전용, 0=읽기/쓰기 가능입니다. 다른 slot이 모두 read-only라는 의미는 아닙니다.
LPA|6|DA4S: 1=두 Telemetry log의 Data Area 4 지원, 0=해당 area 미지원입니다.
LPA|5|MLPS: 1=LID 00h·12h·13h 및 Commands Supported and Effects의 command scope 보고 지원. 0=command scope 보고 미지원이나 00h·12h·13h 로그는 선택적으로 지원할 수 있습니다(MAY).
LPA|4|PES: 1=Persistent Event Log 지원, 0=미지원입니다.
LPA|3|TS: 1=Host/Controller-Initiated Telemetry log와 Telemetry Log Notice 지원, 0=세 가지 모두 미지원입니다.
LPA|2|LPEDS: 1=Get Log Page의 확장 NUMD 및 Log Page Offset 지원, 0=확장 데이터 미지원입니다.
LPA|1|CSES: 1=Commands Supported and Effects Log 지원, 0=미지원입니다.
LPA|0|SMARTS: 1=namespace별 SMART/Health Log 지원, 0=namespace별 보고 미지원입니다. Controller 전체 로그와 구분합니다.
AVSCC|0|VSCF: 1=모든 vendor Admin 명령이 Figure 93 형식, 0=명령 형식이 vendor specific입니다.
APSTA|0|APTS: 1=자동 전원 상태 전환 지원, 0=미지원입니다. 현재 APSTE와 다른 값입니다.
RPMBS|31:24|ASZE: target 존재 시 최대 접근 크기=(값+1)×512 B입니다. 0도 512 B 1단위를 지원합니다. Target 0개이면 host가 무시하는 것이 권고됩니다.
RPMBS|23:16|TSZE: target 존재 시 각 RPMB 크기=(값+1)×128 KiB입니다. Target 0개이면 host가 무시하는 것이 권고됩니다.
RPMBS|5:3|AUTHM: 000b=HMAC SHA-256, 001b~111b=Reserved입니다.
RPMBS|2:0|NRPMBU: 지원 RPMB target 개수입니다. 0=RPMB 미지원. 0이 아니면 Security Send/Receive 지원이 필수이고 모든 target의 RPMBS 능력이 같아야 합니다.
DSTO|1|HIRS: 1=Host-Initiated Refresh 지원, 0=미지원입니다. OACS.DSTS=0이면 HIRS도 0이어야 합니다.
DSTO|0|SDSO: 1=subsystem 전체에 self-test 하나만 진행 가능, 0=controller마다 하나씩 진행 가능합니다.
HCTMA|0|HCTMS: 1=Host Controlled Thermal Management 지원 및 FID 10h Get/Set 지원 필수, 0=미지원입니다.
SANICAP|31:30|NODMMAS: No-Deallocate=1로 시작한 sanitize의 추가 media 변경 여부입니다. 00b=미정의(허용 버전·미지원 조건 있음), 01b=추가 변경 안 함, 10b=추가 변경함, 11b=Reserved입니다.
SANICAP|29|NDI: 1이면 NODAS=1 처리에 Sanitize Config의 NODRM 조건을 적용합니다. NODRM=1이면 Idle 전이 전 user data media를 deallocate합니다. NODRM=0 또는 해당 Feature 미지원이면 NODAS=1 명령을 Invalid Field in Command로 중단합니다. NODAS=0에는 영향이 없습니다. NDI=0이면 NODAS 사용을 지원합니다.
SANICAP|3|VERS: 1=Media Verification 및 Post-Verification Deallocation 상태 지원, 0=둘 다 미지원입니다. BES=0이고 CES=0이면 VERS도 0이어야 합니다.
SANICAP|2|OWS: 1=Overwrite sanitize 지원, 0=미지원입니다.
SANICAP|1|BES: 1=Block Erase sanitize 지원, 0=미지원입니다.
SANICAP|0|CES: 1=Crypto Erase sanitize 지원, 0=미지원입니다. Format NVM의 CRYES와 별도 능력입니다.
ANACAP|7|ANAGIDS: 1=Namespace Management에서 non-zero ANAGRPID 지원, 0=미지원입니다. Namespace Management 미지원이면 0이어야 합니다.
ANACAP|6|ANAGIDLWAS: 1=namespace가 어떤 controller에라도 attach된 동안 ANAGRPID 불변, 0=변경 가능입니다.
ANACAP|4|RANACS: 1=ANA Change 상태 보고 가능, 0=보고하지 않습니다.
ANACAP|3|RANAPLS: 1=ANA Persistent Loss 상태 보고 가능, 0=보고하지 않습니다.
ANACAP|2|RANAIS: 1=ANA Inaccessible 상태 보고 가능, 0=보고하지 않습니다.
ANACAP|1|RANANOS: 1=ANA Non-Optimized 상태 보고 가능, 0=보고하지 않습니다.
ANACAP|0|RANAOS: 이름과 참조 §8.1.1.4는 ANA Optimized 상태를 가리키지만 Figure 312 본문은 Inaccessible이라고 기재되어 있습니다. 원문 불일치로 표시하며 정오표 확인 없이 확정 판정하지 않습니다.
KPIOC|1|KPIOSC: 1=enable 시 subsystem의 모든 namespace에 적용, 0=namespace별 독립 enable/disable 가능입니다. KPIOS=0이면 host가 무시하는 것이 권고됩니다.
KPIOC|0|KPIOS: 1=Key Per I/O 지원, 0=미지원입니다.
TMPTHHA|2:0|TMPTHMH: 지원하는 최대 온도 hysteresis의 절댓값, Kelvin 단위입니다. 속성 미지원이면 000b이어야 합니다.
SQES|7:4|MAXSQES: 최대 entry 크기=2^값 바이트. MINSQES 이상이며 권고 지수 6은 64 B입니다.
SQES|3:0|MINSQES: 최소 entry 크기=2^값 바이트. 지수 6(64 B)이 필수입니다.
CQES|7:4|MAXCQES: 최대 entry 크기=2^값 바이트. MINCQES 이상이며 권고 지수 4는 16 B입니다.
CQES|3:0|MINCQES: 최소 entry 크기=2^값 바이트. 지수 4(16 B)가 필수입니다.
ONCS|12|NSZS: 1=Write Zeroes의 NSZ 지원, 0=미지원입니다. Write Zeroes 미지원이면 0이어야 합니다.
ONCS|11|MAXWZD: 1=Deallocate 여부와 WZDSL에 따라 Write Zeroes 최대 크기가 달라짐. 0=이 비트로 추가 효과 없음. Write Zeroes 미지원 또는 WZSL=0이면 0이어야 합니다.
ONCS|10|NVMAFC: 1=모든 Copy가 fast copy, 0=일부는 fast copy가 아닐 수 있습니다.
ONCS|9|NVMCSA: 1=Copy write 부분을 단일 write atomicity로 처리, 0=Copy atomicity의 별도 규정을 적용합니다. Base의 기본 문구는 1을 권고합니다. 이 자료의 Base 2.1·NVM 1.1 조합에서는 Copy 지원 시 NVMCSA=1이 필수입니다. Copy 미지원이면 host는 무시합니다.
ONCS|8|NVMCPYS: 1=NVM Copy 지원, 0=미지원입니다.
ONCS|7|NVMVFYS: 1이면 Verify를 지원하며 VSL은 권장 최대 크기를 나타냅니다. 0이면 VSL이 0인지 확인하여 지원 여부와 최대 크기 제한을 판단합니다.
ONCS|6|TSS: 1=Timestamp Feature 지원, 0=미지원입니다.
ONCS|5|RESERVS: 1=reservation 지원 및 Report/Register/Acquire/Release 명령 지원 필수, 0=미지원입니다. Host Identifier와 reservation 규정의 조건을 함께 봅니다.
ONCS|4|SSFS: 1=Set Features의 non-zero Save와 Get Features의 non-zero Select 지원, 0=지원하지 않습니다. 개별 Feature의 saveable·changeable·scope도 별도로 확인합니다.
ONCS|3|NVMWZSV: 1이면 Write Zeroes를 지원하며 WZSL은 권장 최대 크기를 나타냅니다. 0이면 WZSL이 0인지 확인하여 지원 여부와 최대 크기 제한을 판단합니다.
ONCS|2|NVMDSMSV: 1이면 DSM을 지원하며 DMRL/DMSL/DMRSL의 0이 아닌 값은 지원 한계를 나타냅니다. 0이면 해당 세 필드의 값을 확인하여 지원 여부를 판단합니다.
ONCS|1|NVMWUSV: 1이면 Write Uncorrectable을 지원하며 WUSL은 권장 최대 크기를 나타냅니다. 0이면 WUSL이 0인지 확인하여 지원 여부와 최대 크기 제한을 판단합니다.
ONCS|0|NVMCMPS: 1=NVM Compare 지원, 0=미지원입니다.
FUSES|0|FCWS: 1=Compare+Write fused operation 지원, 0=미지원입니다. Compare가 sequence의 첫 명령입니다.
FNA|3|FNVMBS: 1=Format NVM의 NSID=FFFFFFFFh 미지원, 0=지원입니다. 이름의 Support만 보고 반대로 해석하지 않습니다.
FNA|2|CRYES: 1=Format NVM secure erase의 cryptographic erase 지원, 0=미지원입니다.
FNA|1|SENS: 1=Format의 secure erase가 subsystem 모든 namespace에 적용, 0=특정 namespace에 적용합니다. NSID=FFFFFFFFh이면 이 값과 무관하게 전체에 적용합니다.
FNA|0|FNS: 1=Format이 subsystem 모든 namespace에 적용, 0=특정 namespace에 적용합니다. NSID=FFFFFFFFh이면 이 값과 무관하게 전체에 적용합니다.
VWC|2:1|FB: 00b=broadcast 지원 미표시(Base 1.3 이하 구현만 허용), 01b=Reserved, 10b=NSID=FFFFFFFFh Flush를 Invalid Namespace or Format으로 중단, 11b=broadcast Flush 지원입니다.
VWC|0|VWCP: 1=휘발성 쓰기 캐시 존재, 0=없음입니다. 캐시가 있으면 FID 06h로 현재 enable을 제어합니다.
ICSVSCC|0|SNVSCF: 1=모든 vendor I/O 명령이 Figure 93 형식, 0=vendor specific 형식입니다.
NWPC|2|PWPS: 1=Permanent Write Protect 지원 및 Write Protection Control 필드 지원 필수, 0=미지원입니다. NWPWPS=0이면 0이어야 합니다.
NWPC|1|WPUPCS: 1=Write Protect Until Power Cycle 지원 및 Write Protection Control 필드 지원 필수, 0=미지원입니다. NWPWPS=0이면 0이어야 합니다.
NWPC|0|NWPWPS: 1=No Write Protect 및 Write Protect 상태 지원 필수, 나머지 두 상태는 선택. 0=Namespace Write Protection 미지원입니다.
SGLS|21|TSDBDS: 1=Transport SGL Data Block descriptor 지원, 0=미지원입니다.
SGLS|20|SAOS: 1=SGL Data Block/Segment/Last Segment Address의 offset 표현 지원, 0=미지원입니다.
SGLS|19|MSDS: 1=정확히 하나의 qword-aligned SGL descriptor를 담은 segment 주소를 MPTR로 지정하는 방식 지원, 0=미지원입니다.
SGLS|18|LLDTS: 1=전송량보다 긴 data/metadata SGL 허용, 0=SGL 길이가 전송량과 같아야 합니다.
SGLS|17|MBA: PSDT=01b에서 1=byte-aligned contiguous metadata buffer 지원, 0=이 정렬 방식 미지원입니다.
SGLS|16|SBBDS: 1=SGL Bit Bucket descriptor 지원, 0=미지원입니다. MDTS 계산의 소스·목적지 차이를 확인합니다.
SGLS|15:8|SDT: 명령당 권장 최대 SGL descriptor 수입니다. 0=권장 최대 미보고이며 강제 제한과 구분합니다.
SGLS|2|KSDBDS: 1=Keyed SGL Data Block descriptor 지원, 0=미지원입니다.
SGLS|1:0|SGLS: 00b=SGL 미지원, 01b=Data Block 정렬·granularity 제한 없음, 10b=dword 정렬·granularity 필요, 11b=Reserved입니다.
TRATTR|2|MRTLL: 1=RMRTG와 Length로 나타낸 길이가 2의 거듭제곱인 경우만 지원, 0=2의 거듭제곱일 필요 없음입니다.
TRATTR|1|TUDCS: 1=user data 변경 추적 지원, 0=미지원입니다.
TRATTR|0|THMCS: 1=host memory 변경 추적 지원, 0=미지원입니다.
FCATT|1|NZNSETIDS: 1=Connect의 non-zero NVMSETID 지원, 0=미지원입니다.
FCATT|0|DCMS: 0=dynamic controller 모델, 1=static controller 모델입니다. 이름만 보고 1을 dynamic으로 해석하지 않습니다.
OFCS|0|DCS: 1=Disconnect 명령과 개별 I/O Queue 삭제 지원, 0=미지원입니다.
'''
BITS={}
def norm(r):return ':'.join(str(int(v)) for v in r.split(':'))
for line in BIT_TEXT.strip().splitlines():
    f,r,t=line.split('|',2); BITS[(f,norm(r))]=t
for i in range(16):
    BITS[('RRLS',str(i))]=f'RRL{i}: 1=Level {i} 지원, 0=미지원입니다.'+(' RRL 지원 시 반드시 1입니다. '+('Default 레벨입니다.' if i==4 else 'Fast Fail 레벨입니다.') if i in (4,15) else '')
for i in range(5):BITS[('CDFS',str(i))]=f'CDF{i}S: 1=Copy descriptor format {i}h 지원, 0=미지원입니다.'

PSD_TEXT=r'''
EPFVTS|Emergency Power Fail vault 시간 scale|EPFVT와 곱하는 시간 scale입니다. EPFVT=0이면 scale도 0이어야 하며 host는 무시합니다.
FQVTS|Forced Quiescence vault 시간 scale|FQVT와 곱하는 시간 scale입니다. FQVT=0이면 scale도 0이어야 하며 host는 무시합니다.
EPFRTS|Emergency Power Fail 복구 시간 scale|EPFRT와 곱하는 시간 scale입니다. EPFRT=0이면 scale도 0이어야 하며 host는 무시합니다.
EPFVT|Emergency Power Fail vault 시간|실패가 없을 때 Emergency Power Fail Processing을 완료하는 최악 시간입니다. PLSI.PLSEPF=0이면 0이어야 합니다. 0=값을 보고하지 않음, 1~99=시간값, 100~255=Reserved. 시간=값×EPFVTS scale입니다.
FQVT|Forced Quiescence vault 시간|실패가 없을 때 Forced Quiescence Processing을 완료하는 최악 시간입니다. PLSI.PLSFQ=0이면 0이어야 합니다. 0=값을 보고하지 않음, 1~99=시간값, 100~255=Reserved. 시간=값×FQVTS scale입니다.
EPFRT|Emergency Power Fail 복구 시간|전원 손실 전에 Emergency Power Fail 처리가 완료된 뒤, 첫 initialization을 완료하는 최악 시간입니다. 실패가 없는 조건에 적용합니다. PLSEPF=0이면 0이어야 합니다. 0=값을 보고하지 않음, 1~99=시간값, 100~255=Reserved. 시간=값×EPFRTS scale입니다.
APS|Active Power scale|00b=미보고, 01b=0.0001 W, 10b=0.01 W, 11b=Reserved입니다. ACTP에 곱합니다.
APW|Active Power 측정 workload|000b=No Workload, 001b=Workload 1, 010b=Workload 2, 011b~111b=Reserved입니다. ACTP≠0일 때 No Workload를 사용하면 안 됩니다. Workload 1은 5분 idle 뒤 1 MiB random write 32개와 30초 idle, Workload 2는 128 KiB sequential write 80,000개입니다. 한 controller에서 수행하고 나머지 controller는 idle 조건입니다. 별도 workload 근거는 §8.1.17.3 / Figure 626입니다.
ACTP|Active Power|APW workload로 10초 동안 측정한 subsystem 최대 평균 전력입니다. 전력=값×APS scale. 0은 값을 보고하지 않는다는 뜻입니다.
IPS|Idle Power scale|00b=해당 state 미보고, 01b=0.0001 W, 10b=0.01 W, 11b=Reserved입니다. IDLP에 곱합니다.
IDLP|Idle Power|Subsystem idle 10초 뒤 시작하는 30초 동안의 일반적인 소비 전력입니다. Pending command·property access·background process·sanitize·self-test 등이 없는 조건입니다. 전력=값×IPS scale. 0은 값을 보고하지 않는다는 뜻입니다.
RWL|상대 write latency|다른 power state와 비교한 상대 write latency입니다. 값이 낮을수록 더 낮은 latency이며 절대 시간 단위가 아닙니다.
RWT|상대 write throughput|다른 power state와 비교한 상대 write throughput입니다. 값이 낮을수록 더 높은 throughput이며 MB/s 값이 아닙니다.
RRL|상대 read latency|다른 power state와 비교한 상대 read latency입니다. 값이 낮을수록 더 낮은 latency입니다. RRLS의 Read Recovery Level과 다른 필드입니다.
RRT|상대 read throughput|다른 power state와 비교한 상대 read throughput입니다. 값이 낮을수록 더 높은 throughput입니다.
EXLAT|상태 복귀 지연|μs 단위의 power state exit 최대 지연입니다. 0은 Exit Latency 미보고입니다. 전환 최대 시간은 이전 state의 EXLAT와 다음 state의 ENLAT 합입니다.
ENLAT|상태 진입 지연|μs 단위의 power state entry 최대 지연입니다. 0은 Entry Latency 미보고입니다.
NOPS|Non-operational state 여부|1=non-operational state로 I/O 명령을 처리하지 않음, 0=operational state로 처리합니다. Non-operational state의 APS/APW/ACTP는 0이어야 합니다.
MXPS|Maximum Power scale|0=0.01 W, 1=0.0001 W 단위입니다. MP에 곱합니다.
MP|최대 지속 전력|Subsystem이 해당 state에서 소비하는 지속 최대 전력입니다. 전력=값×MXPS scale. 0은 값을 보고하지 않는다는 뜻입니다. Host 전력·성능 관리의 대략적 지침이며 플랫폼별 측정 규정과 구분합니다.
'''
PSD={}
for line in PSD_TEXT.strip().splitlines():
    k,t,ko=line.split('|',2);PSD[k]=dict(title=t,ko=ko)

TOPICS={
 '식별·버전':['VID','SSVID','SN','MN','FR','IEEE','CNTLID','VER','CNTRLTYPE','FGUID','SUBNQN','DID'],
 '전원·열 관리':['RTD3R','RTD3E','NSSL','PLSI','NPSS','APSTA','WCTEMP','CCTEMP','HCTMA','MNTMT','MXTMT','TMPTHHA'],
 '명령·전송':['RAB','MDTS','CRDT1','CRDT2','CRDT3','OACS','ACL','ONCS','FUSES','SQES','CQES','MAXCMD','OAQD','SGLS','AVSCC','ICSVSCC'],
 '이벤트·로그':['OAES','AERL','LPA','ELPE','PELS'],
 'Namespace·용량·경로':['CMIC','CTRATT','CRCAP','TNVMCAP','UNVMCAP','NSETIDMAX','ENDGIDMAX','ANATT','ANACAP','ANAGRPMAX','NANAGRPID','MEGCAP','NN','MNAN','MAXDNA','MAXCNA','NWPC'],
 'NVM 동작·atomicity':['AWUN','AWUPF','ACWU','CDFS','FNA','VWC','RRLS','SANICAP','KPIOC'],
 '펌웨어·진단':['FRMW','MTFA','MPTFAWR','FWUG','EDSTT','DSTO','RHIRI','HIRT','BPCAP','RPMBS'],
 'Host memory·마이그레이션':['HMPRE','HMMIN','HMMINDS','HMMAXD','CMMRTD','NMMRTD','MINMRTG','MAXMRTG','TRATTR','MCUDMQ','MNSUDMQ','MCMR','NMCMR','MCDQPC'],
 'Fabrics·관리':['KAS','CQT','IOCCSZ','IORCSZ','ICDOFF','FCATT','MSDBD','OFCS','DCTYPE','NVMSR','VWCI','MEC']}

def make_fields():
    for f in DATA['fields']:
        k=f['id']
        if k.startswith('RESERVED_'):
            f.update(title='NVMe-MI 예약 영역' if f['start']==240 else '예약 영역',unit='Reserved',ko='이 바이트 범위는 '+('NVMe Management Interface 용도로 예약되어 있습니다. 두 PDF에는 내부 layout이 없습니다.' if f['start']==240 else '예약되어 있습니다. 정의된 필드 값으로 해석하거나 임의의 능력 정보를 부여하지 않습니다.'),topic='예약·Vendor Specific')
        elif re.fullmatch(r'PSD\d+',k):
            i=int(k[3:]);f.update(title=f'전원 상태 {i} 설명자',unit='32바이트 반복 구조',ko=f'Power State {i}의 전력·지연·상대 성능을 설명하는 descriptor입니다. '+('PS0은 반드시 지원합니다.' if i==0 else f'NPSS≥{i}인 경우 지원 상태 descriptor로 사용합니다.'),topic='전원·열 관리')
            f['psd_index']=i
            f['sources']=f['sources']+[s for s in dict((b['source']['pdf_page'],b['source']) for b in DATA['psd']).values()]
        else:
            assert k in EDITOR, f'Missing Korean field {k}'
            f.update(EDITOR[k]);f['topic']=next((t for t,keys in TOPICS.items() if k in keys),'예약·Vendor Specific')
        f['encoding']='고정 길이 ASCII' if k in ['SN','MN','FR'] else 'UTF-8 NUL 종료' if k=='SUBNQN' else 'big endian EUI-64 기반' if k=='FGUID' else '바이트 배열 (아래 정의 참조)' if k in ['IEEE','VS'] or 'psd_index' in f or k.startswith('RESERVED_') else 'little endian (하위 바이트부터 저장)'
        if f['start']==f['end'] and not k.startswith('RESERVED_'):f['encoding']='1바이트 값 (비트별 정의 참조)'
        for b in f['bits']:
            r=norm(b['range']);b['range']=r
            if b['english'].strip()=='Reserved':b['ko']='예약 비트입니다. 정의된 기능이나 값으로 해석하지 않습니다.';b['title']='Reserved'
            else:
                assert (k,r) in BITS, f'Missing Korean bit {k}.{r}'
                b['ko']=BITS[k,r];m=re.search(r'\(([A-Z0-9]+)\)',b['english']);b['title']=m[1] if m else '비트 정의'
        f['rules']=[];f['edges']=[];f['notes']=[];f['external']=[]
    for b in DATA['psd']:
        if b['id'].startswith('PSD_RESERVED_'):b.update(title='Reserved',ko='예약 비트입니다. 정의된 값으로 해석하지 않습니다.')
        else:b.update(PSD[b['id']])
    return DATA
