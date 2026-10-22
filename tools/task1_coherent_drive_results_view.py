#!/usr/bin/env python3
"""Offline selectors over completed coherent-drive JSON; no native array reads."""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime,timezone
import fcntl
import hashlib
import html
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

import task1_frequency_results_view as base
import task1_resource_policy as policy

ROOT=Path(__file__).resolve().parents[1]
COHORT='cached_original_square_3000_3030_caps'
MODES=('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin')
IDS=tuple(f'coherent-r{ratio}-p{phase:03d}'for ratio in ('0p5','1')for phase in (0,90,180,270))
GATES=[dict(name='primary_maxTIS_'+stat,unit='V/m',required_direction='greater')for stat in ('mean','p10')]
for _region in ('surface_0_5','primary_complement'):
    GATES.append(dict(name=_region+'_maxTIS_p95',unit='V/m',required_direction='less'))
    GATES.extend(dict(name=_region+'_high_volume_at_'+base.PRIMARY+'_'+stat,unit='m3',required_direction='less')for stat in ('mean','p10'))


def probes_checked(probes):
    rows=probes['measurements'];ids={row['id']for row in rows}
    base.require(probes['status']=='complete'and probes['unloaded_prediction']is True and
        probes['numerical_checks']['all_passed']is True and len(rows)==len(ids)==40 and probes['measurement_grid']['tip_gap_mm']==5 and
        all(row['tip_gap_mm']==5 for row in rows)and {row['depth_from_skin_surface_mm']for row in rows}=={5,10,15,20}and
        {row['axis']for row in rows}=={'X','Y'},'Forty complete unloaded probes/four depths/two axes/5mm tip gap required')
    base.require(probes['actual_fundamental_Hz']==[3000,3030]and
        all(sorted(line['frequency_Hz']for line in row['spectrum'])==[3000,3030]for row in rows),
        'Every probe spectrum must retain the actual3k carrier pair')
    return [{key:copy.deepcopy(row[key])for key in ('id','depth_from_skin_surface_mm','position','axis','centre_mm','plus_mm','minus_mm','tip_gap_mm')}for row in rows],ids


def stored_screen(condition,reference):
    screen=condition['canonical_skin_cap_screen'];checks=screen['checks']
    base.require(screen['normalization']=='skin_contact_only'and
        [{key:check[key]for key in ('name','unit','required_direction')}for check in checks]==GATES and
        all(type(check['passed'])is bool for check in checks)and type(screen['all_screen_checks_passed'])is bool and
        screen['all_screen_checks_passed']==all(check['passed']for check in checks)and
        screen['failed_checks']==[check['name']for check in checks if not check['passed']]and
        reference['canonical_screen_all_passed']==screen['all_screen_checks_passed'],
        'Stored eight-gate definitions/flags must agree; no gate is recomputed')
    return copy.deepcopy(screen)


def source_checked(condition):
    circuit=condition['source_circuit'];base.check_circuit(circuit)
    base.require(circuit['active_frequencies_by_output_Hz']=={'0':[3000,3030],'1':[3000,3030]}and
        circuit['uncommanded_frequency_termination'].replace(' ','')=='0Vthrough50ohm'and
        'unverified'in circuit['hardware_multitone_phase_sync_power_sink_compliance'],
        'Two coherent tones on each of two outputs/commonGND/50ohm; hardware remains unverified')
    waveform=condition['source_waveform']
    base.require(waveform['hard_maximum_bracket_width_V']==1e-6 and waveform['maximum_bracket_width_V']<=1e-6 and
        waveform['source_peak_basis_V']==.5 and waveform['source_resistance_ohm']==50 and
        waveform['seed_unitary']is True and waveform['unitary_after_Vpp_normalization']is False and
        len(waveform['source_Vpp_intervals_V'])==2 and all(len(pair)==2 and 0<=pair[0]<=pair[1]==1. and
            pair[1]-pair[0]<=1e-6 for pair in waveform['source_Vpp_intervals_V']),
        'Stored actual raw source waveform brackets <=1microV and conservative1Vpp upper bound required')
    base.require(condition['field_waveform_audit']['passed']is True and condition['probe_waveform_audit']['passed']is True,
        'Stored field/probe actual-waveform checks must pass')


def power_checked(evidence):
    base.require(len(evidence['outputs'])==2 and {row['output_index']for row in evidence['outputs']}=={0,1}and
        evidence['hardware_absorption_and_compliance_validated']is False and
        evidence['numerical_or_experimental_validation_promoted']is False,
        'Separate signed output powers and unverified hardware absorption/compliance required')
    verification=evidence['unscaled_saved_metric_verification']
    base.require(verification and all(type(row['passed'])is bool and row['passed']for rows in verification.values()for row in rows),
        'Producer saved signed-power verification flags must all pass')


def load_model(summary_path,baseline_audit_path,previous_gui_path):
    summary,proof=base.read_json(summary_path)
    base.require(summary['schema']=='task1-coherent-drive-scout-v1'and summary['status']=='calculated_unadopted'and
        summary['inputs_unchanged']is True and summary['new_PDE']==0 and summary['candidate_adopted']is False and
        summary['full_convergence_validated']is False and summary['experimentally_validated']is False and
        summary['actual_fundamental_Hz']==[3000,3030]and summary['beat_frequency_Hz']==30 and
        len(summary['conditions'])==8 and {row['id']for row in summary['conditions']}==set(IDS),
        'Exactly eight completed unadopted strong coherent conditions required')
    pre,preproof=base.bound_json(summary['preregistration'])
    base.require(pre['schema']=='task1-coherent-drive-scout-preregistration-v1'and pre['status']=='preregistered_not_executed',
        'Source-bound coherent preregistration required')
    audit,auditproof=base.read_json(baseline_audit_path)
    base.require(audit['schema']=='task1-volume-selectivity-v1'and audit['status']=='calculated_unadopted'and audit['inputs_unchanged']is True,
        'Completed canonical square volume reference required')
    source_path=str(Path(summary['canonical_square_reference']['summary_path']).resolve())
    source_summary,sourceproof=base.read_json(source_path)
    base.require(summary['input_sha256'].get(source_path)==sourceproof['SHA256']and source_summary['status']=='complete',
        'Canonical native source summary SHA binding required')
    baselines=[row for row in audit['cases']if str(Path(row['summary_path']).resolve())==source_path]
    base.require(len(baselines)==1,'One exact canonical4-square baseline required')
    baseline=copy.deepcopy(baselines[0]);base.check_circuit(baseline['circuit'])
    base.require(baseline['case_id']=='baseline-square15-xy80'and
        baseline['normalizations']['raw_1Vpp']['normalized_burdens']==summary['canonical_square_reference']['burdens'],
        'Original square raw burdens must remain the only normalization baseline')
    raw=copy.deepcopy(baseline['normalizations']['raw_1Vpp']);raw['source_Vpp_by_output']=[raw['source_Vpp_per_output']]*2
    base.check_mode(raw);baseline['raw_display']=raw
    proofs=[proof,preproof,auditproof,sourceproof];conditions=[];screens=[];native=[];source=None
    cutoffs=baseline['fixed_same_grid_baseline_cutoffs_V_m']
    cached=summary['cached_exclusive_sine_control']
    c,cp=base.bound_json(cached['artifacts']['condition.json']);probes,pp=base.bound_json(cached['artifacts']['probes.json']);proofs.extend((cp,pp))
    base.require(c['schema']=='task1-frequency-resynthesis-condition-v1'and c['status']=='calculated_unadopted'and
        c['id']==cached['id']=='sine-3000-3030-beat30'and c['actual_fundamental_Hz']==[3000,3030]and c['beat_frequency_Hz']==30 and
        c['new_PDE']==0 and cached['new_condition']is False and cached['recomposed']is False and
        c['shared_square_baseline_cutoffs_V_m']==cutoffs,'Exact cached exclusive3k sine reference required; no recomposition')
    base.check_circuit(c['source_provenance']['circuit'])
    base.require(c['source_provenance']['case_id']==baseline['case_id']and c['candidate_adopted']is False and
        c['instrument_loading_validated']is False,'Cached control must retain original geometry and unloaded/unadopted status')
    metadata,ids=probes_checked(probes);modes=copy.deepcopy(c['cohorts'][COHORT]['normalizations']);modes['raw_1Vpp']=modes.pop('raw_sine_1Vpp')
    base.require(set(modes)==set(MODES),'All five cached sine modes required')
    for mode in modes.values():base.check_mode(mode,ids)
    adapted=dict(id=c['id'],cohorts={COHORT:dict(reference_id=baseline['condition_id'],reference_waveform='square_3h',reference_actual_fundamental_Hz=[3000,3030],normalizations=modes)})
    conditions.append(dict(condition=adapted,probe_metadata=metadata,artifacts=copy.deepcopy(cached['artifacts']),display_role='cached_sine',source_evidence=dict(scope='Stored pure-sine source values; no new actual-source bracket or signed-power audit')))
    for reference in summary['conditions']:
        c,cp=base.bound_json(reference['artifacts']['condition.json']);probes,pp=base.bound_json(reference['artifacts']['probes.json']);proofs.extend((cp,pp))
        base.require(c['schema']=='task1-coherent-drive-condition-v1'and c['status']=='calculated_unadopted'and c['id']==reference['id']and
            c['mix_ratio']==reference['mix_ratio']and c['phase_deg']==reference['phase_deg']and c['mix_ratio']in (.5,1)and c['phase_deg']in (0,90,180,270)and
            c['source_case_id']==baseline['case_id']and c['actual_fundamental_Hz']==[3000,3030]and c['active_frequencies_Hz']==[3000,3030]and
            c['source_run_id']==baseline['run_id']and c['source_commit']==baseline['source_commit']and
            c['configuration_sha256']==baseline['configuration_sha256']and
            c['beat_frequency_Hz']==30 and c['harmonics_active']is False and c['new_PDE']==0 and c['candidate_adopted']is False and
            c['instrument_loading_validated']is False and c['full_convergence_validated']is False and c['experimentally_validated']is False and
            c['shared_original_square_cutoffs_V_m']==cutoffs,'Exact strong coherent condition and fixed-cutoff identity required')
        source_checked(c);metadata,ids=probes_checked(probes);modes=copy.deepcopy(c['normalizations'])
        base.require(set(modes)==set(MODES),'Five distinct stored coherent normalizations required')
        for mode in modes.values():
            mode['source_Vpp_by_output']=copy.deepcopy(mode['source_Vpp_upper_by_output_V'])
            base.check_mode(mode,ids);power_checked(mode['signed_per_output_power_evidence'])
            base.require(mode['baseline_derived_numerical_limits']==raw['normalized_burdens']and
                len(mode['actual_source_Vpp_intervals_V'])==2 and
                all(len(pair)==2 and 0<=pair[0]<=pair[1]and pair[1]==upper for pair,upper in zip(mode['actual_source_Vpp_intervals_V'],mode['source_Vpp_upper_by_output_V']))and
                len(mode['physical_pad_current_RMS_mA'])==4,'Stored source intervals, physical-pad currents and canonical burden limits required')
        adapted=dict(id=c['id'],mix_ratio=c['mix_ratio'],phase_deg=c['phase_deg'],cohorts={COHORT:dict(reference_id=baseline['condition_id'],reference_waveform='square_3h',reference_actual_fundamental_Hz=[3000,3030],normalizations=modes)})
        evidence={key:copy.deepcopy(c[key])for key in ('source_waveform','source_circuit','coefficient_vectors','field_waveform_audit','probe_waveform_audit','physical_pad_current_evidence','output_power_evidence')}
        conditions.append(dict(condition=adapted,probe_metadata=metadata,artifacts=copy.deepcopy(reference['artifacts']),display_role='coherent',source_evidence=evidence))
        screens.append(dict(id=c['id'],screen=stored_screen(c,reference)))
        if source is None:source=dict(run_id=c['source_run_id'],case_id=c['source_case_id'],source_commit=c['source_commit'],configuration_sha256=c['configuration_sha256'],circuit=c['source_circuit'])
        for name,item in reference['artifacts'].items():
            if not name.endswith('.json'):native.append(copy.deepcopy(item))
    return dict(schema='task1-coherent-drive-results-view-model-v1',baseline=baseline,conditions=conditions,source=source,screens=screens,
        input_proofs=proofs,native_artifacts_declared_not_opened=native,summary_metadata={key:copy.deepcopy(value)for key,value in summary.items()if key not in ('cached_exclusive_sine_control','canonical_square_reference')},
        cohorts=[COHORT],normalizations=list(MODES),metrics=list(base.METRICS),rois=[base.PRIMARY,base.SLAB],old_gui_path=str(Path(previous_gui_path).resolve()))


EXTRA_SCRIPT=r'''
function driveEvidence(){const norm=$('normalization-select').value;const rows=data.conditions.map(item=>{const m=item.condition.cohorts[data.cohorts[0]].normalizations[norm],p=m.signed_per_output_power_evidence,o=p?p.outputs:[];return[item.condition.id,item.display_role,item.condition.mix_ratio,item.condition.phase_deg,m.actual_source_Vpp_intervals_V?JSON.stringify(m.actual_source_Vpp_intervals_V):'not newly bracketed; stored pure-sine values',m.physical_pad_current_RMS_mA?m.physical_pad_current_RMS_mA.join(', '):'unavailable',o.length?o.map(x=>x.ideal_source_power_W).join(', '):'not newly audited',o.length?o.map(x=>x.metal_delivered_power_W).join(', '):'not newly audited',o.length?o.map(x=>x.source_resistor_loss_W).join(', '):'not newly audited',p?p.requires_output_power_absorption:'unavailable',p?p.has_negative_metal_delivered_power:'unavailable',p?p.hardware_absorption_and_compliance_validated:false];});$('drive-evidence').replaceChildren(table(['ID','scope','r','phase deg','Actual source Vpp intervals (output0/1)','physical pad RMS mA (0–3)','signed ideal W output0/1','signed metal W output0/1','50ohm W output0/1','requires absorption','negative metal power','hardware verified'],rows));}
['normalization-select','roi-select','metric-select'].forEach(id=>$(id).addEventListener('change',driveEvidence));driveEvidence();
function frequencyPower(){const norm=$('normalization-select').value,rows=[];data.conditions.forEach(item=>{const p=item.condition.cohorts[data.cohorts[0]].normalizations[norm].signed_per_output_power_evidence;if(p)p.outputs.forEach(output=>output.spectrum.forEach(line=>rows.push([item.condition.id,output.output_index,line.frequency_Hz,line.ideal_source_power_W,line.metal_delivered_power_W,line.source_resistor_loss_W])));});$('frequency-power').replaceChildren(table(['ID','output','Hz','signed ideal W','signed metal W','resistor W'],rows));}
['normalization-select','roi-select','metric-select'].forEach(id=>$(id).addEventListener('change',frequencyPower));frequencyPower();
'''


def render_html(model,output_path):
    text=base.render_html(model,output_path)
    old='<p>3000/3030Hz (30Hz beat) versus9000/9090Hz (90Hz beat). Carrier and beat both change; this is not a carrier-only experiment or physiological-equivalence comparison. '
    new='<p>Eight NEW coherent3000/3030Hz drive compositions plus a CACHED exclusive-sine3k control;30Hz beat,4 physical pads,2 outputs/commonGND/50Ω. Both tones drive both outputs in the new rows. '
    base.require(old in text,'Review changed base renderer wording');text=text.replace(old,new,1)
    text=text.replace('Existing37-case/4–8–12–16-pad GUI','Previous result GUI (original scope)',1).replace(
        'This new screen contains shared-axis scalar bars, not new-frequency spatial maps. Old maps must not be relabeled as these sine results.',
        'This screen contains shared-axis scalar bars. This viewer creates no physical maps; historical maps must retain their original drive definitions.',1)
    script=base.SCRIPT.replace("colors=['#7a8794','#147ca0','#b65237']","colors=['#7a8794','#147ca0','#b65237','#41834a','#824eaf','#ba7a14','#167a77','#a44773','#4e62b3','#7c7130']")
    script=script.replace('rows.push([item.condition.id,',"rows.push([(item.display_role==='cached_sine'?'CACHED SINE · ':'COHERENT · ')+item.condition.id,")
    script=script.replace("'drive Vpp each'","'Source Vpp upper (baseline nominal)'")+EXTRA_SCRIPT
    before=base64.b64encode(hashlib.sha256(base.SCRIPT.encode()).digest()).decode();after=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    text=text.replace(before,after,1).replace('<script>'+base.SCRIPT+'</script>','<script>'+script+'</script>',1)
    blocks=[]
    for row in model['screens']:
        screen=row['screen'];body=''.join('<tr>'+''.join('<td>'+html.escape(str(check.get(key,'unavailable')))+'</td>'for key in ('name','unit','required_direction','baseline','candidate','relative_change_percent','passed'))+'</tr>'for check in screen['checks'])
        blocks.append('<details><summary>'+html.escape(row['id'])+' · '+('all8 PASS; unadopted'if screen['all_screen_checks_passed']else'FAIL; unadopted')+'</summary><table><tr>'+''.join('<th>'+label+'</th>'for label in ('Gate','unit','direction','baseline','candidate','change %','pass'))+'</tr>'+body+'</table></details>')
    note='<section><h2>Actual source waveform and hardware scope</h2><p>Raw1Vpp means the stored full two-tone source max-minus-min before50Ω, with conservative upper1Vpp and producer bracket≤1µV over1/30s. '+\
        'Skin8/equal-power/current comparisons can require actual source Vpp above1; they are not fixed-voltage results. The ordinary table shows upper bounds for coherent rows; the interval table retains both bounds. '+\
        'The historical square anchor retains its nominal stored source definition; no new waveform bracket is invented for it. Seed coefficients are unitary only before separate actual-Vpp normalization.</p>'+\
        '<p>Signed ideal/metal powers retain negative values and passive-output absorption. Phase synchronization, source sink/compliance and actual multitone hardware remain unverified. '+\
        'Field and40 native-phi actual-waveform checks passed as stored producer evidence; no independent reconstruction occurs in this GUI. Probes remain UNLOADED; ETA loading/bandwidth/attenuation validation is held. No new C1 or physical field map is claimed.</p>'+\
        '<p>Historical square RMS includes both fundamentals and both third harmonics. Coherent and cached pure-sine RMS include the two active fundamentals only; RMS is not modulation.</p>'+\
        '<h2>Stored canonical eight-gate screens</h2><p>Fixed original-square skin_contact_only; selectors do not recompute verdicts. Cached sine has no new screen.</p>'+''.join(blocks)+'<h2>Actual source intervals and signed output powers</h2><div id="drive-evidence"></div><details><summary>Signed power by actual frequency and output</summary><div id="frequency-power"></div></details></section>'
    text=text.replace('<div><label>Cap reference',note+'<div><label>Cap reference',1)
    return text.replace('<title>Task1 · actual-frequency sine comparison</title>','<title>Task1 coherent drive</title>',1).replace('Task1 · Actual-frequency pure-sine comparison','Task1 · Coherent drive',1)


def identity():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,timeout=5).strip()
    paths=(Path(__file__).resolve(),ROOT/'tests/test_task1_coherent_drive_results_view.py',Path(base.__file__).resolve(),Path(policy.__file__).resolve())
    for path in paths:base.require(subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT,timeout=5)==path.read_bytes(),'Commit display source/tests before rendering')
    return dict(source_commit=commit,implementation_sha256={str(path):base.sha(path)for path in paths})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('summary','baseline-audit','previous','output'):parser.add_argument('--'+flag,type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve();receipt_path=output.with_suffix('.receipt.json');failure_path=output.with_suffix('.failure.json')
    base.require(output.suffix=='.html'and output.parent.is_dir()and not any(path.exists()for path in (output,receipt_path,failure_path)),'Fresh output/receipt/failure required')
    source=identity()
    with (ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=json.loads(ledger_path.read_text());limit=policy.effective_limit(ledger)
        seconds=min(120.,limit-ledger['spent_seconds']);base.require(seconds>0,'Validated budget exhausted')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});soft,hard=resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS,(min(3*1024**3,hard)if hard!=resource.RLIM_INFINITY else 3*1024**3,hard))
        base.require(shutil.disk_usage(output.parent).free>=2*1024**3+50*1024**2,'Preserve2GiB plus50MiB allowance')
        started=time.monotonic();status='failed'
        def timeout(signum,frame):raise TimeoutError('Finite coherent JSON-view deadline exceeded')
        signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,seconds)
        try:
            model=load_model(args.summary,args.baseline_audit,args.previous);text=render_html(model,output)
            base.require(len(text.encode())<=49*1024**2 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=3*1024**3,'Unchanged display storage/RSS cap exceeded')
            base.require(identity()==source and all(base.sha(pin['path'])==pin['SHA256']for pin in model['input_proofs']),'Display inputs/source changed')
            with output.open('x')as stream:stream.write(text)
            receipt=dict(schema='task1-coherent-drive-results-view-receipt-v1',status='rendered_precomputed_JSON_only',created_utc=datetime.now(timezone.utc).isoformat(),**source,
                output=dict(path=str(output),SHA256=base.sha(output),bytes=output.stat().st_size),input_proofs=model['input_proofs'],case_count=10,coherent_condition_count=8,
                native_arrays_opened=False,new_PDE=0,new_numerical_postprocessing=0,resources=dict(wall_seconds=time.monotonic()-started,max_seconds=seconds,global_limit_seconds=limit,CPU_count=1,output_limit_bytes=50*1024**2,minimum_reserve_bytes=2*1024**3))
            payload=json.dumps(receipt,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
            base.require(output.stat().st_size+len(payload.encode())<=50*1024**2 and shutil.disk_usage(output.parent).free>=2*1024**3+len(payload.encode()),'Receipt would exceed storage cap/reserve')
            with receipt_path.open('x')as stream:stream.write(payload)
            status=receipt['status'];print(json.dumps(dict(status=status,conditions=10,output=str(output))))
        except BaseException as error:
            with failure_path.open('x')as stream:json.dump(dict(status='failed',error_type=type(error).__name__,error=str(error),partial_evidence_preserved=True),stream,indent=2)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.stem,stage='JSON_only_coherent_drive_view',status=status,seconds=elapsed))
            temporary=ledger_path.with_name(ledger_path.name+'.partial');temporary.write_text(json.dumps(ledger,indent=2)+'\n');temporary.replace(ledger_path)


if __name__=='__main__':main()
