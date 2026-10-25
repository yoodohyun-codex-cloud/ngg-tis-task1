"""Register one finite grouped-pad batch under the root controller's lock.

Imports only the standard-library controller. No research module is imported,
no PDE is executed, and the earlier geometry-only plan remains unchanged.
Compilation and analytic adapter selftests are explicit bounded preparation.
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


RECEIPT_CODE_FILES = (
    'tools/java/GroupedPadBasis.java',
    'tools/java/CloudShapeBasis.java',
    'tools/task1_grouped_postprocess.py',
    'tools/task1_grouped_geometry.py',
    'tools/task1_cloud_batch.py',
    'tools/task1_grouped_registration.py',
    'tests/test_task1_grouped_postprocess.py',
)
RECEIPT_CHECKS = (
    'raw_physical_ids', 'pad_node_mapping', 'node_current_sums',
    'physical_contact_areas', 'array_corruption_rejection', 'compiler',
    'original_operator_E_loss_regression', 'baseline_reproduction',
)


def _caller_owns_execution_lock():
    """Verify both lock kinds on the same regular file via our /proc fdinfo."""
    lock = core.REPO/'.task1-execution.lock'
    core.require(lock.is_file() and not lock.is_symlink(), 'Root global execution lock missing')
    pid = str(os.getpid())
    found = set()
    for fd in Path('/proc/self/fd').iterdir():
        try:
            if not os.path.samefile(fd, lock):
                continue
            for line in (Path('/proc/self/fdinfo')/fd.name).read_text().splitlines():
                parts = line.split()
                if (len(parts) == 9 and parts[0] == 'lock:' and parts[2] in ('FLOCK', 'POSIX')
                        and parts[3:6] == ['ADVISORY', 'WRITE', pid] and parts[7:] == ['0', 'EOF']):
                    found.add(parts[2])
        except (FileNotFoundError, OSError):
            continue
    core.require(found == {'FLOCK', 'POSIX'}, 'Caller must own both root flock and POSIX execution lock')


def validate_receipt(path):
    path = Path(path).resolve()
    core.require(path.is_file() and not path.is_symlink(), 'Regular grouped validation receipt required')
    receipt = core.read(path)
    core.require(receipt.get('status') == 'passed', 'Grouped validation receipt must have status passed')
    codes = receipt.get('code_sha256', {})
    for relative in RECEIPT_CODE_FILES:
        source = core.REPO/relative
        core.require(source.is_file() and not source.is_symlink() and codes.get(relative) == core.sha(source),
                     'Grouped receipt code SHA mismatch: '+relative)
    checks = receipt.get('checks', {})
    core.require(all(checks.get(check) is True for check in RECEIPT_CHECKS),
                 'Grouped validation receipt lacks required explicit passed checks')
    logs = receipt.get('test_logs', [])
    core.require(isinstance(logs, list) and bool(logs), 'Hashed grouped compiler/test evidence required')
    log_pins = {}
    for item in logs:
        evidence = Path(item['path']).resolve()
        core.require(evidence.is_file() and not evidence.is_symlink() and core.sha(evidence) == item.get('sha256'),
                     'Grouped validation evidence SHA mismatch: '+str(evidence))
        log_pins[str(evidence)] = item['sha256']
    return receipt, log_pins


def _mesh(case):
    h = float(case['h_xy_mm'])
    core.require(math.isfinite(h) and h > 0, 'Grouped XY spacing must be positive finite')
    nx = round(50/h)
    sc = int(case['sc_cells'])
    bulk = list(case['bulk_counts'])
    core.require(math.isfinite(h) and h > 0 and 2 <= nx <= 120 and abs(nx*h-50) <= 1e-10,
                 'Registered grouped XY must tile fixed50mm diameter')
    core.require(sc in (2, 4, 8) and bulk in ([14, 14, 40], [18, 18, 56]),
                 'Unregistered grouped SC/bulk grid')
    nxy = sum((-25+(i+.5)*h)**2+(-25+(j+.5)*h)**2 < 625 for j in range(nx) for i in range(nx))
    cells = nxy*(sc+sum(bulk))
    core.require(cells <= core.LIMITS['max_cells'], 'Grouped cell budget exceeds800000')
    return dict(cells=cells, nx=nx, volume_metadata=dict(h_xy_mm=h, sc_cells=sc,
        bulk_layer_counts=bulk, layer_counts=[sc, *bulk], radius_mm=25.,
        geometry_volume_tolerance_relative=.01 if h == 1.25 else .002,
        target_volume_tolerance_relative=.001))


def prepare_grouped(run, ids, plan_path, receipt_path):
    """Called by task1_cloud_batch.py inside its existing global lock context."""
    start = time.monotonic()
    run = Path(run)
    core.paths_check(run)
    core.require(run.is_absolute() and run == run.resolve(), 'Canonical absolute new grouped run required')
    core.require(not run.exists(), 'Never overwrite or retry a grouped prepared/partial run')
    _caller_owns_execution_lock()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    integrity = core.original_integrity()
    receipt_path = Path(receipt_path).resolve()
    receipt, evidence_pins = validate_receipt(receipt_path)
    plan_path = Path(plan_path).resolve()
    old = core.read(plan_path)
    core.require(old.get('schema') == 'task1_grouped_geometry_v1' and old.get('pde_jobs') == 0 and
                 old.get('status') == 'prepared_not_executed' and old.get('execution_allowed') is False,
                 'Original geometry-only nonexecution evidence required; it is not rewritten')
    core.require(old['generator_sha256'] == core.sha(core.REPO/'tools/task1_grouped_geometry.py'),
                 'Grouped geometry generator source pin changed')
    original_config = Path(old['input_source_config']).resolve()
    core.require(original_config.is_relative_to(core.REPO) and
                 core.sha(original_config) == old['input_source_config_sha256'],
                 'Grouped common tissue/contact source config changed')
    core.require(1 <= len(ids) <= 5 and len(set(ids)) == len(ids), 'Finite unique1..5 grouped cases required')
    pool = {case['id']: case for case in old['cases']}
    core.require(len(pool) == len(old['cases']) and all(ident in pool for ident in ids),
                 'Requested grouped IDs must be unique explicit geometry cases')
    selected = [copy.deepcopy(pool[ident]) for ident in ids]
    core.require(selected[0].get('control') == 'original_four_square' and selected[0]['n_pads'] == 4,
                 'First grouped case must be the costed original-four-square producer regression')
    for case in selected:
        core.require(case['n_pads'] in (4, 8, 12, 16) and case['n_outputs'] == 2 and
                     case['n_return_nodes'] == 1 and case['exporter_class'] == 'GroupedPadBasis' and
                     case['frequencies_Hz'] == [3000, 3030, 9000, 9090] and
                     case['area_mode'] == 'equal_total_area_900mm2', 'Grouped finite family topology/scope differs')
        case.update(_mesh(case))
        core.require(core.sha(case['config_file']) == case['config_sha256'] and
                     core.sha(case['mask_file']) == case['mask_sha256'], 'Grouped geometry input SHA differs')
    raw_bound = sum(case['cells']*600 for case in selected)
    core.require(raw_bound <= core.LIMITS['max_batch_added_bytes'], 'Grouped raw bound exceeds2GiB batch cap')
    core.require(shutil.disk_usage(run.parent).free > 2*core.GIB+raw_bound,
                 'Grouped reserve plus conservative raw output bound unavailable')
    budgetpath = core.REPO/'runtime/task1-budget.json'
    budget = core.read(budgetpath) if budgetpath.exists() else dict(limit_seconds=6600, spent_seconds=0., runs=[])
    core.require(budget['limit_seconds'] == 6600 and budget['spent_seconds'] < 6600,
                 'Cumulative grouped budget unavailable; no automatic expansion')
    jdk = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
    javac = shutil.which('javac') or str(jdk/'javac')
    java = str(Path(javac).parent/'java')
    core.require(Path(javac).is_file() and Path(java).is_file(), 'Grouped Java compiler/runtime unavailable')
    run.mkdir()
    for directory in ('configs', 'masks', 'bases', 'cases', 'postprocess', 'logs', 'classes'):
        (run/directory).mkdir()
    core.write(run/'controller.json', dict(status='preparing', phase='copying_registered_inputs',
        pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now()))
    succeeded = False
    registration = None
    try:
        mapping = []
        for case in selected:
            old_config, old_mask = Path(case['config_file']).resolve(), Path(case['mask_file']).resolve()
            mask = run/'masks'/old_mask.name
            core.require(not mask.exists(), 'Unique grouped mask target required')
            shutil.copy2(old_mask, mask)
            old_bytes = old_config.read_bytes()
            values = [line.split(b'=', 1)[1].rstrip(b'\r\n') for line in old_bytes.splitlines(keepends=True)
                      if line.startswith(b'mask.path=')]
            core.require(len(values) == 1 and Path(values[0].decode()).resolve() == old_mask,
                         'Unique grouped source mask.path must match explicit source mask')
            old_token = b'mask.path='+values[0]
            new_token = b'mask.path='+str(mask).encode()
            core.require(old_bytes.count(old_token) == 1, 'Unique grouped path substitution required')
            new_bytes = old_bytes.replace(old_token, new_token)
            core.require(new_bytes.replace(new_token, old_token) == old_bytes,
                         'Grouped config changes must be only mask.path bytes')
            config = run/'configs'/(case['id']+'.properties')
            config.write_bytes(new_bytes)
            mapping.append(dict(original_config=str(old_config), original_sha256=core.sha(old_config),
                new_config=str(config), new_sha256=core.sha(config), changed_fields=['mask.path'],
                original_mask_reference=values[0].decode(), new_mask=str(mask), mask_sha256=core.sha(mask)))
            nodes = case['pad_node_ids']
            case.update(config_file=str(config), config_sha256=core.sha(config), mask_file=str(mask),
                mask_sha256=core.sha(mask), source_run_id=run.name, channels=2,
                java_class='GroupedPadBasis', postprocessor='grouped', status='preregistered_not_executed',
                source_coating_nm=10, source_Rs_fit_window_Hz=500,
                design_id=case['id'], mesh_id=f"grouped_xy{case['nx']}_sc{case['sc_cells']}",
                requires_original_producer_regression_before_next=case.get('control') == 'original_four_square')
            case['design'] = dict(id=case['id'], channels=2, pads=copy.deepcopy(case['pads']),
                                  xy_mm=[[pad['x_mm'], pad['y_mm']] for pad in case['pads']])
            case['cache_signature'] = core.check_cached_operator(case, run)
            case['circuit'] = dict(n_pads=case['n_pads'], n_outputs=2,
                n_signal_pads=sum(node >= 0 for node in nodes), n_return_pads=nodes.count(-1),
                n_return_nodes=1, return_topology='all_return_pads_ideal_common_GND',
                source_Vpp_each=1., source_peak_V=.5, source_resistance_ohm=50.,
                source_phase_deg=[0., 0.], carrier_assignment_Hz=[3000, 3030], harmonics_Hz=[9000, 9090],
                pad_to_node={str(pad): 'GND' if node < 0 else f'out{node}' for pad, node in enumerate(nodes)},
                inactive_source_at_other_frequencies='0 V through50 ohm',
                exclusive_source_return_pair_assumed=False)
        pins = core.source_pins()
        pins.update({str(core.REPO/relative): core.sha(core.REPO/relative) for relative in RECEIPT_CODE_FILES})
        pins.update(evidence_pins)
        pins[str(plan_path)] = core.sha(plan_path)
        pins[str(receipt_path)] = core.sha(receipt_path)
        pins[str(original_config)] = core.sha(original_config)
        reference = receipt.get('baseline_reference', {})
        reference_case = Path(reference.get('case_path', ''))
        reference_basis = Path(reference.get('basis_dir', ''))
        core.require(reference_case.is_file() and core.sha(reference_case) == reference.get('case_sha256'),
                     'Exact reproduced baseline case pin required')
        baseline_record = core.read(reference_case)
        core.require(baseline_record['status'] == 'complete', 'Baseline producer not complete')
        pins[str(reference_case)] = core.sha(reference_case)
        for name, item in baseline_record['native_files'].items():
            path = reference_basis/name
            core.require(path.is_file() and core.sha(path) == item['sha256'], 'Baseline native source changed '+name)
            pins[str(path)] = item['sha256']

        def command(args, log):
            remaining = 6600-budget['spent_seconds']-(time.monotonic()-start)
            core.require(remaining > 0, 'Cumulative budget exhausted during grouped preparation')
            core.require(shutil.disk_usage(run).free >= 2*core.GIB, 'Grouped preparation disk reserve2GiB')
            core.write(run/'controller.json', dict(status='preparing', phase='compile_or_analytic_selftest',
                command=args, pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()),
                updated_utc=core.now(), elapsed_seconds=time.monotonic()-start))
            subprocess.run(args, check=True, stdout=log, stderr=subprocess.STDOUT,
                           timeout=min(120., remaining))

        with (run/'logs/compile-selftest.log').open('x') as log:
            command([javac, '-J-Xmx2g', '-J-XX:ActiveProcessorCount=1', '-encoding', 'UTF-8',
                '-d', str(run/'classes'), str(core.SOURCE/'TisSweep.java'), str(core.SOURCE/'ExploreBasis.java'),
                str(core.SOURCE/'SelectivityShapeBasis.java'), str(core.REPO/'tools/java/CloudShapeBasis.java'),
                str(core.REPO/'tools/java/GroupedPadBasis.java')], log)
            for adapter in ('CloudShapeBasis', 'GroupedPadBasis'):
                command([java, '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1',
                         '-cp', str(run/'classes'), adapter, '--selftest'], log)
        for path in [*(run/'configs').glob('*'), *(run/'masks').glob('*'), *(run/'classes').glob('*')]:
            pins[str(path)] = core.sha(path)
        for path, expected in pins.items():
            core.require(core.sha(path) == expected, 'Grouped pinned input changed during preparation: '+path)
        preparation_seconds = time.monotonic()-start
        registration = dict(schema='task1-cloud-finite-v1', batch_kind='grouped_physical_pads',
            status='prepared', created_utc=core.now(),
            source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=core.REPO, text=True).strip(),
            historical_source_commit='8c3a30a778cc9bf19ccb52ca523598bff0a84650',
            package_integrity=integrity, limits=copy.deepcopy(core.LIMITS), gates=copy.deepcopy(core.GATES),
            cases=selected, expected_raw_bound_bytes=raw_bound, java=java,
            source_and_input_sha256=pins, preparation_seconds=preparation_seconds, path_mapping=mapping,
            grouped_validation_receipt=dict(path=str(receipt_path), sha256=core.sha(receipt_path)),
            original_geometry_plan=dict(path=str(plan_path), sha256=core.sha(plan_path),
                original_execution_allowed=False, original_status=old['status'], source_bytes_modified=False,
                new_registration_resolves_subset_of_blockers=list(old.get('execution_blockers', []))),
            scientific_scope='New finite grouped-pad PDEs; exactly2 common-ground50ohm outputs; later3kHz waveform branch only',
            producer_regression=dict(first_case_id=selected[0]['id'], additional_PDE_cost=1,
                reason='Actual GroupedPadBasis producer regression against already-reproduced original four-square native basis',
                before_advancing_to_other_geometries=True, comparison_tolerance_relative=1e-8,
                comparison_tolerance_absolute=1e-14, reference=receipt.get('baseline_reference')),
            historical_comparison=dict(relative_scalar_tolerance=1e-8, source_loss_matrix_tolerance=1e-8,
                allow_absolute_error_near_zero=1e-14,
                gate='Original four-square producer regression must match frozen same-grid E/phi/source/loss before next case'),
            convergence=dict(field_ROI_percent=1, J_contact_voltage_percent=5, power_percent=2,
                mesh_convergence_validated=False, experimental_validation=False),
            storage=dict(native_location=str(run), persistent_backup_verified=False,
                retirement_of_old_environment_allowed=False),
            next_decision='Compare original4square,new4rectangle and8/12/16 at rawvoltage/equalpower/equalburden; no adoption until convergence')
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
    print(json.dumps(dict(status='prepared', run=str(run), cases=ids,
                          bound_bytes=raw_bound, batch_kind='grouped_physical_pads'), ensure_ascii=False))
    return registration
