#!/usr/bin/env python3
"""JSON-only SC4 sine display with explicit SC2 reference/threshold context."""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import time

import task1_frequency_results_view as base

COHORTS = ('cached_SC4_square_3000_3030_caps', 'cached_SC2_square_3000_3030_caps',
           'fresh_sine_3000_3030_caps')


def load_model(summary_path, baseline_audit_path, sc2_model, overall_gui):
    summary, proof = base.read_json(summary_path)
    base.require(summary['schema']=='task1-frequency-sc4-sensitivity-audit-v1' and
        summary['status']=='calculated_unadopted' and summary['inputs_unchanged'] is True and
        summary['new_PDE']==0 and summary['candidate_adopted'] is False and summary['source_mesh_SC_cells']==4 and
        summary['actual_frequency_pairs']==[list(p)for p in base.PAIRS] and len(summary['conditions'])==2,
        'Completed two-condition SC4 sensitivity required')
    baseline_report, baseline_proof=base.read_json(baseline_audit_path)
    base.require(baseline_report['schema']=='task1-volume-selectivity-v1' and
        baseline_report['status']=='calculated_unadopted','Original SC4 square scalar report required')
    proofs=[proof,baseline_proof];conditions=[];native=[];source=None
    _,p=base.bound_json(summary['preregistration']);proofs.append(p)
    own,p=base.bound_json(summary['SC4_own_cutoff_reference']);proofs.append(p)
    base.require(own['schema']=='task1-SC4-own-cutoff-reference-v1' and
        own['SC4_own_cutoffs_used_for_high_volume_comparison'] is False,
        'Explicit unused own-SC4 versus fixed cross-SC2 threshold record required')
    for ref,pair in zip(summary['conditions'],base.PAIRS):
        c,p=base.bound_json(ref['artifacts']['condition.json']);proofs.append(p)
        probes,p=base.bound_json(ref['artifacts']['probes.json']);proofs.append(p)
        base.require(c['schema']=='task1-frequency-resynthesis-condition-v1' and c['status']=='calculated_unadopted' and
            c['id']==ref['id'] and c['actual_fundamental_Hz']==list(pair) and c['beat_frequency_Hz']==pair[1]-pair[0] and
            c['waveform']=='sine' and c['new_PDE']==0 and c['candidate_adopted'] is False and
            c['instrument_loading_validated'] is False,'Completed unloaded SC4 sine condition required')
        provenance=c['source_provenance'];base.check_circuit(provenance['circuit'])
        base.require(provenance['case_id']=='baseline-square15-sc4','SC4 square source identity required')
        if source is None:source=copy.deepcopy(provenance)
        else:base.require(source==provenance,'SC4 conditions must use the same native source')
        rows=probes['measurements'];ids={r['id']for r in rows}
        base.require(probes['status']=='complete' and probes['unloaded_prediction'] is True and
            probes['actual_fundamental_Hz']==list(pair) and len(rows)==len(ids)==40 and
            probes['measurement_grid']['tip_gap_mm']==5 and all(r['tip_gap_mm']==5 for r in rows) and
            {r['depth_from_skin_surface_mm']for r in rows}=={5,10,15,20} and {r['axis']for r in rows}=={'X','Y'},
            'Actual-frequency40 unloaded5mm-gap probes required')
        base.require(set(c['cohorts'])==set(COHORTS),'All three explicit SC4/SC2/fresh-sine cohorts required')
        for cohort in c['cohorts'].values():
            base.require(set(cohort['normalizations'])==set(base.MODES),'Five stored normalization modes required')
            for mode in cohort['normalizations'].values():base.check_mode(mode,ids)
        conditions.append(dict(condition=c,probe_metadata=[{k:r[k]for k in
            ('id','depth_from_skin_surface_mm','position','axis','centre_mm','plus_mm','minus_mm','tip_gap_mm')}
            for r in rows],artifacts=copy.deepcopy(ref['artifacts'])))
        native.extend(copy.deepcopy(item)for name,item in ref['artifacts'].items()if not name.endswith('.json'))
    source_path=str(Path(source['source_summary']).resolve())
    base.require(Path(source_path).suffix=='.json' and summary['input_sha256'].get(source_path)==base.sha(source_path),
        'SC4 source-summary SHA binding required')
    proofs.append(dict(path=source_path,SHA256=summary['input_sha256'][source_path]))
    matches=[c for c in baseline_report['cases']if c['case_id']=='baseline-square15-sc4' and
             str(Path(c['summary_path']).resolve())==source_path]
    base.require(len(matches)==1,'One exact historical SC4 square baseline required')
    baseline=copy.deepcopy(matches[0]);base.check_circuit(baseline['circuit'])
    raw=copy.deepcopy(baseline['normalizations']['raw_1Vpp']);raw['source_Vpp_by_output']=[raw['source_Vpp_per_output']]*2
    base.check_mode(raw);baseline['raw_display']=raw
    for item in conditions:
        base.require(item['condition']['cohorts'][COHORTS[0]]['reference_id']==baseline['condition_id'] and
            item['condition']['cohorts'][COHORTS[1]]['reference_id']==sc2_model['baseline']['condition_id'],
            'Same-SC4 and absolute-SC2 cap references must identify their actual square baselines')
    return dict(schema='task1-frequency-SC4-results-view-model-v1',conditions=conditions,baseline=baseline,source=source,
        input_proofs=proofs+copy.deepcopy(sc2_model['input_proofs']),native_artifacts_declared_not_opened=native,
        summary_metadata={k:copy.deepcopy(v)for k,v in summary.items()if k not in
            ('conditions','input_sha256','implementation_files_sha256')},old_gui_path=str(Path(overall_gui).resolve()),
        cohorts=list(COHORTS),normalizations=list(base.MODES),metrics=list(base.METRICS),rois=[base.PRIMARY,base.SLAB],
        sc2_context=dict(baseline=sc2_model['baseline'],conditions=sc2_model['conditions']),SC4_own_cutoff_reference=own,
        erratum='Stored strings saying same-grid baseline for fixed high-volume cutoffs are inaccurate for SC4: all SC4 sine high volumes use frozen SC2 square thresholds. SC4 own thresholds were recorded separately and not used. Raw artifacts are unchanged.')


CONTEXT_SCRIPT=r'''
function sc2Context(){const cohort=$('cohort-select').value,roi=$('roi-select').value,metric=$('metric-select').value;
 const matched=cohort==='cached_SC2_square_3000_3030_caps',norm=matched?$('normalization-select').value:'raw_sine_1Vpp';
 $('sc2-scope').textContent=matched?'SC2 context uses the SAME absolute SC2 square burden reference and selected normalization; mesh discretization still differs.':'SC2 context is RAW1Vpp only: selected SC4/fresh-SC4 caps have different references, so these rows are not a matched-normalization comparison.';
 const source=data.sc2_context,rows=[['SC2 square RAW anchor',source.baseline.raw_display]];
 source.conditions.forEach(item=>rows.push(['SC2 '+item.condition.id,item.condition.cohorts.cached_original_square_3000_3030_caps.normalizations[norm]]));
 const off=roi===data.rois[0]?'primary_complement':'supplemental_complement',key=roi+'_mean';
 $('sc2-context').replaceChildren(table(['SC2 context','source Vpp each','ROI mean V/m','P10 V/m','CV','surfaceP95 V/m','non-targetP95 V/m','ROI>=SC2mean m³','contactJmax A/m²','contactJ95 A/m²','skinJmax A/m²','skinJ95 A/m²','source W'],rows.map(([id,m])=>{const r=m.regions[roi][metric],b=m.normalized_burdens;return[id,m.source_Vpp_by_output.join(', '),r.mean,r.p10,r.CV,m.regions.surface_0_5[metric].p95,m.regions[off][metric].p95,r.fixed_baseline_threshold_volume[key].volume_m3,b.surface_J_RMS_max_A_m2,b.surface_J_RMS_p95_A_m2,b.bulk_skin_J_vector_RMS_max_A_m2,b.bulk_skin_J_vector_RMS_p95_A_m2,b.source_power_W];})));
}
['cohort-select','roi-select','metric-select','normalization-select'].forEach(id=>$(id).addEventListener('change',sc2Context));sc2Context();
'''


def render_html(model,output_path,sc2_gui):
    document=base.render_html(model,output_path)
    script=base.SCRIPT.replace('Always shown: original4-square-pad baseline','Always shown: SC4 original4-square-pad baseline')
    script=script.replace('Frozen scalar-volume cutoffs always come from the original square baseline.',
        'SC4 sine high-volume cutoffs are fixed absolute SC2-square values, not SC4 own cutoffs.')
    script=script.replace("'ROI>=original mean m³'","'ROI>=frozen SC2 mean m³'").replace(
        "'non-target>=original mean m³'","'non-target>=frozen SC2 mean m³'")
    old="r.fixed_baseline_threshold_volume[key].volume_m3,m.regions[off][metric].fixed_baseline_threshold_volume[key].volume_m3"
    new="id==='Historical square RAW anchor'?'SC4 own cutoff; separate':r.fixed_baseline_threshold_volume[key].volume_m3,id==='Historical square RAW anchor'?'SC4 own cutoff; separate':m.regions[off][metric].fixed_baseline_threshold_volume[key].volume_m3"
    base.require(old in script,'Review changed underlying renderer threshold-table ABI')
    script=script.replace(old,new)+CONTEXT_SCRIPT
    old_hash=base64.b64encode(hashlib.sha256(base.SCRIPT.encode()).digest()).decode()
    new_hash=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    document=document.replace(old_hash,new_hash,1).replace('<script>'+base.SCRIPT+'</script>','<script>'+script+'</script>',1)
    note='<section><h2>SC4 versus SC2 · reference definitions</h2><p><b>Erratum:</b> '+html.escape(model['erratum'])+'</p>'+\
        '<p>SC4 own-square and fresh-SC4-sine caps are same-grid. SC2-square caps are an absolute cross-grid burden reference. '+\
        'The historical SC4 square row remains RAW; its own-cutoff high volumes are not displayed as SC2-threshold volumes. '+\
        '<a href="'+base.relative(sc2_gui,output_path)+'">Original SC2 frequency GUI</a>. No SC-convergence or frequency-matched C1 claim.</p></section>'
    document=document.replace('<div><label>Cap reference',note+'<div><label>Cap reference',1)
    context='<h2>SC2 context · same V/m units</h2><p id="sc2-scope"></p><section id="sc2-context"></section>'
    return document.replace('<h2>Native complex-phi probe predictions</h2>',context+'<h2>Native complex-phi probe predictions</h2>',1)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('summary','baseline-audit','sc2-summary','sc2-baseline-audit','sc2-gui','overall-gui','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();started=time.monotonic();output=a.output.resolve();receipt=output.with_suffix('.receipt.json')
    base.require(output.parent.is_dir() and not output.exists() and not receipt.exists(),'Fresh existing-directory output/receipt required')
    sc2=base.load_model(a.sc2_summary,a.sc2_baseline_audit,a.overall_gui)
    model=load_model(a.summary,a.baseline_audit,sc2,a.overall_gui);text=render_html(model,output,a.sc2_gui)
    base.require(len(text.encode())<=10*1024**2,'JSON display exceeds10MiB allowance')
    for proof in model['input_proofs']:base.require(base.sha(proof['path'])==proof['SHA256'],'Source JSON changed')
    with output.open('x')as stream:stream.write(text)
    result=dict(schema='task1-frequency-SC4-results-view-receipt-v1',status='rendered_precomputed_JSON_only',
        created_utc=datetime.now(timezone.utc).isoformat(),output=dict(path=str(output),SHA256=base.sha(output),bytes=output.stat().st_size),
        implementation=dict(path=str(Path(__file__).resolve()),SHA256=base.sha(__file__),renderer_SHA256=base.sha(base.__file__)),
        input_proofs=model['input_proofs'],erratum=model['erratum'],new_PDE=0,new_numerical_postprocessing=0,
        native_arrays_opened=False,budget_ledger_modified=False,wall_seconds=time.monotonic()-started)
    with receipt.open('x')as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=result['status'],output=str(output),bytes=output.stat().st_size)))


if __name__=='__main__':main()
