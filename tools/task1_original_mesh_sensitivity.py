"""Two cached original-square mesh sensitivities at one frozen fine command.

No PDE, optimization, SC2 native array decode, source renormalization, burden
rematch, original deletion, convergence promotion or experimental validation.
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
import task1_rounded_sc4_sensitivity as frozen_SC_policy
import task1_original_cached_drive as original
import task1_original_drive_refinement as refinement
ROOT=base.ROOT;GIB=base.GIB;PAIR=base.PAIR;FREQUENCIES=base.FREQUENCIES
require=base.require;view=base.view;drive=base.drive;volume=base.volume;waveform=base.waveform
carrier=base.carrier;frequency=base.frequency;screen=base.screen;core=base.core;policy=base.policy;routing=base.routing
BASELINE_SUMMARY=original.BASELINE_SUMMARY
SELECTED_SUMMARY=ROOT/'docs/cloud-original-drive-refinement-20261021T222000Z/summary.json'
SELECTED_ID='original-refine-3e018f8a317a'
SELECTED_CONDITION=SELECTED_SUMMARY.parent/SELECTED_ID/'condition.json'
OLD_MESH_FAILURE=ROOT/'docs/cloud-restart-20261020/mesh-convergence.json'
SCHEMA='task1-original-mesh-sensitivity-preregistration-v1'
COHORTS=(dict(id='sc4',axis='SC',run_id='cloud-mesh-c1-20261019T190000Z',case_id='baseline-square15-sc4',h_xy_mm=.625,sc_cells=4,cells=361728),
    dict(id='xy_coarse',axis='XY',run_id='cloud-baseline-20261019T185900Z',case_id='baseline-square15-coarse',h_xy_mm=1.25,sc_cells=2,cells=88480))
OUTPUT_BOUND_BYTES=8*1024**2
RESOURCE_CONTRACT=dict(total_seconds=360,source_load_seconds_each=30,per_condition_seconds=120,finalization_seconds=30,
    CPU_count=1,RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,max_added_bytes=OUTPUT_BOUND_BYTES,
    conditions=2,new_PDE=0,derivative_export='compact_float64_metrics_and_probes_no_new_scalar_NPZ')
SENSITIVITY_LIMITS=copy.deepcopy(frozen_SC_policy.SENSITIVITY_LIMITS)
POWER_KEYS=frozen_SC_policy.POWER_KEYS;J95_KEYS=frozen_SC_policy.J95_KEYS
decode_coefficients=frozen_SC_policy.decode_coefficients
COMPACT_ARTIFACT_FILENAMES=refinement.COMPACT_ARTIFACT_FILENAMES
SCALAR_ARCHIVE_OMISSION_REASON=refinement.SCALAR_ARCHIVE_OMISSION_REASON
compact_artifact_manifest=refinement.compact_artifact_manifest


def fixed_fine_modes(saved_modes):
    require(set(saved_modes)==set(screen.MODES),'All five saved fine SC2 comparison modes required')
    result={}
    for name,old in saved_modes.items():
        scale=old['amplitude_scale'];require(type(scale)in(int,float)and math.isfinite(scale)and scale>0,'Saved positive fine amplitude required')
        result[name]=dict(amplitude_scale=scale,fixed_fine_reference_scale=scale,historical_fine_mode_id=name,
            rematched=False,normalization_scope='frozen_fine_scale_no_new_mesh_rematch',
            matches_fine_current_on_new_mesh=False,matches_fine_power_on_new_mesh=False,matches_fine_skin_burden_on_new_mesh=False,
            interpretation='Mode name identifies the original fine comparison only. Exact fine amplitude is reused; equality of current, power or skin burden on this mesh is not asserted.')
    return result


def validate_mesh_config(before,after,axis):
    require(before.keys()==after.keys(),'Same physical property key set required')
    original.validate_original_config(before,before);original.validate_original_config(after,after)
    changed={k for k in before if before[k]!=after[k]}
    if axis=='SC':
        require({'validation.sc_cells'}<=changed<= {'validation.sc_cells','mask.path'} and
            before['validation.sc_cells']=='2'and after['validation.sc_cells']=='4'and
            float(before['h_mm'])==float(after['h_mm'])==.625 and before['mask.sha256']==after['mask.sha256'],
            'SC contrast changes2 to4 cells only, plus optional byte-identical mask path alias')
    elif axis=='XY':
        require(changed=={'h_mm','mask.path','mask.sha256'}and float(before['h_mm'])==.625 and float(after['h_mm'])==1.25 and
            before['validation.sc_cells']==after['validation.sc_cells']=='2',
            'XY contrast changes.625 to1.25 only, plus its same-physical-rectangle mesh mask')
    else:raise ValueError('Only SC and XY independent contrast cohorts are registered')
    return dict(axis=axis,changed_properties=sorted(changed),physical_rectangles_tissue_contact_circuit_unchanged=True,
        phantom_diameter_mm=50.,layer_thicknesses_mm=[.1,5.,5.,15.],physical_area_mm2_per_pad=225.,physical_total_area_mm2=900.)


def roi_volume_diagnostic(fine_regions,new_regions,axis):
    require(set(fine_regions)==set(new_regions)and bool(fine_regions),'Identical physical ROI names required')
    rows=[]
    for region in fine_regions:
        for metric in volume.METRICS:
            old,new=fine_regions[region][metric]['volume_m3'],new_regions[region][metric]['volume_m3']
            require(all(type(v)in(int,float)and math.isfinite(v)and v>0 for v in(old,new)),'Actual positive represented native ROI volumes required')
            agrees=math.isclose(old,new,rel_tol=1e-10,abs_tol=1e-15)
            if axis=='SC':require(agrees,'Same XY SC-only represented ROI volumes must agree')
            rows.append(dict(region=region,metric=metric,fine_volume_m3=old,new_mesh_volume_m3=new,
                relative_change=(new-old)/old,agrees_within_SC_tolerance=agrees))
    return dict(status='represented_native_volumes_reported',axis=axis,rows=rows,
        analytic_volume_renormalization=False,weights='Actual native cell fractional physical ROI overlap and h^2*dz; fixed r5/depth15to20 and surface0to5 masks',
        equality_required=axis=='SC',coarse_volumes_forced_to_fine=False,
        scope='Same physical mask definitions. XY cylinder staircase/native sampling may change represented volume; the actual volume is retained.')


def sensitivity_checks(fine_modes,new_modes,baseline,axis):
    checks=[];flips=[]
    def compare(mode,name,old,new,limit):
        require(all(type(v)in(int,float)and math.isfinite(v)and v>=0 for v in(old,new)),'Finite nonnegative sensitivity metrics required')
        rel=abs(new-old)/old if old else(None if new else 0.)
        checks.append(dict(historical_fine_mode_id=mode,metric=name,fine=old,new_mesh_same_amplitude=new,
            absolute_relative_change=rel,relative_limit=limit,passed=rel is not None and rel<=limit+1e-12))
    for name in('raw_1Vpp','skin_contact_only'):
        old,new=fine_modes[name],new_modes[name]
        require(new['amplitude_scale']==old['amplitude_scale']and new['rematched']is False,'Exact historical fine amplitudes required')
        for stat in('mean','p10'):compare(name,'primary_maxTIS_'+stat,old['regions'][volume.PRIMARY]['maxTIS'][stat],new['regions'][volume.PRIMARY]['maxTIS'][stat],.01)
        for region in('surface_0_5','primary_complement'):compare(name,region+'_maxTIS_p95',old['regions'][region]['maxTIS']['p95'],new['regions'][region]['maxTIS']['p95'],.02)
        a=old.get('actual_burdens',old.get('normalized_burdens'));b=new['actual_burdens']
        require(isinstance(a,dict),'Actual fine skin/contact J and losses required')
        for key in(*J95_KEYS,*POWER_KEYS):compare(name,key,a[key],b[key],.02)
        before=screen.screen_checks(dict(normalizations={'skin_contact_only':old}),baseline)
        after=screen.screen_checks(dict(normalizations={'skin_contact_only':new}),baseline)
        for x,y in zip(before,after):flips.append(dict(historical_fine_mode_id=name,gate=x['name'],fine_passed=x['passed'],
            new_mesh_same_amplitude_passed=y['passed'],unchanged=x['passed']==y['passed']))
    return dict(all_passed=all(c['passed']for c in checks)and all(r['unchanged']for r in flips),axis=axis,checks=checks,
        screen_status_no_flip=all(r['unchanged']for r in flips),screen_status_comparisons=flips,thresholds=SENSITIVITY_LIMITS,
        numerical_validation_promoted=False,full_convergence_validated=False,previous_XY_failures_closed=False,
        scope='Two-level independent SC or XY diagnostic at raw and frozen fine skin8 amplitude only; not bulk/edge/contact convergence or experimental validation')


def implementation_receipt():
    modules=(base,optimizer,frozen_SC_policy,original,refinement,drive,volume,waveform,carrier,frequency,screen,core,policy,view,routing,base.ranking,base.strong)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_original_mesh_sensitivity.py',*[Path(m.__file__).resolve()for m in modules]]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();refs={}
    for p in dict.fromkeys(paths):
        require(p.read_bytes()==subprocess.check_output(['git','show',commit+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT),'Commit all consumed mesh sensitivity source/tests: '+str(p));refs[str(p)]=view.sha(p)
    return dict(implementation_git_commit=commit,implementation_files_sha256=refs)


def context_metadata(decision_path,feedback_path,pins):
    require(decision_path is not None and feedback_path is not None,'Explicit root decision and actual feedback GET context required')
    def bound(path):
        path=Path(path)
        require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and
            not path.is_symlink()and path.stat().st_size<=25*1024**2,'Canonical local public JSON context required')
        digest=view.sha(path);value=view.read(path);require(view.sha(path)==digest,'Context changed while reading')
        pins[str(path)]=digest;return value,dict(path=str(path),SHA256=digest)
    decision,dref=bound(decision_path);feedback,fref=bound(feedback_path)
    require(decision.get('schema')=='task1-original-mesh-sensitivity-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and
        decision.get('new_PDE')==0 and decision.get('selected_condition_id')==SELECTED_ID and
        decision.get('conditions')==[dict(c)for c in COHORTS]and decision.get('resource_contract')==RESOURCE_CONTRACT,
        'Exact root-selected fixed-command two cached mesh sensitivity cohorts required; no peer agreement inferred')
    refs=decision.get('input_sha256');require(isinstance(refs,dict)and bool(refs),'Root decision must bind completed scientific evidence')
    require(all(refs.get(str(p))==view.sha(p)for p in(SELECTED_SUMMARY,SELECTED_CONDITION,OLD_MESH_FAILURE,BASELINE_SUMMARY)),
        'Root decision must bind selected fine result, original mesh failure evidence and canonical source')
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



def cohort_metadata(declared,canonical,refs):
    path=ROOT/'data-native'/declared['run_id']/'postprocess'/declared['case_id']/'summary.json'
    item=view.load_case(path);case=item['case'];meta=item['summary']['mesh_metadata'];before=canonical['config'];after=item['config']
    contrast=validate_mesh_config(before,after,declared['axis'])
    require(case['design']==canonical['case']['design']and item['circuit']==canonical['circuit']and
        case['source_coating_nm']==10 and case['source_Rs_fit_window_Hz']==500,'Exact same physical original rectangles/circuit/nominal contact provenance required')
    require(meta['h_xy_mm']==declared['h_xy_mm']and meta['sc_cells']==declared['sc_cells']and meta['cells']==declared['cells']and
        meta['bulk_layer_counts']==[14,14,40]and meta['tissue_boundaries_mm']==[0,.1,5.1,10.1,25.1],
        'Exact registered independently varied native mesh required')
    for key in('radius_mm','total_depth_mm','channels','frequencies_Hz','phasor_convention','source_peak_V','source_resistance_ohm',
        'field_reconstruction','side_bottom_boundary','tissue_boundaries_mm','bulk_layer_counts'):
        require(meta[key]==canonical['summary']['mesh_metadata'][key],'Physical/reconstruction native metadata mismatch: '+key)
    require(meta['field_reconstruction']=='half_face_flux; top contact term averaged over full cell face h^2','Exact half-face-flux ABI required')
    record_path=item['run']/'cases'/(case['id']+'.json');record=view.read(record_path)
    require(record['status']=='complete'and record['config_sha256']==case['config_sha256']and
        record['postprocess_sha256']==view.sha(path)and all(record['validation'][k]<=v for k,v in core.GATES.items()),
        'Completed source-bound five native equation gates required; this is not a mesh-convergence gate')
    refs.update(base.ranking.input_refs(item));refs.update(item['summary']['input_sha256']);refs[str(Path(case['mask_file']))]=case['mask_sha256']
    for name in('volume.npz',item['summary']['artifacts']['probes_json']):refs[str(path.parent/name)]=item['summary']['artifacts']['files'][name]['SHA256']
    refs[str(record_path)]=view.sha(record_path);manifest=item['run']/'frozen-source-manifest.json';refs[str(manifest)]=view.sha(manifest)
    for name in('selectivity_postprocess.py','selectivity_volume.py','layered_probe_analysis.py','explore_tis.py','explore_inputs.py'):
        p=item['run']/'frozen-source/tis-java'/name;old=canonical['run']/'frozen-source/tis-java'/name
        require(view.sha(p)==view.sha(old),'Mesh cohorts must use byte-identical frozen numerical helper: '+name);refs[str(p)]=view.sha(p);refs[str(old)]=view.sha(old)
    return dict(**declared,summary_path=str(path),source_commit=item['registration']['source_commit'],configuration_sha256=case['config_sha256'],
        mask_sha256=case['mask_sha256'],native_input_sha256=item['summary']['input_sha256'],circuit=item['circuit'],mesh_metadata=meta,
        contrast=contrast,native_five_gate_validation=record['validation'],same_physical_geometry=True,mesh_convergence_claimed=False)


def validate_prior_mesh_failures(report):
    require(report['status']=='failed_gates_preserved'and
        len([r for r in report['comparisons']if r['axis']=='XY'and r['passed']is False])==3,
        'Preserve all three original XY waveform failed gate results')
    return dict(status=report['status'],XY_failed_waveforms=[r['waveform']for r in report['comparisons']if r['axis']=='XY'and r['passed']is False],
        closed=False,new_selected_command_diagnostic_does_not_replace_old_failures=True)


def make_preregistration(baseline_summary,output,*,decision_path,feedback_path):
    require(Path(baseline_summary).resolve()==BASELINE_SUMMARY,'Original fine source is the sole cap/cutoff reference')
    plan=drive.make_preregistration(baseline_summary,output);canonical=drive.baseline_item(baseline_summary);refs=plan['input_sha256']
    context=context_metadata(decision_path,feedback_path,refs)
    source=view.read(SELECTED_SUMMARY);selected=view.read(SELECTED_CONDITION)
    refs[str(SELECTED_SUMMARY)]=view.sha(SELECTED_SUMMARY);refs[str(SELECTED_CONDITION)]=view.sha(SELECTED_CONDITION)
    entries=[e for e in source['conditions']if e['id']==SELECTED_ID]
    require(source.get('schema')=='task1-original-drive-refinement-v1'and source.get('status')=='calculated_unadopted'and
        source.get('inputs_unchanged')is True and len(entries)==1 and entries[0]['artifacts']['condition.json']['SHA256']==refs[str(SELECTED_CONDITION)],
        'Exact completed immutable fine selected refinement result required')
    for artifact in entries[0]['artifacts'].values():
        p=Path(artifact['path']);require(view.sha(p)==artifact['SHA256'],'Fine compact selected artifact SHA differs');refs[str(p)]=artifact['SHA256']
    original.validate_existing_source_identity(selected,canonical['registration']['source_commit'],canonical['case']['config_sha256'])
    require(selected['id']==SELECTED_ID and selected['candidate_adopted']is False and selected['native_volume_metrics']['total_sampled_directions']==2074 and
        selected['source_waveform']['global_normalization']is True,'Actual selected fine2074/ONEglobal-source command required')
    coefficients=decode_coefficients(selected);family=original.free_family_evidence(coefficients,selected['coefficient_family_proof']['genes'])
    require(family['global_scale']==selected['source_waveform']['global_scale'],'Exact fine actual normalized coefficients/globalg required')
    fixed_fine_modes(selected['normalizations'])
    burden,currents=volume.burdens(canonical,base.ranking.condition(canonical));reference=source['canonical_square_reference']
    require(reference['summary_path']==str(BASELINE_SUMMARY)and reference['burdens']==burden and reference['source_current_RMS_by_output_mA']==currents and
        selected['normalizations']['skin_contact_only']['baseline_derived_numerical_limits']==burden,
        'Original fine four-square caps/current/power remain frozen; no rematch/replacement baseline')
    old=view.read(OLD_MESH_FAILURE);refs[str(OLD_MESH_FAILURE)]=view.sha(OLD_MESH_FAILURE)
    prior_failure=validate_prior_mesh_failures(old)
    cohorts=[cohort_metadata(c,canonical,refs)for c in COHORTS]
    implementation=implementation_receipt();refs.update(implementation['implementation_files_sha256']);refs.update(policy.policy_refs(policy.load_ledger()))
    plan.update(schema=SCHEMA,conditions=[dict(c)for c in COHORTS],cohorts=cohorts,resource_limits=copy.deepcopy(RESOURCE_CONTRACT),
        selected_fine_condition=dict(path=str(SELECTED_CONDITION),SHA256=refs[str(SELECTED_CONDITION)]),selected_fine_summary=dict(path=str(SELECTED_SUMMARY),SHA256=refs[str(SELECTED_SUMMARY)]),
        selected_fine_command=dict(condition_id=SELECTED_ID,coefficient_vectors=selected['coefficient_vectors'],source_waveform=selected['source_waveform'],
            five_amplitude_scales={k:v['amplitude_scale']for k,v in selected['normalizations'].items()}),
        canonical_fine_reference=reference,fixed_fine_cutoffs_V_m=selected['shared_original_square_cutoffs_V_m'],
        original_mesh_failures=dict(path=str(OLD_MESH_FAILURE),SHA256=refs[str(OLD_MESH_FAILURE)],**prior_failure),
        root_selection_context=context,sensitivity_limits=SENSITIVITY_LIMITS,new_PDE_conditions=0,fine_array_decode=False,fine_recalculation=False,
        source_renormalization=False,new_mesh_burden_rematch=False,compact_artifact_filenames=list(COMPACT_ARTIFACT_FILENAMES),
        scope='Two independent cached SC/XY mesh contrasts at exact selected fine command/all five fine amplitudes; full float64 metrics/40phi; no new NPZ')
    plan['holds']+=['Only two levels per axis; diagnostic success cannot close original three-wave XY failures or establish SC/XY/bulk/edge/contact convergence',
        'All five mode names identify saved FINE comparison scales only; their current/power/burden equality is not asserted on the other meshes',
        'Actual native fractional ROI weights retained without analytic-volume renormalization; reported XY represented volumes may differ',
        'New scalar arrays calculated in RAM only; no new NPZ/native maps, no registered executable replay/export command; all old raw/NPZ preserved']
    plan.update(implementation);return plan


def verify_plan(path,output,expected=None):
    digest=view.sha(path);plan=view.read(path)
    require(expected is None or digest==expected,'Mesh sensitivity preregistration changed')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['output_directory']==str(output)and
        plan['conditions']==[dict(c)for c in COHORTS]and plan['resource_limits']==RESOURCE_CONTRACT and plan['new_PDE_conditions']==0 and
        plan['fine_array_decode']is False and plan['fine_recalculation']is False and plan['source_renormalization']is False and
        plan['new_mesh_burden_rematch']is False and plan['sensitivity_limits']==SENSITIVITY_LIMITS,'Exact frozen mesh-only scope/output/resources required')
    for name,expected_sha in plan['input_sha256'].items():
        p=Path(name);require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and p.is_file()and not p.is_symlink()and view.sha(p)==expected_sha,
            'Pinned mesh/fine evidence changed: '+name)
    selection=plan['root_selection_context'];require(context_metadata(Path(selection['decision']['path']),Path(selection['actual_feedback']['path']),{})==selection,
        'Actual root selection/feedback changed')
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'],'Frozen mesh source/test implementation changed')
    return plan,digest


def derive_mesh(basis,geometry,volume_meta,cached,selected,post,scalar,probe,output,deadline,baseline_burdens,baseline_currents,cutoffs,base_screen,checkpoint):
    declared=dict(id=selected['id']+'-'+cached['cohort']['id']+'-same-command',waveform=selected['waveform'])
    coefficients=decode_coefficients(selected);seed=copy.deepcopy(coefficients)
    sourceproof=copy.deepcopy(selected['source_waveform'])
    familyproof=dict(exact_selected_fine_coefficients_reused=True,new_source_normalization_performed=False,
        source_peak_basis_V=.5,source_resistance_ohm=50,physical_outputs=2,common_GND_nodes=1)
    checkpoint('frozen_fine_command_reused',condition_id=declared['id'])
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
    # The full scalar arrays are float64 in memory; compact derivative writes no new NPZ.
    drive.write_json(output/'native-volume-metrics.json',native['metrics'])
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
        source_drive='Exact fine selected -j command; actual activity is explicit in the unchanged coefficient vectors')
    drive.write_json(output/'probes.json',probes)
    probecheck=waveform.probe_check(dict(id=declared['id'],probe40=probes))
    fieldcheck=waveform.field_check(dict(id=declared['id'],waveform=declared['waveform'],actual_fundamental_Hz=list(PAIR),metrics=electrical))
    fixed=fixed_fine_modes(selected['normalizations'])
    def fill_mode(mode,scope):
        scale=mode['amplitude_scale'];mode['regions']=volume.summarize_regions(arrays,regions,basis['grid'],scale,cutoffs)
        mode['source_output_RMS_by_output_mA']=[v*scale for v in currents]
        mode['actual_sum_source_output_RMS_mA']=sum(currents)*scale
        mode['signed_per_output_power_evidence']=base.signed_output_powers(electrical,scale)
        mode['physical_pad_current_RMS_mA']=[v*scale for v in padcurrents['physical_pad_current_RMS_mA']]
        mode['return_net_and_local_current_evidence']=base.scaled_return_local_evidence(returnlocal,scale)
        mode['probe40_unloaded']=drive.scaled_probe_rows(probes,scale)
        mode['actual_source_Vpp_intervals_V']=(np.asarray(sourceproof['source_Vpp_intervals_V'])*scale).tolist()
        mode['actual_burdens']={k:v*scale**volume.BURDENS[k]for k,v in burdens.items()}
        mode['actual_power_metrics_W']={k:v*scale**2 for k,v in losses['metrics'].items()}
        mode['comparison_scope']=scope
        mode['original_fine_eight_caps']={k:baseline_burdens[k]for k in screen.CAP_DEGREES}
        mode['actual_skin_cap_ratios']={k:mode['actual_burdens'][k]/baseline_burdens[k]for k in screen.CAP_DEGREES}
        mode['all_original_fine_eight_caps_satisfied']=all(v<=1+1e-12 for v in mode['actual_skin_cap_ratios'].values())
        mode['original_fine_source_power_reference_W']=baseline_burdens['source_power_W']
        require(time.monotonic()<deadline,'Mesh actual120s condition postprocessing deadline exceeded')
    for mode in fixed.values():fill_mode(mode,'Exact historical fine amplitude; current/power/burden equality is not asserted on this mesh')
    checks=screen.screen_checks(dict(normalizations={'skin_contact_only':fixed['skin_contact_only']}),base_screen)
    sc2_modes=copy.deepcopy(selected['normalizations'])
    for mode in sc2_modes.values():
        mode['actual_burdens']=copy.deepcopy(mode['normalized_burdens'])
    physical_ROI=roi_volume_diagnostic(sc2_modes['skin_contact_only']['regions'],fixed['skin_contact_only']['regions'],cached['cohort']['axis'])
    sensitivity=sensitivity_checks(sc2_modes,fixed,base_screen,cached['cohort']['axis'])
    result=dict(schema='task1-original-mesh-sensitivity-condition-v1',status='calculated_unadopted',**declared,
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
        native_volume_XYZ_directional_scalar_archives='No XYZ archive. Fixed diagonal/max2074/full-carrier RMS volume arrays actually calculated in RAM only; new maps require separately registered reconstruction',
        native_volume_metrics=native['metrics'],fixed_fine_amplitude_modes=fixed,rematched=False,
        selected_fine_condition_id=selected['id'],same_source_coefficients_and_whole_Vpp=True,represented_ROI_volumes=physical_ROI,mesh_sensitivity=sensitivity,raw_mode='historical_fine_raw_1Vpp',
        source_geometry_unchanged=True,shared_original_square_cutoffs_V_m=cutoffs,
        raw_carrier_balance_regions={region:{key:carrier.weighted(value,w,basis['grid'])for key,value in balance.items()
            if key in('carrier0_RMS_V_m','carrier1_RMS_V_m','combined_fundamental_RMS_V_m','max_direction_balance','fixed_direction_balance')}
            for region,w in regions.items()},probe_waveform_audit=probecheck,field_waveform_audit=fieldcheck,
        primary_fixed_fine_skin8_screen=dict(checks=checks,all_screen_checks_passed=all(c['passed']for c in checks),
            failed_checks=[c['name']for c in checks if not c['passed']],normalization='frozen_fine_skin_contact_only_amplitude_not_rematched'),
        new_PDE=0,candidate_adopted=False,instrument_loading_validated=False,full_convergence_validated=False,experimentally_validated=False,
        cohort=cached['cohort'],new_volume_scalar_archive_written=False,new_volume_scalar_archive_not_written_reason=SCALAR_ARCHIVE_OMISSION_REASON,
        source_reconstruction=mesh_reconstruction_recipe(basis,coefficients,cached),old_XY_failures_closed=False)
    drive.write_json(output/'condition.json',result)
    return dict(id=declared['id'],status=result['status'],waveform=declared['waveform'],source_Vpp_intervals_V=sourceproof['source_Vpp_intervals_V'],
        mesh_sensitivity=sensitivity,canonical_screen_all_passed=all(c['passed']for c in checks),artifacts=compact_artifact_manifest(output),
        new_volume_scalar_archive_written=False,new_volume_scalar_archive_not_written_reason=SCALAR_ARCHIVE_OMISSION_REASON)



def mesh_reconstruction_recipe(basis,coefficients,cached):
    item=cached['item']
    return dict(status='source_bound_recipe_independent_export_unverified',native_input_sha256=basis['hashes'],
        source_summary_path=str(item['path']),source_summary_SHA256=view.sha(item['path']),
        frozen_fine_mode_amplitude_scales=cached['fine_scales'],
        frozen_numerical_helpers_sha256={str(BASELINE_SUMMARY.parents[2]/'frozen-source/tis-java'/name):view.sha(BASELINE_SUMMARY.parents[2]/'frozen-source/tis-java'/name)for name in('selectivity_postprocess.py','selectivity_volume.py','layered_probe_analysis.py','explore_tis.py','explore_inputs.py')},
        actual_coefficients={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in coefficients.items()},
        source_ROI_weight_archive=dict(path=str(item['path'].parent/'volume.npz'),SHA256=item['summary']['artifacts']['files']['volume.npz']['SHA256']),
        native_grid_configuration_sha256=basis['metadata']['config_sha256'],scalar_dtype='float64 in RAM',
        scalar_method='Frozen scalar.evaluate_volume on native complex E with exact fine coefficients and unchanged actual native fractional ROI weights,2074directions',
        analytic_volume_renormalization=False,old_raw_and_scalar_archives_preserved=True,new_scalar_archive_written=False,
        executable_scalar_export_command_registered=False,independent_scalar_export_reproduction_verified=False,
        required_future_action='Root must register a distinct bounded replay/export with new output, locks and storage/budget admission before exporting scalar arrays')


def execute(plan,output,deadline,checkpoint):
    selected=view.read(plan['selected_fine_condition']['path'])
    canonical_run=BASELINE_SUMMARY.parents[2];post,scalar,probe=drive.import_frozen(canonical_run,plan)
    dirs=optimizer.frozen_direction_set(post,scalar)
    direction_receipt=dict(count=2074,dtype=str(dirs.dtype),SHA256=hashlib.sha256(dirs.tobytes(order='C')).hexdigest(),
        source='Actual frozen point/volume byte-identical ordered real2074 set; helpers SHA-identical across all cohorts',continuous_maximum=False)
    require(direction_receipt['SHA256']==view.read(SELECTED_SUMMARY)['actual_target_direction_set']['SHA256'],'Exact fine sampled direction set required')
    reference=plan['canonical_fine_reference'];results=[]
    for cohort in plan['cohorts']:
        require(deadline-time.monotonic()>=180,'Preserve source30+condition120+final30 before starting a cohort')
        source_deadline=min(deadline-150,time.monotonic()+30);signal.setitimer(signal.ITIMER_REAL,max(.001,source_deadline-time.monotonic()))
        checkpoint('cached_mesh_source_loading',cohort_id=cohort['id'])
        item=view.load_case(cohort['summary_path']);cached=volume.load_native(item);cached['cohort']=cohort
        cached['fine_scales']=plan['selected_fine_command']['five_amplitude_scales']
        basis=post._load_basis(item['run']/'bases'/item['case']['id'],item['case'],source_deadline)
        require(basis['hashes']==cohort['native_input_sha256']and np.array_equal(basis['grid'],cached['grid']),'Actual native cached mesh/grid/source hash differs')
        geometry,volume_meta=post._geometry(basis,item['case'])
        per=min(deadline-30,time.monotonic()+120);signal.setitimer(signal.ITIMER_REAL,max(.001,per-time.monotonic()))
        folder=output/(SELECTED_ID+'-'+cohort['id']+'-same-command');folder.mkdir()
        result=derive_mesh(basis,geometry,volume_meta,cached,selected,post,scalar,probe,folder,per,
            reference['burdens'],reference['source_current_RMS_by_output_mA'],plan['fixed_fine_cutoffs_V_m'],reference['screen_baseline'],checkpoint)
        results.append(result);signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
        checkpoint('cached_mesh_complete',cohort_id=cohort['id']);del basis,cached,geometry,volume_meta
    return dict(schema='task1-original-mesh-sensitivity-v1',status='calculated_unadopted',conditions=results,new_PDE=0,
        selected_fine_condition=plan['selected_fine_condition'],selected_fine_summary=plan['selected_fine_summary'],selected_fine_command=plan['selected_fine_command'],
        fine_result_reused_without_recalculation=True,fine_native_array_decode=False,source_renormalization=False,new_mesh_burden_rematch=False,
        canonical_fine_reference=reference,fixed_fine_cutoffs_V_m=plan['fixed_fine_cutoffs_V_m'],actual_target_direction_set=direction_receipt,
        original_mesh_failures=plan['original_mesh_failures'],previous_XY_failures_closed=False,new_volume_scalar_archive_written=False,
        new_volume_scalar_archive_not_written_reason=SCALAR_ARCHIVE_OMISSION_REASON,compact_artifact_filenames=list(COMPACT_ARTIFACT_FILENAMES),
        root_selection_context=plan['root_selection_context'],candidate_adopted=False,numerical_validation_promoted=False,
        full_convergence_validated=False,experimentally_validated=False,holds=plan['holds'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--prepare',type=Path);group.add_argument('--preregistration',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--baseline-summary',type=Path,default=BASELINE_SUMMARY)
    parser.add_argument('--decision',type=Path);parser.add_argument('--feedback',type=Path)
    args=parser.parse_args();output=args.output.resolve()
    require(output.is_relative_to(ROOT/'docs')and not output.exists(),'Unique new docs output directory required')
    with(ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledger_path);cap=60 if args.prepare else 360
        require(policy.remaining_seconds(ledger)>=cap,'Finite admission budget missing')
        require(shutil.disk_usage(output.parent).free>=2*GIB+OUTPUT_BOUND_BYTES,'Preserve2GiB reserve plus8MiB bounded artifacts')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();deadline=started+cap
        status='failed_preserved';failure=None;state={};counter=0;mutex=threading.RLock();stop=threading.Event();thread=None
        def guard():
            require(core.rss(os.getpid())<3*GIB,'Existing3GiB RSS cap exceeded')
            require(shutil.disk_usage(output.parent).free>=2*GIB,'Existing2GiB disk reserve exhausted')
            if output.exists():require(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=OUTPUT_BOUND_BYTES,'New artifacts exceed8MiB cap')
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
        def interrupted(signum,frame):
            raise TimeoutError('Controlled360s/30s-source/120s-condition stop signal '+str(signum))
        previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for signum in previous:signal.signal(signum,interrupted)
        signal.setitimer(signal.ITIMER_REAL,cap if args.prepare else 30)
        try:
            if args.prepare:
                require(not args.prepare.exists()and not args.prepare.with_name(args.prepare.name+'.failure.json').exists()and
                    not args.prepare.resolve().is_relative_to(output),
                    'New preregistration must remain outside the untouched actual output directory')
                plan=make_preregistration(args.baseline_summary,output,decision_path=args.decision,feedback_path=args.feedback);args.prepare.parent.mkdir(parents=True,exist_ok=True)
                drive.write_json(args.prepare,plan);status='preregistered_not_executed'
            else:
                output.mkdir();thread=threading.Thread(target=heartbeat,daemon=True);thread.start();checkpoint('verify_plan')
                plan,plan_sha=verify_plan(args.preregistration.resolve(),output)
                result=execute(plan,output,deadline,checkpoint)
                verify_plan(args.preregistration.resolve(),output,expected=plan_sha);guard()
                result.update(implementation_receipt(),preregistration=dict(path=str(args.preregistration.resolve()),SHA256=plan_sha),
                    input_sha256=plan['input_sha256'],inputs_unchanged=True,resources=dict(CPU_count=1,max_batch_seconds=360,max_source_seconds_each=30,max_condition_seconds=120,
                        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,wall_seconds=time.monotonic()-started,
                        cumulative_budget_limit_seconds=policy.effective_limit(ledger),new_PDE=0))
                drive.write_json(output/'summary.json',result);status=result['status'];checkpoint('complete')
        except BaseException as error:
            failure=type(error).__name__+': '+str(error)
            if output.exists():drive.write_json(output/'failure.json',dict(status=status,error=failure,phase=state.get('phase'),
                condition_id=state.get('condition_id'),new_PDE=0,partial_artifacts_preserved=True,automatic_retry=False,
                resume_condition='Root reviews preserved completed checkpoints and remaining existing budget before a new preregistered bounded run'))
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
            ledger['runs'].append(dict(run_id=output.name,stage='original_mesh_sensitivity_prepare'if args.prepare else'original_mesh_sensitivity',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
