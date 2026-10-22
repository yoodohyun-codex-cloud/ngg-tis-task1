"""Preregister two bounded single-frequency solver diagnostics, without import work.

The caller owns both global execution locks and freezes sources after preparation.
Original A/D files and the failed historical strict receipt remain immutable.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import task1_cloud_batch as core
from task1_grouped_registration import _caller_owns_execution_lock, _mesh

COARSE = 'residual-default-square15-coarse-3000'
FINE = 'residual-tight-square15-xy120-3000'
SOLVER_VERSION = 'literal-frozen-COCG-rtol-v1'
ARRAYS = ('field', 'potential', 'density', 'source', 'loss')
HELD_CASE = 'best1-square15-xy120'
HELD_RUN = 'cloud-reference-20261019T192000Z'


def _held_reference_proof(registration, case):
    """Narrow read-only exception for D, stopped before its case receipt write.

    This accepts calculated raw evidence as a diagnostic reference. It never
    creates a completion receipt or converts the historical reproduction failure.
    """
    run = registration.parent
    core.require(case['id'] == HELD_CASE and run.name == HELD_RUN,
                 'Only the explicitly held D fine reference may lack a case completion receipt')
    paths = [run/name for name in ('reference-comparison.json', 'controller.json', 'summary.json', 'failure.json')]
    core.require(all(path.is_file() and not path.is_symlink() for path in paths), 'Held D failure proof missing')
    comparison, controller, summary, failure = map(core.read, paths)
    core.require(comparison.get('status') == 'failed' and comparison.get('case_id') == HELD_CASE and
                 comparison.get('run_id') == run.name and comparison.get('matrix_relative_tolerance') == 1e-8 and
                 comparison.get('absolute_tolerance') == 1e-14 and
                 any(row.get('passed') is False for row in comparison.get('circuit_comparisons', [])),
                 'Held D historical strict comparison must remain failed')
    core.require(controller.get('status') == 'error' and controller.get('phase') == 'stopped' and
                 controller.get('current_case') == HELD_CASE and
                 controller.get('current_config_sha256') == case['config_sha256'],
                 'Held D controller does not prove stop at the registered fine case')
    for receipt in (summary, failure):
        core.require(receipt.get('status') == 'error' and receipt.get('run_id') == run.name and
                     receipt.get('failed_case') == HELD_CASE and receipt.get('registration_sha256') == core.sha(registration) and
                     receipt.get('error') == 'Historical Best1 mismatch; C1 not run before investigation' and
                     receipt.get('partial_evidence_preserved') is True,
                     'Held D error/registration proof differs')
    return {str(path): core.sha(path) for path in paths}


def _path(folder, name):
    choices = [path for path in (folder/name, folder/(name+'.gz')) if path.is_file()]
    core.require(len(choices) == 1 and not choices[0].is_symlink(), 'One canonical reference file required: '+name)
    return choices[0]


def _reference(case_id):
    matches = []
    for registration in (core.REPO/'data-native').glob('cloud-*/preregistration.json'):
        pre = core.read(registration)
        for case in pre.get('cases', []):
            if case.get('id') != case_id:
                continue
            record_path = registration.parent/'cases'/(case_id+'.json')
            held_pins = {}
            if record_path.is_file():
                record = core.read(record_path)
                if record.get('status') != 'complete':
                    continue
                post_path = Path(record['postprocess_path']).resolve()
                core.require(post_path.is_relative_to(registration.parent) and
                             core.sha(post_path) == record['postprocess_sha256'], 'Cached postprocess SHA/path differs')
            else:
                held_pins = _held_reference_proof(registration, case)
                post_path = registration.parent/'postprocess'/case_id/'summary.json'
                core.require(post_path.is_file() and not post_path.is_symlink(), 'Held D complete postprocess missing')
            post = core.read(post_path)
            core.require(post['id'] == case_id and post['status'] == 'complete', 'Cached reference not calculated')
            expected_manifest = hashlib.sha256(json.dumps(post['input_sha256'], sort_keys=True,
                separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
            core.require(post.get('input_manifest_sha256') == expected_manifest, 'Cached postprocess input manifest differs')
            folder = registration.parent/'bases'/case_id
            names = ['BASIS_COMPLETE', 'validation.json', 'mesh-metadata.json', 'grid.csv', 'contacts-3000.csv']
            names += [kind+'-3000.bin' for kind in ARRAYS]
            files = {name: str(_path(folder, name)) for name in names}
            pins = dict(held_pins)
            for path in files.values():
                expected = post['input_sha256'].get(path)
                core.require(expected is not None and core.sha(path) == expected, 'Cached native SHA differs: '+path)
                pins[path] = expected
            for key in ('config', 'mask'):
                path = Path(case[key+'_file'])
                core.require(core.sha(path) == case[key+'_sha256'], 'Cached physical input SHA differs')
                if key == 'config':
                    core.require(post['input_sha256'].get(str(path)) == case['config_sha256'],
                                 'Cached postprocess config SHA differs')
                else:
                    # Frozen postprocessing hashes the config, not the mask again.
                    # That pinned config explicitly commits to the mask digest.
                    properties = dict(line.split('=', 1) for line in Path(case['config_file']).read_text().splitlines()
                                      if '=' in line and not line.startswith(('#', '!')))
                    core.require(properties.get('mask.sha256') == case['mask_sha256'],
                                 'Cached config mask SHA differs')
                pins[str(path)] = case[key+'_sha256']
            for path in (registration, post_path, *([record_path] if record_path.is_file() else [])):
                pins[str(path)] = core.sha(path)
            metadata = core.read(files['mesh-metadata.json'])
            core.require(metadata['exporter_class'] == 'SelectivityShapeBasis' and metadata['channels'] == 2 and
                         metadata['config_sha256'] == case['config_sha256'] and
                         metadata['frequencies_Hz'] == [3000, 3030, 9000, 9090], 'Cached baseline exporter differs')
            validation = core.read(files['validation.json'])
            core.require(all(isinstance(validation[key], (int, float)) and 0 <= validation[key] <= limit
                             for key, limit in core.GATES.items()), 'Cached native numerical gate differs')
            matches.append((copy.deepcopy(case), dict(run_id=registration.parent.name, case_id=case_id,
                basis_folder=str(folder), files=files, input_sha256=pins,
                reference_status='held_computed_only' if held_pins else 'case_calculated_complete',
                case_completion_receipt_present=not bool(held_pins), historical_strict_reproduction_passed=False,
                postprocess_path=str(post_path), postprocess_sha256=core.sha(post_path))))
    core.require(len(matches) == 1, 'One unique completed cached physical reference required: '+case_id)
    return matches[0]


def _config(data, changes):
    """Preserve all original lines, changing only declared keys; append new solver keys."""
    seen = set()
    result = []
    for line in data.decode('utf-8').splitlines(keepends=True):
        key = line.split('=', 1)[0] if '=' in line and not line.startswith(('#', '!')) else None
        if key in changes:
            core.require(key not in seen, 'Duplicate changed configuration field')
            line = key+'='+changes[key]+'\n'
            seen.add(key)
        result.append(line)
    core.require({'frequencies', 'mask.path'}.issubset(seen), 'Original frequency/mask fields missing')
    core.require(set(changes)-seen <= {'solver.relative_tolerance', 'solver.max_iterations'}, 'Unexpected new physics field')
    if result and not result[-1].endswith(('\n', '\r')):
        result[-1] += '\n'
    result += [key+'='+value+'\n' for key, value in changes.items() if key not in seen]
    return ''.join(result).encode('utf-8')


def prepare_residual(run):
    started = time.monotonic()
    run = Path(run)
    core.paths_check(run)
    core.require(run.is_absolute() and run == run.resolve() and not run.exists(), 'Fresh canonical residual run required')
    _caller_owns_execution_lock()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    integrity = core.original_integrity()
    coarse, coarse_ref = _reference('baseline-square15-coarse')
    fine, fine_ref = _reference('best1-square15-xy120')
    core.require((coarse['h_xy_mm'], coarse['cells']) == (1.25, 88480) and
                 (fine['h_xy_mm'], fine['cells']) == (50/120, 791280) and
                 all(c['sc_cells'] == 2 and c['bulk_counts'] == [14, 14, 40] for c in (coarse, fine)),
                 'Exact A coarse / held D fine physical meshes required')
    hold_path = Path(fine_ref['basis_folder']).parents[1]/'reference-comparison.json'
    core.require(core.read(hold_path)['status'] == 'failed', 'Original D strict failure must remain preserved')
    historical = core.HIST/'released-circuits/reference-best1-final'
    historical_files = {kind: str(_path(historical, kind+'-3000.bin')) for kind in ('source', 'loss')}
    budget_path = core.REPO/'runtime/task1-budget.json'
    budget = core.read(budget_path)
    core.require(budget['limit_seconds'] == 6600 and budget['spent_seconds'] < 6600, 'Cumulative budget exhausted')
    bound = sum(c['cells']*200+4*1024**2 for c in (coarse, fine))
    core.require(bound <= core.LIMITS['max_batch_added_bytes'] and
                 shutil.disk_usage(run.parent).free >= 2*core.GIB+bound, 'Residual raw allowance/reserve unavailable')
    jdk = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
    javac = shutil.which('javac') or str(jdk/'javac')
    java = str(Path(javac).parent/'java')
    core.require(Path(javac).is_file() and Path(java).is_file(), 'Java compiler/runtime unavailable')
    run.mkdir()
    for name in ('configs', 'masks', 'bases', 'cases', 'postprocess', 'logs', 'classes'):
        (run/name).mkdir()
    core.write(run/'controller.json', dict(status='preparing', updated_utc=core.now(), pid=os.getpid(),
        proc_start_ticks=core.ticks(os.getpid()), phase='register_residual_diagnostic'))
    registration = None
    succeeded = False
    try:
        cases, mappings = [], []
        pins = core.source_pins()
        pins[str(hold_path)] = core.sha(hold_path)
        for path in historical_files.values():
            pins[path] = core.sha(path)
        for old, reference, case_id, tolerance in ((coarse, coarse_ref, COARSE, 1e-9), (fine, fine_ref, FINE, 1e-11)):
            case = copy.deepcopy(old)
            for key in list(case):
                if key.startswith('requires_') or key.startswith('historical_nominal_center_'):
                    del case[key]
            mask = run/'masks'/(case_id+'.csv')
            shutil.copyfile(old['mask_file'], mask)
            core.require(core.sha(mask) == old['mask_sha256'], 'Canonical original mask bytes changed')
            changes = {'frequencies': '3000', 'mask.path': str(mask),
                       'solver.relative_tolerance': str(tolerance), 'solver.max_iterations': '12000'}
            config = run/'configs'/(case_id+'.properties')
            config.write_bytes(_config(Path(old['config_file']).read_bytes(), changes))
            case.update(id=case_id, java_class='ResidualShapeBasis', exporter_class='ResidualShapeBasis',
                postprocessor='residual_diagnostic', channels=2, n_outputs=2, n_pads=4,
                frequencies_Hz=[3000], requested_relative_tolerance=tolerance, solver_max_iterations=12000,
                solver_version=SOLVER_VERSION, config_file=str(config), config_sha256=core.sha(config),
                mask_file=str(mask), mask_sha256=core.sha(mask), source_run_id=run.name,
                diagnostic_reference=reference, diagnostic_role='producer_regression' if case_id == COARSE else 'tighter_stopping_parameter',
                requires_residual_producer_regression_before_next=(case_id == COARSE),
                historical_matrix_files=historical_files if case_id == FINE else {}, status='preregistered_not_executed')
            case.update(_mesh(case))
            historical_carriers = case['circuit'].pop('carrier_assignment_Hz', None)
            case['circuit'].update(actual_diagnostic_frequency_Hz=3000, historical_carrier_assignment_Hz=historical_carriers,
                carrier_assignment_Hz=[3000, 3000],
                source_excitation_definition='Two separate unit basis RHS at3000Hz; not simultaneous two-carrier TIS',
                full_TIS_waveform_claimed=False,
                basis_source_solves=2, source_Vpp_each=1., source_peak_V=.5, source_resistance_ohm=50.)
            case['cache_signature'] = core.check_cached_operator(case, run)
            cases.append(case)
            pins.update(reference['input_sha256'])
            mappings.append(dict(source_config=old['config_file'], source_config_sha256=old['config_sha256'],
                new_config=str(config), new_config_sha256=case['config_sha256'], changed_fields=list(changes),
                source_mask=old['mask_file'], source_mask_sha256=old['mask_sha256'],
                new_mask=str(mask), new_mask_sha256=core.sha(mask), mask_operation='byte-identical copy; no regenerated geometry'))

        def command(args, log):
            remaining = 6600-budget['spent_seconds']-(time.monotonic()-started)
            core.require(remaining > 0 and shutil.disk_usage(run).free >= 2*core.GIB, 'Preparation time/disk exhausted')
            core.write(run/'controller.json', dict(status='preparing', phase='compile_or_analytic_selftest',
                command=args, pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now()))
            subprocess.run(args, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=min(120., remaining))

        with (run/'logs/compile-selftest.log').open('x') as log:
            command([javac, '-J-Xmx2g', '-J-XX:ActiveProcessorCount=1', '-encoding', 'UTF-8', '-d', str(run/'classes'),
                *[str(core.SOURCE/name) for name in ('TisSweep.java', 'ExploreBasis.java', 'SelectivityShapeBasis.java')],
                str(core.REPO/'tools/java/CloudShapeBasis.java'), str(core.REPO/'tools/java/ResidualShapeBasis.java')], log)
            for name in ('CloudShapeBasis', 'ResidualShapeBasis'):
                command([java, '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1',
                    '-cp', str(run/'classes'), name, '--selftest'], log)
        for path in [Path(__file__), core.REPO/'tools/task1_residual_postprocess.py',
                     core.REPO/'tools/java/ResidualShapeBasis.java', *(run/'configs').glob('*'),
                     *(run/'masks').glob('*'), *(run/'classes').glob('*')]:
            pins[str(path)] = core.sha(path)
        for path, expected in pins.items():
            core.require(core.sha(path) == expected, 'Source/reference pin changed: '+path)
        registration = dict(schema='task1-cloud-finite-v1', batch_kind='single_frequency_residual_diagnostic',
            status='prepared', created_utc=core.now(),
            source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=core.REPO, text=True).strip(),
            historical_source_commit='8c3a30a778cc9bf19ccb52ca523598bff0a84650', package_integrity=integrity,
            limits=copy.deepcopy(core.LIMITS), gates=copy.deepcopy(core.GATES), cases=cases,
            java=java, source_and_input_sha256=pins, preparation_seconds=time.monotonic()-started,
            new_PDE_conditions_maximum=2, total_basis_RHS_solves_maximum=4, expected_raw_bound_bytes=bound,
            raw_bound_note='200B/cell plus4MiB/case; no assumed compression savings;1frequency2outputs',
            path_mapping=mappings, frozen_source_snapshot_owner='root core.freeze_sources once',
            diagnostic_contract=dict(frequency_Hz=3000, full_TIS=False, ROI_or_envelope_claimed=False,
                producer_regression=dict(relative_global_maxnorm=1e-8, absolute=1e-14, exact_grid_and_contact_bytes=True),
                historical_strict_gate=dict(relative_componentwise=1e-8, absolute_componentwise=1e-14,
                    criterion='abs(new_i-old_i) <= absolute + relative*abs(old_i)', all_failed_entries_preserved=True),
                normwise_metrics='separate diagnostics; never substitute for historical componentwise gate',
                numerical_passivity_floor_absolute=1e-14, numerical_passivity_floor_relative=1e-10),
            historical_strict_failure_hold=dict(path=str(hold_path), sha256=core.sha(hold_path),
                original_status='failed', reclassified=False, claimed_resolved=False, old_fine_C1_promoted=False),
            scientific_scope='New producer regression then fixed-operator tighter solver stop; not optimization or independent solver validation',
            storage=dict(native_location=str(run), persistent_backup_verified=False, retirement_of_old_environment_allowed=False),
            next_decision='Only after default producer regression passes execute tight fine; preserve strict comparison outcome and use residual/change norms to select next bounded investigation')
        core.write(run/'preregistration.json', registration)
        core.write(run/'controller.json', dict(status='prepared', updated_utc=core.now()))
        succeeded = True
    except BaseException as error:
        core.write(run/'preparation-failure.json', dict(status='preparation_failed_preserved',
            error_type=type(error).__name__, error=str(error), observed_utc=core.now(), automatic_retry=False))
        raise
    finally:
        elapsed = registration['preparation_seconds'] if succeeded else time.monotonic()-started
        budget['spent_seconds'] += elapsed
        budget['runs'].append(dict(run_id=run.name, stage='preparation', seconds=elapsed,
            status='prepared' if succeeded else 'preparation_failed_preserved'))
        core.write(budget_path, budget)
    print(json.dumps(dict(status='prepared', run=str(run), cases=[c['id'] for c in cases],
        expected_raw_bound_bytes=bound, full_TIS=False)))
    return registration
