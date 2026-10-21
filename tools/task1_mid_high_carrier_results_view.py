#!/usr/bin/env python3
"""JSON-only view of completed actual mid-high-carrier native runs and cached3k.

No native E/phi/NPZ reads, numerical gates, normalization calculation, PDE,
instrument loading, or resource-ledger changes occur in this display tool.
"""
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

PAIRS=((5000,5030),(9000,9030))
COHORTS=('cached_original_square_3000_3030_caps','cached_sine_3000_3030_caps')
MODES=('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin')


def read_mid_high_proof(summary,pre,summary_path):
    """Verify the new JSON proof; never reopen failed-donor artifacts or arrays."""
    base.require(summary['resources']['actual_native_RHS_solves']==6 and
        summary['resources']['reused_9000_RHS_solves']==2 and
        summary['resources']['reused_regression_RHS_solves']==4 and
        pre['actual_new_native_RHS_solves_max']==6 and pre['reused_9000_RHS_solves']==2 and pre['reused_regression_RHS_solves']==4,
        'Mid/high must declare6 new RHS,2 reused9000 RHS and4 reused regression RHS')
    ref=summary['producer_regression']
    base.require(ref['status']=='passed' and Path(ref['path']).resolve().parent==Path(summary_path).resolve().parent,
        'Passed regression proof must belong to the new mid/high run')
    proof,pin=base.bound_json(ref)
    base.require(proof['status']=='passed' and proof['reused_regression_RHS_solves']==4 and
        proof['new_regression_RHS_solves']==0,'Passed proof must preserve reused4/new0 regression accounting')
    declared=pre['donor_reference'];recorded=summary['donor_reference'];reused=proof['reused_from_donor']
    keys=('run_path','basis_path','source_commit','original_registration_SHA256','original_failure','native_file_inventory_sha256')
    base.require(all(reused[key]==declared[key]==recorded[key]for key in keys) and
        declared['actual_reused_RHS_solves']==4 and declared['new_regression_RHS_solves']==0 and
        recorded['reused_regression_RHS_solves']==4 and recorded['new_regression_RHS_solves']==0 and
        recorded['original_failed_stage_charge']==declared['original_failed_stage_charge'],
        'Donor provenance and original failed-stage charge must remain explicit and unchanged')
    return pin


def validate_frequency_assembly(assembly,config_sha256=None):
    """Check recorded source identities only; never open or combine native data."""
    meta=assembly['assembly_metadata'];raw=assembly['raw_new_frequency_metadata']
    cached=assembly['cached_frequency_metadata']['9000'];sources=assembly['frequency_sources']
    base.require(meta['schema']=='task1-mid-high-cached-frequency-assembly-v1' and
        meta['actual_new_basis_RHS_solves']==6 and meta['cached_basis_RHS_reused']==2 and
        meta['total_analysis_basis_vectors']==8 and meta['analysis_frequencies_Hz']==[5000,5030,9000,9030] and
        meta['raw_native_metadata_frequencies_Hz']==[5000,5030,9030] and meta['raw_metadata_modified'] is False and
        meta['single_four_frequency_native_producer_claimed'] is False and meta['inputs_unchanged'] is True,
        'Three new frequencies/six RHS must remain distinct from four analysis frequencies/eight vectors')
    base.require(raw['frequencies_Hz']==[5000,5030,9030] and raw['actual_basis_RHS_solves']==6 and
        raw['exporter_class']=='CloudFrequencyMidHighBasis' and raw['exporter_kind']=='mid_high_frequency_native' and
        cached['frequencies_Hz']==[3000,3030,9000,9090] and set(sources)=={'5000','5030','9000','9030'},
        'Raw new producer and cached9000 metadata must retain their original frequency lists')
    if config_sha256 is not None:base.require(raw['config_sha256']==config_sha256,'New raw config SHA differs from condition source')
    mask_shas=set()
    for frequency,row in sources.items():
        expected=cached if frequency=='9000' else raw
        base.require(row['frequency_Hz']==int(frequency) and row['basis_RHS_vectors']==2 and
            row['kind']==('reused_cached_native' if frequency=='9000' else 'new_native') and
            row['config_sha256']==expected['config_sha256'] and row['exporter_class']==expected['exporter_class'] and
            bool(row['basis_folder']) and bool(row['input_sha256']) and len(row['mask_sha256'])==64,
            'Every actual frequency requires its unchanged native/cached source and config provenance')
        mask_shas.add(row['mask_sha256'])
    base.require(len(mask_shas)==1,'Frequency source physical masks must match')


def probe_metadata(probes,pair):
    rows=probes['measurements'];ids={r['id']for r in rows}
    base.require(probes['status']=='complete' and probes['unloaded_prediction'] is True and
        probes['numerical_checks']['all_passed'] is True and len(rows)==len(ids)==40 and
        probes['measurement_grid']['tip_gap_mm']==5 and all(r['tip_gap_mm']==5 for r in rows) and
        {r['depth_from_skin_surface_mm']for r in rows}=={5,10,15,20} and {r['axis']for r in rows}=={'X','Y'},
        'Completed40 unloaded5mm-gap probe rows required')
    base.require(all(sorted(v['frequency_Hz']for v in r['spectrum'])==list(pair)for r in rows),
        'Each raw probe spectrum must use the actual carrier pair')
    return [{k:r[k]for k in ('id','depth_from_skin_surface_mm','position','axis','centre_mm','plus_mm','minus_mm','tip_gap_mm')}
        for r in rows],ids


def saved_screen(condition):
    screen=condition['canonical_square_cap_screen'];checks=screen['checks']
    base.require(screen['normalization']=='skin_contact_only' and screen['candidate_adopted'] is False and
        len(checks)==8 and len({c['name']for c in checks})==8 and all(type(c['passed']) is bool for c in checks) and
        type(screen['all_screen_checks_passed']) is bool and screen['all_screen_checks_passed']==all(c['passed']for c in checks),
        'Consistent stored eight-gate screen required; no gate is recalculated here')
    return copy.deepcopy(screen)


def load_model(summary_path,registration_path,cached_summary_path,old_gui_path):
    summary,proof=base.read_json(summary_path);pre,preproof=base.read_json(registration_path)
    base.require(summary['schema']=='task1-mid-high-carrier-result-v1' and summary['status']=='calculated_unadopted' and
        summary['inputs_unchanged'] is True and summary['candidate_adopted'] is False and
        summary['full_convergence_validated'] is False and summary['producer_regression']['status']=='passed' and
        summary['registration_sha256']==preproof['SHA256'] and summary['actual_frequency_pairs']==[list(p)for p in PAIRS] and
        summary['actual_beat_frequencies_Hz']==[30,30] and len(summary['conditions'])==2,
        'Terminal mid-high-carrier results with passed producer regression required')
    base.require(pre['schema']=='task1-mid-high-carrier-preregistration-v1' and pre['status']=='prepared' and
        pre['regression_required_before_new_bundle'] is True and
        pre['new_native_frequencies_Hz']==[5000,5030,9030] and pre['analysis_frequency_pairs_Hz']==[list(p)for p in PAIRS] and
        pre['cached_frequency_Hz']==9000 and pre['cached_9000_readback_required'] is True and set(pre['comparison_references'])==set(COHORTS),
        'Exact source-bound mid-high-carrier registration required')
    proofs=[proof,preproof,read_mid_high_proof(summary,pre,summary_path)];conditions=[];screens=[];native=[]
    validate_frequency_assembly(summary['frequency_assembly'])
    baseline=copy.deepcopy(pre['original_square_volume_reference_row']);base.check_circuit(baseline['circuit'])
    base.require(baseline['case_id']=='baseline-square15-xy80' and
        baseline['fixed_same_grid_baseline_cutoffs_V_m']==pre['fixed_square_SC2_cutoffs_V_m'],
        'Original square scalar/cutoff reference required')
    source_summary=str(Path(pre['source_baseline_summary']).resolve());source_pins=pre['source_and_input_sha256']
    base.require(Path(source_summary).suffix=='.json' and source_pins.get(source_summary)==base.sha(source_summary) and
        str(Path(baseline['summary_path']).resolve())==source_summary,'Original source-summary SHA binding required')
    proofs.append(dict(path=source_summary,SHA256=source_pins[source_summary]))
    raw=copy.deepcopy(baseline['normalizations']['raw_1Vpp']);raw['source_Vpp_by_output']=[raw['source_Vpp_per_output']]*2
    base.check_mode(raw);baseline['raw_display']=raw
    for ref,pair in zip(summary['conditions'],PAIRS):
        condition,p=base.bound_json(ref['artifacts']['condition.json']);proofs.append(p)
        probes,p=base.bound_json(ref['artifacts']['probes.json']);proofs.append(p)
        base.require(condition['schema']=='task1-mid-high-carrier-condition-v1' and condition['status']=='calculated_unadopted' and
            condition['id']==ref['id'] and condition['actual_fundamental_Hz']==list(pair) and condition['beat_frequency_Hz']==30 and
            condition['waveform']=='sine' and condition['candidate_adopted'] is False and
            condition['full_convergence_validated'] is False and condition['instrument_loading_validated'] is False,
            'Actual mid/high-frequency sine condition identity required')
        base.check_circuit(condition['source_provenance']['circuit'])
        provenance=condition['source_provenance']
        assembly={key:provenance[key]for key in ('assembly_metadata','frequency_sources','raw_new_frequency_metadata','cached_frequency_metadata')}
        base.require(assembly==summary['frequency_assembly'] and bool(provenance['configuration_hash_scope']),
            'Condition assembly/provenance must equal its source-bound summary')
        validate_frequency_assembly(assembly,provenance['configuration_sha256'])
        base.require(condition['source_provenance']['circuit']['carrier_assignment_Hz']==list(pair),
            'Circuit metadata must identify the actual new source frequencies')
        metadata,ids=probe_metadata(probes,pair)
        base.require(set(condition['cohorts'])==set(COHORTS) and
            condition['fixed_square_SC2_cutoffs_V_m']==pre['fixed_square_SC2_cutoffs_V_m'],'Two fixed reference cohorts/cutoffs required')
        for name,cohort in condition['cohorts'].items():
            base.require(set(cohort['normalizations'])==set(MODES) and
                cohort['reference_id']==pre['comparison_references'][name]['id'],'Five stored modes with explicit reference identity required')
            for mode in cohort['normalizations'].values():
                base.check_mode(mode,ids)
                base.require(mode['baseline_derived_numerical_limits']==pre['comparison_references'][name]['burdens'],
                    'Stored burden limits differ from declared reference')
        screen=saved_screen(condition);screens.append(dict(condition_id=condition['id'],screen=screen))
        if 'canonical_screen_all_passed'in ref:
            base.require(ref['canonical_screen_all_passed']==screen['all_screen_checks_passed'],'Summary screen flag differs')
        conditions.append(dict(condition=condition,probe_metadata=metadata,artifacts=copy.deepcopy(ref['artifacts']),display_role='new_analysis'))
        native.extend(copy.deepcopy(item)for name,item in ref['artifacts'].items()if not name.endswith('.json'))
    cached,cachedproof=base.read_json(cached_summary_path);proofs.append(cachedproof)
    base.require(cached['schema']=='task1-frequency-resynthesis-audit-v1' and cached['status']=='calculated_unadopted' and
        cached['inputs_unchanged'] is True,'Completed cached actual3k sine reference bundle required')
    refs=[r for r in cached['conditions']if r['actual_fundamental_Hz']==[3000,3030]]
    base.require(len(refs)==1,'One cached actual3k sine condition required')
    ref=refs[0];c,p=base.bound_json(ref['artifacts']['condition.json']);proofs.append(p)
    base.require(source_pins.get(p['path'])==p['SHA256'] and c['status']=='calculated_unadopted' and
        c['actual_fundamental_Hz']==[3000,3030] and c['beat_frequency_Hz']==30 and c['waveform']=='sine' and
        c['shared_square_baseline_cutoffs_V_m']==pre['fixed_square_SC2_cutoffs_V_m'],
        'Cached3k condition must be the exact registered reference, never relabeled native data')
    probes,p=base.bound_json(ref['artifacts']['probes.json']);proofs.append(p);metadata,ids=probe_metadata(probes,(3000,3030))
    aliases={COHORTS[0]:COHORTS[0],COHORTS[1]:'fresh_sine_3000_3030_caps'};adapted=copy.deepcopy(c);adapted['cohorts']={}
    for name,old_name in aliases.items():
        cohort=copy.deepcopy(c['cohorts'][old_name]);modes=cohort['normalizations'];modes['raw_1Vpp']=modes.pop('raw_sine_1Vpp')
        base.require(set(modes)==set(MODES),'Cached reference must contain all five existing values')
        for mode in modes.values():
            base.check_mode(mode,ids)
            base.require(mode['baseline_derived_numerical_limits']==pre['comparison_references'][name]['burdens'],
                'Cached/current reference numerical limits differ')
        adapted['cohorts'][name]=cohort
    conditions.append(dict(condition=adapted,probe_metadata=metadata,artifacts=copy.deepcopy(ref['artifacts']),display_role='cached_reference',
        display_key_aliases=dict(cohorts=aliases,raw_mode='raw_sine_1Vpp → raw_1Vpp; stored numbers unchanged')))
    provenance=copy.deepcopy(conditions[0]['condition']['source_provenance']);provenance['case_id']=provenance['native_case_id']
    return dict(schema='task1-mid-high-carrier-results-view-model-v1',conditions=conditions,baseline=baseline,source=provenance,
        input_proofs=proofs,native_artifacts_declared_not_opened=native,canonical_screens=screens,
        summary_metadata=copy.deepcopy(summary),registration_metadata=dict(source_commit=pre['source_commit'],
            fixed_square_SC2_cutoffs_V_m=pre['fixed_square_SC2_cutoffs_V_m'],contact=pre.get('contact',{})),
        old_gui_path=str(Path(old_gui_path).resolve()),cohorts=list(COHORTS),normalizations=list(MODES),
        metrics=list(base.METRICS),rois=[base.PRIMARY,base.SLAB])


def screen_html(model):
    esc=lambda x:html.escape(str(x));parts=[]
    for row in model['canonical_screens']:
        screen=row['screen'];body=''.join('<tr>'+''.join('<td>'+esc(check.get(k,'unavailable'))+'</td>'for k in
            ('name','unit','required_direction','baseline','candidate','relative_change_percent','passed'))+'</tr>'for check in screen['checks'])
        parts.append('<details><summary>'+esc(row['condition_id'])+' · '+('all8 PASS; unadopted'if screen['all_screen_checks_passed']else'FAIL; not nominated')+'</summary>'+\
            '<table><tr>'+''.join('<th>'+h+'</th>'for h in ('Gate','unit','direction','baseline','candidate','change %','pass'))+'</tr>'+body+'</table></details>')
    return '<section><h2>Stored canonical eight-gate screen</h2><p>Fixed original-square caps, skin_contact_only, primary r≤5mm/depth15–20mm. '+\
        'These stored gate outcomes do not change with the display selectors and are not recalculated by this GUI. '+\
        'A pass permits separately registered validation; it does not adopt a candidate. Cached3k is a reference, with no newly calculated8-gate verdict here.</p>'+''.join(parts)+'</section>'


def assembly_html(model):
    assembly=model['summary_metadata']['frequency_assembly'];esc=lambda value:html.escape(str(value))
    rows=''.join('<tr>'+''.join('<td>'+esc(value)+'</td>'for value in
        (frequency,row['kind'],row['basis_RHS_vectors'],row['exporter_class'],row['config_sha256'],row['mask_sha256'],row['basis_folder']))+'</tr>'
        for frequency,row in sorted(assembly['frequency_sources'].items(),key=lambda item:int(item[0])))
    return '<section><h2>Actual frequency source inventory</h2><p>Raw new producer:5000,5030,9030Hz only,6 RHS. '+\
        'Analysis inventory:5000,5030,9000,9030Hz,8 basis vectors including2 cached9000Hz vectors. '+\
        'The new config SHA covers the three new frequencies; the original cached9000 config SHA is recorded separately below. '+\
        'The original raw9000 producer metadata still lists3000/3030/9000/9090Hz. Basis folders are local native paths; this GUI does not open them.</p>'+\
        '<table><tr>'+''.join('<th>'+label+'</th>'for label in ('Hz','source kind','RHS vectors','exporter','config SHA256','mask SHA256','local basis folder'))+'</tr>'+rows+'</table></section>'


def render_html(model,output_path,cached_gui_path,lower_gui_path=None):
    if lower_gui_path is None:lower_gui_path=Path(__file__).resolve().parents[1]/'docs/CLOUD_LOWER_CARRIER_RESULTS_20261021.html'
    text=base.render_html(model,output_path)
    old='<p>3000/3030Hz (30Hz beat) versus9000/9090Hz (90Hz beat). Carrier and beat both change; this is not a carrier-only experiment or physiological-equivalence comparison. '
    new='<p>NEW actual5000/5030Hz and9000/9030Hz analyses versus CACHED actual3000/3030Hz sine reference; all three beat frequencies are30Hz. The9000Hz basis is reused;5030/9030Hz are distinct actual frequencies. Earlier9000/9090Hz (90Hz beat) is separate. Initial bare2000/2010Hz is a separate historical condition. No physiological equivalence is claimed. '
    base.require(old in text,'Review changed base renderer frequency wording')
    text=text.replace(old,new,1).replace('Task1 · Actual-frequency pure-sine comparison','Task1 · Actual mid-high-carrier comparison',1)
    text=text.replace('Existing37-case/4–8–12–16-pad GUI','Previous overall4–8–12–16-pad GUI',1)
    script=base.SCRIPT.replace("colors=['#7a8794','#147ca0','#b65237']","colors=['#7a8794','#147ca0','#b65237','#41834a']")
    script=script.replace('rows.push([item.condition.id,',"rows.push([(item.display_role==='cached_reference'?'CACHED REF · ':'NEW ANALYSIS · ')+item.condition.id,")
    script=script.replace("c.id+' ·40 UNLOADED probes", "(item.display_role==='cached_reference'?'CACHED REF · ':'NEW ANALYSIS · ')+c.id+' ·40 UNLOADED probes")
    oldhash=base64.b64encode(hashlib.sha256(base.SCRIPT.encode()).digest()).decode();newhash=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    text=text.replace(oldhash,newhash,1).replace('<script>'+base.SCRIPT+'</script>','<script>'+script+'</script>',1)
    note='<section><p><b>Actual mid/high frequency provenance:</b> producer regression must pass before the mid/high-frequency bundle. '+\
        'Regression is a same-operator/code-path check, not independent-solver or mesh validation. '+\
        'This run records6 new RHS at5000/5030/9030Hz,2 reused cached9000Hz RHS and4 reused3k regression RHS; the original failed-stage cost is preserved. Donor provenance was checked by the producer; this viewer reads only the new regression proof JSON, not old failed-run JSON or native files. '+\
        'Square3k and sine3k are separately named cap/current/power references; fixed high-volume cutoffs always remain the original square3k values. '+\
        '<a href="'+base.relative(cached_gui_path,output_path)+'">Original cached frequency GUI</a> · '+\
        '<a href="'+base.relative(lower_gui_path,output_path)+'">Lower1k/2k comparison GUI</a>.</p>'+\
        '<p><b>ETA5001 / DSOX1202A loading held:</b> all40 probe rows are UNLOADED. No new phantom differential-port impedance, calibrated transfer function, actual attenuation-switch verification or frequency-matched C1 was calculated.</p>'+\
        '<p>Shared-axis scalar bars are not physical XY/XZ maps. No old field or map is relabeled as a new mid/high-frequency result.</p></section>'
    return text.replace('<div><label>Cap reference',note+assembly_html(model)+screen_html(model)+'<div><label>Cap reference',1)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('summary','registration','cached-summary','cached-gui','lower-gui','previous-gui','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();started=time.monotonic();output=a.output.resolve();receipt=output.with_suffix('.receipt.json')
    base.require(output.parent.is_dir() and not output.exists() and not receipt.exists(),'Fresh output/receipt required')
    model=load_model(a.summary,a.registration,a.cached_summary,a.previous_gui);text=render_html(model,output,a.cached_gui,a.lower_gui)
    base.require(len(text.encode())<=12*1024**2,'JSON-only GUI exceeds12MiB display cap')
    for proof in model['input_proofs']:base.require(base.sha(proof['path'])==proof['SHA256'],'Source JSON changed during display assembly')
    with output.open('x')as stream:stream.write(text)
    result=dict(schema='task1-mid-high-carrier-results-view-receipt-v1',status='rendered_precomputed_JSON_only',
        created_utc=datetime.now(timezone.utc).isoformat(),output=dict(path=str(output),SHA256=base.sha(output),bytes=output.stat().st_size),
        implementation=dict(path=str(Path(__file__).resolve()),SHA256=base.sha(__file__),renderer_SHA256=base.sha(base.__file__)),
        input_proofs=model['input_proofs'],actual_native_pairs=[list(p)for p in PAIRS],cached_reference_pair=[3000,3030],
        all_beat_frequencies_Hz=30,new_PDE=0,new_numerical_postprocessing=0,native_arrays_opened=False,budget_ledger_modified=False,
        wall_seconds=time.monotonic()-started)
    with receipt.open('x')as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=result['status'],output=str(output),bytes=output.stat().st_size)))


if __name__=='__main__':main()
