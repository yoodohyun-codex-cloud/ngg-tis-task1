"""Two inward source-position contrasts; outward geometry is infeasible at D50.

Import has no computation side effects. Only the root may prepare the fixed
two-case family under both global locks; the existing controller executes PDEs.
"""
from __future__ import annotations

import copy
import csv
import io
import math
import os
from pathlib import Path
import shutil
import subprocess
import time

import task1_cloud_batch as core
import task1_resource_policy as policy
import task1_asymmetric_registration as asym
import task1_contact_sensitivity_registration as contact
from task1_grouped_registration import _caller_owns_execution_lock,_mesh
from task1_reference_registration import _changed_config,_properties

CASE_IDS=('asym-source-in0p625-xy80','asym-source-in1p25-xy80')
DELTAS=(-.625,-1.25)
EXPECTED_CELLS=351680
EXPECTED_RAW_BOUND_BYTES=422016000
MIN_REMAINING_SECONDS=1800
SOURCE_RUN='cloud-asymmetric-20261021T051000Z'
SOURCE_ID=asym.CASE_ID
VOLUME=core.REPO/'docs/cloud-continuation-20261021/volume-asymmetric.json'
NATIVE_AUDIT=core.REPO/'docs/cloud-continuation-20261021/native-causal-20261021T085900Z/result.json'
CARRIER_AUDIT=core.REPO/'docs/cloud-next-20261021T085200Z/carrier-balance-20261021T091500Z/result.json'
FEEDBACK=core.REPO/'docs/cloud-extended-20261021T102700Z/feedback-before.json'
RETURN_IDS=('asym-return-out0p625-xy80','asym-return-in0p625-xy80')


def _mask_bytes(rows):
    """Exact existing native CSV contract, without an unselected helper import."""
    stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n')
    writer.writerow(['pad','i','j','area_m2'])
    for pad,i,j,area in rows:writer.writerow([pad,i,j,format(area,'.17g')])
    return stream.getvalue().encode('utf-8')


def _delta(delta):
    core.require(type(delta) in (int,float) and delta in DELTAS,'Only inward source-coordinate shifts minus0.625/minus1.25mm are allowed; outward is infeasible')
    return int(delta/.625)


def outward_rejection_proof():
    x,y=19.375,16.875
    return dict(status='rejected_outside_fixed_D50',requested_coordinate_shift_mm=.625,
        physical_cross_vertex_xy_mm=[x,y],vertex_radius_squared_mm2=x*x+y*y,
        fixed_radius_squared_mm2=625.,fixed_diameter_mm=50.,
        maximum_continuous_outward_coordinate_shift_mm=(-70+math.sqrt(4975))/4,
        positive_h0p625_integer_outward_step_exists=False,geometry_clipped=False,area_renormalized=False,
        reason='Real cross vertex exceeds D50; preserve fixed shape/area/domain and register only authorized inward levels')


def translated_design(source_design,delta):
    _delta(delta);asym.aligned_mixed_mask(source_design)
    design=copy.deepcopy(source_design)
    for pad,dx,dy in ((0,-delta,-delta),(1,delta,delta)):
        p=design['pads'][pad];p['center_mm']=[p['center_mm'][0]+dx,p['center_mm'][1]+dy]
        p['polygon_mm']=[[x+dx,y+dy]for x,y in p['polygon_mm']]
        for rectangle in p['union_rectangles_mm']:
            rectangle['center_mm']=[rectangle['center_mm'][0]+dx,rectangle['center_mm'][1]+dy]
    core.require(all(x*x+y*y<625 for p in design['pads']for x,y in p['polygon_mm']), 'Translated source physical outline outside fixedD50')
    gaps=dict(source_return_horizontal=3.75+delta,source_return_vertical=5.625+delta,
              source_source_diagonal=math.sqrt(2)*(5+2*delta))
    core.require(all(value>0 for value in gaps.values()),'Physical source/return contacts must remain separated')
    design.update(id=CASE_IDS[DELTAS.index(delta)].removesuffix('-xy80'),
        group='source_position_only_fixed_asymmetric_geometry',xy_mm=[p['center_mm']for p in design['pads']],
        source_coordinate_shift_mm=delta,source_radial_distance_change_mm=math.sqrt(2)*delta,
        minimum_gap_mm=3.75+delta,geometry_revision='fixed-return-source-inward-diagonal-translation-v1',
        verified_physical_gaps_mm=gaps,
        area_policy='Unchanged281.25/281.25/168.75/168.75mm2 pads; only source centres move')
    return design


def _source_face_keys():
    expected=set()
    for p,centre in ((0,24),(1,56)):
        for width,height in ((28,20),(20,28)):
            expected.update((p,i,j)for j in range(centre-height//2,centre+height//2)
                for i in range(centre-width//2,centre+width//2))
    expected.update((2,i,j)for j in range(15,33)for i in range(44,68))
    expected.update((3,i,j)for j in range(47,65)for i in range(12,36))
    return expected


def translated_mask(source_rows,delta):
    step=_delta(delta);h=.625;face=(h/1000)**2
    core.require(len(source_rows)==2304 and len({(p,i,j)for p,i,j,_ in source_rows})==2304 and
        {(p,i,j)for p,i,j,_ in source_rows}==_source_face_keys() and
        all(a==face and type(p) is int and type(i) is int and type(j) is int for p,i,j,a in source_rows),
        'Only the exact full-face completed asymmetric source mask can be translated')
    rows=[];covered=set()
    for p,i,j,a in source_rows:
        if p==0:i,j=i-step,j-step
        elif p==1:i,j=i+step,j+step
        core.require(0<=i<80 and 0<=j<80 and (i,j)not in covered and
            all((-25+ii*h)**2+(-25+jj*h)**2<625 for ii in (i,i+1)for jj in (j,j+1)),
            'Source translation overlaps a pad or leaves fixedD50')
        covered.add((i,j));rows.append((p,i,j,a))
    counts=[sum(p==pad for p,_,_,_ in rows)for pad in range(4)]
    areas=[math.fsum(a for p,_,_,a in rows if p==pad)for pad in range(4)]
    core.require(counts==[720,720,432,432] and all(abs(a/(v*1e-6)-1)<=1e-10
        for a,v in zip(areas,(281.25,281.25,168.75,168.75))), 'Fixed900mm2 physical contact allocation changed')
    return rows,areas,dict(rule='exact-full-face-source-index-translation-v1',h_xy_mm=h,
        delta_coordinate_mm=delta,source_radial_distance_change_mm=math.sqrt(2)*delta,
        physical_pad_index_offsets={'0':[-step,-step],'1':[step,step],'2':[0,0],'3':[0,0]},
        faces_per_pad=counts,contacts=len(rows),represented_pad_areas_m2=areas,physical_total_area_mm2=900.,
        return_rows_unchanged=True,partial_faces=0,discarded_slivers=0,renormalization=False,
        physical_shape_size_rotation_wiring_changed=False,mesh_convergence_claimed=False)


def changed_position_config(data,path,sha,delta):
    _delta(delta)
    before=_properties(data)
    for p,(x,y)in ((0,(-10.,-10.)),(1,(10.,10.))):
        core.require(float(before[f'pad.{p}.x_mm'])==x and float(before[f'pad.{p}.y_mm'])==y,
                     'Original source centres must remain the completed asymmetric control')
    changes={'mask.path':str(path),'mask.sha256':sha,'pad.0.x_mm':str(-10-delta),
        'pad.0.y_mm':str(-10-delta),'pad.1.x_mm':str(10+delta),'pad.1.y_mm':str(10+delta)}
    return _changed_config(data,changes),changes


def verify_root_decision(path):
    """A proposal cannot prepare until both actual return cases are analyzed."""
    path=Path(path)
    core.require(path.is_absolute() and path==path.resolve() and path.is_relative_to(core.REPO) and
        path.is_file() and not path.is_symlink(),'Canonical local completed-return-evidence decision required')
    decision=core.read(path);pins={str(path):core.sha(path)}
    core.require(decision.get('schema')=='task1-source-position-decision-v1' and
        decision.get('status')=='preregistered_not_started' and decision.get('source_run_id')==SOURCE_RUN and
        decision.get('source_case_id')==SOURCE_ID and decision.get('case_ids')==list(CASE_IDS) and
        isinstance(decision.get('chosen_question'),str) and bool(decision['chosen_question'].strip()),
        'Explicit root source-position selection after actual return results required')
    returns=decision.get('return_results',[])
    core.require(len(returns)==2 and {r['case_id']for r in returns}==set(RETURN_IDS),'Both completed return-position results required')
    expected={}
    for row in returns:
        for key in ('summary','case_record'):
            p=Path(row[key+'_path'])
            core.require(p.is_absolute() and p==p.resolve() and p.is_file() and not p.is_symlink() and
                p.is_relative_to(core.REPO/'data-native') and core.sha(p)==row[key+'_sha256'],
                'Actual return-result SHA/path differs')
            pins[str(p)]=row[key+'_sha256']
        summary,record=core.read(row['summary_path']),core.read(row['case_record_path'])
        core.require(summary['id']==record['id']==row['case_id'] and summary['status']==record['status']=='complete' and
            record['postprocess_path']==row['summary_path'] and record['postprocess_sha256']==row['summary_sha256'] and
            all(record['validation'][key]<=value for key,value in core.GATES.items()),
            'Return-position case must actually complete all unchanged native gates')
        run=Path(row['summary_path']).parents[2];pre=run/'preregistration.json';registration=core.read(pre)
        case=next(c for c in registration['cases']if c['id']==row['case_id'])
        core.require(case['h_xy_mm']==.625 and case['sc_cells']==2 and case['bulk_counts']==[14,14,40] and
            case['channels']==2 and case['cells']==351680,'Completed return-position source grid/model differs')
        pins[str(pre)]=core.sha(pre)
        for key in ('config','mask'):
            p=Path(case[key+'_file']);core.require(core.sha(p)==case[key+'_sha256'],'Return-position config/mask SHA differs')
            pins[str(p)]=case[key+'_sha256']
        expected[row['case_id']]=row
    evidence=decision.get('return_volume_report',{});p=Path(evidence.get('path',''))
    core.require(p.is_absolute() and p==p.resolve() and p.is_relative_to(core.REPO) and p.is_file() and
        core.sha(p)==evidence.get('sha256'),'Pinned actual return-position volume/burden report required')
    report=core.read(p);pins[str(p)]=evidence['sha256']
    core.require(report['status']=='calculated_unadopted' and report['inputs_unchanged'] is True,
                 'Completed actual return-position volume comparison required before admission')
    for ident,row in expected.items():
        matches=[r for r in report['cases']if r['case_id']==ident and r['summary_path']==row['summary_path']]
        core.require(len(matches)==1 and report['inputs_sha256'].get(row['summary_path'])==row['summary_sha256'],
                     'Volume report must bind both actual return-position source summaries')
    return dict(path=str(path),SHA256=core.sha(path),chosen_question=decision['chosen_question'],
        return_volume_report=evidence,actual_return_case_ids=list(RETURN_IDS)),pins


def prepare_source_position(run,decision_path):
    started=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run==run.resolve() and not run.exists(), 'New canonical unique source-position run required')
    _caller_owns_execution_lock();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    budget_path=core.REPO/'runtime/task1-budget.json';budget=policy.load_ledger(budget_path);limit=policy.effective_limit(budget)
    core.require(limit==13800 and limit-budget['spent_seconds']>=MIN_REMAINING_SECONDS,
        'Need approved13800s policy and1800s: prep60+2x600+2x180validation+120UI+60preservation')
    core.require(decision_path is not None,'Actual completed return-position evidence and root selection are mandatory')
    selected_decision,decision_pins=verify_root_decision(Path(decision_path).absolute())
    limits=core.effective_limits(budget);pins=core.source_pins(budget)
    test=core.REPO/'tests/test_task1_source_position_registration.py'
    for p in (Path(__file__).resolve(),test,Path(asym.__file__).resolve(),Path(contact.__file__).resolve()):
        pins[str(p)]=core.sha(p)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=core.REPO,text=True).strip()
    for name,expected in pins.items():
        p=Path(name);core.require(core.sha(p)==expected,'Source/policy SHA changed: '+name)
        if p.suffix in ('.py','.java'):
            core.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(core.REPO))],cwd=core.REPO)==p.read_bytes(),
                         'Commit all consumed implementation sources/tests before preparation: '+name)
    core.require(shutil.disk_usage(run.parent).free>2*core.GIB+EXPECTED_RAW_BOUND_BYTES,'Two raw bases plus2GiB reserve unavailable')
    run.mkdir();succeeded=False;registration=None
    try:
        for d in ('configs','masks','bases','cases','postprocess','logs','classes','geometry-audit'):(run/d).mkdir()
        def guard(phase):
            remaining=min(60-(time.monotonic()-started),limit-budget['spent_seconds']-(time.monotonic()-started)-1740)
            core.require(remaining>0 and core.rss(os.getpid())<3*core.GIB and shutil.disk_usage(run).free>=2*core.GIB,
                         'Source-position preparation60s/RSS/reserve unavailable at '+phase)
            core.write(run/'controller.json',dict(status='preparing',phase=phase,pid=os.getpid(),
                proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now(),elapsed_seconds=time.monotonic()-started))
            return remaining
        guard('original_and_source_integrity');integrity=core.original_integrity()
        volume,native,carrier,feedback=(core.read(p)for p in (VOLUME,NATIVE_AUDIT,CARRIER_AUDIT,FEEDBACK))
        core.require(volume['status']=='calculated_unadopted' and volume['inputs_unchanged'] is True and
            native['status']==carrier['status']=='complete_diagnostic_only' and
            native['inputs_unchanged'] is True and carrier['inputs_unchanged'] is True,
            'Completed actual asymmetric volume/native association/carrier evidence required')
        source,old_config,old_mask,source_pins=contact._source_case(core,SOURCE_RUN,SOURCE_ID,volume)
        baseline,base_config,base_mask,base_pins=contact._source_case(core,'cloud-mesh-c1-20261019T190000Z',
            'baseline-square15-xy80',volume)
        core.require(source['source_coating_nm']==10 and source['source_Rs_fit_window_Hz']==500 and
            source['circuit']['pad_to_node']=={'0':'out0','1':'out1','2':'GND','3':'GND'}, 'Nominal10nmRs500/top4pad2output circuit required')
        src_props,base_props=_properties(old_config.read_bytes()),_properties(base_config.read_bytes())
        keys={k for k in src_props if k.startswith('z.')or k.endswith(('.sigma','.epsilon_r'))}
        core.require(all(src_props[k]==base_props[k]for k in keys),'Same-grid baseline material/contact model differs')
        source_rows,source_areas,_=asym.aligned_mixed_mask(source['design'])
        core.require(old_mask.read_bytes()==_mask_bytes(source_rows),'Actual completed source mask bytes differ from exact aligned mixed geometry')
        pins.update(source_pins);pins.update(base_pins)
        for p in (VOLUME,NATIVE_AUDIT,CARRIER_AUDIT,FEEDBACK):pins[str(p)]=core.sha(p)
        pins.update(decision_pins)
        core.write(run/'geometry-audit/rejected-outward-request.json',outward_rejection_proof())
        cases=[];mappings=[]
        for ident,delta in zip(CASE_IDS,DELTAS):
            guard('register_'+ident);design=translated_design(source['design'],delta)
            rows,areas,receipt=translated_mask(source_rows,delta)
            core.require(areas==source_areas,'Position-only contrast must preserve represented physical pad areas exactly')
            mask=run/'masks'/(ident+'.csv');mask.write_bytes(_mask_bytes(rows))
            config=run/'configs'/(ident+'.properties');data,changes=changed_position_config(old_config.read_bytes(),mask,core.sha(mask),delta);config.write_bytes(data)
            core.write(run/'geometry-audit'/(ident+'-design.json'),design);core.write(run/'geometry-audit'/(ident+'-mask.json'),receipt)
            case=copy.deepcopy(source)
            case.update(id=ident,design_id=design['id'],design=design,config_file=str(config),config_sha256=core.sha(config),
                mask_file=str(mask),mask_sha256=core.sha(mask),source_run_id=run.name,source_coordinate_shift_mm=delta,
                expected_pad_areas_m2=areas,source_parent_case_id=SOURCE_ID,
                parent_position_control=dict(run_id=SOURCE_RUN,case_id=SOURCE_ID,summary_path=str(core.REPO/'data-native'/SOURCE_RUN/'postprocess'/SOURCE_ID/'summary.json'),
                    summary_sha256=source_pins[str(core.REPO/'data-native'/SOURCE_RUN/'postprocess'/SOURCE_ID/'summary.json')]),
                position_only_contrast=True,physical_area_shape_rotation_wiring_changed=False,status='preregistered_not_executed',
                candidate_adopted=False,mesh_convergence_validated=False,existing_XY_contact_model_holds_preserved=True)
            case.update(_mesh(case));core.require(case['cells']==EXPECTED_CELLS,'351680cell mesh changed')
            case['cache_signature']=core.check_cached_operator(case,run);cases.append(case)
            mappings.append(dict(original_config=str(old_config),original_sha256=core.sha(old_config),new_config=str(config),
                new_sha256=core.sha(config),changed_fields=list(changes),new_mask_sha256=core.sha(mask),
                changed_physical_parameter='Signal0/1centre radial-coordinate shiftδ only',unchanged_return_pads=[2,3],
                contact_tissue_circuit_mesh_changed=False))
        jdk=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
        javac=shutil.which('javac') or str(jdk/'javac');java=str(Path(javac).resolve().parent/'java')
        core.require(Path(javac).is_file() and Path(java).is_file(),'Matching installed Java compiler/runtime required')
        def command(args,log):subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=guard('compile_or_analytic_selftest'))
        with (run/'logs/compile-selftest.log').open('x')as log:
            command([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'),str(core.SOURCE/'ExploreBasis.java'),str(core.SOURCE/'SelectivityShapeBasis.java'),
                str(core.REPO/'tools/java/CloudShapeBasis.java')],log)
            command([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),'CloudShapeBasis','--selftest'],log)
        for p in [*(run/'configs').glob('*'),*(run/'masks').glob('*'),*(run/'classes').glob('*'),*(run/'geometry-audit').glob('*')]:pins[str(p)]=core.sha(p)
        for p,expected in pins.items():core.require(core.sha(p)==expected,'Pinned source-position input changed: '+p)
        guard('final_integrity')
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='two_source_position_only_contrasts',status='prepared',
            created_utc=core.now(),source_commit=commit,package_integrity=integrity,limits=limits,gates=copy.deepcopy(core.GATES),
            cases=cases,java=java,new_PDE_conditions_maximum=2,expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,
            source_and_input_sha256=pins,preparation_seconds=time.monotonic()-started,path_mapping=mappings,
            local_continuation_phase='S4',source_feedback=dict(path=str(FEEDBACK),SHA256=core.sha(FEEDBACK),
                stable_source_keys=[r['source_key']for r in feedback.get('new_substantive_feedback',[])]),
            resource_policy_immutable_refs=policy.policy_refs(budget),root_selection_decision=selected_decision,
            scientific_question='How do inward source-centre levels minus0.625/minus1.25mm alter target/shallow overlap relative to the completed return-only levels?',
            parameter_family=dict(delta_coordinate_mm=list(DELTAS),cached_parent_delta_mm=0.,only_changed_parameter='signal0/1XYpositions'),
            rejected_geometry_requests=[outward_rejection_proof()],
            planned_normalizations=['raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin'],
            comparison_waveforms=['square_3h','sine','triangle_3h'],
            fixed_comparisons='Original same-grid225mm2 square baseline and same-physical-shapeδ0parent; primarymean/P10, surface/offtargetP95 and highvolume at originalprimarymean/P10cutoffs',
            fixed_cutoffs_V_m=dict(baseline_mean=4.061848941601601,baseline_p10=3.6457357391300533),
            root_validation_reserve_seconds=360,root_UI_reserve_seconds=120,root_preservation_reserve_seconds=60,
            candidate_adopted=False,mesh_convergence_validated=False,experimental_validation=False,existing_XY_contact_model_holds_preserved=True,
            contact_uncertainty='Frozen nominalPBS10nmRs500specificZ; no newRs/area scaling or actualskinvalidation',
            source_causal_interpretation='Position contrast of coupled commonGND network, not isolated per-source causal attribution',
            frozen_source_snapshot_owner='standalone CLI freezesources once inside dual executionlock',
            storage=dict(native_location=str(run),persistent_backup_verified=False,retirement_of_old_environment_allowed=False),
            next_decision='Report absoluteROImean/P10 and non-targetburdens under5modes, then allpriorgates; no automaticadoption/extraPDE')
        core.write(run/'preregistration.json',registration);core.write(run/'controller.json',dict(status='prepared',updated_utc=core.now()));succeeded=True
    except BaseException as error:
        core.write(run/'preparation-failure.json',dict(status='preparation_failed_preserved',error_type=type(error).__name__,error=str(error),
            observed_utc=core.now(),partial_evidence_preserved=True,automatic_retry=False));raise
    finally:
        elapsed=time.monotonic()-started;budget['spent_seconds']+=elapsed
        budget['runs'].append(dict(run_id=run.name,stage='preparation',seconds=elapsed,status='prepared'if succeeded else'preparation_failed_preserved'))
        core.write(budget_path,budget)
    return registration


def main():
    import argparse
    import fcntl
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--decision',type=Path,required=True);args=parser.parse_args()
    with (core.REPO/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=prepare_source_position(args.output,args.decision);core.freeze_sources(args.output.resolve())
    print(dict(status=result['status'],run=str(args.output),cases=list(CASE_IDS)))


if __name__=='__main__':main()
