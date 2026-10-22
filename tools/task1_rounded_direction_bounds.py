#!/usr/bin/env python3
"""Saved-field direction bounds for four rounded/square SC2/SC4 cohorts.

Reuses frozen nine-lambda PSD bounds and saved2074 lower bounds. No PDE,
direction resampling, source renormalization, adoption or convergence claim.
"""
from __future__ import annotations
import argparse
import copy
import fcntl
import gzip
import json
import math
import os
from pathlib import Path
import resource
import signal
import shutil
import subprocess
import threading
import time
import zipfile
for _key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_key]='1'
import numpy as np
import task1_direction_bounds_audit as bounds
import task1_return_position_volume_registration as native
import task1_adjacent_source_volume_registration as probes
import task1_results_view as view
import task1_volume_selectivity as volume
import task1_candidate_screen as screen
import task1_cloud_batch as core
import task1_resource_policy as policy

ROOT=Path(__file__).resolve().parents[1];GIB=1024**3
SCHEMA='task1-rounded-direction-bounds-preregistration-v1'
RESULT_SCHEMA='task1-rounded-direction-bounds-v1'
BASE_RUN=bounds.BASE_RUN;BASE_ID=bounds.BASE_ID
ROUND_RUN='cloud-rounded-fullface-20261021T200000Z';ROUND_ID='rounded-fullface225-xy80'
SC4_RUN='cloud-rounded-sc4-20261021T204000Z';SC4_ID='rounded-fullface225-sc4-xy80'
SELECTED_ID='rounded-opt-e7b3bf639935'
CONTROL_VOLUME=ROOT/'docs/cloud-rounded-fullface-context-20261021T200000Z/volume.json'
OPT_SUMMARY=ROOT/'docs/cloud-rounded-drive-optimization-20261021T203000Z/summary.json'
SC4_SUMMARY=ROOT/'docs/cloud-rounded-sc4-sensitivity-20261021T204000Z/summary.json'
SOURCE_SUMMARIES=(CONTROL_VOLUME,OPT_SUMMARY,SC4_SUMMARY)
PAIR=(3000,3030);FREQUENCIES=(3000,3030,9000,9090)
require=native.require


def _json(path,refs,expected=None):return bounds._json(path,refs,expected)


def implementation_receipt():
    modules=(bounds,native,probes,view,volume,screen,core,policy)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_rounded_direction_bounds.py',
        ROOT/'tests/test_task1_direction_bounds_audit.py',ROOT/'tests/test_task1_rounded_direction_bounds_actual_schema.py',*[Path(m.__file__).resolve()for m in modules]]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();refs={}
    for p in dict.fromkeys(paths):
        require(p.read_bytes()==subprocess.check_output(['git','show',commit+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT),
            'Commit rounded-bound implementation/helpers/tests before registration: '+str(p));refs[str(p)]=native.sha(p)
    return dict(implementation_git_commit=commit,implementation_files_sha256=refs)


def decode_coefficients(condition):
    rows=condition['coefficient_vectors']
    require(set(rows)=={str(f)for f in FREQUENCIES},'Actual four-frequency coefficient receipt required')
    decoded={}
    for f in FREQUENCIES:
        row=rows[str(f)];a=np.asarray(row['real'],float);b=np.asarray(row['imaginary'],float)
        require(set(row)=={'real','imaginary'}and a.shape==b.shape==(2,)and np.isfinite(a).all()and np.isfinite(b).all(),
            'Finite actual complex two-output coefficients required');decoded[f]=a+1j*b
    require(all(np.any(decoded[f])for f in PAIR)and not np.any(decoded[9000])and not np.any(decoded[9090]),
        'Selected optimized sine has two actual fundamentals and zero harmonics')
    return {str(f):copy.deepcopy(rows[str(f)])for f in PAIR}


def validate_fixed_modes(selected,sc4):
    require(sc4['coefficient_vectors']==selected['coefficient_vectors']and sc4['source_waveform']==selected['source_waveform']
        and sc4.get('same_source_coefficients_and_whole_Vpp')is True and sc4['selected_SC2_condition_id']==selected['id'],
        'Exact selected SC2 coefficients and whole-wave Vpp must survive SC4; no renormalization')
    old=selected['normalizations'];fixed=sc4['fixed_SC2_amplitude_modes']
    require(set(old)==set(fixed)==set(screen.MODES),'All five original SC2 amplitude modes required')
    for name in screen.MODES:
        a,b=old[name],fixed[name]
        require(type(a['amplitude_scale'])in(int,float)and math.isfinite(a['amplitude_scale'])and a['amplitude_scale']>0
            and a['amplitude_scale']==b['amplitude_scale']and b.get('SC4_skin_caps_rematched')is False
            and b.get('normalization_scope')=='frozen_SC2_amplitude_no_SC4_rematch'
            and b.get('historical_SC2_mode_id')==name,'SC4 must retain exact historical SC2 amplitude, not supplemental rematch')
        require(b['original_SC2_eight_caps']=={k:a['baseline_derived_numerical_limits'][k]for k in screen.CAP_DEGREES}
            and np.array_equal(np.asarray(b['actual_source_Vpp_intervals_V']),
                np.asarray(selected['source_waveform']['source_Vpp_intervals_V'])*a['amplitude_scale']),
            'Fixed SC4 mode must retain original SC2 caps and actual whole-wave Vpp at its saved amplitude')
    return copy.deepcopy(fixed)


def validate_mesh_identity(sc2,sc4,c2,c4):
    require(sc2['sc_cells']==2 and sc4['sc_cells']==4 and sc2['cells']==351680 and sc4['cells']==361728,
        'Genuine SC2/SC4 cell counts required; no SC2 identity adapter')
    keys=('h_xy_mm','radius_mm','total_depth_mm','bulk_layer_counts','tissue_boundaries_mm','channels',
        'source_peak_V','source_resistance_ohm','phasor_convention','field_reconstruction','frequencies_Hz')
    require(all(sc2[k]==sc4[k]for k in keys)and sc2['h_xy_mm']==.625 and sc2['bulk_layer_counts']==[14,14,40]
        and sc2['tissue_boundaries_mm']==[0,.1,5.1,10.1,25.1]and sc2['channels']==2,
        'SC-only refinement must preserve physical layers, XY/bulk, circuit and reconstruction')
    require(c2.keys()==c4.keys()and{k for k in c2 if c2[k]!=c4[k]}=={'validation.sc_cells','mask.path'}
        and c2['validation.sc_cells']=='2'and c4['validation.sc_cells']=='4'and c2['mask.sha256']==c4['mask.sha256'],
        'Only actual SC cell count and byte-identical mask path alias may change')
    old,new=np.asarray(sc2['z_faces_mm']),np.asarray(sc4['z_faces_mm'])
    require(np.allclose(old[:3],[0,.05,.1],rtol=0,atol=1e-12)
        and np.allclose(new[:5],[0,.025,.05,.075,.1],rtol=0,atol=1e-12)
        and np.allclose(old[2:],new[4:],rtol=0,atol=1e-12),'SC faces refine only; all bulk faces must remain fixed')
    return dict(SC2_cells=351680,SC4_cells=361728,SC2_layers=2,SC4_layers=4,
        physical_mask_identical=True,allowed_config_differences=['mask.path','validation.sc_cells'],full_convergence_validated=False)


def _sc4_base(refs,rounded_base):
    """Explicit genuine SC4 metadata adapter, independent of frozen SC2 _case guard."""
    run=ROOT/'data-native'/SC4_RUN;summary_path=run/'postprocess'/SC4_ID/'summary.json'
    summary=_json(summary_path,refs);pre=_json(run/'preregistration.json',refs);receipt=_json(run/'cases'/(SC4_ID+'.json'),refs)
    require(pre.get('batch_kind')=='one_rounded_SC_only_sensitivity_basis'and pre['gates']==core.GATES and len(pre['cases'])==1,
        'Actual completed one-basis SC4 registration required')
    case=pre['cases'][0];meta=summary['mesh_metadata'];m2=rounded_base['metadata']
    require(case['id']==SC4_ID and case.get('SC_only_sensitivity')is True and summary['id']==receipt['id']==SC4_ID
        and summary['status']==receipt['status']=='complete'and receipt['postprocess_sha256']==refs[str(summary_path)]
        and receipt['postprocess_path']==str(summary_path)and receipt['config_sha256']==case['config_sha256']==meta['config_sha256'],
        'Exact controller-completed genuine SC4 receipt/config required')
    config_path=Path(case['config_file']);mask_path=Path(case['mask_file'])
    native._pin(config_path,refs,ROOT,case['config_sha256']);native._pin(mask_path,refs,ROOT,case['mask_sha256'])
    rcase=rounded_base['registered_case'];mask2=Path(rcase['mask_file'])
    require(case['mask_sha256']==rcase['mask_sha256']and mask_path.read_bytes()==mask2.read_bytes()
        and case['design']==rcase['design']and case['circuit']==rcase['circuit']and case['circuit']['n_outputs']==2,
        'SC4 must retain exact physical rounded mask bytes/design/circuit')
    identity=validate_mesh_identity(m2,meta,native._properties(Path(rcase['config_file'])),native._properties(config_path))
    require(meta['exporter_class']==m2['exporter_class']and meta['exporter_kind']==m2['exporter_kind'], 'Honest unchanged native producer required')
    item=view.load_case(summary_path);refs.update(native_refs_for_item(item))
    require(item['full_skin']and all(type(receipt['validation'].get(k))in(int,float)and math.isfinite(receipt['validation'][k])
        and 0<=receipt['validation'][k]<=limit for k,limit in core.GATES.items()),'SC4 native five gates and source-bound full-skin audit required')
    manifest_path=run/'frozen-source-manifest.json';manifest=_json(manifest_path,refs)
    require(manifest['source_commit']==pre['source_commit']and manifest['files'],'SC4 frozen producer manifest required')
    for original,row in manifest['files'].items():
        p=Path(row['path']);p=p if p.is_absolute()else ROOT/p
        require(p.is_relative_to(run/'frozen-source')and pre['source_and_input_sha256'].get(original)==row['sha256'],
            'SC4 frozen source pin mismatch');native._pin(p,refs,ROOT,row['sha256'])
    expected=summary['input_sha256']
    for name,digest in expected.items():
        p=native._regular(Path(name),ROOT)
        if p.name in ('mesh-metadata.json','validation.json','BASIS_COMPLETE'):native._pin(p,refs,ROOT,digest)
    files=bounds._selected_files(dict(native_expected_input_sha256=expected,basis_folder=str(run/'bases'/SC4_ID),
        volume_npz=str(summary_path.parent/'volume.npz'),volume_npz_sha256=summary['artifacts']['files']['volume.npz']['SHA256']),refs)
    require(_json(files['metadata']['path'],refs,files['metadata']['SHA256'])==meta,'SC4 native/summary metadata mismatch')
    return dict(case=dict(run_id=SC4_RUN,case_id=SC4_ID,summary=str(summary_path),summary_sha256=refs[str(summary_path)],
        config_sha256=case['config_sha256'],mask_sha256=case['mask_sha256'],source_commit=pre['source_commit'],
        comparison_signature=item['signature'],native_expected_input_sha256=expected),files=files,metadata=meta,
        registered_case=case,physical_geometry=case['design'],physical_geometry_kind='fixed_native_face_union',SC_refinement_identity=identity)


def native_refs_for_item(item):
    refs={str(item['path']):view.sha(item['path']),str(item['run']/'preregistration.json'):view.sha(item['run']/'preregistration.json')}
    for p in item['audit_paths']:refs[str(p)]=view.sha(p)
    probe=item['path'].parent/item['summary']['artifacts']['probes_json']
    native._pin(probe,refs,ROOT,item['summary']['artifacts']['files'][probe.name]['SHA256'])
    require(any(c['id']in item['full_skin']for c in item['conditions']),'Completed source-bound full-skin reference required')
    return refs


def _condition_artifacts(source,ident,refs,expected_schema):
    rows=[r for r in source['conditions']if r['id']==ident];require(len(rows)==1,'Exact completed selected condition required')
    artifacts=rows[0]['artifacts'];condition=_json(artifacts['condition.json']['path'],refs,artifacts['condition.json']['SHA256'])
    require(condition['schema']==expected_schema and condition['status']=='calculated_unadopted'and condition['id']==ident
        and condition['actual_fundamental_Hz']==list(PAIR)and condition['source_geometry_unchanged']is True
        and condition['new_PDE']==0 and condition['candidate_adopted']is False,'Completed unchanged native coefficient/field condition required')
    archive=artifacts['volume.npz'];native._regular(Path(archive['path']),ROOT);refs[archive['path']]=archive['SHA256']
    metrics=_json(artifacts['native-volume-metrics.json']['path'],refs,artifacts['native-volume-metrics.json']['SHA256'])
    require(metrics==condition['native_volume_metrics']and metrics['total_sampled_directions']==2074,'Exact completed2074 scalar/statistics source binding required')
    return condition,archive,artifacts['condition.json']


def source_bundle(refs):
    control=_json(CONTROL_VOLUME,refs);opt=_json(OPT_SUMMARY,refs);sc4_summary=_json(SC4_SUMMARY,refs)
    require(control['schema']=='task1-volume-selectivity-v1'and control['status']=='calculated_unadopted'and control['inputs_unchanged']is True
        and control['new_PDE_solves']==0,'Completed original/rounded square volume controls required')
    for obj,schema in ((opt,'task1-rounded-drive-optimization-v1'),(sc4_summary,'task1-rounded-sc4-sensitivity-v1')):
        require(obj['schema']==schema and obj['status']=='calculated_unadopted'and obj['inputs_unchanged']is True
            and obj['new_PDE']==0 and obj['candidate_adopted']is False,'Completed unchanged rounded drive/sensitivity evidence required')
    bases={};cases=[];a1=3/(2*math.sqrt(2))
    for run,ident in ((BASE_RUN,BASE_ID),(ROUND_RUN,ROUND_ID)):
        item,pre=native._case(ROOT,run,ident,refs);probes._validate_probe40(item,refs,ROOT)
        require(pre['gates']==core.GATES,'Original five numerical equation gates unchanged')
        case=next(c for c in pre['cases']if c['id']==ident);summary=_json(item['summary'],refs,item['summary_sha256']);meta=summary['mesh_metadata']
        require(meta['source_peak_V']==.5 and meta['source_resistance_ohm']==50 and meta['phasor_convention']=='peak,+jomega_t'
            and meta['field_reconstruction']=='half_face_flux; top contact term averaged over full cell face h^2', 'Exact frozen native E convention required')
        base=dict(case=item,files=bounds._selected_files(item,refs),metadata=meta,registered_case=case,
            physical_geometry=case['design'],physical_geometry_kind=case.get('geometry_kind','four_square'));bases[ident]=base
        rows=[r for r in control['cases']if r['summary_path']==item['summary']]
        require(len(rows)==1 and control['inputs_sha256'].get(item['summary'])==item['summary_sha256'],'Square control summary/volume source binding differs')
        saved=next(c for c in summary['conditions']if c['waveform']=='square_3h')
        cases.append(dict(id=saved['id'],cohort='original_SC2_square'if ident==BASE_ID else'rounded_SC2_square',basis_id=ident,
            coefficients={'3000':dict(real=[0.,0.],imaginary=[-a1,0.]),'3030':dict(real=[0.,0.],imaginary=[0.,-a1])},
            volume_file=base['files']['volume'],normalizations=copy.deepcopy(rows[0]['normalizations']),
            saved_raw_XYZ_primary_statistics=copy.deepcopy(saved['volume_metrics']['regions']['target']['statistics']),
            old_screen_source=dict(path=str(CONTROL_VOLUME),SHA256=refs[str(CONTROL_VOLUME)],old_screens_replaced=False)))
    require(bases[BASE_ID]['case']['comparison_signature']==bases[ROUND_ID]['case']['comparison_signature'],
        'Original and rounded SC2 share the exact grid/material/contact/ROI contract')
    proof_path=ROOT/'data-native'/ROUND_RUN/'geometry-audit/rounded-mask-proof.json'
    proof=_json(proof_path,refs)
    require(proof.get('physical_geometry_frozen')is True and proof.get('future_grid_reranking_allowed')is False,
        'Frozen physical rounded staircase contour proof required')
    selected,archive,artifact=_condition_artifacts(opt,SELECTED_ID,refs,'task1-rounded-drive-optimization-condition-v1')
    sc4_id=SELECTED_ID+'-SC4-same-command'
    selected4,archive4,artifact4=_condition_artifacts(sc4_summary,sc4_id,refs,'task1-rounded-sc4-sensitivity-condition-v1')
    fixed=validate_fixed_modes(selected,selected4);coefficients=decode_coefficients(selected);decode_coefficients(selected4)
    for c,run,ident in ((selected,ROUND_RUN,ROUND_ID),(selected4,SC4_RUN,SC4_ID)):
        require(c['source_run_id']==run and c['source_case_id']==ident,'Actual selected source basis identity differs')
    bases[SC4_ID]=_sc4_base(refs,bases[ROUND_ID])
    require(selected['configuration_sha256']==bases[ROUND_ID]['metadata']['config_sha256']and
        selected4['configuration_sha256']==bases[SC4_ID]['metadata']['config_sha256'],'Selected condition/native config identity differs')
    command=_json(ROOT/'data-native'/SC4_RUN/'preregistration.json',refs)['selected_SC2_command']
    require(command['condition_id']==SELECTED_ID and command['raw_coefficient_vectors']==selected['coefficient_vectors']
        and command['raw_source_Vpp_intervals_V']==selected['source_waveform']['source_Vpp_intervals_V']
        and command['SC2_original_cutoffs_V_m']==selected['shared_original_square_cutoffs_V_m']==selected4['shared_original_square_cutoffs_V_m'],
        'Native SC4 registration must bind actual selected SC2 coefficients, whole Vpp and original cutoffs')
    for c,archive,artifact,ident,cohort,modes in ((selected,archive,artifact,ROUND_ID,'rounded_SC2_selected',selected['normalizations']),
            (selected4,archive4,artifact4,SC4_ID,'rounded_SC4_selected_same_command',fixed)):
        cases.append(dict(id=c['id'],cohort=cohort,basis_id=ident,coefficients=copy.deepcopy(coefficients),volume_file=archive,
            normalizations=copy.deepcopy(modes),source_waveform=copy.deepcopy(c['source_waveform']),
            saved_raw_XYZ_primary_statistics=copy.deepcopy(c['native_volume_metrics']['regions']['target']['statistics']),
            old_screen_source=dict(**artifact,old_screen=copy.deepcopy(c.get('canonical_skin_cap_screen',c.get('primary_fixed_SC2_skin8_screen'))),old_screens_replaced=False)))
    require(len(cases)==4 and len(bases)==3 and all(set(c['normalizations'])==set(screen.MODES)for c in cases),'Four exact cohorts and five saved amplitudes required')
    return dict(cases=cases,bases=bases,source_summaries=[dict(path=str(p),SHA256=refs[str(p)])for p in SOURCE_SUMMARIES],
        physical_rounded_geometry_proof=dict(path=str(proof_path),SHA256=refs[str(proof_path)]),
        fixed_SC2_cutoffs=selected['shared_original_square_cutoffs_V_m'],SC4_supplemental_rematches_included=False)


def selection_context(decision_path,feedback_path,refs):
    decision=_json(decision_path,refs);feedback=_json(feedback_path,refs)
    require(decision.get('schema')=='task1-rounded-direction-bounds-root-decision-v1'and decision.get('status')=='selected_not_executed'
        and decision.get('root_selected')is True and decision.get('peer_endorsed')is False and decision.get('new_PDE')==0
        and decision.get('candidate_adopted')is False and isinstance(decision.get('question'),str)and decision['question'].strip(),
        'Root-selected unexecuted four-cohort direction diagnostic required')
    require(decision.get('source_summary')==dict(path=str(SC4_SUMMARY),SHA256=native.sha(SC4_SUMMARY))
        and decision.get('feedback')==dict(path=str(feedback_path),SHA256=refs[str(feedback_path)]),'Exact actual sensitivity/feedback decision bindings required')
    require(feedback.get('schema')=='task1-queue-feedback-v1'and feedback.get('status')=='read_only_feedback_checked'
        and feedback.get('error')is None and feedback.get('public_GitHub_only')is True and feedback.get('messages_sent')==0
        and feedback.get('new_PDE')==0,'Actual read-only public GitHub feedback receipt required')
    def contains(obj):
        if isinstance(obj,dict):return (obj.get('id')==6324462120 and obj.get('body_sha256')=='42edf78969362113168d1236acacd02b8fdf0789d56d16093456996c08cdc532')or any(contains(v)for v in obj.values())
        return isinstance(obj,list)and any(contains(v)for v in obj)
    require(contains(feedback),'Feedback6324462120 actual body/hash must be present, not inferred endorsement')
    for p,digest in decision.get('input_sha256',{}).items():_json(p,refs,digest)
    return dict(decision=dict(path=str(decision_path),SHA256=refs[str(decision_path)]),
        feedback=dict(path=str(feedback_path),SHA256=refs[str(feedback_path)]),peer_endorsed=False,feedback_id='6324462120')


def make_preregistration(output,decision_path,feedback_path):
    refs={};context=selection_context(decision_path,feedback_path,refs);bundle=source_bundle(refs);implementation=implementation_receipt()
    refs.update(implementation['implementation_files_sha256']);ledger=policy.load_ledger();refs.update(policy.policy_refs(ledger))
    return dict(schema=SCHEMA,status='preregistered_not_executed',created_utc=core.now(),output_directory=str(output),sources=bundle,
        case_order=[c['id']for c in bundle['cases']],lambdas=list(bounds.LAMBDAS),input_sha256=refs,root_selection=context,
        numerical_contract=dict(PSD_upper_helper=dict(path=str(Path(bounds.__file__).resolve()),SHA256=native.sha(bounds.__file__)),
            upper='2sqrt(min over nine fixed lambda eigmax(lambda*A3000+(1-lambda)*A3030)); outward guard retained',
            lower='Existing saved2074 sampled-direction maxTIS; no resampling, unchanged',
            actual_XYZ='2min(abs(E3000.axis),abs(E3030.axis)); separate native archive, not an upper-bound surrogate',
            actual_coherent_coefficients=True,source_renormalization=False,source_whole_Vpp_preserved=True,
            mode_reference='All five historical SC2 amplitudes; SC4 fixed modes only, without supplemental rematches',
            cutoffs='OriginalSC2square2074 raw maxTIS primary/slab mean/P10 fixed; neither rounded nor upper-bound cutoffs',
            robust_screen='Eight conditional interval comparisons using opposite interval ends and frozen gate arithmetic; old screens unchanged',
            conditional_discrete_model_only=True,formal_IEEE_or_solver_certificate=False),
        resources=dict(CPU_count=1,total_seconds=600,per_condition_seconds=120,source_load_seconds=60,RSS_bytes=3*GIB,
            minimum_free_disk_bytes=2*GIB,max_added_bytes=2*GIB,cumulative_seconds=policy.effective_limit(ledger)),
        new_PDE=0,phi_or_harmonic_field_reads=False,new_probes=False,old_screens_replaced=False,**implementation)


def verify_plan(path,output,expected=None,*,hash_arrays):
    p=native._regular(Path(path),ROOT);digest=native.sha(p);plan=native.read(p)
    require(expected is None or digest==expected,'Rounded bounds preregistration changed')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['output_directory']==str(output)
        and plan['lambdas']==list(bounds.LAMBDAS)and len(plan['case_order'])==4 and plan['new_PDE']==0
        and plan['resources']['per_condition_seconds']==120 and plan['old_screens_replaced']is False,'Exact four-cohort finite bound registration required')
    for name,digest_expected in plan['input_sha256'].items():
        f=native._regular(Path(name),ROOT)
        if hash_arrays or f.suffix not in ('.npz','.gz','.bin'):require(native.sha(f)==digest_expected,'Preregistered bound input changed: '+name)
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'],'Frozen rounded-bound source changed')
    context=plan['root_selection'];require(selection_context(Path(context['decision']['path']),Path(context['feedback']['path']),{})==context,'Root decision/actual feedback changed')
    require(json.loads(json.dumps(source_bundle({})))==plan['sources'],'Completed condition coefficients/amplitudes/native provenance changed')
    return plan,native.sha(p)


def _load_base(base):
    files=base['files'];p=Path(files['grid']['path']);opener=gzip.open if p.suffix=='.gz'else open
    with opener(p,'rt')as stream:grid=np.atleast_1d(np.genfromtxt(stream,delimiter=',',names=True))
    meta=base['metadata'];expected=351680 if meta['sc_cells']==2 else 361728
    require(meta['sc_cells']in(2,4)and len(grid)==meta['cells']==expected and
        grid.dtype.names==('x_mm','y_mm','z_mm','layer','volume_m3')and all(np.isfinite(grid[k]).all()for k in grid.dtype.names),
        'Actual source-specific SC2/SC4 native grid dimensions/schema required')
    return dict(grid=grid,metadata=meta,field={f:bounds._array(files[str(f)]['path'],(2,len(grid),3))for f in PAIR})


def _load_scalars(case,base):
    with zipfile.ZipFile(case['volume_file']['path'])as z:require(sum(e.file_size for e in z.infolist())<=GIB,'Bounded native scalar archive required')
    arrays,regions=bounds._load_scalars(case,base)
    expected=set(volume.METRICS)|{'maxTIS_direction_index'}|{'region_'+k+'_m3'for k in ('total','target','surface_0_5','subsurface_5_10','remaining','off_target')}
    require(set(arrays)==expected,'Exact completed scalar archive ABI required')
    return arrays,regions


def compose_fundamentals(fields,coefficient_vectors):
    spectra={}
    for f in PAIR:
        row=coefficient_vectors[str(f)];coeff=np.asarray(row['real'],float)+1j*np.asarray(row['imaginary'],float)
        field=np.asarray(fields[f])
        require(coeff.shape==(2,)and np.isfinite(coeff).all()and field.ndim==3 and field.shape[0]==2
            and field.shape[2]==3 and np.iscomplexobj(field)and np.isfinite(field).all(),'Actual complex two-output native fields/coefficient vectors required')
        spectra[f]=np.einsum('c,cnk->nk',coeff,field)
    return spectra


def conditional_eight_screen(candidate,baseline):
    """Independent direction intervals for all eight unchanged electrical gates."""
    checks=[]
    for definition in screen.GATE_DEFINITIONS:
        name=definition['name'];direction=definition['required_direction'];unit=definition['unit']
        if name.startswith('primary_maxTIS_'):
            region=volume.PRIMARY;stat=name.removeprefix('primary_maxTIS_');cutoff=None
        else:
            region='surface_0_5'if name.startswith('surface_0_5')else'primary_complement'
            cutoff=name.split('_high_volume_at_',1)[1]if '_high_volume_at_'in name else None;stat='p95'if cutoff is None else None
        def interval(mode):
            data=mode['regions'][region]
            if cutoff is not None:
                v=data['continuous_direction_fixed_cutoff_volume_intervals'][cutoff];return v['lower_volume_m3'],v['upper_volume_m3']
            return data['old2074_maxTIS_LB'][stat],data['continuous_direction_UB'][stat]
        low,high=interval(candidate);blow,bhigh=interval(baseline)
        failure=bounds.robust_failure(low,high,blow,bhigh,direction=direction,unit=unit)
        eps=screen.tolerance(blow if direction=='greater'else bhigh,unit)
        guard=(1e-18 if unit=='m3'else 1e-12)+1e-10*max(low,high,blow,bhigh)
        passed=low-guard>=bhigh+eps if direction=='greater'else high+guard<=blow-eps
        result='conditional_direction_robust_pass'if passed else failure['status']
        checks.append(dict(definition,**{k:v for k,v in failure.items()if k not in ('required_direction','unit','status')},
            status=result,region=region,statistic=stat,fixed_original_cutoff_name=cutoff,
            signed_guaranteed_pass_margin=(low-bhigh if direction=='greater'else blow-high),
            old_screen_replaced=False,conditional_native_field_model_only=True))
    return dict(checks=checks,any_conditional_direction_robust_failure=any(c['status']=='conditional_direction_robust_failure'for c in checks),
        all_conditional_direction_robust_pass=all(c['status']=='conditional_direction_robust_pass'for c in checks),
        inconclusive_count=sum(c['status']=='inconclusive'for c in checks),old_screen_replaced=False)


def execute(plan,output,deadline,checkpoint):
    loaded={};start=time.monotonic()
    for ident,base in plan['sources']['bases'].items():
        loaded[ident]=_load_base(base);bounds._deadline(min(deadline,start+60));checkpoint('native_fundamentals_loaded',basis_id=ident)
    require(np.array_equal(loaded[BASE_ID]['grid'],loaded[ROUND_ID]['grid']),'Original/rounded SC2 native grid order must match exactly')
    results=[];baseline=None;cutoffs=None
    for case in plan['sources']['cases']:
        per=min(deadline,time.monotonic()+120);signal.setitimer(signal.ITIMER_REAL,max(.001,per-time.monotonic()))
        checkpoint('condition_start',condition_id=case['id']);base=loaded[case['basis_id']];arrays,regions=_load_scalars(case,base);lb=arrays['maxTIS']
        if cutoffs is None:
            cutoffs={r+'_'+s:volume.weighted_statistics(lb,regions[r])[s]for r in(volume.PRIMARY,volume.SLAB)for s in('mean','p10')}
            require(cutoffs==plan['sources']['fixed_SC2_cutoffs']['maxTIS'],'Saved original SC2 scalar cutoffs must reproduce exactly')
        spectra=compose_fundamentals(base['field'],case['coefficients'])
        fields=bounds.field_bounds(spectra[3000],spectra[3030],deadline=per)
        validation=bounds.validate_lower_bound(lb,fields['continuous_direction_UB_V_m'])
        validation['upper_enlarged_to_unchanged_saved_LB_cells']=int(np.count_nonzero(lb>fields['continuous_direction_UB_V_m']))
        fields['continuous_direction_UB_eigen_guard_only_V_m']=fields['continuous_direction_UB_V_m'].copy()
        fields['continuous_direction_UB_V_m']=np.maximum(fields['continuous_direction_UB_V_m'],lb)
        validation['XYZ_primary_mean_P10_regression']={}
        for name in ('X_TIS','Y_TIS','Z_TIS'):
            require(np.all(fields[name]<=lb+1e-12+1e-10*lb),'Saved2074 directions must include actual XYZ axes')
            actual=volume.weighted_statistics(fields[name],regions[volume.PRIMARY]);saved=case['saved_raw_XYZ_primary_statistics'][name]
            require(all(math.isclose(actual[k],saved[k],rel_tol=1e-12,abs_tol=1e-14)for k in ('mean','p10')),'Source-bound XYZ mean/P10 differs: '+name)
            validation['XYZ_primary_mean_P10_regression'][name]=dict(passed=True,actual={k:actual[k]for k in ('mean','p10')},saved={k:saved[k]for k in ('mean','p10')})
        folder=output/case['id'];folder.mkdir();modes={}
        np.savez_compressed(folder/'direction-bounds.npz',**{k:v for k,v in fields.items()if k not in ('X_TIS','Y_TIS','Z_TIS')},old2074_maxTIS_LB=lb)
        np.savez_compressed(folder/'directional-XYZ.npz',**{k:fields[k]for k in ('X_TIS','Y_TIS','Z_TIS')})
        for name,saved in case['normalizations'].items():
            scale=saved['amplitude_scale'];actual=volume.weighted_statistics(lb*scale,regions[volume.PRIMARY]);expected=saved['regions'][volume.PRIMARY]['maxTIS']
            require(all(math.isclose(actual[k],expected[k],rel_tol=1e-12,abs_tol=1e-14)for k in ('mean','p10')),'Saved2074 lower-bound amplitude/statistics regression differs')
            mode=copy.deepcopy({k:v for k,v in saved.items()if k not in ('regions','probe40_unloaded')})
            mode['regions']=bounds._summaries(fields,lb,regions,base['grid'],scale,cutoffs)
            mode.update(normalization_recomputed=False,actual_SC4_equal_burden_claimed=False if case['basis_id']==SC4_ID else None)
            modes[name]=mode;bounds._deadline(per)
        robust={name:conditional_eight_screen(mode,baseline['normalizations'][name])for name,mode in modes.items()}if baseline else{}
        result=dict(id=case['id'],cohort=case['cohort'],basis_id=case['basis_id'],status='calculated_supplemental_unadopted',normalizations=modes,
            lower_upper_validation=validation,direction_robust_eight_gate_comparisons=robust,source=case,
            native_basis_provenance=dict(source_commit=plan['sources']['bases'][case['basis_id']]['case']['source_commit'],
                configuration_sha256=base['metadata']['config_sha256'],mask_sha256=plan['sources']['bases'][case['basis_id']]['case']['mask_sha256'],
                native_grid=plan['sources']['bases'][case['basis_id']]['files']['grid'],SC_cells=base['metadata']['sc_cells'],
                native_cells=base['metadata']['cells'],physical_geometry=plan['sources']['bases'][case['basis_id']]['physical_geometry']),
            archives={name:dict(path=str(folder/name),SHA256=native.sha(folder/name))for name in ('direction-bounds.npz','directional-XYZ.npz')},
            represented_ROI_volumes_m3={r:float(w.sum())for r,w in regions.items()},fixed_original_SC2_cutoffs_V_m=cutoffs,
            old_screens_replaced=False,new_PDE=0,new_probes=False,SC4_supplemental_rematch_included=False)
        core.write(folder/'summary.json',result);results.append(result)
        if baseline is None:baseline=result
        checkpoint('condition_complete',condition_id=case['id'])
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    sc2=next(r for r in results if r['cohort']=='rounded_SC2_selected');sc4=next(r for r in results if r['cohort']=='rounded_SC4_selected_same_command')
    roi_identity=[]
    for name,old in sc2['represented_ROI_volumes_m3'].items():
        new=sc4['represented_ROI_volumes_m3'][name]
        require(math.isclose(old,new,rel_tol=1e-10,abs_tol=1e-15),'SC refinement changed represented physical ROI volume')
        roi_identity.append(dict(region=name,SC2_volume_m3=old,SC4_volume_m3=new,SC4_minus_SC2_m3=new-old))
    return dict(schema=RESULT_SCHEMA,status='calculated_supplemental_unadopted',conditions=results,numerical_contract=plan['numerical_contract'],
        new_PDE=0,old_screens_replaced=False,new_probes=False,phi_or_harmonic_field_reads=False,
        source_renormalization=False,normalization_changed=False,SC4_supplemental_rematches_included=False,
        candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,global_impossibility_claimed=False,
        root_selection=plan['root_selection'],input_sha256=plan['input_sha256'],
        SC2_SC4_physical_ROI_volume_identity=dict(passed=True,SC2_native_cells=351680,SC4_native_cells=361728,
            distinct_native_grid_identity_preserved=True,regions=roi_identity,relative_tolerance=1e-10,absolute_tolerance_m3=1e-15),
        holds=['Bounds condition on the fixed native fields, materials, interface and source commands; not solver/mesh error bounds',
            'SC4 retains historical SC2 amplitudes, so current/power or burden equality on SC4 is not asserted',
            'Rounded outline is the frozen70mm staircase, not a smooth circle or isolated edge-convergence experiment',
            'No biological threshold, safety limit, activation or global physical impossibility inferred'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',type=Path);group.add_argument('--preregistration',type=Path)
    parser.add_argument('--decision',type=Path);parser.add_argument('--feedback',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output
    require(output.is_absolute()and output==output.resolve()and output.is_relative_to(ROOT/'docs')and output.parent.is_dir()and not output.exists(),'New canonical docs output required')
    with (ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledgerpath=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledgerpath);cap=60 if args.prepare else 600
        require(policy.remaining_seconds(ledger)>=cap and shutil.disk_usage(output.parent).free>=2*GIB+256*1024**2,'Existing finite budget/disk admission failed')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();deadline=start+cap
        status='failed_preserved';failure=None;state={};stop=threading.Event();mutex=threading.RLock();thread=None;counter=0
        def guard():
            require(core.rss(os.getpid())<3*GIB and shutil.disk_usage(output.parent).free>=2*GIB,'RSS3GiB/disk2GiB reserve exceeded')
            if output.exists():require(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=2*GIB,'Added artifacts exceed2GiB')
        def checkpoint(phase,**extra):
            nonlocal counter
            with mutex:
                guard();counter+=1;state.update(phase=phase,status=status if phase=='complete'else'running',pid=os.getpid(),
                    proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now(),elapsed_seconds=time.monotonic()-start,**extra)
                core.write(output/f'checkpoint-{counter:03d}-{phase}.json',dict(state));core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5):
                try:
                    with mutex:guard();core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-start))
                except BaseException as error:state['resource_guard_failure']=str(error);os.kill(os.getpid(),signal.SIGTERM);return
        def interrupted(sig,frame):raise TimeoutError('Finite rounded direction-bounds stop '+str(sig))
        previous={sig:signal.getsignal(sig)for sig in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for sig in previous:signal.signal(sig,interrupted)
        signal.setitimer(signal.ITIMER_REAL,cap)
        try:
            if args.prepare:
                require(args.prepare.is_absolute()and args.prepare==args.prepare.resolve()and args.prepare.is_relative_to(ROOT/'docs')and not args.prepare.exists()
                    and not args.prepare.with_name(args.prepare.name+'.failure.json').exists()and not args.prepare.is_relative_to(output),'New external preregistration path required')
                plan=make_preregistration(output,args.decision,args.feedback)
                with args.prepare.open('x')as stream:json.dump(plan,stream,indent=2,allow_nan=False);stream.write('\n')
                status='preregistered_not_executed'
            else:
                require(args.decision is None and args.feedback is None,'Root context frozen before execution')
                output.mkdir();thread=threading.Thread(target=heartbeat,daemon=True);thread.start();checkpoint('verify_inputs')
                plan,digest=verify_plan(args.preregistration,output,hash_arrays=True)
                result=execute(plan,output,deadline,checkpoint);verify_plan(args.preregistration,output,digest,hash_arrays=True);guard()
                result.update(implementation_receipt(),preregistration=dict(path=str(args.preregistration),SHA256=digest),inputs_unchanged=True,
                    resources=dict(CPU_count=1,max_seconds=600,max_condition_seconds=120,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                        wall_seconds=time.monotonic()-start,cumulative_limit_seconds=policy.effective_limit(ledger)))
                core.write(output/'summary.json',result);status=result['status'];checkpoint('complete')
        except BaseException as error:
            failure=type(error).__name__+': '+str(error)
            dest=output/'failure.json'if output.exists()else args.prepare.with_name(args.prepare.name+'.failure.json')if args.prepare else None
            if dest is not None and not dest.exists():core.write(dest,dict(status=status,error=failure,phase=state.get('phase'),condition_id=state.get('condition_id'),
                partial_artifacts_preserved=True,automatic_retry=False,new_PDE=0))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-start;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='rounded_direction_bounds_prepare'if args.prepare else'rounded_direction_bounds_audit',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()));core.write(ledgerpath,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for sig,handler in previous.items():signal.signal(sig,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
