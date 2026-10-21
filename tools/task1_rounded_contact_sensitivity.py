"""Two SC4 contact-impedance uncertainty readbacks; no nominal-field recomputation.

Frozen SC2 amplitudes and supplemental original-SC2-constant rematches remain
separate. Relative changes are reported without an invented acceptance cutoff.
"""
from __future__ import annotations
import argparse
import copy
import fcntl
import hashlib
import importlib
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
import task1_rounded_sc4_sensitivity as previous
ROOT=previous.ROOT;GIB=previous.GIB;PAIR=previous.PAIR;FREQUENCIES=previous.FREQUENCIES
base=previous.base;optimizer=previous.optimizer;require=previous.require;view=previous.view;drive=previous.drive
volume=previous.volume;waveform=previous.waveform;carrier=previous.carrier;frequency=previous.frequency
screen=previous.screen;core=previous.core;policy=previous.policy;routing=previous.routing
SCHEMA='task1-rounded-contact-sensitivity-preregistration-v1'
NATIVE_RUN='cloud-rounded-contact-20261021T210000Z'
FACTORS=(.5,2.)
CASE_IDS=('rounded-fullface225-contact0p5-sc4-xy80','rounded-fullface225-contact2-sc4-xy80')
OUTPUT_BOUND_BYTES=128*1024**2
decode_coefficients=previous.decode_coefficients
fixed_sc2_modes=previous.fixed_sc2_modes
validate_roi_volumes=previous.validate_roi_volumes


def validate_storage(free_bytes,added_bytes=0,initial=False):
    require(type(free_bytes)is int and type(added_bytes)is int and free_bytes>=0 and added_bytes>=0,
        'Explicit nonnegative storage bytes required')
    require(OUTPUT_BOUND_BYTES<=2*GIB and added_bytes<=OUTPUT_BOUND_BYTES,
        'Two-case contact post artifacts exceed registered128MiB bound; existing2GiB maximum is unchanged')
    require(free_bytes>=2*GIB+(OUTPUT_BOUND_BYTES if initial else 0),
        'Preserve2GiB free reserve and the registered128MiB initial output allowance')
    return True


def validate_contact_config(before,after,factor):
    require(type(factor)in(int,float)and factor in FACTORS,'Exactly0.5 or2 times nominal complex specific contact impedance required')
    require(before.keys()==after.keys()and before.get('validation.sc_cells')==after.get('validation.sc_cells')=='4',
        'Same SC4 properties schema required')
    zkeys={f'z.{f}.{part}'for f in FREQUENCIES for part in('re','im')}
    allowed=zkeys|{'mask.path'}
    require(all(before[k]==after[k]for k in before if k not in allowed)and before.get('mask.sha256')==after.get('mask.sha256'),
        'Only complex specific interface impedance and byte-identical mask path alias may change')
    for key in zkeys:
        a,b=float(before[key]),float(after[key])
        require(math.isfinite(a)and math.isfinite(b)and math.isclose(b,a*factor,rel_tol=1e-12,abs_tol=1e-15),
            'Every real and imaginary specific contact-Z component must receive the exact registered factor')
    return dict(complex_specific_contact_impedance_factor=factor,changed_config_fields=sorted(k for k in before if before[k]!=after[k]),
        units='ohm*m^2 unchanged; factor is dimensionless',additional_Rs_subtraction=False,contact_area_rescaling=False,
        physical_mask_SHA256=before['mask.sha256'],SC_cells=4,source_output_resistance_unchanged=True,
        interpretation='Uncertain PBS-to-skin contact-model transfer diagnostic; not a new validated measured skin interface')


def contact_comparisons(nominal_modes,condition_fixed_modes,baseline):
    require(set(nominal_modes)==set(condition_fixed_modes)==set(screen.MODES),'All five fixed historical SC2 amplitudes required')
    rows=[]
    def difference(name,a,b):
        require(all(type(v)in(int,float)and math.isfinite(v)for v in(a,b)),'Finite actual nominal/contact comparison values required')
        relative=b/a-1 if a else None
        return dict(name=name,nominal=a,condition=b,signed_delta=b-a,relative_change=relative,
            absolute_relative_change=abs(relative)if relative is not None else None)
    for name in screen.MODES:
        old,new=nominal_modes[name],condition_fixed_modes[name]
        require(old['amplitude_scale']==new['amplitude_scale'],'Contact uncertainty primary comparisons must preserve the exact SC2 amplitude')
        metrics=[]
        for region in old['regions']:
            require(region in new['regions'],'Same physical ROI names required')
            a,b=old['regions'][region]['maxTIS'],new['regions'][region]['maxTIS']
            for stat in('mean','p10','p95','p99','max','std','CV'):
                if stat in a and stat in b and a[stat]is not None and b[stat]is not None:metrics.append(difference(region+'_maxTIS_'+stat,a[stat],b[stat]))
            for cutoff,entry in a.get('fixed_baseline_threshold_volume',{}).items():
                metrics.append(difference(region+'_high_volume_at_'+cutoff,entry['volume_m3'],b['fixed_baseline_threshold_volume'][cutoff]['volume_m3']))
        a=old.get('actual_burdens',old.get('normalized_burdens'));b=new.get('actual_burdens',new.get('normalized_burdens'))
        require(isinstance(a,dict)and set(a)==set(b),'Same actual skin/contact burden definitions required')
        metrics.extend(difference(key,a[key],b[key])for key in a)
        if 'actual_power_metrics_W'in old:
            metrics.extend(difference('power:'+key,value,new['actual_power_metrics_W'][key])for key,value in old['actual_power_metrics_W'].items())
        before=screen.screen_checks(dict(normalizations={'skin_contact_only':old}),baseline)
        after=screen.screen_checks(dict(normalizations={'skin_contact_only':new}),baseline)
        rows.append(dict(historical_SC2_mode_id=name,amplitude_scale=old['amplitude_scale'],metrics=metrics,
            screen_status_comparisons=[dict(gate=x['name'],nominal_passed=x['passed'],condition_passed=y['passed'],changed=x['passed']!=y['passed'])for x,y in zip(before,after)]))
    return dict(status='contact_uncertainty_comparison_not_validation',mode_comparisons=rows,
        relative_change_acceptance_threshold=None,numerical_validation_promoted=False,
        interpretation='Report changes and original eight-gate outcomes; magnitude of a change is not assigned an arbitrary sensitivity pass/fail or biological meaning')


def native_module():return importlib.import_module('task1_rounded_contact_registration')


def implementation_receipt():
    modules=(previous,base,optimizer,native_module(),drive,volume,waveform,carrier,frequency,screen,core,policy,view,routing)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_rounded_contact_sensitivity.py',ROOT/'tests/test_task1_rounded_contact_storage_admission.py',*[Path(m.__file__).resolve()for m in modules]]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();refs={}
    for p in dict.fromkeys(paths):
        require(p.read_bytes()==subprocess.check_output(['git','show',commit+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT),'Commit all consumed contact post sources/tests: '+str(p));refs[str(p)]=view.sha(p)
    return dict(implementation_git_commit=commit,implementation_files_sha256=refs)


def derive_contact(basis,geometry,volume_meta,cached,selected,post,scalar,probe,output,deadline,baseline_burdens,baseline_currents,cutoffs,base_screen,checkpoint):
    declared=dict(id=cached['item']['case']['id']+'-same-command',waveform=selected['waveform'])
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
    fixed=fixed_sc2_modes(selected['fixed_SC2_amplitude_modes'])
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
        require(time.monotonic()<deadline,'Contact actual120s condition postprocessing deadline exceeded')
    for mode in fixed.values():fill_mode(mode,'Exact historical SC2 amplitude; current/power equality on SC4 is not asserted')
    for mode in rematched.values():
        mode['SC4_rematched']=True;mode['normalization_reference']='ORIGINAL SC2 square constants only; no SC4 baseline caps'
        fill_mode(mode,'Supplemental SC4 rematch using unchanged original SC2 caps/current/power/cutoffs')
    checks=screen.screen_checks(dict(normalizations={'skin_contact_only':fixed['skin_contact_only']}),base_screen)
    supplemental_checks=screen.screen_checks(dict(normalizations=rematched),base_screen)
    physical_ROI=validate_roi_volumes(selected['fixed_SC2_amplitude_modes']['skin_contact_only']['regions'],fixed['skin_contact_only']['regions'])
    comparisons=contact_comparisons(selected['fixed_SC2_amplitude_modes'],fixed,base_screen)
    result=dict(schema='task1-rounded-contact-sensitivity-condition-v1',status='calculated_unadopted',**declared,
        complex_specific_contact_impedance_factor=cached['contact_factor'],nominal_contact_impedance_factor=1.,
        contact_configuration_contract=cached['contact_configuration_contract'],
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
        selected_SC2_condition_id=selected['selected_SC2_condition_id'],nominal_SC4_condition_id=selected['id'],same_source_coefficients_and_whole_Vpp=True,physical_ROI_volume_agreement=physical_ROI,contact_uncertainty_comparisons=comparisons,raw_mode='historical_SC2_raw_1Vpp',
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
        contact_uncertainty_comparisons=comparisons,canonical_screen_all_passed=all(c['passed']for c in checks),artifacts={name:dict(path=str(output/name),SHA256=view.sha(output/name))
            for name in('condition.json','probes.json','volume.npz','native-volume-metrics.json')})



def make_preregistration(native_registration,output):
    native_registration=Path(native_registration).resolve();run=native_registration.parent
    require(run==ROOT/'data-native'/NATIVE_RUN and native_registration.name=='preregistration.json','Exact paired rounded SC4 contact native registration required')
    pre=view.read(native_registration);refs={str(native_registration):view.sha(native_registration)}
    require(pre.get('batch_kind')=='paired_rounded_SC4_complex_contact_scale'and pre.get('gates')==core.GATES and
        tuple(c['id']for c in pre['cases'])==CASE_IDS and tuple(c['contact_impedance_complex_scale']for c in pre['cases'])==FACTORS,
        'Exactly the two registered SC4 complex-contact factors and original native gates required')
    refs.update(pre['source_and_input_sha256'])
    selection=pre['root_selection_decision'];decision=view.read(selection['path'])
    require(view.sha(selection['path'])==selection['SHA256']and decision.get('schema')=='task1-rounded-contact-root-decision-v1'and
        decision.get('status')=='selected_not_executed'and decision.get('root_selected')is True and decision.get('peer_endorsed')is False and
        decision.get('new_PDE')==2 and decision.get('new_native_RHS')==16 and decision.get('case_ids')==list(CASE_IDS)and
        decision.get('contact_complex_scales')==list(FACTORS),'Exact root-selected paired contact uncertainty decision required')
    refs[str(Path(selection['path']))]=selection['SHA256']
    nominal_refs=pre['nominal_SC4_result'];require(nominal_refs==decision['nominal_SC4_result'],'Identical main registered nominal SC4 evidence required')
    objects={}
    for key in('summary','condition'):
        ref=nominal_refs[key];require(view.sha(ref['path'])==ref['SHA256'],'Nominal SC4 result SHA differs')
        objects[key]=view.read(ref['path']);refs[ref['path']]=ref['SHA256']
    nominal_summary,nominal=objects['summary'],objects['condition']
    require(nominal_summary['schema']=='task1-rounded-sc4-sensitivity-v1'and nominal_summary['status']=='calculated_unadopted'and
        nominal_summary['inputs_unchanged']is True and nominal_summary['SC_sensitivity']['all_passed']is True and
        nominal_summary['SC4_source_case_id']==previous.SC4_ID and nominal['schema']=='task1-rounded-sc4-sensitivity-condition-v1'and
        nominal['status']=='calculated_unadopted'and nominal['source_case_id']==previous.SC4_ID and
        nominal['same_source_coefficients_and_whole_Vpp']is True and nominal['coefficient_vectors']==pre['selected_SC2_command']['raw_coefficient_vectors'],
        'Completed nominal SC4 two-level sensitivity and exact selected source coefficients required; no adoption inferred')
    entries=[c for c in nominal_summary['conditions']if c['id']==nominal['id']]
    require(len(entries)==1 and entries[0]['artifacts']['condition.json']==nominal_refs['condition'],'Nominal SC4 condition must be its genuine summary artifact')
    for ref in entries[0]['artifacts'].values():refs[ref['path']]=ref['SHA256']
    native_nominal=pre['nominal_native_registration'];require(view.sha(native_nominal['path'])==native_nominal['SHA256'],'Nominal SC4 native registration changed')
    refs[native_nominal['path']]=native_nominal['SHA256'];oldpre=view.read(native_nominal['path']);nominal_run=Path(native_nominal['path']).parent
    oldcase=next(c for c in oldpre['cases']if c['id']==previous.SC4_ID)
    require(oldpre['selected_SC2_command']==pre['selected_SC2_command'],'The root-selected SC2 coefficients and amplitudes must remain unchanged')
    oldconfig=view.properties(oldcase['config_file']);refs[oldcase['config_file']]=oldcase['config_sha256'];refs[oldcase['mask_file']]=oldcase['mask_sha256']
    oldsp=nominal_run/'postprocess'/previous.SC4_ID/'summary.json';oldpost=view.read(oldsp);refs[str(oldsp)]=view.sha(oldsp)
    oldgrid=[(path,d)for path,d in oldpost['input_sha256'].items()if Path(path).name in('grid.csv','grid.csv.gz')]
    require(len(oldgrid)==1,'One nominal SC4 physical grid provenance SHA required')
    cases=[]
    for ident,factor,case in zip(CASE_IDS,FACTORS,pre['cases']):
        sp=run/'postprocess'/ident/'summary.json';item=view.load_case(sp);meta=item['summary']['mesh_metadata']
        record_path=run/'cases'/(ident+'.json');record=view.read(record_path)
        require(record['status']=='complete'and record['postprocess_sha256']==view.sha(sp)and
            all(record['validation'][k]<=v for k,v in core.GATES.items()),'Both native contact cases must complete five native gates before post registration')
        require(case['design']==oldcase['design']and case['mask_sha256']==oldcase['mask_sha256']and item['circuit']==oldcase['circuit']and
            meta['sc_cells']==4 and meta['cells']==361728 and meta['h_xy_mm']==.625 and meta['bulk_layer_counts']==[14,14,40]and
            meta['z_faces_mm']==oldpost['mesh_metadata']['z_faces_mm']and meta['tissue_boundaries_mm']==[0,.1,5.1,10.1,25.1],
            'All physical geometry, SC4 grid/layers/circuit must equal nominal SC4')
        configproof=validate_contact_config(oldconfig,item['config'],factor)
        require(view.sha(case['mask_file'])==oldcase['mask_sha256'],'Contact factors must use byte-identical physical mask')
        native=item['summary']['input_sha256'];grid=[(path,d)for path,d in native.items()if Path(path).name in('grid.csv','grid.csv.gz')]
        require(len(grid)==1 and grid[0][1]==oldgrid[0][1],'Contact scaling must retain the identical nominal physical native grid bytes')
        refs.update(base.ranking.input_refs(item));refs.update(native);refs[str(record_path)]=view.sha(record_path);refs[case['mask_file']]=case['mask_sha256']
        for name in('volume.npz',item['summary']['artifacts']['probes_json']):refs[str(sp.parent/name)]=item['summary']['artifacts']['files'][name]['SHA256']
        cases.append(dict(id=ident,factor=factor,summary_path=str(sp),native_input_sha256=native,configuration_sha256=case['config_sha256'],
            native_five_gate_validation=record['validation'],contact_configuration_contract=configproof))
    for name in('selectivity_postprocess.py','selectivity_volume.py','layered_probe_analysis.py','explore_tis.py','explore_inputs.py'):
        path=run/'frozen-source/tis-java'/name;old=nominal_run/'frozen-source/tis-java'/name
        require(view.sha(path)==view.sha(old),'Nominal and contact-uncertainty frozen numerical helper bytes differ');refs[str(path)]=view.sha(path)
    canonical=nominal_summary['canonical_SC2_reference'];require(canonical['summary_path']==str(base.BASELINE_SUMMARY),'Original SC2 square remains sole normalization baseline')
    implementation=implementation_receipt();refs.update(implementation['implementation_files_sha256']);refs.update(policy.policy_refs(policy.load_ledger()))
    return dict(schema=SCHEMA,status='preregistered_not_executed',created_utc=core.now(),output_directory=str(output),
        native_registration=dict(path=str(native_registration),SHA256=refs[str(native_registration)]),cases=cases,nominal_SC4_result=nominal_refs,
        nominal_native_registration=native_nominal,selected_SC2_command=pre['selected_SC2_command'],canonical_SC2_reference=canonical,
        fixed_SC2_cutoffs_V_m=nominal['shared_original_square_cutoffs_V_m'],root_selection_decision=selection,source_feedback=pre['source_feedback'],
        input_sha256=refs,new_PDE_conditions=0,nominal_SC4_array_decode=False,nominal_SC4_recalculation=False,source_renormalization=False,
        contact_relative_change_acceptance_threshold=None,
        resource_limits=dict(total_seconds=600,per_condition_seconds=120,CPU_count=1,RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,
            max_added_bytes=2*GIB,registered_post_output_bound_bytes=OUTPUT_BOUND_BYTES),
        holds=['Complex specific contactZ0.5/2 times nominal PBS model is an uncertainty condition, not validated skin impedance or an optimized geometry',
            'Relative changes are diagnostic without an arbitrary pass cutoff; original eight-screen outcomes are reported individually',
            'Historical SC2 amplitudes do not imply current/power/cap equality on each contact condition; supplemental rematches use original SC2 references only',
            'SC2/SC4 mesh sensitivity does not establish XY/bulk/edge/contact convergence, experiment, activation or human safety',
            'Probes are unloaded; ETA5001 instrument loading, source absorption/compliance and phase hardware remain unverified'],**implementation)


def verify_plan(path,output,expected=None):
    digest=view.sha(path);plan=view.read(path)
    require(expected is None or digest==expected,'Contact post preregistration changed')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['output_directory']==str(output)and
        plan['new_PDE_conditions']==0 and plan['source_renormalization']is False and plan['nominal_SC4_recalculation']is False and
        plan['contact_relative_change_acceptance_threshold']is None and tuple(c['id']for c in plan['cases'])==CASE_IDS and
        tuple(c['factor']for c in plan['cases'])==FACTORS and
        plan['resource_limits']['registered_post_output_bound_bytes']==OUTPUT_BOUND_BYTES and
        plan['resource_limits']['disk_reserve_bytes']==plan['resource_limits']['max_added_bytes']==2*GIB,
        'Exact paired contact uncertainty post scope and original storage policy required')
    native=plan['native_registration'];require(native['path']==str(ROOT/'data-native'/NATIVE_RUN/'preregistration.json')and
        plan['input_sha256'].get(native['path'])==native['SHA256'],'Exact paired native registration pin required')
    pre=view.read(native['path'])
    require(pre['nominal_SC4_result']==plan['nominal_SC4_result']and pre['selected_SC2_command']==plan['selected_SC2_command'],
        'Post source selection must equal main native registration')
    for name,d in plan['input_sha256'].items():
        p=Path(name);require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and p.is_file()and not p.is_symlink()and view.sha(p)==d,
            'Pinned nominal/contact evidence changed: '+name)
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'],'Contact post implementation changed')
    return plan,digest


def execute(plan,output,deadline,checkpoint):
    nominal=view.read(plan['nominal_SC4_result']['condition']['path']);canonical=plan['canonical_SC2_reference']
    run=ROOT/'data-native'/NATIVE_RUN;post,scalar,probe=drive.import_frozen(run,plan)
    dirs=optimizer.frozen_direction_set(post,scalar)
    direction_receipt=dict(count=2074,SHA256=hashlib.sha256(dirs.tobytes(order='C')).hexdigest(),
        source='Actual frozen point/volume directions byte-identical; all numerical helper bytes equal nominal SC4',continuous_maximum=False)
    results=[]
    for declared in plan['cases']:
        per=min(deadline-60,time.monotonic()+120);require(per>time.monotonic(),'Contact post finalization reserve unavailable')
        signal.setitimer(signal.ITIMER_REAL,max(.001,per-time.monotonic()));checkpoint('contact_condition_start',condition_id=declared['id'])
        item=view.load_case(declared['summary_path']);cached=volume.load_native(item)
        cached.update(contact_factor=declared['factor'],contact_configuration_contract=declared['contact_configuration_contract'])
        basis=post._load_basis(run/'bases'/declared['id'],item['case'],min(per,time.monotonic()+60))
        require(basis['hashes']==declared['native_input_sha256']and np.array_equal(basis['grid'],cached['grid']),'Actual contact basis/grid/hash mismatch')
        geometry,volume_meta=post._geometry(basis,item['case']);folder=output/(declared['id']+'-same-command');folder.mkdir()
        result=derive_contact(basis,geometry,volume_meta,cached,nominal,post,scalar,probe,folder,per,canonical['burdens'],
            canonical['source_current_RMS_by_output_mA'],plan['fixed_SC2_cutoffs_V_m'],canonical['screen_baseline'],checkpoint)
        result.update(native_contact_case_id=declared['id'],complex_specific_contact_impedance_factor=declared['factor'],
            contact_configuration_contract=declared['contact_configuration_contract'],native_five_gate_validation=declared['native_five_gate_validation'])
        results.append(result);checkpoint('contact_condition_complete',condition_id=declared['id'])
        del basis,cached,item
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    return dict(schema='task1-rounded-contact-sensitivity-v1',status='calculated_unadopted',conditions=results,new_PDE=0,
        nominal_SC4_result=plan['nominal_SC4_result'],nominal_SC4_result_reused_without_recalculation=True,nominal_SC4_native_array_decode=False,
        selected_SC2_command=plan['selected_SC2_command'],actual_target_direction_set=direction_receipt,
        canonical_SC2_reference=canonical,fixed_SC2_cutoffs_V_m=plan['fixed_SC2_cutoffs_V_m'],
        relative_change_acceptance_threshold=None,numerical_validation_promoted=False,candidate_adopted=False,
        full_convergence_validated=False,experimentally_validated=False,root_selection_decision=plan['root_selection_decision'],holds=plan['holds'])


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
        validate_storage(shutil.disk_usage(output.parent).free,initial=True)
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();deadline=started+cap
        status='failed_preserved';failure=None;state={};counter=0;mutex=threading.RLock();stop=threading.Event();thread=None
        def guard():
            require(core.rss(os.getpid())<3*GIB,'Existing3GiB RSS cap exceeded')
            added=sum(p.stat().st_size for p in output.rglob('*')if p.is_file())if output.exists()else 0
            validate_storage(shutil.disk_usage(output.parent).free,added)
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
                require(args.native_registration is not None,'Paired native registration must supply nominal SC4 and frozen SC2 command');plan=make_preregistration(args.native_registration,output);args.prepare.parent.mkdir(parents=True,exist_ok=True)
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
            ledger['runs'].append(dict(run_id=output.name,stage='rounded_contact_post_prepare'if args.prepare else'rounded_contact_sensitivity',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
