#!/usr/bin/env python3
"""Six finite net-return-current drive re-syntheses of two cached adjacent bases.

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

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
FREQUENCIES=(3000,3030,9000,9090)
PAIR=(3000,3030)
SCHEMA='task1-return-current-drive-scout-preregistration-v1'
CONTROL_SUMMARY=ROOT/'docs/cloud-next-frequency-20261021T104000Z/summary.json'
CONTROL_ID='sine-3000-3030-beat30'
BASELINE_SUMMARY=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json'
SOURCE_CASES=(dict(geometry='adjacent-square',run_id='cloud-finite-loop-20261020T002600Z-fine',case_id='adjacent-square15-xy80'),
    dict(geometry='adjacent-cross',run_id='cloud-adjacent-cross-20261021T164000Z',case_id='balancedcross225-adjacent-sources-xy80'))
CONDITIONS=tuple(dict(id=f"return-net-{label}-tau{tag}",geometry=source['geometry'],tau=tau)
    for source,label in zip(SOURCE_CASES,('square','cross'))for tau,tag in((0.,'0'),(.5,'0p5'),(1.,'1')))
RESPONSE_RESOLUTION=2e-6
VPP_WIDTH=1e-6
LEVELS=(128,256,512,1024,2048,2560)
require=drive.require


def operator_diagnostics(response):
    r=np.asarray(response,complex)
    require(r.shape==(4,2)and np.isfinite(r).all(),'Finite four-pad/two-output response required')
    norm=max(float(np.max(abs(r))),1e-30)
    require(float(np.max(abs(r.sum(axis=0))))/norm<=2e-6,'Full physical-pad response KCL failed')
    singular=np.linalg.svd(r[2:4],compute_uv=False)
    if not(singular[0]>0 and singular[-1]/singular[0]>RESPONSE_RESOLUTION):
        error=ValueError('Return response rank/SVD unresolved at native2e-6 resolution; do not construct weights')
        error.return_response_evidence=dict(response_real_A=r.real.tolist(),response_imaginary_A=r.imag.tolist(),
            return_singular_values_A=singular.tolist(),relative_resolution=RESPONSE_RESOLUTION)
        raise error
    return dict(full_response_singular_values_A=np.linalg.svd(r,compute_uv=False).tolist(),return_singular_values_A=singular.tolist(),return_relative_minimum_singular_value=float(singular[-1]/singular[0]),
        return_condition_number=float(singular[0]/singular[-1]),relative_resolution=RESPONSE_RESOLUTION)


def return_response(density,contacts,source):
    d=np.asarray(density,complex);source=np.asarray(source,complex)
    require(getattr(contacts.dtype,'names',None)and {'pad','area_m2'}<=set(contacts.dtype.names),'Explicit native contact pad/area fields required')
    pad=np.asarray(contacts['pad']);area=np.asarray(contacts['area_m2'],float)
    require(d.shape==(2,len(area))and source.shape==(2,2)and np.isfinite(d).all()and np.isfinite(source).all()and
        np.isfinite(area).all()and np.all(area>0)and np.isfinite(pad).all()and np.all(pad==np.round(pad))and
        set(pad.astype(int))==set(range(4)),'Channel-major finite complex density, physical4pads and positive areas required')
    r=np.asarray([np.sum(d[:,pad==p]*area[pad==p],axis=1)for p in range(4)])
    norm=max(float(np.max(abs(r))),float(np.max(abs(source))),1e-30)
    error=float(np.max(abs(r[:2]-source))/norm)
    require(error<=2e-6,'Integrated physical signal-pad/source response mismatch')
    proof=operator_diagnostics(r);proof.update(source_groupwise_relative_error=error,
        KCL_groupwise_relative_error=float(np.max(abs(r.sum(axis=0)))/norm),
        physical_pad_area_m2=[float(area[pad==p].sum())for p in range(4)],
        response_peak_real_A=r.real.tolist(),response_peak_imaginary_A=r.imag.tolist())
    return r,proof


def design_coefficients(response3000,response3030,tau):
    require(type(tau)in(int,float)and tau in(0.,.5,1.),'Registered tau0/.5/1 only')
    matrices=[np.asarray(response3000,complex),np.asarray(response3030,complex)]
    proofs=[operator_diagnostics(r)for r in matrices]
    denominators=[matrices[0][2,1],matrices[1][3,0]]
    for r,d in zip(matrices,denominators):
        require(abs(d)/max(float(np.max(abs(r[2:4]))),1e-30)>RESPONSE_RESOLUTION,'Return-response denominator unresolved')
    q0=-matrices[0][2,0]/denominators[0];q1=-matrices[1][3,1]/denominators[1]
    coefficients={3000:np.array([1.,tau*q0],complex),3030:np.array([tau*q1,1.],complex),9000:np.zeros(2,complex),9090:np.zeros(2,complex)}
    residuals=[]
    for f,r,pad in zip(PAIR,matrices,(2,3)):
        actual=r@coefficients[f];predicted=(1-tau)*(r[pad,0]if f==3000 else r[pad,1])
        norm=max(float(np.max(abs(actual[:2]))),1e-30);prediction_error=float(abs(actual[pad]-predicted)/norm)
        require(prediction_error<=2e-6,'Cancellation transfer prediction differs')
        relative=float(abs(actual[pad])/norm)
        if tau==1:require(relative<=2e-6,'Full return cancellation fails native2e-6 residual')
        residuals.append(dict(frequency_Hz=f,wrong_return_pad=pad,actual_peak_current_real_A=float(actual[pad].real),
            actual_peak_current_imaginary_A=float(actual[pad].imag),net_current_relative_error=relative,prediction_relative_error=prediction_error))
    return coefficients,dict(tau=tau,q0=dict(real=float(q0.real),imaginary=float(q0.imag)),q1=dict(real=float(q1.real),imaginary=float(q1.imag)),
        return_operator_diagnostics=proofs,wrong_return_predictions=residuals,
        coefficient_convention='Relative complex cosine command coefficients [1,tau*q0] at3000Hz, [tau*q1,1] at3030Hz; peak0.5V basis,+jwt',
        common_GND_nodes=1,isolated_pairs_claimed=False,zero_net_current_implies_zero_local_J=False)


def tone_activity(coefficients):
    return {str(output):[f for f in PAIR if abs(coefficients[f][output])>0]for output in range(2)}


def normalize_source(coefficients,waveform_statistics,SamplingLimits):
    require(set(coefficients)==set(FREQUENCIES),'All four available source frequencies required')
    seed={f:np.asarray(c,complex).copy()for f,c in coefficients.items()}
    require(all(c.shape==(2,)and np.isfinite(c).all()for c in seed.values())and not np.any(seed[9000])and not np.any(seed[9090])and
        all(any(abs(seed[f][j])>0 for f in PAIR)for j in range(2)),'Finite actual source ABI; harmonics zero; each output driven required')
    brackets=[];histories=[]
    for output in range(2):
        history=[];accepted=None
        for level in LEVELS:
            sampling=SamplingLimits(samples_per_highest_cycle=level,max_statistics_samples=262144,plot_duration_s=min(.002,4000/(3030*level)))
            stats=waveform_statistics(list(PAIR),np.asarray([.5*seed[f][output]for f in PAIR]),list(PAIR),sampling=sampling)
            lo,hi=float(stats['Vpp_lower_V']),float(stats['Vpp_upper_V'])
            require(math.isfinite(lo)and math.isfinite(hi)and 0<lo<=hi,'Positive finite actual source Vpp interval required')
            history.append(dict(samples_per_highest_cycle=level,raw_Vpp_lower_V=lo,raw_Vpp_upper_V=hi))
            if (hi-lo)/hi<=VPP_WIDTH:accepted=(lo,hi);break
        if accepted is None:
            error=ValueError('Source global full-wave1uV Vpp bracket gate failed')
            error.source_waveform_evidence=dict(status='held_source_Vpp_bracket',output_index=output,levels=history)
            raise error
        brackets.append(accepted);histories.append(history)
    scale=1/max(hi for lo,hi in brackets);intervals=[[lo*scale,hi*scale]for lo,hi in brackets]
    require(max(hi-lo for lo,hi in intervals)<=VPP_WIDTH+1e-14,'Global source raw1uV bracket gate failed')
    return {f:c*scale for f,c in seed.items()},dict(global_scale=scale,global_normalization=True,independent_column_normalization=False,
        source_Vpp_intervals_V=intervals,maximum_bracket_width_V=max(hi-lo for lo,hi in intervals),hard_maximum_raw_bracket_width_V=VPP_WIDTH,
        source_Vpp_upper_by_output_V=[hi for lo,hi in intervals],raw_source_upper_max_V=1.,outputs=[dict(output_index=i,levels=h)for i,h in enumerate(histories)],
        seed_unitary=False,unitary_after_Vpp_normalization=False,source_peak_basis_V=.5,source_resistance_ohm=50,common_period_s=1/30,
        interpretation='ONE global upper-bound scaling preserves every intra-frequency ratio/cancellation. Each output<=1Vpp; only maximum output upper is1Vpp; not each output exactly1Vpp')


def normalization_modes(candidate,baseline,current_sum,baseline_current_sum,source_intervals):
    intervals=np.asarray(source_intervals,float)
    require(intervals.shape==(2,2)and np.isfinite(intervals).all()and np.all(intervals[:,0]>0)and
        np.all(intervals[:,0]<=intervals[:,1])and np.all(intervals[:,1]<=1+1e-14)and
        np.all(intervals[:,1]-intervals[:,0]<=VPP_WIDTH+1e-14),'Verified two actual1Vpp source intervals required')
    modes=volume.normalization_modes(candidate,baseline,current_sum,baseline_current_sum)
    for mode in modes.values():
        scale=mode['amplitude_scale'];mode.pop('source_Vpp_per_output',None)
        mode['actual_source_Vpp_intervals_V']=(intervals*scale).tolist()
        mode['source_Vpp_upper_by_output_V']=(intervals[:,1]*scale).tolist()
        mode['source_Vpp_definition']='actual max-minus-min of commanded nonzero-tone source spectrum before50ohm; bounds, not each tone Vpp'
        mode['unitary_after_Vpp_normalization']=False
    return modes


def implementation_receipt():
    modules=(drive,volume,waveform,carrier,frequency,power,screen,core,policy,view,ranking)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_return_current_drive_scout.py',ROOT/'tools/task1_candidate_ranking.py',
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
    require(decision.get('schema')=='task1-return-current-drive-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and
        decision.get('conditions')==[dict(c)for c in CONDITIONS],'Exact root-selected6 return-current conditions required; peer endorsement must not be inferred')
    refs=decision.get('input_sha256');require(isinstance(refs,dict)and bool(refs),'Root decision must bind completed scientific evidence')
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


def source_metadata(declared,canonical,refs):
    path=ROOT/'data-native'/declared['run_id']/'postprocess'/declared['case_id']/'summary.json'
    item=view.load_case(path);case=item['case'];meta=item['summary']['mesh_metadata'];circuit=item['circuit']
    require(item['signature']==canonical['signature'],'Same native grid/material/contact/ROI comparison signature required')
    require(circuit['n_pads']==4 and circuit['n_outputs']==2 and circuit['n_return_nodes']==1 and
        circuit['pad_to_node']=={'0':'out0','1':'out1','2':'GND','3':'GND'}and circuit['source_resistance_ohm']==50,
        'Exactly4pads/2outputs/commonGND50ohm required')
    config=view.properties(case['config_file']);expected=[[-10.,-10.],[10.,-10.],[10.,10.],[-10.,10.]]
    require(all([float(config[f'pad.{i}.x_mm']),float(config[f'pad.{i}.y_mm'])]==xy for i,xy in enumerate(expected)),
        'Actual physical pad coordinates/order must match adjacent source0/1 and wrong returns2/3')
    require(meta['h_xy_mm']==.625 and meta['sc_cells']==2 and meta['bulk_layer_counts']==[14,14,40]and meta['cells']==351680,
        'Exact original same-grid fine mesh required')
    refs.update(ranking.input_refs(item));refs.update(item['summary']['input_sha256'])
    refs[str(Path(case['mask_file']))]=case['mask_sha256']
    archive=path.parent/'volume.npz';refs[str(archive)]=item['summary']['artifacts']['files']['volume.npz']['SHA256']
    manifest=item['run']/'frozen-source-manifest.json';refs[str(manifest)]=view.sha(manifest)
    for name in ('selectivity_postprocess.py','selectivity_volume.py','layered_probe_analysis.py','explore_tis.py','explore_inputs.py'):
        actual=item['run']/'frozen-source/tis-java'/name;original=canonical['run']/'frozen-source/tis-java'/name
        require(view.sha(actual)==view.sha(original),'Do not mix frozen numerical helper versions: '+name)
        refs[str(actual)]=view.sha(actual)
    return dict(**declared,summary_path=str(path),summary_SHA256=view.sha(path),source_commit=item['registration']['source_commit'],
        configuration_sha256=case['config_sha256'],mask_sha256=case['mask_sha256'],physical_pad_centres_mm=expected,
        native_input_sha256=item['summary']['input_sha256'],circuit=circuit,comparison_signature=item['signature'])


def make_preregistration(baseline_summary,output,*,decision_path,feedback_path):
    require(Path(baseline_summary).resolve()==BASELINE_SUMMARY,'Exact original canonical square baseline required')
    plan=drive.make_preregistration(baseline_summary,output);canonical=drive.baseline_item(baseline_summary)
    selection=context_metadata(decision_path,feedback_path,plan['input_sha256'])
    sources=[source_metadata(src,canonical,plan['input_sha256'])for src in SOURCE_CASES]
    plan.update(schema=SCHEMA,conditions=[dict(c)for c in CONDITIONS],source_cases=sources,root_selection_context=selection,
        waveform='coherent_two_frequency_return_net_current',feedback_id='T1-F010-return-net-current-drive',
        scope='Two cached adjacent geometries x tau0,.5,1; no new PDE, source ports, pads or ground nodes',
        source_Vpp_definition='ONE global factor1/max(source_Vpp_upper_by_output), raw output vector<=1Vpp with maxupper1V; raw bracket<=1uV; later modes scale intervals exactly',
        source_Vpp_bracket_width_V=VPP_WIDTH,response_relative_resolution=RESPONSE_RESOLUTION,direction_count=2074,
        active_frequencies_Hz=list(PAIR),available_native_frequencies_Hz=list(FREQUENCIES),beat_frequency_Hz=30,
        eight_gate_definitions=screen.GATE_DEFINITIONS,
        wrong_return_definition={'3000':2,'3030':3},ground_topology='One ideal commonGND node remains; zero net pad current does not imply zero local current or isolated pairs',
        resource_limits=dict(CPU_count=1,total_seconds=600,source_operator_seconds=60,per_condition_seconds=60,finalization_seconds=60,
            RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,max_added_bytes=2*GIB,cumulative_budget_seconds=policy.effective_limit(policy.load_ledger())),
        opposite_control_response_status='Not evaluated; canonical opposite square response not loaded or assigned a measured rank from symmetry',
        holds=plan['holds']+['No isolated pairs, local contact J cancellation, mesh/contact convergence or hardware multitone/sink validation claimed'])
    plan.update(implementation_receipt());plan['input_sha256'].update(plan['implementation_files_sha256'])
    plan['resource_policy_refs']=policy.policy_refs(policy.load_ledger());plan['input_sha256'].update(plan['resource_policy_refs'])
    return plan


def verify_plan(path,output,expected=None):
    digest=view.sha(path);plan=view.read(path)
    require(expected is None or digest==expected,'Preregistration changed during execution')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['new_PDE_conditions']==0 and
        plan['conditions']==[dict(c)for c in CONDITIONS]and plan['baseline_summary']==str(BASELINE_SUMMARY)and
        plan['output_directory']==str(output)and plan['source_Vpp_bracket_width_V']==VPP_WIDTH and
        plan['direction_count']==2074 and plan['eight_gate_definitions']==screen.GATE_DEFINITIONS and
        plan['response_relative_resolution']==RESPONSE_RESOLUTION and
        [{k:src[k]for k in('geometry','run_id','case_id')}for src in plan['source_cases']]==list(SOURCE_CASES),
        'Exact6 return-net-current conditions/source/output/limits required')
    for name,digest0 in plan['input_sha256'].items():
        p=Path(name);require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and p.is_file()and
            not p.is_symlink()and view.sha(p)==digest0,'Pinned source changed: '+name)
    require(view.read(BASELINE_SUMMARY)['input_sha256']==plan['native_input_sha256'],'Original native manifest changed')
    selection=plan['root_selection_context']
    require(context_metadata(Path(selection['decision']['path']),Path(selection['actual_feedback']['path']),{})==selection,
        'Exact root decision and observed public feedback context changed')
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'],'Committed implementation changed')
    return plan,digest


def signed_output_powers(metrics,scale=1.):
    evidence=power.output_power_evidence(metrics,amplitude_scale=scale)
    evidence['requires_source_power_absorption']=any(row['ideal_source_power_W']<0 or
        any(tone['ideal_source_power_W']<0 for tone in row['spectrum'])for row in evidence['outputs'])
    evidence['has_negative_metal_delivered_power']=any(row['metal_delivered_power_W']<0 for row in evidence['outputs'])
    evidence['requires_output_power_absorption']=any(row['metal_delivered_power_W']<0 or
        any(tone['metal_delivered_power_W']<0 for tone in row['spectrum'])for row in evidence['outputs'])
    evidence['has_negative_per_frequency_ideal_source_power']=any(tone['ideal_source_power_W']<0 for row in evidence['outputs']for tone in row['spectrum'])
    evidence['hardware_absorption_and_compliance_validated']=False
    return evidence


def physical_pad_currents(basis,coefficients):
    rows=[];squares=np.zeros(4);errors=[]
    for f in PAIR:
        row=basis['f'][f];contacts=row['contacts'];pad=contacts['pad'].astype(int);area=contacts['area_m2']
        density=coefficients[f]@row['density'];currents=np.asarray([np.sum(density[pad==p]*area[pad==p])for p in range(4)])
        source=row['source']@coefficients[f];den=max(float(np.max(abs(currents))),float(np.max(abs(source))),1e-30)
        kcl=float(abs(currents.sum())/den);source_error=float(np.max(abs(currents[:2]-source))/den)
        require(max(kcl,source_error)<=2e-6,'Actual coherent physical-pad/source KCL gate failed')
        squares+=abs(currents)**2/2;errors.append(max(kcl,source_error))
        rows.append(dict(frequency_Hz=f,pad_current_peak_real_A=currents.real.tolist(),pad_current_peak_imaginary_A=currents.imag.tolist(),
            KCL_groupwise_relative_error=kcl,source_groupwise_relative_error=source_error))
    return dict(physical_pads=4,independent_outputs=2,common_GND_return_pads=[2,3],spectrum=rows,
        physical_pad_current_RMS_mA=(np.sqrt(squares)*1000).tolist(),maximum_groupwise_relative_error=max(errors))


def derive(basis,geometry,volume_meta,cached,declared,post,scalar,probe,output,deadline,baseline_burdens,baseline_currents,cutoffs,base_screen,checkpoint,responses):
    seed,designproof=design_coefficients(responses[3000],responses[3030],declared['tau'])
    try:
        coefficients,sourceproof=normalize_source(seed,probe.waveform_statistics,probe.SamplingLimits)
    except ValueError as error:
        if hasattr(error,'source_waveform_evidence'):drive.write_json(output/'source-waveform-failure.json',error.source_waveform_evidence)
        raise
    checkpoint('normalized_source',condition_id=declared['id'])
    spectra=post._spectra(basis,coefficients);active={f:spectra[f]for f in PAIR}
    electrical=post._electrical(basis,coefficients,geometry,deadline)
    padcurrents=physical_pad_currents(basis,coefficients)
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
        source_drive='Actual per-output activity from coefficients; tau0 exclusive, other tau coherent',
        actual_tone_activity_Hz=tone_activity(coefficients))
    drive.write_json(output/'probes.json',probes)
    probecheck=waveform.probe_check(dict(id=declared['id'],probe40=probes))
    fieldcheck=waveform.field_check(dict(id=declared['id'],waveform='coherent_two_tone_sine',actual_fundamental_Hz=list(PAIR),metrics=electrical))
    modes=normalization_modes(burdens,baseline_burdens,sum(currents),sum(baseline_currents),sourceproof['source_Vpp_intervals_V'])
    for name,mode in modes.items():
        scale=mode['amplitude_scale'];mode['regions']=volume.summarize_regions(arrays,regions,basis['grid'],scale,cutoffs)
        mode['source_output_RMS_by_output_mA']=[v*scale for v in currents]
        mode['signed_per_output_power_evidence']=signed_output_powers(electrical,scale)
        mode['physical_pad_current_RMS_mA']=[v*scale for v in padcurrents['physical_pad_current_RMS_mA']]
        mode['probe40_unloaded']=drive.scaled_probe_rows(probes,scale)
        require(time.monotonic()<deadline,'Per-condition60s full-metrics deadline exceeded')
    checks=screen.screen_checks(dict(normalizations=modes),base_screen)
    result=dict(schema='task1-return-current-drive-condition-v1',status='calculated_unadopted',**declared,
        source_case_id=cached['item']['case']['id'],source_run_id=cached['item']['run'].name,
        source_commit=cached['item']['registration']['source_commit'],configuration_sha256=basis['metadata']['config_sha256'],
        source_circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
            return_topology='all_return_pads_ideal_common_GND',source_resistance_ohm=50,
            active_frequencies_by_output_Hz=tone_activity(coefficients),uncommanded_frequency_termination='0V through50ohm',
            hardware_multitone_phase_sync_power_sink_compliance='unverified; not experimental-ready'),
        actual_fundamental_Hz=list(PAIR),beat_frequency_Hz=30,active_frequencies_Hz=list(PAIR),harmonics_active=False,
        seed_coefficients={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in seed.items()},
        coefficient_vectors={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in coefficients.items()},
        source_waveform=sourceproof,return_current_design=designproof,
        return_cancellation_validation=cancellation_validation(basis,coefficients,declared['tau']),electrical_metrics=electrical,bulk_skin_J=skin,layer_contact_source_losses=losses,
        physical_pad_current_evidence=padcurrents,output_power_evidence=signed_output_powers(electrical),
        centre20_directional_E_TIS=dict(point_mm=[0.,0.,20.],unit='V/m',
            scope='Layered interpolated electric field at central20mm point; directional fundamental envelope widths, not ROI metrics or probe voltage',
            axes={axis:float(2*min(abs(complex(row['real_V_m'][index],row['imaginary_V_m'][index]))
                for row in electrical['centre_field_spectrum']if row['frequency_Hz']in PAIR))for index,axis in enumerate(('X','Y','Z'))}),
        native_volume_XYZ_directional_scalar_archives='not produced in this bounded scout; fixed diagonal and2074maximum volume arrays are supplied',
        native_volume_metrics=native['metrics'],normalizations=modes,shared_original_square_cutoffs_V_m=cutoffs,
        raw_carrier_balance_regions={region:{key:carrier.weighted(value,w,basis['grid'])for key,value in balance.items()
            if key in('carrier0_RMS_V_m','carrier1_RMS_V_m','combined_fundamental_RMS_V_m','max_direction_balance','fixed_direction_balance')}
            for region,w in regions.items()},probe_waveform_audit=probecheck,field_waveform_audit=fieldcheck,
        canonical_skin_cap_screen=dict(checks=checks,all_screen_checks_passed=all(c['passed']for c in checks),
            failed_checks=[c['name']for c in checks if not c['passed']],normalization='skin_contact_only'),
        new_PDE=0,candidate_adopted=False,instrument_loading_validated=False,full_convergence_validated=False,experimentally_validated=False)
    drive.write_json(output/'condition.json',result)
    return dict(id=declared['id'],status=result['status'],geometry=declared['geometry'],tau=declared['tau'],
        canonical_screen_all_passed=all(c['passed']for c in checks),artifacts={name:dict(path=str(output/name),SHA256=view.sha(output/name))
            for name in('condition.json','probes.json','volume.npz','native-volume-metrics.json')})


def cancellation_validation(basis,coefficients,tau):
    result=[]
    for f,wrong in ((3000,2),(3030,3)):
        row=basis['f'][f];contacts=row['contacts'];pad=contacts['pad'].astype(int);area=contacts['area_m2'];j=coefficients[f]@row['density']
        bypad=np.asarray([np.sum(j[pad==p]*area[pad==p])for p in range(4)]);current=row['source']@coefficients[f]
        den=max(float(np.max(abs(current))),1e-30);residual=float(abs(bypad[wrong])/den)
        if tau==1:require(residual<=2e-6,'Actual globally normalized density full-cancellation residual exceeds2e-6/source current')
        result.append(dict(frequency_Hz=f,wrong_return_pad=wrong,net_current_real_A=float(bypad[wrong].real),
            net_current_imaginary_A=float(bypad[wrong].imag),net_current_over_max_source_current=residual,
            wrong_return_local_J_peak_max_A_m2=float(np.max(abs(j[pad==wrong]))),
            wrong_return_absolute_patch_current_integral_A=float(np.sum(abs(j[pad==wrong])*area[pad==wrong]))))
    return dict(frequencies=result,full_cancel_tolerance=2e-6,common_GND_nodes=1,
        zero_net_implies_zero_local_J=False,isolated_pairs=False)


def execute(plan,output,deadline,checkpoint):
    canonical=drive.baseline_item(BASELINE_SUMMARY);baseline=volume.load_native(canonical)
    post,scalar,probe=drive.import_frozen(canonical['run'],plan)
    burden,currents=volume.burdens(canonical,baseline['condition'])
    cutoffs={metric:{region+'_'+stat:volume.weighted_statistics(baseline['arrays'][metric],baseline['regions'][region])[stat]
        for region in(volume.PRIMARY,volume.SLAB)for stat in('mean','p10')}for metric in volume.METRICS}
    base_screen=dict(normalizations={'skin_contact_only':dict(regions=volume.summarize_regions(baseline['arrays'],baseline['regions'],baseline['grid'],1.,cutoffs))})
    results=[];operators=[]
    for source in plan['source_cases']:
        signal.setitimer(signal.ITIMER_REAL,max(.001,min(60.,deadline-time.monotonic())))
        checkpoint('source_operator_start',geometry=source['geometry'])
        item=view.load_case(source['summary_path']);cached=volume.load_native(item)
        require(item['signature']==canonical['signature']and np.array_equal(cached['grid'],baseline['grid']),'Same grid/material/contact/ROI required')
        basis=post._load_basis(item['run']/'bases'/item['case']['id'],item['case'],min(deadline,time.monotonic()+60))
        require(basis['hashes']==source['native_input_sha256'],'Adjacent native source manifest differs')
        geometry,volume_meta=post._geometry(basis,item['case']);responses={};proofs={}
        folder=output/'operators'/source['geometry'];folder.mkdir(parents=True)
        for f in PAIR:
            try:
                r,proof=return_response(basis['f'][f]['density'],basis['f'][f]['contacts'],basis['f'][f]['source'])
            except ValueError as error:
                drive.write_json(folder/'operator-failure.json',dict(status='held_invalid_or_unresolved_return_operator',
                    frequency_Hz=f,error=str(error),source=source,source_hashes=basis['hashes'],
                    partial_response_proofs=proofs,response_evidence=getattr(error,'return_response_evidence',None)))
                raise
            responses[f]=r;proofs[str(f)]=proof
        drive.write_json(folder/'return-response.json',dict(source=source,frequency_response=proofs,source_hashes=basis['hashes']))
        operators.append(dict(geometry=source['geometry'],path=str(folder/'return-response.json'),SHA256=view.sha(folder/'return-response.json')))
        checkpoint('source_operator_complete',geometry=source['geometry'])
        for declared in [c for c in plan['conditions']if c['geometry']==source['geometry']]:
            per=min(deadline,time.monotonic()+60);signal.setitimer(signal.ITIMER_REAL,max(.001,per-time.monotonic()))
            out=output/declared['id'];out.mkdir();checkpoint('condition_start',condition_id=declared['id'])
            results.append(derive(basis,geometry,volume_meta,cached,declared,post,scalar,probe,out,per,burden,currents,cutoffs,base_screen,checkpoint,responses))
            checkpoint('condition_complete',condition_id=declared['id'])
        del basis,cached,responses
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    return dict(schema='task1-return-current-drive-scout-v1',status='calculated_unadopted',conditions=results,return_operators=operators,new_PDE=0,
        canonical_square_reference=dict(condition_id=baseline['condition']['id'],summary_path=str(BASELINE_SUMMARY),burdens=burden,
            source_current_RMS_by_output_mA=currents,screen_baseline=base_screen),
        actual_fundamental_Hz=list(PAIR),beat_frequency_Hz=30,comparison='Two adjacent geometries x tau0,.5,1;4pads/2outputs/onecommonGND/50ohm',
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
            ledger['runs'].append(dict(run_id=output.name,stage='return_current_drive_prepare'if args.prepare else'return_current_drive_scout',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
