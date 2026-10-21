"""Register one fixed stepped perimeter union; no work occurs on import.

One8-RHS native condition, four physical225mm2 pads, two outputs/commonGND.
The contour is a frozen union of full native faces, not a smooth annular arc.
"""
from __future__ import annotations
import copy
import csv
import functools
import io
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import task1_cloud_batch as core
import task1_resource_policy as policy
import task1_contact_sensitivity_registration as contact
from task1_grouped_registration import _caller_owns_execution_lock,_mesh
from task1_reference_registration import _changed_config,_properties
CASE_ID='perimeter-shell225-notch-xy80'
SOURCE_RUN=BASE_RUN='cloud-mesh-c1-20261019T190000Z'
SOURCE_ID=BASE_ID='baseline-square15-xy80'
VOLUME=core.REPO/'docs/cloud-tangential-return-context-20261021T183000Z/volume.json'
EXPECTED_CELLS=351680
EXPECTED_RAW_BOUND_BYTES=211008000
MIN_REMAINING_SECONDS=1320
PREPARATION_SECONDS=120
H=.625
REQUIRED_CONTEXT={
 'docs/cloud-rotation-coherent-20261021T182000Z/summary.json':('task1-rotation-coherent-scout-v1','calculated_unadopted'),
 'docs/cloud-rotation-amplitude-bounds-20261021T181000Z/summary.json':('task1-rotation-amplitude-bounds-v1','completed_bounds_diagnostic'),
 'docs/cloud-tangential-return-context-20261021T183000Z/volume.json':('task1-volume-selectivity-v1','calculated_unadopted'),
 'docs/cloud-tangential-return-context-20261021T183000Z/screen.json':('task1-candidate-screen-v1','screen_complete_not_adopted'),
}


def _mask_bytes(rows):
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n')
    writer.writerow(['pad','i','j','area_m2'])
    for p,i,j,a in rows:writer.writerow([p,i,j,format(a,'.17g')])
    return stream.getvalue().encode()


def components(cells):
    unseen=set(cells);sizes=[]
    while unseen:
        todo=[unseen.pop()];n=0
        while todo:
            i,j=todo.pop();n+=1
            for q in((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                if q in unseen:unseen.remove(q);todo.append(q)
        sizes.append(n)
    return sorted(sizes,reverse=True)


def hole_cells(cells):
    lowx=min(i for i,j in cells)-1;highx=max(i for i,j in cells)+1
    lowy=min(j for i,j in cells)-1;highy=max(j for i,j in cells)+1
    empty={(i,j)for i in range(lowx,highx+1)for j in range(lowy,highy+1)}-set(cells)
    todo=[(lowx,lowy)];outside=set()
    while todo:
        p=todo.pop()
        if p in outside:continue
        outside.add(p);i,j=p
        todo.extend(q for q in((i-1,j),(i+1,j),(i,j-1),(i,j+1))if q in empty and q not in outside)
    return empty-outside


def boundary_loop(cells):
    """Cancel shared native edges; preserve the actual nonconvex physical loop."""
    edges=set()
    for i,j in cells:
        corners=((i,j),(i+1,j),(i+1,j+1),(i,j+1))
        for a,b in zip(corners,corners[1:]+corners[:1]):
            if(b,a)in edges:edges.remove((b,a))
            else:edges.add((a,b))
    following={}
    for a,b in edges:
        core.require(a not in following,'Ambiguous point-touch physical boundary')
        following[a]=b
    start=min(following);loop=[start];current=following[start]
    while current!=start:
        core.require(current not in loop and len(loop)<=len(edges),'Non-simple physical boundary')
        loop.append(current);current=following[current]
    core.require(len(loop)==len(edges),'Multiple physical loops or hole')
    area=sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(loop,loop[1:]+loop[:1]))/2
    core.require(area==len(cells),'Physical outline area differs from full-face union')
    return[[-25+i*H,-25+j*H]for i,j in loop]


def rotate90(cells):return{(79-j,i)for i,j in cells}


@functools.lru_cache(maxsize=1)
def shell_faces():
    """Only defines this original contour; future grids must not rerank cells."""
    candidate={(i,j)for i in range(43,80)for j in range(43,80)if
        all((-25+ii*H)**2+(-25+jj*H)**2<625 for ii in(i,i+1)for jj in(j,j+1))}
    radius=lambda p:(2*p[0]-79)**2+(2*p[1]-79)**2
    prefix={p for p in candidate if radius(p)>2890};ties={p for p in candidate if radius(p)==2890}
    core.require(len(candidate)==989 and len(prefix)==571 and len(ties)==6 and(67,67)in prefix,'Frozen shell construction changed')
    northeast=(prefix|ties)-{(67,67)}
    core.require(len(northeast)==576 and northeast=={(j,i)for i,j in northeast},'Exact225mm2 and diagonal symmetry required')
    northwest=rotate90(northeast);southwest=rotate90(northwest);southeast=rotate90(southwest)
    pads=(southwest,northeast,southeast,northwest)
    core.require(len(set.union(*pads))==2304,'Physical pads overlap')
    core.require(all(components(p)==[576]and not hole_cells(p)for p in pads),'Each pad must be one component with no holes')
    core.require(all((-25+ii*H)**2+(-25+jj*H)**2<625 for p in pads for i,j in p for ii in(i,i+1)for jj in(j,j+1)),
        'Physical full contact face outside fixedD50')
    return tuple(tuple(sorted(p,key=lambda ij:(ij[1],ij[0])))for p in pads)


def shell_design(baseline):
    core.require(baseline['id']=='baseline-square15'and baseline['phantom_diameter_mm']==50 and baseline['contact_plane_z_mm']==0 and
        baseline['total_pads']==4 and baseline['source_outputs']==2 and baseline['return_connection']=='all_return_pads_ideal_common_GND'and
        len(baseline['pads'])==4,'Exact original square physical baseline required')
    design=copy.deepcopy(baseline);faces=shell_faces();area=(H/1000)**2;rows=[];centroids=[]
    for p,(pad,cells,oldcentre)in enumerate(zip(design['pads'],faces,((-10.,-10.),(10.,10.),(10.,-10.),(-10.,10.)))):
        core.require(pad['pad']==p and tuple(pad['center_mm'])==oldcentre and pad['shape']=='rectangle'and pad['width_mm']==pad['height_mm']==15 and
            pad['rotation_deg']==0 and pad['analytic_area_mm2']==225 and pad['role']==('signal'if p<2 else'common_gnd_return')and
            pad['source_output']==(p if p<2 else None),'Original square shape/area/identity/wiring required')
        loop=boundary_loop(cells);cx=math.fsum(-25+(i+.5)*H for i,j in cells)/576;cy=math.fsum(-25+(j+.5)*H for i,j in cells)/576
        xmin=min(-25+i*H for i,j in cells);xmax=max(-25+(i+1)*H for i,j in cells)
        ymin=min(-25+j*H for i,j in cells);ymax=max(-25+(j+1)*H for i,j in cells)
        centroids.append([cx,cy]);rows.extend((p,i,j,area)for i,j in cells)
        pad.update(shape='masked_face_union',geometry_primitive='fixed_union_of_native_full_face_rectangles',center_mm=[cx,cy],centroid_mm=[cx,cy],
            width_mm=xmax-xmin,height_mm=ymax-ymin,rotation_deg=0.,corner_radius_mm=0.,
            dimension_fields_role='Bounding-box extents only; centroid differs from bbox centre; not rectangle contact',
            bounding_box_mm=[xmin,ymin,xmax,ymax],bounding_box_center_mm=[(xmin+xmax)/2,(ymin+ymax)/2],
            area_mm2=225.,analytic_area_mm2=225.,polygon_area_mm2=225.,polygon_mm=loop,boundary_loops_mm=[loop],
            boundary_loop_closure='Implicit final-to-first; CCW physical outer loop; no holes',native_face_indices=[list(ij)for ij in cells],
            native_face_h_mm=H,native_face_lower_corner_origin_mm=[-25.,-25.],native_face_count=576,
            union_rectangles_mm=[dict(center_mm=[-25+(i+.5)*H,-25+(j+.5)*H],width_mm=H,height_mm=H)for i,j in cells],
            physical_outline_frozen=True,smooth_annular_arc_claimed=False,convex_hull_used=False)
    gaps=[]
    for p in range(4):
        for q in range(p+1,4):
            squared=min(max(abs(i-k)-1,0)**2+max(abs(j-l)-1,0)**2 for i,j in faces[p]for k,l in faces[q])
            gaps.append(dict(pad_a=p,pad_b=q,gap_mm=H*math.sqrt(squared)))
    core.require(min(g['gap_mm']for g in gaps)==3.75,'Fixed physical gap changed')
    maximum=max(x*x+y*y for p in design['pads']for x,y in p['polygon_mm']);core.require(maximum==623.828125,'Fixed rim corner changed')
    common=dict(geometry_kind='fixed_native_face_union',combined_geometry_and_placement=True,isolated_shape_effect_claimed=False,
        native_full_face_contact=True,physical_total_contact_area_mm2=900.,minimum_physical_gap_mm=3.75,minimum_gap_XY_cells=6,
        maximum_physical_vertex_radius_squared_mm2=maximum,rim_clearance_mm=25-math.sqrt(maximum),physical_geometry_frozen=True,
        future_grid_reranking_allowed=False,strict_outermost576_claimed=False)
    design.update(**common,id=CASE_ID.removesuffix('-xy80'),group='fixed_stepped_perimeter_shell_combined_shape_placement',xy_mm=centroids,
        minimum_gap_mm=3.75,verified_physical_gaps_mm=gaps,geometry_revision='perimeter-shell225-outer-diagonal-notch-v1',
        area_policy='Original225mm2 each/900mm2 total; contact outline andplacement change together',
        rim_clearance_hold='Only0.02344849664mm to idealrim; outer staircase/edge/contact uncertainty remains',
        fixed_outline_regeneration_policy='Intersect frozen physical boundary loops at future grids; never rerun radial ranking as refinement')
    proof=dict(**common,rule='fixed-Q1-radial-prefix-all6ties-minus-outermost-diagonal-rotated-union-v1',h_xy_mm=H,
        faces_per_pad=[576]*4,contacts=2304,represented_pad_areas_m2=[math.fsum(area for _ in p)for p in faces],full_face_area_m2=area,
        partial_faces=0,clipping=False,renormalization=False,components_per_pad=[1]*4,holes_per_pad=[0]*4,pad_centroids_mm=centroids,
        verified_physical_gaps_mm=gaps,boundary_loop_count_per_pad=[1]*4,x_y_reflection_each_quadrant=True,quarter_turn_symmetry=True,
        mesh_convergence_claimed=False,construction=dict(quarter_candidate_count=989,prefix_count_above_cutoff=571,
            cutoff_center_radius_squared_integer=2890,cutoff_tie_faces_all=6,removed_Q1_face=[67,67],removed_face_is_outer_boundary_notch=True,
            rejected_innermost_diagonal_face=[59,59],rejected_reason='Creates one enclosed4-neighbour complement hole',
            pad_quadrants=['SW','NE','SE','NW'],pad_Q1_quarter_turns=[2,0,3,1]))
    return design,rows,proof['represented_pad_areas_m2'],proof


def changed_shell_config(data,design,path,sha):
    before=_properties(data);changes={'mask.path':str(path),'mask.sha256':sha}
    for p,pad in enumerate(design['pads']):
        core.require(before[f'pad.{p}.shape']=='rectangle'and float(before[f'pad.{p}.width_mm'])==15 and
            float(before[f'pad.{p}.height_mm'])==15 and float(before[f'pad.{p}.rotation_deg'])==0 and
            float(before[f'pad.{p}.analytic_area_mm2'])==225,'Original square config geometry required')
        changes.update({f'pad.{p}.shape':'masked_face_union',f'pad.{p}.width_mm':str(pad['width_mm']),
            f'pad.{p}.height_mm':str(pad['height_mm']),f'pad.{p}.x_mm':format(pad['center_mm'][0],'.17g'),f'pad.{p}.y_mm':format(pad['center_mm'][1],'.17g')})
    return _changed_config(data,changes),changes


def verify_context(decision_path,feedback_path):
    pins={}
    def pin(path,expected=None):
        p=Path(path);core.require(p.is_absolute() and p==p.resolve() and p.is_relative_to(core.REPO) and
            p.is_file() and not p.is_symlink(),'Canonical local metadata context required')
        digest=core.sha(p);core.require(expected is None or digest==expected,'Context SHA differs');pins[str(p)]=digest
        return p,core.read(p)
    dp,decision=pin(decision_path)
    core.require(decision.get('schema')=='task1-perimeter-shell-root-decision-v1' and
        decision.get('status')=='selected_not_executed' and decision.get('case_id')==CASE_ID and
        decision.get('source_run_id')==SOURCE_RUN and decision.get('source_case_id')==SOURCE_ID and
        isinstance(decision.get('question'),str)and bool(decision['question'].strip())and
        decision.get('selected_variant')=='radial_prefix_all_cutoff_ties_minus_outermost_diagonal'and
        decision.get('removed_Q1_face')==[67,67]and decision.get('cutoff_center_radius_squared_integer')==2890 and
        decision.get('minimum_gap_mm')==3.75 and decision.get('maximum_corner_radius_squared_mm2')==623.828125 and
        decision.get('new_PDE')==1 and decision.get('new_native_RHS')==8 and decision.get('independent_outputs')==2 and
        decision.get('physical_pads')==4 and decision.get('fixed_total_area_mm2')==900 and decision.get('candidate_adopted')is False and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False,
        'Exact root-selected fixed stepped perimeter shell decision required')
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
    for relative,(schema,status)in REQUIRED_CONTEXT.items():
        path=core.REPO/relative
        core.require(str(path)in decision.get('input_sha256',{}),'Missing completed source context: '+relative)
        obj=core.read(path)
        core.require(obj.get('schema')==schema and obj.get('status')==status and
            (schema=='task1-candidate-screen-v1' or obj.get('inputs_unchanged')is True),
            'Completed unchanged scientific context required: '+relative)
        if schema=='task1-candidate-screen-v1':
            target=core.REPO/'docs/cloud-tangential-return-context-20261021T183000Z/volume.json'
            core.require(obj.get('input_volume_report')==dict(path=str(target),SHA256=pins[str(target)]),
                'Completed screen must bind the exact unchanged source volume')
        if 'coherent-'in relative:
            core.require(obj.get('new_PDE')==0 and len(obj.get('conditions',[]))==5 and
                all(c.get('status')=='calculated_unadopted' and c.get('canonical_screen_all_passed')is False for c in obj['conditions']),
                'All five actual completed unadopted coherent controls required')
    return dict(path=str(dp),SHA256=pins[str(dp)],question=decision['question'],root_selected=True,peer_endorsed=False),dict(
        path=str(fp),SHA256=pins[str(fp)],observed_utc=feedback['observed_utc'],public_GET_checked=True,
        public_comment_identity_and_body_sha256=comments,root_selected_geometry=True,peer_geometry_endorsement=False),pins


def bounded_command(argv,log,guard):
    """One installed Java process; inherited1CPU, own group, no orphan/retry."""
    child=None
    try:
        allowance=guard('compile_or_analytic_selftest')
        child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,stdin=subprocess.DEVNULL)
        while True:
            core.require(core.rss(os.getpid())+core.rss(child.pid)<3*core.GIB,'Preparation aggregateRSS3GiB exceeded')
            try:
                code=child.wait(timeout=min(5.,allowance))
                core.require(code==0,'Preparation Java exit '+str(code));return
            except subprocess.TimeoutExpired:
                allowance=guard('compile_or_analytic_selftest_heartbeat')
    finally:
        if child is not None and child.poll()is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)


def prepare_perimeter_shell(run,decision_path,feedback_path):
    started=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run==run.resolve() and not run.exists() and
        not run.with_name(run.name+'.preparation-failure.json').exists(),
        'New canonical unique perimeter-shell run required; preserve failed run IDs')
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
        for p in (Path(__file__).resolve(),core.REPO/'tests/test_task1_perimeter_shell_registration.py',
            Path(contact.__file__).resolve(),VOLUME):pins[str(p)]=core.sha(p)
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
        design,rows,areas,proof=shell_design(source['design'])
        mask=run/'masks'/(CASE_ID+'.csv');mask.write_bytes(_mask_bytes(rows))
        config=run/'configs'/(CASE_ID+'.properties');data,changes=changed_shell_config(old_config.read_bytes(),design,mask,core.sha(mask));config.write_bytes(data)
        core.write(run/'geometry-audit/perimeter-design.json',design);core.write(run/'geometry-audit/perimeter-mask-proof.json',proof)
        case=copy.deepcopy(source)
        case.update(id=CASE_ID,design_id=design['id'],design=design,source_run_id=run.name,
            config_file=str(config),config_sha256=core.sha(config),mask_file=str(mask),mask_sha256=core.sha(mask),expected_pad_areas_m2=areas,
            geometry_kind='fixed_native_face_union',combined_geometry_and_placement=True,isolated_shape_effect_claimed=False,
            native_full_face_contact=True,minimum_physical_gap_mm=3.75,minimum_gap_XY_cells=6,
            maximum_physical_vertex_radius_squared_mm2=623.828125,rim_clearance_mm=25-math.sqrt(623.828125),
            physical_geometry_frozen=True,future_grid_reranking_allowed=False,strict_outermost576_claimed=False,
            physical_total_contact_area_mm2=900.,n_pads=4,n_outputs=2,channels=2,
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
        for p,digest in pins.items():core.require(core.sha(p)==digest,'Pinned perimeter-shell input changed: '+p)
        guard('final_integrity')
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='one_fixed_stepped_perimeter_shell',status='prepared',
            created_utc=core.now(),source_commit=commit,package_integrity=integrity,limits=limits,gates=copy.deepcopy(core.GATES),cases=[case],java=java,
            new_PDE_conditions_maximum=1,new_native_RHS_maximum=8,expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,source_and_input_sha256=pins,
            preparation_seconds=time.monotonic()-started,root_selection_decision=decision,source_feedback=feedback,
            resource_policy_immutable_refs=policy.policy_refs(budget),
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
            next_decision='One newnative8RHS only, thenfullskin/probe40/volume5modes/fixed8screens; no adoption orautomaticrefinement from one combined contactshape andplacement contrast')
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
        result=prepare_perimeter_shell(args.prepare,args.decision,args.feedback)
    print(dict(status=result['status'],run=str(args.prepare),case_id=CASE_ID))


if __name__=='__main__':main()
