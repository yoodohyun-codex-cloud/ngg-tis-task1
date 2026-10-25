"""Two finite complex-contact sensitivity bases on immutable rounded SC4 pads.

No work on import. Scale the already once-converted nominal PBS specific Z by
0.5/2, both real and imaginary parts. Do not subtract Rs or normalize area again.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import task1_rounded_sc4_registration as sc4
rounded=sc4.rounded
parent=sc4.parent
core=sc4.core
policy=sc4.policy
_caller_owns_execution_lock=sc4._caller_owns_execution_lock
_mesh=sc4._mesh
_properties=sc4._properties
_changed_config=sc4._changed_config
bounded_command=sc4.bounded_command
SOURCE_RUN='cloud-rounded-sc4-20261021T204000Z'
SOURCE_ID='rounded-fullface225-sc4-xy80'
CASE_IDS=('rounded-fullface225-contact0p5-sc4-xy80','rounded-fullface225-contact2-sc4-xy80')
FACTORS=(.5,2.)
EXPECTED_CELLS=361728
EXPECTED_RAW_BOUND_BYTES=434073600
MIN_REMAINING_SECONDS=1800
PREPARATION_SECONDS=120
FREQUENCIES=(3000,3030,9000,9090)
MODES=('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin')


def changed_contact_config(data,mask_path,scale):
    core.require(type(scale)in(int,float)and scale in FACTORS,'Only registered complex-Z scales0.5/2 allowed')
    source=_properties(data)
    core.require(source.get('h_mm')=='0.625'and source.get('validation.sc_cells')=='4'and source.get('bulk.counts')=='14,14,40'and
        source.get('channels')=='2'and source.get('frequencies')=='3000,3030,9000,9090','Exact two-output rounded SC4 grid/four-frequency basis required')
    changes={'mask.path':str(mask_path)}
    for f in FREQUENCIES:
        real=float(source[f'z.{f}.re']);imag=float(source[f'z.{f}.im'])
        core.require(math.isfinite(real)and real>0 and math.isfinite(imag),'Finite passive nominal specific complex Z required')
        for suffix,value in (('re',real),('im',imag)):
            scaled=value*scale;core.require(math.isfinite(scaled),'Scaled specificZ overflow')
            changes[f'z.{f}.{suffix}']=format(scaled,'.17g')
    return _changed_config(data,changes),changes


def validate_nominal_source(source,maskbytes):
    core.require(source.get('id')==SOURCE_ID and source.get('h_xy_mm')==.625 and source.get('sc_cells')==4 and
        source.get('bulk_counts')==[14,14,40]and source.get('channels')==2 and source.get('cells')==EXPECTED_CELLS,
        'Exact completed nominal rounded SC4 source required')
    geometry_keys=('geometry_kind','geometry_revision','native_full_face_contact','physical_total_contact_area_mm2','minimum_physical_gap_mm',
        'minimum_gap_XY_cells','maximum_physical_vertex_radius_squared_mm2','rim_clearance_mm','physical_geometry_frozen','future_grid_reranking_allowed')
    for record in (source,source['design']):
        core.require(all(record.get(k)==rounded.COMMON[k]for k in geometry_keys),'Frozen physical rounded geometry changed')
    circuit=source['circuit'];core.require(circuit.get('n_pads')==4 and circuit.get('n_outputs')==2 and circuit.get('n_return_nodes')==1 and
        circuit.get('source_resistance_ohm')==50 and circuit.get('source_peak_V')==.5 and
        circuit.get('pad_to_node')=={'0':'out0','1':'out1','2':'GND','3':'GND'},'Same four-pad/two-output commonGND50ohm source required')
    areas=source.get('expected_pad_areas_m2',[]);core.require(len(areas)==4 and all(math.isclose(a,.000225,rel_tol=1e-12,abs_tol=1e-16)for a in areas),
        'Physical225mm2 per pad/900total required')
    rows=[]
    for p,(pad,faces,centre)in enumerate(zip(source['design']['pads'],rounded.rounded_faces(),rounded.CENTRES)):
        core.require(pad.get('pad')==p and pad.get('shape')=='masked_face_union'and pad.get('center_mm')==list(centre)and
            pad.get('width_mm')==pad.get('height_mm')==17.5 and pad.get('rotation_deg')==0 and pad.get('analytic_area_mm2')==225 and
            pad.get('role')==('signal'if p<2 else'common_gnd_return')and pad.get('source_output')==(p if p<2 else None)and
            pad.get('native_face_indices')==[list(v)for v in faces]and pad.get('polygon_mm')==parent.boundary_loop(faces)and
            pad.get('boundary_loops_mm')==[pad['polygon_mm']],'Actual fixed rounded physical outline/role/area differs')
        rows.extend((p,i,j,(.625/1000)**2)for i,j in faces)
    digest=hashlib.sha256(maskbytes).hexdigest()
    core.require(digest==source['mask_sha256']and maskbytes==rounded._mask_bytes(rows),'Exact nominal mask bytes required; no partial patch or area renormalization')
    return dict(physical_geometry_unchanged=True,mask_byte_SHA256=digest,physical_total_contact_area_mm2=900.,
        source_and_new_SC_cells=4,physical_SC_thickness_mm=.1,XY_bulk_material_circuit_unchanged=True,
        additional_Rs_subtractions=0,additional_area_normalizations=0)


def nominal_source(pins):
    run=core.REPO/'data-native'/SOURCE_RUN
    def load(path):pins[str(path)]=core.sha(path);return core.read(path)
    pp=run/'preregistration.json';pre=load(pp);core.require(pre['status']=='prepared','Nominal SC4 registration missing')
    cases=[c for c in pre['cases']if c['id']==SOURCE_ID];core.require(len(cases)==1,'One exact nominal SC4 case required');case=copy.deepcopy(cases[0])
    record=load(run/'cases'/(SOURCE_ID+'.json'));sp=Path(record['postprocess_path']);post=load(sp)
    core.require(record.get('status')=='complete'and post.get('status')=='complete'and post['id']==SOURCE_ID and
        record['postprocess_sha256']==pins[str(sp)]and all(record['validation'][k]<=v for k,v in core.GATES.items()),
        'Nominal SC4 must have completed existing five native equation gates')
    for key in ('config','mask'):
        p=Path(case[key+'_file']);core.require(p.is_file()and not p.is_symlink()and p.resolve().is_relative_to(run)and
            core.sha(p)==case[key+'_sha256'],'Nominal config/mask hash/path differs');pins[str(p)]=case[key+'_sha256']
    core.require(record['config_sha256']==case['config_sha256']and case['source_coating_nm']==10 and case['source_Rs_fit_window_Hz']==500,
        'Nominal once-converted10nm PBS Rs500 provenance differs')
    meta=post['mesh_metadata'];core.require(meta['h_xy_mm']==.625 and meta['sc_cells']==4 and meta['cells']==EXPECTED_CELLS and
        meta['bulk_layer_counts']==[14,14,40]and meta['tissue_boundaries_mm']==[0,.1,5.1,10.1,25.1]and
        meta['frequencies_Hz']==list(FREQUENCIES),'Nominal same SC4 physical layers and frequencies required')
    for p,d in post['input_sha256'].items():
        if Path(p).name in('mesh-metadata.json','validation.json'):core.require(core.sha(p)==d,'Nominal small native metadata SHA differs');pins[p]=d
    return case,pre,Path(case['config_file']),Path(case['mask_file']),dict(path=str(pp),SHA256=pins[str(pp)])


def verify_context(decision_path,feedback_path):
    pins={}
    def pin(path,expected=None):
        p=Path(path);core.require(p.is_absolute() and p==p.resolve() and p.is_relative_to(core.REPO) and
            p.is_file() and not p.is_symlink(),'Canonical local metadata context required')
        digest=core.sha(p);core.require(expected is None or digest==expected,'Context SHA differs');pins[str(p)]=digest
        return p,core.read(p)
    dp,decision=pin(decision_path)
    core.require(decision.get('schema')=='task1-rounded-contact-root-decision-v1' and
        decision.get('status')=='selected_not_executed' and decision.get('case_ids')==list(CASE_IDS) and decision.get('contact_complex_scales')==list(FACTORS) and
        decision.get('source_run_id')==SOURCE_RUN and decision.get('source_case_id')==SOURCE_ID and
        isinstance(decision.get('question'),str)and bool(decision['question'].strip()) and
        decision.get('new_PDE')==2 and
        decision.get('new_native_RHS')==16 and decision.get('independent_outputs')==2 and decision.get('physical_pads')==4 and
        decision.get('fixed_total_area_mm2')==900 and decision.get('candidate_adopted')is False and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False,
        'Exact root-selected paired complex-contact sensitivity decision required')
    declared=decision['feedback'];core.require(Path(feedback_path)==Path(declared['path']),'Explicit feedback must match root-decision pin')
    fp,feedback=pin(feedback_path,declared['SHA256'])
    core.require(feedback.get('schema')=='task1-queue-feedback-v1' and feedback.get('status')=='read_only_feedback_checked' and
        feedback.get('error') is None and feedback.get('public_GitHub_only') is True and feedback.get('messages_sent')==0 and
        feedback.get('new_PDE')==0,'Actual read-only public GET feedback receipt required')
    receipts=feedback.get('receipts',[])
    expected={(p,k,f'repos/yoodohyun-codex-cloud/ngg-tis-task1/'+(f'pulls/{p}' if k=='head' else f'issues/{p}/comments'))
        for p in (1,2) for k in ('head','comments')}
    core.require(len(receipts)==4 and {(r.get('pull'),r.get('kind'),r.get('endpoint')) for r in receipts}==expected,
        'Exact publicPR1/PR2 head/comment GET receipts required')
    comments=[]
    import hashlib
    for receipt in receipts:
        if receipt['kind']=='head':
            core.require(re.fullmatch('[0-9a-f]{40}',receipt.get('evidence',{}).get('head_sha','')) is not None,'Public PR head SHA required')
            continue
        for c in receipt['evidence']:
            core.require(isinstance(c.get('body'),str) and hashlib.sha256(c['body'].encode()).hexdigest()==c.get('body_sha256'),
                'Feedback body SHA mismatch')
            if receipt['pull']==2:comments.append({k:c.get(k) for k in ('id','author','html_url','body_sha256')})
    core.require(any(c['id']==6321929825 and c['author']=='yoodohyun-codex-cloud' and
        c['html_url']=='https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6321929825'
        for c in comments),'Signed-output/circuit feedback6321929825 must be present')
    for path,digest in decision.get('input_sha256',{}).items():
        core.require(Path(path).suffix in ('.json','.md'),'Metadata-only decision evidence required');pin(path,digest)
    evidence=decision.get('nominal_SC4_result',{});objects={}
    for key in ('summary','condition'):
        ref=evidence.get(key,{});path=Path(ref.get('path',''))
        core.require(str(path)in decision.get('input_sha256',{})and decision['input_sha256'][str(path)]==ref.get('SHA256'),
            'Completed nominal SC4 result SHA must be an explicit root input')
        _,objects[key]=pin(path,ref['SHA256'])
    summary,condition=objects['summary'],objects['condition']
    core.require(summary.get('schema')=='task1-rounded-sc4-sensitivity-v1'and summary.get('status')=='calculated_unadopted'and
        summary.get('inputs_unchanged')is True and summary.get('new_PDE')==0 and summary.get('candidate_adopted')is False and
        summary.get('SC4_source_case_id')==SOURCE_ID and summary.get('SC4_source_run_id')==SOURCE_RUN and
        summary.get('SC_sensitivity',{}).get('all_passed')is True,
        'Actual completed unchanged SC4 sensitivity required; no full convergence or adoption claim')
    refs=[c for c in summary.get('conditions',[])if c.get('id')==condition.get('id')]
    core.require(len(refs)==1 and refs[0]['artifacts']['condition.json']==evidence['condition']and
        condition.get('schema')=='task1-rounded-sc4-sensitivity-condition-v1'and condition.get('status')=='calculated_unadopted'and
        condition.get('source_case_id')==SOURCE_ID and condition.get('source_run_id')==SOURCE_RUN and
        condition.get('candidate_adopted')is False and condition.get('same_source_coefficients_and_whole_Vpp')is True,
        'Nominal completed same-command SC4 condition binding required')
    command=summary['selected_SC2_command'];modes=condition['fixed_SC2_amplitude_modes']
    core.require(set(modes)==set(MODES)and all(type(modes[k]['amplitude_scale'])in(int,float)and
        math.isfinite(modes[k]['amplitude_scale'])and modes[k]['amplitude_scale']>0 and
        modes[k].get('SC4_skin_caps_rematched')is False for k in MODES)and
        condition['coefficient_vectors']==command['raw_coefficient_vectors']and
        condition['shared_original_square_cutoffs_V_m']==command['SC2_original_cutoffs_V_m']and
        modes['skin_contact_only']['amplitude_scale']==command['SC2_skin8_amplitude_scale'],
        'Exactly frozen source coefficients, five SC2 amplitudes and original SC2 cutoffs required')
    scales={k:modes[k]['amplitude_scale']for k in MODES}
    return dict(path=str(dp),SHA256=pins[str(dp)],question=decision['question'],root_selected=True,peer_endorsed=False,selected_SC2_command=command,nominal_SC4_result=evidence,fixed_SC2_mode_amplitudes=scales,nominal_configuration_sha256=condition['configuration_sha256']),dict(
        path=str(fp),SHA256=pins[str(fp)],observed_utc=feedback['observed_utc'],public_GET_checked=True,
        public_comment_identity_and_body_sha256=comments,root_selected_contact_sensitivity=True,peer_contact_endorsement=False),pins


def prepare_rounded_contact(run,decision_path,feedback_path):
    started=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run==run.resolve() and not run.exists() and
        not run.with_name(run.name+'.preparation-failure.json').exists(),
        'New canonical unique rounded-contact run required; preserve failed run IDs')
    _caller_owns_execution_lock();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    budget_path=core.REPO/'runtime/task1-budget.json';budget=policy.load_ledger(budget_path);limit=policy.effective_limit(budget)
    core.require(limit==13800 and limit-budget['spent_seconds']>=MIN_REMAINING_SECONDS,'Approved13800s policy with1800s finite queue reserve required')
    success=False;registration=None;created=False
    old_handlers={sig:signal.getsignal(sig)for sig in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
    def interrupted(sig,frame):raise RuntimeError('Bounded preparation interrupted by signal '+str(sig))
    for sig in old_handlers:signal.signal(sig,interrupted)
    signal.setitimer(signal.ITIMER_REAL,max(.001,PREPARATION_SECONDS-(time.monotonic()-started)))
    try:
        decision,feedback,pins=verify_context(Path(decision_path).absolute(),Path(feedback_path).absolute())
        pins.update(core.source_pins(budget))
        for p in (Path(__file__).resolve(),core.REPO/'tests/test_task1_rounded_contact_registration.py',Path(sc4.__file__).resolve(),
            Path(rounded.__file__).resolve(),Path(parent.__file__).resolve()):pins[str(p)]=core.sha(p)
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=core.REPO,text=True).strip()
        for name,digest in pins.items():
            p=Path(name);core.require(core.sha(p)==digest,'Pinned source/context changed: '+name)
            if p.suffix in ('.py','.java'):
                core.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(core.REPO))],cwd=core.REPO)==p.read_bytes(),
                    'Commit all consumed implementation sources/tests before preparation: '+name)
        limits=core.effective_limits(budget)
        core.require(EXPECTED_RAW_BOUND_BYTES==2*EXPECTED_CELLS*600<=limits['max_batch_added_bytes'] and
            shutil.disk_usage(run.parent).free>2*core.GIB+EXPECTED_RAW_BOUND_BYTES,'Two raw bases plus2GiB reserve unavailable')
        run.mkdir();created=True
        for d in ('configs','masks','bases','cases','postprocess','logs','classes','geometry-audit'):(run/d).mkdir()
        def guard(phase):
            elapsed=time.monotonic()-started;remaining=min(PREPARATION_SECONDS-elapsed,limit-budget['spent_seconds']-elapsed-1680)
            core.require(remaining>0 and core.rss(os.getpid())<3*core.GIB and shutil.disk_usage(run).free>=2*core.GIB,
                'Preparation120s/RSS/reserve exhausted at '+phase)
            core.write(run/'controller.json',dict(status='preparing',phase=phase,pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),
                updated_utc=core.now(),elapsed_seconds=elapsed));return remaining
        guard('nominal_SC4_integrity');integrity=core.original_integrity()
        source,nominal_pre,old_config,old_mask,nominal_pre_ref=nominal_source(pins)
        source_mask=old_mask.read_bytes();identity=validate_nominal_source(source,source_mask)
        command=decision['selected_SC2_command']
        core.require(command==nominal_pre['selected_SC2_command']and decision['nominal_configuration_sha256']==source['config_sha256'],
            'Completed nominal result must bind exact original SC4 registration/config/selected SC2 command')
        cases=[];mappings=[]
        for ident,factor in zip(CASE_IDS,FACTORS):
            guard('prepare_contact_'+ident)
            mask=run/'masks'/(ident+'.csv');mask.write_bytes(source_mask)
            core.require(core.sha(mask)==source['mask_sha256'],'Contact sensitivity must preserve identical mask bytes/SHA')
            config=run/'configs'/(ident+'.properties');data,changes=changed_contact_config(old_config.read_bytes(),mask,factor);config.write_bytes(data)
            model=dict(kind='once_converted_nominal_PBS_specific_complex_Z_scale',nominal_config_sha256=source['config_sha256'],
                complex_scale=factor,both_real_and_imaginary_scaled=True,additional_Rs_subtractions=0,additional_area_normalizations=0,
                contact_area_rescaled=False,nominal_Rs_fit_window_Hz=500,actual_skin_contact_validated=False)
            case=copy.deepcopy(source)
            case.update(id=ident,source_run_id=run.name,config_file=str(config),config_sha256=core.sha(config),
                mask_file=str(mask),mask_sha256=source['mask_sha256'],contact_impedance_complex_scale=factor,
                contact_only_sensitivity=True,contact_uncertainty_only=True,SC_only_sensitivity=False,SC_discretization_unchanged=True,physical_geometry_unchanged=True,
                contact_model_revision=model,contact_model_revision_sha256=hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                selected_SC2_command=command,fixed_SC2_mode_amplitudes=decision['fixed_SC2_mode_amplitudes'],
                nominal_SC4_source_reference=dict(run_id=SOURCE_RUN,case_id=SOURCE_ID,config_file=str(old_config),config_sha256=source['config_sha256']),
                original_SC2_caps_and_cutoffs_frozen=True,contact_caps_rematched=False,
                status='preregistered_not_executed',candidate_adopted=False,mesh_convergence_validated=False,
                existing_XY_SC_bulk_edge_contact_holds_preserved=True)
            case['SC4_nominal_reference']=copy.deepcopy(case['nominal_SC4_source_reference'])
            if 'SC2_source_reference'in case:case['historical_SC2_geometry_reference']=case.pop('SC2_source_reference')
            if 'cached_original_SC4_reference'in case:case['historical_original_SC4_nominal_reference']=case.pop('cached_original_SC4_reference')
            case.update(_mesh(case));core.require(case['cells']==EXPECTED_CELLS,'361728cell SC4 geometry/mesh changed')
            case['cache_signature']=core.check_cached_operator(case,run);cases.append(case)
            mappings.append(dict(original_config=str(old_config),original_sha256=source['config_sha256'],new_config=str(config),
                new_sha256=core.sha(config),changed_fields=list(changes),contact_impedance_complex_scale=factor,
                electrical_tissue_mesh_geometry_frequency_changed_fields=[],additional_Rs_subtractions=0,additional_area_normalizations=0,
                mask_bytes_unchanged=True,mask_sha256=source['mask_sha256']))
        core.write(run/'geometry-audit/contact-sensitivity-identity.json',identity)
        jdk=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin');javac=shutil.which('javac') or str(jdk/'javac')
        java=str(Path(javac).resolve().parent/'java');core.require(Path(javac).is_file() and Path(java).is_file(),'Matching installed Java compiler/runtime required')
        with (run/'logs/compile-selftest.log').open('x') as log:
            def compile_call(args):bounded_command(args,log,guard)
            compile_call([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(run/'classes'),str(core.SOURCE/'TisSweep.java'),
                str(core.SOURCE/'ExploreBasis.java'),str(core.SOURCE/'SelectivityShapeBasis.java'),str(core.REPO/'tools/java/CloudShapeBasis.java')])
            compile_call([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),'CloudShapeBasis','--selftest'])
        for d in ('configs','masks','classes','geometry-audit'):
            for p in (run/d).iterdir():pins[str(p)]=core.sha(p)
        for p,digest in pins.items():core.require(core.sha(p)==digest,'Pinned rounded-fullface input changed: '+p)
        guard('final_integrity')
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='paired_rounded_SC4_complex_contact_scale',status='prepared',
            created_utc=core.now(),source_commit=commit,package_integrity=integrity,limits=limits,gates=copy.deepcopy(core.GATES),cases=cases,java=java,
            new_PDE_conditions_maximum=2,new_native_RHS_maximum=16,expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,source_and_input_sha256=pins,
            preparation_seconds=time.monotonic()-started,root_selection_decision=decision,source_feedback=feedback,
            nominal_native_registration=nominal_pre_ref,nominal_SC4_result=decision['nominal_SC4_result'],selected_SC2_command=command,
            fixed_SC2_mode_amplitudes=decision['fixed_SC2_mode_amplitudes'],physical_identity=identity,
            resource_policy_immutable_refs=policy.policy_refs(budget),scientific_question=decision['question'],path_mapping=mappings,
            unchanged_controls=[dict(run_id=SOURCE_RUN,case_id=SOURCE_ID,new_PDE=0)],planned_normalizations=[],
            normalization_scope='Basis only. Separate root post fixes actual source coefficients and all five saved SC2 amplitudes/original SC2 caps,cutoffs,I,P; rematched views must be separate',
            comparison_waveforms=['square_3h','sine','triangle_3h'],fixed_ROIs='r<=5mm depth15..20 pluswholeXYsupplement; surface0..5 and complements',
            root_native_stage_max_seconds=600,native_condition_max_seconds=600,root_full_skin_reserve_seconds=240,
            root_contact_post_reserve_seconds=600,root_feedback_reserve_seconds=120,root_preservation_reserve_seconds=120,
            preparation_max_seconds=120,queue_max_seconds=1800,
            candidate_adopted=False,mesh_convergence_validated=False,experimental_validation=False,
            existing_XY_SC_bulk_edge_contact_holds_preserved=True,peer_contact_sensitivity_endorsement=False,
            contact_uncertainty='NominalPBSspecificZ complex-scale uncertainty only; originalRs/measurementarea once conversion already done; no actualskinvalidation',
            frozen_source_snapshot_owner='Standalone CLI freezes once under both global execution locks',
            storage=dict(native_location=str(run),persistent_backup_verified=False,retirement_of_old_environment_allowed=False),
            next_decision='Two independently solved contact bases; retain nominal cache and report fixed-command/five-A changes plus separate rematch; no automatic adoption or validation promotion')
        core.write(run/'preregistration.json',registration);core.freeze_sources(run)
        guard('source_freeze_complete');core.write(run/'controller.json',dict(status='prepared',updated_utc=core.now()));success=True
    except BaseException as error:
        failure=run/'preparation-failure.json'if created else run.with_name(run.name+'.preparation-failure.json')
        if not failure.exists():core.write(failure,dict(status='preparation_failed_preserved',error_type=type(error).__name__,error=str(error),
            observed_utc=core.now(),partial_evidence_preserved=True,automatic_retry=False))
        if created:core.write(run/'controller.json',dict(status='preparation_failed_preserved',updated_utc=core.now(),error=str(error)))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        for sig,handler in old_handlers.items():signal.signal(sig,handler)
        elapsed=time.monotonic()-started;budget['spent_seconds']+=elapsed
        budget['runs'].append(dict(run_id=run.name,stage='preparation',seconds=elapsed,status='prepared' if success else 'preparation_failed_preserved'))
        core.write(budget_path,budget)
    return registration


def main():
    import argparse
    import fcntl
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',type=Path,required=True)
    parser.add_argument('--decision',type=Path,required=True);parser.add_argument('--feedback',type=Path,required=True)
    args=parser.parse_args()
    with (core.REPO/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=prepare_rounded_contact(args.prepare,args.decision,args.feedback)
    print(dict(status=result['status'],run=str(args.prepare),case_ids=list(CASE_IDS)))


if __name__=='__main__':main()
