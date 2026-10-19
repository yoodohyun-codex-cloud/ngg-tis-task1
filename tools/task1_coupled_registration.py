"""Register one final coupled-grid sensitivity check, without changing physics.

This module does not import research modules or start computations on import.
The root controller calls preparation under its one global execution lock and
calls the comparison after the bounded solve/postprocess. Old sources and runs
remain unchanged. Source snapshots are created once by the root controller.
"""
from __future__ import annotations

import copy
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


CASE_ID = 'baseline-square15-coupled-xy100-sc8-bulk'
TEMPLATE_ID = 'baseline-square15-xy100'
EXPECTED_CELLS = 786000
EXPECTED_RAW_BOUND_BYTES = 471600000
GATE_PERCENT = dict(
    target20_modulation_V_m=1., target20_total_E_RMS_V_m=1.,
    roi_mean_TIS_V_m=1., roi_p10_TIS_V_m=1., roi_mean_RMS_V_m=1.,
    target_superficial_p95_ratio=1., surface_J_RMS_max_A_m2=5.,
    surface_J_RMS_p95_A_m2=5., contact_voltage_RMS_max_V=5.,
    SC_power_W=2., contact_power_W=2., source_power_W=2.,
)


def _completed_same_xy_baseline(template):
    """Locate one already-computed physical baseline; no repeat solve allowed."""
    source_config = core.HIST/'configs'/Path(template['config_file']).name
    source_values = _properties(source_config.read_bytes())
    matches = []
    for registration_path in (core.REPO/'data-native').glob('cloud-*/preregistration.json'):
        registration = core.read(registration_path)
        for case in registration.get('cases', []):
            if (case.get('id') != TEMPLATE_ID or case.get('channels') != 2 or
                    case.get('h_xy_mm') != .5 or case.get('sc_cells') != 2 or
                    case.get('bulk_counts') != [14, 14, 40] or
                    case.get('java_class', 'CloudShapeBasis') != 'CloudShapeBasis'):
                continue
            case_record = registration_path.parent/'cases'/(case['id']+'.json')
            if not case_record.is_file():
                continue
            record = core.read(case_record)
            if record.get('status') != 'complete':
                continue
            post_path = Path(record['postprocess_path']).resolve()
            config_path = Path(case['config_file']).resolve()
            mask_path = Path(case['mask_file']).resolve()
            core.require(post_path.is_relative_to(registration_path.parent) and
                         config_path.is_relative_to(registration_path.parent) and
                         mask_path.is_relative_to(registration_path.parent),
                         'Portable completed baseline must belong to its actual local run')
            core.require(core.sha(post_path) == record['postprocess_sha256'] and
                         core.sha(config_path) == case['config_sha256'] and
                         core.sha(mask_path) == template['mask_sha256'] == case['mask_sha256'],
                         'Completed same-XY baseline pins differ')
            actual_values = _properties(config_path.read_bytes())
            core.require({k: v for k, v in source_values.items() if k != 'mask.path'} ==
                         {k: v for k, v in actual_values.items() if k != 'mask.path'},
                         'Completed same-XY baseline tissue/contact/circuit differs')
            post = core.read(post_path)
            core.require(post.get('status') == 'complete' and post.get('id') == TEMPLATE_ID and
                         post['mesh_metadata']['h_xy_mm'] == .5 and post['mesh_metadata']['sc_cells'] == 2 and
                         post['mesh_metadata']['bulk_layer_counts'] == [14, 14, 40],
                         'Complete same-XY native postprocess required')
            matches.append(dict(run_id=registration_path.parent.name, case_id=case['id'],
                registration_path=str(registration_path), registration_sha256=core.sha(registration_path),
                case_record_path=str(case_record), case_record_sha256=core.sha(case_record),
                postprocess_path=str(post_path), postprocess_sha256=core.sha(post_path),
                config_file=str(config_path), config_sha256=core.sha(config_path),
                mask_file=str(mask_path), mask_sha256=core.sha(mask_path),
                native_input_sha256=post['input_sha256']))
    core.require(len(matches) == 1, 'One unique complete h0.5/SC2/bulk14,14,40 baseline required; no implicit recomputation')
    return matches[0]


def _comparison_values(condition):
    metrics = condition['metrics']
    regions = condition['volume_metrics']['regions']
    target = regions['target']['statistics']
    superficial = regions['surface_0_5']['statistics']['maxTIS']
    core.require(superficial['p95'] > 0, 'Positive fixed superficial P95 comparison denominator required')
    values = {name: metrics[name] for name in GATE_PERCENT if name in metrics}
    values.update(roi_mean_TIS_V_m=target['maxTIS']['mean'],
        roi_p10_TIS_V_m=target['maxTIS']['p10'], roi_mean_RMS_V_m=target['RMS']['mean'],
        target_superficial_p95_ratio=target['maxTIS']['mean']/superficial['p95'])
    core.require(set(values) == set(GATE_PERCENT) and
                 all(math.isfinite(float(value)) and value >= 0 for value in values.values()),
                 'All12 fixed finite coupled-grid metrics required')
    return values


def compare_coupled(run, case, post):
    """Return all36 fixed gates; failures remain data, never a safety claim."""
    core.require(case['id'] == CASE_ID and post.get('status') == 'complete' and post.get('id') == CASE_ID,
                 'Exact completed coupled-grid case required')
    reference = case['coupled_baseline_reference']
    baseline_path = Path(reference['postprocess_path'])
    core.require(core.sha(baseline_path) == reference['postprocess_sha256'],
                 'Same-XY baseline scalar source changed')
    baseline = core.read(baseline_path)
    old_metadata, new_metadata = baseline['mesh_metadata'], post['mesh_metadata']
    for key in ('h_xy_mm', 'radius_mm', 'total_depth_mm', 'tissue_boundaries_mm',
                'field_reconstruction', 'source_resistance_ohm', 'source_peak_V', 'channels'):
        core.require(old_metadata.get(key) == new_metadata.get(key),
                     'Coupled comparison physical/normalization mismatch: '+key)
    core.require(old_metadata['sc_cells'] == 2 and old_metadata['bulk_layer_counts'] == [14, 14, 40] and
                 new_metadata['sc_cells'] == 8 and new_metadata['bulk_layer_counts'] == [18, 18, 56] and
                 new_metadata['cells'] == EXPECTED_CELLS,
                 'Coupled comparison must vary SC and bulk together at fixed h0.5')
    rows = []
    for wave in ('square_3h', 'sine', 'triangle_3h'):
        before = [item for item in baseline['conditions'] if item['waveform'] == wave]
        after = [item for item in post['conditions'] if item['waveform'] == wave]
        core.require(len(before) == len(after) == 1, 'One same-wave condition required per coupled comparison')
        core.require(before[0]['actual_fundamental_Hz'] == after[0]['actual_fundamental_Hz'] == [3000, 3030] and
                     before[0]['phase_deg'] == after[0]['phase_deg'] == [0., 0.] and
                     before[0]['source_Vpp_per_output'] == after[0]['source_Vpp_per_output'] == 1.,
                     'Same fixed waveform/carrier/phase/1Vpp condition required')
        old_values, new_values = _comparison_values(before[0]), _comparison_values(after[0])
        changes = {}
        for metric, limit in GATE_PERCENT.items():
            a, b = float(old_values[metric]), float(new_values[metric])
            change = 100*(b-a)/abs(a) if a else (0. if b == 0 else None)
            changes[metric] = dict(before=a, after=b, relative_change_percent=change,
                limit_percent=limit, passed=change is not None and abs(change) <= limit)
        rows.append(dict(waveform=wave, baseline_condition_id=before[0]['id'],
            coupled_condition_id=after[0]['id'], changes=changes,
            passed=all(item['passed'] for item in changes.values())))
    passed = all(row['passed'] for row in rows)
    return dict(schema='task1-coupled-grid-comparison-v1', run_id=Path(run).name, case_id=CASE_ID,
        status='passed_registered_coupled_comparison' if passed else 'failed_registered_coupled_comparison',
        all_registered_comparison_gates_passed=passed, gate_count=36, waveform_comparisons=rows,
        baseline_reference=reference, h_xy_mm=.5, baseline_sc_cells=2, coupled_sc_cells=8,
        baseline_bulk_counts=[14, 14, 40], coupled_bulk_counts=[18, 18, 56],
        physical_domain_and_source_unchanged=True,
        scope='One coupled SC/bulk refinement at fixed XY; cannot separate independent-axis error or prove continuum convergence',
        independent_axis_convergence_validated=False, continuum_convergence_validated=False,
        experimental_validation=False, safety_or_activation_validated=False,
        failed_gates_preserved=True, no_threshold_relaxation=True)


def prepare_coupled(run):
    """Prepare exactly one new coupled grid inside the root's existing lock."""
    start = time.monotonic()
    run = Path(run)
    core.paths_check(run)
    core.require(run.is_absolute() and run == run.resolve(), 'Canonical absolute coupled run required')
    core.require(not run.exists(), 'Never overwrite or retry a coupled prepared/partial run')
    _caller_owns_execution_lock()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    integrity = core.original_integrity()
    prereg_path = core.HIST/'preregistration.json'
    designs_path = core.HIST/'inputs/designs.json'
    old = core.read(prereg_path)
    template = copy.deepcopy(old['case_pool'][TEMPLATE_ID])
    old_config = core.HIST/'configs'/Path(template['config_file']).name
    old_mask = core.HIST/'masks'/Path(template['mask_file']).name
    core.require(core.sha(old_config) == template['config_sha256'] and
                 core.sha(old_mask) == template['mask_sha256'], 'Coupled frozen template input SHA differs')
    reference = _completed_same_xy_baseline(template)
    case = copy.deepcopy(template)
    case.update(id=CASE_ID, h_xy_mm=.5, sc_cells=8, bulk_counts=[18, 18, 56],
        channels=2, n_outputs=2, n_pads=4, java_class='CloudShapeBasis', postprocessor='legacy_native',
        exporter_class='SelectivityShapeBasis', design_id='baseline-square15', mesh_id='coupled_xy100_sc8_bulk',
        source_run_id=run.name, source_coating_nm=10, source_Rs_fit_window_Hz=500,
        historical_nominal_candidate_alias='coat010-f0500-minusRs-square_3h',
        nominal_reference_role='coupled_grid_sensitivity_of_historical_Best1_family',
        coupled_baseline_reference=reference, requires_coupled_comparison_after_postprocess=True,
        status='preregistered_not_executed')
    case.update(_mesh(case))
    bound = case['cells']*600
    core.require(case['cells'] == EXPECTED_CELLS and bound == EXPECTED_RAW_BOUND_BYTES and
                 bound <= core.LIMITS['max_batch_added_bytes'], 'Coupled786000cell/471600000byte bound differs')
    core.require(shutil.disk_usage(run.parent).free > 2*core.GIB+bound,
                 'Coupled raw output plus2GiB reserve unavailable')
    budgetpath = core.REPO/'runtime/task1-budget.json'
    budget = core.read(budgetpath) if budgetpath.exists() else dict(limit_seconds=6600, spent_seconds=0., runs=[])
    core.require(budget['limit_seconds'] == 6600 and budget['spent_seconds'] < 6600,
                 'Cumulative budget exhausted; no coupled-grid budget expansion')
    jdk = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
    javac = shutil.which('javac') or str(jdk/'javac')
    java = str(Path(javac).parent/'java')
    core.require(Path(javac).is_file() and Path(java).is_file(), 'Coupled Java compiler/runtime unavailable')
    run.mkdir()
    for directory in ('configs', 'masks', 'bases', 'cases', 'postprocess', 'logs', 'classes'):
        (run/directory).mkdir()
    core.write(run/'controller.json', dict(status='preparing', phase='coupled_grid_registration',
        pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now()))
    succeeded = False
    registration = None
    try:
        mask = run/'masks'/(CASE_ID+'.csv')
        shutil.copy2(old_mask, mask)
        core.require(core.sha(mask) == template['mask_sha256'], 'Coupled h0.5 mask bytes changed')
        config = run/'configs'/(CASE_ID+'.properties')
        changes = {'validation.sc_cells': '8', 'bulk.counts': '18,18,56', 'mask.path': str(mask)}
        config.write_bytes(_changed_config(old_config.read_bytes(), changes))
        case.update(config_file=str(config), config_sha256=core.sha(config),
                    mask_file=str(mask), mask_sha256=core.sha(mask))
        designs = {design['id']: design for design in core.read(designs_path)}
        case['design'] = copy.deepcopy(designs['baseline-square15'])
        case['design']['channels'] = 2
        case['design']['xy_mm'] = [pad['center_mm'] for pad in case['design']['pads']]
        case['circuit'] = dict(n_pads=4, n_outputs=2, n_signal_pads=2, n_return_pads=2,
            n_return_nodes=1, return_topology='all_return_pads_ideal_common_GND',
            source_Vpp_each=1., source_peak_V=.5, source_resistance_ohm=50.,
            source_phase_deg=[0., 0.], carrier_assignment_Hz=[3000, 3030], harmonics_Hz=[9000, 9090],
            pad_to_node={'0': 'out0', '1': 'out1', '2': 'GND', '3': 'GND'},
            inactive_source_at_other_frequencies='0 V through50 ohm',
            exclusive_source_return_pair_assumed=False)
        case['cache_signature'] = core.check_cached_operator(case, run)
        pins = core.source_pins()
        for path in (Path(__file__), core.REPO/'tools/task1_reference_registration.py',
                     core.REPO/'tools/task1_grouped_registration.py', prereg_path, designs_path, old_config, old_mask):
            pins[str(path)] = core.sha(path)
        for key in ('registration', 'case_record', 'postprocess'):
            pins[reference[key+'_path']] = reference[key+'_sha256']
        pins.update(reference['native_input_sha256'])

        def command(args, log):
            remaining = 6600-budget['spent_seconds']-(time.monotonic()-start)
            core.require(remaining > 0, 'Coupled cumulative preparation budget exhausted')
            core.require(shutil.disk_usage(run).free >= 2*core.GIB, 'Coupled2GiB preparation reserve')
            core.write(run/'controller.json', dict(status='preparing', phase='compile_or_analytic_selftest',
                command=args, pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now(),
                elapsed_seconds=time.monotonic()-start))
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
            core.require(core.sha(path) == expected, 'Coupled source/baseline input changed: '+path)
        registration = dict(schema='task1-cloud-finite-v1', batch_kind='one_coupled_grid_sensitivity',
            status='prepared', created_utc=core.now(),
            source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=core.REPO, text=True).strip(),
            historical_source_commit='8c3a30a778cc9bf19ccb52ca523598bff0a84650',
            package_integrity=integrity, limits=copy.deepcopy(core.LIMITS), gates=copy.deepcopy(core.GATES),
            cases=[case], new_PDE_conditions_maximum=1, expected_raw_bound_bytes=bound, java=java,
            source_and_input_sha256=pins, preparation_seconds=time.monotonic()-start,
            path_mapping=[dict(original_config=str(old_config), original_sha256=core.sha(old_config),
                new_config=str(config), new_sha256=core.sha(config), changed_fields=list(changes),
                original_mask=str(old_mask), new_mask=str(mask), mask_sha256=core.sha(mask),
                mask_bytes_unchanged=True, physical_material_contact_circuit_changed=False)],
            scientific_scope='One coupled SC/bulk grid check; unchanged4square top contact/10nmRs500/2outputs/commonGND/50ohm',
            coupled_grid_selection=dict(h_xy_mm=.5, sc_cells=8, bulk_counts=[18, 18, 56], cells=EXPECTED_CELLS,
                already_computed_same_xy_baseline=dict(h_xy_mm=.5, sc_cells=2, bulk_counts=[14, 14, 40], cells=550200),
                rejected_finer_xy_options=[
                    dict(h_xy_mm=50/120, sc_cells=4, bulk_counts=[14, 14, 40], cells=813888,
                         reason='exceeds fixed800000cell cap'),
                    dict(h_xy_mm=50/120, sc_cells=8, bulk_counts=[14, 14, 40], cells=859104,
                         reason='exceeds fixed800000cell cap')],
                reason='Fixed h0.5 allows simultaneous SC8 and bulk18/18/56 under800000cells without changing phantom size'),
            fixed_comparison_gate_percent=GATE_PERCENT, coupled_comparison_baseline=reference,
            comparison_waveforms=['square_3h', 'sine', 'triangle_3h'], fixed_gate_count=36,
            convergence=dict(field_ROI_percent=1, J_contact_voltage_percent=5, power_percent=2,
                coupled_comparison_pending=True, independent_axis_convergence_validated=False,
                continuum_convergence_validated=False, experimental_validation=False),
            storage=dict(native_location=str(run), persistent_backup_verified=False,
                retirement_of_old_environment_allowed=False),
            frozen_source_snapshot_owner='root core.freeze_sources once after this preparation',
            next_decision='Preserve all36 gate outcomes; coupled failure blocks adoption, passing this finite pair does not certify continuum convergence or safety')
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
        budgetpath.parent.mkdir(exist_ok=True)
        core.write(budgetpath, budget)
    print(json.dumps(dict(status='prepared', run=str(run), cases=[CASE_ID], cells=EXPECTED_CELLS,
        bound_bytes=bound, batch_kind='one_coupled_grid_sensitivity'), ensure_ascii=False))
    return registration
