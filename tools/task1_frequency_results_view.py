#!/usr/bin/env python3
"""Offline JSON-only viewer for two completed actual-frequency sine results.

No native arrays, field reconstruction, new normalization, research imports,
simulation, external requests or resource-ledger changes occur in this viewer.
"""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import html
import json
import math
import os
from pathlib import Path
import time
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = 'primary_r5_depth15_20'
SLAB = 'supplemental_wholeXY_depth15_20'
REGIONS = ('total', PRIMARY, SLAB, 'surface_0_5', 'primary_complement', 'supplemental_complement')
METRICS = ('maxTIS', 'fixedTIS', 'RMS')
COHORTS = ('cached_original_square_3000_3030_caps', 'fresh_sine_3000_3030_caps')
MODES = ('raw_sine_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power',
         'skin_contact_only', 'legacy_composite_full_skin')
BURDENS = ('surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2', 'contact_voltage_RMS_max_V',
    'SC_power_W', 'contact_power_W', 'source_power_W', 'bulk_skin_J_vector_RMS_max_A_m2',
    'bulk_skin_J_vector_RMS_p95_A_m2', 'skin_SC_plus_dermis_power_W')
PAIRS = ((3000, 3030), (9000, 9090))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    path = Path(path).resolve()
    require(path.suffix == '.json' and path.is_file() and path.stat().st_size <= 20*1024**2,
            'Only existing JSON inputs <=20MiB are supported')
    before = sha(path)
    value = json.loads(path.read_text())
    finite_tree(value)
    require(sha(path) == before, 'JSON input changed while reading')
    return value, dict(path=str(path), SHA256=before)


def finite_tree(value):
    if isinstance(value, float):
        require(math.isfinite(value), 'Nonfinite precomputed value')
    elif isinstance(value, dict):
        for item in value.values():
            finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            finite_tree(item)


def bound_json(reference):
    value, proof = read_json(reference['path'])
    require(proof['SHA256'] == reference['SHA256'], 'JSON artifact SHA mismatch: '+proof['path'])
    return value, proof


def check_circuit(circuit):
    require(circuit['n_pads'] == 4 and circuit['n_outputs'] == 2 and circuit['n_return_nodes'] == 1 and
        circuit['source_resistance_ohm'] == 50 and circuit['pad_to_node'] ==
        {'0': 'out0', '1': 'out1', '2': 'GND', '3': 'GND'}, 'Four physical pads/two outputs/common GND/50ohm required')


def check_mode(mode, raw_probe_ids=None):
    require(set(mode['normalized_burdens']) == set(BURDENS) and
        set(mode['baseline_derived_numerical_limits']) == set(BURDENS), 'All nine stored burden/limit metrics required')
    require(len(mode['source_Vpp_by_output']) == len(mode['source_output_RMS_by_output_mA']) == 2,
            'Explicit two-output source voltage/current required')
    require(set(mode['regions']) == set(REGIONS), 'Six precomputed regions required')
    for metrics in mode['regions'].values():
        require(set(metrics) == set(METRICS), 'Three distinct stored field metrics required')
        for stats in metrics.values():
            require(all(key in stats for key in ('mean', 'p10', 'p95', 'max', 'CV', 'p10_over_mean',
                'volume_m3', 'hotspot', 'fixed_baseline_threshold_volume')), 'Stored absolute/weighted volume statistics required')
    if raw_probe_ids is not None:
        require(len(mode['probe40_unloaded']) == 40 and {row['id'] for row in mode['probe40_unloaded']} == raw_probe_ids,
                'All40 precomputed unloaded probe rows required for every normalization')


def load_model(summary_path, baseline_audit_path, old_gui_path):
    summary, summary_proof = read_json(summary_path)
    require(summary['schema'] == 'task1-frequency-resynthesis-audit-v1' and
        summary['status'] == 'calculated_unadopted' and summary['new_PDE'] == 0 and
        summary['inputs_unchanged'] is True and summary['candidate_adopted'] is False and
        summary['actual_frequency_pairs'] == [list(pair) for pair in PAIRS] and
        summary['actual_beat_frequencies_Hz'] == [30, 90] and len(summary['conditions']) == 2,
        'Exactly two completed, unadopted actual-frequency sine conditions required')
    audit, audit_proof = read_json(baseline_audit_path)
    require(audit['schema'] == 'task1-volume-selectivity-v1' and audit['status'] == 'calculated_unadopted' and
        audit['inputs_unchanged'] is True, 'Completed square-baseline volume audit required')
    proofs = [summary_proof, audit_proof]
    if 'preregistration' in summary:
        _, proof = bound_json(summary['preregistration']); proofs.append(proof)
    conditions, source = [], None
    declared_native = []
    for reference, pair in zip(summary['conditions'], PAIRS):
        require(reference['actual_fundamental_Hz'] == list(pair) and reference['beat_frequency_Hz'] == pair[1]-pair[0],
                'Carrier and beat metadata do not match')
        condition, proof = bound_json(reference['artifacts']['condition.json']); proofs.append(proof)
        probes, proof = bound_json(reference['artifacts']['probes.json']); proofs.append(proof)
        require(condition['schema'] == 'task1-frequency-resynthesis-condition-v1' and
            condition['status'] == 'calculated_unadopted' and condition['id'] == reference['id'] and
            condition['actual_fundamental_Hz'] == list(pair) and condition['beat_frequency_Hz'] == pair[1]-pair[0] and
            condition['waveform'] == 'sine' and condition['new_PDE'] == 0 and
            condition['candidate_adopted'] is False and condition['instrument_loading_validated'] is False,
            'Completed unloaded pure-sine condition identity required')
        provenance = condition['source_provenance']; check_circuit(provenance['circuit'])
        require(provenance['case_id'] == 'baseline-square15-xy80', 'Original four-square-pad geometry required')
        if source is None:
            source = copy.deepcopy(provenance)
        else:
            require(provenance == source, 'Both conditions must use the same square native source')
        require(probes['status'] == 'complete' and probes['unloaded_prediction'] is True and
            probes['actual_fundamental_Hz'] == list(pair) and len(probes['measurements']) == 40 and
            probes['measurement_grid']['tip_gap_mm'] == 5,
            'Completed actual-frequency unloaded40-probe JSON required')
        measurements = probes['measurements']; probe_ids = {row['id'] for row in measurements}
        require(len(probe_ids) == 40 and all(row['tip_gap_mm'] == 5 for row in measurements) and
            {row['depth_from_skin_surface_mm'] for row in measurements} == {5, 10, 15, 20} and
            {row['axis'] for row in measurements} == {'X', 'Y'}, 'Four depths/two horizontal axes/5mm tip gap required')
        require(set(condition['cohorts']) == set(COHORTS), 'Both separately named cap-reference cohorts required')
        for cohort in condition['cohorts'].values():
            require(set(cohort['normalizations']) == set(MODES), 'All five stored normalizations required')
            for mode in cohort['normalizations'].values():
                check_mode(mode, probe_ids)
        conditions.append(dict(condition=condition, probe_metadata=[{key: row[key] for key in
            ('id', 'depth_from_skin_surface_mm', 'position', 'axis', 'centre_mm', 'plus_mm', 'minus_mm', 'tip_gap_mm')}
            for row in measurements], artifacts=copy.deepcopy(reference['artifacts'])))
        for name, item in reference['artifacts'].items():
            if not name.endswith('.json'):
                declared_native.append(copy.deepcopy(item))  # No native file is opened or byte-hashed here.
    source_path = str(Path(source['source_summary']).resolve())
    require(Path(source_path).suffix == '.json', 'Source summary must be JSON; native inputs are never opened')
    require(summary['input_sha256'].get(source_path) == sha(source_path), 'Source summary SHA is not bound to frequency audit')
    proofs.append(dict(path=source_path, SHA256=summary['input_sha256'][source_path]))
    baselines = [case for case in audit['cases'] if str(Path(case['summary_path']).resolve()) == source_path]
    require(len(baselines) == 1, 'One exact original-square baseline must be supplied')
    baseline = copy.deepcopy(baselines[0]); check_circuit(baseline['circuit'])
    require(baseline['case_id'] == source['case_id'] and all(
        item['condition']['cohorts'][COHORTS[0]]['reference_id'] == baseline['condition_id'] for item in conditions),
        'Historical square cap cohort must identify the displayed original square baseline')
    raw = copy.deepcopy(baseline['normalizations']['raw_1Vpp'])
    raw['source_Vpp_by_output'] = [raw['source_Vpp_per_output']]*2
    check_mode(raw)
    baseline['raw_display'] = raw
    return dict(schema='task1-frequency-results-view-model-v1', conditions=conditions, baseline=baseline,
        source=source, input_proofs=proofs, native_artifacts_declared_not_opened=declared_native,
        summary_metadata={key: copy.deepcopy(value) for key, value in summary.items() if key not in
            ('conditions', 'input_sha256', 'implementation_files_sha256')}, old_gui_path=str(Path(old_gui_path).resolve()),
        cohorts=list(COHORTS), normalizations=list(MODES), metrics=list(METRICS), rois=[PRIMARY, SLAB])


SCRIPT = r'''
'use strict';
const data=JSON.parse(document.getElementById('view-data').textContent), $=id=>document.getElementById(id);
const node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
const fmt=x=>x===null||x===undefined?'undefined':typeof x==='number'?x.toPrecision(7):String(x);
function fill(id,rows){rows.forEach(([v,label])=>{const n=node('option',label);n.value=v;$(id).append(n);});}
function table(headers,rows){const t=node('table'),h=node('tr');headers.forEach(x=>h.append(node('th',x)));t.append(h);rows.forEach(row=>{const tr=node('tr');row.forEach(x=>tr.append(node('td',fmt(x))));t.append(tr);});return t;}
fill('cohort-select',data.cohorts.map(x=>[x,x]));
fill('roi-select',data.rois.map((x,i)=>[x,i?'Supplement: whole XY, depth15–20mm':'Primary: r≤5mm, depth15–20mm']));
fill('metric-select',[['maxTIS','maxTIS · sampled direction maximum'],['fixedTIS','fixedTIS · (X+Y)/√2'],['RMS','E vector RMS · not modulation']]);
fill('normalization-select',data.normalizations.map(x=>[x,x]));
function bars(id,rows,limit,title){const host=$(id);host.replaceChildren(node('h3',title),node('p',`Common axis:0–${fmt(limit)} V/m for all displayed conditions and normalizations.`));
 rows.forEach(([label,value,color])=>{const line=node('div');line.className='bar-row';line.append(node('span',label));const bar=node('div');bar.className='track';const inner=node('div');inner.style.width=(limit?100*value/limit:0)+'%';inner.style.background=color;bar.append(inner);line.append(bar,node('b',fmt(value)+' V/m'));host.append(line);});}
function update(){const cohort=$('cohort-select').value,roi=$('roi-select').value,metric=$('metric-select').value,norm=$('normalization-select').value;
 const base=data.baseline.raw_display,ref=data.conditions[0].condition.cohorts[cohort];
 $('baseline').textContent=`Always shown: original4-square-pad baseline ${data.baseline.condition_id}; RAW1Vpp/output,3000/3030Hz +third harmonics. ROImean ${fmt(base.regions[roi][metric].mean)},P10 ${fmt(base.regions[roi][metric].p10)} V/m. Historical raw anchor; it is not renormalized to the fresh-sine cohort.`;
 $('reference').textContent=`Selected cap/current/power reference: ${ref.reference_id}, ${ref.reference_waveform}, ${ref.reference_actual_fundamental_Hz.join('/')}Hz. Frozen scalar-volume cutoffs always come from the original square baseline.`;
 const rows=[['Historical square RAW anchor',base,null]],colors=['#7a8794','#147ca0','#b65237'];
 data.conditions.forEach(item=>rows.push([item.condition.id,item.condition.cohorts[cohort].normalizations[norm],item]));
 let roiLimit=0,offLimit=0;const modes=[base];data.conditions.forEach(item=>data.cohorts.forEach(c=>data.normalizations.forEach(n=>modes.push(item.condition.cohorts[c].normalizations[n]))));
 modes.forEach(m=>{roiLimit=Math.max(roiLimit,m.regions[roi][metric].mean,m.regions[roi][metric].p10);offLimit=Math.max(offLimit,m.regions.surface_0_5[metric].p95,m.regions[roi===data.rois[0]?'primary_complement':'supplemental_complement'][metric].p95);});
 bars('roi-bars',rows.flatMap(([id,m],i)=>[[id+' mean',m.regions[roi][metric].mean,colors[i]],[id+' P10',m.regions[roi][metric].p10,colors[i]]]),roiLimit,'Stored absolute ROI mean / P10');
 const off=roi===data.rois[0]?'primary_complement':'supplemental_complement';
 bars('off-bars',rows.flatMap(([id,m],i)=>[[id+' z0–5P95',m.regions.surface_0_5[metric].p95,colors[i]],[id+' non-targetP95',m.regions[off][metric].p95,colors[i]]]),offLimit,'Stored superficial / non-target P95');
 $('statistics').replaceChildren(table(['Condition','drive Vpp each','ROI mean V/m','P10 V/m','CV','P10/mean','max V/m','surfaceP95 V/m','non-targetP95 V/m','globalmax V/m','hotspot X,Y,+depth mm','layer','ROI>=original mean m³','non-target>=original mean m³'],rows.map(([id,m])=>{const r=m.regions[roi][metric],g=m.regions.total[metric],key=roi+'_mean';return[id,m.source_Vpp_by_output.join(', '),r.mean,r.p10,r.CV,r.p10_over_mean,r.max,m.regions.surface_0_5[metric].p95,m.regions[off][metric].p95,g.max,g.hotspot.center_xyz_mm.join(', '),g.hotspot.layer,r.fixed_baseline_threshold_volume[key].volume_m3,m.regions[off][metric].fixed_baseline_threshold_volume[key].volume_m3];})));
 $('burdens').replaceChildren(table(['Condition','output RMS mA each','RMS mA sum','source W','SC W','SC+dermis W','contact W','contactJmax A/m²','contactJ95 A/m²','skin-volumeJmax A/m²','skin-volumeJ95 A/m²','contact RMS V','active skin/contact caps','source power cap','1Vpp ceiling'],rows.map(([id,m])=>{const b=m.normalized_burdens;return[id,m.source_output_RMS_by_output_mA.join(', '),m.sum_source_output_RMS_mA,b.source_power_W,b.SC_power_W,b.skin_SC_plus_dermis_power_W,b.contact_power_W,b.surface_J_RMS_max_A_m2,b.surface_J_RMS_p95_A_m2,b.bulk_skin_J_vector_RMS_max_A_m2,b.bulk_skin_J_vector_RMS_p95_A_m2,b.contact_voltage_RMS_max_V,m.active_skin_contact_caps.join(', '),m.includes_source_power_cap,m.includes_1Vpp_ceiling];})));
 $('probes').replaceChildren();data.conditions.forEach(item=>{const c=item.condition,m=c.cohorts[cohort].normalizations[norm],meta=Object.fromEntries(item.probe_metadata.map(p=>[p.id,p]));const detail=node('details');detail.append(node('summary',c.id+' ·40 UNLOADED probes ·5mm tip gap'));detail.append(table(['ID','depth mm','centre X,Y,+z mm','axis','tip gap mm','RMS V','Vpp lower V','Vpp upper V','fundamental envelope variation V'],m.probe40_unloaded.map(r=>[r.id,meta[r.id].depth_from_skin_surface_mm,meta[r.id].centre_mm.join(', '),meta[r.id].axis,meta[r.id].tip_gap_mm,r.RMS_V,r.Vpp_lower_V,r.Vpp_upper_V,r.fundamental_envelope_variation_V])));$('probes').append(detail);});
}
['cohort-select','roi-select','metric-select','normalization-select'].forEach(id=>$(id).addEventListener('change',update));update();
'''


def relative(path, output):
    return quote(os.path.relpath(Path(path).resolve(), Path(output).resolve().parent), safe='/')


def render_html(model, output_path):
    encoded = json.dumps(model, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    csp = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    esc = html.escape
    links = []
    for proof in model['input_proofs']:
        links.append('<li><a href="'+relative(proof['path'], output_path)+'">'+esc(Path(proof['path']).name)+'</a> SHA256 '+esc(proof['SHA256'])+'</li>')
    source = model['source']
    metadata = {key: source[key] for key in ('run_id', 'case_id', 'source_commit', 'configuration_sha256', 'circuit')}
    css = 'body{max-width:1500px;margin:24px auto;padding:0 20px;background:#f7fafc;color:#183047;font:14px/1.5 system-ui}select{max-width:370px;padding:7px;margin:5px}aside{position:sticky;top:0;background:#e8f2fa;border-left:5px solid #24769a;padding:12px;z-index:2}section{background:white;padding:14px;margin:14px 0;overflow:auto}table{border-collapse:collapse;white-space:nowrap;font-size:12px}td,th{padding:7px;border-bottom:1px solid #d8e2e9;text-align:right}td:first-child,th:first-child{text-align:left}th{background:#e7eef4}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px}a{color:#1a6591}.bar-row{display:grid;grid-template-columns:minmax(190px,310px) minmax(120px,1fr) 130px;align-items:center;gap:8px;margin:9px 0;font-size:12px}.track{height:17px;background:#e6edf2}.track div{height:17px}details{margin:12px 0}footer{font-size:12px}'
    controls = ''.join('<label>'+name+' <select id="'+key+'"></select></label>' for key, name in (
        ('cohort-select', 'Cap reference'), ('roi-select', 'ROI'), ('metric-select', 'Metric'), ('normalization-select', 'Normalization')))
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+\
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'sha256-'+csp+'\'; style-src \'unsafe-inline\'">'+\
        '<title>Task1 · actual-frequency sine comparison</title><style>'+css+'</style><body><h1>Task1 · Actual-frequency pure-sine comparison</h1>'+\
        '<p>3000/3030Hz (30Hz beat) versus9000/9090Hz (90Hz beat). Carrier and beat both change; this is not a carrier-only experiment or physiological-equivalence comparison. '+\
        'Same original4-square-pad geometry,2 independent outputs/common GND/50Ω; fixed D50mm and0.1/5/5/15mm layers. Values are precomputed, not recomputed by this page.</p>'+\
        '<p>Primary ROI:r≤5mm,depth15–20mm. WholeXY at that depth is supplemental. All field tables/bars use V/m; burdens use A/m²,V RMS,W,mA. '+\
        'maxTIS is a2074-direction sampled maximum; fixedTIS uses(X+Y)/√2; RMS is not TIS modulation. Here both active sine carriers are included in RMS.</p>'+\
        '<p><b>Calculated and unadopted.</b> Existing SC/XY/bulk/contact convergence holds remain; no new C1 control, instrument-loaded prediction, experimental validation or safety certification. '+\
        'Skin/contact-only can exceed1Vpp numerically; legacy composite additionally caps source power and1Vpp. Current sum is output-RMS bookkeeping, not common-return current.</p>'+\
        '<p><a href="'+relative(model['old_gui_path'], output_path)+'">Existing37-case/4–8–12–16-pad GUI</a> (unchanged). '+\
        'This new screen contains shared-axis scalar bars, not new-frequency spatial maps. Old maps must not be relabeled as these sine results.</p>'+\
        '<div>'+controls+'</div><aside id="baseline"></aside><p id="reference"></p><section id="roi-bars"></section><section id="off-bars"></section>'+\
        '<h2>Absolute target and non-target statistics</h2><section id="statistics"></section><h2>Drive and separate burdens</h2><section id="burdens"></section>'+\
        '<h2>Native complex-phi probe predictions</h2><p>Each condition has40 stored rows:depth5/10/15/20mm ×5 cross-shaped centre positions ×X/Y differential axes. '+\
        'Tip gap is5mm; centre position is separate. Vpp bounds,RMS and fundamental-envelope variation below are UNLOADED. Raw probe JSON links retain spectra; no loaded/scope-calibration claim.</p><section id="probes"></section>'+\
        '<h2>Source and evidence</h2><pre>'+esc(json.dumps(metadata, ensure_ascii=False, indent=2))+'</pre><ul>'+''.join(links)+'</ul>'+\
        '<details><summary>Recorded completion, holds and resources</summary><pre>'+esc(json.dumps(model['summary_metadata'], ensure_ascii=False, indent=2))+'</pre></details>'+\
        '<footer>Offline JSON-only display; source JSON SHAs verified. Native arrays were not opened or byte-hashed. No new numerical postprocessing, normalization, PDE or budget-ledger mutation.</footer>'+\
        '<script type="application/json" id="view-data">'+encoded+'</script><script>'+SCRIPT+'</script></body></html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--baseline-audit', type=Path, required=True)
    parser.add_argument('--old-gui', type=Path, default=ROOT/'docs/CLOUD_VOLUME_RESULTS_20261021_v6.html')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); started = time.monotonic(); output = args.output.resolve()
    receipt = output.with_suffix('.receipt.json')
    require(output.suffix == '.html' and output.parent.is_dir() and not output.exists() and not receipt.exists(),
            'Fresh HTML/receipt in an existing directory required')
    model = load_model(args.summary, args.baseline_audit, args.old_gui)
    document = render_html(model, output)
    require(len(document.encode()) <= 10*1024**2, 'JSON-only GUI exceeds10MiB display allowance')
    for proof in model['input_proofs']:
        require(sha(proof['path']) == proof['SHA256'], 'Source JSON changed during display assembly')
    with output.open('x') as stream:
        stream.write(document)
    result = dict(schema='task1-frequency-results-view-receipt-v1', status='rendered_precomputed_JSON_only',
        created_utc=datetime.now(timezone.utc).isoformat(), output=dict(path=str(output), SHA256=sha(output), bytes=output.stat().st_size),
        implementation=dict(path=str(Path(__file__).resolve()), SHA256=sha(__file__)), input_proofs=model['input_proofs'],
        native_artifacts_declared_not_opened=model['native_artifacts_declared_not_opened'], new_PDE=0,
        new_numerical_postprocessing=0, budget_ledger_modified=False, wall_seconds=time.monotonic()-started)
    with receipt.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status=result['status'], output=str(output), bytes=output.stat().st_size)))


if __name__ == '__main__':
    main()
