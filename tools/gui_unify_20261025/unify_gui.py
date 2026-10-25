"""Pure offline hub renderer for preserved, separately identified TIS views.

No I/O or numerical work on import. The sole owner verifies/copies each view and
passes its immutable metadata. Only one child document is active at a time.
"""
from __future__ import annotations
import html
import json
import re
from pathlib import PurePosixPath

SOURCE_KEYS=('human','manual','top5','sc','probe')


def _require(ok,message):
    if not ok:raise ValueError(message)


def _source(key,value):
    _require(isinstance(value,dict),'Source metadata object required')
    path=value.get('file')
    _require(isinstance(path,str)and path and not path.startswith('/')and
        str(PurePosixPath(path))==path and all(p not in ('','.','..')for p in path.split('/'))and
        all(re.fullmatch(r'[A-Za-z0-9_.-]+',p)for p in path.split('/'))and path.endswith('.html'),
        'Safe offline HTML path required')
    _require(re.fullmatch('[0-9a-f]{64}',value.get('SHA256',''))is not None,'Verified source SHA256 required')
    _require(type(value.get('bytes'))is int and value['bytes']>0,'Exact nonempty view byte count required')
    for field in ('label','model','run_id','topology','validation'):
        _require(isinstance(value.get(field),str)and value[field].strip(),'Source '+field+' required')
    for field in ('source_commit','result_commit'):
        _require(value.get(field)is None or re.fullmatch('[0-9a-f]{40}',value[field])is not None,'Immutable commit or explicit null required')
    out=dict(value,key=key)
    out.setdefault('limitations','계산·수치 검증·실험 검증 상태는 각 자료에서 따로 확인합니다.')
    return out


def navigation(sources):
    """Known anchors from the preserved documents; no data conversion."""
    rows=[]
    def add(id,label,key,anchor,detail,range_anchor=None):
        if key in sources:
            rows.append(dict(id=id,label=label,source=key,anchor=anchor,detail=detail,
                range_anchor=range_anchor,group='human'if key=='human'else'legacy'if key in('manual','top5','probe')else'sensitivity'))
    add('human-fields','사람 문헌 비교','human','metric','인간 전완·VS·전도도 평균·혼합 유전율의 명시적 대체 모델입니다. 같은 4패드 기준과 비교합니다.','limits')
    add('human-inputs','사람 자료·출처','human','material-inputs','SC와 VS의 의미, σ/ε의 서로 다른 출처와 조건, 근육 방향성 가정을 확인합니다.','limits')
    add('human-roi','사람 모델 ROI·부담','human','bars','전체 부피 ROI와 표층·비표적, 피부·접촉·층별 손실 및 서로 다른 정규화 조건을 확인합니다.','limits')
    add('top5','기존 전극 Best 5','top5','cards','기존 팬텀 가정에서 선별한 전극 배치 5종입니다. 사람 문헌 모델의 새 순위가 아닙니다.','top5-manual-ranges')
    add('top5-burden','Best 5 피부 부담','top5','burdens','기존 후보의 Jmax/J95·접촉·전력과 전압/전력/부담 비교 조건을 함께 확인합니다.','top5-manual-ranges')
    add('pair','Best 1 ↔ 2전극','manual','TIS','기존 best1과 y=0 중심의 단일 자극 전극쌍을 비교합니다. 단일 쌍에는 귀환 전극이 포함됩니다.','manual-range-controls')
    add('pair-voltage','필요 전압·손실','manual','source-ratios','목표 RMS를 맞춘 전압·전류·접촉·손실과 공간분포 차이를 확인합니다.','manual-range-controls')
    add('field-shape','전기장 형태·방향','manual','field-shape','기존 best1/C1의 실제 복소 E에서 만든 순간 벡터·화살표와 전극 배치입니다.','manual-range-controls')
    add('paper-waveforms','Carrier·변조·파형','manual','paper-figure','Carrier RMS·방향별 변조·실제 합성 파형·envelope·선 프로파일을 구분해 표시합니다.','manual-range-controls')
    if 'probe'in sources:
        add('probes','40점 전압·파형·스펙트럼','probe',sources['probe'].get('anchor',''),'기존 팬텀의 저장된 복소 전위차로 계산한 5mm 차동 프로브·깊이별 십자 위치입니다. 사람 문헌 모델의 새 측정 결과가 아닙니다.',sources['probe'].get('range_anchor','probe-ranges'))
        add('legacy-probe-proof','기존 측정 근거','manual','probes','기존 best1/C1의 측정 정의·원본 연결을 함께 확인합니다.','manual-range-controls')
    else:
        add('probes','측정 위치·Vpp','manual','probes','기존 복소 전위에 기반한 5mm 차동 팁과 깊이별 십자 위치의 예측입니다. 장비 부하 검증 상태를 확인합니다.','manual-range-controls')
    add('manual-ranges','모든 눈금 조절','manual','manual-range-controls','기존 22개 수치 그래프의 공통/개별 축·색 범위와 설정 JSON 저장·불러오기를 사용합니다.','manual-range-controls')
    add('pad-count','4·8·12·16 패드','top5','pad-count-reference','물리적 패드 수와 독립 출력·귀환 경로를 구분한 기존 strip 가족 대조입니다.','top5-manual-ranges')
    add('sc-sensitivity','SC 가정 민감도','sc','metric','이전 SC εr 민감도 결과를 사람 문헌 비교와 별도 자료로 보존합니다.','limits')
    add('human-proof','새 모델 검증 상태','human','proof','소스·설정·입력 해시와 보존 검사, SC 비교 및 전체 수렴 보류 항목을 확인합니다.','limits')
    add('legacy-proof','기존 모델 실행 근거','manual','provenance','기존 best1/C1의 실행 ID·출처·실험 검증 보류와 원시 필드 연결을 확인합니다.','manual-range-controls')
    return rows


def default_features(views):
    available={v['id']for v in views}
    proposals=[
        ('전극 Best 5와 피부 부담','top5','기존 팬텀 가정의 후보·순위와 단위/ROI를 유지합니다.'),
        ('단일 전극쌍 y=0 및 필요 Vpp/RMS 비교','pair','귀환 전극을 포함한 2전극과 목표 RMS 일치 조건을 연결합니다.'),
        ('전기장 공간 형태·방향·전극 배치','field-shape','순간 벡터와 RMS/변조를 구분합니다.'),
        ('Cell 논문을 참고한 carrier·파형·envelope·프로파일','paper-waveforms','본 연구의 원시 필드로 만든 그림이며 논문 그림을 복사하지 않습니다.'),
        ('공통 눈금과 그래프별 수동 조절','manual-ranges','고정 기본 눈금과 수동 축/색 범위를 함께 유지합니다.'),
        ('깊이별 십자 위치·5mm 차동 프로브 예측','probes','무부하/장비 미확인 상태를 보존합니다.'),
        ('주파수별 사람 문헌 입력·출처·불확실성','human-inputs','VS 대체층·전완 전이·혼합 유전율을 명시합니다.'),
        ('목표/비표적 부피 ROI와 고변조 범위','human-roi','임의의 수치 기준을 생리적 역치로 표시하지 않습니다.'),
        ('4·8·12·16 패드와 출력/귀환 구분','pad-count','패드 수를 독립 전원 출력 수로 간주하지 않습니다.'),
        ('이전 SC 민감도 및 검증 근거 보존','sc-sensitivity','새 모델과 별도 run·물성으로 확인합니다.'),
    ]
    return [dict(request=label,status='기존 검증 화면 연결'if view not in('human-inputs','human-roi')else'새 비교 모델 연결',view_id=view,detail=detail)
        for label,view,detail in proposals if view in available]


def build(sources,features=None,*,generated_utc=None):
    """Return {html, manifest}; caller owns copying, verification and publication.

    sources keys human/manual/top5/(optional)sc/probe contain file,label,model,run_id,
    topology,validation,SHA256,bytes and source_commit/result_commit (null allowed).
    Each file is an offline relative path from this hub's output directory.
    """
    _require(isinstance(sources,dict)and all(k in SOURCE_KEYS for k in sources),'Known source families required')
    _require(all(k in sources for k in ('human','manual','top5')),'Human, manual legacy and top5 views are required')
    normalized={k:_source(k,v)for k,v in sources.items()}
    views=navigation(normalized)
    features=default_features(views)if features is None else features
    ids={v['id']for v in views}
    _require(isinstance(features,list),'Feature audit list required')
    for row in features:
        _require(isinstance(row,dict)and row.get('view_id')in ids and
            all(isinstance(row.get(k),str)and row[k].strip()for k in('request','status','detail')),'Traceable feature audit row required')
    manifest=dict(schema='task1-unified-offline-gui-v1',generated_utc=generated_utc,sources=normalized,views=views,features=features,
        new_PDE=0,source_views_modified_by_hub_renderer=False,original_source_files_overwritten=False,one_active_iframe=True,
        data_separation='Human reference model, historical phantom ranking/C1/probes, and SC sensitivity retain separate material/run identities.',
        human_top5_single_pair_or_loaded_probe_new_calculation=False,
        Windows_storage_verified=False,OneDrive_sync_verified=False)
    encoded=json.dumps(manifest,ensure_ascii=False,allow_nan=False,separators=(',',':')).replace('<','\\u003c')
    return dict(html=TEMPLATE.replace('__DATA__',encoded),manifest=manifest)


TEMPLATE='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TIS 결과 · 요청 항목 통합</title>
<style>
:root{color-scheme:light;--ink:#162c42;--muted:#53687b;--line:#d8e1e9;--blue:#155f95}*{box-sizing:border-box}body{margin:0;font:14px system-ui,-apple-system,sans-serif;background:#edf2f6;color:var(--ink)}header,main{max-width:1580px;margin:auto;padding:18px}header{padding-bottom:8px}h1{font-size:24px;margin:0 0 6px}p{line-height:1.55;margin:8px 0}.note{background:#fff7dc;border:1px solid #e1d18c;border-radius:8px;padding:10px 13px}.muted,small{color:var(--muted)}nav{display:flex;flex-wrap:wrap;gap:7px;padding:12px 0}button,a.action{font:inherit;border:1px solid #aec0ce;background:white;border-radius:6px;padding:8px 11px;color:var(--ink);cursor:pointer}button[aria-pressed=true]{background:var(--blue);color:#fff;border-color:var(--blue)}button:focus-visible,a:focus-visible{outline:3px solid #d89121;outline-offset:2px}.context{background:white;border:1px solid var(--line);border-radius:8px;padding:12px 15px}.context h2{font-size:18px;margin:0 0 7px}.context-grid{display:grid;grid-template-columns:2fr 1.2fr 1.2fr;gap:12px}.label{font-size:12px;font-weight:650;color:var(--muted)}.value{overflow-wrap:anywhere}.mono{font:12px ui-monospace,monospace;overflow-wrap:anywhere}.actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}.actions a{text-decoration:none}#viewer{display:block;border:1px solid #ccd9e3;border-radius:8px;width:100%;height:calc(100vh - 210px);min-height:620px;background:white;margin-top:12px}details{background:white;border:1px solid var(--line);border-radius:8px;margin:12px 0;padding:12px 15px}summary{font-weight:650;cursor:pointer}.scroll{overflow:auto}table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:9px;border-bottom:1px solid #e1e7ec}td:nth-child(1){min-width:190px}td:nth-child(3){min-width:240px}.feature-link{white-space:nowrap;padding:5px 8px;font-size:12px}.family{display:inline-block;font-size:12px;font-weight:650;padding:3px 8px;border-radius:14px;background:#e2edf8;color:#194f78}.family[data-family=human]{background:#d9efe5;color:#215d45}.family[data-family=sensitivity]{background:#eee5f6;color:#65427c}#load-state{font-size:12px}a{color:#165f96}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto}.scope{margin:8px 0 0;color:#705a1c;font-size:12px}footer{padding:0 18px 20px;color:var(--muted);max-width:1580px;margin:auto;font-size:12px}@media(max-width:800px){header,main{padding:12px}h1{font-size:21px}.context-grid{grid-template-columns:1fr}.context-grid>div{padding:3px 0}nav{gap:5px}nav button{font-size:12px;padding:7px 8px}#viewer{height:78vh;min-height:560px}.actions{gap:6px}.actions button,.actions a{font-size:12px}}
</style>
<header><h1>TIS 결과 · 오늘 요청 항목 통합</h1><p class="muted">전극 배치, 단일 전극쌍, 전기장, 파형, 측정 예측과 새 문헌 비교 모델을 한곳에서 확인합니다.</p><p class="note">각 화면의 <b>물성·후보·run·검증 상태</b>를 함께 표시합니다. 기존 팬텀의 Best 5·best1/C1·측정 예측과 새 사람 문헌 대체 모델은 서로 다른 자료입니다. 사람 문헌 모델의 새 Best 5·단일쌍·프로브 예측은 미계산이며, 기존 프로브 예측의 장비 부하 검증도 미완료입니다.</p></header>
<main><nav id="view-tabs" aria-label="결과 항목"></nav><section class="context" aria-live="polite"><div class="family" id="family"></div><h2 id="view-title"></h2><div class="context-grid"><div><div class="label">사용 자료 / 물성</div><div class="value" id="view-model"></div></div><div><div class="label">패드 · 출력 · 귀환</div><div class="value" id="view-topology"></div></div><div><div class="label">검증 상태</div><div class="value" id="view-validation"></div></div></div><p id="view-detail"></p><div class="mono" id="view-run"></div><p class="scope" id="view-limits"></p><div class="actions"><a class="action" id="direct-open" target="_blank" rel="noopener">선택 화면을 별도 창으로 열기</a><button id="range-shortcut">선택 자료의 눈금 조절</button><button id="fullscreen">그림 화면 확대</button><span id="load-state" role="status"></span></div></section>
<iframe id="viewer" title="TIS 선택 결과" loading="eager" referrerpolicy="no-referrer"></iframe>
<details><summary>오늘 요청 항목 반영 현황</summary><p class="muted">새 계산을 만들어 넣지 않고, 실제 보존된 자료와 연결합니다. 화면별 숫자·눈금·검증 범위를 확인할 수 있습니다.</p><div class="scroll" id="feature-table"></div></details>
<details><summary>이 화면의 원본·출처·보존 상태</summary><p>각 하위 HTML의 원시 데이터와 이전 실행 식별자를 유지합니다. 한 번에 한 하위 화면만 로드합니다. Windows 저장과 OneDrive 동기화 상태는 별도 검증이 필요합니다.</p><pre id="source-proof" class="mono"></pre></details></main>
<footer>계산 완료, 수치 검증, 전체 수렴과 실험 검증은 별도 상태입니다. 변조 크기나 전기장 일치만으로 활성화·안전성을 판정하지 않습니다.</footer>
<script id="hub-data" type="application/json">__DATA__</script><script>
'use strict';
const D=JSON.parse(document.getElementById('hub-data').textContent),$=id=>document.getElementById(id),frame=$('viewer'),stateKey='task1-unified-view-v1';
let current=null,lastFile=null;
const familyLabel=key=>key==='human'?'사람 문헌 대체 모델':key==='sc'?'이전 SC 가정 민감도':'기존 팬텀 가정';
function destination(v,anchor=v.anchor){return D.sources[v.source].file+(anchor?'#'+encodeURIComponent(anchor):'')}
function select(id,anchorOverride){
 const v=D.views.find(x=>x.id===id);if(!v)return false;const s=D.sources[v.source],anchor=anchorOverride===undefined?v.anchor:anchorOverride,url=destination(v,anchor);
 current=v;$('family').textContent=familyLabel(v.source);$('family').dataset.family=v.source==='human'?'human':v.source==='sc'?'sensitivity':'legacy';$('view-title').textContent=v.label;$('view-model').textContent=s.model;$('view-topology').textContent=s.topology;$('view-validation').textContent=s.validation;$('view-detail').textContent=v.detail;$('view-run').textContent='run: '+s.run_id+' | source: '+(s.source_commit||'별도 원문 식별자 참조')+' | result: '+(s.result_commit||'별도 원문 식별자 참조');$('view-limits').textContent=s.limitations;$('direct-open').href=url;$('range-shortcut').disabled=!v.range_anchor;
 for(const b of $('view-tabs').querySelectorAll('button'))b.setAttribute('aria-pressed',String(b.dataset.view===id));
 const same=lastFile===s.file;lastFile=s.file;frame.title=v.label+' · '+s.model;$('load-state').textContent=same?'같은 자료의 선택 위치를 표시합니다.':'보존된 결과 화면을 불러오는 중…';frame.src=url;
 try{localStorage.setItem(stateKey,id)}catch(e){}
 return true;
}
for(const v of D.views){const b=document.createElement('button');b.type='button';b.textContent=v.label;b.dataset.view=v.id;b.setAttribute('aria-pressed','false');b.onclick=()=>select(v.id);$('view-tabs').append(b)}
frame.onload=()=>{$('load-state').textContent='선택한 자료를 표시했습니다. 눈금과 수치의 범위는 해당 화면에서 확인합니다.'};
frame.onerror=()=>{$('load-state').textContent='하위 HTML 파일을 찾을 수 없습니다. 배포 폴더의 파일을 함께 보존해 주세요.'};
$('range-shortcut').onclick=()=>{if(current&&current.range_anchor)select(current.id,current.range_anchor)};
$('fullscreen').onclick=async()=>{try{if(frame.requestFullscreen)await frame.requestFullscreen();else $('load-state').textContent='확대 기능은 이 브라우저에서 지원되지 않습니다. 별도 창 열기를 사용해 주세요.'}catch(e){$('load-state').textContent='별도 창 열기로 큰 화면에서 확인할 수 있습니다.'}};
const table=document.createElement('table'),thead=document.createElement('tr');for(const h of['요청 항목','반영 상태','연결 자료와 범위','열기']){const th=document.createElement('th');th.textContent=h;thead.append(th)}table.append(thead);
for(const item of D.features){const tr=document.createElement('tr');for(const key of['request','status','detail']){const td=document.createElement('td');td.textContent=item[key];tr.append(td)}const td=document.createElement('td'),b=document.createElement('button');b.type='button';b.className='feature-link';b.textContent='해당 항목';b.onclick=()=>{select(item.view_id);$('view-tabs').scrollIntoView({block:'start',behavior:'smooth'})};td.append(b);tr.append(td);table.append(tr)}$('feature-table').append(table);
$('source-proof').textContent=JSON.stringify({schema:D.schema,generated_utc:D.generated_utc,sources:D.sources,new_PDE:D.new_PDE,one_active_iframe:D.one_active_iframe,source_views_modified_by_hub_renderer:D.source_views_modified_by_hub_renderer,original_source_files_overwritten:D.original_source_files_overwritten,human_top5_single_pair_or_loaded_probe_new_calculation:D.human_top5_single_pair_or_loaded_probe_new_calculation,Windows_storage_verified:D.Windows_storage_verified,OneDrive_sync_verified:D.OneDrive_sync_verified},null,2);
let saved=null;try{saved=localStorage.getItem(stateKey)}catch(e){}select(D.views.some(v=>v.id===saved)?saved:D.views[0].id);
window.task1UnifiedGUI=Object.freeze({select,current:()=>current&&({id:current.id,source:current.source,url:frame.getAttribute('src')}),viewIds:()=>D.views.map(v=>v.id)});
</script></html>'''
