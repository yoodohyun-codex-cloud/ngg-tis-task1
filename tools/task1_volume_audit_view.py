#!/usr/bin/env python3
"""Offline selectors over completed, source-bound volume-audit JSON only.

No research-module imports, native-array reads, normalization calculation,
field reconstruction, PDE, adoption or network requests occur in this viewer.
"""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import html
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
PRIMARY = 'primary_r5_depth15_20'
SLAB = 'supplemental_wholeXY_depth15_20'
REGIONS = ('total', PRIMARY, SLAB, 'surface_0_5', 'primary_complement', 'supplemental_complement')
METRICS = ('maxTIS', 'fixedTIS', 'RMS')
MODES = ('raw_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power',
         'skin_contact_only', 'legacy_composite_full_skin')
BURDENS = ('surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2', 'contact_voltage_RMS_max_V',
    'SC_power_W', 'contact_power_W', 'source_power_W', 'bulk_skin_J_vector_RMS_max_A_m2',
    'bulk_skin_J_vector_RMS_p95_A_m2', 'skin_SC_plus_dermis_power_W')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            value.update(chunk)
    return value.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_tree(value):
    if isinstance(value, float):
        require(math.isfinite(value), 'Nonfinite audit value')
    elif isinstance(value, dict):
        for item in value.values():
            finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            finite_tree(item)


def number(value, name, *, nullable=False):
    if nullable and value is None:
        return
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0, 'Finite nonnegative '+name+' required')


def check_case(case):
    for key in ('case_id', 'condition_id', 'run_id', 'summary_path', 'baseline_summary',
                'comparison_signature', 'source_commit', 'configuration_sha256', 'physical_model_version'):
        require(isinstance(case.get(key), str) and case[key], 'Missing case provenance: '+key)
    require(case.get('adopted') is False and case.get('calculation_status') == 'cached_native_scalar_audit_complete',
            'Only calculated, unadopted cached audits supported')
    circuit = case['circuit']
    require(circuit.get('n_pads') in (4, 8, 12, 16) and circuit.get('n_outputs') == 2 and
            circuit.get('n_return_nodes') == 1 and circuit.get('source_resistance_ohm') == 50 and
            isinstance(circuit.get('return_topology'), str), 'Explicit physical pads/two outputs/common return/50ohm required')
    mesh = case['mesh']
    require(mesh.get('radius_mm') == 25 and math.isclose(mesh.get('total_depth_mm', 0), 25.1, abs_tol=1e-12),
            'Fixed D50 and25.1mm depth required')
    boundaries = mesh.get('tissue_boundaries_mm')
    require(isinstance(boundaries, list) and len(boundaries) == 5 and all(
        type(actual) in (int, float) and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
        for actual, expected in zip(boundaries, (0., .1, 5.1, 10.1, 25.1))),
        'Fixed SC/dermis/fat/muscle layer boundaries required')
    require(set(case['normalizations']) == set(MODES), 'All five distinct precomputed normalizations required')
    reproduction = case['primary_ROI_reproduction']
    require(all(reproduction.get(metric, {}).get('passed') is True for metric in METRICS), 'Original primary ROI regression evidence required')
    for mode_name, mode in case['normalizations'].items():
        for key in ('amplitude_scale', 'source_Vpp_per_output', 'sum_source_output_RMS_mA'):
            number(mode[key], key)
        require(len(mode['source_output_RMS_by_output_mA']) == 2, 'Two output RMS currents required')
        for current in mode['source_output_RMS_by_output_mA']:
            number(current, 'source current RMS mA')
        require(set(mode['regions']) == set(REGIONS), 'All six precomputed regions required')
        require(set(mode['normalized_burdens']) == set(BURDENS), 'Nine separately reported burdens required')
        require(set(mode['baseline_derived_numerical_limits']) == set(BURDENS), 'Frozen same-grid burden limits required')
        for value in (*mode['normalized_burdens'].values(), *mode['baseline_derived_numerical_limits'].values()):
            number(value, 'burden/limit')
        require(mode['includes_source_power_cap'] is (mode_name == 'legacy_composite_full_skin') and
                mode['includes_1Vpp_ceiling'] is (mode_name == 'legacy_composite_full_skin'), 'Normalization cap definitions changed')
        require(isinstance(mode.get('active_skin_contact_caps'), list), 'Active-cap list required')
        for region, metrics in mode['regions'].items():
            require(set(metrics) == set(METRICS), 'Three separate electrical metrics required')
            for metric, stats in metrics.items():
                for key in ('min', 'max', 'mean', 'p10', 'p50', 'p90', 'p95', 'p99', 'std', 'volume_m3'):
                    number(stats[key], region+'/'+metric+'/'+key)
                number(stats['CV'], 'CV', nullable=True)
                number(stats['p10_over_mean'], 'P10/mean', nullable=True)
                hotspot = stats['hotspot']
                require(len(hotspot['center_xyz_mm']) == 3 and all(type(x) in (int, float) and math.isfinite(x)
                    for x in hotspot['center_xyz_mm']), 'Finite hotspot XYZ in mm required')
                cutoffs = stats['fixed_baseline_threshold_volume']
                expected = {roi+'_'+stat for roi in (PRIMARY, SLAB) for stat in ('mean', 'p10')}
                require(set(cutoffs) == expected, 'Four frozen raw-baseline cutoffs required')
                for cutoff in cutoffs.values():
                    for key in ('cutoff_V_m', 'volume_m3', 'region_volume_fraction'):
                        number(cutoff[key], key)
                    require(cutoff['region_volume_fraction'] <= 1 and '>=' in cutoff['comparison'],
                            'Native >= classification with fraction<=1 required')
    probe = case['raw_probe_artifact_reference']
    require('unloaded' in probe['scope'].lower() and isinstance(probe['SHA256'], str), 'Unloaded native-probe reference required')


def validate_audit(path, verify_sources=True):
    path = Path(path).resolve()
    require(path.stat().st_size <= 25*1024**2, 'Single audit JSON exceeds25MiB read allowance')
    report_sha = sha(path)
    report = read(path)
    finite_tree(report)
    require(report.get('schema') == 'task1-volume-selectivity-v1' and report.get('status') == 'calculated_unadopted' and
            report.get('new_PDE_solves') == 0 and report.get('inputs_unchanged') is True and
            report.get('selected_for_adoption') == [], 'Completed unchanged unadopted cached-audit schema required')
    require(isinstance(report.get('cases'), list) and 0 < len(report['cases']) <= 12, '1..12 audit cases required')
    scope = report['scope']
    require(set(scope['metrics']) == set(METRICS) and 'volume-weighted' in scope['quantiles'] and
            'side=left' in scope['quantiles'] and 'unchanged' in scope['primary_ROI'], 'Weighted metric/primary-ROI definitions missing')
    pins = report['inputs_sha256']
    require(isinstance(pins, dict) and pins, 'Source input SHA manifest required')
    prereg = report['preregistration']
    require(prereg.get('verified_before_and_after') is True and pins.get(str(Path(prereg['path']).resolve())) == prereg['SHA256'],
            'Before/after preregistration SHA binding required')
    small, native = {}, {}
    for name, expected in pins.items():
        source = Path(name).resolve()
        require(isinstance(expected, str) and len(expected) == 64 and all(char in '0123456789abcdef' for char in expected), 'Valid SHA256 required')
        is_native = source.suffix in ('.npz', '.bin', '.gz') or source.name == 'grid.csv'
        if is_native:
            native[str(source)] = expected
            continue  # Never open/decode/query native scalar, grid, E orphi files.
        require(source.suffix in ('.json', '.properties', '.csv', '.py', '.java'), 'Unexpected input type; review source manifest')
        if verify_sources:
            require(source.is_file() and sha(source) == expected, 'Small source input SHA mismatch: '+str(source))
        small[str(source)] = expected
    for case in report['cases']:
        check_case(case)
        require(str(Path(case['summary_path']).resolve()) in small, 'Case summary must be a bound JSON input')
        probe = case['raw_probe_artifact_reference']
        require(pins.get(str(Path(probe['path']).resolve())) == probe['SHA256'], 'Raw unloaded probe SHA not bound to audit')
    require(sha(path) == report_sha, 'Audit JSON changed during source verification')
    return dict(path=str(path), SHA256=report_sha, report=report, verified_small_inputs=small,
        native_inputs_declared_not_opened=native, source_verification_performed=verify_sources)


def collect_cases(validated_reports):
    found = {}
    for audit in validated_reports:
        for case in audit['report']['cases']:
            key = str(Path(case['summary_path']).resolve())
            if key in found:
                require(digest(found[key]) == digest(case), 'Conflicting duplicate case: '+case['case_id'])
            else:
                found[key] = copy.deepcopy(case)
    return list(found.values())


def build_model(validated_reports):
    require(validated_reports and all(audit.get('source_verification_performed') is True for audit in validated_reports),
            'Actual small-source verification required for a display model')
    cases, cohorts, holds = collect_cases(validated_reports), {}, []
    for case in cases:
        case['viewer_id'] = case['run_id']+'/'+case['case_id']
        cohorts.setdefault(case['comparison_signature'], []).append(case)
    cohort_rows = []
    for signature, members in cohorts.items():
        by_path = {str(Path(case['summary_path']).resolve()): case for case in members}
        referenced = {str(Path(case['baseline_summary']).resolve()) for case in members}
        require(len(referenced) == 1, 'Ambiguous same-grid baseline for one cohort')
        baseline = by_path.get(next(iter(referenced)))
        if baseline is not None:
            require(baseline['circuit']['n_pads'] == 4 and baseline['circuit']['n_outputs'] == 2,
                    'Same-grid baseline must be four physical pads/two independent outputs')
        for case in members:
            case['baseline_present'] = baseline is not None
            case['viewer_holds'] = [] if baseline else ['same-grid four-pad baseline row missing from supplied audits']
            if not baseline:
                holds.append(dict(case_id=case['case_id'], reason=case['viewer_holds'][0]))
        cohort_rows.append(dict(signature=signature, baseline_id=baseline['viewer_id'] if baseline else None,
            case_ids=[case['viewer_id'] for case in members], mesh=members[0]['mesh']))
    audits = [dict(path=audit['path'], SHA256=audit['SHA256'], scope=audit['report']['scope'],
        implementation_git_commit=audit['report'].get('implementation_git_commit'),
        implementation_file_SHA256=audit['report'].get('implementation_file_SHA256'),
        preregistration=audit['report']['preregistration'], verified_small_inputs=audit['verified_small_inputs'],
        native_inputs_declared_not_opened=audit['native_inputs_declared_not_opened']) for audit in validated_reports]
    return dict(schema='task1-volume-audit-view-model-v1', cases=cases, cohorts=cohort_rows, holds=holds, audits=audits,
        definitions=dict(primary_ROI=PRIMARY, supplemental_ROI=SLAB, metrics=list(METRICS), normalizations=list(MODES),
            scalar_units='V/m', volume_units='m3', hotspot_coordinates='mm; z=0 skin surface; +z depth',
            burden_units='J A/m2; contact V RMS; power W; physical-output current RMS mA',
            weighted_statistics='Native represented-volume weights; stable inverse ECDF side=left; no interpolation.',
            thresholds='Stored scaled scalar >= frozen raw same-grid four-pad baseline cutoff; all volumes already evaluated by the audit.',
            status='Calculated electrical proxies; primary ROI statistic regression only. No adoption, whole-3D convergence, experiment, physiology or safety certification.',
            native_hash_scope='Viewer hashes report and small input files only; native NPZ/grid/E/phi hashes are recorded audit provenance and are not re-read here.'))


SCRIPT = r'''
'use strict';
const model=JSON.parse(document.getElementById('report-data').textContent);
const ids=['cohort-select','roi-select','metric-select','normalization-select','cutoff-select'];
const $=id=>document.getElementById(id);
const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
const fmt=x=>x===null||x===undefined?'undefined':typeof x==='number'?Number(x).toPrecision(7):String(x);
function link(path,label){const a=el('a',label);a.href=path;return a;}
function table(headers,rows){const t=el('table'),head=el('tr');headers.forEach(x=>head.append(el('th',x)));t.append(head);rows.forEach(row=>{const tr=el('tr');row.forEach(x=>tr.append(el('td',fmt(x))));t.append(tr);});return t;}
function fill(id,options){options.forEach(([value,label])=>{const o=el('option',label);o.value=value;$(id).append(o);});}
fill('cohort-select',model.cohorts.map((c,i)=>[c.signature,`${i+1}: XY${c.mesh.h_xy_mm} mm / SC${c.mesh.sc_cells} / bulk ${c.mesh.bulk_layer_counts.join(',')}`]));
fill('roi-select',[[model.definitions.primary_ROI,'PRIMARY: central r≤5mm, depth15–20mm (unchanged)'],[model.definitions.supplemental_ROI,'SUPPLEMENT: whole modeled XY, depth15–20mm']]);
fill('metric-select',[['maxTIS','maxTIS: fundamental sampled-direction maximum'],['fixedTIS','fixedTIS: fundamental (X+Y)/√2 direction'],['RMS','RMS: full4-line vector field; not modulation']]);
fill('normalization-select',[['raw_1Vpp','1. Raw1Vpp/output'],['equal_total_source_output_RMS_sum','2. Equal sum of two output RMS currents'],['equal_total_power','3. Equal total source power'],['skin_contact_only','4. Skin/contact8 caps; no power/1Vpp ceiling'],['legacy_composite_full_skin','5. Legacy full skin:8 caps +source power +1Vpp ceiling']]);
const cutoffs=[model.definitions.primary_ROI+'_mean',model.definitions.primary_ROI+'_p10',model.definitions.supplemental_ROI+'_mean',model.definitions.supplemental_ROI+'_p10'];
fill('cutoff-select',cutoffs.map(x=>[x,x+' (frozen raw same-grid baseline)']));
function update(){const cohort=model.cohorts.find(c=>c.signature===$('cohort-select').value),roi=$('roi-select').value,metric=$('metric-select').value,norm=$('normalization-select').value,cutoff=$('cutoff-select').value;
 const members=cohort.case_ids.map(id=>model.cases.find(c=>c.viewer_id===id)),base=members.find(c=>c.viewer_id===cohort.baseline_id),complement=roi===model.definitions.primary_ROI?'primary_complement':'supplemental_complement';
 $('baseline-banner').replaceChildren();if(base){const n=base.normalizations[norm],s=n.regions[roi][metric];$('baseline-banner').append(el('b',`Always-visible SAME-GRID4-pad baseline: ${base.case_id}`),el('p',`${roi}; ${metric}; ${norm}. Absolute mean ${fmt(s.mean)} V/m, P10 ${fmt(s.p10)} V/m; source ${fmt(n.source_Vpp_per_output)} Vpp/output;2 outputs/common return. Geometric/mesh success is not inferred.`));}else{$('baseline-banner').append(el('b','HELD: same-grid four-pad baseline row missing. No baseline values invented.'));}
 $('results').replaceChildren();const rows=[];
 members.forEach(c=>{const n=c.normalizations[norm],s=n.regions[roi][metric],off=n.regions[complement][metric],surface=n.regions.surface_0_5[metric],global=n.regions.total[metric],high=s.fixed_baseline_threshold_volume[cutoff],oh=off.fixed_baseline_threshold_volume[cutoff],gh=global.fixed_baseline_threshold_volume[cutoff];
 rows.push([c.case_id,c.circuit.n_pads,c.circuit.n_outputs,s.mean,s.p10,s.CV,s.p10_over_mean,s.max,s.volume_m3,surface.p95,off.p95,global.max,global.hotspot.center_xyz_mm.join(', '),global.hotspot.layer,high.cutoff_V_m,high.volume_m3,high.region_volume_fraction,oh.volume_m3,gh.volume_m3]);});
 [4,8,12,16].filter(n=>!members.some(c=>c.circuit.n_pads===n)).forEach(n=>rows.push([`${n}pads: no supplied same-grid audit`,n,2,...Array(16).fill('unavailable')]));
 $('results').append(table(['Case','pads','outputs','ROI mean V/m','ROI P10 V/m','CV','P10/mean','ROI max V/m','ROI m³','z0–5 P95 V/m','non-target P95 V/m','global max V/m','global hotspot X,Y,+z mm','layer','frozen cutoff V/m','ROI >=cutoff m³','ROI >= fraction','non-target >=m³','whole phantom >=m³'],rows));
 $('burdens').replaceChildren();const br=members.map(c=>{const n=c.normalizations[norm],b=n.normalized_burdens;return[c.case_id,n.source_Vpp_per_output,n.source_output_RMS_by_output_mA.join(', '),n.sum_source_output_RMS_mA,b.source_power_W,b.SC_power_W,b.skin_SC_plus_dermis_power_W,b.contact_power_W,b.surface_J_RMS_max_A_m2,b.surface_J_RMS_p95_A_m2,b.bulk_skin_J_vector_RMS_max_A_m2,b.bulk_skin_J_vector_RMS_p95_A_m2,b.contact_voltage_RMS_max_V,n.active_skin_contact_caps.join(', ')||'none equal to this scale',n.includes_source_power_cap,n.includes_1Vpp_ceiling];});
 $('burdens').append(table(['Case','Vpp/output','output RMS mA each','RMS mA sum (bookkeeping)','source W','SC W','SC+dermis W','contact W','contact Jmax A/m²','contact J95 A/m²','skin-volume Jmax A/m²','skin-volume J95 A/m²','contact RMS V','active skin/contact caps','source power cap','1Vpp ceiling'],br));
 $('evidence').replaceChildren();members.forEach(c=>{const d=el('details'),summary=el('summary',c.case_id+' — source / circuit / status / unloaded native-phi probes');d.append(summary);
 const meta={run_id:c.run_id,source_commit:c.source_commit,configuration_sha256:c.configuration_sha256,physical_model_version:c.physical_model_version,mesh:c.mesh,circuit:c.circuit,calculation:c.calculation_status,numerical_validation:c.numerical_validation_status,experimental_validation:c.experimental_validation_status,primary_ROI_reproduction:c.primary_ROI_reproduction,viewer_holds:c.viewer_holds,normalization:c.normalizations[norm].interpretation};
 const pre=el('pre',JSON.stringify(meta,null,2));d.append(pre);d.append(link(c.links.summary,'Source summary JSON'),el('span',' · '),link(c.links.probe,'UNLOADED native complex-phi probe JSON'),el('p','No new Vpp, instrument loading or physiological equivalence was calculated by this viewer.'));$('evidence').append(d);});
 $('quantity').textContent=metric==='RMS'?'Threshold volume means high field RMS volume; it is not TIS modulation volume.':'Threshold volume means high fundamental TIS modulation volume; not activation volume.';
}
ids.forEach(id=>$(id).addEventListener('change',update));update();
'''


def relative(path, output):
    return quote(os.path.relpath(Path(path).resolve(), Path(output).resolve().parent), safe='/')


def render_html(model, output_path, common_maps_path):
    data = copy.deepcopy(model)
    for case in data['cases']:
        case['links'] = dict(summary=relative(case['summary_path'], output_path),
            probe=relative(case['raw_probe_artifact_reference']['path'], output_path))
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    script_hash = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    esc = html.escape
    sources = ''.join('<li><a href="'+relative(audit['path'], output_path)+'">'+esc(audit['path'])+'</a> SHA256 '+esc(audit['SHA256'])+'</li>' for audit in model['audits'])
    controls = ''.join('<label>'+label+'<select id="'+key+'"></select></label>' for key, label in (
        ('cohort-select', 'Same-grid cohort'), ('roi-select', 'ROI'), ('metric-select', 'Metric'),
        ('normalization-select', 'Normalization'), ('cutoff-select', 'Frozen baseline cutoff')))
    css = 'body{font:14px/1.5 system-ui;color:#183047;background:#f8fafb;margin:24px}label{display:inline-flex;flex-direction:column;margin:8px}select{max-width:420px;padding:6px}aside{position:sticky;top:0;background:#e8f2fa;padding:12px;border-left:5px solid #21668f;z-index:2}section{overflow:auto;background:white;padding:12px;margin:16px 0}table{border-collapse:collapse;white-space:nowrap;font-size:12px}td,th{padding:7px;border-bottom:1px solid #d9e2e8;text-align:right}td:first-child,th:first-child{text-align:left}th{background:#e7edf3}pre{font-size:11px;white-space:pre-wrap;overflow-wrap:anywhere}details{padding:10px;border:1px solid #dae2e8;margin:10px 0}a{color:#165e94}'
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+\
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'sha256-'+script_hash+'\'; style-src \'unsafe-inline\'">'+\
        '<title>Task1 cached volume audit</title><style>'+css+'</style><body><h1>Task1 · Native volume audit</h1>'+\
        '<p>Primary ROI remains central r≤5mm, depth15–20mm. Whole modeled XY at that depth is a separate supplement. D50mm; layers0.1/5/5/15mm; top pads,2 outputs/common return/50Ω. '+\
        'All numbers below are already-computed audit values in V/m, m³, A/m², W and mA. No normalization, threshold classification, native-field query or PDE runs in this page.</p>'+\
        '<p>Volume weights: fractional central ROI; exact face-clipped depth overlap; whole modeled XY uses native staircase cells, without ideal-cylinder renormalization. Quantiles: stable inverse volume-weighted ECDF, side=left. '+\
        'Fundamental-only maxTIS/fixedTIS and full4-line E RMS are different quantities. fixedTIS uses direction(1/√2,1/√2,0). '+\
        'maxTIS uses2074 sampled directions, a lower bound to the continuous-direction maximum. RMS includes both fundamentals and both third harmonics; each source frequency is recorded below. '+\
        'A hotspot at a tissue interface is not evidence of deep concentration. Numerical burden/cutoff values are not human safety or activation limits.</p>'+\
        '<p>Only reports and small input hashes were checked by this viewer. Native NPZ/grid/E/phi bytes were not opened; their hashes retain the original audit provenance. Mesh convergence, experiment and adoption remain unvalidated.</p>'+\
        '<p><a href="'+relative(common_maps_path, output_path)+'">Existing common-scale maps</a> — use that screen’s original units/normalizations (V/cm); this viewer uses stored V/m. These selectors do not create or rescale maps.</p>'+\
        '<div>'+controls+'</div><aside id="baseline-banner"></aside><p id="quantity"></p><h2>Absolute ROI / non-target / hotspot / >=fixed-cutoff volume</h2><section id="results"></section>'+\
        '<h2>Source drive and separate burdens</h2><p>Equal current uses the sum of the two output RMS currents, including passive-frequency currents. It is bookkeeping, not common-GND return current. '+\
        'Skin/contact-only has8 caps without source-power or1Vpp ceilings; legacy composite adds both. A scale above1 is a numerical comparison, not a stimulation recommendation.</p><section id="burdens"></section>'+\
        '<h2>Source, grid, wiring, validation and UNLOADED probe references</h2><p>Relative artifact links refer to the original local repository and native data; a copied HTML or GitHub page may not provide those local files.</p><div id="evidence"></div><h2>Input audit receipts</h2><ul>'+sources+'</ul>'+\
        '<noscript>JavaScript is required only to select stored values. No external script or network connection is used.</noscript>'+\
        '<script type="application/json" id="report-data">'+encoded+'</script><script>'+SCRIPT+'</script></body></html>'


def implementation_identity():
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, timeout=5).strip()
    committed = subprocess.check_output(['git', 'show', commit+':tools/task1_volume_audit_view.py'], cwd=ROOT, timeout=5)
    require(committed == Path(__file__).read_bytes(), 'Commit the reviewed new viewer before rendering')
    return dict(source_commit=commit, implementation_file=str(Path(__file__).resolve()), implementation_SHA256=sha(__file__))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--common-maps', type=Path, default=ROOT/'docs/CLOUD_RESULTS.html')
    args = parser.parse_args()
    output = args.output.resolve()
    receipt_path, failure_path = output.with_suffix('.receipt.json'), output.with_suffix('.failure.json')
    require(output.suffix == '.html' and not any(path.exists() for path in (output, receipt_path, failure_path)), 'Fresh HTML/receipt paths required; preserve previous outputs')
    require(0 < len(args.audit) <= 12 and len(set(path.resolve() for path in args.audit)) == len(args.audit), '1..12 unique audit files required')
    implementation = implementation_identity()
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger_path = ROOT/'runtime/task1-budget.json'
        ledger = read(ledger_path)
        require(ledger['limit_seconds'] == 6600 and type(ledger['spent_seconds']) in (int, float) and
            math.isfinite(ledger['spent_seconds']) and 0 <= ledger['spent_seconds'] < 6600, 'Existing6600s ledger must remain unchanged')
        seconds = min(120., 6600-ledger['spent_seconds'])
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        current_soft, current_hard = resource.getrlimit(resource.RLIMIT_AS)
        address_limit = min(3*GIB, current_hard) if current_hard != resource.RLIM_INFINITY else 3*GIB
        resource.setrlimit(resource.RLIMIT_AS, (address_limit, current_hard))
        ancestor = output.parent
        while not ancestor.exists():
            ancestor = ancestor.parent
        require(shutil.disk_usage(ancestor).free >= 2*GIB+50*1024**2, 'Preserve2GiB reserve plus50MiB output allowance')
        output.parent.mkdir(parents=True, exist_ok=True)
        started, status = time.monotonic(), 'failed'
        def timeout(signum, frame):
            raise TimeoutError('Finite120s/remaining6600s JSON-view deadline exceeded')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        try:
            audits = [validate_audit(path) for path in args.audit]
            model = build_model(audits)
            document = render_html(model, output, args.common_maps)
            require(len(document.encode()) < 50*1024**2-128*1024, 'Standalone view exceeds50MiB allowance')
            require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= 3*GIB, 'Viewer exceeded3GiB RSS')
            require(implementation_identity() == implementation, 'Viewer source/HEAD changed')
            for audit in audits:
                require(sha(audit['path']) == audit['SHA256'], 'Audit JSON changed during display assembly')
                for path, expected in audit['verified_small_inputs'].items():
                    require(sha(path) == expected, 'Small source changed during display assembly')
            with output.open('x') as stream:
                stream.write(document)
            receipt = dict(schema='task1-volume-audit-view-receipt-v1', status='rendered_precomputed_JSON_only',
                created_utc=datetime.now(timezone.utc).isoformat(), **implementation,
                output=dict(path=str(output), SHA256=sha(output), bytes=output.stat().st_size),
                audit_inputs=[{key: value for key, value in audit.items() if key != 'report'} for audit in audits],
                case_count=len(model['cases']), cohort_count=len(model['cohorts']), holds=model['holds'],
                common_maps=dict(path=str(args.common_maps.resolve()), exists=args.common_maps.is_file(),
                    SHA256=sha(args.common_maps) if args.common_maps.is_file() else None, meaning='existing maps only; selectors do not rescale maps'),
                new_PDE=0, new_volume_analysis=0, source_inputs_unchanged=True,
                resources=dict(wall_seconds=time.monotonic()-started, max_seconds=seconds, CPU_count=1,
                    peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024, output_limit_bytes=50*1024**2,
                    global_limit_seconds=6600, minimum_reserve_bytes=2*GIB))
            text = json.dumps(receipt, indent=2, allow_nan=False)+'\n'
            require(output.stat().st_size+len(text.encode()) <= 50*1024**2, 'HTML and receipt exceed50MiB cap')
            require(shutil.disk_usage(output.parent).free >= 2*GIB+len(text.encode()), 'Receipt would violate2GiB reserve')
            with receipt_path.open('x') as stream:
                stream.write(text)
            status = receipt['status']
            print(json.dumps(dict(status=status, output=str(output), receipt=str(receipt_path), cases=len(model['cases']), new_PDE=0)))
        except BaseException as error:
            with failure_path.open('x') as stream:
                json.dump(dict(status='failed', error_type=type(error).__name__, error=str(error),
                    partial_evidence_preserved=True, new_PDE=0, new_volume_analysis=0), stream, indent=2)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-started
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=output.stem, stage='precomputed_volume_audit_view', status=status,
                seconds=elapsed, finished_utc=datetime.now(timezone.utc).isoformat()))
            temporary = ledger_path.with_name(ledger_path.name+'.partial')
            temporary.write_text(json.dumps(ledger, indent=2)+'\n')
            temporary.replace(ledger_path)


if __name__ == '__main__':
    main()
