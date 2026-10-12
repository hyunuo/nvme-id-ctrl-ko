# 외부 근거 확인 항목

PCIe Transport 1.1·NVMe-MI 2.0·MI 1.2d·IEEE 구성 지침을 확보하여 일부 관련 규정을 통합했습니다. 아래 항목은 확보 사실과 내용 대조 완료를 구분하여 확인해야 합니다. 최신 상태는 source/catalog.json의 원문 및 확인 상태를 따릅니다.

## NVMe over PCIe Transport Specification

PCI Header ID/SS 레지스터 배치·읽기 방법. 두 PDF에는 값 일치 관계만 있습니다.

관련 필드: VID, SSVID

## NVM Express Management Interface Specification

FRU·VPD·관리 endpoint·MI 예약 바이트·out-of-band firmware 절차의 상세 정의.

관련 필드: FGUID, NVMSR, VWCI, MEC, RESERVED_240, MPTFAWR

## Zoned Namespace Command Set Specification

ZNS event/log 및 CSI 02h의 command set별 atomicity·명령 정의. NVM SSD를 기본으로 하며 ZNS 의미를 대신 정의하지 않습니다.

관련 필드: OAES, ONCS, AWUN, AWUPF, ACWU

## IEEE OUI / EUI-64 등록·구성 자료

실제 OUI 할당 유효성 및 조직별 식별자 할당 확인.

관련 필드: IEEE, FGUID

## 기타 I/O Command Set 규격

다른 command set의 extended LBA format·aggregate 명령 지원을 판정하는 추가 근거. Copy descriptor format 4h의 SLM source namespace 규정도 추가 확인이 필요합니다.

관련 필드: CTRATT, ONCS, CDFS

## 원문 불일치·정의 공백

- ANACAP: 원문 불일치: RANAOS 이름·§8.1.1.4 참조는 Optimized지만 bit 0 설명은 Inaccessible입니다. 확정 정합성 판정에서 제외하고 원문/정오표를 확인하세요.
- KPIOC: 원문 참조 번호 불일치: Figure 312는 §8.1.11을 가리키지만 해당 절은 Host-Initiated Refresh입니다. Key Per I/O 절은 §8.1.13이며 두 참조를 모두 보존했습니다.
- FUSES: 원문 정의 공백: 필드 크기는 16비트(523:522)인데 Figure 312의 비트 표는 7:1 Reserved, 0 FCWS만 제공합니다. 15:8은 이 표에서 명시되지 않아 임의로 Reserved 정의를 추가하지 않았습니다.
- AWUPF: 원문 문구 차이: Figure 117(p.91)은 실패 후 이전 성공 write 데이터를 반환한다고 적지만 §2.1.4.3(p.16)은 interrupted write에 all-old 또는 all-new를 허용합니다. 실패/중단 조건을 구분하며 이 자료만으로 문구 충돌을 확정 해소하지 않습니다.
- CMMRTD: Figure 312 일부 문구는 Track Memory Ranges, Figure 469의 제목은 Track Memory Changes입니다. Figure 469와 §5.1.27.1.2의 실제 요청 구조를 기준으로 확인합니다.
- NMMRTD: Figure 312 일부 문구는 Track Memory Ranges, Figure 469의 제목은 Track Memory Changes입니다. Figure 469와 §5.1.27.1.2의 실제 요청 구조를 기준으로 확인합니다.
- MINMRTG: Figure 312 일부 문구는 Track Memory Ranges, Figure 469의 제목은 Track Memory Changes입니다. Figure 469와 §5.1.27.1.2의 실제 요청 구조를 기준으로 확인합니다.
- MAXMRTG: Figure 312 일부 문구는 Track Memory Ranges, Figure 469의 제목은 Track Memory Changes입니다. Figure 469와 §5.1.27.1.2의 실제 요청 구조를 기준으로 확인합니다.
- SUBNQN: 원문 적용 조건 불일치: Figure 312의 SUBNQN 행은 Discovery 열을 R로 표시하지만, 같은 행 본문에는 Discovery controller의 NQN 보고 요구가 있습니다. Discovery에 대해서는 표와 본문을 임의로 하나로 확정하지 않고 Transport 규정 또는 정오표를 추가 확인합니다.
