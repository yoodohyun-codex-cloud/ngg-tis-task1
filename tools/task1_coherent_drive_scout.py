#!/usr/bin/env python3
"""Eight finite two-tone/two-output re-syntheses of one existing four-pad basis.

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

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
FREQUENCIES=(3000,3030,9000,9090)
PAIR=(3000,3030)
SCHEMA='task1-coherent-drive-scout-preregistration-v1'
CONTROL_SUMMARY=ROOT/'docs/cloud-next-frequency-20261021T104000Z/summary.json'
CONTROL_ID='sine-3000-3030-beat30'
BASELINE_SUMMARY=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json'
CONDITIONS=tuple(dict(id=f'coherent-r{label}-p{phase:03d}',mix_ratio=r,phase_deg=phase)
    for r,label in ((.5,'0p5'),(1.,'1'))for phase in(0,90,180,270))
VPP_WIDTH=1e-6
LEVELS=(128,256,512,1024,2048,2560)
require=drive.require


def seed_coefficients(r,phase_deg):
    require(type(r)in(int,float)and r in(.5,1.)and type(phase_deg)in(int,float)and phase_deg in(0,90,180,270),
        'Exactly two registered rational mix ratios and four phases required')
    phase=np.deg2rad(phase_deg)
    unitary=np.array([[1,-r*np.exp(-1j*phase)],[r*np.exp(1j*phase),1]],complex)/math.sqrt(1+r*r)
    return {3000:-1j*unitary[0].copy(),3030:-1j*unitary[1].copy(),9000:np.zeros(2,complex),9090:np.zeros(2,complex)}


def validated_coefficients(coefficients):
    require(set(coefficients)==set(FREQUENCIES),'All four available frequencies must remain explicit')
    result={f:np.asarray(coefficients[f],complex).copy()for f in FREQUENCIES}
    require(all(c.shape==(2,)and np.isfinite(c).all()for c in result.values()),'Finite actual two-output coefficients required')
    require(all(np.all(abs(result[f])>0)for f in PAIR)and not np.any(result[9000])and not np.any(result[9090]),
        'Both actual fundamentals must drive both outputs; harmonics must be zero')
    return result


def normalize_source(coefficients,waveform_statistics,SamplingLimits):
    """Normalize each ideal Thevenin waveform using a verified full-period upper.

    0.5*c is the PEAK voltage phasor before50ohm. Tone amplitudes and loaded
    metal voltages are not substituted for full-wave max-minus-min source Vpp.
    """
    result=validated_coefficients(coefficients);outputs=[];scales=[];intervals=[]
    for output in range(2):
        samples=[];accepted=None
        for level in LEVELS:
            sampling=SamplingLimits(samples_per_highest_cycle=level,max_statistics_samples=262144,
                plot_duration_s=min(.002,4000/(3030*level)))
            stats=waveform_statistics(list(PAIR),np.asarray([.5*result[f][output]for f in PAIR]),list(PAIR),sampling=sampling)
            lower,upper=float(stats['Vpp_lower_V']),float(stats['Vpp_upper_V'])
            require(math.isfinite(lower)and math.isfinite(upper)and 0<lower<=upper,'Finite positive coherent-source Vpp bracket required')
            width=(upper-lower)/upper
            samples.append(dict(samples_per_highest_cycle=level,raw_Vpp_lower_V=lower,raw_Vpp_upper_V=upper,normalized_width_V=width))
            if width<=VPP_WIDTH:
                accepted=(lower,upper);break
        if accepted is None:
            error=ValueError('Source full-wave1uV Vpp bracket gate failed; preserve held evidence')
            error.source_waveform_evidence=dict(status='held_source_Vpp_bracket',output_index=output,levels=samples,
                already_normalized_outputs=outputs,hard_maximum_bracket_width_V=VPP_WIDTH)
            raise error
        lower,upper=accepted;scales.append(1/upper);intervals.append([lower/upper,1.])
        outputs.append(dict(output_index=output,levels=samples,column_scale=1/upper,
            source_Vpp_interval_V=[lower/upper,1.],source_Vpp_definition='full1/30s max-minus-min of Re(sum(.5*c_f*exp(+j2pi*f*t))) before50ohm'))
    for f in FREQUENCIES:result[f]*=np.asarray(scales)
    return result,dict(outputs=outputs,column_scales=scales,source_Vpp_intervals_V=intervals,
        maximum_bracket_width_V=max(hi-lo for lo,hi in intervals),hard_maximum_bracket_width_V=VPP_WIDTH,
        source_peak_basis_V=.5,source_resistance_ohm=50,common_period_s=1/30,
        seed_unitary=bool(np.allclose(np.asarray([coefficients[f]for f in PAIR]).conj().T@np.asarray([coefficients[f]for f in PAIR]),np.eye(2),rtol=1e-12,atol=1e-12)),unitary_after_Vpp_normalization=False,
        interpretation='Conservative actual waveform intervals ending at1Vpp; no experimental source calibration claim')


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
        mode['source_Vpp_definition']='actual full two-tone max-minus-min before50ohm; bounds, not each tone Vpp'
        mode['unitary_after_Vpp_normalization']=False
    return modes


def implementation_receipt():
    modules=(drive,volume,waveform,carrier,frequency,power,screen,core,policy,view)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_coherent_drive_scout.py',ROOT/'tools/task1_candidate_ranking.py',
        *[Path(module.__file__).resolve()for module in modules]]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();pins={}
    for path in paths:
        require(path.read_bytes()==subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT),
            'Implementation/helper/test differs from committed HEAD: '+str(path))
        pins[str(path)]=view.sha(path)
    return dict(implementation_git_commit=commit,implementation_files_sha256=pins)


def control_metadata(pins):
    require(CONTROL_SUMMARY.is_file(),'Exact cached exclusive3k sine control is missing; do not fabricate/recompose silently')
    summary=view.read(CONTROL_SUMMARY);pins[str(CONTROL_SUMMARY)]=view.sha(CONTROL_SUMMARY)
    require(summary['schema']=='task1-frequency-resynthesis-audit-v1'and summary['status']=='calculated_unadopted'and
        summary['inputs_unchanged']is True and summary['candidate_adopted']is False,'Terminal source-bound cached sine control required')
    refs=[c for c in summary['conditions']if c['id']==CONTROL_ID];require(len(refs)==1,'One actual cached3k sine control required')
    refs=refs[0]['artifacts'];condition=view.read(refs['condition.json']['path'])
    require(view.sha(refs['condition.json']['path'])==refs['condition.json']['SHA256']and
        condition['status']=='calculated_unadopted'and condition['waveform']=='sine'and condition['actual_fundamental_Hz']==list(PAIR)and
        condition['source_provenance']['source_summary']==str(BASELINE_SUMMARY)and condition['source_Vpp_by_output']==[1.,1.],
        'Cached exclusive sine condition/source identity differs')
    for f,expected in ((3000,[-1j,0j]),(3030,[0j,-1j])):
        c=condition['coefficient_vectors'][str(f)]
        actual=np.asarray(c['real'])+1j*np.asarray(c['imaginary'])
        require(np.array_equal(actual,np.asarray(expected)),'Cached sine control must remain exclusive unit sine')
    for ref in refs.values():
        path=Path(ref['path']).resolve();require(path.is_file(),'Cached sine artifact missing')
        pins[str(path)]=ref['SHA256']
    return dict(id=CONTROL_ID,summary_path=str(CONTROL_SUMMARY),artifacts=refs,
        source_case_id='baseline-square15-xy80',new_PDE=0,new_condition=False,recomposed=False)


def context_metadata(decision_path,feedback_path,pins):
    require(decision_path is not None and feedback_path is not None,'Explicit root decision and actual feedback GET context required')
    def bound(path):
        path=Path(path)
        require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and
            not path.is_symlink()and path.stat().st_size<=25*1024**2,'Canonical local public JSON context required')
        digest=view.sha(path);value=view.read(path);require(view.sha(path)==digest,'Context changed while reading')
        pins[str(path)]=digest;return value,dict(path=str(path),SHA256=digest)
    decision,dref=bound(decision_path);feedback,fref=bound(feedback_path)
    require(decision.get('schema')=='task1-coherent-drive-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and
        decision.get('conditions')==[dict(c)for c in CONDITIONS],'Exact root-selected8 seeds required; peer endorsement must not be inferred')
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


def make_preregistration(baseline_summary,output,*,decision_path,feedback_path):
    require(Path(baseline_summary).resolve()==BASELINE_SUMMARY,'Exact original same-grid baseline required')
    plan=drive.make_preregistration(baseline_summary,output)
    selection=context_metadata(decision_path,feedback_path,plan['input_sha256'])
    plan.update(root_selection_context=selection)
    plan.update(schema=SCHEMA,conditions=[dict(c)for c in CONDITIONS],waveform='coherent_two_tone_sine',
        feedback_id='T1-F010-coherent-two-output-scout',scope='Eight new output drive conditions only; original4square/2outputs/commonGND/50ohm; no new PDE',
        active_frequencies_Hz=list(PAIR),available_native_frequencies_Hz=list(FREQUENCIES),beat_frequency_Hz=30,
        source_Vpp_definition='Each actual two-tone Thevenin waveform before50ohm has Vpp upper1V and width<=1uV; preserve lower/upper',
        source_Vpp_bracket_width_V=VPP_WIDTH,unitary_seed_definition='rows=f3000,f3030; columns=out0,out1; c=-j/sqrt(1+r²)*[[1,-r exp(-jphi)],[r exp(jphi),1]]',
        seed_unitary_only=True,direction_count=2074,eight_gate_definitions=screen.GATE_DEFINITIONS,
        resource_limits=dict(CPU_count=1,total_seconds=600,source_load_seconds=60,per_condition_seconds=60,finalization_seconds=60,
            RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,max_added_bytes=2*GIB,cumulative_budget_seconds=policy.effective_limit(policy.load_ledger())),
        canonical_reference='Original square3h four spectral lines; fixed original primary and supplemental mean/P10 cutoffs for all modes',
        cached_exclusive_sine_control=control_metadata(plan['input_sha256']))
    plan['holds']+=['AWG arbitrary two-tone generation, interoutput phase synchronization, signed power sinking and compliance unverified; not experimental-ready',
        'Both sources active at BOTH fundamentals; exclusive-other-carrier-inactive label does not describe this actual drive',
        '2074 sampled real directions remain a continuous-direction lower bound; no sphere or mesh/contact convergence promotion']
    plan.update(implementation_receipt());plan['input_sha256'].update(plan['implementation_files_sha256'])
    plan['resource_policy_refs']=policy.policy_refs(policy.load_ledger());plan['input_sha256'].update(plan['resource_policy_refs'])
    return plan


def verify_plan(path,output,expected=None):
    digest=view.sha(path);plan=view.read(path)
    require(expected is None or digest==expected,'Preregistration changed during execution')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['new_PDE_conditions']==0 and
        plan['conditions']==[dict(c)for c in CONDITIONS]and plan['baseline_summary']==str(BASELINE_SUMMARY)and
        plan['output_directory']==str(output)and plan['source_Vpp_bracket_width_V']==VPP_WIDTH and
        plan['direction_count']==2074 and plan['eight_gate_definitions']==screen.GATE_DEFINITIONS,
        'Exact8 coherent drives/source/output/limits required')
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


def derive(basis,geometry,volume_meta,cached,declared,post,scalar,probe,output,deadline,baseline_burdens,baseline_currents,cutoffs,base_screen,checkpoint):
    seed=seed_coefficients(declared['mix_ratio'],declared['phase_deg'])
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
        source_drive='Both frequencies coherent on both physical outputs; no exclusive carrier assignment')
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
    result=dict(schema='task1-coherent-drive-condition-v1',status='calculated_unadopted',**declared,
        source_case_id=cached['item']['case']['id'],source_run_id=cached['item']['run'].name,
        source_commit=cached['item']['registration']['source_commit'],configuration_sha256=basis['metadata']['config_sha256'],
        source_circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
            return_topology='all_return_pads_ideal_common_GND',source_resistance_ohm=50,
            active_frequencies_by_output_Hz={'0':[3000,3030],'1':[3000,3030]},uncommanded_frequency_termination='0V through50ohm',
            hardware_multitone_phase_sync_power_sink_compliance='unverified; not experimental-ready'),
        actual_fundamental_Hz=list(PAIR),beat_frequency_Hz=30,active_frequencies_Hz=list(PAIR),harmonics_active=False,
        seed_coefficients={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in seed.items()},
        coefficient_vectors={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in coefficients.items()},
        source_waveform=sourceproof,electrical_metrics=electrical,bulk_skin_J=skin,layer_contact_source_losses=losses,
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
    return dict(id=declared['id'],status=result['status'],mix_ratio=declared['mix_ratio'],phase_deg=declared['phase_deg'],
        canonical_screen_all_passed=all(c['passed']for c in checks),artifacts={name:dict(path=str(output/name),SHA256=view.sha(output/name))
            for name in('condition.json','probes.json','volume.npz','native-volume-metrics.json')})


def execute(plan,output,deadline,checkpoint):
    item=drive.baseline_item(BASELINE_SUMMARY);cached=volume.load_native(item)
    post,scalar,probe=drive.import_frozen(item['run'],plan)
    basis=post._load_basis(item['run']/'bases'/item['case']['id'],item['case'],min(deadline,time.monotonic()+60))
    require(basis['hashes']==plan['native_input_sha256']and np.array_equal(basis['grid'],cached['grid']),'Original sourceSHA/grid differs')
    geometry,volume_meta=post._geometry(basis,item['case'])
    burden,currents=volume.burdens(item,cached['condition'])
    cutoffs={metric:{region+'_'+stat:volume.weighted_statistics(cached['arrays'][metric],cached['regions'][region])[stat]
        for region in(volume.PRIMARY,volume.SLAB)for stat in('mean','p10')}for metric in volume.METRICS}
    base_screen=dict(normalizations={'skin_contact_only':dict(regions=volume.summarize_regions(cached['arrays'],cached['regions'],basis['grid'],1.,cutoffs))})
    control=plan['cached_exclusive_sine_control'];ctrl=view.read(control['artifacts']['condition.json']['path'])
    control_record=dict(**control,raw_coherent_exclusive_control=ctrl['cohorts']['cached_original_square_3000_3030_caps']['normalizations']['raw_sine_1Vpp'])
    require(ctrl['source_provenance']['configuration_sha256']==basis['metadata']['config_sha256'],'Cached exclusive sine uses another source config')
    results=[]
    for declared in plan['conditions']:
        per=min(deadline,time.monotonic()+60);signal.setitimer(signal.ITIMER_REAL,max(.001,per-time.monotonic()))
        folder=output/declared['id'];folder.mkdir();checkpoint('condition_start',condition_id=declared['id'])
        results.append(derive(basis,geometry,volume_meta,cached,declared,post,scalar,probe,folder,per,burden,currents,cutoffs,base_screen,checkpoint))
        checkpoint('condition_complete',condition_id=declared['id'])
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    return dict(schema='task1-coherent-drive-scout-v1',status='calculated_unadopted',conditions=results,new_PDE=0,
        cached_exclusive_sine_control=control_record,canonical_square_reference=dict(condition_id=cached['condition']['id'],
            summary_path=str(BASELINE_SUMMARY),burdens=burden,source_current_RMS_by_output_mA=currents,screen_baseline=base_screen),
        actual_fundamental_Hz=list(PAIR),beat_frequency_Hz=30,comparison='8coherent-drive conditions; same4physicalpads/2outputs/commonGND/50ohm',
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
            ledger['runs'].append(dict(run_id=output.name,stage='coherent_drive_prepare'if args.prepare else'coherent_drive_scout',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
