"""One same-centre/same-area full-face SHAPE comparison; no work on import.

Exactly576 fixed native face rectangles per physical pad; this stepped outline
is not a smooth circle and has70mm perimeter, exceeding the source square60mm.
"""
from __future__ import annotations
import copy
import functools
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import task1_perimeter_shell_registration as parent
core=parent.core
policy=parent.policy
contact=parent.contact
_caller_owns_execution_lock=parent._caller_owns_execution_lock
_mesh=parent._mesh
_changed_config=parent._changed_config
_properties=parent._properties
_mask_bytes=parent._mask_bytes
bounded_command=parent.bounded_command
CASE_ID='rounded-fullface225-xy80'
SOURCE_RUN=BASE_RUN='cloud-mesh-c1-20261019T190000Z'
SOURCE_ID=BASE_ID='baseline-square15-xy80'
INWARD_ID='perimeter-shell225-inward0p625-xy80'
VOLUME=core.REPO/'docs/cloud-perimeter-inward-context-20261021T194000Z/volume.json'
HISTORICAL_CIRCLE=core.REPO/'docs/cloud-resume-20261020/fourpad-coarse-results/equal-circle225-coarse-summary.json'
EXPECTED_CELLS=351680
EXPECTED_RAW_BOUND_BYTES=211008000
MIN_REMAINING_SECONDS=1320
PREPARATION_SECONDS=120
H=.625
CENTRES=((-10.,-10.),(10.,10.),(10.,-10.),(-10.,10.))
COMMON=dict(geometry_kind='fixed_native_face_union',combined_geometry_and_placement=False,isolated_shape_effect_claimed=False,
    native_full_face_contact=True,physical_total_contact_area_mm2=900.,minimum_physical_gap_mm=2.5,minimum_gap_XY_cells=4,
    maximum_physical_vertex_radius_squared_mm2=528.90625,rim_clearance_mm=25-math.sqrt(528.90625),physical_geometry_frozen=True,
    future_grid_reranking_allowed=False,shape_only_contrast=True,centres_unchanged=True,area_unchanged=True,smooth_circle_claimed=False,
    perimeter_reduction_claimed=False,isolated_edge_effect_claimed=False,geometry_revision='rounded-fullface225-odd-r2le730-v1',
    physical_outline_perimeter_mm_per_pad=70.,source_square_perimeter_mm_per_pad=60.,strict_radial_prefix_face_count=560,
    cutoff_tie_face_count=16,all_cutoff_ties_included=True,cutoff_local_odd_radius_squared=730)


@functools.lru_cache(maxsize=1)
def rounded_faces():
    # This defines ONE physical contour at the registered original grid. Future
    # meshes intersect the frozen polygon; they must never repeat this ranking.
    local={(u,v)for u in range(-39,40,2)for v in range(-39,40,2)if u*u+v*v<=730}
    core.require(len(local)==576 and sum(u*u+v*v<730 for u,v in local)==560 and
        sum(u*u+v*v==730 for u,v in local)==16 and
        all((-v,u)in local and(-u,v)in local and(v,u)in local for u,v in local),'All16ties and exact localD4 symmetry required')
    faces=[]
    for cx,cy in CENTRES:
        ic,jc=round((cx+25)/H),round((cy+25)/H)
        cells={((u-1)//2+ic,(v-1)//2+jc)for u,v in local}
        core.require(parent.components(cells)==[576] and not parent.hole_cells(cells),'One connected hole-free rounded face union required')
        faces.append(tuple(sorted(cells,key=lambda q:(q[1],q[0]))))
    core.require(len(set.union(*(set(p)for p in faces)))==2304,'Physical pads overlap')
    return tuple(faces)


def rounded_design(baseline):
    core.require(baseline['id']=='baseline-square15' and baseline['phantom_diameter_mm']==50 and baseline['contact_plane_z_mm']==0 and
        baseline['total_pads']==4 and baseline['source_outputs']==2 and baseline['return_connection']=='all_return_pads_ideal_common_GND'and
        len(baseline['pads'])==4,'Exact original same-centre square baseline required')
    design=copy.deepcopy(baseline);rows=[];areas=[];faces=rounded_faces()
    for p,(pad,cells,centre)in enumerate(zip(design['pads'],faces,CENTRES)):
        core.require(pad['pad']==p and tuple(pad['center_mm'])==centre and pad['shape']=='rectangle' and
            pad['width_mm']==pad['height_mm']==15 and pad['rotation_deg']==0 and pad['analytic_area_mm2']==225 and
            pad['role']==('signal'if p<2 else'common_gnd_return')and pad['source_output']==(p if p<2 else None),
            'Original square centre/shape/area/role/wiring required')
        loop=parent.boundary_loop(cells);xmin=min(x for x,y in loop);xmax=max(x for x,y in loop)
        ymin=min(y for x,y in loop);ymax=max(y for x,y in loop)
        perimeter=math.fsum(math.hypot(x-u,y-v)for (x,y),(u,v)in zip(loop,loop[1:]+loop[:1]))
        core.require(perimeter==70. and xmax-xmin==ymax-ymin==17.5 and
            all(x*x+y*y<625 for x,y in loop),'Exact stepped70mm contour/bbox and fixedD50 required')
        core.require(math.fsum(-25+(i+.5)*H for i,j in cells)/576==centre[0]and
            math.fsum(-25+(j+.5)*H for i,j in cells)/576==centre[1],'Physical contact centroid must remain exactly unchanged')
        pad.update(shape='masked_face_union',geometry_primitive='fixed_union_of_native_full_face_rectangles',centroid_mm=list(centre),
            width_mm=17.5,height_mm=17.5,rotation_deg=0.,corner_radius_mm=0.,
            dimension_fields_role='Bounding-box extents only; actualcontact is fixed stepped face union, not circle orrectangle',
            bounding_box_mm=[xmin,ymin,xmax,ymax],bounding_box_center_mm=list(centre),area_mm2=225.,analytic_area_mm2=225.,polygon_area_mm2=225.,
            polygon_mm=loop,boundary_loops_mm=[loop],boundary_loop_closure='Implicit final-to-first; CCW simple physical outline; noholes',
            native_face_indices=[list(ij)for ij in cells],native_face_h_mm=H,native_face_lower_corner_origin_mm=[-25.,-25.],native_face_count=576,
            union_rectangles_mm=[dict(center_mm=[-25+(i+.5)*H,-25+(j+.5)*H],width_mm=H,height_mm=H)for i,j in cells],
            physical_outline_frozen=True,smooth_annular_arc_claimed=False,smooth_circle_claimed=False,convex_hull_used=False,
            physical_outline_perimeter_mm=perimeter,local_D4_symmetric=True)
        rows.extend((p,i,j,(H/1000)**2)for i,j in cells);areas.append(math.fsum((H/1000)**2 for _ in cells))
    gaps=[]
    for p in range(4):
        for q in range(p+1,4):
            squared=min(max(abs(i-k)-1,0)**2+max(abs(j-l)-1,0)**2 for i,j in faces[p]for k,l in faces[q])
            gaps.append(dict(pad_a=p,pad_b=q,gap_mm=H*math.sqrt(squared)))
    maximum=max(x*x+y*y for p in design['pads']for x,y in p['polygon_mm'])
    core.require(min(g['gap_mm']for g in gaps)==2.5 and maximum==528.90625,'Frozen rounded D50/gap proof changed')
    design.update(**COMMON,id=CASE_ID.removesuffix('-xy80'),group='fixed_same_centre_area_rounded_fullface_shape',xy_mm=[list(v)for v in CENTRES],
        minimum_gap_mm=2.5,verified_physical_gaps_mm=gaps,area_policy='Same physical centres/225mm2 each900total; shape changes axialextent/gaps andperimeter',
        fixed_outline_regeneration_policy='Intersect these frozen full-face boundary loops at futuregrids; never rerank radial cells',
        contact_edge_hold='Not a circle refinement or proof ofpartial-contact error removal; XY/SC/bulk/edge/contact holds retained')
    proof=dict(**COMMON,rule='all-odd-local-cell-centres-u2plusv2le730-all16ties-fixed-fullface-union-v1',h_xy_mm=H,
        faces_per_pad=[576]*4,contacts=2304,represented_pad_areas_m2=areas,full_face_area_m2=(H/1000)**2,partial_faces=0,
        clipping=False,renormalization=False,components_per_pad=[1]*4,holes_per_pad=[0]*4,pad_centroids_mm=[list(v)for v in CENTRES],
        verified_physical_gaps_mm=gaps,boundary_loop_count_per_pad=[1]*4,mesh_convergence_claimed=False,local_D4_symmetric=True,
        future_grid_definition='Frozen physical polygons; the original h=.625 construction rule must not be rerun')
    return design,rows,areas,proof


def changed_rounded_config(data,design,path,sha):
    before=_properties(data);changes={'mask.path':str(path),'mask.sha256':sha}
    for p,pad in enumerate(design['pads']):
        core.require(before[f'pad.{p}.shape']=='rectangle'and float(before[f'pad.{p}.width_mm'])==15 and
            float(before[f'pad.{p}.height_mm'])==15 and float(before[f'pad.{p}.rotation_deg'])==0 and
            [float(before[f'pad.{p}.x_mm']),float(before[f'pad.{p}.y_mm'])]==pad['center_mm'] and
            float(before[f'pad.{p}.analytic_area_mm2'])==225,'Exact original square config/centres required')
        changes.update({f'pad.{p}.shape':'masked_face_union',f'pad.{p}.width_mm':'17.5',f'pad.{p}.height_mm':'17.5'})
    return _changed_config(data,changes),changes


def verify_context(decision_path,feedback_path):
    pins={}
    def pin(path,expected=None):
        p=Path(path);core.require(p.is_absolute() and p==p.resolve() and p.is_relative_to(core.REPO) and
            p.is_file() and not p.is_symlink(),'Canonical local metadata context required')
        digest=core.sha(p);core.require(expected is None or digest==expected,'Context SHA differs');pins[str(p)]=digest
        return p,core.read(p)
    dp,decision=pin(decision_path)
    core.require(decision.get('schema')=='task1-rounded-fullface-root-decision-v1' and
        decision.get('status')=='selected_not_executed' and decision.get('case_id')==CASE_ID and
        decision.get('source_run_id')==SOURCE_RUN and decision.get('source_case_id')==SOURCE_ID and
        isinstance(decision.get('question'),str)and bool(decision['question'].strip()) and
        decision.get('new_PDE')==1 and
        decision.get('new_native_RHS')==8 and decision.get('independent_outputs')==2 and decision.get('physical_pads')==4 and
        decision.get('fixed_total_area_mm2')==900 and decision.get('candidate_adopted')is False and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False,
        'Exact root-selected same-centre area rounded SHAPE decision required')
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
    objects={}
    for key in ('inward_volume','inward_screen'):
        ref=decision.get(key,{});path=Path(ref.get('path',''))
        core.require(path.is_absolute()and str(path)in decision.get('input_sha256',{})and
            decision['input_sha256'][str(path)]==ref.get('SHA256'),'Actual completed inward volume/screen SHA must be explicit root inputs')
        _,objects[key]=pin(path,ref['SHA256'])
    volume,screen=objects['inward_volume'],objects['inward_screen']
    core.require(volume.get('schema')=='task1-volume-selectivity-v1'and volume.get('status')=='calculated_unadopted'and
        volume.get('inputs_unchanged')is True and volume.get('selected_for_adoption')==[] and
        any(c.get('case_id')==INWARD_ID and c.get('adopted')is False for c in volume.get('cases',[])),
        'Completed unchanged unadopted actual inward volume required')
    candidates=[c for c in screen.get('cases',[])if c.get('case_id')==INWARD_ID]
    core.require(screen.get('schema')=='task1-candidate-screen-v1'and screen.get('status')=='screen_complete_not_adopted'and
        screen.get('input_volume_report')==decision['inward_volume']and screen.get('baseline_case_id')==BASE_ID and
        screen.get('candidate_adopted')is False and len(candidates)==1 and len(candidates[0].get('checks',[]))==8 and
        candidates[0].get('all_screen_checks_passed')is False and any(c.get('passed')is False for c in candidates[0]['checks']),
        'Actual same-volume inward8screen failure required; no success/adoption claim')
    return dict(path=str(dp),SHA256=pins[str(dp)],question=decision['question'],root_selected=True,peer_endorsed=False),dict(
        path=str(fp),SHA256=pins[str(fp)],observed_utc=feedback['observed_utc'],public_GET_checked=True,
        public_comment_identity_and_body_sha256=comments,root_selected_geometry=True,peer_geometry_endorsement=False),pins


def prepare_rounded_fullface(run,decision_path,feedback_path):
    started=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run==run.resolve() and not run.exists() and
        not run.with_name(run.name+'.preparation-failure.json').exists(),
        'New canonical unique rounded-fullface run required; preserve failed run IDs')
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
        for p in (Path(__file__).resolve(),core.REPO/'tests/test_task1_rounded_fullface_registration.py',
            Path(contact.__file__).resolve(),Path(parent.__file__).resolve(),HISTORICAL_CIRCLE,
            core.REPO/'tools/task1_rounded_fullface_volume_registration.py',core.REPO/'tests/test_task1_rounded_fullface_volume_registration.py',VOLUME):pins[str(p)]=core.sha(p)
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
        baseline,base_config,base_mask=source,old_config,old_mask
        core.require(source['source_coating_nm']==10 and source['source_Rs_fit_window_Hz']==500,'NominalPBS10nm/Rs500 parent required')
        src,base=_properties(old_config.read_bytes()),_properties(base_config.read_bytes())
        core.require(src['h_mm']=='0.625' and src['validation.sc_cells']=='2' and src['bulk.counts']=='14,14,40' and
            src['frequencies']=='3000,3030,9000,9090' and src['channels']=='2' and source['channels']==2 and
            source['h_xy_mm']==.625 and source['sc_cells']==2 and source['bulk_counts']==[14,14,40],
            'Exact original two-output/four-frequency XY80/SC2/bulk14,14,40 parent required')
        core.require({k:v for k,v in src.items() if k.startswith('z.') or k.endswith(('.sigma','.epsilon_r'))}==
            {k:v for k,v in base.items() if k.startswith('z.') or k.endswith(('.sigma','.epsilon_r'))},'Parent/baseline contact/tissue physics differs')
        design,rows,areas,proof=rounded_design(source['design'])
        mask=run/'masks'/(CASE_ID+'.csv');mask.write_bytes(_mask_bytes(rows))
        config=run/'configs'/(CASE_ID+'.properties');data,changes=changed_rounded_config(old_config.read_bytes(),design,mask,core.sha(mask));config.write_bytes(data)
        core.write(run/'geometry-audit/rounded-design.json',design);core.write(run/'geometry-audit/rounded-mask-proof.json',proof)
        case=copy.deepcopy(source)
        case.update(id=CASE_ID,design_id=design['id'],design=design,source_run_id=run.name,
            config_file=str(config),config_sha256=core.sha(config),mask_file=str(mask),mask_sha256=core.sha(mask),expected_pad_areas_m2=areas,
            **COMMON,n_pads=4,n_outputs=2,channels=2,
            prototype_reference=dict(run_id=SOURCE_RUN,case_id=SOURCE_ID,config_file=str(old_config),config_sha256=core.sha(old_config)),
            historical_parent_original_prototype=source.get('prototype_reference'),
            baseline_same_grid_reference=dict(run_id=BASE_RUN,case_id=BASE_ID,config_file=str(base_config),config_sha256=core.sha(base_config)),
            combined_geometry_and_area_allocation=False,isolated_area_effect_claimed=False,
            status='preregistered_not_executed',candidate_adopted=False,mesh_convergence_validated=False,existing_XY_contact_model_holds_preserved=True)
        case.update(_mesh(case));core.require(case['cells']==EXPECTED_CELLS,'351680cell mesh changed')
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
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='one_same_centre_area_rounded_fullface_shape',status='prepared',
            created_utc=core.now(),source_commit=commit,package_integrity=integrity,limits=limits,gates=copy.deepcopy(core.GATES),cases=[case],java=java,
            new_PDE_conditions_maximum=1,new_native_RHS_maximum=8,expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,source_and_input_sha256=pins,
            preparation_seconds=time.monotonic()-started,root_selection_decision=decision,source_feedback=feedback,
            resource_policy_immutable_refs=policy.policy_refs(budget),
            historical_coarse_circle=dict(summary_path=str(HISTORICAL_CIRCLE),summary_sha256=core.sha(HISTORICAL_CIRCLE),
                diagnostic_only=True,same_geometry_refinement=False,new_circle_discovery_claimed=False),
            scientific_question=decision['question'],
            unchanged_controls=[dict(run_id=BASE_RUN,case_id=BASE_ID,new_PDE=0)],
            path_mapping=[dict(original_config=str(old_config),original_sha256=core.sha(old_config),new_config=str(config),new_sha256=core.sha(config),
                changed_fields=list(changes),electrical_contact_tissue_mesh_frequency_changed_fields=[],
                geometry_is_explicit_mask=True,fixed_native_face_union=True,physical_outline_frozen=True,future_grid_reranking_allowed=False)],
            planned_normalizations=['raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin'],
            comparison_waveforms=['square_3h','sine','triangle_3h'],fixed_cutoffs_V_m=dict(baseline_mean=4.061848941601601,baseline_p10=3.6457357391300533),
            fixed_ROIs='Primaryr<=5mm depth15..20; supplementarywholeXYsame-depth; surface0..5 and bothcomplements',
            root_full_skin_reserve_seconds=180,root_volume_reserve_seconds=180,root_probe_reserve_seconds=120,root_UI_reserve_seconds=120,
            preparation_max_seconds=120,queue_max_seconds=1320,candidate_adopted=False,mesh_convergence_validated=False,experimental_validation=False,
            existing_XY_contact_model_holds_preserved=True,peer_geometry_endorsement=False,
            contact_uncertainty='Unchanged nominalPBS specificZ: one originalRs subtraction/area conversion; actualskincontact unvalidated',
            frozen_source_snapshot_owner='Standalone CLI freezes once under both global execution locks',
            storage=dict(native_location=str(run),persistent_backup_verified=False,retirement_of_old_environment_allowed=False),
            next_decision='One newnative8RHS only, thenfullskin/probe40/volume5modes/fixed8screens; no adoption orautomaticrefinement from one same-centre area shape contrast; not smoothcircle, perimeterreduction or contactartifact proof')
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
        result=prepare_rounded_fullface(args.prepare,args.decision,args.feedback)
    print(dict(status=result['status'],run=str(args.prepare),case_id=CASE_ID))


if __name__=='__main__':main()
