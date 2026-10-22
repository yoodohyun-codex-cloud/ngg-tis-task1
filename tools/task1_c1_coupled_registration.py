"""One genuine C1 pair on the latest completed TIS coupled grid.

No research imports, preparation, solves or writes occur on import. The root
controller owns the lock, execution monitor and subsequent source snapshot.
This comparison is independent of the preserved historical strict-matrix hold.
"""
from __future__ import annotations

import copy
import csv
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time

import task1_cloud_batch as core
from task1_grouped_registration import _caller_owns_execution_lock, _mesh
from task1_reference_registration import _changed_config, _properties
from task1_coupled_registration import GATE_PERCENT


TIS_CASE = 'baseline-square15-coupled-xy100-sc8-bulk'
CASE_ID = 'baseline-square15-C1pair0-coupled-xy100-sc8-bulk'
TEMPLATE_ID = 'baseline-square15-C1pair0-xy80'


def _latest_completed_tis():
    matches = []
    for registration_path in (core.REPO/'data-native').glob('cloud-*/preregistration.json'):
        pre = core.read(registration_path)
        for case in pre.get('cases', []):
            if case.get('id') != TIS_CASE:
                continue
            run = registration_path.parent
            record_path = run/'cases'/(TIS_CASE+'.json')
            comparison_path = run/'coupled-comparison.json'
            if not record_path.is_file() or not comparison_path.is_file():
                continue
            record, comparison = core.read(record_path), core.read(comparison_path)
            core.require(record['status'] == 'complete' and core.read(run/'summary.json')['status'] == 'complete',
                         'Latest TIS run and case must be complete')
            post_path = Path(record['postprocess_path']).resolve()
            core.require(post_path.is_relative_to(run) and core.sha(post_path) == record['postprocess_sha256'],
                         'Latest TIS postprocess SHA/path differs')
            post = core.read(post_path)
            core.require(post['status'] == 'complete' and post['id'] == TIS_CASE and
                         case['h_xy_mm'] == .5 and case['sc_cells'] == 8 and
                         case['bulk_counts'] == [18, 18, 56] and case['channels'] == 2 and case['cells'] == 786000,
                         'Latest completed TIS coupled mesh differs')
            core.require(comparison['run_id'] == run.name and comparison['case_id'] == TIS_CASE and
                         comparison['status'] == 'passed_registered_coupled_comparison' and
                         comparison['all_registered_comparison_gates_passed'] is True and comparison['gate_count'] == 36,
                         'All36 prior coupled-grid comparison gates must pass')
            rows = comparison['waveform_comparisons']
            core.require(len(rows) == 3 and {row['waveform'] for row in rows} == {'square_3h', 'sine', 'triangle_3h'},
                         'All3 fixed coupled waveforms required')
            for row in rows:
                core.require(row['passed'] is True and set(row['changes']) == set(GATE_PERCENT),
                             'All12 fixed coupled metrics required per waveform')
                for key, value in row['changes'].items():
                    core.require(value['passed'] is True and value['limit_percent'] == GATE_PERCENT[key] and
                                 value['relative_change_percent'] is not None and
                                 abs(value['relative_change_percent']) <= GATE_PERCENT[key],
                                 'Coupled gate values or limits differ')
            config, mask = Path(case['config_file']), Path(case['mask_file'])
            core.require(core.sha(config) == case['config_sha256'] and core.sha(mask) == case['mask_sha256'],
                         'Latest TIS physical input SHA differs')
            matches.append((case, post, dict(run_id=run.name, case_id=TIS_CASE,
                registration_path=str(registration_path), registration_sha256=core.sha(registration_path),
                record_path=str(record_path), record_sha256=core.sha(record_path),
                postprocess_path=str(post_path), postprocess_sha256=core.sha(post_path),
                coupled_comparison_path=str(comparison_path), coupled_comparison_sha256=core.sha(comparison_path),
                config_file=str(config), config_sha256=core.sha(config), mask_file=str(mask), mask_sha256=core.sha(mask))))
    core.require(len(matches) == 1, 'One unique completed latest TIS coupled-grid source required')
    return matches[0]


def prepare_c1_coupled(run):
    start = time.monotonic()
    run = Path(run)
    core.paths_check(run)
    core.require(run.is_absolute() and run == run.resolve() and not run.exists(),
                 'New canonical coupled C1 run required; no retries/overwrites')
    _caller_owns_execution_lock()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    integrity = core.original_integrity()
    tis_case, tis_post, reference = _latest_completed_tis()
    pre_path = core.HIST/'preregistration.json'
    template = copy.deepcopy(core.read(pre_path)['case_pool'][TEMPLATE_ID])
    old_config = core.HIST/'configs'/Path(template['config_file']).name
    old_mask = core.HIST/'masks'/Path(template['mask_file']).name
    core.require(core.sha(old_config) == template['config_sha256'] and core.sha(old_mask) == template['mask_sha256'],
                 'Frozen true C1 template pin differs')
    old_values, tis_values = _properties(old_config.read_bytes()), _properties(Path(reference['config_file']).read_bytes())
    shared = {key for key in old_values if key.endswith(('.sigma', '.epsilon_r')) or key.startswith('z.')}
    core.require(all(old_values[key] == tis_values[key] for key in shared), 'C1 and latest TIS material/contact model differs')
    for c1_pad, tis_pad in ((0, 0), (1, 2)):
        for key in ('x_mm', 'y_mm', 'width_mm', 'height_mm', 'shape', 'rotation_deg', 'represented_area_m2'):
            core.require(old_values[f'pad.{c1_pad}.{key}'] == tis_values[f'pad.{tis_pad}.{key}'],
                         'Selected true C1 pair positions/areas differ from latest TIS')
    core.require(float(old_values['pad.0.x_mm']) == -10 and float(old_values['pad.0.y_mm']) == -10 and
                 float(old_values['pad.1.x_mm']) == 10 and float(old_values['pad.1.y_mm']) == -10 and
                 old_values['channels'] == '1', 'Exact source(-10,-10)/return(10,-10) C1 pair required')
    case = copy.deepcopy(template)
    case.update(id=CASE_ID, h_xy_mm=.5, sc_cells=8, bulk_counts=[18, 18, 56], channels=1,
        n_pads=2, n_outputs=1, java_class='CloudShapeBasis', postprocessor='legacy_native',
        exporter_class='SelectivityShapeBasis', mesh_id='coupled_xy100_sc8_bulk', source_run_id=run.name,
        source_coating_nm=10, source_Rs_fit_window_Hz=500, latest_TIS_reference=reference,
        primary_comparison_waveform='sine', primary_actual_carriers_Hz=[3000, 3030],
        status='preregistered_not_executed')
    case.update(_mesh(case))
    bound = case['cells']*600  # Conservative two-output-sized allowance, not actual C1 array dimensions.
    core.require(case['cells'] == 786000 and bound == 471600000 and bound <= core.LIMITS['max_batch_added_bytes'],
                 'Exact coupled C1 cell/conservative raw budget differs')
    core.require(shutil.disk_usage(run.parent).free > 2*core.GIB+bound, 'Coupled C1 raw allowance plus2GiB reserve unavailable')
    budgetpath = core.REPO/'runtime/task1-budget.json'
    budget = core.read(budgetpath)
    core.require(budget['limit_seconds'] == 6600 and budget['spent_seconds'] < 6600, 'Existing cumulative C1 budget exhausted')
    jdk = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
    javac = shutil.which('javac') or str(jdk/'javac')
    java = str(Path(javac).parent/'java')
    core.require(Path(javac).is_file() and Path(java).is_file(), 'Coupled C1 Java compiler/runtime unavailable')
    run.mkdir()
    for directory in ('configs', 'masks', 'bases', 'cases', 'postprocess', 'logs', 'classes'):
        (run/directory).mkdir()
    core.write(run/'controller.json', dict(status='preparing', phase='subset_latest_TIS_physical_faces',
        pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now()))
    registration = None
    succeeded = False
    try:
        source_mask = Path(reference['mask_file'])
        lines = source_mask.read_bytes().splitlines(keepends=True)
        core.require(lines[0].rstrip(b'\r\n') == b'pad,i,j,area_m2', 'Latest TIS mask header differs')
        selected = [lines[0]]
        for line in lines[1:]:
            if not line.strip():
                continue
            pad, tail = line.split(b',', 1)
            if pad == b'0': selected.append(line)
            elif pad == b'2': selected.append(b'1,'+tail)
        mask = run/'masks'/(CASE_ID+'.csv')
        mask.write_bytes(b''.join(selected))
        with mask.open() as stream:
            patches = list(csv.DictReader(stream))
        core.require({int(row['pad']) for row in patches} == {0, 1}, 'Exactly2 physical C1 pads required')
        areas = [math.fsum(float(row['area_m2']) for row in patches if int(row['pad']) == pad) for pad in (0, 1)]
        core.require(all(abs(area/.000225-1) <= 1e-10 for area in areas), 'Each selected C1 pad must retain225mm2')
        config = run/'configs'/(CASE_ID+'.properties')
        changes = {'h_mm': '0.5', 'validation.sc_cells': '8', 'bulk.counts': '18,18,56',
                   'mask.path': str(mask), 'mask.sha256': core.sha(mask)}
        config.write_bytes(_changed_config(old_config.read_bytes(), changes))
        case.update(config_file=str(config), config_sha256=core.sha(config), mask_file=str(mask),
                    mask_sha256=core.sha(mask), expected_pad_areas_m2=areas)
        case['design'] = copy.deepcopy(case['control_design'])
        case['design']['channels'] = 1
        case['design']['xy_mm'] = [pad['center_mm'] for pad in case['design']['pads']]
        case['circuit'] = dict(n_pads=2, n_outputs=1, n_signal_pads=1, n_return_pads=1,
            n_return_nodes=1, return_topology='one_actual_return_pad_at_GND',
            source_Vpp_each=1., source_peak_V=.5, source_resistance_ohm=50., source_phase_deg=[0.],
            actual_carriers_separately_Hz=[3000, 3030], primary_waveform='sine',
            pad_to_node={'0': 'out0', '1': 'GND'}, inactive_source_at_other_frequencies='0 V through50 ohm',
            other_TIS_pads_physically_present=False, other_TIS_output_present=False,
            two_carrier_TIS_from_single_sine=0.)
        case['cache_signature'] = core.check_cached_operator(case, run)
        pins = core.source_pins()
        for path in (Path(__file__), core.REPO/'tools/task1_coupled_registration.py',
                     core.REPO/'tools/task1_reference_registration.py', core.REPO/'tools/task1_grouped_registration.py',
                     pre_path, old_config, old_mask, Path(reference['config_file']), source_mask):
            pins[str(path)] = core.sha(path)
        for prefix in ('registration', 'record', 'postprocess', 'coupled_comparison'):
            pins[reference[prefix+'_path']] = reference[prefix+'_sha256']
        pins.update(tis_post['input_sha256'])
        historical_hold = core.REPO/'data-native/cloud-reference-20261019T192000Z/reference-comparison.json'
        hold = dict(status='preserved_separate_historical_reproduction_hold', claimed_resolved=False)
        if historical_hold.is_file():
            core.require(core.read(historical_hold)['status'] == 'failed', 'Historical strict failure must remain unchanged')
            pins[str(historical_hold)] = core.sha(historical_hold)
            hold.update(path=str(historical_hold), sha256=core.sha(historical_hold), original_status='failed',
                        old_fine_C1_reclassified=False)

        def command(args, log):
            remaining = 6600-budget['spent_seconds']-(time.monotonic()-start)
            core.require(remaining > 0 and shutil.disk_usage(run).free >= 2*core.GIB,
                         'Coupled C1 preparation cumulative time/disk reserve exhausted')
            core.write(run/'controller.json', dict(status='preparing', phase='compile_or_analytic_selftest',
                command=args, pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now()))
            subprocess.run(args, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=min(120., remaining))

        with (run/'logs/compile-selftest.log').open('x') as log:
            command([javac, '-J-Xmx2g', '-J-XX:ActiveProcessorCount=1', '-encoding', 'UTF-8', '-d', str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'), str(core.SOURCE/'ExploreBasis.java'),
                str(core.SOURCE/'SelectivityShapeBasis.java'), str(core.REPO/'tools/java/CloudShapeBasis.java')], log)
            command([java, '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1',
                     '-cp', str(run/'classes'), 'CloudShapeBasis', '--selftest'], log)
        for path in [*(run/'configs').glob('*'), *(run/'masks').glob('*'), *(run/'classes').glob('*')]:
            pins[str(path)] = core.sha(path)
        for path, expected in pins.items():
            core.require(core.sha(path) == expected, 'Coupled C1 source/latest TIS pin changed: '+path)
        registration = dict(schema='task1-cloud-finite-v1', batch_kind='latest_coupled_TIS_true_C1_pair',
            status='prepared', created_utc=core.now(),
            source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=core.REPO, text=True).strip(),
            historical_source_commit='8c3a30a778cc9bf19ccb52ca523598bff0a84650', package_integrity=integrity,
            limits=copy.deepcopy(core.LIMITS), gates=copy.deepcopy(core.GATES), cases=[case],
            new_PDE_conditions_maximum=1, expected_raw_bound_bytes=bound,
            raw_bound_note='600B/cell conservative allowance; actual native source dimension is1, never2outputs',
            java=java, source_and_input_sha256=pins, preparation_seconds=time.monotonic()-start,
            path_mapping=[dict(original_config=str(old_config), original_sha256=core.sha(old_config),
                new_config=str(config), new_sha256=core.sha(config), changed_fields=list(changes),
                source_TIS_mask=str(source_mask), source_TIS_mask_sha256=core.sha(source_mask),
                new_C1_mask=str(mask), new_C1_mask_sha256=core.sha(mask),
                operation='Keep physical TISpad0 andpad2; remap return2->1 only; every retained i,j,area text byte unchanged',
                represented_pad_areas_m2=areas)],
            latest_TIS_reference=reference, historical_strict_failure_hold=hold,
            primary_controls=dict(waveform='sine', actual_carriers_separately_Hz=[3000, 3030],
                reference_TIS_waveform='square_3h', matching_definitions=['central20 totalE RMS', 'ROI mean totalE RMS'],
                native_probe_gap_mm=5, native_probe_count_per_condition=40,
                legacy_postprocessor_extra_square_triangle_rows='secondary waveform controls; not pure single-frequency sine'),
            scientific_scope='New true2pad/1output C1 on exact completed Egrid; latest TIS matching control, not historical strict reproduction',
            convergence=dict(latest_TIS_36_coupled_comparison_gates_passed=True,
                C1_independent_mesh_convergence_validated=False, continuum_convergence_validated=False,
                experimental_validation=False, activation_equivalence_claimed=False),
            storage=dict(native_location=str(run), persistent_backup_verified=False,
                retirement_of_old_environment_allowed=False), frozen_source_snapshot_owner='root core.freeze_sources once',
            next_decision='After completion match pure sine to latest TISsquare at central20 andROI RMS separately; report Vpp/current/J/contact/power and native40probes with same linked run/candidate IDs')
        core.write(run/'preregistration.json', registration)
        core.write(run/'controller.json', dict(status='prepared', updated_utc=core.now()))
        succeeded = True
    except BaseException as error:
        core.write(run/'preparation-failure.json', dict(status='preparation_failed_preserved',
            error_type=type(error).__name__, error=str(error), observed_utc=core.now(),
            partial_evidence_preserved=True, automatic_retry=False))
        raise
    finally:
        elapsed = registration['preparation_seconds'] if succeeded else time.monotonic()-start
        budget['spent_seconds'] += elapsed
        budget['runs'].append(dict(run_id=run.name, stage='preparation', seconds=elapsed,
            status='prepared' if succeeded else 'preparation_failed_preserved'))
        core.write(budgetpath, budget)
    print(json.dumps(dict(status='prepared', run=str(run), cases=[CASE_ID], cells=786000,
        conservative_bound_bytes=bound, batch_kind='latest_coupled_TIS_true_C1_pair'), ensure_ascii=False))
    return registration
