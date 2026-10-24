"""Pure metadata wrapper: actual centred-y0 C1 versus unchanged f35 TIS.

The frozen packed dashboard supplies the active SCRIPT/CSP and all maps. This
wrapper adds only fixed, source-provided comparison tables/proof text. No native
read, solve, ledger, Git operation or result file write occurs here.
"""
from __future__ import annotations
import html
import importlib.util
import json
import math
from pathlib import Path

BASE_SOURCE = Path('/workspace/ngg-tis-task1/tools/task1_best1_pair_dashboard.py')
_spec = importlib.util.spec_from_file_location('centered_frozen_pair_dashboard', BASE_SOURCE)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
NEW_ID = 'centered-square15-C1-y0-xy80-f3000'
OLD_ID = 'baseline-square15-C1pair0-xy80'
MATCH = 'ROI_energy_RMS'
MODE = 'skin_contact_only'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def near(actual, expected):
    return isinstance(actual, (list, tuple)) and len(actual) == len(expected) and all(
        finite(a) and abs(a-b) <= 1e-8 for a, b in zip(actual, expected))


def node(value):
    return 'out0' if value in (0, 'out0') else 'out1' if value in (1, 'out1') else 'GND'


def validate(payload):
    base.validate(payload)
    a, s = payload['analysis'], payload['spatial']
    pair = a['single_pair'];circuit = pair['circuit']
    require(pair.get('case_id') == NEW_ID and a.get('new_PDE') == 1 and a.get('new_native_RHS') == 1,
            'Completed actual centred-y0 one-condition/one-RHS result required, not an old result alias')
    require(a.get('status') == 'calculated_unadopted' and a.get('full_convergence_validated') is False and
            a.get('candidate_adopted') is False, 'Calculated diagnostics must retain convergence/adoption holds')
    require(circuit.get('n_pads') == 2 and circuit.get('n_outputs') == 1 and circuit.get('n_return_nodes') == 1 and
            circuit.get('source_resistance_ohm') == 50, 'True one-output, one-return, two-pad 50ohm case required')
    require(pair.get('frequency_Hz') == 3000, 'Actual single3000Hz source required')
    require(isinstance(pair.get('physical_pad_centres_mm'), list) and len(pair['physical_pad_centres_mm']) == 2 and
            all(near(x, y) for x, y in zip(pair['physical_pad_centres_mm'], [[-10, 0], [10, 0]])),
            'Analysis must identify the actual new centred pad centres')
    pads = {p['pad']: p for p in s['C1']['pad_centres']}
    outlines = {p['pad']: p for p in s['C1']['physical_outlines']}
    for pad, x in ((0, -10), (1, 10)):
        p = pads[pad]
        require(near([p['x_mm'], p['y_mm']], [x, 0]) and node(p['node']) == ('out0' if pad == 0 else 'GND') and
                finite(p['area_mm2']) and abs(p['area_mm2']-225) < 1e-8,
                'Display must retain genuine source/return identities at(-10,0)/(10,0),225mm2 each')
        poly = outlines[pad]['polygon_mm']
        if len(poly) == 5 and near(poly[0], poly[-1]):
            poly = poly[:-1]
        expected = [[x-7.5, -7.5], [x+7.5, -7.5], [x+7.5, 7.5], [x-7.5, 7.5]]
        require(len(poly) == 4 and all(any(near(q, corner) for q in poly) for corner in expected),
                'Exact new15x15mm square outlines required; never relabel oldy-minus10 geometry')
    old = payload.get('offcenter_comparison', {})
    require(isinstance(old.get('schema'), str) and old.get('old_case_id') == OLD_ID and old.get('new_case_id') == NEW_ID,
            'Explicit preserved old/new C1 source identities required')
    require(all(near(x, y) for x, y in zip(old.get('old_centres_mm', []), [[-10, -10], [10, -10]])) and
            len(old.get('old_centres_mm', [])) == 2 and all(near(x, y) for x, y in zip(old.get('new_centres_mm', []), [[-10, 0], [10, 0]])) and
            len(old.get('new_centres_mm', [])) == 2, 'Oldy-minus10 control and newy0 cannot be conflated')
    fixed = old.get('modes', {}).get(MODE, {}).get(MATCH, {})
    for key in ('old', 'new'):
        row = fixed.get(key, {})
        require(all(finite(row.get(k)) for k in ('required_source_Vpp', 'source_current_RMS_mA')) and
                all(finite(row.get('burdens', {}).get(k)) for k in base.BURDENS), 'Stored fixedskin8ROI old/new values required')
    changes = fixed.get('relative_change', {})
    require(all(finite(changes.get(k)) for k in ('required_source_Vpp', 'source_current_RMS_mA')) and
            all(finite(changes.get('burdens', {}).get(k)) for k in base.BURDENS), 'Stored signed new/old fractional changes required')
    return payload


def esc(value):
    return html.escape(str(value), quote=True)


def fmt(value):
    return format(value, '.12g') if finite(value) else '미제공'


def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(v)+'</th>' for v in headers)+\
        '</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def previous_link(payload):
    previous = payload.get('provenance', {}).get('previous_GUI', {})
    if not isinstance(previous, dict) or not isinstance(previous.get('href'), str):
        return '<p class="muted">과거y=−10 GUI 링크는 이payload에 미제공입니다. 원본 case ID와 고정대조 수치는 그대로 보존합니다.</p>'
    href = previous['href']
    require(href.startswith(('https://github.com/', 'http://localhost/', 'http://127.0.0.1/')) or
            (not ':' in href and not any(ord(c) < 32 for c in href)), 'Only explicit source GUI links allowed')
    return '<p class="muted"><a href="'+esc(href)+'">보존된 이전 y=−10 GUI · 원본 다운로드</a> · source commit <code>'+\
        esc(previous.get('commit', '미제공'))+'</code> · index SHA256 <code>'+esc(previous.get('SHA256', '미제공'))+'</code></p>'


def fixed_panel(payload):
    fixed = payload['offcenter_comparison']['modes'][MODE][MATCH]
    old, new, change = (fixed[k] for k in ('old', 'new', 'relative_change'))
    rows = []
    for label, key in (('50Ω 앞 source Vpp [V]', 'required_source_Vpp'), ('단일 출력 RMS 전류 [mA]', 'source_current_RMS_mA')):
        rows.append([label, fmt(old[key]), fmt(new[key]), fmt(change[key]*100)+' %'])
    labels = {'surface_J_RMS_max_A_m2': '접촉 normal J 최대 [A/m²]',
              'surface_J_RMS_p95_A_m2': '접촉 normal J P95 [A/m²]',
              'contact_voltage_RMS_max_V': '접촉 전압 최대 RMS [V]',
              'bulk_skin_J_vector_RMS_max_A_m2': 'SC+dermis 벡터 J 최대 [A/m²]',
              'bulk_skin_J_vector_RMS_p95_A_m2': 'SC+dermis 벡터 J P95 [A/m²]',
              'SC_power_W': 'SC 손실 [W]', 'contact_power_W': '접촉 계면 손실 [W]',
              'skin_SC_plus_dermis_power_W': 'SC+dermis 손실 [W]', 'source_power_W': '총 source 전력 [W]'}
    for key, label in labels.items():
        rows.append([label, fmt(old['burdens'][key]), fmt(new['burdens'][key]), fmt(change['burdens'][key]*100)+' %'])
    return '<section id="offcenter-fixed-comparison"><h2 class="section">고정 대조: 기존 y=−10 vs 신규 y=0 단일 전극쌍</h2>'+\
        '<p class="note">이 표는 <b>skin8 TIS 기준 + ROI 에너지 RMS 매칭</b>에 고정되며 위 선택을 바꿔도 변하지 않습니다. '+\
        '동일한 f35 목표에 각각 필요한 C1 source 진폭을 비교합니다. 감소·증가율은 원본에 저장된 signed relative_change를 그대로 단위 변환한 값이며 새로 재계산하지 않습니다.</p>'+\
        table(['비교 지표', '기존 source(−10,−10) / return(+10,−10)', '신규 source(−10,0) / return(+10,0)', '저장된 변화율 (new/old−1)'], rows)+\
        '<p class="muted">두 C1 모두 정방형225mm²×2=450mm²/독립1출력/귀환1개/50Ω입니다. y 위치를 실제로 바꾼 신규 native PDE이며 과거 결과의 좌표 라벨만 바꾼 것이 아닙니다. '+\
        'TIS는 기존4개 모서리 완화형/900mm²의 동일 구동·진폭을 재사용합니다. RMS 일치는 형상·전류·표면 부담·생리적 효과의 동등성이 아닙니다.</p>'+previous_link(payload)+'</section>'


def hotspots_panel(payload):
    proofs = payload['spatial'].get('proofs', {})
    rows = []
    for name, key, unit in (('신규 C1 전체 RMS 전역 최대', 'raw_RMS_global_max', 'V/m'),
                            ('신규 C1 접촉 normal J 최대', 'contact_Jmax', 'A/m²'),
                            ('신규 C1 SC+dermis 벡터 J 최대', 'bulk_skin_Jmax', 'A/m²')):
        item = proofs.get(key, {})
        item = item.get('C1', {}) if isinstance(item, dict) else {}
        rows.append([name, fmt(item.get('value_V_m', item.get('value_A_m2')))+' '+unit,
                     json.dumps(item['center_xyz_mm'], ensure_ascii=False) if item.get('center_xyz_mm') is not None else '미제공',
                     item.get('layer', '접촉면 영수증 참조' if key == 'contact_Jmax' else '미제공')])
    return '<section id="centered-raw-hotspots"><h2 class="section">새 C1의 전역 최대 위치 · raw1Vpp 고정 영수증</h2>'+\
        table(['원본 raw 지표 (정규화 선택과 독립)', '값', 'native 중심 xyz [mm]', '층'], rows)+\
        '<p class="muted">각 위치와 값은 신규 실제 계산의 Float64 proof입니다. 위 skin8/매칭 진폭과 별도로 raw1Vpp를 고정해 표시합니다. '+\
        'SC 또는 표면 층 경계의 높은 전기장을 깊이15–20mm 집중으로 해석하지 않습니다. 좌표 미제공 항목을0 또는 통과로 만들지 않습니다.</p></section>'


def replace_once(text, old, new):
    require(text.count(old) == 1, 'Frozen static dashboard anchor changed; review instead of silently patching')
    return text.replace(old, new, 1)


def render(payload: dict) -> str:
    """Return centred-y0 HTML; active frozen JavaScript/CSP stay byte-identical."""
    validate(payload)
    result = base.render(payload)
    # Static prose only. The packed payload and active SCRIPT are left intact.
    result = replace_once(result, '<title>현재 best1 vs 단일 전극쌍 · 작업1</title>', '<title>현재 best1 vs 중앙y=0 단일 전극쌍 · 작업1</title>')
    result = replace_once(result, 'TASK 1 · EXISTING NATIVE RESPONSE · RMS MATCH', 'TASK 1 · NEW CENTERED C1 NATIVE RESPONSE · RMS MATCH')
    result = replace_once(result, '<h1>현재 best1과 단일 전극쌍을 같은 RMS에서 비교</h1>', '<h1>현재 best1과 중앙 y=0 단일 전극쌍 비교</h1>')
    result = replace_once(result, '<h2>단일 전극쌍 · 3 kHz sine</h2>', '<h2>중앙 y=0 단일 전극쌍 · 3 kHz sine</h2>')
    result = replace_once(result, '15×15 mm 정방형 source와 귀환 전극을 포함한 실제 전극쌍. TIS와 전극 형상이 다릅니다.',
                          '실제 신규 source(−10,0) / return(+10,0) · 15×15mm 정방형2개. 중앙 y=0이며 TIS와 전극 형상·면적이 다릅니다.')
    result = replace_once(result, '<div class="notice"><b>전극 형상과 접촉면적이 다른 대조입니다.</b>',
                          '<div class="notice"><b>중앙 y=0 C1 · 실제 신규1조건/3000Hz1주파수/1출력/1RHS를 계산한 결과입니다.</b> 기존 TIS 응답은 재사용했습니다. <b>전극 형상과 접촉면적이 다른 대조입니다.</b>')
    result = replace_once(result, '신규 PDE는 수행하지 않습니다.', '신규 중앙 C1 native PDE1조건·1RHS가 실제 완료됐습니다. 기존 TIS 및 과거 y=−10 C1은 재계산하지 않았으며 전체 수렴·실험·채택은 미검증입니다.')
    anchor = '<h2 class="section">실제 source Vpp는 각 출력과 비교</h2>'
    result = replace_once(result, anchor, fixed_panel(payload)+hotspots_panel(payload)+anchor)
    require('<script>'+base.SCRIPT+'</script>' in result, 'Active frozen SCRIPT changed unexpectedly')
    return result
