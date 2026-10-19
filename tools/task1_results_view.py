#!/usr/bin/env python3
"""Render a local, offline Task 1 evidence dashboard from completed results.

This reader does no solve and imports no research module.  Scientific figures
use saved display-only native-phi gradients; native-cell statistics remain the
authority for scores.  Run serially under the shared finite resource budget.
"""
from __future__ import annotations

import argparse
import base64
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import resource
import signal
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

ROOT = Path(__file__).resolve().parents[1]
CAPS = {
    'surface_J_RMS_max_A_m2': (1, 'Jmax'),
    'surface_J_RMS_p95_A_m2': (1, 'J95'),
    'contact_voltage_RMS_max_V': (1, 'contact V RMS'),
    'SC_power_W': (2, 'SC loss'),
    'contact_power_W': (2, 'contact loss'),
    'source_power_W': (2, 'total source power'),
}
GIB = 1024**3


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def properties(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            result[key.strip()] = value.strip()
    return result


def comparison_signature(summary, config):
    """Separate incompatible meshes/materials/contacts, before scaling."""
    mesh = summary['mesh_metadata']
    values = {key: mesh.get(key) for key in (
        'h_xy_mm', 'radius_mm', 'total_depth_mm', 'sc_cells', 'bulk_layer_counts',
        'z_faces_mm', 'tissue_boundaries_mm', 'field_reconstruction', 'source_resistance_ohm')}
    values['physical_models'] = {key: value for key, value in config.items()
        if key.endswith(('.sigma', '.epsilon_r')) or key.startswith('z.')}
    values['target'] = 'r<=5mm; surface-depth15<=z<=20mm; fractional native volume'
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def scales(metrics, reference):
    if metrics['source_power_W'] <= 0 or reference['source_power_W'] <= 0:
        raise ValueError('Positive total source power required for normalization')
    candidates = {'1Vpp ceiling': 1.}
    for key, (degree, label) in CAPS.items():
        a, b = metrics[key], reference[key]
        if not math.isfinite(a) or not math.isfinite(b) or min(a, b) < 0:
            raise ValueError('Nonnegative finite burden metrics required: '+key)
        if a > 0:
            candidates[label] = (b/a)**(1/degree)
    cap = min(candidates.values())
    return dict(raw=1., equal_total_power=math.sqrt(reference['source_power_W']/metrics['source_power_W']),
                composite_burden=cap, composite_limiting=[key for key, value in candidates.items()
                    if math.isclose(value, cap, rel_tol=1e-9, abs_tol=1e-12)],
                composite_candidate_scales=candidates)


def load_case(path):
    path = Path(path).resolve()
    summary = read(path)
    if summary.get('status') != 'complete':
        raise ValueError('Dashboard requires completed result: '+str(path))
    run = path.parents[2]
    registration = read(run/'preregistration.json')
    matches = [case for case in registration['cases'] if case['id'] == summary['id']]
    if len(matches) != 1:
        raise ValueError('One registered source case required')
    case = matches[0]
    config = properties(case['config_file'])
    config_hash = sha(case['config_file'])
    if config_hash != summary['mesh_metadata']['config_sha256'] or config_hash != case['config_sha256']:
        raise ValueError('Config hash mismatch: '+summary['id'])
    circuit = case.get('circuit') or dict(n_pads=case.get('n_pads'), n_outputs=case.get('n_outputs'),
        pad_to_node=case.get('pad_node_ids'), return_topology='common_GND', n_return_nodes=1,
        source_resistance_ohm=case.get('source_resistance_ohm'),
        inactive_source_at_other_frequencies=case.get('inactive_output_termination'))
    if circuit.get('n_pads') is None or circuit.get('n_outputs') is None:
        raise ValueError('Physical pad and independent output counts must be explicit')
    conditions = [item for item in summary['conditions'] if item['waveform'] == 'square_3h']
    if not conditions:
        raise ValueError('Explicit later square_3h result required')
    probes_path = path.parent/summary['artifacts']['probes_json']
    expected = summary['artifacts']['files'][probes_path.name]['SHA256']
    if sha(probes_path) != expected:
        raise ValueError('Probe artifact SHA mismatch')
    probe_conditions = {item['id']: item['probe40'] for item in read(probes_path)['conditions']}
    spatial, bulk_skin_j = {}, {}
    # Only attach stable complete audits whose referenced summary matches.
    for audit_path in sorted((run/'audit').glob('*.json')):
        audit = read(audit_path)
        if audit.get('case_id') == summary['id'] and audit.get('summary_sha256') == sha(path):
            for item in audit.get('conditions', []):
                if 'spatial' in item:
                    spatial[item['condition_id']] = item['spatial']
                if 'bulk_skin_J' in item:
                    bulk_skin_j[item['condition_id']] = item['bulk_skin_J']
    return dict(path=path, summary=summary, run=run, registration=registration, case=case,
        circuit=circuit, config=config, signature=comparison_signature(summary, config),
        conditions=conditions, probes=probe_conditions, spatial=spatial, bulk_skin_J=bulk_skin_j,
        physical_model_version=hashlib.sha256(json.dumps({key: value for key, value in config.items()
            if key.endswith(('.sigma', '.epsilon_r')) or key.startswith('z.')}, sort_keys=True).encode()).hexdigest())


def row_data(item, condition, reference=None):
    volume = condition['volume_metrics']['regions']
    target = volume['target']['statistics']
    normalizations = scales(condition['metrics'], reference['metrics']) if reference else None
    values = {}
    for mode in ('raw', 'equal_total_power', 'composite_burden'):
        scale = 1. if mode == 'raw' else (normalizations[mode] if normalizations else None)
        values[mode] = None if scale is None else dict(
            amplitude_scale=scale, source_Vpp_per_output=condition['source_Vpp_per_output']*scale,
            ROI_mean_V_cm=target['maxTIS']['mean']*scale*.01,
            ROI_P10_V_cm=target['maxTIS']['p10']*scale*.01,
            ROI_max_V_cm=target['maxTIS']['max']*scale*.01,
            ROI_E_RMS_mean_V_cm=target['RMS']['mean']*scale*.01,
            ROI_fixed_direction_TIS_mean_V_cm=target['fixedTIS']['mean']*scale*.01,
            ROI_fixed_direction_TIS_P10_V_cm=target['fixedTIS']['p10']*scale*.01,
            superficial_P95_V_cm=volume['surface_0_5']['statistics']['maxTIS']['p95']*scale*.01,
            off_target_P95_V_cm=volume['off_target']['statistics']['maxTIS']['p95']*scale*.01,
            global_max_V_cm=volume['total']['statistics']['maxTIS']['max']*scale*.01,
            Jmax_mA_cm2=condition['metrics']['surface_J_RMS_max_A_m2']*scale*.1,
            J95_mA_cm2=condition['metrics']['surface_J_RMS_p95_A_m2']*scale*.1,
            contact_V_RMS_mV=condition['metrics']['contact_voltage_RMS_max_V']*scale*1000,
            SC_loss_uW=condition['metrics']['SC_power_W']*scale**2*1e6,
            contact_loss_uW=condition['metrics']['contact_power_W']*scale**2*1e6,
            source_power_uW=condition['metrics']['source_power_W']*scale**2*1e6,
            max_source_current_RMS_mA=condition['metrics']['max_source_current_RMS_mA']*scale)
    return dict(case_id=item['summary']['id'], condition_id=condition['id'], run_id=item['run'].name,
        n_pads=item['circuit']['n_pads'], n_outputs=item['circuit']['n_outputs'],
        comparison_signature=item['signature'], reference_condition_id=reference['id'] if reference else None,
        normalizations=normalizations, values=values,
        source_commit=item['registration']['source_commit'], config_sha256=item['case']['config_sha256'],
        physical_contact_model_sha256=item['physical_model_version'],
        summary_sha256=sha(item['path']), input_manifest_sha256=item['summary']['input_manifest_sha256'],
        postprocessor_sha256=item['summary']['postprocessor_sha256'],
        circuit=item['circuit'], mesh=item['summary']['mesh_metadata'],
        status=dict(calculation='complete', conservation=('passed' if all(gate['status'] == 'passed'
            for gate in item['summary']['validation_gate_status'].values()) else 'failed'),
            convergence='not established; see separate mesh evidence', experiment='not validated'),
        spatial=item['spatial'].get(condition['id']), bulk_skin_J=item['bulk_skin_J'].get(condition['id']))


def esc(value):
    return html.escape(str(value), quote=True)


def number(value):
    return '—' if value is None else f'{value:.6g}'


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def probe_csv(item, condition, directory):
    probe = item['probes'][condition['id']]
    if probe['status'] != 'complete' or len(probe['measurements']) != 40:
        raise ValueError('Complete cross-grid40 native-potential probe rows required')
    rows = []
    for row in probe['measurements']:
        envelope = row['fundamental_fixed_axis_envelope']
        rows.append(dict(run_id=item['run'].name, candidate_id=condition['id'], probe_id=row['id'],
            depth_from_surface_mm=row['depth_from_skin_surface_mm'], centre_mm=json.dumps(row['centre_mm']),
            axis=row['axis'], tip_gap_mm=row['tip_gap_mm'], plus_mm=json.dumps(row['plus_mm']),
            minus_mm=json.dumps(row['minus_mm']), voltage_definition=row['voltage_definition'],
            unloaded_RMS_V=row['RMS_V'], full_waveform_Vpp_lower_V=row['Vpp_lower_V'],
            full_waveform_Vpp_upper_V=row['Vpp_upper_V'],
            fundamental_envelope_min_V=envelope['minimum_V'],
            fundamental_envelope_max_V=envelope['maximum_V'],
            fundamental_envelope_width_V=envelope['variation_range_V'],
            fundamental_modulation_index=envelope['modulation_index'],
            spectrum_peak_phasors=json.dumps(row['spectrum'], separators=(',', ':')),
            nominal_attenuation_only=json.dumps(row.get('nominal_instrument', []), separators=(',', ':')),
            actual_instrument_prediction_status='unavailable: differential impedance/capacitance, bandwidth, calibration unverified',
            source_config_sha256=item['case']['config_sha256']))
    path = directory/(condition['id']+'-probe40.csv')
    write_csv(path, rows)
    return path, probe


def plotting():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    return plt, np


def save_figure(figure, path, plt):
    figure.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(figure)
    return path


def coordinates_figure(directory):
    plt, np = plotting()
    from matplotlib.patches import Circle, Rectangle
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.4), layout='constrained')
    left, right = axes
    left.add_patch(Circle((0, 0), 25, fill=False, color='#344c67'))
    for x, y in [(0, 0), (5, 0), (-5, 0), (0, 5), (0, -5)]:
        left.scatter(x, y, c='#d54d26', s=25)
        left.plot([x-2.5, x+2.5], [y, y], c='#2673a5', lw=1.2)
        left.plot([x, x], [y-2.5, y+2.5], c='#2673a5', lw=1.2)
    left.annotate('X probe tips: -2.5 / +2.5 mm', xy=(2.5, 0), xytext=(0, -16),
                  ha='center', fontsize=9, arrowprops=dict(arrowstyle='->'))
    left.set(xlim=(-27, 27), ylim=(-27, 27), xlabel='X [mm]', ylabel='Y [mm]',
        title='Five centres per depth; two probe axes per centre')
    left.set_aspect('equal')
    left.grid(alpha=.15)
    right.add_patch(Rectangle((-5, 15), 10, 5, color='#dba646', alpha=.4, label='Target ROI section'))
    for boundary in (0, .1, 5.1, 10.1, 25.1):
        right.axhline(boundary, color='#555555', lw=.7)
    for depth in (5, 10, 15, 20):
        right.scatter([-5, 0, 5], [depth]*3, c='#d54d26', s=20)
        right.text(12, depth, f'{depth} mm', va='center', fontsize=9)
    right.set(xlim=(-25, 25), ylim=(26, -.7), xlabel='X [mm]; section Y=0',
        ylabel='Depth +z [mm] from skin surface z=0', title='Depth points and physical layer interfaces')
    right.legend(loc='lower left', fontsize=8)
    figure.suptitle('Probe centre offset 5 mm and differential tip gap 5 mm are separate quantities', fontsize=12)
    return save_figure(figure, directory/'probe-coordinates.png', plt)


def waveform_figure(item, condition, probe, directory):
    plt, np = plotting()
    row = next(row for row in probe['measurements'] if row['id'] == 'd20-centre-X')
    spectrum = row['spectrum']
    frequencies = np.array([row['frequency_Hz'] for row in spectrum])
    phasors = np.array([complex(row['real_V'], row['imaginary_V']) for row in spectrum])
    samples = min(100000, row['common_period']['samples'])
    t = np.arange(samples)*row['common_period']['period_s']/samples
    voltage = np.real(np.exp(2j*np.pi*t[:, None]*frequencies)@phasors)
    fundamental = row['fundamental_fixed_axis_envelope']['frequencies_Hz']
    mask = np.isin(frequencies, fundamental)
    envelope = abs(np.exp(2j*np.pi*t[:, None]*frequencies[mask])@phasors[mask])
    figure, axes = plt.subplots(1, 2, figsize=(11, 3.8), layout='constrained')
    axes[0].plot(t*1000, voltage*1000, lw=.55, color='#215a87', label='All active harmonics')
    axes[0].plot(t*1000, envelope*1000, color='#cd6d25', lw=1.2, label='Fundamental-only analytic envelope')
    axes[0].plot(t*1000, -envelope*1000, color='#cd6d25', lw=1.2)
    axes[0].set(xlabel='Time [ms]; one exact common period', ylabel='Differential voltage [mV]',
        title='Centre (0,0,+20) mm; X tips ±2.5 mm')
    axes[0].legend(fontsize=8, loc='upper right')
    axes[1].stem(frequencies, abs(phasors)*1000, basefmt=' ')
    axes[1].set(xlabel='Frequency [Hz]', ylabel='Peak spectral amplitude [mV]', title='Native complex φ(+)−φ(−) spectrum')
    figure.suptitle(condition['id']+' • unloaded prediction', fontsize=11)
    return save_figure(figure, directory/(condition['id']+'-waveform.png'), plt)


def map_archive(item, condition):
    metadata = next((row for row in item['summary']['maps'] if row.get('actual_carrier_Hz') in
        (None, condition['actual_fundamental_Hz'][0])), None)
    if metadata is None:
        return None
    path = item['path'].parent/metadata.get('directory', '.')/metadata['file']
    # Direct summary artifact listings can place a C1 map in a subdirectory.
    relative = str(path.relative_to(item['path'].parent))
    expected = item['summary']['artifacts']['files'].get(relative)
    if expected and sha(path) != expected['SHA256']:
        raise ValueError('Saved display-map SHA mismatch')
    return path


def maps_figure(records, mode, metric, directory, group_name):
    plt, np = plotting()
    from matplotlib.patches import Circle, Rectangle
    available, maximum = [], 0.
    for item, condition, row in records:
        path = map_archive(item, condition)
        value = row['values'][mode]
        if path is None or value is None:
            continue
        with np.load(path, allow_pickle=False) as archive:
            values = archive[metric]*.01*value['amplitude_scale']
            xy_shape, xz_shape = tuple(archive['xy_shape']), tuple(archive['xz_shape'])
            axis, z = archive['xy_axis_mm'].copy(), archive['xz_z_mm'].copy()
        finite = values[np.isfinite(values)]
        if len(finite):
            maximum = max(maximum, float(finite.max()))
        available.append((item, condition, values, xy_shape, xz_shape, axis, z))
    if not available:
        return None
    maximum = maximum or 1.
    figure, axes = plt.subplots(len(available), 5, figsize=(17, 3.3*len(available)),
        squeeze=False, layout='constrained')
    for r, (item, condition, values, xy_shape, xz_shape, axis, z) in enumerate(available):
        count = math.prod(xy_shape)
        xy, xz = values[:count].reshape(xy_shape), values[count:].reshape(xz_shape)
        for d, depth in enumerate((5, 10, 15, 20)):
            ax = axes[r, d]
            im = ax.pcolormesh(axis, axis, xy[d], shading='nearest', cmap='viridis', vmin=0, vmax=maximum)
            ax.add_patch(Circle((0, 0), 5, fill=False, color='white', lw=1.1,
                linestyle='-' if depth in (15, 20) else '--'))
            ax.set(title=f'z={depth} mm', xlabel='X [mm]', ylabel='Y [mm]', xlim=(-25, 25), ylim=(-25, 25))
            ax.set_aspect('equal')
        ax = axes[r, 4]
        ax.pcolormesh(axis, z, xz, shading='nearest', cmap='viridis', vmin=0, vmax=maximum)
        for boundary in (.1, 5.1, 10.1):
            ax.axhline(boundary, color='white', alpha=.7, lw=.7)
        ax.add_patch(Rectangle((-5, 15), 10, 5, fill=False, edgecolor='white', lw=1.2))
        ax.set(title='XZ; Y=0', xlabel='X [mm]', ylabel='Depth +z [mm]', xlim=(-25, 25), ylim=(25.1, 0))
        axes[r, 0].text(-.42, .5, f"{item['circuit']['n_pads']} pads\n{condition['id']}",
            transform=axes[r, 0].transAxes, rotation=90, va='center', ha='center', fontsize=8)
    metric_label = {'square_maxTIS_V_m': 'Fundamental sampled-direction maxTIS',
        'square_fixedTIS_V_m': 'Fundamental fixed-direction TIS',
        'square_RMS_V_m': 'All-harmonic vector E RMS'}[metric]
    figure.colorbar(im, ax=axes.ravel().tolist(), label=metric_label+' [V/cm]', shrink=.8)
    figure.suptitle(f'{group_name} • {mode} • common linear range 0–{maximum:.4g} V/cm\n'
        'Display-only −grad(native φ); blank samples unsupported; boundary peaks do not establish focus', fontsize=12)
    return save_figure(figure, directory/(group_name+'-'+mode+'-'+metric+'.png'), plt)


def image_tag(path):
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f'<img loading="lazy" alt="{esc(path.stem)}" src="data:image/png;base64,{encoded}">'


def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+\
        '</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+cell+'</td>' for cell in row)+'</tr>'
            for row in rows)+'</tbody></table></div>'


def build(args, directory):
    paths = args.summary or sorted((ROOT/'data-native').glob('*/postprocess/*/summary.json'))
    items = [load_case(path) for path in paths]
    if not items:
        raise ValueError('At least one completed registered four-pad baseline required')
    baseline_path = (args.baseline or ROOT/'data-native/cloud-baseline-20261019T185900Z/postprocess/baseline-square15-coarse/summary.json').resolve()
    baseline = next((item for item in items if item['path'] == baseline_path), None)
    if baseline is None:
        baseline = load_case(baseline_path)
        items.insert(0, baseline)
    if baseline['circuit']['n_pads'] != 4 or baseline['circuit']['n_outputs'] != 2:
        raise ValueError('Pinned baseline must be four physical pads and two independent outputs')
    # Same-grid comparisons always have an explicit original-square four-pad reference.
    references = {}
    for item in items:
        if item['circuit']['n_pads'] == 4 and item['circuit']['n_outputs'] == 2 and (
            item['case'].get('design_id') == 'baseline-square15' or item['case'].get('control') == 'original_four_square'):
            references.setdefault(item['signature'], item['conditions'][0])
    records = []
    for item in items:
        for condition in item['conditions']:
            records.append((item, condition, row_data(item, condition, references.get(item['signature']))))
    payload = dict(schema='task1_offline_result_comparison_v1', created_utc=datetime.now(timezone.utc).isoformat(),
        generator_sha256=sha(__file__), baseline_condition_id=baseline['conditions'][0]['id'],
        definitions=dict(target='r<=5 mm, surface depth15–20 mm volume',
            maxTIS='fundamental-only 2074 sampled-direction max 2 min projected carrier peaks; angular lower bound',
            RMS='vector E RMS over all active harmonics; not TIS modulation',
            equal_total_power='scale sqrt(P_same_grid_four_pad/P_candidate), may exceed1; source power includes50ohm resistors',
            composite_burden='scale min(1, baseline/candidate Jmax,J95,contactV, sqrt(power ratios SC/contact/source)); per-item cap',
            caps='numerical four-pad reference values, not human safety limits',
            contact='PBS-minus-Rs area-specific surrogate, not validated real skin contact',
            actual_instrument='unavailable until differential input impedance, capacitance, bandwidth and calibration are measured'),
        conditions=[row for _, _, row in records], missing_pad_counts=[n for n in (8, 12, 16)
            if not any(row['n_pads'] == n and row['n_outputs'] == 2 for _, _, row in records)],
        new_PDE=0, new_research_postprocess=0, experiment_validated=False)
    (directory/'comparison.json').write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n')
    flat = []
    for _, _, row in records:
        for mode, values in row['values'].items():
            if values is not None:
                flat.append(dict(run_id=row['run_id'], condition_id=row['condition_id'], n_pads=row['n_pads'],
                    n_outputs=row['n_outputs'], normalization=mode, **values,
                    reference_condition_id=row['reference_condition_id'], config_sha256=row['config_sha256']))
    write_csv(directory/'comparison.csv', flat)
    sections = ["<h1>Task 1 · TIS research evidence</h1><p>고정 D50 mm 팬텀 · 상부 접촉 · SC/dermis/fat/muscle 0.1/5/5/15 mm. "
        "목표 ROI: 중앙 r≤5 mm, 표면 기준 깊이 15–20 mm. 수치 결과 화면이며 깊이 집중·실험·인체 안전 검증은 완료되지 않았습니다.</p>",
        '<div class="notice">4개 패드 기준은 항상 표시됩니다. 8·12·16개 패드는 각각 물리 접촉 수이며 독립 출력 수와 구분합니다. '
        '다른 격자 사이의 변화를 설계 개선 순위로 사용하지 않습니다. PBS 계면 모델과 피부 접촉 검증은 별개입니다.</div>']
    fixed = next(row for item, _, row in records if item is baseline)
    b = fixed['values']['raw']
    sections.append('<section class="baseline"><h2>고정 4패드 기준 · '+esc(fixed['condition_id'])+'</h2><p>'+
        '2 independent outputs · common GND · 50 Ω/output · 1 Vpp/output, open-circuit command. '
        'ROI mean <b>'+number(b['ROI_mean_V_cm'])+'</b> V/cm · P10 <b>'+number(b['ROI_P10_V_cm'])+
        '</b> V/cm · global max '+number(b['global_max_V_cm'])+' V/cm. '+
        '계산 완료 / 전류·전력 보존 검사 '+esc(fixed['status']['conservation'])+' / 수렴 미확립 / 실험 미검증.</p></section>')
    sections.append('<h2>같은 격자와 물성에서 비교</h2><p>표의 maxTIS는 기본 두 carrier의 방향별 최대 변조 폭입니다. '
        'square_3h의 전체 합성파 Vpp·RMS 및 기본파 envelope는 프로브 자료에서 별도로 제공합니다. '
        '동일 총전력은 50 Ω 출력저항 손실까지 포함한 source power를 맞춥니다. '
        '복합 부담 상한은 Jmax·J95·접촉 RMS 전압·SC 손실·접촉 손실·총전력을 각각 4패드 수치값 이하로 제한하며 진폭 scale≤1입니다.</p>')
    sections.append('<p>부담 표의 Jmax/J95는 전극 접촉면 법선 RMS 전류밀도의 최대값 및 접촉면적 가중 P95입니다. '
        'SC·dermis 내부 벡터 전류밀도는 별도 bulk-skin audit가 있을 때 증거 목록에 함께 표시합니다. '
        '이 수치 비교 기준은 인체 안전 한계가 아닙니다.</p>')
    grouped = {}
    for item, condition, row in records:
        if row['n_outputs'] == 2:
            grouped.setdefault(row['comparison_signature'], []).append((item, condition, row))
    for index, (signature, group) in enumerate(grouped.items(), 1):
        group_name = f'grid-{index}-{signature[:8]}'
        mesh = group[0][2]['mesh']
        sections.append('<section><h3>'+esc(group_name)+f" · XY {mesh['h_xy_mm']} mm · SC {mesh['sc_cells']} · bulk "+
            esc(mesh['bulk_layer_counts'])+'</h3>')
        for mode, label in [('raw', '동일 명령 1 Vpp'), ('equal_total_power', '동일 총전력'),
                            ('composite_burden', '복합 부담 상한 · 절대 ROI 변조 잔존값')]:
            rows = []
            for item, condition, row in group:
                values = row['values'][mode]
                if values is None:
                    rows.append([esc(row['condition_id']), str(row['n_pads']), '2',
                        '<b>동일 격자 4패드 기준 없음; 정규화 보류</b>']+['—']*9)
                    continue
                rows.append([esc(row['condition_id']), str(row['n_pads']), str(row['n_outputs']),
                    *[number(values[key]) for key in ('amplitude_scale', 'ROI_mean_V_cm', 'ROI_P10_V_cm',
                    'ROI_max_V_cm', 'Jmax_mA_cm2', 'J95_mA_cm2', 'contact_V_RMS_mV',
                    'SC_loss_uW', 'contact_loss_uW', 'source_power_uW')]])
            for n in (4, 8, 12, 16):
                if not any(row['n_pads'] == n for _, _, row in group):
                    rows.append([f'{n} pads', str(n), '2 (planned)', '<b>계산 자료 없음</b>']+['—']*9)
            sections.append('<h4>'+label+'</h4>'+table(['조건', 'pads', 'outputs', 'scale', 'ROI mean V/cm',
                'ROI P10 V/cm', 'ROI max V/cm', 'Jmax mA/cm²', 'J95 mA/cm²', 'contact mV RMS',
                'SC µW', 'contact µW', 'source µW'], rows))
            if args.figures:
                for metric in ('square_maxTIS_V_m', 'square_RMS_V_m'):
                    figure = maps_figure(group, mode, metric, directory, group_name)
                    if figure:
                        sections.append('<details><summary>공통 선형 색범위 · '+esc(metric)+' 지도</summary>'+image_tag(figure)+'</details>')
        sections.append('</section>')
    sections.append('<h2>회로·물성·실행 증거</h2><p>다른 carrier에서도 비구동 출력은 0 V/50 Ω로 종단됩니다. '
        '물리 귀환 패드는 각 주파수에 모두 참여하는 단일 이상 공통 GND에 연결됩니다. '
        '초기 2000/2010 Hz bare sinusoid benchmark는 이 후기 3000/3030 Hz square_3h 계산과 분리하여 추적합니다. '
        'COMSOL 5.3a (예정 build5.3.1.201)의 설치·license·실행 가능 여부는 미검증입니다.</p>')
    for item, condition, row in records:
        regions = condition['volume_metrics']['regions']
        spatial_rows = []
        for region, name in [('target', 'ROI r≤5mm,z15–20'), ('surface_0_5', '비표적 z0–5'),
                             ('off_target', '전체 비표적'), ('total', '전체 팬텀')]:
            for metric, label in [('maxTIS', '기본파 방향 최대 TIS'),
                                  ('fixedTIS', '고정 방향 (X+Y)/√2 TIS'), ('RMS', '전체 harmonic vector E RMS')]:
                values = regions[region]['statistics'][metric]
                spatial_rows.append([esc(name), esc(label), *[number(values[key]*.01)
                    for key in ('mean', 'p10', 'p95', 'max')]])
        details = dict(run_id=row['run_id'], candidate_id=row['condition_id'], source_commit=row['source_commit'],
            config_sha256=row['config_sha256'], physical_contact_model_sha256=row['physical_contact_model_sha256'],
            input_manifest_sha256=row['input_manifest_sha256'], postprocessor_sha256=row['postprocessor_sha256'],
            summary_sha256=row['summary_sha256'], calculation_status=row['status'], circuit=row['circuit'],
            frequencies_Hz=condition['actual_fundamental_Hz'], actual_waveform=condition['waveform'],
            mesh=dict(h_xy_mm=row['mesh']['h_xy_mm'], sc_cells=row['mesh']['sc_cells'],
                bulk_counts=row['mesh']['bulk_layer_counts'], cells=row['mesh']['cells']),
            composite_scale=row['normalizations'], spatial_audit=row['spatial'], bulk_skin_J=row['bulk_skin_J'],
            tissue_contact_model=dict(tissue='piecewise-constant complex conductivity; no dielectric dispersion',
                contact='PBS area-specific impedance minus selected Rs surrogate; z properties in ohm*m2',
                source_coating_nm=item['case'].get('source_coating_nm'),
                Rs_fit_window_Hz=item['case'].get('source_Rs_fit_window_Hz'),
                model_version_sha256=row['physical_contact_model_sha256']),
            raw_centre_E_peak_complex_spectrum=condition['metrics'].get('centre_field_spectrum'),
            spatial_location_status='native cell locations available' if row['spatial'] else 'spatial audit not attached; maximum location unreported')
        sections.append('<details><summary>'+esc(row['condition_id'])+'</summary>'+
            table(['영역', '정의', 'mean V/cm', 'P10 V/cm', 'P95 V/cm', 'max V/cm'], spatial_rows)+
            '<pre>'+esc(json.dumps(details,
            ensure_ascii=False, indent=2))+'</pre></details>')
    sections.append('<h2>프로브: 4깊이 × 5중심 × 2방향 = 조건별40행</h2><p>z=0 피부 표면, +z 깊이. '
        '중심 (0,0), (±5,0), (0,±5) mm 각각에서 X/Y 차동 팁 간격5 mm를 유지합니다. '
        '복소 φ(+)−φ(−)로 실제 합성파를 재구성하며 E×간격 대체값은 사용하지 않습니다. '
        '표는 무부하 계산입니다. ETA5001 50×/500× 명목 감쇠만 반영한 값은 CSV에 별도 표시합니다. '
        '입력 임피던스·대역폭·보정 검증이 없으므로 실제 측정기 부하가 반영된 예측은 보류합니다.</p>')
    if args.figures:
        sections.append(image_tag(coordinates_figure(directory)))
    for item, condition, row in records:
        csv_path, probe = probe_csv(item, condition, directory)
        encoded = base64.b64encode(csv_path.read_bytes()).decode()
        sections.append('<details><summary>'+esc(condition['id'])+' · 40행 프로브</summary>'+
            f'<p><a download="{esc(csv_path.name)}" href="data:text/csv;base64,{encoded}">40행 CSV 다운로드</a></p>')
        probe_rows = []
        for measurement in probe['measurements']:
            envelope = measurement['fundamental_fixed_axis_envelope']
            probe_rows.append([esc(measurement['id']), esc(measurement['centre_mm']),
                number(measurement['Vpp_lower_V']*1000), number(measurement['Vpp_upper_V']*1000),
                number(measurement['RMS_V']*1000), number(envelope['variation_range_V']*1000)])
        sections.append(table(['ID', 'centre X/Y/+z mm', 'full Vpp lower mV', 'full Vpp upper mV',
            'RMS mV', 'fundamental envelope width mV'], probe_rows))
        if args.figures:
            sections.append(image_tag(waveform_figure(item, condition, probe, directory)))
        sections.append('</details>')
    c1 = [row for _, _, row in records if row['n_outputs'] == 1]
    sections.append('<h2>단일 전극쌍 비교</h2><p>한 신호 패드와 한 귀환 패드의 단일 출력 조건입니다. '
        '같은 전기장 RMS는 같은 생리적 활성화 또는 같은 TIS 변조를 뜻하지 않습니다. '+
        ('C1 계산 '+str(len(c1))+'개를 위 증거 목록과 프로브에서 제공합니다. 목표점/ROI RMS 일치 전압·전류·부담 비교는 별도 C1 분석 산출물을 참조합니다.'
         if c1 else '완료된 C1 원시 계산이 아직 없어 요구 인가전압 비교를 보류합니다.')+'</p>')
    encoded = base64.b64encode((directory/'comparison.csv').read_bytes()).decode()
    sections.append('<p><a download="comparison.csv" href="data:text/csv;base64,'+encoded+'">전체 정규화 비교 CSV</a></p>'+
        '<footer>Generated '+esc(payload['created_utc'])+' · offline, no remote calls · new PDE0 · '+
        '수치 보존 검사는 격자 수렴·독립 solver·실험 검증과 구분합니다.</footer>')
    css = '''body{max-width:1500px;margin:32px auto;padding:0 24px;font:15px/1.55 system-ui,sans-serif;color:#183047;background:#f8fafb}h1,h2,h3,h4{line-height:1.3}h1{font-size:30px}h2{margin-top:34px}section,.notice,details{background:white;border:1px solid #d8e2ea;border-radius:10px;padding:16px;margin:16px 0}.baseline{border-left:6px solid #246b98;position:sticky;top:0;z-index:2;box-shadow:0 2px 7px #18304720}.notice{border-left:6px solid #d69331}table{border-collapse:collapse;font-size:12px;width:100%;white-space:nowrap}th,td{text-align:right;border-bottom:1px solid #e2e7ed;padding:7px}th:first-child,td:first-child{text-align:left;max-width:330px;white-space:normal}th{background:#eaf0f5}tbody tr:hover{background:#f0f5f8}.scroll{overflow:auto}img{max-width:100%;height:auto;margin-top:14px}pre{font-size:11px;white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer;font-weight:600}footer{font-size:12px;color:#5b6c7b;margin:24px 0}a{color:#145f99}'''
    document = '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+\
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'; navigate-to data:">'+\
        '<title>Task 1 TIS results</title><style>'+css+'</style><body>'+''.join(sections)+'</body></html>'
    args.output.write_text(document)
    return dict(status='rendered_offline_evidence', output=str(args.output), assets=str(directory),
        completed_conditions=len(records), missing_pad_counts=payload['missing_pad_counts'],
        new_PDE=0, source_files_edited=0)


def self_test():
    reference = {key: 4. for key in CAPS}
    candidate = {key: (16. if degree == 2 else 8.) for key, (degree, _) in CAPS.items()}
    result = scales(candidate, reference)
    assert result['raw'] == 1 and result['equal_total_power'] == .5 and result['composite_burden'] == .5
    lighter = {key: .25 for key in CAPS}
    assert scales(lighter, reference)['composite_burden'] == 1.
    # Composite cap must satisfy every individual metric, not just one sum.
    candidate['surface_J_RMS_p95_A_m2'] = 20.
    result = scales(candidate, reference)
    assert result['composite_burden'] == .2
    for key, (degree, _) in CAPS.items():
        assert candidate[key]*result['composite_burden']**degree <= reference[key]*(1+1e-12)
    minimal = dict(mesh_metadata=dict(h_xy_mm=1., sc_cells=2))
    other = dict(mesh_metadata=dict(h_xy_mm=.5, sc_cells=2))
    assert comparison_signature(minimal, {'z.3000.re': '1'}) != comparison_signature(other, {'z.3000.re': '1'})
    assert comparison_signature(minimal, {'z.3000.re': '1'}) != comparison_signature(minimal, {'z.3000.re': '2'})
    return dict(passed=True, checks='individual nonlinear caps, no voltage boosting, mesh/contact cohort separation', new_PDE=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, action='append')
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/CLOUD_RESULTS.html')
    parser.add_argument('--assets-dir', type=Path)
    parser.add_argument('--figures', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test()))
        return
    args.output = args.output.resolve()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    directory = (args.assets_dir or args.output.parent/('cloud-results-'+stamp)).resolve()
    if directory.exists():
        raise ValueError('Use a new unique derived-artifact directory; preserve previous figures')
    if not args.output.parent.is_dir() or not directory.parent.is_dir():
        raise ValueError('Output parent must exist for explicit storage accounting')
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        budget_path = ROOT/'runtime/task1-budget.json'
        budget = read(budget_path)
        if budget['limit_seconds'] != 6600:
            raise ValueError('Existing finite6600-second resource budget changed')
        remaining = budget['limit_seconds']-budget['spent_seconds']
        if remaining <= 0:
            raise ValueError('Existing time budget exhausted; rendering not started')
        if __import__('shutil').disk_usage(directory.parent).free < 2*GIB+50*1024**2:
            raise ValueError('2GiB reserve plus50MiB visualization allowance unavailable')
        start, status = time.monotonic(), 'failed'
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        def timeout(signum, frame):
            raise TimeoutError('Finite visualization deadline exceeded')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, min(120., remaining))
        directory.mkdir()
        try:
            result = build(args, directory)
            added = sum(path.stat().st_size for path in directory.glob('*'))+args.output.stat().st_size
            if added > 50*1024**2:
                raise RuntimeError('Visualization exceeded50MiB output allowance; preserve generated evidence')
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > 3*GIB:
                raise MemoryError('Visualization exceeded existing3GiB RSS budget')
            result['resources'] = dict(wall_seconds=time.monotonic()-start, generated_bytes=added,
                peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                max_seconds=min(120., remaining), added_MiB_limit=50, CPU_count=1)
            (directory/'render-receipt.json').write_text(json.dumps(result, indent=2)+'\n')
            status = result['status']
            print(json.dumps(result))
        except Exception as error:
            (directory/'render-failure.json').write_text(json.dumps(dict(status='failed',
                type=type(error).__name__, message=str(error), partial_artifacts_preserved=True), indent=2)+'\n')
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            seconds = time.monotonic()-start
            budget['spent_seconds'] += seconds
            budget['runs'].append(dict(run_id=directory.name, stage='offline_evidence_visualization',
                status=status, seconds=seconds))
            budget_path.write_text(json.dumps(budget, indent=2)+'\n')


if __name__ == '__main__':
    main()
