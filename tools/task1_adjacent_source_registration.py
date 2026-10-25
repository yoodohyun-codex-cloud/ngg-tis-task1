"""Register one adjacent-source cross, reusing three completed 2x2 controls.

No work starts on import. Changing physical source adjacency is a wiring
contrast in the unchanged common-GND network, not isolated pair stimulation.
"""
from __future__ import annotations

import copy
import math
import os
from pathlib import Path
import shutil
import subprocess
import time

import task1_cloud_batch as core
import task1_resource_policy as policy
import task1_cross_allocation_registration as allocation
import task1_contact_sensitivity_registration as contact
from task1_grouped_registration import _caller_owns_execution_lock, _mesh
from task1_reference_registration import _changed_config, _properties

CASE_ID='balancedcross225-adjacent-sources-xy80'
OLD_PHYSICAL_PAD_BY_NEW=(0,2,1,3)
EXPECTED_CELLS=351680
EXPECTED_RAW_BOUND_BYTES=211008000
MIN_REMAINING_SECONDS=1020
SOURCE_RUN='cloud-cross-allocation-20261021T150000Z'
SOURCE_ID='crossalloc-source225-return225-xy80'
CACHED_SQUARE_RUN='cloud-finite-loop-20261020T002600Z-fine'
CACHED_SQUARE_ID='adjacent-square15-xy80'
_mask_bytes=allocation._mask_bytes


def adjacent_design(opposite_balanced_design):
    allocation.allocation_mask(opposite_balanced_design)
    core.require(opposite_balanced_design['source_pad_area_mm2'] == 225., 'Only the balanced225mm2 physical cross control is allowed')
    design=copy.deepcopy(opposite_balanced_design)
    original=copy.deepcopy(design['pads'])
    design['pads']=[]
    for new,old in enumerate(OLD_PHYSICAL_PAD_BY_NEW):
        pad=original[old]
        pad.update(pad=new,role='signal' if new<2 else 'common_gnd_return',
            source_output=new if new<2 else None,indexed_pair=new%2,original_physical_pad_id=old)
        design['pads'].append(pad)
    design.update(id=CASE_ID.removesuffix('-xy80'),group='balanced_cross_source_adjacency_wiring_control',
        xy_mm=[p['center_mm'] for p in design['pads']],
        geometry_revision='physical-contacts-unchanged-source-adjacency-v1',
        physical_geometry_control_id=opposite_balanced_design['id'],
        original_physical_pad_by_solver_pad=list(OLD_PHYSICAL_PAD_BY_NEW),
        source_source_spacing_mm=20.,opposite_control_source_spacing_mm=math.sqrt(800),
        source_adjacency='adjacent_bottom_row',physical_outline_area_centres_rotation_changed=False,
        area_policy='Unchanged four225mm2 crosses/900mm2; only connection roles change')
    core.require(design['id'] not in ('baseline-square15',opposite_balanced_design['id']), 'Wiring candidate requires a distinct design identity')
    return design


def relabel_mask(original_rows):
    """Only physical electrode labels change; no face/area/coordinate moves."""
    h=.625;face=(h/1000)**2;expected=set()
    for old,(cx,cy) in enumerate(((24,24),(56,56),(56,24),(24,56))):
        for width,height in ((26,16),(16,26)):
            expected.update((old,i,j) for j in range(cy-height//2,cy+height//2)
                            for i in range(cx-width//2,cx+width//2))
    core.require(len(original_rows) == 2304 and len({(p,i,j) for p,i,j,_ in original_rows}) == 2304 and
        {(p,i,j) for p,i,j,_ in original_rows} == expected and
        all(type(p) is int and type(i) is int and type(j) is int and a == face for p,i,j,a in original_rows),
        'Only the exact completed balanced-cross full-face control may be relabelled')
    new_by_old={old:new for new,old in enumerate(OLD_PHYSICAL_PAD_BY_NEW)}
    rows=sorted(((new_by_old[p],i,j,a) for p,i,j,a in original_rows),key=lambda r:(r[0],r[2],r[1]))
    areas=[math.fsum(a for p,_,_,a in rows if p == pad) for pad in range(4)]
    core.require(all(abs(a/.000225-1) <= 1e-10 for a in areas), 'Physical contact areas changed')
    return rows,areas,dict(rule='physical-pad-id-permutation-only-v1',old_physical_pad_by_new_solver_pad=list(OLD_PHYSICAL_PAD_BY_NEW),
        physical_face_coordinates_and_areas_unchanged=True,faces_per_pad=[576]*4,contacts=2304,
        represented_pad_areas_m2=areas,physical_total_area_mm2=900.,partial_faces=0,
        physical_outline_area_centres_rotation_changed=False,renormalization=False,
        return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
        old_physical_pad_to_node={'0':'out0','2':'out1','1':'GND','3':'GND'},
        independent_source_return_pairs_assumed=False)


def changed_wiring_config(data,path,sha):
    before=_properties(data)
    for p,(x,y) in enumerate(((-10.,-10.),(10.,10.),(10.,-10.),(-10.,10.))):
        core.require(float(before[f'pad.{p}.x_mm']) == x and float(before[f'pad.{p}.y_mm']) == y and
            before[f'pad.{p}.shape'] == 'cross' and float(before[f'pad.{p}.width_mm']) == 16.25 and
            float(before[f'pad.{p}.height_mm']) == 16.25 and float(before[f'pad.{p}.arm_width_mm']) == 10 and
            float(before[f'pad.{p}.analytic_area_mm2']) == 225, 'Completed physical balanced cross descriptor required')
    changes={'mask.path':str(path),'mask.sha256':sha,'pad.1.x_mm':'10.0','pad.1.y_mm':'-10.0',
             'pad.2.x_mm':'10.0','pad.2.y_mm':'10.0'}
    return _changed_config(data,changes),changes


def _cached_square_control(baseline_config):
    """Verify the exact existing adjacent square operator, without another solve."""
    run=core.REPO/'data-native'/CACHED_SQUARE_RUN;pre=run/'preregistration.json'
    case=next(c for c in core.read(pre)['cases'] if c['id'] == CACHED_SQUARE_ID)
    rp=run/'cases'/(CACHED_SQUARE_ID+'.json');record=core.read(rp)
    summary=Path(record['postprocess_path']);config=Path(case['config_file']);mask=Path(case['mask_file'])
    core.require(record['status'] == 'complete' and core.read(summary)['status'] == 'complete' and
        case['h_xy_mm'] == .625 and case['sc_cells'] == 2 and case['bulk_counts'] == [14,14,40] and
        case['channels'] == 2 and case['cells'] == EXPECTED_CELLS and
        core.sha(summary) == record['postprocess_sha256'] and core.sha(config) == case['config_sha256'] and
        core.sha(mask) == case['mask_sha256'] and all(record['validation'][k] <= v for k,v in core.GATES.items()),
        'Completed eligible adjacent-square cache required; never reschedule its PDE')
    old,new=_properties(baseline_config),_properties(config.read_bytes())
    excluded={'mask.path','mask.sha256'}|{f'pad.{p}.{xy}' for p in range(4) for xy in ('x_mm','y_mm')}
    core.require({k:v for k,v in old.items() if k not in excluded} == {k:v for k,v in new.items() if k not in excluded},
                 'Adjacent-square cache mesh/material/contact/source physics differ')
    for p,(x,y) in enumerate(((-10.,-10.),(10.,-10.),(10.,10.),(-10.,10.))):
        core.require(float(new[f'pad.{p}.x_mm']) == x and float(new[f'pad.{p}.y_mm']) == y,
                     'Cached square adjacency is a different physical wiring')
    circuit=case['circuit']
    core.require(circuit['n_pads'] == 4 and circuit['n_outputs'] == 2 and circuit['n_return_nodes'] == 1 and
        circuit['pad_to_node'] == {'0':'out0','1':'out1','2':'GND','3':'GND'} and
        circuit['source_resistance_ohm'] == 50 and circuit['source_peak_V'] == .5 and
        circuit['carrier_assignment_Hz'] == [3000,3030], 'Cached square circuit differs')
    pins={str(p):core.sha(p) for p in (pre,rp,summary,config,mask)}
    return dict(run_id=run.name,case_id=CACHED_SQUARE_ID,registration_path=str(pre),registration_sha256=pins[str(pre)],
        case_record_path=str(rp),case_record_sha256=pins[str(rp)],postprocess_path=str(summary),postprocess_sha256=pins[str(summary)],
        config_file=str(config),config_sha256=pins[str(config)],mask_file=str(mask),mask_sha256=pins[str(mask)],
        numerical_native_gates_passed=True,full_skin_and_volume_audit_scope='Requires matching cached audit before normalized2x2 reporting'),pins


def verify_root_decision(path):
    path=Path(path)
    core.require(path.is_absolute() and path == path.resolve() and path.is_relative_to(core.REPO) and
        path.is_file() and not path.is_symlink(), 'Canonical root wiring decision required')
    decision=core.read(path)
    core.require(decision.get('schema') == 'task1-adjacent-source-decision-v1' and decision.get('status') == 'preregistered_not_started' and
        decision.get('case_ids') == [CASE_ID] and isinstance(decision.get('chosen_question'),str) and
        bool(decision['chosen_question'].strip()), 'Explicit new wiring question after completed allocation screening required')
    evidence=decision.get('cross_allocation_report',{});p=Path(evidence.get('path',''))
    core.require(p.is_absolute() and p == p.resolve() and p.is_relative_to(core.REPO) and p.is_file() and
        not p.is_symlink() and core.sha(p) == evidence.get('sha256'), 'Actual completed allocation-screen SHA required')
    volume=core.read(p);pins={str(path):core.sha(path),str(p):core.sha(p)}
    core.require(volume['status'] == 'calculated_unadopted' and volume['inputs_unchanged'] is True and
        len(volume['cases']) == 4 and {c['case_id'] for c in volume['cases']} == {allocation.BASE_ID,*allocation.CASE_IDS},
        'All three allocation controls and original same-grid baseline must be screened first')
    for row in volume['cases']:
        _,_,_,refs=contact._source_case(core,row['run_id'],row['case_id'],volume)
        core.require(volume['inputs_sha256'].get(row['summary_path']) == refs[row['summary_path']], 'Screen/source summary SHA differs')
        pins.update(refs)
    return dict(path=str(path),SHA256=core.sha(path),chosen_question=decision['chosen_question'],
        cross_allocation_report=evidence),volume,pins


def prepare_adjacent_source(run,decision_path):
    started=time.monotonic();run=Path(run);core.paths_check(run)
    core.require(run.is_absolute() and run == run.resolve() and not run.exists(), 'New unique canonical adjacent-source run required')
    _caller_owns_execution_lock();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    budget_path=core.REPO/'runtime/task1-budget.json';budget=policy.load_ledger(budget_path);limit=policy.effective_limit(budget)
    core.require(limit == 13800 and limit-budget['spent_seconds'] >= MIN_REMAINING_SECONDS,
        'Need approved13800s and1020remaining: prep60+PDE600+validation180+UI120+preservation60')
    selected,volume,pins=verify_root_decision(Path(decision_path).absolute())
    pins.update(core.source_pins(budget));limits=core.effective_limits(budget)
    for p in (Path(__file__).resolve(),core.REPO/'tests/test_task1_adjacent_source_registration.py',
        Path(allocation.__file__).resolve(),core.REPO/'tests/test_task1_cross_allocation_registration.py',Path(contact.__file__).resolve()):pins[str(p)]=core.sha(p)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=core.REPO,text=True).strip()
    for name,digest in pins.items():
        p=Path(name);core.require(core.sha(p) == digest,'Pinned evidence/source changed: '+name)
        if p.suffix in ('.py','.java'):
            core.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(core.REPO))],cwd=core.REPO) == p.read_bytes(),
                         'Commit every consumed source/test before preparation: '+name)
    core.require(EXPECTED_RAW_BOUND_BYTES == EXPECTED_CELLS*600 <= limits['max_batch_added_bytes'] and
        shutil.disk_usage(run.parent).free > 2*core.GIB+EXPECTED_RAW_BOUND_BYTES, 'Single raw basis plus2GiB reserve unavailable')
    run.mkdir();succeeded=False;registration=None
    try:
        for d in ('configs','masks','bases','cases','postprocess','logs','classes','geometry-audit'):(run/d).mkdir()
        def guard(phase):
            elapsed=time.monotonic()-started;remaining=min(60-elapsed,limit-budget['spent_seconds']-elapsed-960)
            core.require(remaining > 0 and core.rss(os.getpid()) < 3*core.GIB and shutil.disk_usage(run).free >= 2*core.GIB,
                         'Preparation60s/RSS/reserve failed at '+phase)
            core.write(run/'controller.json',dict(status='preparing',phase=phase,pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),
                updated_utc=core.now(),elapsed_seconds=elapsed));return remaining
        guard('integrity_and_cached_controls');integrity=core.original_integrity()
        source,old_config,old_mask,refs=contact._source_case(core,SOURCE_RUN,SOURCE_ID,volume);pins.update(refs)
        baseline,base_config,_,basepins=contact._source_case(core,allocation.BASE_RUN,allocation.BASE_ID,volume);pins.update(basepins)
        square,squarepins=_cached_square_control(base_config.read_bytes());pins.update(squarepins)
        source_rows,source_areas,_=allocation.allocation_mask(source['design'])
        core.require(source['source_coating_nm'] == 10 and source['source_Rs_fit_window_Hz'] == 500 and
            old_mask.read_bytes() == _mask_bytes(source_rows), 'Completed nominal balanced-cross geometry must match exact mask bytes')
        design=adjacent_design(source['design']);rows,areas,receipt=relabel_mask(source_rows)
        core.require(areas == source_areas,'Wiring contrast must preserve exact physical pad areas')
        mask=run/'masks'/(CASE_ID+'.csv');mask.write_bytes(_mask_bytes(rows))
        config=run/'configs'/(CASE_ID+'.properties')
        data,changes=changed_wiring_config(old_config.read_bytes(),mask,core.sha(mask));config.write_bytes(data)
        core.write(run/'geometry-audit'/(CASE_ID+'-design.json'),design);core.write(run/'geometry-audit'/(CASE_ID+'-mask.json'),receipt)
        case=copy.deepcopy(source)
        case.update(id=CASE_ID,design_id=design['id'],design=design,source_run_id=run.name,
            config_file=str(config),config_sha256=core.sha(config),mask_file=str(mask),mask_sha256=core.sha(mask),expected_pad_areas_m2=areas,
            original_physical_pad_by_solver_pad=list(OLD_PHYSICAL_PAD_BY_NEW),physical_geometry_control=dict(run_id=SOURCE_RUN,case_id=SOURCE_ID),
            source_adjacency='adjacent_bottom_row',wiring_only_contrast=True,status='preregistered_not_executed',
            n_pads=4,n_outputs=2,channels=2,candidate_adopted=False,mesh_convergence_validated=False,existing_XY_contact_model_holds_preserved=True)
        case.update(_mesh(case));core.require(case['cells'] == EXPECTED_CELLS,'351680cell mesh changed')
        case['cache_signature']=core.check_cached_operator(case,run)
        jdk=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin');javac=shutil.which('javac') or str(jdk/'javac')
        java=str(Path(javac).resolve().parent/'java');core.require(Path(javac).is_file() and Path(java).is_file(),'Matching Java compiler/runtime required')
        with (run/'logs/compile-selftest.log').open('x') as log:
            def command(args):subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=guard('compile_or_analytic_selftest'))
            command([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'),str(core.SOURCE/'ExploreBasis.java'),str(core.SOURCE/'SelectivityShapeBasis.java'),str(core.REPO/'tools/java/CloudShapeBasis.java')])
            command([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),'CloudShapeBasis','--selftest'])
        feedback=core.read(allocation.FEEDBACK);pins[str(allocation.FEEDBACK)]=core.sha(allocation.FEEDBACK)
        for directory in ('configs','masks','classes','geometry-audit'):
            for p in (run/directory).iterdir():pins[str(p)]=core.sha(p)
        for p,digest in pins.items():core.require(core.sha(p) == digest,'Pinned adjacency input changed: '+p)
        guard('final_integrity')
        registration=dict(schema='task1-cloud-finite-v1',batch_kind='one_balanced_cross_source_adjacency_contrast',status='prepared',
            created_utc=core.now(),source_commit=commit,package_integrity=integrity,limits=limits,gates=copy.deepcopy(core.GATES),cases=[case],java=java,
            new_PDE_conditions_maximum=1,expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,source_and_input_sha256=pins,
            preparation_seconds=time.monotonic()-started,root_selection_decision=selected,resource_policy_immutable_refs=policy.policy_refs(budget),
            source_feedback=dict(path=str(allocation.FEEDBACK),SHA256=core.sha(allocation.FEEDBACK),
                stable_source_keys=[r['source_key'] for r in feedback.get('new_substantive_feedback',[])]),
            scientific_question='At fixed physical225mm2 contacts and nominal commonGND circuit, how does adjacent versus diagonal source assignment interact with square versus cross shape?',
            two_by_two_controls=dict(square_opposite=dict(run_id=allocation.BASE_RUN,case_id=allocation.BASE_ID),square_adjacent=square,
                cross_opposite=dict(run_id=SOURCE_RUN,case_id=SOURCE_ID),cross_adjacent=dict(run_id=run.name,case_id=CASE_ID)),
            original_physical_pad_by_new_solver_pad=list(OLD_PHYSICAL_PAD_BY_NEW),
            symmetry_check='D50 rotations/reflections preserve source-source distance; adjacent20mm differs from diagonal28.284mm and cannot be their symmetry alias',
            path_mapping=[dict(original_config=str(old_config),original_sha256=core.sha(old_config),new_config=str(config),new_sha256=core.sha(config),
                changed_fields=list(changes),geometry_descriptor_only_positions=True,operative_change='physical pad role labels only; all face coordinates/areas unchanged')],
            planned_normalizations=['raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin'],
            comparison_waveforms=['square_3h','sine','triangle_3h'],fixed_cutoffs_V_m=dict(baseline_mean=4.061848941601601,baseline_p10=3.6457357391300533),
            comparison_contract='Originalsquare opposite remains normalization baseline; screen absoluteROImean/P10 and surface/complementP95/highvolume under all5modes; r5primary plus wholeXYsupplement; no point-only selection',
            contact_uncertainty='Frozen nominalPBS10nmRs500specificZ, no new Rs subtraction/area scaling, actualskin unvalidated',
            ground_return_mechanism_changed=False,source_phase_or_amplitude_changed=False,independent_pairs_assumed=False,
            root_validation_reserve_seconds=180,root_UI_reserve_seconds=120,root_preservation_reserve_seconds=60,
            candidate_adopted=False,mesh_convergence_validated=False,experimental_validation=False,existing_XY_contact_model_holds_preserved=True,
            frozen_source_snapshot_owner='Standalone CLI freezes once under both execution locks',
            storage=dict(native_location=str(run),persistent_backup_verified=False,retirement_of_old_environment_allowed=False),
            next_decision='Complete cached4cell fullskin/volume comparison and prior numerical holds before any refinement/adoption; no automatic next PDE')
        core.write(run/'preregistration.json',registration);core.write(run/'controller.json',dict(status='prepared',updated_utc=core.now()));succeeded=True
    except BaseException as error:
        core.write(run/'preparation-failure.json',dict(status='preparation_failed_preserved',error_type=type(error).__name__,error=str(error),
            observed_utc=core.now(),partial_evidence_preserved=True,automatic_retry=False));raise
    finally:
        elapsed=time.monotonic()-started;budget['spent_seconds']+=elapsed
        budget['runs'].append(dict(run_id=run.name,stage='preparation',seconds=elapsed,status='prepared' if succeeded else 'preparation_failed_preserved'))
        core.write(budget_path,budget)
    return registration


def main():
    import argparse
    import fcntl
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--decision',type=Path,required=True);args=parser.parse_args()
    with (core.REPO/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=prepare_adjacent_source(args.output,args.decision);core.freeze_sources(args.output.resolve())
    print(dict(status=result['status'],run=str(args.output),cases=[CASE_ID]))


if __name__ == '__main__':main()
