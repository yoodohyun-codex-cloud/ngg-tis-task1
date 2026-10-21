"""Prepare one SC-only rounded-pad sensitivity basis, without changing caps.

Import performs no data access. The source mask bytes and physical contours are
unchanged; SC thickness stays0.1mm while its discretization increases2→4cells.
"""
from __future__ import annotations
import copy
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import task1_rounded_fullface_registration as rounded
core=rounded.core
policy=rounded.policy
contact=rounded.contact
parent=rounded.parent
_caller_owns_execution_lock=rounded._caller_owns_execution_lock
_mesh=rounded._mesh
_changed_config=rounded._changed_config
_properties=rounded._properties
bounded_command=rounded.bounded_command
CASE_ID='rounded-fullface225-sc4-xy80'
SOURCE_RUN='cloud-rounded-fullface-20261021T200000Z'
SOURCE_ID='rounded-fullface225-xy80'
BASE_RUN='cloud-mesh-c1-20261019T190000Z'
BASE_ID='baseline-square15-xy80'
CACHED_SC4_ID='baseline-square15-sc4'
VOLUME=core.REPO/'docs/cloud-rounded-fullface-context-20261021T200000Z/volume.json'
EXPECTED_CELLS=361728
EXPECTED_RAW_BOUND_BYTES=217036800
MIN_REMAINING_SECONDS=1320
PREPARATION_SECONDS=120
CAPS={'surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2','contact_voltage_RMS_max_V','SC_power_W','contact_power_W',
    'bulk_skin_J_vector_RMS_max_A_m2','bulk_skin_J_vector_RMS_p95_A_m2','skin_SC_plus_dermis_power_W'}


def changed_sc4_config(data,mask_path):
    source=_properties(data)
    core.require(source.get('h_mm')=='0.625'and source.get('validation.sc_cells')=='2'and source.get('bulk.counts')=='14,14,40'and
        source.get('frequencies')=='3000,3030,9000,9090'and source.get('channels')=='2','Exact source SC2 grid and four basis frequencies required')
    changes={'validation.sc_cells':'4','mask.path':str(mask_path)}
    return _changed_config(data,changes),changes


def validate_physical_identity(source,maskbytes):
    core.require(source.get('id')==SOURCE_ID and source.get('h_xy_mm')==.625 and source.get('sc_cells')==2 and
        source.get('bulk_counts')==[14,14,40]and source.get('channels')==2 and source.get('cells')==351680,
        'Exact original rounded SC2 source required')
    for record in (source,source['design']):
        core.require(all(record.get(k)==v for k,v in rounded.COMMON.items()),'Frozen rounded source physical provenance differs')
    circuit=source['circuit'];core.require(circuit.get('n_pads')==4 and circuit.get('n_outputs')==2 and circuit.get('n_return_nodes')==1 and
        circuit.get('source_resistance_ohm')==50 and circuit.get('source_peak_V')==.5 and
        circuit.get('pad_to_node')=={'0':'out0','1':'out1','2':'GND','3':'GND'},'Same four-pad/two-output common-GND circuit required')
    areas=source.get('expected_pad_areas_m2',[])
    core.require(len(areas)==4 and all(math.isclose(a,.000225,rel_tol=1e-12,abs_tol=1e-16)for a in areas),'Four unchanged225mm2 contacts required')
    expected=[]
    for p,(pad,faces,centre)in enumerate(zip(source['design']['pads'],rounded.rounded_faces(),rounded.CENTRES)):
        core.require(pad.get('pad')==p and pad.get('shape')=='masked_face_union'and pad.get('center_mm')==list(centre)and
            pad.get('width_mm')==pad.get('height_mm')==17.5 and pad.get('rotation_deg')==0 and pad.get('analytic_area_mm2')==225 and
            pad.get('role')==('signal'if p<2 else'common_gnd_return')and pad.get('source_output')==(p if p<2 else None)and
            pad.get('native_face_indices')==[list(v)for v in faces]and pad.get('polygon_mm')==parent.boundary_loop(faces)and
            pad.get('boundary_loops_mm')==[pad['polygon_mm']],'Physical rounded contour/identity/area/wiring changed')
        expected.extend((p,i,j,(.625/1000)**2)for i,j in faces)
    digest=hashlib.sha256(maskbytes).hexdigest()
    core.require(digest==source['mask_sha256']and maskbytes==rounded._mask_bytes(expected),'Exact unchanged full-face source mask bytes required')
    return dict(physical_geometry_unchanged=True,mask_byte_SHA256=digest,physical_total_contact_area_mm2=900.,
        old_SC_cells=2,new_SC_cells=4,physical_SC_thickness_mm=.1,source_SC_cell_thickness_mm=.05,new_SC_cell_thickness_mm=.025,
        XY_bulk_contact_circuit_material_unchanged=True,physical_contour_regenerated_for_new_grid=False)


def validate_selected_condition(summary,condition,condition_id):
    core.require(summary.get('schema')in ('task1-rounded-drive-scout-v1','task1-rounded-drive-optimization-v1')and
        summary.get('status')=='calculated_unadopted'and summary.get('inputs_unchanged')is True and summary.get('new_PDE')==0 and
        summary.get('candidate_adopted')is False and summary.get('source_geometry',{}).get('source_case_id')==SOURCE_ID and
        summary.get('source_geometry',{}).get('source_run_id')==SOURCE_RUN and
        len([r for r in summary.get('conditions',[])if r.get('id')==condition_id and r.get('status')=='calculated_unadopted'])==1,
        'Actual completed selected weak/optimized rounded SC2 source condition required')
    core.require(condition.get('schema')in ('task1-rounded-drive-condition-v1','task1-rounded-drive-optimization-condition-v1')and
        condition.get('status')=='calculated_unadopted'and condition.get('id')==condition_id and condition.get('new_PDE')==0 and
        condition.get('candidate_adopted')is False and condition.get('source_case_id')==SOURCE_ID and condition.get('source_run_id')==SOURCE_RUN and
        condition.get('active_frequencies_Hz')==condition.get('actual_fundamental_Hz')==[3000,3030]and
        re.fullmatch('[0-9a-f]{64}',condition.get('configuration_sha256',''))is not None,
        'Selected source identity/configuration and exact two-carrier family differ')
    coefficients=condition['coefficient_vectors'];core.require(set(coefficients)=={'3000','3030','9000','9090'},'Explicit four-frequency two-output coefficients required')
    for f,c in coefficients.items():
        core.require(set(c)=={'real','imaginary'}and all(isinstance(c[k],list)and len(c[k])==2 and
            all(type(v)in(int,float)and math.isfinite(v)for v in c[k])for k in c),'Finite two-output complex coefficient vectors required')
        if f in ('9000','9090'):core.require(all(v==0 for k in c.values()for v in k),'Selected two-tone coefficients must keep harmonics inactive')
        else:core.require(any(v!=0 for k in c.values()for v in k),'Both selected carriers must remain active')
    mode=condition['normalizations']['skin_contact_only'];scale=mode['amplitude_scale'];caps=mode['baseline_derived_numerical_limits']
    core.require(type(scale)in(int,float)and math.isfinite(scale)and scale>0 and mode.get('includes_source_power_cap')is False and
        mode.get('includes_1Vpp_ceiling')is False and CAPS<=set(caps)and all(math.isfinite(caps[k])and caps[k]>0 for k in CAPS),
        'Saved positive SC2 amplitude under original eight numerical caps required')
    raw=condition['source_waveform']['source_Vpp_intervals_V'];scaled=mode['actual_source_Vpp_intervals_V']
    for intervals in (raw,scaled):
        core.require(isinstance(intervals,list)and len(intervals)==2 and all(isinstance(row,list)and len(row)==2 and
            all(type(v)in(int,float)and math.isfinite(v)and v>0 for v in row)and row[1]>=row[0]for row in intervals),
            'Saved positive full-source waveform Vpp intervals required')
    core.require(all(math.isclose(s,v*scale,rel_tol=1e-12,abs_tol=1e-14)for a,b in zip(raw,scaled)for v,s in zip(a,b))and
        isinstance(condition.get('shared_original_square_cutoffs_V_m'),dict)and bool(condition['shared_original_square_cutoffs_V_m']),
        'Saved source Vpp scaling or fixed original SC2 cutoff metadata differs')
    return dict(condition_id=condition_id,source_run_id=SOURCE_RUN,source_case_id=SOURCE_ID,configuration_sha256=condition['configuration_sha256'],
        raw_coefficient_vectors=copy.deepcopy(coefficients),SC2_skin8_amplitude_scale=scale,SC2_skin8_source_Vpp_intervals_V=copy.deepcopy(scaled),
        raw_source_Vpp_intervals_V=copy.deepcopy(raw),SC2_original_eight_caps=copy.deepcopy(caps),
        SC2_original_cutoffs_V_m=copy.deepcopy(condition['shared_original_square_cutoffs_V_m']),coefficients_and_SC2_amplitude_frozen=True,
        SC4_rematching_performed=False,all_eight_screens_passed_required_for_sensitivity=False,candidate_adopted=False)


def cached_original_sc4(pins):
    run=core.REPO/'data-native'/BASE_RUN
    def load(path):pins[str(path)]=core.sha(path);return core.read(path)
    pre=load(run/'preregistration.json');case=next(c for c in pre['cases']if c['id']==CACHED_SC4_ID)
    sc2=next(c for c in pre['cases']if c['id']==BASE_ID);record=load(run/'cases'/(CACHED_SC4_ID+'.json'))
    sp=Path(record['postprocess_path']);post=load(sp);config=Path(case['config_file']);sc2config=Path(sc2['config_file'])
    for path,expected in ((config,case['config_sha256']),(sc2config,sc2['config_sha256']),(Path(case['mask_file']),case['mask_sha256'])):
        core.require(core.sha(path)==expected,'Cached original SC4 config/mask SHA changed');pins[str(path)]=expected
    before,after=_properties(sc2config.read_bytes()),_properties(config.read_bytes())
    core.require(before.keys()==after.keys()and before['validation.sc_cells']=='2'and after['validation.sc_cells']=='4'and
        [k for k in before if before[k]!=after[k]]==['validation.sc_cells'],'Cached original SC2→SC4 must change exactly one grid property')
    core.require(record.get('status')=='complete'and record['postprocess_sha256']==pins[str(sp)]and post['status']=='complete'and
        post['id']==CACHED_SC4_ID and all(record['validation'][k]<=v for k,v in core.GATES.items()),'Cached original SC4 native gates/postprocess incomplete')
    meta=post['mesh_metadata'];core.require(meta['sc_cells']==4 and meta['h_xy_mm']==.625 and meta['cells']==EXPECTED_CELLS and
        meta['bulk_layer_counts']==[14,14,40]and meta['frequencies_Hz']==[3000,3030,9000,9090]and
        meta['tissue_boundaries_mm']==[0,.1,5.1,10.1,25.1],'Cached SC4 original fixed-layer mesh differs')
    declared=post['input_sha256']
    for f in (3000,3030,9000,9090):
        found=[p for p in declared if Path(p).name==f'field-{f}.bin.gz']
        core.require(len(found)==1 and Path(found[0]).is_file(),'Required cached SC4 complex field unavailable')
    return dict(run_id=BASE_RUN,case_id=CACHED_SC4_ID,summary_path=str(sp),summary_sha256=pins[str(sp)],config_sha256=case['config_sha256'],
        cells=EXPECTED_CELLS,new_PDE=0,native_array_bytes_read=False,declared_native_inputs_sha256=declared,
        existing_native_validation=copy.deepcopy(record['validation']),validation_scope='Existing five discrete-equation gates only; no new convergence or experiment certification',
        normalization_reference=False,role='Cached original SC-axis numerical diagnostic; original SC2 caps remain fixed')


def verify_context(decision_path,feedback_path):
    pins={}
    def pin(path,expected=None):
        p=Path(path);core.require(p.is_absolute() and p==p.resolve() and p.is_relative_to(core.REPO) and
            p.is_file() and not p.is_symlink(),'Canonical local metadata context required')
        digest=core.sha(p);core.require(expected is None or digest==expected,'Context SHA differs');pins[str(p)]=digest
        return p,core.read(p)
    dp,decision=pin(decision_path)
    core.require(decision.get('schema')=='task1-rounded-sc4-root-decision-v1' and
        decision.get('status')=='selected_not_executed' and decision.get('case_id')==CASE_ID and
        decision.get('source_run_id')==SOURCE_RUN and decision.get('source_case_id')==SOURCE_ID and
        isinstance(decision.get('question'),str)and bool(decision['question'].strip()) and
        decision.get('new_PDE')==1 and
        decision.get('new_native_RHS')==8 and decision.get('independent_outputs')==2 and decision.get('physical_pads')==4 and
        decision.get('fixed_total_area_mm2')==900 and decision.get('candidate_adopted')is False and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False,
        'Exact root-selected one-condition SC-only sensitivity decision required')
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
    optref=decision.get('optimization_result',{});op=Path(optref.get('path',''))
    core.require(str(op)in decision.get('input_sha256',{})and decision['input_sha256'][str(op)]==optref.get('SHA256'),
        'Actual completed rounded optimization must be explicitly SHA-pinned')
    _,optimization=pin(op,optref['SHA256'])
    core.require(optimization.get('schema')=='task1-rounded-drive-optimization-v1'and optimization.get('status')=='calculated_unadopted'and
        optimization.get('inputs_unchanged')is True and optimization.get('new_PDE')==0 and optimization.get('candidate_adopted')is False and
        optimization.get('source_geometry',{}).get('source_case_id')==SOURCE_ID and
        optimization.get('source_geometry',{}).get('source_run_id')==SOURCE_RUN,'Completed unadopted actual rounded optimization required')
    selected=decision.get('selected_condition',{})
    core.require(selected.get('normalization')=='skin_contact_only'and isinstance(selected.get('condition_id'),str),
        'Explicit root-selected source SC2 condition and frozen normalization required')
    objects={}
    for key in ('summary','condition'):
        ref=selected.get(key,{});path=Path(ref.get('path',''))
        core.require(str(path)in decision.get('input_sha256',{})and decision['input_sha256'][str(path)]==ref.get('SHA256'),
            'Selected source summary/condition SHA must be root inputs')
        _,objects[key]=pin(path,ref['SHA256'])
    selection=validate_selected_condition(objects['summary'],objects['condition'],selected['condition_id'])
    refs=[c for c in objects['summary']['conditions']if c['id']==selected['condition_id']]
    core.require(refs[0]['artifacts']['condition.json']==selected['condition'],'Selected condition must be the genuine saved summary artifact')
    return dict(path=str(dp),SHA256=pins[str(dp)],question=decision['question'],root_selected=True,peer_endorsed=False,selected_SC2_command=selection),dict(
        path=str(fp),SHA256=pins[str(fp)],observed_utc=feedback['observed_utc'],public_GET_checked=True,
        public_comment_identity_and_body_sha256=comments,root_selected_geometry=True,peer_geometry_endorsement=False),pins


def prepare_rounded_sc4(run,decision_path,feedback_path):
    started=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run==run.resolve() and not run.exists() and
        not run.with_name(run.name+'.preparation-failure.json').exists(),
        'New canonical unique rounded-SC4 run required; preserve failed run IDs')
    _caller_owns_execution_lock();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    budget_path=core.REPO/'runtime/task1-budget.json';budget=policy.load_ledger(budget_path);limit=policy.effective_limit(budget)
    core.require(limit==13800 and limit-budget['spent_seconds']>=MIN_REMAINING_SECONDS,'Approved13800s policy with1320s finite queue reserve required')
    success=False;registration=None;created=False
    old_handlers={sig:signal.getsignal(sig)for sig in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
    def interrupted(sig,frame):raise RuntimeError('Bounded preparation interrupted by signal '+str(sig))
    for sig in old_handlers:signal.signal(sig,interrupted)
    signal.setitimer(signal.ITIMER_REAL,max(.001,PREPARATION_SECONDS-(time.monotonic()-started)))
    try:
        decision,feedback,pins=verify_context(Path(decision_path).absolute(),Path(feedback_path).absolute())
        pins.update(core.source_pins(budget))
        for p in (Path(__file__).resolve(),core.REPO/'tests/test_task1_rounded_sc4_registration.py',Path(rounded.__file__).resolve(),
            Path(parent.__file__).resolve(),Path(contact.__file__).resolve(),VOLUME):pins[str(p)]=core.sha(p)
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=core.REPO,text=True).strip()
        for name,digest in pins.items():
            p=Path(name);core.require(core.sha(p)==digest,'Pinned source/context changed: '+name)
            if p.suffix in ('.py','.java'):
                core.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(core.REPO))],cwd=core.REPO)==p.read_bytes(),
                    'Commit all consumed implementation sources/tests before preparation: '+name)
        limits=core.effective_limits(budget)
        core.require(EXPECTED_RAW_BOUND_BYTES==EXPECTED_CELLS*600<=limits['max_batch_added_bytes'] and
            shutil.disk_usage(run.parent).free>2*core.GIB+EXPECTED_RAW_BOUND_BYTES,'Single raw basis plus2GiB reserve unavailable')
        run.mkdir();created=True
        for d in ('configs','masks','bases','cases','postprocess','logs','classes','geometry-audit'):(run/d).mkdir()
        def guard(phase):
            elapsed=time.monotonic()-started;remaining=min(PREPARATION_SECONDS-elapsed,limit-budget['spent_seconds']-elapsed-1200)
            core.require(remaining>0 and core.rss(os.getpid())<3*core.GIB and shutil.disk_usage(run).free>=2*core.GIB,
                'Preparation120s/RSS/reserve exhausted at '+phase)
            core.write(run/'controller.json',dict(status='preparing',phase=phase,pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),
                updated_utc=core.now(),elapsed_seconds=elapsed));return remaining
        guard('original_and_parent_integrity');integrity=core.original_integrity();volume=core.read(VOLUME)
        core.require(volume['status']=='calculated_unadopted' and volume['inputs_unchanged'] is True,'Completed unchanged volume containing the original square control required')
        source,old_config,old_mask,spins=contact._source_case(core,SOURCE_RUN,SOURCE_ID,volume);pins.update(spins)
        baseline,base_config,base_mask,bpins=contact._source_case(core,BASE_RUN,BASE_ID,volume);pins.update(bpins)
        core.require(source['source_coating_nm']==10 and source['source_Rs_fit_window_Hz']==500,'NominalPBS10nm/Rs500 parent required')
        src,base=_properties(old_config.read_bytes()),_properties(base_config.read_bytes())
        core.require(src['h_mm']=='0.625' and src['validation.sc_cells']=='2' and src['bulk.counts']=='14,14,40' and
            src['frequencies']=='3000,3030,9000,9090' and src['channels']=='2' and source['channels']==2 and
            source['h_xy_mm']==.625 and source['sc_cells']==2 and source['bulk_counts']==[14,14,40],
            'Exact original two-output/four-frequency XY80/SC2/bulk14,14,40 parent required')
        core.require({k:v for k,v in src.items() if k.startswith('z.') or k.endswith(('.sigma','.epsilon_r'))}==
            {k:v for k,v in base.items() if k.startswith('z.') or k.endswith(('.sigma','.epsilon_r'))},'Parent/baseline contact/tissue physics differs')
        identity=validate_physical_identity(source,old_mask.read_bytes());cached_sc4=cached_original_sc4(pins)
        selection=decision['selected_SC2_command']
        core.require(selection['configuration_sha256']==source['config_sha256'],'Selected actual SC2 command belongs to another configuration')
        original=next(c for c in volume['cases']if c['case_id']==BASE_ID)
        core.require(selection['SC2_original_eight_caps']==original['normalizations']['skin_contact_only']['baseline_derived_numerical_limits']and
            selection['SC2_original_cutoffs_V_m']==original['fixed_same_grid_baseline_cutoffs_V_m'],
            'Selected command must preserve original SC2 square caps/cutoffs exactly')
        mask=run/'masks'/(CASE_ID+'.csv');mask.write_bytes(old_mask.read_bytes())
        core.require(core.sha(mask)==source['mask_sha256'],'Copied mask must remain byte-identical')
        config=run/'configs'/(CASE_ID+'.properties');data,changes=changed_sc4_config(old_config.read_bytes(),mask);config.write_bytes(data)
        core.write(run/'geometry-audit/SC-only-identity.json',identity)
        case=copy.deepcopy(source)
        case.update(id=CASE_ID,mesh_id='xy80-sc4',sc_cells=4,source_run_id=run.name,config_file=str(config),config_sha256=core.sha(config),
            mask_file=str(mask),mask_sha256=source['mask_sha256'],expected_pad_areas_m2=copy.deepcopy(source['expected_pad_areas_m2']),
            SC_only_sensitivity=True,shape_only_contrast=False,physical_design_origin_shape_only=True,physical_geometry_unchanged=True,physical_SC_thickness_mm=.1,
            prototype_reference=dict(run_id=SOURCE_RUN,case_id=SOURCE_ID,config_file=str(old_config),config_sha256=source['config_sha256']),
            historical_shape_prototype=source.get('prototype_reference'),
            SC2_source_reference=dict(run_id=SOURCE_RUN,case_id=SOURCE_ID,config_file=str(old_config),config_sha256=source['config_sha256']),
            cached_original_SC4_reference=cached_sc4,selected_SC2_command=selection,
            original_SC2_caps_and_cutoffs_frozen=True,SC4_rematching_performed=False,
            status='preregistered_not_executed',candidate_adopted=False,mesh_convergence_validated=False,
            existing_XY_SC_bulk_edge_contact_holds_preserved=True)
        case.pop('baseline_same_grid_reference',None)
        case['canonical_SC2_caps_reference']=dict(run_id=BASE_RUN,case_id=BASE_ID,config_file=str(base_config),config_sha256=core.sha(base_config),same_native_grid=False,scope='Frozen original SC2 numerical caps/cutoffs; not a rematched SC4 baseline')
        case.update(_mesh(case));core.require(case['cells']==EXPECTED_CELLS,'361728cell SC4 mesh changed')
        case['cache_signature']=core.check_cached_operator(case,run)
        jdk=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin');javac=shutil.which('javac') or str(jdk/'javac')
        java=str(Path(javac).resolve().parent/'java');core.require(Path(javac).is_file() and Path(java).is_file(),'Matching installed Java compiler/runtime required')
        with (run/'logs/compile-selftest.log').open('x') as log:
            def command(args):bounded_command(args,log,guard)
            command([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(run/'classes'),str(core.SOURCE/'TisSweep.java'),
                str(core.SOURCE/'ExploreBasis.java'),str(core.SOURCE/'SelectivityShapeBasis.java'),str(core.REPO/'tools/java/CloudShapeBasis.java')])
            command([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),'CloudShapeBasis','--selftest'])
        for d in ('configs','masks','classes','geometry-audit'):
            for p in (run/d).iterdir():pins[str(p)]=core.sha(p)
        for p,digest in pins.items():core.require(core.sha(p)==digest,'Pinned rounded-fullface input changed: '+p)
        guard('final_integrity')
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='one_rounded_SC_only_sensitivity_basis',status='prepared',
            created_utc=core.now(),source_commit=commit,package_integrity=integrity,limits=limits,gates=copy.deepcopy(core.GATES),cases=[case],java=java,
            new_PDE_conditions_maximum=1,new_native_RHS_maximum=8,expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,source_and_input_sha256=pins,
            preparation_seconds=time.monotonic()-started,root_selection_decision=decision,source_feedback=feedback,
            resource_policy_immutable_refs=policy.policy_refs(budget),
            selected_SC2_command=selection,cached_original_SC4_reference=cached_sc4,physical_identity=identity,
            scientific_question=decision['question'],
            unchanged_controls=[dict(run_id=SOURCE_RUN,case_id=SOURCE_ID,new_PDE=0),dict(run_id=BASE_RUN,case_id=CACHED_SC4_ID,new_PDE=0)],
            path_mapping=[dict(original_config=str(old_config),original_sha256=core.sha(old_config),new_config=str(config),new_sha256=core.sha(config),
                changed_fields=list(changes),electrical_contact_tissue_frequency_changed_fields=[],mesh_changed_fields=['validation.sc_cells'],
                geometry_is_explicit_mask=True,fixed_native_face_union=True,physical_outline_frozen=True,future_grid_reranking_allowed=False)],
            planned_normalizations=[],normalization_scope='Basis only; separate root tool must keep selected SC2 coefficients/amplitude and original SC2 caps/cutoffs fixed; rematched SC4 display is optional and separate',
            comparison_waveforms=['square_3h','sine','triangle_3h'],fixed_cutoffs_V_m=dict(baseline_mean=4.061848941601601,baseline_p10=3.6457357391300533),
            fixed_ROIs='Primaryr<=5mm depth15..20; supplementarywholeXYsame-depth; surface0..5 and bothcomplements',
            root_full_skin_reserve_seconds=180,root_volume_reserve_seconds=180,root_probe_reserve_seconds=120,root_UI_reserve_seconds=120,
            preparation_max_seconds=120,queue_max_seconds=1320,candidate_adopted=False,mesh_convergence_validated=False,experimental_validation=False,
            existing_XY_contact_model_holds_preserved=True,peer_geometry_endorsement=False,
            contact_uncertainty='Unchanged nominalPBS specificZ: one originalRs subtraction/area conversion; actualskincontact unvalidated',
            frozen_source_snapshot_owner='Standalone CLI freezes once under both global execution locks',
            storage=dict(native_location=str(run),persistent_backup_verified=False,retirement_of_old_environment_allowed=False),
            next_decision='One newSC4basis8RHS only. Separate root comparison keeps actual selected SC2 coefficients/amplitude and original SC2 caps/cutoffs fixed; no silent SC4cap redefinition, adoption, two-level full-convergence claim or automatic nextPDE')
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
        result=prepare_rounded_sc4(args.prepare,args.decision,args.feedback)
    print(dict(status=result['status'],run=str(args.prepare),case_id=CASE_ID))


if __name__=='__main__':main()
