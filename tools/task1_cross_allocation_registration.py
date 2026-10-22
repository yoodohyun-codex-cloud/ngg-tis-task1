"""Three fixed-total-area cross allocations; import never starts computation.

Only explicit preparation under both global locks is supported. The root owns
all actual PDE/postprocessing and any subsequent numerical validation decision.
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
import task1_cross_registration as cross
import task1_contact_sensitivity_registration as contact
from task1_grouped_registration import _caller_owns_execution_lock, _mesh
from task1_reference_registration import _changed_config, _properties

SOURCE_AREAS = (200., 225., 250.)
CASE_IDS = ('crossalloc-source200-return250-xy80',
            'crossalloc-source225-return225-xy80',
            'crossalloc-source250-return200-xy80')
EXPECTED_CELLS = 351680
EXPECTED_RAW_BOUND_BYTES = 633024000
MIN_REMAINING_SECONDS = 2700
BASE_RUN = 'cloud-mesh-c1-20261019T190000Z'
BASE_ID = 'baseline-square15-xy80'
FEEDBACK = core.REPO/'docs/cloud-extended-20261021T102700Z/feedback-before.json'
REQUIRED_EVIDENCE_IDS = (BASE_ID, 'asym-cross281p25-return168p75-xy80',
    'asym-return-out0p625-xy80', 'asym-return-in0p625-xy80',
    'asym-source-in0p625-xy80', 'asym-source-in1p25-xy80')


def _mask_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['pad', 'i', 'j', 'area_m2'])
    for p, i, j, a in rows:
        writer.writerow([p, i, j, format(a, '.17g')])
    return stream.getvalue().encode('utf-8')


def _outline(x, y, length):
    a, b = length/2, 5.
    return [[x+u, y+v] for u, v in [(-b,-a),(b,-a),(b,-b),(a,-b),(a,b),(b,b),
        (b,a),(-b,a),(-b,b),(-a,b),(-a,-b),(-b,-b)]]


def allocation_design(baseline_design, source_area_mm2):
    core.require(type(source_area_mm2) in (int,float) and source_area_mm2 in SOURCE_AREAS,
                 'Only the preregistered200/225/250mm2 source allocations are allowed')
    design = copy.deepcopy(baseline_design)
    core.require(design['phantom_diameter_mm'] == 50 and design['contact_plane_z_mm'] == 0 and
        design['total_pads'] == 4 and design['source_outputs'] == 2 and len(design['pads']) == 4 and
        design['return_connection'] == 'all_return_pads_ideal_common_GND', 'FixedD50/top4pad2output contract differs')
    for p, (pad, centre) in enumerate(zip(design['pads'], cross.CENTRES_MM)):
        core.require(pad['pad'] == p and tuple(pad['center_mm']) == centre and
            pad['rotation_deg'] == pad['corner_radius_mm'] == 0 and
            pad['role'] == ('signal' if p < 2 else 'common_gnd_return') and
            pad['source_output'] == (p if p < 2 else None), 'Fixed physical position/rotation/wiring differs')
        area = source_area_mm2 if p < 2 else 450-source_area_mm2
        length = (area+100)/20
        x, y = centre
        pad.update(shape='cross', width_mm=length, height_mm=length,
            outer_length_mm=length, arm_width_mm=10., analytic_area_mm2=area,
            area_mm2=area, polygon_area_mm2=area, polygon_mm=_outline(x,y,length),
            geometry_primitive='union_of_two_centered_axis_aligned_rectangles',
            union_rectangles_mm=[dict(center_mm=[x,y],width_mm=length,height_mm=10.),
                                 dict(center_mm=[x,y],width_mm=10.,height_mm=length)])
    design.update(id=CASE_IDS[SOURCE_AREAS.index(source_area_mm2)].removesuffix('-xy80'),
        group='fixed900mm2_all_cross_source_return_allocation', channels=2,
        xy_mm=[p['center_mm'] for p in design['pads']], minimum_gap_mm=3.75,
        geometry_revision='aligned-all-cross-fixed-arm10-allocation-v1',
        source_pad_area_mm2=source_area_mm2, return_pad_area_mm2=450-source_area_mm2,
        allocation_parameter_mm=(source_area_mm2-225)/20,
        physical_total_contact_area_mm2=900., area_change_vs_four_square225_percent=0.,
        area_policy='Fixed900mm2 total; source/return allocation and outer lengths vary jointly; arm10 and centres fixed')
    return design


def allocation_mask(design):
    area = design.get('source_pad_area_mm2')
    core.require(area in SOURCE_AREAS, 'Unknown registered allocation')
    # Reconstruct the exact expected geometry to reject stale/corrupt descriptors.
    expected = allocation_design(design, area)
    core.require(design == expected, 'Allocation geometry/area/position metadata differs')
    h, rows, covered = .625, [], set()
    counts = []
    for p, pad in enumerate(design['pads']):
        x, y = pad['center_mm']; length = pad['outer_length_mm']
        core.require(all(px*px+py*py < 625 for px,py in pad['polygon_mm']), 'Cross physical vertex outside fixedD50')
        cx, cy = round((x+25)/h), round((y+25)/h)
        outer, arm = round(length/h), 16
        core.require(outer in (24,26,28) and length/h == outer, 'Unaligned cross length')
        faces = set()
        for width,height in ((outer,arm),(arm,outer)):
            faces.update((i,j) for j in range(cy-height//2,cy+height//2)
                         for i in range(cx-width//2,cx+width//2))
        core.require(not covered.intersection(faces), 'Physical pads overlap')
        covered.update(faces); counts.append(len(faces))
        for i,j in sorted(faces,key=lambda ij:(ij[1],ij[0])):
            core.require(all((-25+ii*h)**2+(-25+jj*h)**2 < 625
                for ii in (i,i+1) for jj in (j,j+1)), 'Contact face outside fixedD50')
            rows.append((p,i,j,(h/1000)**2))
    areas = [math.fsum(a for p,_,_,a in rows if p == pad) for pad in range(4)]
    desired = [area,area,450-area,450-area]
    core.require(len(rows) == 2304 and all(abs(a/(v*1e-6)-1) <= 1e-10 for a,v in zip(areas,desired)),
                 'Fixed900mm2 represented allocation differs')
    return rows, areas, dict(rule='integer-full-face-concave-cross-union-v1',h_xy_mm=h,
        contacts=2304,faces_per_pad=counts,represented_pad_areas_m2=areas,
        physical_pad_areas_mm2=desired,physical_total_area_mm2=900.,bounding_box_gap_mm=3.75,
        maximum_physical_vertex_radius_mm=max(math.hypot(x,y) for p in design['pads'] for x,y in p['polygon_mm']),
        partial_faces=0,discarded_slivers=0,renormalization=False,geometry_convergence_claimed=False,
        convex_hull_approximation_used=False)


def config_for_allocation(data, design, maskpath, masksha, areas):
    _, expected, _ = allocation_mask(design)
    core.require(areas == expected, 'Config must use exact represented contact areas')
    changes = {'mask.path':str(maskpath),'mask.sha256':masksha}
    for p,pad in enumerate(design['pads']):
        changes.update({f'pad.{p}.shape':'cross',f'pad.{p}.width_mm':str(pad['outer_length_mm']),
            f'pad.{p}.height_mm':str(pad['outer_length_mm']),f'pad.{p}.analytic_area_mm2':str(pad['analytic_area_mm2']),
            f'pad.{p}.represented_area_m2':format(areas[p],'.17g')})
    output = _changed_config(data,changes)
    additions = {f'pad.{p}.arm_width_mm':'10.0' for p in range(4)}
    core.require(not set(additions).intersection(_properties(output)), 'Baseline must not contain cross-only descriptors')
    output += (b'' if output.endswith(b'\n') else b'\n')+''.join(k+'='+v+'\n' for k,v in additions.items()).encode()
    before, after = _properties(data), _properties(output)
    core.require(set(after) == set(before)|set(additions) and
        all(after[k] == v for k,v in before.items() if k not in changes), 'Non-geometry physical fields changed')
    return output, {**changes,**additions}


def verify_root_decision(path):
    path = Path(path)
    core.require(path.is_absolute() and path == path.resolve() and path.is_relative_to(core.REPO) and
        path.is_file() and not path.is_symlink(), 'Canonical root allocation-selection decision required')
    decision = core.read(path)
    core.require(decision.get('schema') == 'task1-cross-allocation-decision-v1' and
        decision.get('status') == 'preregistered_not_started' and decision.get('case_ids') == list(CASE_IDS) and
        isinstance(decision.get('chosen_question'),str) and bool(decision['chosen_question'].strip()), 'Explicit three-case root decision required')
    evidence = decision.get('source_volume_report',{}); report_path = Path(evidence.get('path',''))
    core.require(report_path.is_absolute() and report_path == report_path.resolve() and report_path.is_relative_to(core.REPO) and
        report_path.is_file() and not report_path.is_symlink() and core.sha(report_path) == evidence.get('sha256'),
        'Pinned actual six-case volume report required')
    report = core.read(report_path)
    core.require(report['status'] == 'calculated_unadopted' and report['inputs_unchanged'] is True and
        len(report['cases']) == 6 and {c['case_id'] for c in report['cases']} == set(REQUIRED_EVIDENCE_IDS),
        'All six completed baseline/asymmetric/return/source volume controls required')
    pins = {str(path):core.sha(path),str(report_path):core.sha(report_path)}
    # Strict existing metadata-only validator checks each actual complete/native
    # case, config/mask, frozen circuit, same351680 grid and full-skin audit pins.
    for row in report['cases']:
        _,_,_,refs = contact._source_case(core,row['run_id'],row['case_id'],report)
        core.require(report['inputs_sha256'].get(row['summary_path']) == refs[row['summary_path']],
                     'Volume report does not bind its actual source summary')
        pins.update(refs)
    return dict(path=str(path),SHA256=core.sha(path),chosen_question=decision['chosen_question'],
        source_volume_report=evidence,completed_evidence_case_ids=list(REQUIRED_EVIDENCE_IDS)),report,pins


def prepare_cross_allocation(run, decision_path):
    started=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run == run.resolve() and not run.exists(), 'New canonical unique allocation run required')
    _caller_owns_execution_lock();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    budget_path=core.REPO/'runtime/task1-budget.json';budget=policy.load_ledger(budget_path)
    limit=policy.effective_limit(budget)
    core.require(limit == 13800 and limit-budget['spent_seconds'] >= MIN_REMAINING_SECONDS,
        'Need approved13800s and2700remaining: prep60+3x600+3x180validation+180UI+120preservation')
    selected,volume,pins=verify_root_decision(Path(decision_path).absolute())
    limits=core.effective_limits(budget);pins.update(core.source_pins(budget))
    for p in (Path(__file__).resolve(),core.REPO/'tests/test_task1_cross_allocation_registration.py',
              Path(cross.__file__).resolve(),Path(contact.__file__).resolve()):pins[str(p)]=core.sha(p)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=core.REPO,text=True).strip()
    for name,digest in pins.items():
        p=Path(name);core.require(core.sha(p) == digest,'Pinned source/policy/input changed: '+name)
        if p.suffix in ('.py','.java'):
            core.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(core.REPO))],cwd=core.REPO) == p.read_bytes(),
                         'Commit every consumed implementation/test before preparation: '+name)
    core.require(EXPECTED_RAW_BOUND_BYTES == 3*EXPECTED_CELLS*600 <= limits['max_batch_added_bytes'] and
        shutil.disk_usage(run.parent).free > 2*core.GIB+EXPECTED_RAW_BOUND_BYTES, 'Three raw bases plus2GiB reserve unavailable')
    run.mkdir();succeeded=False;registration=None
    try:
        for d in ('configs','masks','bases','cases','postprocess','logs','classes','geometry-audit'):(run/d).mkdir()
        def guard(phase):
            elapsed=time.monotonic()-started
            remaining=min(60-elapsed,limit-budget['spent_seconds']-elapsed-2640)
            core.require(remaining > 0 and core.rss(os.getpid()) < 3*core.GIB and
                shutil.disk_usage(run).free >= 2*core.GIB, 'Preparation60s/RSS/reserve failed at '+phase)
            core.write(run/'controller.json',dict(status='preparing',phase=phase,pid=os.getpid(),
                proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now(),elapsed_seconds=elapsed))
            return remaining
        guard('original_and_baseline_integrity');integrity=core.original_integrity()
        baseline,old_config,old_mask,refs=contact._source_case(core,BASE_RUN,BASE_ID,volume);pins.update(refs)
        core.require(baseline['source_coating_nm'] == 10 and baseline['source_Rs_fit_window_Hz'] == 500,
                     'Only nominal10nm/Rs500 contact physics is permitted')
        cross.validate_baseline_template(baseline,baseline['design'],old_config.read_bytes())
        feedback=core.read(FEEDBACK);pins[str(FEEDBACK)]=core.sha(FEEDBACK)
        reference=dict(run_id=BASE_RUN,case_id=BASE_ID,postprocess_path=str(core.REPO/'data-native'/BASE_RUN/'postprocess'/BASE_ID/'summary.json'),
            postprocess_sha256=refs[str(core.REPO/'data-native'/BASE_RUN/'postprocess'/BASE_ID/'summary.json')],
            config_file=str(old_config),config_sha256=core.sha(old_config),mask_file=str(old_mask),mask_sha256=core.sha(old_mask))
        cases=[];mappings=[]
        for ident,area in zip(CASE_IDS,SOURCE_AREAS):
            guard('register_'+ident);design=allocation_design(baseline['design'],area)
            rows,areas,receipt=allocation_mask(design)
            mask=run/'masks'/(ident+'.csv');mask.write_bytes(_mask_bytes(rows))
            config=run/'configs'/(ident+'.properties')
            data,changes=config_for_allocation(old_config.read_bytes(),design,mask,core.sha(mask),areas);config.write_bytes(data)
            core.write(run/'geometry-audit'/(ident+'-design.json'),design)
            core.write(run/'geometry-audit'/(ident+'-mask.json'),receipt)
            case=copy.deepcopy(baseline)
            case.update(id=ident,design_id=design['id'],design=design,source_run_id=run.name,
                config_file=str(config),config_sha256=core.sha(config),mask_file=str(mask),mask_sha256=core.sha(mask),
                expected_pad_areas_m2=areas,baseline_same_grid_reference=reference,
                java_class='CloudShapeBasis',postprocessor='legacy_native',exporter_class='SelectivityShapeBasis',
                channels=2,n_outputs=2,n_pads=4,physical_total_contact_area_mm2=900.,
                contact_area_policy=design['area_policy'],source_pad_area_mm2=area,return_pad_area_mm2=450-area,
                source_outer_length_mm=(area+100)/20,return_outer_length_mm=(550-area)/20,
                arm_width_mm=10.,allocation_parameter_mm=(area-225)/20,
                status='preregistered_not_executed',candidate_adopted=False,mesh_convergence_validated=False,
                existing_XY_contact_model_holds_preserved=True)
            case.update(_mesh(case));core.require(case['cells'] == EXPECTED_CELLS, '351680cell mesh changed')
            case['cache_signature']=core.check_cached_operator(case,run);cases.append(case)
            mappings.append(dict(original_config=str(old_config),original_sha256=core.sha(old_config),new_config=str(config),
                new_sha256=core.sha(config),changed_fields=list(changes),new_mask_sha256=core.sha(mask),
                operative_change='Explicit top contact masks only; specificZ/mesh/tissue/circuit/frequencies unchanged',
                geometry_descriptors_metadata_only=True,Rs_subtractions_added=0,contact_area_conversions_added=0))
        jdk=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
        javac=shutil.which('javac') or str(jdk/'javac');java=str(Path(javac).resolve().parent/'java')
        core.require(Path(javac).is_file() and Path(java).is_file(),'Matching Java compiler/runtime required')
        with (run/'logs/compile-selftest.log').open('x') as log:
            def command(args):subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT,
                timeout=guard('compile_or_analytic_selftest'))
            command([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'),str(core.SOURCE/'ExploreBasis.java'),str(core.SOURCE/'SelectivityShapeBasis.java'),
                str(core.REPO/'tools/java/CloudShapeBasis.java')])
            command([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),'CloudShapeBasis','--selftest'])
        for directory in ('configs','masks','classes','geometry-audit'):
            for p in (run/directory).iterdir():pins[str(p)]=core.sha(p)
        for p,digest in pins.items():core.require(core.sha(p) == digest,'Pinned allocation input changed: '+p)
        guard('final_integrity')
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='three_cross_area_allocation_contrasts',status='prepared',
            created_utc=core.now(),source_commit=commit,package_integrity=integrity,limits=limits,gates=copy.deepcopy(core.GATES),
            cases=cases,java=java,new_PDE_conditions_maximum=3,expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,
            source_and_input_sha256=pins,preparation_seconds=time.monotonic()-started,path_mapping=mappings,
            local_continuation_phase='cross_allocation',root_selection_decision=selected,
            source_feedback=dict(path=str(FEEDBACK),SHA256=core.sha(FEEDBACK),
                stable_source_keys=[r['source_key'] for r in feedback.get('new_substantive_feedback',[])]),
            resource_policy_immutable_refs=policy.policy_refs(budget),
            scientific_question='At fixed900mm2/arm10/centres/gap, does source-return cross allocation improve deep ROI without increasing shallow/non-target high modulation?',
            parameter_family=dict(source_area_mm2=list(SOURCE_AREAS),return_area_mm2=[250.,225.,200.],
                source_outer_mm=[15.,16.25,17.5],return_outer_mm=[17.5,16.25,15.],arm_mm=10.,
                total_area_mm2=900.,constant_adjacent_gap_mm=3.75,
                interpretation='One geometric family jointly changes allocation and outer length/perimeter; no isolated area causal claim'),
            planned_normalizations=['raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin'],
            comparison_waveforms=['square_3h','sine','triangle_3h'],
            fixed_cutoffs_V_m=dict(baseline_mean=4.061848941601601,baseline_p10=3.6457357391300533),
            comparison_contract='Same-grid original225square baseline and cached asymmetric parent; absolute primarymean/P10 and surface/complementP95/highvolume with fixed primary baseline cutoffs in all5modes; supplementary wholeXYslab does not replace r5ROI',
            root_validation_reserve_seconds=540,root_UI_reserve_seconds=180,root_preservation_reserve_seconds=120,
            candidate_adopted=False,mesh_convergence_validated=False,experimental_validation=False,
            existing_XY_contact_model_holds_preserved=True,
            contact_uncertainty='Frozen nominalPBS10nmRs500specificZ; one originalRs subtraction and area conversion; actualskin unvalidated',
            frozen_source_snapshot_owner='Standalone CLI freezes once under both execution locks',
            storage=dict(native_location=str(run),persistent_backup_verified=False,retirement_of_old_environment_allowed=False),
            next_decision='Evaluate all5normalizations/non-target caps; only a genuine promising case may be nominated for separately budgeted convergence; no automatic next PDE/adoption')
        core.write(run/'preregistration.json',registration)
        core.write(run/'controller.json',dict(status='prepared',updated_utc=core.now()));succeeded=True
    except BaseException as error:
        core.write(run/'preparation-failure.json',dict(status='preparation_failed_preserved',error_type=type(error).__name__,
            error=str(error),observed_utc=core.now(),partial_evidence_preserved=True,automatic_retry=False));raise
    finally:
        elapsed=time.monotonic()-started;budget['spent_seconds']+=elapsed
        budget['runs'].append(dict(run_id=run.name,stage='preparation',seconds=elapsed,
            status='prepared' if succeeded else 'preparation_failed_preserved'))
        core.write(budget_path,budget)
    return registration


def main():
    import argparse
    import fcntl
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--decision',type=Path,required=True)
    args=parser.parse_args()
    with (core.REPO/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=prepare_cross_allocation(args.output,args.decision);core.freeze_sources(args.output.resolve())
    print(dict(status=result['status'],run=str(args.output),cases=list(CASE_IDS)))


if __name__ == '__main__':main()
