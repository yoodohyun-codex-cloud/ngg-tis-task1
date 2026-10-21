"""One physical return-pad rotation; import never prepares or starts a solve.

Only pad2 of the completed asymmetric parent is rotated90degrees about its
unchanged centre. Axis-aligned width/height encode that rotation once; operative
rotation_deg stays0. The root owns the one finite PDE and subsequent audits.
"""
from __future__ import annotations

import copy
import csv
import io
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

import task1_cloud_batch as core
import task1_resource_policy as policy
import task1_asymmetric_registration as asym
import task1_contact_sensitivity_registration as contact
from task1_grouped_registration import _caller_owns_execution_lock,_mesh
from task1_reference_registration import _changed_config,_properties

CASE_ID='asym-return2-rot90-xy80'
SOURCE_RUN='cloud-asymmetric-20261021T051000Z'
SOURCE_ID='asym-cross281p25-return168p75-xy80'
BASE_RUN='cloud-mesh-c1-20261019T190000Z'
BASE_ID='baseline-square15-xy80'
VOLUME=core.REPO/'docs/cloud-continuation-20261021/volume-asymmetric.json'
EXPECTED_CELLS=351680
EXPECTED_RAW_BOUND_BYTES=211008000
MIN_REMAINING_SECONDS=1320
PREPARATION_SECONDS=120


def _mask_bytes(rows):
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n')
    writer.writerow(['pad','i','j','area_m2'])
    for p,i,j,a in rows:writer.writerow([p,i,j,format(a,'.17g')])
    return stream.getvalue().encode()


def _rectangles(pad):
    return pad.get('union_rectangles_mm',[dict(center_mm=pad['center_mm'],width_mm=pad['width_mm'],height_mm=pad['height_mm'])])


def _physical_gaps(design):
    result=[]
    for p in range(4):
        for q in range(p+1,4):
            gaps=[]
            for a in _rectangles(design['pads'][p]):
                for b in _rectangles(design['pads'][q]):
                    dx=abs(a['center_mm'][0]-b['center_mm'][0])-(a['width_mm']+b['width_mm'])/2
                    dy=abs(a['center_mm'][1]-b['center_mm'][1])-(a['height_mm']+b['height_mm'])/2
                    core.require(not(dx<0 and dy<0),'Physical rotated pad collides with another contact')
                    gaps.append(math.hypot(max(dx,0),max(dy,0)))
            result.append(dict(pad_a=p,pad_b=q,gap_mm=min(gaps)))
    core.require(all(r['gap_mm']>0 for r in result),'Positive physical separation required')
    return result


def rotated_design(source_design):
    asym.aligned_mixed_mask(source_design)
    design=copy.deepcopy(source_design);pad=design['pads'][2];x,y=pad['center_mm']
    pad.update(width_mm=11.25,height_mm=15.,rotation_deg=0.,
        polygon_mm=[[x-(v-y),y+(u-x)] for u,v in pad['polygon_mm']],
        applied_physical_rotation_deg=90,original_intrinsic_dimensions_mm=[15.,11.25],
        geometry_primitive='axis_aligned_rectangle_after_single90deg_rotation',
        rotation_encoding='Physical+90deg once; swapped axis-aligned width/height; operative rotation_deg0')
    core.require(all(u*u+v*v<625 for p in design['pads'] for u,v in p['polygon_mm']), 'Rotated physical vertex outside fixedD50')
    gaps=_physical_gaps(design)
    design.update(id=CASE_ID.removesuffix('-xy80'),group='one_return_orientation_only_asymmetric_parent',
        applied_physical_rotation_deg=90,rotated_physical_pad_id=2,
        minimum_gap_mm=min(r['gap_mm'] for r in gaps),verified_physical_gaps_mm=gaps,
        geometry_revision='fixed-centre-pad2-single90deg-axis-swap-v1',
        area_policy='Identical281.25/281.25/168.75/168.75mm2;900mm2 total; only physicalGNDpad2 orientation changes',
        physical_total_contact_area_mm2=900.,original_parent_design_id=source_design['id'])
    core.require(all(design['pads'][p] == source_design['pads'][p] for p in (0,1,3)), 'Sources and returnpad3 must remain unchanged')
    return design


def _source_keys():
    keys=set()
    for p,c in ((0,24),(1,56)):
        for w,h in ((28,20),(20,28)):
            keys.update((p,i,j) for j in range(c-h//2,c+h//2) for i in range(c-w//2,c+w//2))
    keys.update((2,i,j) for j in range(15,33) for i in range(44,68))
    keys.update((3,i,j) for j in range(47,65) for i in range(12,36))
    return keys


def rotate_mask(source_rows):
    """Rigid full-face index permutation; preserve every stored area value."""
    h=.625;face=(h/1000)**2
    core.require(len(source_rows)==2304 and len({(p,i,j) for p,i,j,_ in source_rows})==2304 and
        {(p,i,j) for p,i,j,_ in source_rows}==_source_keys() and all(type(p) is int and type(i) is int and
        type(j) is int and math.isfinite(a) and a>0 and abs(a-face)<=4*math.ulp(1.)*face for p,i,j,a in source_rows),
        'Exact asymmetric-parent full-face physical mask required')
    rows=[];covered=set()
    for p,i,j,a in source_rows:
        if p==2:i,j=79-j,i-32
        core.require(0<=i<80 and 0<=j<80 and (i,j) not in covered and
            all((-25+ii*h)**2+(-25+jj*h)**2<625 for ii in (i,i+1) for jj in (j,j+1)),
            'Rotated mask overlaps another physical pad or leaves fixedD50')
        covered.add((i,j));rows.append((p,i,j,a))
    rows.sort(key=lambda r:(r[0],r[2],r[1]))
    counts=[sum(p==pad for p,_,_,_ in rows) for pad in range(4)]
    areas=[math.fsum(a for p,_,_,a in rows if p==pad) for pad in range(4)]
    core.require(counts==[720,720,432,432] and all(abs(a/(v*1e-6)-1)<=1e-10 for a,v in
        zip(areas,(281.25,281.25,168.75,168.75))), 'Physical counts or900mm2 allocation changed')
    for p in (0,1,3):
        core.require([r for r in rows if r[0]==p] == [r for r in source_rows if r[0]==p], 'Unrotated mask rows must remain exact')
    return rows,areas,dict(rule='exact-pad2-face-index-plus90deg-permutation-v1',h_xy_mm=h,
        rotated_physical_pad_id=2,applied_physical_rotation_deg=90,operative_rotation_deg=0,
        centre_mm=[10.,-10.],old_width_height_mm=[15.,11.25],new_width_height_mm=[11.25,15.],
        old_to_new_indices='pad2:(i,j)->(79-j,i-32); inverse(i_new,j_new)->(j_new+32,79-i_new)',
        faces_per_pad=counts,contacts=2304,represented_pad_areas_m2=areas,physical_total_contact_area_mm2=900.,
        unchanged_physical_pads=[0,1,3],contact_area_values_preserved=True,partial_faces=0,
        clipping=False,renormalization=False,mesh_convergence_claimed=False)


def changed_rotation_config(data,path,sha):
    before=_properties(data)
    core.require(float(before['pad.2.width_mm'])==15 and float(before['pad.2.height_mm'])==11.25 and
        float(before['pad.2.rotation_deg'])==0 and float(before['pad.2.x_mm'])==10 and
        float(before['pad.2.y_mm'])==-10 and before['pad.2.shape']=='rectangle', 'Completed parent pad2 rectangle descriptor required')
    changes={'mask.path':str(path),'mask.sha256':sha,'pad.2.width_mm':'11.25','pad.2.height_mm':'15.0'}
    return _changed_config(data,changes),changes


def verify_context(decision_path,feedback_path):
    pins={}
    def pin(path,expected=None):
        p=Path(path);core.require(p.is_absolute() and p==p.resolve() and p.is_relative_to(core.REPO) and
            p.is_file() and not p.is_symlink(),'Canonical local metadata context required')
        digest=core.sha(p);core.require(expected is None or digest==expected,'Context SHA differs');pins[str(p)]=digest
        return p,core.read(p)
    dp,decision=pin(decision_path)
    core.require(decision.get('schema')=='task1-one-return-rotation-root-decision-v1' and
        decision.get('status')=='selected_not_executed' and decision.get('case_id')==CASE_ID and
        decision.get('source_run_id')==SOURCE_RUN and decision.get('source_case_id')==SOURCE_ID and
        isinstance(decision.get('question'),str) and bool(decision['question'].strip()) and
        decision.get('rotated_physical_pad_id')==2 and decision.get('physical_rotation_deg')==90 and
        decision.get('new_PDE')==1 and decision.get('new_native_RHS')==8 and decision.get('independent_outputs')==2 and
        decision.get('physical_pads')==4 and decision.get('fixed_total_area_mm2')==900 and decision.get('candidate_adopted') is False and
        decision.get('root_selected') is True and decision.get('peer_endorsed') is False,'Explicit root-selected one-pad rotation decision required')
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
        for c in comments),'Latest signed-output/circuit feedback6321929825 must be present')
    for path,digest in decision.get('input_sha256',{}).items():
        core.require(Path(path).suffix in ('.json','.md'),'Metadata-only decision evidence required');pin(path,digest)
    return dict(path=str(dp),SHA256=pins[str(dp)],question=decision['question'],root_selected=True,peer_endorsed=False),dict(
        path=str(fp),SHA256=pins[str(fp)],observed_utc=feedback['observed_utc'],public_GET_checked=True,
        public_comment_identity_and_body_sha256=comments,root_selected_geometry=True,peer_rotation_endorsement=False),pins


def prepare_one_return_rotation(run,decision_path,feedback_path):
    started=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run==run.resolve() and not run.exists(),'New canonical unique one-return-rotation run required')
    _caller_owns_execution_lock();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    budget_path=core.REPO/'runtime/task1-budget.json';budget=policy.load_ledger(budget_path);limit=policy.effective_limit(budget)
    core.require(limit==13800 and limit-budget['spent_seconds']>=MIN_REMAINING_SECONDS,'Approved13800s policy with1320s finite queue reserve required')
    decision,feedback,pins=verify_context(Path(decision_path).absolute(),Path(feedback_path).absolute())
    pins.update(core.source_pins(budget))
    for p in (Path(__file__).resolve(),core.REPO/'tests/test_task1_one_return_rotation_registration.py',
        Path(asym.__file__).resolve(),Path(contact.__file__).resolve(),VOLUME):pins[str(p)]=core.sha(p)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=core.REPO,text=True).strip()
    for name,digest in pins.items():
        p=Path(name);core.require(core.sha(p)==digest,'Pinned source/context changed: '+name)
        if p.suffix in ('.py','.java'):
            core.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(core.REPO))],cwd=core.REPO)==p.read_bytes(),
                'Commit all consumed implementation sources/tests before preparation: '+name)
    limits=core.effective_limits(budget)
    core.require(EXPECTED_RAW_BOUND_BYTES==EXPECTED_CELLS*600<=limits['max_batch_added_bytes'] and
        shutil.disk_usage(run.parent).free>2*core.GIB+EXPECTED_RAW_BOUND_BYTES,'Single raw basis plus2GiB reserve unavailable')
    run.mkdir();success=False;registration=None
    try:
        for d in ('configs','masks','bases','cases','postprocess','logs','classes','geometry-audit'):(run/d).mkdir()
        def guard(phase):
            elapsed=time.monotonic()-started;remaining=min(PREPARATION_SECONDS-elapsed,limit-budget['spent_seconds']-elapsed-1200)
            core.require(remaining>0 and core.rss(os.getpid())<3*core.GIB and shutil.disk_usage(run).free>=2*core.GIB,
                'Preparation120s/RSS/reserve exhausted at '+phase)
            core.write(run/'controller.json',dict(status='preparing',phase=phase,pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),
                updated_utc=core.now(),elapsed_seconds=elapsed));return remaining
        guard('original_and_parent_integrity');integrity=core.original_integrity();volume=core.read(VOLUME)
        core.require(volume['status']=='calculated_unadopted' and volume['inputs_unchanged'] is True,'Completed unchanged asymmetric parent/control volume required')
        source,old_config,old_mask,spins=contact._source_case(core,SOURCE_RUN,SOURCE_ID,volume);pins.update(spins)
        baseline,base_config,base_mask,bpins=contact._source_case(core,BASE_RUN,BASE_ID,volume);pins.update(bpins)
        core.require(source['source_coating_nm']==10 and source['source_Rs_fit_window_Hz']==500,'NominalPBS10nm/Rs500 parent required')
        src,base=_properties(old_config.read_bytes()),_properties(base_config.read_bytes())
        core.require({k:v for k,v in src.items() if k.startswith('z.') or k.endswith(('.sigma','.epsilon_r'))}==
            {k:v for k,v in base.items() if k.startswith('z.') or k.endswith(('.sigma','.epsilon_r'))},'Parent/baseline contact/tissue physics differs')
        source_rows=[(int(r['pad']),int(r['i']),int(r['j']),float(r['area_m2'])) for r in csv.DictReader(io.StringIO(old_mask.read_text()))]
        design=rotated_design(source['design']);rows,areas,proof=rotate_mask(source_rows)
        core.require(areas==[math.fsum(a for p,_,_,a in source_rows if p==pad) for pad in range(4)],'Rotation must preserve exact represented areas')
        mask=run/'masks'/(CASE_ID+'.csv');mask.write_bytes(_mask_bytes(rows))
        config=run/'configs'/(CASE_ID+'.properties');data,changes=changed_rotation_config(old_config.read_bytes(),mask,core.sha(mask));config.write_bytes(data)
        core.write(run/'geometry-audit/rotated-design.json',design);core.write(run/'geometry-audit/rotation-mask-proof.json',proof)
        case=copy.deepcopy(source)
        case.update(id=CASE_ID,design_id=design['id'],design=design,source_run_id=run.name,
            config_file=str(config),config_sha256=core.sha(config),mask_file=str(mask),mask_sha256=core.sha(mask),expected_pad_areas_m2=areas,
            applied_physical_rotation_deg=90,rotated_physical_pad_id=2,operative_config_rotation_deg=0,rotation_only_contrast=True,
            physical_total_contact_area_mm2=900.,n_pads=4,n_outputs=2,channels=2,
            prototype_reference=dict(run_id=SOURCE_RUN,case_id=SOURCE_ID,config_file=str(old_config),config_sha256=core.sha(old_config)),
            historical_parent_original_prototype=source.get('prototype_reference'),
            baseline_same_grid_reference=dict(run_id=BASE_RUN,case_id=BASE_ID,config_file=str(base_config),config_sha256=core.sha(base_config)),
            source_parent_combined_shape_area_allocation=True,combined_geometry_and_area_allocation=False,isolated_area_effect_claimed=False,
            status='preregistered_not_executed',candidate_adopted=False,mesh_convergence_validated=False,existing_XY_contact_model_holds_preserved=True)
        case.update(_mesh(case));core.require(case['cells']==EXPECTED_CELLS,'351680cell mesh changed')
        case['cache_signature']=core.check_cached_operator(case,run)
        jdk=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin');javac=shutil.which('javac') or str(jdk/'javac')
        java=str(Path(javac).resolve().parent/'java');core.require(Path(javac).is_file() and Path(java).is_file(),'Matching installed Java compiler/runtime required')
        with (run/'logs/compile-selftest.log').open('x') as log:
            def command(args):subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=guard('compile_or_analytic_selftest'))
            command([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(run/'classes'),str(core.SOURCE/'TisSweep.java'),
                str(core.SOURCE/'ExploreBasis.java'),str(core.SOURCE/'SelectivityShapeBasis.java'),str(core.REPO/'tools/java/CloudShapeBasis.java')])
            command([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),'CloudShapeBasis','--selftest'])
        for d in ('configs','masks','classes','geometry-audit'):
            for p in (run/d).iterdir():pins[str(p)]=core.sha(p)
        for p,digest in pins.items():core.require(core.sha(p)==digest,'Pinned one-return-rotation input changed: '+p)
        guard('final_integrity')
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='one_asymmetric_parent_return_pad2_rotation',status='prepared',
            created_utc=core.now(),source_commit=commit,package_integrity=integrity,limits=limits,gates=copy.deepcopy(core.GATES),cases=[case],java=java,
            new_PDE_conditions_maximum=1,new_native_RHS_maximum=8,expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,source_and_input_sha256=pins,
            preparation_seconds=time.monotonic()-started,root_selection_decision=decision,source_feedback=feedback,
            resource_policy_immutable_refs=policy.policy_refs(budget),
            scientific_question='Rotate only physical commonGNDpad2 by90deg at fixed centre/area, asking whether targetmean/P10 survive while surface/complement modulation falls at common original-square caps',
            unchanged_controls=[dict(run_id=BASE_RUN,case_id=BASE_ID,new_PDE=0),dict(run_id=SOURCE_RUN,case_id=SOURCE_ID,new_PDE=0)],
            path_mapping=[dict(original_config=str(old_config),original_sha256=core.sha(old_config),new_config=str(config),new_sha256=core.sha(config),
                changed_fields=list(changes),electrical_contact_tissue_mesh_frequency_changed_fields=[],
                geometry_is_explicit_mask=True,rotation_encoded_once_by_axis_dimension_swap=True)],
            planned_normalizations=['raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin'],
            comparison_waveforms=['square_3h','sine','triangle_3h'],fixed_cutoffs_V_m=dict(baseline_mean=4.061848941601601,baseline_p10=3.6457357391300533),
            fixed_ROIs='Primaryr<=5mm depth15..20; supplementarywholeXYsame-depth; surface0..5 and bothcomplements',
            root_full_skin_reserve_seconds=180,root_volume_reserve_seconds=180,root_probe_reserve_seconds=120,root_UI_reserve_seconds=120,
            preparation_max_seconds=120,queue_max_seconds=1320,candidate_adopted=False,mesh_convergence_validated=False,experimental_validation=False,
            existing_XY_contact_model_holds_preserved=True,peer_rotation_endorsement=False,
            contact_uncertainty='Unchanged nominalPBS specificZ: one originalRs subtraction/area conversion; actualskincontact unvalidated',
            frozen_source_snapshot_owner='Standalone CLI freezes once under both global execution locks',
            storage=dict(native_location=str(run),persistent_backup_verified=False,retirement_of_old_environment_allowed=False),
            next_decision='One newnative8RHS only, thenfullskin/probe40/volume5modes/fixed8screens; no adoption orautomaticrefinement from one orientation contrast')
        core.write(run/'preregistration.json',registration);core.write(run/'controller.json',dict(status='prepared',updated_utc=core.now()));success=True
    except BaseException as error:
        core.write(run/'preparation-failure.json',dict(status='preparation_failed_preserved',error_type=type(error).__name__,error=str(error),
            observed_utc=core.now(),partial_evidence_preserved=True,automatic_retry=False));raise
    finally:
        elapsed=time.monotonic()-started;budget['spent_seconds']+=elapsed
        budget['runs'].append(dict(run_id=run.name,stage='preparation',seconds=elapsed,status='prepared' if success else 'preparation_failed_preserved'))
        core.write(budget_path,budget)
    return registration


def main():
    import argparse
    import fcntl
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true',required=True)
    for name in ('output','decision','feedback'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    with (core.REPO/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=prepare_one_return_rotation(args.output,args.decision,args.feedback);core.freeze_sources(args.output.resolve())
    print(dict(status=result['status'],run=str(args.output),case_id=CASE_ID))


if __name__=='__main__':main()
