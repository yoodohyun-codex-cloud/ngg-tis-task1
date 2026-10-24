"""Pure, count-checked patches for the two preserved pre-paper GUI scripts.

No I/O, data decode, calculation, browser, lock or publication occurs on import.
The caller injects window.task1FixedScaleContract before all executable scripts,
owns all data/manifest verification, and recomputes the changed CSP hashes.
"""
from __future__ import annotations


def once(text: str, before: str, after: str) -> str:
    count = text.count(before)
    if count != 1:
        raise ValueError(f'Expected one reviewed legacy anchor, found {count}: {before[:100]}')
    return text.replace(before, after, 1)


def counted(text: str, before: str, after: str, count: int) -> str:
    actual = text.count(before)
    if actual != count:
        raise ValueError(f'Expected {count} reviewed legacy anchors, found {actual}: {before[:100]}')
    return text.replace(before, after)


def _prefix(script: str, current: bool) -> str:
    declarations = "\nconst TASK1_LOCKED_E=window.task1FixedScaleContract.electric_field.upper_V_m;\n"
    declarations += "if(!(Number.isFinite(TASK1_LOCKED_E)&&TASK1_LOCKED_E>0))throw Error('Fixed electric-field scale contract required');\n"
    if current:
        declarations += "const TASK1_LOCKED_J=window.task1FixedScaleContract.current_density.upper_A_m2;\n"
        declarations += "if(!(Number.isFinite(TASK1_LOCKED_J)&&TASK1_LOCKED_J>0))throw Error('Fixed contact-current scale contract required');\n"
    return once(script, "'use strict';", "'use strict';" + declarations)


def patch_original(script: str) -> str:
    """Lock original RMS/J maps across every existing mode/match/plane/depth."""
    script = _prefix(script, current=True)
    script = once(script,
        "fill('range',{global:'전체 native volume 공통 범위',primary_ROI:'목표 ROI 공통 범위 · 표시 clipping'},'primary_ROI');",
        "fill('range',{global:'모든 조건 고정 범위 · 자동 조정 없음'},'global');$('range').disabled=true;")
    script = once(script,
        "region=$('range').value==='global'?'total':primary,fmax=Math.max(...['TIS','C1'].map(k=>S.regions[k][region].max*scales[k])),jmax=Math.max(mode.reference_burdens.surface_J_RMS_max_A_m2,match.burdens.surface_J_RMS_max_A_m2)",
        "region='total',fmax=TASK1_LOCKED_E,jmax=TASK1_LOCKED_J")
    script = once(script,
        "$('field-legend').textContent=`E RMS 공통 0–${F(fmax)} V/m · ${region==='total'?'전체 native volume 범위':'목표 ROI 표시 범위: 초과값 clipping'}`;",
        "$('field-legend').textContent=`E RMS 고정 0–${F(fmax)} V/m · 모든 지원 조건에서 동일 / 자동 조정 없음`;" )
    script = once(script,
        "$('contact-legend').textContent=`접촉 normal J RMS 공통 0–${F(jmax)} A/m²`;",
        "$('contact-legend').textContent=`접촉 normal J RMS 고정 0–${F(jmax)} A/m² · 모든 지원 조건에서 동일`;" )
    script = counted(script, "canvas.dataset.vmax=String(max);",
        "canvas.dataset.vmin='0';canvas.dataset.vmax=String(max);canvas.dataset.scaleMode='fixed_all_conditions';canvas.dataset.axisOrientation=f.down?'depth_down':'y_up';", 2)
    return script


def patch_vectors(script: str) -> str:
    """Lock instantaneous magnitude and arrow denominator, including XY orientation."""
    script = _prefix(script, current=False)
    script = once(script,
        "max=Math.max(views.TIS.max,views.C1.max);cache.views=views;",
        "max=TASK1_LOCKED_E;cache.views=views;")
    script = once(script,
        "const xp=u=>pad.l+(u-umin)/(umax-umin)*width,yp=v=>pad.t+(v-vmin)/(vmax-vmin)*height;",
        "const down=p.kind!=='XY',xp=u=>pad.l+(u-umin)/(umax-umin)*width,yp=v=>pad.t+(down?(v-vmin):(vmax-v))/(vmax-vmin)*height;"
        "el.dataset.vmin='0';el.dataset.vmax=String(max);el.dataset.scaleMode='fixed_all_conditions';el.dataset.axisOrientation=down?'depth_down':'y_up';")
    script = once(script,
        "g.fillRect(xp(ue[i]),yp(ve[j]),Math.max(.3,xp(ue[i+1])-xp(ue[i])+.2),Math.max(.3,yp(ve[j+1])-yp(ve[j])+.2));",
        "g.fillRect(xp(ue[i]),Math.min(yp(ve[j]),yp(ve[j+1])),Math.max(.3,xp(ue[i+1])-xp(ue[i])+.2),Math.max(.3,Math.abs(yp(ve[j+1])-yp(ve[j]))+.2));")
    script = once(script,
        "let dx=a/(umax-umin)*width,dy=b/(vmax-vmin)*height,l=Math.hypot(dx,dy);",
        "let dx=a/(umax-umin)*width,dy=(p.kind==='XY'?-b:b)/(vmax-vmin)*height,l=Math.hypot(dx,dy);")
    script = once(script,
        "cache.transform[c]={xp,yp,umin,umax,vmin,vmax,pad,width,height,arrows};",
        "cache.transform[c]={xp,yp,umin,umax,vmin,vmax,pad,width,height,arrows,down};")
    script = once(script,
        "v=tr.vmin+(event.clientY-rect.top-tr.pad.t)/tr.height*(tr.vmax-tr.vmin);",
        "v=tr.down?tr.vmin+(event.clientY-rect.top-tr.pad.t)/tr.height*(tr.vmax-tr.vmin):tr.vmax-(event.clientY-rect.top-tr.pad.t)/tr.height*(tr.vmax-tr.vmin);")
    script = once(script,
        " V/m · 현재 두 단면의 실제 순간 |E(t)| 최대 · 상한 clipping 없음'",
        " V/m · 전체 지원 조건 고정 상한 / 시간·단면·구동 변경에도 동일'")
    script = once(script,
        "must(Number.isFinite(cache.scale)&&cache.scale===expectedMax,'Shared unclipped maximum is not actual two-case maximum');",
        "must(Number.isFinite(cache.scale)&&cache.scale===TASK1_LOCKED_E,'Fixed instantaneous field scale contract drift');"
        "must(expectedMax<=TASK1_LOCKED_E*(1+1e-12),'Actual instantaneous field exceeds registered fixed scale');")
    script = once(script,
        "shared_unclipped_maximum_V_m:expectedMax,maximum_projected_arrow_fraction:",
        "shared_unclipped_maximum_V_m:TASK1_LOCKED_E,current_view_actual_maximum_V_m:expectedMax,scale_mode:'fixed_all_conditions',maximum_projected_arrow_fraction:")
    script = once(script,
        "getState:()=>({plane_id:cache.plane?.id,common_max_V_m:cache.scale,time_ms:cache.time_ms})",
        "getState:()=>({plane_id:cache.plane?.id,common_max_V_m:cache.scale,time_ms:cache.time_ms,scale_mode:'fixed_all_conditions'})")
    return script


def patch_static(html: str) -> str:
    """Correct only explanatory HTML prose; executable patches stay separate."""
    html = once(html,
        '<label for="range">공통 색상 범위',
        '<label for="range">모든 조건 고정 범위')
    html = once(html,
        '목표 범위 clipping은 표시만 바꾸며 표면 층 경계의 높은 값을 깊이 집중으로 해석하지 않습니다.',
        '전기장과 접촉 전류밀도 색 범위는 전체 지원 조건을 포괄하는 사전 고정 상한을 사용하며 선택에 따라 자동 조정하지 않습니다. 표면 층 경계의 높은 값을 깊이 집중으로 해석하지 않습니다.')
    html = once(html,
        '전체 단면 최대에 맞춘 공통 색 범위를 사용하므로 표층 최대가 크면 깊은 영역의 색 차이가 작게 보일 수 있습니다.',
        '모든 지원 조건에서 같은 고정 전기장 범위를 사용하므로 표층 최대가 크면 깊은 영역의 색 차이가 작게 보일 수 있습니다. 시간·단면·주파수·구동 조건을 바꿔도 범위와 화살표 크기 분모는 자동 변경하지 않습니다.')
    return html
