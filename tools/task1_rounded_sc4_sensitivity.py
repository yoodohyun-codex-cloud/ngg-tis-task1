"""One selected rounded-drive SC2→SC4 sensitivity readback; no PDE or SC2 recomputation.

Historical SC2 amplitudes and newly rematched SC4 modes remain separate. All
normalization constants and cutoffs are the original SC2 square references.
"""
from __future__ import annotations
import argparse
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
for _name in('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_name]='1'
import numpy as np
import task1_rounded_drive_scout as base
import task1_rounded_drive_optimization as optimizer
import task1_rounded_sc4_registration as registration
ROOT=base.ROOT;GIB=base.GIB;PAIR=base.PAIR;FREQUENCIES=base.FREQUENCIES
SCHEMA='task1-rounded-sc4-sensitivity-preregistration-v1'
SC4_RUN='cloud-rounded-sc4-20261021T204000Z';SC4_ID='rounded-fullface225-sc4-xy80'
SC4_SUMMARY=ROOT/'data-native'/SC4_RUN/'postprocess'/SC4_ID/'summary.json'
SC2_SUMMARY=base.SOURCE_SUMMARY
require=base.require;view=base.view;drive=base.drive;volume=base.volume;waveform=base.waveform
carrier=base.carrier;frequency=base.frequency;screen=base.screen;core=base.core;policy=base.policy;routing=base.routing
SENSITIVITY_LIMITS=dict(primary_mean_relative=.01,primary_p10_relative=.01,off_target_p95_relative=.02,
    skin_contact_J95_relative=.02,power_relative=.02,eight_screen_status_flips_allowed=0)
POWER_KEYS=('SC_power_W','contact_power_W','skin_SC_plus_dermis_power_W','source_power_W')
J95_KEYS=('surface_J_RMS_p95_A_m2','bulk_skin_J_vector_RMS_p95_A_m2')


def decode_coefficients(condition):
    value=condition['coefficient_vectors'];require(set(value)=={str(f)for f in FREQUENCIES},'Explicit actual four-frequency coefficients required')
    result={}
    for f in FREQUENCIES:
        row=value[str(f)];require(set(row)=={'real','imaginary'},'Real/imaginary coefficient ABI required')
        re,im=np.asarray(row['real'],float),np.asarray(row['imaginary'],float)
        require(re.shape==im.shape==(2,)and np.isfinite(re).all()and np.isfinite(im).all(),'Finite actual two-output coefficients required')
        result[f]=re+1j*im
    require(all(np.any(result[f])for f in PAIR)and not np.any(result[9000])and not np.any(result[9090]),'Selected two active carriers/zero harmonics required')
    return result


def fixed_sc2_modes(saved_modes):
    require(set(saved_modes)==set(screen.MODES),'All five saved SC2 mode IDs required')
    result={}
    for name,old in saved_modes.items():
        scale=old['amplitude_scale'];require(type(scale)in(int,float)and math.isfinite(scale)and scale>0,'Saved positive SC2 amplitude required')
        result[name]=dict(amplitude_scale=scale,historical_SC2_mode_id=name,
            normalization_scope='frozen_SC2_amplitude_no_SC4_rematch',matches_SC2_current_on_SC4=False,matches_SC2_power_on_SC4=False,
            SC4_skin_caps_rematched=False,interpretation='Historical SC2 mode amplitude reused exactly; its current/power/burden equality is not asserted on SC4')
    return result


def validate_roi_volumes(sc2_regions,sc4_regions):
    require(set(sc2_regions)==set(sc4_regions)and bool(sc2_regions),'Identical named physical ROI definitions required')
    rows=[]
    for region in sc2_regions:
        for metric in volume.METRICS:
            old,new=sc2_regions[region][metric]['volume_m3'],sc4_regions[region][metric]['volume_m3']
            require(all(type(v)in(int,float)and math.isfinite(v)and v>0 for v in(old,new))and
                math.isclose(old,new,rel_tol=1e-10,abs_tol=1e-15),'Represented physical ROI volume differs across SC meshes: '+region)
            rows.append(dict(region=region,metric=metric,SC2_volume_m3=old,SC4_volume_m3=new))
    return dict(passed=True,all_passed=True,relative_tolerance=1e-10,absolute_tolerance_m3=1e-15,regions=rows,
        scope='Physical volume sums agree; native cell counts/SC cell thicknesses intentionally differ')


def sensitivity_checks(sc2_modes,sc4_fixed_modes,baseline):
    checks=[];flips=[]
    def compare(mode,name,old,new,limit):
        require(all(type(v)in(int,float)and math.isfinite(v)and v>=0 for v in(old,new)),'Finite nonnegative SC sensitivity metrics required')
        rel=abs(new-old)/old if old else(None if new else 0.)
        passed=(rel is not None and rel<=limit+1e-12)
        checks.append(dict(historical_SC2_mode_id=mode,metric=name,SC2=old,SC4_same_amplitude=new,
            absolute_relative_change=rel,relative_limit=limit,passed=passed))
    for name in('raw_1Vpp','skin_contact_only'):
        old,new=sc2_modes[name],sc4_fixed_modes[name]
        require(new['amplitude_scale']==old['amplitude_scale'],'SC sensitivity must use exactly saved SC2 amplitude')
        for stat in('mean','p10'):compare(name,'primary_maxTIS_'+stat,old['regions'][volume.PRIMARY]['maxTIS'][stat],new['regions'][volume.PRIMARY]['maxTIS'][stat],.01)
        for region in('surface_0_5','primary_complement'):
            compare(name,region+'_maxTIS_p95',old['regions'][region]['maxTIS']['p95'],new['regions'][region]['maxTIS']['p95'],.02)
        a=old.get('actual_burdens',old.get('normalized_burdens'));b=new.get('actual_burdens',new.get('normalized_burdens'))
        require(isinstance(a,dict)and isinstance(b,dict),'Actual same-amplitude skin/contact current and power metrics required')
        for key in(*J95_KEYS,*POWER_KEYS):compare(name,key,a[key],b[key],.02)
        before=screen.screen_checks(dict(normalizations={'skin_contact_only':old}),baseline)
        after=screen.screen_checks(dict(normalizations={'skin_contact_only':new}),baseline)
        for x,y in zip(before,after):
            same=x['passed']==y['passed'];flips.append(dict(historical_SC2_mode_id=name,gate=x['name'],SC2_passed=x['passed'],SC4_same_amplitude_passed=y['passed'],unchanged=same))
    return dict(all_passed=all(r['passed']for r in checks)and all(r['unchanged']for r in flips),checks=checks,screen_status_no_flip=all(r['unchanged']for r in flips),
        screen_status_comparisons=flips,thresholds=SENSITIVITY_LIMITS,numerical_validation_promoted=False,full_convergence_validated=False,
        scope='Two-level SC discretization sensitivity at raw and historical SC2skin8 amplitude only; not XY/bulk/edge/contact convergence or experimental validation')


def implementation_receipt():
    modules=(base,optimizer,registration,drive,volume,waveform,carrier,frequency,screen,core,policy,view,routing)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_rounded_sc4_sensitivity.py',*[Path(m.__file__).resolve()for m in modules]]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();refs={}
    for p in dict.fromkeys(paths):
        require(p.read_bytes()==subprocess.check_output(['git','show',commit+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT),'Commit all consumed SC4 post sources/tests: '+str(p));refs[str(p)]=view.sha(p)
    return dict(implementation_git_commit=commit,implementation_files_sha256=refs)


def make_preregistration(native_registration,output):
    native_registration=Path(native_registration).resolve();run=native_registration.parent
    require(run==ROOT/'data-native'/SC4_RUN and native_registration.name=='preregistration.json','Exact prepared rounded SC4 native registration required')
    pre=view.read(native_registration);refs={str(native_registration):view.sha(native_registration)}
    require(pre.get('batch_kind')=='one_rounded_SC_only_sensitivity_basis'and pre.get('gates')==core.GATES and len(pre['cases'])==1,'Exact one-condition SC4 native registration/gates required')
    decision_path=Path(pre['root_selection_decision']['path']);decision=view.read(decision_path)
    selection,feedback,context=registration.verify_context(decision_path,Path(pre['source_feedback']['path']));refs.update(context)
    require(selection==pre['root_selection_decision']and selection['selected_SC2_command']==pre['selected_SC2_command'],'Native SC4 root selection changed')
    selected_ref=decision['selected_condition'];selected=view.read(selected_ref['condition']['path']);source=view.read(selected_ref['summary']['path'])
    item=view.load_case(SC4_SUMMARY);case=item['case'];meta=item['summary']['mesh_metadata']
    require(case['id']==SC4_ID and case['SC_only_sensitivity']is True and case['mask_sha256']==source['source_geometry']['mask_sha256']and
        meta['sc_cells']==4 and meta['cells']==361728 and meta['h_xy_mm']==.625 and meta['bulk_layer_counts']==[14,14,40]and
        meta['tissue_boundaries_mm']==[0,.1,5.1,10.1,25.1]and case['design']==view.load_case(SC2_SUMMARY)['case']['design'],
        'Only SC discretization2→4 may change; physical rounded mask/contour/mesh layers fixed')
    record_path=run/'cases'/(SC4_ID+'.json');record=view.read(record_path)
    require(record['status']=='complete'and record['postprocess_sha256']==view.sha(SC4_SUMMARY)and
        all(record['validation'][k]<=v for k,v in core.GATES.items()),'Completed SC4 native five equation gates required before post registration')
    before=registration._properties(Path(case['SC2_source_reference']['config_file']).read_bytes());after=item['config']
    changed={k for k in before if before[k]!=after[k]}
    require(before.keys()==after.keys()and changed=={'validation.sc_cells','mask.path'}and before['mask.sha256']==after['mask.sha256']and
        before['validation.sc_cells']=='2'and after['validation.sc_cells']=='4','Only SC cell count and byte-identical mask path alias may differ')
    refs.update(base.ranking.input_refs(item));refs.update(item['summary']['input_sha256']);refs[str(Path(case['mask_file']))]=case['mask_sha256']
    for name in('volume.npz',item['summary']['artifacts']['probes_json']):refs[str(SC4_SUMMARY.parent/name)]=item['summary']['artifacts']['files'][name]['SHA256']
    refs[str(record_path)]=view.sha(record_path)
    # Source SC2 artifacts are reused as immutable evidence; never decoded/recomputed by this tool.
    for entry in source['conditions']:
        if entry['id']==selected['id']:
            for ref in entry['artifacts'].values():refs[ref['path']]=ref['SHA256']
    for name in('selectivity_postprocess.py','selectivity_volume.py','layered_probe_analysis.py','explore_tis.py','explore_inputs.py'):
        p=run/'frozen-source/tis-java'/name;old=SC2_SUMMARY.parents[2]/'frozen-source/tis-java'/name
        require(view.sha(p)==view.sha(old),'SC2/SC4 frozen numerical helper bytes differ');refs[str(p)]=view.sha(p);refs[str(old)]=view.sha(old)
    manifest=run/'frozen-source-manifest.json';refs[str(manifest)]=view.sha(manifest)
    canonical=source['canonical_square_reference'];require(canonical['summary_path']==str(base.BASELINE_SUMMARY),'Original SC2 square must remain sole cap/current/power/screen baseline')
    require(selected['normalizations']['skin_contact_only']['baseline_derived_numerical_limits']==pre['selected_SC2_command']['SC2_original_eight_caps']and
        selected['shared_original_square_cutoffs_V_m']==pre['selected_SC2_command']['SC2_original_cutoffs_V_m']and
        selected['native_volume_metrics']['total_sampled_directions']==2074,'Selected SC2 constants/direction definition must remain frozen')
    implementation=implementation_receipt();refs.update(implementation['implementation_files_sha256']);refs.update(policy.policy_refs(policy.load_ledger()))
    return dict(schema=SCHEMA,status='preregistered_not_executed',created_utc=core.now(),output_directory=str(output),native_registration=dict(path=str(native_registration),SHA256=refs[str(native_registration)]),
        SC4_summary=str(SC4_SUMMARY),native_input_sha256=item['summary']['input_sha256'],selected_SC2_condition=selected_ref,
        selected_SC2_command=pre['selected_SC2_command'],canonical_SC2_reference=canonical,fixed_SC2_cutoffs_V_m=selected['shared_original_square_cutoffs_V_m'],
        cached_original_SC4_reference=pre['cached_original_SC4_reference'],root_selection_decision=pre['root_selection_decision'],source_feedback=feedback,
        native_five_gate_validation=record['validation'],sensitivity_limits=SENSITIVITY_LIMITS,conditions=[dict(id=selected['id']+'-SC4-same-command')],
        input_sha256=refs,new_PDE_conditions=0,SC2_array_decode=False,SC2_recalculation=False,source_renormalization=False,
        resource_limits=dict(total_seconds=600,per_condition_seconds=120,CPU_count=1,RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,max_added_bytes=2*GIB),
        holds=['Two SC levels only; passing this diagnostic is not full SC/XY/bulk/edge/contact convergence or adoption',
            'Fixed historical SC2 amplitudes do not retain current/power/skin-cap equality on SC4; separately named supplemental rematches retain ORIGINAL SC2 constants',
            'All40 probes remain unloaded; ETA5001 loading/hardware/experiment/activation/COMSOL unverified'],**implementation)


def verify_plan(path,output,expected=None):
    digest=view.sha(path);plan=view.read(path)
    require(expected is None or digest==expected,'SC4 post preregistration changed')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['output_directory']==str(output)and
        plan['new_PDE_conditions']==0 and plan['source_renormalization']is False and plan['SC2_recalculation']is False and plan['sensitivity_limits']==SENSITIVITY_LIMITS,
        'Exact frozen SC4 post scope/output/gates required')
    native=plan['native_registration'];require(native['path']==str(ROOT/'data-native'/SC4_RUN/'preregistration.json')and
        plan['input_sha256'].get(native['path'])==native['SHA256'],'Exact native SC4 registration pin required')
    pre=view.read(native['path']);decision=view.read(pre['root_selection_decision']['path'])
    require(pre['selected_SC2_command']==plan['selected_SC2_command']and decision['selected_condition']==plan['selected_SC2_condition']and
        plan['conditions']==[dict(id=pre['selected_SC2_command']['condition_id']+'-SC4-same-command')],
        'Post selected source/command must equal the main native preregistration')
    for name,d in plan['input_sha256'].items():
        p=Path(name);require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and p.is_file()and not p.is_symlink()and view.sha(p)==d,'Pinned SC4/SC2 evidence changed: '+name)
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'],'SC4 post implementation changed')
    return plan,digest


def derive_sc4(basis,geometry,volume_meta,cached,selected,post,scalar,probe,output,deadline,baseline_burdens,baseline_currents,cutoffs,base_screen,checkpoint):
    declared=dict(id=selected['id']+'-SC4-same-command',waveform=selected['waveform'])
    coefficients=decode_coefficients(selected);seed=copy.deepcopy(coefficients)
    sourceproof=copy.deepcopy(selected['source_waveform'])
    familyproof=dict(exact_selected_SC2_coefficients_reused=True,new_source_normalization_performed=False,
        source_peak_basis_V=.5,source_resistance_ohm=50,physical_outputs=2,common_GND_nodes=1)
    checkpoint('frozen_SC2_command_reused',condition_id=declared['id'])
    spectra=post._spectra(basis,coefficients);active={f:spectra[f]for f in PAIR}
    electrical=post._electrical(basis,coefficients,geometry,deadline)
    padcurrents=base.physical_pad_currents(basis,coefficients);returnlocal=base.return_local_current_evidence(basis,coefficients)
    regression=None
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
    rematched=routing.normalization_modes(burdens,baseline_burdens,sum(currents),sum(baseline_currents),sourceproof['source_Vpp_intervals_V'])
    fixed=fixed_sc2_modes(selected['normalizations'])
    def fill_mode(mode,scope):
        scale=mode['amplitude_scale'];mode['regions']=volume.summarize_regions(arrays,regions,basis['grid'],scale,cutoffs)
        mode['source_output_RMS_by_output_mA']=[v*scale for v in currents]
        mode['signed_per_output_power_evidence']=base.signed_output_powers(electrical,scale)
        mode['physical_pad_current_RMS_mA']=[v*scale for v in padcurrents['physical_pad_current_RMS_mA']]
        mode['return_net_and_local_current_evidence']=base.scaled_return_local_evidence(returnlocal,scale)
        mode['probe40_unloaded']=drive.scaled_probe_rows(probes,scale)
        mode['actual_source_Vpp_intervals_V']=(np.asarray(sourceproof['source_Vpp_intervals_V'])*scale).tolist()
        mode['actual_burdens']={k:v*scale**volume.BURDENS[k]for k,v in burdens.items()}
        mode['actual_power_metrics_W']={k:v*scale**2 for k,v in losses['metrics'].items()}
        mode['comparison_scope']=scope
        mode['original_SC2_eight_caps']={k:baseline_burdens[k]for k in screen.CAP_DEGREES}
        mode['original_SC2_source_power_reference_W']=baseline_burdens['source_power_W']
        require(time.monotonic()<deadline,'SC4 actual120s condition postprocessing deadline exceeded')
    for mode in fixed.values():fill_mode(mode,'Exact historical SC2 amplitude; current/power equality on SC4 is not asserted')
    for mode in rematched.values():
        mode['SC4_rematched']=True;mode['normalization_reference']='ORIGINAL SC2 square constants only; no SC4 baseline caps'
        fill_mode(mode,'Supplemental SC4 rematch using unchanged original SC2 caps/current/power/cutoffs')
    checks=screen.screen_checks(dict(normalizations={'skin_contact_only':fixed['skin_contact_only']}),base_screen)
    supplemental_checks=screen.screen_checks(dict(normalizations=rematched),base_screen)
    sc2_modes=copy.deepcopy(selected['normalizations'])
    for mode in sc2_modes.values():
        mode['actual_burdens']=copy.deepcopy(mode['normalized_burdens'])
    physical_ROI=validate_roi_volumes(sc2_modes['skin_contact_only']['regions'],fixed['skin_contact_only']['regions'])
    sensitivity=sensitivity_checks(sc2_modes,fixed,base_screen)
    result=dict(schema='task1-rounded-sc4-sensitivity-condition-v1',status='calculated_unadopted',**declared,
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
        physical_pad_current_evidence=padcurrents,output_power_evidence=base.signed_output_powers(electrical),
        coefficient_family_proof=familyproof,return_net_and_local_current_evidence=returnlocal,
        centre20_directional_E_TIS=dict(point_mm=[0.,0.,20.],unit='V/m',
            scope='Layered interpolated electric field at central20mm point; directional fundamental envelope widths, not ROI metrics or probe voltage',
            axes={axis:float(2*min(abs(complex(row['real_V_m'][index],row['imaginary_V_m'][index]))
                for row in electrical['centre_field_spectrum']if row['frequency_Hz']in PAIR))for index,axis in enumerate(('X','Y','Z'))}),
        native_volume_XYZ_directional_scalar_archives='not produced in this bounded scout; fixed diagonal and2074maximum volume arrays are supplied',
        native_volume_metrics=native['metrics'],fixed_SC2_amplitude_modes=fixed,supplemental_SC4_rematched_modes=rematched,
        selected_SC2_condition_id=selected['id'],same_source_coefficients_and_whole_Vpp=True,physical_ROI_volume_agreement=physical_ROI,SC_sensitivity=sensitivity,raw_mode='historical_SC2_raw_1Vpp',
        source_geometry_unchanged=True,shared_original_square_cutoffs_V_m=cutoffs,
        raw_carrier_balance_regions={region:{key:carrier.weighted(value,w,basis['grid'])for key,value in balance.items()
            if key in('carrier0_RMS_V_m','carrier1_RMS_V_m','combined_fundamental_RMS_V_m','max_direction_balance','fixed_direction_balance')}
            for region,w in regions.items()},probe_waveform_audit=probecheck,field_waveform_audit=fieldcheck,
        primary_fixed_SC2_skin8_screen=dict(checks=checks,all_screen_checks_passed=all(c['passed']for c in checks),
            failed_checks=[c['name']for c in checks if not c['passed']],normalization='frozen_SC2_skin_contact_only_amplitude'),
        supplemental_SC4_rematched_skin8_screen=dict(checks=supplemental_checks,all_screen_checks_passed=all(c['passed']for c in supplemental_checks)),
        new_PDE=0,candidate_adopted=False,instrument_loading_validated=False,full_convergence_validated=False,experimentally_validated=False)
    drive.write_json(output/'condition.json',result)
    return dict(id=declared['id'],status=result['status'],waveform=declared['waveform'],source_Vpp_intervals_V=sourceproof['source_Vpp_intervals_V'],
        SC_sensitivity=sensitivity,canonical_screen_all_passed=all(c['passed']for c in checks),artifacts={name:dict(path=str(output/name),SHA256=view.sha(output/name))
            for name in('condition.json','probes.json','volume.npz','native-volume-metrics.json')})



def execute(plan,output,deadline,checkpoint):
    selected=view.read(plan['selected_SC2_condition']['condition']['path'])
    item=view.load_case(SC4_SUMMARY);cached=volume.load_native(item)
    post,scalar,probe=drive.import_frozen(item['run'],plan)
    basis=post._load_basis(item['run']/'bases'/SC4_ID,item['case'],min(deadline,time.monotonic()+60))
    require(basis['hashes']==plan['native_input_sha256']and np.array_equal(basis['grid'],cached['grid']),'Actual SC4 basis/grid/hash mismatch')
    dirs=optimizer.frozen_direction_set(post,scalar)
    direction_receipt=dict(count=2074,SHA256=hashlib.sha256(dirs.tobytes(order='C')).hexdigest(),
        source='SC4 frozen point/volume direction bytes equal; all five frozen numerical helpers SHA-identical to selected SC2 source',continuous_maximum=False)
    geometry,volume_meta=post._geometry(basis,item['case']);canonical=plan['canonical_SC2_reference']
    per=min(deadline-60,time.monotonic()+120);require(per>time.monotonic(),'SC4 post finalization reserve unavailable')
    signal.setitimer(signal.ITIMER_REAL,max(.001,per-time.monotonic()));folder=output/plan['conditions'][0]['id'];folder.mkdir()
    result=derive_sc4(basis,geometry,volume_meta,cached,selected,post,scalar,probe,folder,per,canonical['burdens'],
        canonical['source_current_RMS_by_output_mA'],plan['fixed_SC2_cutoffs_V_m'],canonical['screen_baseline'],checkpoint)
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    return dict(schema='task1-rounded-sc4-sensitivity-v1',status='calculated_unadopted',conditions=[result],new_PDE=0,
        selected_SC2_condition=plan['selected_SC2_condition'],SC2_result_reused_without_recalculation=True,SC2_native_array_decode=False,
        selected_SC2_command=plan['selected_SC2_command'],SC4_source_case_id=SC4_ID,SC4_source_run_id=SC4_RUN,
        actual_target_direction_set=direction_receipt,SC_sensitivity=result['SC_sensitivity'],
        canonical_SC2_reference=canonical,cached_original_SC4_reference=plan['cached_original_SC4_reference'],
        cached_original_SC4_scalar_arrays_used=False,cached_original_SC4_caps_used=False,
        fixed_SC2_cutoffs_V_m=plan['fixed_SC2_cutoffs_V_m'],native_five_gate_validation=plan['native_five_gate_validation'],
        candidate_adopted=False,numerical_validation_promoted=False,full_convergence_validated=False,experimentally_validated=False,
        root_selection_decision=plan['root_selection_decision'],holds=plan['holds'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--prepare',type=Path);group.add_argument('--preregistration',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--native-registration',type=Path)
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
        def interrupted(signum,frame):raise TimeoutError('Controlled600s/60s-source/120s-condition stop signal '+str(signum))
        previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for signum in previous:signal.signal(signum,interrupted)
        signal.setitimer(signal.ITIMER_REAL,60)
        try:
            if args.prepare:
                require(not args.prepare.exists()and not args.prepare.with_name(args.prepare.name+'.failure.json').exists()and
                    not args.prepare.resolve().is_relative_to(output),
                    'New preregistration must remain outside the untouched actual output directory')
                require(args.native_registration is not None,'Main native registration must supply the selected SC2 command');plan=make_preregistration(args.native_registration,output);args.prepare.parent.mkdir(parents=True,exist_ok=True)
                drive.write_json(args.prepare,plan);status='preregistered_not_executed'
            else:
                output.mkdir();thread=threading.Thread(target=heartbeat,daemon=True);thread.start();checkpoint('verify_plan')
                plan,plan_sha=verify_plan(args.preregistration.resolve(),output)
                result=execute(plan,output,deadline,checkpoint)
                verify_plan(args.preregistration.resolve(),output,expected=plan_sha);guard()
                result.update(implementation_receipt(),preregistration=dict(path=str(args.preregistration.resolve()),SHA256=plan_sha),
                    input_sha256=plan['input_sha256'],inputs_unchanged=True,resources=dict(CPU_count=1,max_batch_seconds=600,max_condition_seconds=120,
                        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,wall_seconds=time.monotonic()-started,
                        cumulative_budget_limit_seconds=policy.effective_limit(ledger),new_PDE=0))
                drive.write_json(output/'summary.json',result);status=result['status'];checkpoint('complete')
        except BaseException as error:
            failure=type(error).__name__+': '+str(error)
            if output.exists():drive.write_json(output/'failure.json',dict(status=status,error=failure,phase=state.get('phase'),
                condition_id=state.get('condition_id'),new_PDE=0,partial_artifacts_preserved=True,automatic_retry=False))
            elif args.prepare:
                failure_path=args.prepare.with_name(args.prepare.name+'.failure.json')
                if not failure_path.exists():
                    failure_path.parent.mkdir(parents=True,exist_ok=True)
                    drive.write_json(failure_path,dict(status=status,error=failure,new_PDE=0,partial_artifacts_preserved=True,automatic_retry=False))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='rounded_sc4_post_prepare'if args.prepare else'rounded_sc4_sensitivity',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
