"""OCP DSSD 2.6 overlay. Never promote profile rules to generic NVMe rules."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SCOPE='OCP Datacenter NVMe SSD 2.6를 적용하는 PCIe SSD'
# fields | PDF/printed page | section | requirement IDs | applicability | observations | Korean requirement | interpretation
ROWS=r'''
MDTS|9|4.3|NVMe-CFG-2|공통|MDTS, CAP.MPSMIN, 전송 데이터·metadata 크기|최소 256 KiB 전송을 지원해야 한다. MDTS가 0이 아니면 2^MDTS × 2^(12+CAP.MPSMIN) ≥ 262144 bytes인지 확인한다. MDTS=0은 이 필드에 한도가 없다는 뜻이며 지원하지 않음을 뜻하지 않는다. 이 경우 명령별 한도와 실제 256 KiB 전송 지원을 추가 확인한다.|환산
MDTS|10|4.3|NVMe-CFG-16,NVMe-CFG-17|공통|CAP.MPSMIN, CAP.MPSMAX, MDTS|CAP.MPSMIN=0, CAP.MPSMAX≥1이어야 한다. 따라서 MDTS의 기준 단위는 4 KiB이며 MDTS가 0이 아니면 최소값은 6이다. MPSMAX나 현재 CC.MPS로 MDTS 단위를 환산하지 않는다.|환산
MDTS|17|4.7|CTO-3,CTO-6|TTR-2의 I/O 준비 조건을 만족한 상태|MDTS, FID 07h Number of Queues, CAP.MQES, QD1 및 full-load 지연 측정|MDTS·큐 수·최대 큐 엔트리 설정으로 CTO-3을 위반하지 않아야 한다. QD1 I/O는 8초 이내, full load에서는 1시간 중 2초 초과 I/O가 7개 이하여야 한다. Identify 값만으로 이 동작을 판정할 수 없다.|명시
RAB|9|4.3|NVMe-CFG-1|공통|CAP.AMS, CC.AMS, FID 01h Arbitration, RAB|기본 arbitration은 Round Robin이며 Weighted Round Robin with Urgent Class Priority도 지원해야 한다. RAB는 burst 권고값이다. 이 요구가 RAB의 특정 수치를 지정하거나 arbitration 지원 비트를 대신하지는 않는다.|관계
CTRATT DID|10|4.3|NVMe-CFG-12|공통|CAP.CPS, CTRATT.Multiple Domains Support, DID|CAP.CPS=11b이고 multiple domains를 지원하지 않아야 한다. CNS 01h의 multiple-domain 지원 보고 및 DID는 Base의 단일-domain 정의와 일치해야 한다. OCP의 직접 지정 대상은 CAP.CPS이다.|관계
CNTRLTYPE|10|4.3|NVMe-CFG-13|공통|CNTRLTYPE, CAP.CSS|CNTRLTYPE=01h이어야 하며 CAP.CSS bit 0=1, bit 6=0, bit 7=0이어야 한다. Administrative·Discovery controller용 NVMe 설명을 OCP SSD의 허용 유형으로 해석하지 않는다.|명시
SQES|10|4.3|NVMe-CFG-14|공통|SQES[7:4], SQES[3:0], CC.IOSQES|최대 SQ entry는 64 bytes이므로 SQES[7:4]=6이다. NVM의 최소 entry 64 bytes 정의와 합치면 SQES=66h이다.|환산
CQES|10|4.3|NVMe-CFG-15|공통|CQES[7:4], CQES[3:0], CC.IOCQES|최대 CQ entry는 16 bytes이므로 CQES[7:4]=4이다. 최소 entry 16 bytes 정의와 합치면 CQES=44h이다.|환산
ELPE|10|4.3|NVMe-CFG-18|공통|ELPE, Error Information Log 엔트리 수|256개의 Error Log 엔트리를 지원해야 한다. ELPE는 0-based 8-bit 값이므로 ELPE=FFh, 엔트리 수=ELPE+1=256이다.|환산
HMMIN HMPRE|10|4.3|NVMe-CFG-19|공통|HMMIN, HMPRE, FID 0Dh Host Memory Buffer|HMMIN=0 및 HMPRE=0이어야 하며 Host Memory Buffer 기능을 지원하지 않아야 한다. 0을 크기 미보고나 일시적 비활성화로 해석하지 않는다.|명시
OACS|10|4.4|NVMe-AD-3,NVMe-AD-4|공통|OACS Namespace Management/Attachment 지원 비트, CNS, 명령 결과|Namespace Management와 Namespace Attachment를 지원해야 한다. 해당 OACS 지원 보고와 생성·삭제·attach/detach 동작을 함께 확인한다.|관계
OACS FNA|10|4.4|NVMe-AD-5|공통|OACS Format NVM 지원, FNA Cryptographic Erase 지원, SES 000b/001b/010b|Format NVM 및 SES 000b, 001b, 010b를 지원해야 한다. Format 지원 보고와 cryptographic erase 지원 보고가 명령 동작에 맞아야 한다.|관계
OACS|10|4.4|NVMe-AD-6|공통|OACS bit 6, NVMe-MI Receive/Send, tunneled MI command 종류|OACS bit 6=1로 NVMe-MI Receive/Send 명령 지원을 보고한다. Receive로 매핑되는 필수 MI 명령은 in-band tunneling으로 지원하고 Send로 매핑되는 MI 명령은 금지한다. NVMe-MI Send라는 NVMe 운반 명령의 지원과 내부 MI 명령의 허용 여부를 구분한다.|명시
SANICAP|11|4.4|NVMe-AD-7|공통|SANICAP BES/OWS/CES, Sanitize SANACT|Block Erase 010b, Overwrite 011b, Crypto Erase 100b를 모두 지원해야 한다. SANICAP의 세 지원 비트와 각 명령의 실행 결과가 일치해야 한다.|관계
CTRATT|11|4.4|NVMe-AD-10|공통|CTRATT UUID List 지원, Identify CNS 17h|UUID List CNS 17h를 지원해야 한다. UUID List 지원 보고와 반환 목록을 함께 확인한다.|관계
OACS EDSTT DSTO|11|4.4|NVMe-AD-12|공통|OACS Device Self-test 지원, EDSTT, DSTO, 명령 및 Log 06h|Device Self-test 명령을 지원해야 한다. 지원 비트를 보고하고 EDSTT·DSTO를 Base의 지원 시 정의에 따라 보고한다. 이 요구 자체는 DSTO의 특정 값을 지정하지 않는다.|관계
OACS|191|13|DP-CFG-11|고객이 DP-CFG-11의 A 설정을 선택한 경우|고객의 항목별 A/B 선택, OACS bit 10, in-band Lockdown|A는 Required이므로 Lockdown을 지원하고 OACS bit 10=1로 보고해야 한다. 제품 전체를 A형/B형으로 단정하지 말고 이 항목의 고객 선택을 확인한다.|명시
OACS|191|13|DP-CFG-11|고객이 DP-CFG-11의 B 설정을 선택한 경우|고객의 항목별 A/B 선택, OACS bit 10, in-band Lockdown|B는 Prohibited이므로 in-band Lockdown을 지원하면 안 되며 OACS bit 10=0이어야 한다. 프로파일을 모르면 A 조건과 B 조건 중 어느 것이 적용되는지 판단할 수 없다.|명시
OACS|11|4.4|NVMe-AD-14,NVMe-AD-15,NVMe-AD-16|DP-CFG-11에서 Lockdown 지원을 요구한 경우|지원 Admin 명령·Feature 목록, Lockdown 동작, Log 14h|Lockdown 자신을 포함한 모든 지원 in-band Admin 명령 및 모든 지원 Feature를 lockdown할 수 있어야 한다. AD-14의 일반 지원 문장에는 DP-CFG-11 예외를 적용한다.|명시
SANICAP|11|4.4|NVMe-AD-17,NVMe-AD-18|공통|SANICAP NODMMAS, NDI, Sanitize 후 media 변경|NODMMAS=01b, NDI=0이어야 한다. Sanitize 후 추가 media modification은 금지한다.|명시
SANICAP FNA|11|4.4|NVMe-AD-8,NVMe-AD-19|purge 또는 NODAS=1 Sanitize 후 checksum 오류 예외가 발생한 경우|Sanitize/Format 인자, sanitize status, deallocation 및 후속 read 결과|AD-8의 purge 후에는 deallocate하고 미기록 LBA read에서 zero를 반환한다. Overwrite sanitize는 마지막 overwrite pass의 bytes를 반환하는 예외가 있다. AD-19의 checksum 오류 예외는 NODAS=1이어도 deallocate하고 성공 후 status=100b를 보고한다. 이 예외는 NVMe의 일반 동작을 override한다.|명시
SANICAP|12|4.4|NVMe-AD-26|공통|Sanitize Media Verification 지원 보고, SANICAP 해당 비트, 검증 동작|TP4152의 Sanitize Media Verification을 지원해야 한다. Base 2.1에 통합된 대응 지원 정의와 검증 동작을 대조한다. 원래 TP 전체를 이 문서만으로 재구성하지는 않는다.|관계
FNA|12|4.4|NVMe-AD-23|공통|FNA bit 0 및 bit 1, namespace별 Format NVM|FNA bit 0=0, bit 1=0이어야 하며 namespace별 Format NVM을 지원해야 한다.|명시
AERL|12|4.4|NVMe-AD-24|공통|AERL raw 값, outstanding Asynchronous Event Request 수|AERL 필드에 최소 4를 보고해야 한다. 0-based이므로 동시 outstanding AER 지원 수는 최소 5이다. 최소 4개 요청 지원으로 잘못 환산하지 않는다.|명시
AERL OAES|12|4.4|NVMe-AD-25|해당 event reporting은 enabled이나 outstanding AER가 없는 경우|FID 0Bh event enable, event 발생/대기 이력, AER completion|event 정보를 보존하여 이후 AER 응답에 사용해야 하며 대기 중인 중복 event는 한 번만 보고한다. AER가 없다는 이유로 OAES 지원 비트가 바뀌는 것은 아니다.|명시
OACS LPA|12|4.4|NVMe-AD-27|공통|OACS Get LBA Status 지원 비트, LID 0Eh 지원|Get LBA Status 명령은 OCP 필수가 아니다. 그러나 LBA Status Information Log는 필수다. Log 지원만으로 OACS의 명령 지원 비트를 반드시 1로 만들지 않는다.|명시
NN MNAN|12|4.4.1|NSM-4,NSM-5|고객 DP-CFG-2 선택 및 usable capacity를 확인한 경우|DP-CFG-2 A/B 선택, usable capacity(TiB), NN, MNAN 및 namespace 생성 가능 수|A는 최소 16 namespace 지원이다. B는 NSM-5의 용량별 표를 적용한다(≤1 TiB:16, (1,2]:32, (2,3]:48, (3,4]:64, …, >7 TiB:128). NSM-5 본문의 at 7 TiB 128과 표의 >7 TiB 128 경계 표현이 다르므로 7 TiB 경계는 고객 확인 대상으로 남긴다. NN/MNAN의 서로 다른 NVMe 의미를 고려해 실제 지원 수를 확인한다.|관계
CTRATT|12|4.4.1|NSM-6|공통|CTRATT Namespace Granularity 지원, CNS 16h descriptor 수|Namespace Granularity List에서 최소 1 descriptor를 보고해야 한다. 지원 보고와 목록을 대조하고 목록의 0-based 개수를 실제 개수로 환산한다.|관계
TNVMCAP UNVMCAP|12|4.4.1|NSM-7|공통|TNVMCAP, UNVMCAP, namespace 할당 상태|두 용량 필드를 지원해야 한다. OCP는 이 문장에서 두 값이 항상 0보다 커야 한다고 요구하지 않는다. UNVMCAP=0은 모두 할당된 상태일 수 있다.|명시
CTRATT|13|4.4.1|NSM-8|공통|CTRATT Extended LBA Formats Supported|Extended LBA Formats Supported 비트를 0으로 보고하고 extended LBA formats를 지원하지 않아야 한다.|명시
VWC|15|4.5|NVMe-IO-3|공통|VWC volatile-cache-present, PLP, Flush/FUA, FID 06h WCE disable 결과|PLP 때문에 cache가 non-volatile이며 volatile write cache는 없다. VWC의 cache-present 보고는 이에 맞아야 한다. FUA는 성능 저하를 유발하지 않고 Flush는 non-volatile cache에 영향이 없어야 한다. WCE disable Set Features는 Base에서 정의한 오류로 실패해야 한다.|관계
ONCS|15|4.5|NVMe-IO-2,NVMe-IO-4|공통|Dataset Management/Write Zeroes 동작, ONCS 해당 비트, CNS 06h 명령별 지원·크기 한도|DSM과 Write Zeroes를 지원하며 Write Zeroes의 DEAC와 FUA도 지원해야 한다. Base 2.1/NVM 1.1에서는 명령별 크기 제한과 ONCS variant 정의까지 확인한다. OCP의 명령 지원 문장을 ONCS 해당 비트가 무조건 1이라는 요구로 바꾸지 않는다.|관계
ONCS|15|4.5|NVMe-IO-8|공통|ONCS Compare 지원, Compare 명령 결과|Compare 명령을 지원해야 하며 해당 지원 보고와 실제 동작이 일치해야 한다.|관계
FUSES ACWU|15|4.5|NVMe-IO-9|공통|FUSES fused Compare/Write 지원, ACWU, namespace NACWU, fused 실행|Compare and Write fused pair를 지원해야 한다. FUSES 지원 보고와 ACWU 및 namespace atomicity 제한을 Base/NVM 정의에 맞게 함께 확인한다. 이 요구 자체는 ACWU의 고정 수치를 지정하지 않는다.|관계
ONCS|190|13|DP-CFG-7|고객 DP-CFG-7 선택을 확인한 경우|항목별 A/B 선택, Write Uncorrectable 지원 보고 및 실행|A에서는 Write Uncorrectable이 Optional이며 B에서는 Required이다. A의 Optional을 Prohibited로 해석하지 않는다.|명시
ONCS|15|4.5|NVMe-IO-10,NVMe-IO-11,NVMe-IO-12|Write Uncorrectable을 지원하는 모델|지원 보고, 단일 LBA 요청 및 최대 LBA 요청, CNS 06h 한도|FTL IU와 관계없이 단일 LBA 단위 marking을 지원하고 NVM Command Set의 최소·최대 범위보다 추가적인 LBA 수 제한을 두면 안 된다. DP-CFG-7 선택과 함께 확인한다.|명시
ONCS|16|4.6|NVMe-OPT-2,NVMe-OPT-4,NVMe-OPT-5,NVMe-OPT-13|Timestamp 지원 및 Set Features로 timestamp를 설정한 경우|ONCS Timestamp 지원, FID 0Eh timestamp/origin/synch/saveable, reset 종류|Timestamp를 지원한다. NSSR 이외 Controller Level Reset에서는 설정 timestamp를 유지하고 Origin=001b를 보고한다. NSSR 보존은 선택이다. Synch는 항상 0이며 Timestamp는 saveable이 아니어야 한다. 특정 Feature의 비저장성이 ONCS 전체 저장 기능 미지원이라는 뜻은 아니다.|명시
LPA|16|4.6|NVMe-OPT-8|공통|LPA bit 3, telemetry notices 및 Log 07h/08h|LPA bit 3=1이어야 하며 Telemetry Log Notices를 지원해야 한다.|명시
LPA OAES|16|4.6|NVMe-OPT-6|Telemetry Log Changed event를 발생시키는 경우|telemetry event 원인, periodic logging, event completion|오류 상황에만 Telemetry Log Changed event를 생성하고 주기적 logging 때문에 생성하지 않아야 한다. Log 지원과 event 발생 정책을 구분한다.|명시
OAES|16|4.6|NVMe-OPT-9,NVMe-OPT-10|공통|OAES bit 8/9, attached namespace, Changed Namespace List, firmware activation event|OAES bit 8=1, bit 9=1이어야 한다. Namespace Attribute Changed event는 controller에 attached된 namespace에 대해서만 보고한다.|명시
AWUPF|16|4.6|NVMe-OPT-15|NAWUPF를 보고하는 namespace의 atomicity를 확인하는 경우|namespace IU, NAWUPF, NSFEAT.NAWUPF 관련 선택, LBA 크기, AWUPF|OCP는 IU 크기를 namespace NAWUPF로 보고하도록 요구한다. NAWUPF는 0-based LBA 수이므로 (NAWUPF+1)×LBA 크기로 환산하고 적용되는 Base/NVM atomicity 관계를 확인한다. 이 요구는 controller AWUPF 자체를 IU 값으로 고정하지 않는다.|관계
ONCS CDFS|16|4.6|NVMe-OPT-16|공통|ONCS Copy 지원, CDFS Format 0 지원, CNS 06h Copy 지원, 명령 동작|Copy 및 Source Range Entries Descriptor Format 0을 지원해야 한다. Base 2.1/NVM 1.1의 ONCS·CDFS·명령별 Identify 지원 보고와 맞아야 한다.|관계
LPA|18|4.8.1|STD-LOG-6,STD-LOG-7,STD-LOG-8,STD-LOG-9|공통|LPA Commands Supported and Effects/telemetry/Persistent Event 지원, LID 05h/07h/08h/0Dh|네 Log를 모두 지원해야 한다. 대응 LPA 지원 비트와 Log 반환을 대조한다. 이 문장만으로 모든 LPA 비트를 1로 만들거나 Data Area 4까지 필수라고 단정하지 않는다.|관계
LPA|19|4.8.1|STD-LOG-18|공통|LPA bit 0, namespace-specific SMART 요청|namespace별 SMART / Health Log를 지원하지 않아야 하며 LPA bit 0=0이어야 한다.|명시
PELS|20|4.8.1|STD-LOG-22|공통|PELS raw 값, Persistent Event Log 최대 크기|PELS가 나타내는 최대 크기는 최소 5 MiB여야 한다. 단위가 64 KiB이므로 PELS≥80(50h)이다. 현재 반환 Log 길이가 항상 5 MiB라는 뜻은 아니다.|환산
FR|114|4.9.16.1|TELDF-11|Telemetry data area header를 확인하는 경우|CNS 01h FR 8 bytes, telemetry header bytes 63:56|Telemetry header의 Firmware Revision은 Identify Controller FR 값과 같아야 한다. 현재 활성 firmware와 다른 slot의 revision을 비교 대상으로 쓰지 않는다.|명시
EDSTT|122|4.10|SELFTST-3|extended Device Self-test(STC=2h)를 실행하는 경우|EDSTT, extended self-test 실제 완료 시간|extended self-test는 30분 이내에 완료되어야 하며 EDSTT≤30분으로 보고해야 한다. 명령 CQE 완료와 background self-test 완료를 구분한다.|명시
OACS FRMW|123|4.11|FWUP-3,FWUP-4|공통|OACS firmware command 지원, FRMW resetless activation 지원, Firmware Commit CA|Firmware Image Download와 Firmware Commit CA=000b/001b/010b/011b를 지원해야 한다. resetless activation 지원 보고가 CA=011b 실행과 맞아야 한다.|관계
FRMW|123|4.11|FWUP-6|공통|FRMW slot 수·slot 1 read-only, Firmware Slot Information Log|최소 2개의 read/write firmware slot을 지원해야 한다. FWUP-20의 read-only slot 1까지 포함하면 총 slot 수는 최소 3이다. 최소 2개는 전체 slot 수가 아니라 read/write slot 수다.|환산
FRMW FR|124|4.11|FWUP-20|공통 및 security version 증가 firmware가 RW slot에 활성화된 경우|FRMW slot 1 read-only, slot Log, security version 및 활성 firmware|slot 1은 read-only로 지원해야 한다. RW slot에 활성화한 firmware가 Security Version Number를 증가시키면 read-only slot 1도 해당 이미지로 갱신해야 한다. 호스트의 일반 download에 대한 read-only와 장치 내부 갱신을 구분한다.|명시
MTFA MPTFAWR|123|4.11|FWUP-7|Firmware Commit CA=011b(resetless)를 실행하는 경우|MTFA, MPTFAWR, Commit 수신부터 activation 및 I/O/Admin 준비까지 시간|MTFA≤0Ah이어야 하며 Commit 수신부터 activation 완료 및 I/O/Admin 명령 수신 준비까지 1초 이내여야 한다. MTFA 단위는 100 ms다. OCP가 직접 0Ah를 지정한 필드는 MTFA이며 MPTFAWR의 raw 값을 같은 수치로 제한하지 않는다.|명시
FRMW APSTA NPSS|123|4.11|FWUP-11|resetless firmware activation 수행 전후|현재 Feature 값, Timestamp, 큐, power management/APST 설정, PCIe 및 MI 상태|resetless activation은 현재 Feature 값, Timestamp, 큐 설정, TCG 및 NVMe-MI 상태를 보존하고 PCIe link 상태에 영향을 주면 안 된다. 지원 능력과 현재 Feature 설정을 구분한다.|명시
SN|123|4.11|FWUP-13|firmware update 전후|Identify SN, VPD/FRU 고유 Serial Number|firmware 이미지에 포함되어 갱신 가능한 VPD/FRU라도 장치 고유 Serial Number는 firmware update 동안 보존해야 한다.|관계
FR|124|4.11|FWUP-22|현재 활성 firmware image가 손상된 경우|동일 image backup, slot별 revision, failover 이력|동일 image의 backup copy로 failover해야 하며 다른 slot의 다른 firmware revision으로 자동 failover하면 안 된다. 원문은 이를 NVMe override로 명시한다.|명시
FR|125|4.11|FWUP-28|FIPS 140-3 인증을 받은 제품|FIPS 인증의 Firmware Version 목록, Identify FR|인증서의 Firmware Version 값은 Identify FR 값과 일치해야 한다. 인증 정보가 없으면 해당 조건을 확인할 수 없다.|명시
FWUG|125|4.11|FWUP-29|공통|FWUG, Firmware Image Download offset/size|FWUG=01h, 즉 4096-byte granularity를 보고해야 한다. FFh(제약 없음)나 00h(정보 없음)를 같은 의미로 취급하지 않는다.|명시
ONCS NPSS|166|10.3|PWR-1,PWR-5|공통|FID 02h Power Management, SV=1, power cycle 후 값, ONCS 저장 지원|Power Management를 지원하고 SV=1로 지정한 power level을 power cycle 후에도 저장해야 한다. 지원 capability·저장된 값·현재 값을 각각 확인한다.|관계
CTRATT|166|10.3|PWR-9|공통|CTRATT bit 1, Non-Operational Power State Permissive Mode|Non-Operational Power State Permissive Mode를 지원하지 않아야 하며 CTRATT bit 1=0이어야 한다.|명시
WCTEMP|164|9.2|TTHROTTLE-9|공통|WCTEMP raw 값|WCTEMP=015Eh(350 K, 원문 표기 77°C)이어야 한다. 원문의 지정 정수값을 우선 사용한다.|명시
CCTEMP|164|9.2|TTHROTTLE-10|공통|CCTEMP raw 값|CCTEMP=0166h(358 K, 원문 표기 85°C)이어야 한다. 원문의 지정 정수값을 우선 사용한다.|명시
WCTEMP CCTEMP|163|9.2|TTHROTTLE-2,TTHROTTLE-5,TTHROTTLE-7|thermal throttling 시작/해제 및 reporting enabled/outstanding AER 조건|composite temperature, SMART Critical Warning bit 1, FID 0Bh, AER|77°C에서 throttling을 시작하고 75°C 미만이면 해제한다. 시작/해제 시 SMART Critical Warning bit 1을 설정/해제하고 reporting enabled이며 AER가 outstanding이면 temperature threshold event를 완료한다.|명시
CCTEMP|164|9.2|TTHROTTLE-8|component가 critical temperature에 도달하여 보호 shutdown하는 경우|실제 온도, composite 보고, SMART/AER, shutdown 순서|보호 shutdown 전에 composite temperature=85°C를 보고하고 event reporting enabled 및 outstanding AER 조건에서 temperature threshold event를 완료한다.|명시
WCTEMP|164|9.2|TTHROTTLE-11|composite temperature≥77°C인 경우|SMART Warning Composite Temperature Time, 온도·전원 이력|warning temperature time을 매분 갱신한다. 75°C 미만으로 내려가거나 critical shutdown 또는 power cycle하면 해당 갱신 구간이 끝난다.|명시
WCTEMP CCTEMP|108|4.9.14.2.8|EVC-TEMP-2|Temperature Debug Event를 기록하는 경우|temperature debug event ID, composite 변화, WCTEMP/CCTEMP|event ID 0000h는 WCTEMP−2로 하강, 0001h는 WCTEMP로 상승, 0002h는 CCTEMP 도달이다. 기록 후 중복 기록 방지를 위한 2-degree hysteresis는 SHOULD(권고)이며 event 매핑은 SHALL이다.|명시
OACS|180|12.1|SEC-46|TCG device인 경우|OACS bit 0, in-band Security Send/Receive|TCG device는 in-band Security Send/Receive를 지원해야 하며 OACS bit 0=1이어야 한다.|명시
SN MN VID|184|12.3.1|CERT-1|SPDM leaf certificate를 확인하는 경우|인증서 DMTF-serialNumber/product/manufacturer, SN/MN/VID|DMTF-serialNumber는 SN, DMTF-product는 MN과 같아야 한다. DMTF-manufacturer는 VID의 hexadecimal ASCII 표현이며 앞의 0x나 뒤의 h를 붙이지 않는다.|명시
MN|194|14.1|LABL-11|고객의 서면 면제가 없는 경우|Barcode-1 model, label model, Identify MN, 고객 면제 문서|세 Model Number가 모두 같아야 한다. 고객의 서면 면제가 있으면 그 범위를 먼저 확인한다.|명시
SN|194|14.1|LABL-12|공통|Barcode-1 serial, label serial, Identify SN|세 Serial Number가 모두 같아야 한다.|명시
'''

EXTRA_ROWS=r'''
NPSS APSTA|166|10.3|PWR-6,PWR-7|idle 상태 또는 각 power state/setting으로 동작하는 경우|idle 및 workload 소비전력, latency/performance, PCIe Slot Power Limit, NVMe/DSSD PS|idle 시 latency/performance에 영향을 주지 않고 자동으로 소비전력을 5 W 이하로 낮춰야 한다. 모든 설정에서 PCIe Slot Power Limit을 넘으면 안 된다. 이 요구 자체는 APSTA=1이나 특정 NPSS 값을 지정하지 않으며 실제 측정과 PCIe 자료가 필요하다.|관계
MN|170|11.1|SMBUS-3|DP-CFG-4에서 Basic Management 지원을 선택한 경우|DP-CFG-4 선택, SMBus §11.2 bytes 152:113, Identify MN bytes 63:24|SMBus Model Number 40 bytes는 Identify MN의 사본이어야 한다. §11.2의 p.173 표와 함께 대조한다.|명시
TNVMCAP|170|11.1|SMBUS-3|DP-CFG-4에서 Basic Management 지원을 선택한 경우|SMBus §11.2 bytes 88:85, TNVMCAP, GB 환산·표현 정밀도|SMBus Total NVM Capacity는 TNVMCAP와 같은 총 usable capacity를 GB 단위로 나타낸다. TNVMCAP는 bytes이므로 raw 정수끼리 비교하지 않는다. §11.2 p.171은 GB 정수 표현의 반올림 방식을 지정하지 않으므로 비정수 GB 경계는 추가 근거가 필요하다.|명시
NPSS|170|11.1|SMBUS-3|DP-CFG-4에서 Basic Management 지원을 선택하고 현재 power state를 확인하는 경우|FID 02h 현재 PS, 해당 PSD, SMBus §11.2 bytes 84:53|SMBus Configured NVMe Power State는 현재 설정된 PS의 PSD 32-byte 사본이며 little-endian이다. §11.2 p.171에서 정의한다. DSSD vendor Power State 구조와 NVMe PSD를 혼동하지 않는다.|명시
MN TNVMCAP NPSS|190|13|DP-CFG-4|고객의 Basic Management 설정을 확인한 경우|DP-CFG-4 항목별 A/B 선택, Basic Management interface 지원|A 설정에서는 Required, B에서는 Prohibited이다. 관련 SMBus 사본 비교는 지원하는 A 설정에 적용하고 다른 DP-CFG의 선택으로 이 항목을 추정하지 않는다.|명시
CTRATT|14|4.4.3|UUID-1,UUID-2,UUID-3,UUID-4,UUID-5,UUID-6|OCP vendor-specific Feature·Log 또는 Persistent Event의 UUID Index를 사용하는 경우|CNS 17h UUID entry, Identifier Association, Get/Set Features/Get Log UUID Index|UUID List에 C194D55BE0944794A21D29998F56BE6Fh를 big-endian으로 담고 해당 Identifier Association=00b여야 한다. 이 UUID의 index 또는 index 0과 OCP가 정의한 vendor FID/LID 조합은 OCP 기능·Log에 접근해야 한다. Get/Set Features, Get Log 및 vendor Persistent Event는 해당 UUID Index 기능을 지원해야 한다.|명시
NN MNAN|190|13|DP-CFG-2|고객의 namespace 수 설정을 확인한 경우|DP-CFG-2 항목별 A/B 선택, usable capacity|A 설정은 NSM-4의 최소 16개, B 설정은 NSM-5의 용량별 최소 개수다. 다른 DP-CFG 항목의 A/B 선택으로 namespace 수 설정을 추정하지 않는다.|명시
NN MNAN|126|4.14|SECTOR-3|공장 출하 상태|active namespace 목록, namespace 크기, 최대 capacity, NN, MNAN|공장 출하 시 최대 capacity 크기의 active namespace 1개를 구성해야 한다. 현재 active 개수=1을 지원 namespace 수 NN=1이라는 요구로 바꾸지 않는다.|명시
FR FRMW|125|4.12|FDEF-1|공장 출하 상태|모든 firmware slot의 revision 및 image, 최신 production firmware|모든 firmware slot은 최신 production firmware image를 포함해야 한다. 현재 활성 FR뿐 아니라 read-only slot을 포함한 전체 slot을 확인한다.|명시
ONCS|126|4.12|FDEF-6|공장 출하 상태이며 별도 default 예외가 없는 saveable Feature|ONCS 저장 지원, Feature별 saveable 및 saved 값, 예외 규정|saveable Feature에 saved 값이 없어야 한다. saved 값 부재와 save 기능 미지원을 구분하며 ONCS 지원 비트를 이 요구 때문에 0으로 바꾸지 않는다.|명시
ONCS|127|4.15.1|GETF-1,GETF-2,GETF-5|OCP §4.15에서 정의한 Feature를 요청하는 경우|SEL=00b/01b/10b/11b, CQE CHANG/NSSPEC/SVBL, §4.15.2 scope/saveable, 지원 여부|모든 SEL 값을 지원해야 한다. SEL=11b는 CHANG=1, NSSPEC는 Feature의 namespace scope 여부, SVBL은 Feature의 saveable 여부에 맞게 보고하며 bits 7:3=0이다. 미지원 FID는 Invalid Field in Command(02h)를 반환한다. 이 요구를 모든 NVMe FID의 저장 의무로 확장하지 않는다.|명시
LPA ENDGIDMAX CTRATT|19|4.8.1|STD-LOG-17|공통|Endurance Group Information Log 09h, group 구성, 관련 Identify 지원 보고|장치 전체에 단일 Endurance Group을 사용하고 LID 09h를 지원해야 한다. Endurance Group Event Aggregate LID 0Fh는 OCP 필수가 아니다. group 개수=1을 최대 identifier ENDGIDMAX=1로 자동 치환하지 않는다.|관계
LPA|19|4.8.1|STD-LOG-19,STD-LOG-20|Persistent Event·Telemetry·Error Log 내용을 확인하는 경우|Log 0Dh/07h/08h/01h 내용, event 순서 및 trimming|이 Log에는 user data 또는 user data로 계산한 결과가 없어야 한다. Persistent Event는 최신 event부터 보고하고 공간 부족 시 vendor가 덜 중요하다고 판단한 event부터 제거한다.|명시
LPA PELS|20|4.8.1|STD-LOG-21,STD-LOG-23|Persistent Event reporting context 또는 Log 보존을 확인하는 경우|context 유지 시간, last access, log-full 예외, purge/reset/power-loss 전후 Log|context는 host release 또는 마지막 접근 후 최소 5분까지 유지한다. Log가 차서 event 제거에 context release가 필요한 예외가 있으며 context 중 새 event를 버리면 안 된다. STD-LOG-23의 해당 Log는 purge·power loss·reset·Format·protected mode에서도 보존한다. 세부 대상과 purge 예외는 원문 목록을 함께 확인한다.|명시
'''

PSD_ROWS=r'''
165|10.2|PCM-1|지원 상태이며 해당 PS를 실제 사용한 경우|MP, MPS, workload별 전력 측정|pre-conditioned device에서 최소 15분 측정하고 sampling 간격은 2 ms 이하, 평균 window는 1초로 한다. 어떤 workload에서도 최대 평균 소비전력은 현재 PS의 Maximum Power를 넘으면 안 된다. MP는 MPS scale로 W 단위로 환산한다.
166|10.2|PCM-4|지원 상태|MP, MPS, PCM-1 방식의 최대 평균 측정값|각 PSD의 Maximum Power는 PCM-1 방식으로 측정한 maximum average power를 나타내야 한다.
166|10.3|PWR-1,PWR-4|장치의 power state 목록을 확인하는 경우|NPSS, 지원 PSD, 장치 최대 rated power envelope|NVMe 정의에 맞게 PSD 표를 채우되 장치 최대 rated power envelope보다 높은 entry는 채우면 안 된다. NPSS 밖의 미사용 entry를 지원 state로 계산하지 않는다.
166|10.3|PWR-8|두 개 이상의 지원 PS를 비교하는 경우|각 지원 PSD의 MP 및 MPS, 예외 규정|별도 예외가 없으면 둘 이상의 지원 NVMe PS에 같은 Maximum Power 값을 사용하면 안 된다. 동일 raw MP의 비교와 MPS로 환산한 실제 power 비교를 함께 기록하고 단위가 다를 때의 해석은 명시한다.
'''

def extend_ocp(data):
    pages=json.loads((ROOT/'source/ocp_pages.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'source/ocp_manifest.json').read_text(encoding='utf-8'))
    assert manifest['sha256']==hashlib.sha256((ROOT/'OCP2_6.pdf').read_bytes()).hexdigest(),'OCP PDF changed; run extract_ocp.py and review the overlay'
    data['documents']['ocp']={'filename':'OCP2_6.pdf','sha256':hashlib.sha256((ROOT/'OCP2_6.pdf').read_bytes()).hexdigest(),'title':'Datacenter NVMe SSD Specification','version':'2.6','date':'2024-09-25','pages':211}
    fields={f['id']:f for f in data['fields']};refs={};records=[]
    for f in fields.values():
        for r in f['rules']:r['standard']='nvme'
    def add(keys,page,section,ids,condition,observe,expected,interpretation='명시'):
        ids=ids.split(',');sources=[]
        for req in ids:
            pg=pages[page-1];assert re.search(r'(?m)^'+re.escape(req)+r'\b',pg['text']),f'{req} absent p{page}'
            refid='ocp:'+req
            s=dict(doc='ocp',section=section,requirement=req,pdf_page=page,page=page,figure=None,english=pg['text'])
            sources.append(s)
            if refid not in refs:
                refs[refid]=dict(id=refid,title=req+' · OCP 조건',name=req,ko='',topic='OCP 2.6',sources=[s],rules=[],edges=[],incoming=[],notes=[],external=[],kind='reference')
            statement=f'{condition}: {expected}'
            if statement not in refs[refid]['ko']:refs[refid]['ko']+=(('\n' if refs[refid]['ko'] else '')+statement)
            if req=='SMBUS-3':
                for extra in [171,173]:
                    extra_source=dict(doc='ocp',section='11.2',requirement='SMBUS-3',context_only=True,pdf_page=extra,page=extra,figure=None,english=pages[extra-1]['text'])
                    sources.append(extra_source)
                    if extra_source not in refs[refid]['sources']:refs[refid]['sources'].append(extra_source)
        for key in keys.split():
            f=fields[key];cats=['상태·적용 조건'] if interpretation=='관계' else ['필드 간 관계']
            if any(w in observe for w in ['FID','Features','命令']):cats=['Feature·명령']
            if any(w in observe for w in ['Log','event','telemetry']):cats=list(dict.fromkeys(cats+['Log·이벤트']))
            r=dict(id=f'{key}-ocp-{len(f["rules"])+1}',standard='ocp',condition=SCOPE+' / '+condition,observe=observe,expected=expected,level='SHALL'+(' · NVMe 정의로 환산/연결' if interpretation!='명시' else ''),interpretation=interpretation,profile_scope=condition,sources=sources,categories=cats,field_applicability=(f'NPSS≥{f["psd_index"]}인 지원 상태; ' if 'psd_index' in f else '')+SCOPE,related_fields=[k for k in keys.split() if k!=key],related_refs=['ocp:'+req for req in ids])
            f['rules'].append(r)
            for req in ids:
                f['edges'].append(dict(target='ocp:'+req,type='OCP 정합성 근거',text=expected))
                refs['ocp:'+req]['incoming'].append(dict(target=key,type='OCP 정합성 근거',text=expected))
            f['check_categories']=list(dict.fromkeys(f['check_categories']+cats))
        records.append(dict(fields=keys.split(),page=page,section=section,requirements=ids,condition=condition,observe=observe,expected=expected,interpretation=interpretation))
    for row in (ROWS+'\n'+EXTRA_ROWS).strip().splitlines():
        if not row.strip():continue
        keys,page,section,ids,condition,observe,expected,interpretation=row.split('|');add(keys,int(page),section,ids,condition,observe,expected,interpretation)
    for row in PSD_ROWS.strip().splitlines():
        page,section,ids,condition,observe,expected=row.split('|');add(' '.join('PSD'+str(i) for i in range(32)),int(page),section,ids,condition,observe,expected)
    data['references'].extend(refs.values())
    limitations=[
        'OCP 2.6 전체 적합성 검사표가 아니라 CNS 01h의 직접 값 및 관련 동작을 중심으로 선별한 조건이다. Identify만으로 전력·지연·purge·보안 동작을 판정하지 않는다.',
        'OCP NVMe-1은 Base 2.0e / NVM 1.0e / PCIe 1.0e 또는 이후 버전을 허용한다. 이 도구는 Base 2.1 / NVM 1.1에 연결하므로 ONCS variant 등 버전 차이를 별도로 확인한다.',
        '§13의 A/B 선택은 항목별 고객 선택이며 서로 섞을 수 있다. 프로파일·고객 면제·FIPS/TCG/SPDM 자료가 없으면 관련 조건은 미확인이다.',
        'NSM-5의 정확히 7 TiB 경계는 본문과 표의 표현이 다르다. 공급사·고객 확인 전 임의로 한쪽을 확정하지 않는다.',
        '§11.2의 SMBus 사본 비교는 DP-CFG-4의 A 설정에 적용한다. GB 정수 표현의 반올림 방식은 추가 근거가 필요하다.',
        'TP4152, IEEE 2883 purge, NVMe-MI, PCIe Slot Power Limit 및 인증/고객 문서의 전체 규정은 이 세 PDF만으로 검증하지 않는다.'
    ]
    count=sum(r.get('standard')=='ocp' for f in fields.values() for r in f['rules'])
    data['ocp_audit']=dict(scope=SCOPE,requirements=len(refs),cases=len(records),checks=count,fields=sum(any(r.get('standard')=='ocp' for r in f['rules']) for f in fields.values()),records=records,limitations=limitations)
    data['consistency_audit']['nvme_checks']=data['consistency_audit']['after_checks']
    data['consistency_audit']['after_checks']+=count
    data['notes'].append('OCP 조건은 PCIe DSSD 2.6를 적용하는 제품에만 해당하며 일반 NVMe 조건과 별도로 표시한다.')
    return data
