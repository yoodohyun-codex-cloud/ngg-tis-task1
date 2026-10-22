#!/usr/bin/env python3
"""Five finite sine/coherent re-syntheses of one cached rotated-return basis.

No PDE, electrode/topology change, source mutation, retry, hardware readiness,
physiological equivalence, full convergence or automatic candidate adoption.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import copy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import threading
import time
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_name]='1'
import numpy as np
import task1_drive_ratio_audit as drive
import task1_volume_selectivity as volume
import task1_waveform_check as waveform
import task1_carrier_balance_audit as carrier
import task1_frequency_resynthesis as frequency
import task1_output_power_evidence as power
import task1_candidate_screen as screen
import task1_cloud_batch as core
import task1_resource_policy as policy
import task1_results_view as view
import task1_candidate_ranking as ranking
import task1_coherent_drive_scout as strong
import task1_rotation_drive_ratio_scout as rotation

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
FREQUENCIES=(3000,3030,9000,9090)
PAIR=(3000,3030)
SCHEMA='task1-rotation-coherent-scout-preregistration-v1'
BASELINE_SUMMARY=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json'
SOURCE_RUN='cloud-one-return-rotation-20261021T174000Z'
SOURCE_ID='asym-return2-rot90-xy80'
SOURCE_SUMMARY=ROOT/'data-native'/SOURCE_RUN/'postprocess'/SOURCE_ID/'summary.json'
CONTROL_VOLUME=ROOT/'docs/cloud-one-return-rotation-context-20261021T174000Z/volume.json'
CONDITIONS=(dict(id='rotation-sine-control',waveform='sine'),)+tuple(
    dict(id=f'rotation-coherent-r{label}-p{phase:03d}',waveform='coherent_two_tone_sine',mix_ratio=r,phase_deg=phase)
    for r,label in((.5,'0p5'),(1.,'1'))for phase in(90,270))
VPP_WIDTH=1e-6
require=drive.require
seed_coefficients=strong.seed_coefficients
normalize_source=strong.normalize_source
normalization_modes=strong.normalization_modes
signed_output_powers=strong.signed_output_powers
physical_pad_currents=strong.physical_pad_currents
source_metadata=rotation.source_metadata


def control_coefficients():
    return {3000:np.array([-1j,0j]),3030:np.array([0j,-1j]),9000:np.zeros(2,complex),9090:np.zeros(2,complex)}


def condition_coefficients(declared,waveform_statistics,SamplingLimits):
    require(declared in CONDITIONS,'Exactly five registered rotation sine/coherent conditions required')
    if declared['waveform']!='sine':
        return normalize_source(seed_coefficients(declared['mix_ratio'],declared['phase_deg']),waveform_statistics,SamplingLimits)
    coefficients=control_coefficients();outputs=[]
    for output,f in enumerate(PAIR):
        stats=waveform_statistics([f],np.array([-.5j]),[f],sampling=SamplingLimits(samples_per_highest_cycle=128,
            max_statistics_samples=262144,plot_duration_s=min(.002,4000/(f*128))))
        lo,hi=float(stats['Vpp_lower_V']),float(stats['Vpp_upper_V'])
        require(math.isfinite(lo)and math.isfinite(hi)and 0<lo<=hi and lo<=1+2e-12 and hi>=1-2e-12,
            'Sine control waveform bracket must contain analytic1Vpp')
        outputs.append(dict(output_index=output,frequencies_Hz=[f],numerical_Vpp_lower_V=lo,numerical_Vpp_upper_V=hi,
            analytic_source_Vpp_V=1.,column_scale=1.,source_Vpp_interval_V=[1.,1.]))
    return coefficients,dict(outputs=outputs,column_scales=[1.,1.],source_Vpp_intervals_V=[[1.,1.],[1.,1.]],
        maximum_bracket_width_V=0.,hard_maximum_bracket_width_V=VPP_WIDTH,source_peak_basis_V=.5,source_resistance_ohm=50,
        common_period_s=1/30,seed_unitary=True,unitary_after_Vpp_normalization=True,normalization_performed=False,
        interpretation='Exclusive pure-sine control: exact -j unit coefficients and analytic1Vpp before50ohm; sampled brackets independently contain1Vpp')


def validate_cached_sine(actual,cached,amplitude_scale=1.):
    require(type(amplitude_scale)in(int,float)and math.isfinite(amplitude_scale)and amplitude_scale>0,
        'Finite positive explicit cached-sine amplitude scale required')
    linear=('target20_modulation_V_m','target20_total_E_RMS_V_m','surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2',
        'contact_voltage_RMS_max_V','max_source_current_RMS_mA')
    quadratic=('SC_power_W','contact_power_W','skin_power_W','tissue_contact_power_W','source_power_W','source_resistor_power_W')
    errors=[]
    def compare(a,b,shape,name):
        a=np.asarray(a,float);b=np.asarray(b,float)
        require(a.shape==b.shape==shape and np.isfinite(a).all()and np.isfinite(b).all(),'Finite exact cached sine shape required: '+name)
        delta=abs(a-b);require(np.all(delta<=1e-14+1e-10*abs(b)),'Cached source-bound pure-sine regression failed: '+name)
        errors.extend(delta.reshape(-1).tolist())
    require(actual.get('sampled_direction_count')==cached.get('sampled_direction_count')==2074,'Same2074 direction contract required')
    for name in linear:compare(actual[name],cached[name]*amplitude_scale,(),name)
    for name in quadratic:compare(actual[name],cached[name]*amplitude_scale**2,(),name)
    compare(actual['source_current_RMS_by_output_mA'],np.asarray(cached['source_current_RMS_by_output_mA'])*amplitude_scale,(2,),
        'source_current_RMS_by_output_mA')
    for name,re,im,dim in(('source_current_spectrum','real_A','imaginary_A',2),
        ('loaded_metal_voltage_spectrum','real_V','imaginary_V',2),('centre_field_spectrum','real_V_m','imaginary_V_m',3)):
        aa=actual[name];bb=cached[name]
        require(len(aa)==len(bb)==4 and {r['frequency_Hz']for r in aa}=={r['frequency_Hz']for r in bb}==set(FREQUENCIES),
            'Exact4freq spectra including explicit zero third harmonics required: '+name)
        aa={r['frequency_Hz']:r for r in aa};bb={r['frequency_Hz']:r for r in bb}
        for f in FREQUENCIES:
            for component in(re,im):compare(aa[f][component],np.asarray(bb[f][component])*amplitude_scale,(dim,),name+':'+str(f)+':'+component)
    return dict(passed=True,amplitude_scale=amplitude_scale,linear_metric_fields=list(linear),quadratic_metric_fields=list(quadratic),
        maximum_absolute_error=max(errors,default=0.),relative_tolerance=1e-10,absolute_tolerance=1e-14,
        meaning='Electrical/contact/centre complex-field control regression only; no sine native NPZ archive presumed')


def implementation_receipt():
    modules=(drive,volume,waveform,carrier,frequency,power,screen,core,policy,view,ranking,strong,rotation)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_rotation_coherent_scout.py',ROOT/'tools/task1_candidate_ranking.py',
        *[Path(module.__file__).resolve()for module in modules]]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();pins={}
    for path in paths:
        require(path.read_bytes()==subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT),
            'Implementation/helper/test differs from committed HEAD: '+str(path))
        pins[str(path)]=view.sha(path)
    return dict(implementation_git_commit=commit,implementation_files_sha256=pins)


def context_metadata(decision_path,feedback_path,pins):
    require(decision_path is not None and feedback_path is not None,'Explicit root decision and actual feedback GET context required')
    def bound(path):
        path=Path(path)
        require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and
            not path.is_symlink()and path.stat().st_size<=25*1024**2,'Canonical local public JSON context required')
        digest=view.sha(path);value=view.read(path);require(view.sha(path)==digest,'Context changed while reading')
        pins[str(path)]=digest;return value,dict(path=str(path),SHA256=digest)
    decision,dref=bound(decision_path);feedback,fref=bound(feedback_path)
    require(decision.get('schema')=='task1-rotation-coherent-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and
        decision.get('conditions')==[dict(c)for c in CONDITIONS],'Exact root-selected5 rotation sine/coherent conditions required; peer endorsement must not be inferred')
    refs=decision.get('input_sha256');require(isinstance(refs,dict)and bool(refs),'Root decision must bind completed scientific evidence')
    require(refs.get(str(Path(feedback_path)))==fref['SHA256'],'Root decision must bind the same actual feedback GET receipt')
    for name,digest in refs.items():
        path=Path(name)
        require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and
            not path.is_symlink()and path.suffix=='.json'and path.stat().st_size<=25*1024**2 and view.sha(path)==digest,
            'Root selected evidence changed: '+name)
        pins[str(path)]=digest
    require(feedback.get('schema')=='task1-queue-feedback-v1'and feedback.get('status')=='read_only_feedback_checked'and
        feedback.get('error')is None and feedback.get('public_GitHub_only')is True and feedback.get('messages_sent')==0 and
        feedback.get('new_PDE')==0 and feedback.get('peer_agreement_inferred')is False and
        feedback.get('new_feedback_automatically_adopted')is False,'Actual read-only public GitHub GET context required')
    bodies=[]
    for receipt in feedback.get('receipts',[]):
        if receipt.get('kind')!='comments':continue
        for row in receipt.get('evidence',[]):
            require(isinstance(row.get('body'),str)and hashlib.sha256(row['body'].encode()).hexdigest()==row.get('body_sha256'),
                'Actual feedback comment body SHA mismatch')
            bodies.append({key:row[key]for key in('id','author','updated_at','body_sha256','html_url')})
    require(bool(bodies),'Actual public comment body evidence required')
    return dict(root_selected=True,peer_endorsed=False,decision=dref,actual_feedback=fref,
        feedback_observed_utc=feedback['observed_utc'],feedback_comment_evidence=bodies,
        meaning='Root chose this bounded scientific question under existing user authorization; GET is not peer agreement')


def make_preregistration(baseline_summary,output,*,decision_path,feedback_path):
    require(Path(baseline_summary).resolve()==BASELINE_SUMMARY,'Exact original-square canonical reference required')
    plan=drive.make_preregistration(baseline_summary,output);canonical=drive.baseline_item(baseline_summary)
    selection=context_metadata(decision_path,feedback_path,plan['input_sha256']);source=source_metadata(canonical,plan['input_sha256'])
    sourceitem=view.load_case(SOURCE_SUMMARY)
    sine=[c for c in sourceitem['summary']['conditions']if c['id']==SOURCE_ID+'-sine'and c['waveform']=='sine']
    require(len(sine)==1 and sine[0]['actual_fundamental_Hz']==list(PAIR)and sine[0]['source_Vpp_per_output']==1. and sine[0]['phase_deg']==[0.,0.],
        'Exact source-bound nativepost exclusive sine1Vpp0/0 reference required')
    source['cached_sine_electrical_reference']=dict(condition_id=sine[0]['id'],metrics=sine[0]['metrics'],
        actual_coefficient_amplitude_scale=1.,source_summary=str(SOURCE_SUMMARY),source_summary_SHA256=view.sha(SOURCE_SUMMARY),
        native_sine_scalar_archive_claimed=False,recomputed_control_volume_and_probes=True)
    plan.update(schema=SCHEMA,conditions=[dict(c)for c in CONDITIONS],source_geometry=source,root_selection_context=selection,
        waveform_family='sine_control_and_coherent_two_tone_sine',feedback_id='T1-F010-rotation-coherent-shape-interaction',
        scope='Five new drive conditions at fixed rotated-return geometry: one exclusive sine control, four coherent mix drives; no PDE',
        active_frequencies_Hz=list(PAIR),available_native_frequencies_Hz=list(FREQUENCIES),beat_frequency_Hz=30,
        source_Vpp_definition='Control exact analytic1Vpp each; coherent actual whole two-tone Vpp upper1V with raw bracket width<=1uV before50ohm',
        source_Vpp_bracket_width_V=VPP_WIDTH,seed_unitary_only=True,
        direction_count=2074,eight_gate_definitions=screen.GATE_DEFINITIONS,
        resource_limits=dict(CPU_count=1,total_seconds=600,source_load_seconds=60,per_condition_seconds=60,finalization_seconds=60,
            RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,max_added_bytes=2*GIB,cumulative_budget_seconds=policy.effective_limit(policy.load_ledger())),
        canonical_reference='Original four-square4line eight-skin burdens/cutoffs; rotation square1/1 is an unchanged cached control')
    plan['holds']+=['AWG arbitrary two-tone generation, interoutput phase synchronization, signed power sinking and compliance unverified; not experimental-ready',
        'New pure-sine control native volume and40phi computed once; cached nativepost sine electrical/centre-field metrics validated separately',
        'Positive exclusive square3h amplitude bounds do not exclude coherent drive or another geometry',
        '2074 sampled real directions remain a continuous-direction lower bound; no sphere or mesh/contact convergence promotion']
    plan.update(implementation_receipt());plan['input_sha256'].update(plan['implementation_files_sha256'])
    plan['resource_policy_refs']=policy.policy_refs(policy.load_ledger());plan['input_sha256'].update(plan['resource_policy_refs'])
    return plan


def verify_plan(path,output,expected=None):
    digest=view.sha(path);plan=view.read(path)
    require(expected is None or digest==expected,'Preregistration changed during execution')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['new_PDE_conditions']==0 and
        plan['conditions']==[dict(c)for c in CONDITIONS]and plan['baseline_summary']==str(BASELINE_SUMMARY)and
        plan['output_directory']==str(output) and
        plan['direction_count']==2074 and plan['eight_gate_definitions']==screen.GATE_DEFINITIONS and
        plan['source_geometry']['summary_path']==str(SOURCE_SUMMARY) and plan['source_Vpp_bracket_width_V']==VPP_WIDTH,
        'Exact5 rotation sine/coherent conditions/source/output/limits required')
    for name,digest0 in plan['input_sha256'].items():
        p=Path(name);require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and p.is_file()and
            not p.is_symlink()and view.sha(p)==digest0,'Pinned source changed: '+name)
    require(view.read(BASELINE_SUMMARY)['input_sha256']==plan['native_input_sha256'],'Original native manifest changed')
    selection=plan['root_selection_context']
    require(context_metadata(Path(selection['decision']['path']),Path(selection['actual_feedback']['path']),{})==selection,
        'Exact root decision and observed public feedback context changed')
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'],'Committed implementation changed')
    return plan,digest


def derive(basis,geometry,volume_meta,cached,declared,post,scalar,probe,output,deadline,baseline_burdens,baseline_currents,cutoffs,base_screen,checkpoint):
    seed=control_coefficients()if declared['waveform']=='sine'else seed_coefficients(declared['mix_ratio'],declared['phase_deg'])
    try:
        coefficients,sourceproof=condition_coefficients(declared,probe.waveform_statistics,probe.SamplingLimits)
    except ValueError as error:
        if hasattr(error,'source_waveform_evidence'):drive.write_json(output/'source-waveform-failure.json',error.source_waveform_evidence)
        raise
    checkpoint('normalized_source',condition_id=declared['id'])
    spectra=post._spectra(basis,coefficients);active={f:spectra[f]for f in PAIR}
    electrical=post._electrical(basis,coefficients,geometry,deadline)
    padcurrents=physical_pad_currents(basis,coefficients)
    regression=validate_cached_sine(electrical,cached['cached_sine_reference']['metrics'])if declared['waveform']=='sine'else None
    losses=waveform.layer_losses_from_matrices({f:r['loss']for f,r in basis['f'].items()},
        {f:r['source']for f,r in basis['f'].items()},coefficients,electrical)
    skin=waveform.bulk_skin_current_density(active,basis['grid'],geometry['gamma_S_m'])
    burdens=frequency.candidate_burdens(electrical,skin,losses);currents=electrical['source_current_RMS_by_output_mA']
    checkpoint('volume_projection',condition_id=declared['id'])
    weights={r:cached['arrays']['region_'+r+'_m3']for r in('total','target','surface_0_5','subsurface_5_10','remaining','off_target')}
    native=scalar.evaluate_volume(active,basis['grid'],volume_meta,fundamental_frequencies_Hz=list(PAIR),region_weights=weights,
        fibonacci_count=2048,chunk_cells=256,deadline_monotonic=deadline)
    arrays={k:native['scalars'][k]for k in(*volume.METRICS,'maxTIS_direction_index')}
    arrays.update({'region_'+k+'_m3':v for k,v in native['region_weights_m3'].items()})
    regions=volume.region_weights(arrays,basis['grid'],basis['metadata'])
    np.savez_compressed(output/'volume.npz',**arrays);drive.write_json(output/'native-volume-metrics.json',native['metrics'])
    balance=carrier.carrier_metrics(active[3000],active[3030],arrays['maxTIS_direction_index'],arrays['maxTIS'],arrays['fixedTIS'])
    provenance=dict(source_run_id=cached['item']['run'].name,source_condition_id=cached['condition']['id'],
        source_candidate_id=declared['id'],input_sha256=post._digest(basis['hashes']),code_sha256=view.sha(__file__),result_sha256=post._digest(basis['validation']))
    probes=probe.evaluate_layered_probe(basis['grid'],{f:basis['f'][f]['potential']for f in PAIR},
        {f:basis['f'][f]['field']for f in PAIR},geometry,{f:coefficients[f]for f in PAIR},provenance=provenance,
        fundamental_frequencies_Hz=list(PAIR),plus_pitch_mm=5.,tip_gap_mm=5.,depths_mm=(5.,10.,15.,20.))
    require(probes['status']=='complete'and probes['numerical_checks']['all_passed']and len(probes['measurements'])==40,
        'All40 actual coherent nativephi/E probes required')
    for row in probes['measurements']:row.pop('time_plot',None)
    probes.update(actual_source_Vpp_intervals_V=sourceproof['source_Vpp_intervals_V'],actual_fundamental_Hz=list(PAIR),
        source_drive='Exclusive sine control'if declared['waveform']=='sine'else'Both actual fundamentals coherent on both outputs')
    drive.write_json(output/'probes.json',probes)
    probecheck=waveform.probe_check(dict(id=declared['id'],probe40=probes))
    fieldcheck=waveform.field_check(dict(id=declared['id'],waveform=declared['waveform'],actual_fundamental_Hz=list(PAIR),metrics=electrical))
    modes=normalization_modes(burdens,baseline_burdens,sum(currents),sum(baseline_currents),sourceproof['source_Vpp_intervals_V'])
    for mode in modes.values():
        mode['source_Vpp_definition']='Actual full source waveform max-minus-min before50ohm; analytic control or coherent bounds, not per-tone Vpp'
        mode['unitary_after_Vpp_normalization']=sourceproof['unitary_after_Vpp_normalization']
    for name,mode in modes.items():
        scale=mode['amplitude_scale'];mode['regions']=volume.summarize_regions(arrays,regions,basis['grid'],scale,cutoffs)
        mode['source_output_RMS_by_output_mA']=[v*scale for v in currents]
        mode['signed_per_output_power_evidence']=signed_output_powers(electrical,scale)
        mode['physical_pad_current_RMS_mA']=[v*scale for v in padcurrents['physical_pad_current_RMS_mA']]
        mode['probe40_unloaded']=drive.scaled_probe_rows(probes,scale)
        require(time.monotonic()<deadline,'Per-condition60s full-metrics deadline exceeded')
    checks=screen.screen_checks(dict(normalizations=modes),base_screen)
    result=dict(schema='task1-rotation-coherent-condition-v1',status='calculated_unadopted',**declared,
        source_case_id=cached['item']['case']['id'],source_run_id=cached['item']['run'].name,
        source_commit=cached['item']['registration']['source_commit'],configuration_sha256=basis['metadata']['config_sha256'],
        source_circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
            return_topology='all_return_pads_ideal_common_GND',source_resistance_ohm=50,
            active_frequencies_by_output_Hz={str(o):[f for f in PAIR if coefficients[f][o]!=0]for o in range(2)},uncommanded_frequency_termination='0V through50ohm',
            hardware_multitone_phase_sync_power_sink_compliance='unverified; not experimental-ready'),
        actual_fundamental_Hz=list(PAIR),beat_frequency_Hz=30,active_frequencies_Hz=list(PAIR),harmonics_active=False,
        cached_sine_electrical_regression=regression,
        seed_coefficients={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in seed.items()},
        coefficient_vectors={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in coefficients.items()},
        source_waveform=sourceproof,electrical_metrics=electrical,bulk_skin_J=skin,layer_contact_source_losses=losses,
        physical_pad_current_evidence=padcurrents,output_power_evidence=signed_output_powers(electrical),
        centre20_directional_E_TIS=dict(point_mm=[0.,0.,20.],unit='V/m',
            scope='Layered interpolated electric field at central20mm point; directional fundamental envelope widths, not ROI metrics or probe voltage',
            axes={axis:float(2*min(abs(complex(row['real_V_m'][index],row['imaginary_V_m'][index]))
                for row in electrical['centre_field_spectrum']if row['frequency_Hz']in PAIR))for index,axis in enumerate(('X','Y','Z'))}),
        native_volume_XYZ_directional_scalar_archives='not produced in this bounded scout; fixed diagonal and2074maximum volume arrays are supplied',
        native_volume_metrics=native['metrics'],normalizations=modes,raw_mode='raw_1Vpp',
        source_geometry_unchanged=True,shared_original_square_cutoffs_V_m=cutoffs,
        raw_carrier_balance_regions={region:{key:carrier.weighted(value,w,basis['grid'])for key,value in balance.items()
            if key in('carrier0_RMS_V_m','carrier1_RMS_V_m','combined_fundamental_RMS_V_m','max_direction_balance','fixed_direction_balance')}
            for region,w in regions.items()},probe_waveform_audit=probecheck,field_waveform_audit=fieldcheck,
        canonical_skin_cap_screen=dict(checks=checks,all_screen_checks_passed=all(c['passed']for c in checks),
            failed_checks=[c['name']for c in checks if not c['passed']],normalization='skin_contact_only'),
        new_PDE=0,candidate_adopted=False,instrument_loading_validated=False,full_convergence_validated=False,experimentally_validated=False)
    drive.write_json(output/'condition.json',result)
    return dict(id=declared['id'],status=result['status'],waveform=declared['waveform'],source_Vpp_intervals_V=sourceproof['source_Vpp_intervals_V'],
        canonical_screen_all_passed=all(c['passed']for c in checks),artifacts={name:dict(path=str(output/name),SHA256=view.sha(output/name))
            for name in('condition.json','probes.json','volume.npz','native-volume-metrics.json')})


def execute(plan,output,deadline,checkpoint):
    canonical=drive.baseline_item(BASELINE_SUMMARY);baseline=volume.load_native(canonical)
    item=view.load_case(SOURCE_SUMMARY);cached=volume.load_native(item)
    require(item['signature']==canonical['signature']and np.array_equal(cached['grid'],baseline['grid']),'Source/canonical grid/material/contact identity differs')
    post,scalar,probe=drive.import_frozen(canonical['run'],plan)
    basis=post._load_basis(item['run']/'bases'/item['case']['id'],item['case'],min(deadline,time.monotonic()+60))
    require(basis['hashes']==plan['source_geometry']['native_input_sha256']and np.array_equal(basis['grid'],cached['grid']),
        'Rotation geometry native basis/source hashes differ')
    cached['cached_sine_reference']=plan['source_geometry']['cached_sine_electrical_reference']
    geometry,volume_meta=post._geometry(basis,item['case']);burden,currents=volume.burdens(canonical,baseline['condition'])
    cutoffs={metric:{region+'_'+stat:volume.weighted_statistics(baseline['arrays'][metric],baseline['regions'][region])[stat]
        for region in(volume.PRIMARY,volume.SLAB)for stat in('mean','p10')}for metric in volume.METRICS}
    base_screen=dict(normalizations={'skin_contact_only':dict(regions=volume.summarize_regions(baseline['arrays'],baseline['regions'],basis['grid'],1.,cutoffs))})
    results=[]
    for declared in plan['conditions']:
        per=min(deadline,time.monotonic()+60);signal.setitimer(signal.ITIMER_REAL,max(.001,per-time.monotonic()))
        folder=output/declared['id'];folder.mkdir();checkpoint('condition_start',condition_id=declared['id'])
        results.append(derive(basis,geometry,volume_meta,cached,declared,post,scalar,probe,folder,per,burden,currents,cutoffs,base_screen,checkpoint))
        checkpoint('condition_complete',condition_id=declared['id'])
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    return dict(schema='task1-rotation-coherent-scout-v1',status='calculated_unadopted',conditions=results,new_PDE=0,
        cached_controls=plan['source_geometry']['cached_controls'],cached_control_volume=plan['source_geometry']['cached_control_volume'],
        source_geometry=plan['source_geometry'],canonical_square_reference=dict(condition_id=baseline['condition']['id'],summary_path=str(BASELINE_SUMMARY),
            burdens=burden,source_current_RMS_by_output_mA=currents,screen_baseline=base_screen),
        actual_fundamental_Hz=list(PAIR),all_active_frequencies_Hz=list(PAIR),beat_frequency_Hz=30,waveform_family='sine_control_and_coherent_two_tone_sine',
        comparison='One new sine control plus four coherent sine mixes at unchanged rotated-return geometry; canonical original square8 skin caps',
        candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,holds=plan['holds'],
        root_selection_context=plan['root_selection_context'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--prepare',type=Path);group.add_argument('--preregistration',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--baseline-summary',type=Path,default=BASELINE_SUMMARY)
    parser.add_argument('--decision',type=Path);parser.add_argument('--feedback',type=Path)
    args=parser.parse_args();output=args.output.resolve()
    require(output.is_relative_to(ROOT/'docs')and not output.exists(),'Unique new docs output directory required')
    with(ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledger_path);cap=60 if args.prepare else 600
        require(policy.remaining_seconds(ledger)>=cap,'Finite admission budget missing')
        require(shutil.disk_usage(output.parent).free>=2*GIB+256*1024**2,'Preserve2GiB reserve plus bounded artifacts')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();deadline=started+cap
        status='failed_preserved';failure=None;state={};counter=0;mutex=threading.RLock();stop=threading.Event();thread=None
        def guard():
            require(core.rss(os.getpid())<3*GIB,'Existing3GiB RSS cap exceeded')
            require(shutil.disk_usage(output.parent).free>=2*GIB,'Existing2GiB disk reserve exhausted')
            if output.exists():require(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=2*GIB,'New artifacts exceed2GiB cap')
        def checkpoint(phase,**extra):
            nonlocal counter
            with mutex:
                guard();counter+=1;state.update(phase=phase,status=status if phase=='complete'else'running',pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),
                    updated_utc=core.now(),elapsed_seconds=time.monotonic()-started,**extra)
                drive.write_json(output/f'checkpoint-{counter:03d}-{phase}.json',dict(state));core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5):
                try:
                    with mutex:guard();core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-started))
                except BaseException as error:
                    state['resource_guard_failure']=str(error);os.kill(os.getpid(),signal.SIGTERM);return
        def interrupted(signum,frame):raise TimeoutError('Controlled600s/60s-source-or-condition stop signal '+str(signum))
        previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for signum in previous:signal.signal(signum,interrupted)
        signal.setitimer(signal.ITIMER_REAL,60)
        try:
            if args.prepare:
                require(not args.prepare.exists()and not args.prepare.resolve().is_relative_to(output),
                    'New preregistration must remain outside the untouched actual output directory')
                plan=make_preregistration(args.baseline_summary,output,decision_path=args.decision,feedback_path=args.feedback);args.prepare.parent.mkdir(parents=True,exist_ok=True)
                drive.write_json(args.prepare,plan);status='preregistered_not_executed'
            else:
                output.mkdir();thread=threading.Thread(target=heartbeat,daemon=True);thread.start();checkpoint('verify_plan')
                plan,plan_sha=verify_plan(args.preregistration.resolve(),output)
                result=execute(plan,output,deadline,checkpoint)
                verify_plan(args.preregistration.resolve(),output,expected=plan_sha);guard()
                result.update(implementation_receipt(),preregistration=dict(path=str(args.preregistration.resolve()),SHA256=plan_sha),
                    input_sha256=plan['input_sha256'],inputs_unchanged=True,resources=dict(CPU_count=1,max_batch_seconds=600,max_condition_seconds=60,
                        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,wall_seconds=time.monotonic()-started,
                        cumulative_budget_limit_seconds=policy.effective_limit(ledger),new_PDE=0))
                drive.write_json(output/'summary.json',result);status=result['status'];checkpoint('complete')
        except BaseException as error:
            failure=type(error).__name__+': '+str(error)
            if output.exists():drive.write_json(output/'failure.json',dict(status=status,error=failure,phase=state.get('phase'),
                condition_id=state.get('condition_id'),new_PDE=0,partial_artifacts_preserved=True,automatic_retry=False))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='rotation_coherent_prepare'if args.prepare else'rotation_coherent_scout',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
