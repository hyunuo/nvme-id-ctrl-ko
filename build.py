"""Validate the curated spec data and generate one self-contained HTML (stdlib only).

Usage: python build.py [--refresh-content]
"""
import argparse,json,re,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'

def bit_indices(r):
    parts=list(map(int,r.split(':')));return set(range(parts[-1],parts[0]+1))

def validate(d):
    allnodes=d['fields']+d['references'];nodes={n['id']:n for n in allnodes}
    assert len(nodes)==len(allnodes),'Duplicate ids'
    bytes_seen={};gaps={};bit_count=0
    for f in d['fields']:
        assert f['title'] and re.search('[가-힣]',f['ko']),f['id']
        assert f['unit'] and f['encoding'] and f['sources'],f['id']
        for offset in range(f['start'],f['end']+1):
            assert offset not in bytes_seen,f'Duplicate byte {offset}'
            bytes_seen[offset]=f['id']
        bits=set()
        for b in f['bits']:
            value=bit_indices(b['range']);assert not bits&value,f'Duplicate bit {f["id"]}:{b["range"]}'
            assert max(value)<(f['end']-f['start']+1)*8,f['id']
            assert re.search('[가-힣]',b['ko']),f['id']
            bits|=value;bit_count+=1
        if bits:
            missing=set(range((f['end']-f['start']+1)*8))-bits
            if missing:gaps[f['id']]=sorted(missing)
    assert set(bytes_seen)==set(range(4096)),'Byte layout not contiguous'
    assert gaps=={'FUSES':list(range(8,16))},f'Unexpected source bit definition gap: {gaps}'
    psdbits=set()
    for b in d['psd']:
        ix=bit_indices(b['range']);assert not psdbits&ix,b['range'];psdbits|=ix
        assert re.search('[가-힣]',b['ko']),b['id']
    assert psdbits==set(range(256)),'PSD layout not contiguous'
    psds=[n for n in d['fields'] if 'psd_index' in n]
    assert len(psds)==32 and all(n['start']==2048+32*n['psd_index'] for n in psds)
    rule_count=0;edge_count=0
    for n in allnodes:
        for e in n['edges']:
            assert e['target'] in nodes,f'Broken edge {n["id"]} -> {e["target"]}'
            assert any(x['target']==n['id'] and x['type']==e['type'] for x in nodes[e['target']]['incoming']),'Missing reverse edge'
            edge_count+=1
        for rule in n['rules']:
            assert all(rule.get(k) for k in ['condition','observe','expected','level','sources']),n['id']
            rule_count+=1
            if 'consistency_audit' in d and n in d['fields']:
                assert rule.get('id') and rule.get('categories'),n['id']
                assert all(c in d['consistency_audit']['categories'] for c in rule['categories'])
        for s in n['sources']+[s for r in n['rules'] for s in r['sources']]:
            assert s['doc'] in d['documents'] and s['section'] and s['pdf_page']>0,n['id']
            assert s['page']==s['pdf_page']-(22 if s['doc']=='base' else 0),n['id']
    # Version-pinned files must agree with the stored hashes if present.
    for doc in d['documents'].values():
        p=ROOT/doc['filename']
        if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==doc['sha256'],'Source PDF changed; re-extract and review'
    assert all(k in nodes for k in ['ONCS','VS','PLSI','CRCAP','MPTFAWR','TRATTR','CDFS','PSD31'])
    if 'consistency_audit' in d:
        assert d['consistency_audit']['field_count']==len(d['fields'])
        assert all(f.get('overview_status') and 'check_categories' in f for f in d['fields'])
        assert all(f['rules'] or f['id']=='VS' or f['overview_status'] in ['별도 조건 없음','등록된 조건 없음'] for f in d['fields']),'Unreviewed field'
        assert not any(r['condition']=='필드 값을 해석할 때' for f in d['fields'] for r in f['rules']),'Decoding guidance counted as consistency check'
        assert d['consistency_audit']['after_checks']==sum(len(f['rules']) for f in d['fields'])
    if 'ocp_audit' in d:
        ocp_rules=[r for f in d['fields'] for r in f['rules'] if r.get('standard')=='ocp']
        assert len(ocp_rules)==d['ocp_audit']['checks']
        for r in ocp_rules:
            assert r['profile_scope'] and r['interpretation'] and 'OCP' in r['field_applicability']
            assert all(s['doc']=='ocp' and s.get('requirement') for s in r['sources'])
        assert len({(f['id'],r['id']) for f in d['fields'] for r in f['rules']})==sum(len(f['rules']) for f in d['fields'])
    if 'editorial_audit' in d:
        assert len(d['editorial_audit']['fields'])==len(d['fields'])
        assert not any(r['condition'].startswith('비트 ') for f in d['fields'] for r in f['rules']),'Copied bit definition is not a check'
        assert all(r.get('check_kind') for f in d['fields'] for r in f['rules'])
    return dict(byte_ranges=len(d['fields']),bytes_covered=len(bytes_seen),field_bit_ranges=bit_count,
                psd_bit_ranges=len(d['psd']),psd_bits_covered=len(psdbits),power_states=len(psds),
                related_clauses=len(d['references']),relations=edge_count,manual_checks=rule_count,
                source_definition_gaps=gaps,status='passed_with_documented_source_gap')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refresh-content',action='store_true');args=parser.parse_args()
    if (ROOT/'source/catalog.json').exists():
        from catalog import compile_catalog
        d=compile_catalog()
    elif args.refresh_content:
        from reference_content import assemble
        d=assemble();(ROOT/'content.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    else:d=json.loads((ROOT/'content.json').read_text(encoding='utf-8'))
    report=validate(d)
    (ROOT/'content.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    template=(ROOT/'template.html').read_text(encoding='utf-8')
    assert '__DATA__' in template and not re.search('[\u3040-\u30ff]',template),'Unexpected template language'
    data=json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    html=template.replace('__DATA__',data)
    html=html.replace('__APP__',(ROOT/'app.js').read_text(encoding='utf-8'))
    assert '<script src=' not in html and '<link ' not in html
    OUT.mkdir(exist_ok=True)
    (OUT/'id_ctrl_ko.html').write_text(html,encoding='utf-8')
    guide=ROOT/'source/user_guide.html'
    if guide.exists():(OUT/'user_guide.html').write_text(guide.read_text(encoding='utf-8'),encoding='utf-8')
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if 'coverage_summary' in d:
        coverage=dict(summary=d['coverage_summary'],fields=d['coverage'],footnotes=d['footnote_excerpt_ids'],
                      unresolved=[dict(id=e['id'],owner=e['owner'],reason=e['reason']) for e in d['excerpts'] if e['status']!='원문 대조 완료'])
        (OUT/'source_coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8')
        stages=OUT/'stages';stages.mkdir(exist_ok=True)
        stage_data=[dict(stage=1,title='원문 대응과 검토 상태',technical_status='passed',coverage=d['coverage_summary'],content_review='등록과 대조 완료를 분리하며 미대조 항목은 보류 상태로 유지',external=d['external_acquisition']),
                    dict(stage=2,title='필드 탭과 직접 관계',technical_status='implemented',tabs=['description','related','checks'],compatibility='기존 필드 hash 유지',validation='enhancement_validation.json'),
                    dict(stage=3,title='작업별 체크리스트',technical_status='implemented',workflows=[dict(id=w['id'],conditions=len(w['condition_ids'])) for w in d['workflows']],exports=['CSV','browser print']),
                    dict(stage=4,title='제품별 수동 검토',technical_status='implemented',project_schema=1,catalog_revision=d['catalog_revision'],storage='사용자가 내보내는 JSON',validation='enhancement_validation.json')]
        for stage in stage_data:(stages/f"stage{stage['stage']}.json").write_text(json.dumps(stage,ensure_ascii=False,indent=2),encoding='utf-8')
        for index,entry in enumerate(['coverage','VWC','workflows','project'],1):
            snapshot=html.replace("../${encodeURIComponent(D.documents[s.doc].filename)}", "../../${encodeURIComponent(D.documents[s.doc].filename)}")
            snapshot=snapshot.replace('href="user_guide.html"','href="../user_guide.html"')
            snapshot=snapshot.replace("display();\n</script>",f"if(!location.hash)history.replaceState(null,'','#{entry}');display();\n</script>")
            (stages/f'stage{index}.html').write_text(snapshot,encoding='utf-8')
        handoff=['# 단계별 인계 기록','','최종 파일: output/id_ctrl_ko.html','','편집 원본: source/catalog.json. Python 과거 편집 모듈은 이관 기록이며 현재 빌더의 원본이 아닙니다.','',
                 '## 1단계','',f"전체 {len(d['coverage'])}개 범위 대응 등록. 고유 조건 {len(d['conditions'])}개. 원문 대조 완료 필드 {d['coverage_summary']['confirmed']}개.",
                 '남은 의미 대조·예외 확인은 상태로 표시합니다. 등록 완료를 내용 확인 완료라고 표시하지 않습니다.','',
                 '## 2단계','','세 탭·직접 관계도/표·역방향 탐색·조건 링크·공통 적용 설정을 제공합니다.','',
                 '## 3단계','','여섯 작업 화면은 고정 조건 ID를 참조합니다. 자료 목록·순서·조건·미확인 사항·CSV/인쇄·단위 예제를 제공합니다.','',
                 '## 4단계','','JSON 프로젝트, 관측 대상과 시점, 파일명·메모, 결과·검토자, 변경 이력, revision 재확인 및 삭제 조건 보존을 제공합니다.','',
                 '## 검증','','test_catalog.py: 고정 ID/순서 변경/의무 수준 변경/원문 누락/PSD 독립 대상 검사.','enhancement_qa.cjs: 오프라인 전체 화면·직접 링크·6개 작업·잘못된 JSON·저장/복원·이력·개정/삭제·CSV·모바일 검사.','',
                 '## 재생성','','python build.py','',
                 '## 남은 외부 근거','','IEEE OUI CSV 서버는 HTTP 418로 거절했습니다. source/external_manifest.json에 시도 결과를 기록했습니다. 미조회 값을 미할당으로 판정하지 않습니다.',
                 '다른 Command Set·보안 인증·고객 자료와 원문 불일치는 후속 확인 목록에 남습니다.']
        (OUT/'implementation_handoff.md').write_text('\n'.join(handoff)+'\n',encoding='utf-8')
    ext=['# 외부 근거 확인 항목','', 'PCIe Transport 1.1·NVMe-MI 2.0·MI 1.2d·IEEE 구성 지침을 확보하여 일부 관련 규정을 통합했습니다. 아래 항목은 확보 사실과 내용 대조 완료를 구분하여 확인해야 합니다. 최신 상태는 source/catalog.json의 원문 및 확인 상태를 따릅니다.','']
    for e in d['external']:ext.extend(['## '+e['title'],'',e['needed'],'','관련 필드: '+', '.join(e['fields']),''])
    ext.extend(['## 원문 불일치·정의 공백',''])
    for f in d['fields']:
        for note in f['notes']:ext.extend(['- '+f['id']+': '+note])
    (OUT/'source_notes.md').write_text('\n'.join(ext)+'\n',encoding='utf-8')
    if 'ocp_audit' in d:
        a=d['ocp_audit']
        (OUT/'ocp_audit.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
        lines=['# OCP DSSD 2.6 — CNS 01h 정합성 조건','',a['scope'],'',
               f"Requirement ID {a['requirements']}개 / 적용 조건별 항목 {a['cases']}개 / 연결 필드·PSD {a['fields']}개 / 반복 포함 조건 {a['checks']}개",'',
               '## 적용 범위·미확인 항목','']+['- '+t for t in a['limitations']]+['','## 조건 목록','']
        for r in a['records']:
            lines.extend([f"### {', '.join(r['fields'])} — {', '.join(r['requirements'])}",'',
                          '적용: '+r['condition'],'','관측: '+r['observe'],'',r['expected'],'',
                          f"근거: OCP 2.6 §{r['section']} · 인쇄/PDF p.{r['page']} · {r['interpretation']}",''])
        (OUT/'ocp_audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if 'editorial_audit' in d:
        a=d['editorial_audit']
        (OUT/'editorial_audit.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
        lines=['# 전체 필드 편집·정합성 조건 재검토','',a['scope'],'',
               f"정의/해석으로 분리: {len(a['removed'])}개; 구체적 조건으로 다시 작성: {len(a['added'])}개; 요구 관계 수정: {len(a['rewritten'])}개",'',
               '## 필드별 결과','','| 필드 | 남긴 조건 수 | 해석 안내 수 | 구분 |','|---|---:|---:|---|']
        lines += [f"| {f['id']} | {f['checks']} | {f['guidance']} | {f['status']} |" for f in a['fields']]
        lines+=['','## 요구 관계 수정','']
        for r in a['rewritten']:lines += [f"- {r['field']}: {r['before']} → {r['after']}"]
        lines+=['','## 구체적 조건으로 작성','']
        for r in a['added']:lines += [f"- {r['field']}: {r['condition']} / {r['observe']} → {r['expected']}"]
        lines+=['','## 정합성 목록에서 분리한 항목','']
        for r in a['removed']:lines += [f"- {r['field']} / {r['condition']}: {r['reason']}"]
        lines+=['','## 범위와 한계','']+a['limitations']
        (OUT/'editorial_audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if 'consistency_audit' in d:
        audit=d['consistency_audit']
        (OUT/'consistency_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
        summary=['# 정합성 조건 재검토 기록','',audit['scope'],'',
                 f"NVMe 조건 수: {audit['before_checks']} → {audit.get('nvme_checks',audit['after_checks'])}; OCP 포함 전체: {audit['after_checks']} (반복 PSD·형식·예약값 조건 포함)",
                 f"전체 {audit['field_count']}개 범위 중 {audit['fields_with_checks']}개에 조건을 정리했습니다. VS는 Vendor 문서가 필요합니다.",'',
                 '## 추가한 항목','']
        for a in audit['additions']:
            summary.extend([f"- **{a['field']} / {a['category']}**: {a['condition']} → {a['expected']}"])
        summary.extend(['','## 검토 한계','']+['- '+v for v in audit['limitations']])
        (OUT/'consistency_audit.md').write_text('\n'.join(summary)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    print('Created output/id_ctrl_ko.html')

if __name__=='__main__':main()
