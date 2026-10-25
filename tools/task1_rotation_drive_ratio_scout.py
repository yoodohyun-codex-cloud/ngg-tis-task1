#!/usr/bin/env python3
"""Four finite square3h drive-ratio re-syntheses of one cached rotated-return basis.

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
SCHEMA='task1-rotation-drive-ratio-scout-preregistration-v1'
BASELINE_SUMMARY=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json'
SOURCE_RUN='cloud-one-return-rotation-20261021T174000Z'
SOURCE_ID='asym-return2-rot90-xy80'
SOURCE_SUMMARY=ROOT/'data-native'/SOURCE_RUN/'postprocess'/SOURCE_ID/'summary.json'
CONTROL_VOLUME=ROOT/'docs/cloud-one-return-rotation-context-20261021T174000Z/volume.json'
CONDITIONS=tuple(dict(id=ident,source_Vpp_by_output=values)for ident,values in (
    ('rotation-ratio-o0-half',[.5,1.]),('rotation-ratio-o0-sqrt-half',[2**-.5,1.]),
    ('rotation-ratio-o1-sqrt-half',[1.,2**-.5]),('rotation-ratio-o1-half',[1.,.5])))
scaled_coefficients=drive.scaled_coefficients
normalization_adapter=drive.normalization_adapter
scaled_probe_rows=drive.scaled_probe_rows
VPP_WIDTH=1e-6
LEVELS=(128,256,512,1024,2048,2560)
require=drive.require


def source_waveform_evidence(base,actual,sourceVpp,waveform_statistics,SamplingLimits):
    v=np.asarray(sourceVpp,float);a1=3/(2*math.sqrt(2));a3=1/(2*math.sqrt(2))
    require(v.shape==(2,)and np.isfinite(v).all()and np.all(v>0),'Two positive actual sourceVpp values required')
    expected={3000:np.array([-1j*a1,0j]),3030:np.array([0j,-1j*a1]),9000:np.array([-1j*a3,0j]),9090:np.array([0j,-1j*a3])}
    require(set(base)==set(actual)==set(FREQUENCIES),'All four square3h frequencies required')
    for f in FREQUENCIES:
        require(np.asarray(base[f]).shape==(2,)and np.asarray(actual[f]).shape==(2,)and np.isfinite(base[f]).all()and
            np.isfinite(actual[f]).all()and np.allclose(base[f],expected[f],rtol=0,atol=1e-15)and
            np.allclose(actual[f],expected[f]*v,rtol=0,atol=1e-15), 'Preserve exact registered square3h amplitudes/phase/carrier assignment')
    outputs=[]
    for output,carrier_hz in enumerate(PAIR):
        frequencies=[carrier_hz,3*carrier_hz]
        phasors=np.asarray([.5*actual[f][output]for f in frequencies])
        sampling=SamplingLimits(samples_per_highest_cycle=128,max_statistics_samples=262144,
            plot_duration_s=min(.002,4000/(max(frequencies)*128)))
        stats=waveform_statistics(frequencies,phasors,[carrier_hz],sampling=sampling)
        lo,hi=float(stats['Vpp_lower_V']),float(stats['Vpp_upper_V']);tol=2e-12*v[output]+1e-15
        require(math.isfinite(lo)and math.isfinite(hi)and 0<lo<=hi and lo<=v[output]+tol and hi>=v[output]-tol,
            'Actual square3h waveform bounds must contain analytic declared sourceVpp')
        outputs.append(dict(output_index=output,frequencies_Hz=frequencies,analytic_source_Vpp_V=float(v[output]),
            numerical_Vpp_lower_V=lo,numerical_Vpp_upper_V=hi,phase_convention='-j sine fundamental and own third harmonic, positive exp(+jwt)'))
    return dict(actual_source_Vpp_by_output=v.tolist(),source_peak_basis_V=.5,analytic_waveform_peak_factor=1.,
        sampled_outputs=outputs,source_waveform_check_passed=True,
        source_Vpp_definition='Analytic full square3h max-minus-min before50ohm, not fundamental toneVpp or2sqrt2RMS',
        analytic_identity='a1*sin(theta)+a3*sin(3theta)=sqrt2*(1.5*sin(theta)-sin(theta)^3); extrema at sin(theta)=+/-1/sqrt2 have values+/-1; .5Vpeak basis gives1Vpp',
        normalization_performed=False,hardware_waveform_calibration_validated=False)


def implementation_receipt():
    modules=(drive,volume,waveform,carrier,frequency,power,screen,core,policy,view,ranking)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_rotation_drive_ratio_scout.py',ROOT/'tools/task1_candidate_ranking.py',
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
    require(decision.get('schema')=='task1-rotation-drive-ratio-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and
        decision.get('conditions')==[dict(c)for c in CONDITIONS],'Exact root-selected4 rotation source-vector conditions required; peer endorsement must not be inferred')
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


def source_metadata(canonical,refs):
    item=view.load_case(SOURCE_SUMMARY);case=item['case'];meta=item['summary']['mesh_metadata'];condition=ranking.condition(item)
    require(item['signature']==canonical['signature']and item['circuit']['n_pads']==4 and item['circuit']['n_outputs']==2 and
        item['circuit']['n_return_nodes']==1 and item['circuit']['source_resistance_ohm']==50 and
        item['circuit']['pad_to_node']=={'0':'out0','1':'out1','2':'GND','3':'GND'},'Exact original material/grid/contact and4pad2output commonGND50ohm required')
    require(case.get('applied_physical_rotation_deg')==90 and case.get('rotated_physical_pad_id')==2 and case.get('rotation_only_contrast')is True,
        'Exact completed one-return90 geometry required')
    refs.update(ranking.input_refs(item));refs.update(item['summary']['input_sha256']);refs[str(Path(case['mask_file']))]=case['mask_sha256']
    archive=SOURCE_SUMMARY.parent/'volume.npz';refs[str(archive)]=item['summary']['artifacts']['files']['volume.npz']['SHA256']
    manifest=item['run']/'frozen-source-manifest.json';refs[str(manifest)]=view.sha(manifest)
    for name in('selectivity_postprocess.py','selectivity_volume.py','layered_probe_analysis.py','explore_tis.py','explore_inputs.py'):
        actual=item['run']/'frozen-source/tis-java'/name;original=canonical['run']/'frozen-source/tis-java'/name
        require(view.sha(actual)==view.sha(original),'Frozen numerical helper identity differs: '+name);refs[str(actual)]=view.sha(actual)
    report=view.read(CONTROL_VOLUME);refs[str(CONTROL_VOLUME)]=view.sha(CONTROL_VOLUME)
    require(report['schema']=='task1-volume-selectivity-v1'and report['status']=='calculated_unadopted'and report['inputs_unchanged']is True,
        'Completed source-bound cached controls volume report required')
    controls={}
    for name,path in(('canonical_original_square',BASELINE_SUMMARY),('rotation_equal_drive',SOURCE_SUMMARY)):
        rows=[r for r in report['cases']if r['summary_path']==str(path)]
        require(len(rows)==1 and report['inputs_sha256'].get(str(path))==view.sha(path),'Exact cached equal-drive control/source SHA required')
        require(rows[0]['condition_id']==path.parent.name+'-square_3h'and rows[0]['normalizations']['raw_1Vpp']['amplitude_scale']==1,
            'Reuse stored square3h1/1 control; do not recompose or relabel a sine control')
        controls[name]=rows[0]
    require(controls['rotation_equal_drive']['baseline_summary']==str(BASELINE_SUMMARY),'Canonical original-square limits must remain the only reference')
    return dict(summary_path=str(SOURCE_SUMMARY),source_case_id=SOURCE_ID,source_run_id=SOURCE_RUN,
        source_commit=item['registration']['source_commit'],configuration_sha256=case['config_sha256'],mask_sha256=case['mask_sha256'],
        native_input_sha256=item['summary']['input_sha256'],circuit=item['circuit'],condition_id=condition['id'],
        cached_control_volume=dict(path=str(CONTROL_VOLUME),SHA256=refs[str(CONTROL_VOLUME)]),cached_controls=controls)


def make_preregistration(baseline_summary,output,*,decision_path,feedback_path):
    require(Path(baseline_summary).resolve()==BASELINE_SUMMARY,'Exact original-square canonical reference required')
    plan=drive.make_preregistration(baseline_summary,output);canonical=drive.baseline_item(baseline_summary)
    selection=context_metadata(decision_path,feedback_path,plan['input_sha256']);source=source_metadata(canonical,plan['input_sha256'])
    plan.update(schema=SCHEMA,conditions=[dict(c)for c in CONDITIONS],source_geometry=source,root_selection_context=selection,waveform='square_3h',
        feedback_id='T1-F010-one-return-rotation-drive-ratio',scope='Four drive amplitude ratios only at fixed rotated-return geometry and source phase0/0; no PDE',
        source_Vpp_definition='Analytic square3h full waveform max-minus-min; basis .5Vpeak; actual raw declared output vector, not coherent two-fundamentals per output',
        direction_count=2074,eight_gate_definitions=screen.GATE_DEFINITIONS,
        resource_limits=dict(CPU_count=1,total_seconds=600,source_load_seconds=60,per_condition_seconds=60,finalization_seconds=60,
            RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,max_added_bytes=2*GIB,cumulative_budget_seconds=policy.effective_limit(policy.load_ledger())),
        canonical_reference='Original four-square4line eight-skin burdens/cutoffs; rotation1/1 is an unchanged cached control, not a new condition')
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
        plan['source_geometry']['summary_path']==str(SOURCE_SUMMARY) and plan['waveform']=='square_3h',
        'Exact4 rotation source vectors/source/output/limits required')
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
    for f in FREQUENCIES:
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
    seed=post._coefficients(2,'square_3h');coefficients=scaled_coefficients(seed,declared['source_Vpp_by_output'])
    sourceproof=source_waveform_evidence(seed,coefficients,declared['source_Vpp_by_output'],probe.waveform_statistics,probe.SamplingLimits)
    checkpoint('normalized_source',condition_id=declared['id'])
    spectra=post._spectra(basis,coefficients);active=spectra
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
    probes=probe.evaluate_layered_probe(basis['grid'],{f:basis['f'][f]['potential']for f in FREQUENCIES},
        {f:basis['f'][f]['field']for f in FREQUENCIES},geometry,coefficients,provenance=provenance,
        fundamental_frequencies_Hz=list(PAIR),plus_pitch_mm=5.,tip_gap_mm=5.,depths_mm=(5.,10.,15.,20.))
    require(probes['status']=='complete'and probes['numerical_checks']['all_passed']and len(probes['measurements'])==40,
        'All40 actual coherent nativephi/E probes required')
    for row in probes['measurements']:row.pop('time_plot',None)
    probes.update(actual_source_Vpp_by_output=declared['source_Vpp_by_output'],actual_fundamental_Hz=list(PAIR),
        source_drive='Each source retains its exclusive fundamental and own third harmonic; square3h phase0/0')
    drive.write_json(output/'probes.json',probes)
    probecheck=waveform.probe_check(dict(id=declared['id'],probe40=probes))
    fieldcheck=waveform.field_check(dict(id=declared['id'],waveform='square_3h',actual_fundamental_Hz=list(PAIR),metrics=electrical))
    modes=normalization_adapter(burdens,baseline_burdens,sum(currents),sum(baseline_currents),declared['source_Vpp_by_output'])
    for name,mode in modes.items():
        scale=mode['amplitude_scale'];mode['regions']=volume.summarize_regions(arrays,regions,basis['grid'],scale,cutoffs)
        mode['source_output_RMS_by_output_mA']=[v*scale for v in currents]
        mode['signed_per_output_power_evidence']=signed_output_powers(electrical,scale)
        mode['physical_pad_current_RMS_mA']=[v*scale for v in padcurrents['physical_pad_current_RMS_mA']]
        mode['probe40_unloaded']=drive.scaled_probe_rows(probes,scale)
        require(time.monotonic()<deadline,'Per-condition60s full-metrics deadline exceeded')
    checks=screen.screen_checks(dict(normalizations=modes),base_screen)
    result=dict(schema='task1-rotation-drive-ratio-condition-v1',status='calculated_unadopted',**declared,
        source_case_id=cached['item']['case']['id'],source_run_id=cached['item']['run'].name,
        source_commit=cached['item']['registration']['source_commit'],configuration_sha256=basis['metadata']['config_sha256'],
        source_circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
            return_topology='all_return_pads_ideal_common_GND',source_resistance_ohm=50,
            active_frequencies_by_output_Hz={'0':[3000,9000],'1':[3030,9090]},uncommanded_frequency_termination='0V through50ohm',
            hardware_multitone_phase_sync_power_sink_compliance='unverified; not experimental-ready'),
        waveform='square_3h',actual_fundamental_Hz=list(PAIR),beat_frequency_Hz=30,active_frequencies_Hz=list(FREQUENCIES),harmonics_active=True,
        seed_coefficients={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in seed.items()},
        coefficient_vectors={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in coefficients.items()},
        source_waveform=sourceproof,electrical_metrics=electrical,bulk_skin_J=skin,layer_contact_source_losses=losses,
        physical_pad_current_evidence=padcurrents,output_power_evidence=signed_output_powers(electrical),
        centre20_directional_E_TIS=dict(point_mm=[0.,0.,20.],unit='V/m',
            scope='Layered interpolated electric field at central20mm point; directional fundamental envelope widths, not ROI metrics or probe voltage',
            axes={axis:float(2*min(abs(complex(row['real_V_m'][index],row['imaginary_V_m'][index]))
                for row in electrical['centre_field_spectrum']if row['frequency_Hz']in PAIR))for index,axis in enumerate(('X','Y','Z'))}),
        native_volume_XYZ_directional_scalar_archives='not produced in this bounded scout; fixed diagonal and2074maximum volume arrays are supplied',
        native_volume_metrics=native['metrics'],normalizations=modes,raw_mode='raw_declared_Vpp',
        source_geometry_unchanged=True,shared_original_square_cutoffs_V_m=cutoffs,
        raw_carrier_balance_regions={region:{key:carrier.weighted(value,w,basis['grid'])for key,value in balance.items()
            if key in('carrier0_RMS_V_m','carrier1_RMS_V_m','combined_fundamental_RMS_V_m','max_direction_balance','fixed_direction_balance')}
            for region,w in regions.items()},probe_waveform_audit=probecheck,field_waveform_audit=fieldcheck,
        canonical_skin_cap_screen=dict(checks=checks,all_screen_checks_passed=all(c['passed']for c in checks),
            failed_checks=[c['name']for c in checks if not c['passed']],normalization='skin_contact_only'),
        new_PDE=0,candidate_adopted=False,instrument_loading_validated=False,full_convergence_validated=False,experimentally_validated=False)
    drive.write_json(output/'condition.json',result)
    return dict(id=declared['id'],status=result['status'],source_Vpp_by_output=declared['source_Vpp_by_output'],
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
    return dict(schema='task1-rotation-drive-ratio-scout-v1',status='calculated_unadopted',conditions=results,new_PDE=0,
        cached_controls=plan['source_geometry']['cached_controls'],cached_control_volume=plan['source_geometry']['cached_control_volume'],
        source_geometry=plan['source_geometry'],canonical_square_reference=dict(condition_id=baseline['condition']['id'],summary_path=str(BASELINE_SUMMARY),
            burdens=burden,source_current_RMS_by_output_mA=currents,screen_baseline=base_screen),
        actual_fundamental_Hz=list(PAIR),all_active_frequencies_Hz=list(FREQUENCIES),beat_frequency_Hz=30,waveform='square_3h',
        comparison='Four output amplitude vectors at unchanged rotated-return geometry; canonical original square8 skin caps',
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
            ledger['runs'].append(dict(run_id=output.name,stage='rotation_drive_ratio_prepare'if args.prepare else'rotation_drive_ratio_scout',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
