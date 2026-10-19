"""Finite Task 1 reconstruction controller; frozen research inputs stay unchanged.

prepare registers unique immutable inputs. execute owns the one global lock,
uses one CPU, and never retries an attempted run. Native output is local evidence,
not a verified persistent backup. No import of research modules during inventory.
"""
from __future__ import annotations

import argparse
import copy
import csv
from datetime import datetime, timezone
import fcntl
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'tis-java'
HIST = SOURCE / 'runs/selectivity-design-20261019T155933Z'
GIB = 1024**3
LIMITS = dict(cpu=1, concurrent_solves=1, max_cells=800000,
              per_condition_seconds=600, cumulative_seconds=6600,
              java_heap_bytes=2*GIB, aggregate_rss_bytes=3*GIB,
              minimum_free_disk_bytes=2*GIB, max_batch_added_bytes=2*GIB)
GATES = dict(max_residual=2e-7, max_power_error=2e-7,
             max_current_error=2e-6, max_area_relative_error=1e-10,
             max_interface_normal_current_relative_error=2e-7)


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def write(path, obj):
    path = Path(path)
    tmp = path.with_name(path.name + '.partial')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    tmp.replace(path)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def ticks(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])


def rss(pid):
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return int(line.split()[1])*1024
    except FileNotFoundError:
        pass
    return 0


def original_integrity():
    index = read(REPO/'PACKAGE_INDEX.json')
    for item in index['files']:
        p = REPO/item['path']
        require(p.is_file() and not p.is_symlink(), 'Missing original '+item['path'])
        require(p.stat().st_size == item['bytes'] and sha(p) == item['sha256'],
                'Original payload changed '+item['path'])
    return dict(status='passed', files=len(index['files']),
                bytes=sum(p['bytes'] for p in index['files']),
                scope='All original indexed bytes; explicitly allows new files. No numerical claim.')


def paths_check(run):
    require(run.parent == REPO/'data-native' and run.name.startswith('cloud-'),
            'New run must be REPO/data-native/cloud-*')
    require(not run.is_symlink(), 'Run must not be a symlink')


def source_pins():
    files = [p for p in SOURCE.glob('*.py') if not p.name.startswith('test_')]
    files += [SOURCE/p for p in ('TisSweep.java', 'ExploreBasis.java', 'SelectivityShapeBasis.java')]
    files += [Path(__file__), REPO/'tools/java/CloudShapeBasis.java']
    files += [REPO/name for name in ('tools/task1_producer_regression.py',
              'tools/task1_grouped_postprocess.py', 'tools/task1_grouped_registration.py',
              'tools/task1_reference_registration.py', 'tools/task1_coupled_registration.py',
              'tools/task1_c1_coupled_registration.py')
              if (REPO/name).is_file()]
    return {str(p): sha(p) for p in files}


def operator_signature(case):
    """Ignore portable paths, retain physical inputs and actual producer code."""
    values = {}
    for line in Path(case['config_file']).read_text().splitlines():
        if '=' in line and not line.startswith(('#', '!')):
            key, value = line.split('=', 1)
            if key != 'mask.path':
                values[key] = value
    producer = case.get('java_class', 'CloudShapeBasis')
    files = [SOURCE/name for name in ('TisSweep.java', 'ExploreBasis.java', 'SelectivityShapeBasis.java')]
    if producer == 'GroupedPadBasis':
        files.append(REPO/'tools/java/GroupedPadBasis.java')
    payload = dict(config=values, mask_sha256=sha(case['mask_file']), producer=producer,
                   numerical_code_sha256={p.name: sha(p) for p in files})
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def check_cached_operator(case, run):
    signature = operator_signature(case)
    for path in (REPO/'data-native').glob('cloud-*/preregistration.json'):
        if path.parent == run:
            continue
        prior = read(path)
        for old in prior['cases']:
            record = path.parent/'cases'/(old['id']+'.json')
            if record.exists() and read(record).get('status') == 'complete':
                if old.get('cache_signature', operator_signature(old)) == signature:
                    raise ValueError('Completed operator already exists; reuse '+str(record))
    return signature


def freeze_sources(run):
    pre = read(run/'preregistration.json')
    manifest = {}
    for name, expected in pre['source_and_input_sha256'].items():
        source = Path(name)
        if source.is_relative_to(REPO) and source.suffix in ('.py', '.java'):
            require(sha(source) == expected, 'Source drift before freezing '+name)
            target = run/'frozen-source'/source.relative_to(REPO)
            target.parent.mkdir(parents=True, exist_ok=True)
            require(not target.exists(), 'Never overwrite frozen source')
            shutil.copy2(source, target)
            manifest[name] = dict(path=str(target), sha256=expected)
    write(run/'frozen-source-manifest.json', dict(source_commit=pre['source_commit'], files=manifest))


def prepare(run, ids):
    start = time.monotonic()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    paths_check(run)
    integrity = original_integrity()
    require(1 <= len(ids) <= 6 and len(set(ids)) == len(ids), 'Finite unique 1..6 cases required')
    old = read(HIST/'preregistration.json')
    require(all(i in old['case_pool'] and not old['case_pool'][i].get('existing_reference') for i in ids),
            'Only explicitly packaged fresh-compute historical cases supported')
    require(not run.exists(), 'Never overwrite or retry a prepared/partial run')
    run.mkdir(parents=True)
    for d in ('configs', 'masks', 'bases', 'cases', 'postprocess', 'logs', 'classes'):
        (run/d).mkdir()
    designs = {d['id']: d for d in read(HIST/'inputs/designs.json')}
    cases, mapping = [], []
    for ident in ids:
        case = copy.deepcopy(old['case_pool'][ident])
        old_config = HIST/'configs'/Path(case['config_file']).name
        old_mask = HIST/'masks'/Path(case['mask_file']).name
        require(sha(old_config) == case['config_sha256'], 'Historical config pin differs')
        require(sha(old_mask) == case['mask_sha256'], 'Historical mask pin differs')
        mask = run/'masks'/old_mask.name
        if not mask.exists():
            shutil.copy2(old_mask, mask)
        config = run/'configs'/(ident+'.properties')
        old_text = old_config.read_text()
        old_value = next(line.split('=', 1)[1] for line in old_text.splitlines() if line.startswith('mask.path='))
        require(old_text.count('mask.path='+old_value) == 1, 'Unique path replacement required')
        config.write_text(old_text.replace('mask.path='+old_value, 'mask.path='+str(mask)))
        require(config.read_text().replace(str(mask), old_value) == old_text, 'Non-path configuration mutation')
        mapping.append(dict(original_config=str(old_config), original_sha256=sha(old_config),
                            new_config=str(config), new_sha256=sha(config),
                            changed_fields=['mask.path'], original_mask_reference=old_value,
                            new_mask=str(mask), mask_sha256=sha(mask)))
        case.update(config_file=str(config), config_sha256=sha(config),
                    mask_file=str(mask), source_run_id=run.name,
                    source_coating_nm=10, source_Rs_fit_window_Hz=500)
        case['design'] = copy.deepcopy(case.get('control_design') or designs[case['design_id']])
        case['design']['channels'] = case['channels']
        case['design']['xy_mm'] = [p['center_mm'] for p in case['design']['pads']]
        case['cache_signature'] = check_cached_operator(case, run)
        case['circuit'] = dict(n_pads=2*case['channels'], n_outputs=case['channels'],
            return_topology='all_return_pads_ideal_common_GND', n_return_nodes=1,
            source_Vpp_each=1., source_peak_V=.5, source_resistance_ohm=50.,
            inactive_source_at_other_frequencies='0 V through 50 ohm',
            pad_to_node={str(p): f'out{p}' if p < case['channels'] else 'GND' for p in range(2*case['channels'])},
            carrier_assignment_Hz=[3000, 3030] if case['channels']==2 else [3000],
            note='C1 basis also separately evaluated at 3030 Hz; square_3h has explicit harmonics')
        cases.append(case)
    bound = sum(c['cells']*(600 if c['channels']==2 else 340) for c in cases)
    require(bound <= LIMITS['max_batch_added_bytes'], 'Batch storage arithmetic exceeds 2GiB cap')
    require(shutil.disk_usage(run).free > 2*GIB+bound, 'Reserve + uncompressed output bound unavailable')
    jdk = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
    javac = shutil.which('javac') or str(jdk/'javac')
    java = str(Path(javac).parent/'java')
    require(Path(javac).is_file() and Path(java).is_file(), 'Java compiler/runtime unavailable')
    pins = source_pins()
    with (run/'logs/compile-selftest.log').open('w') as log:
        subprocess.run([javac, '-J-Xmx2g', '-J-XX:ActiveProcessorCount=1', '-encoding', 'UTF-8', '-d', str(run/'classes'),
                        str(SOURCE/'TisSweep.java'), str(SOURCE/'ExploreBasis.java'),
                        str(SOURCE/'SelectivityShapeBasis.java'), str(REPO/'tools/java/CloudShapeBasis.java')],
                       check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        subprocess.run([java, '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1',
                        '-cp', str(run/'classes'), 'CloudShapeBasis', '--selftest'],
                       check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    for p in [*(run/'configs').glob('*'), *(run/'masks').glob('*'), *(run/'classes').glob('*')]:
        pins[str(p)] = sha(p)
    plan = dict(schema='task1-cloud-finite-v1', status='prepared', created_utc=now(),
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        historical_source_commit='8c3a30a778cc9bf19ccb52ca523598bff0a84650',
        package_integrity=integrity, limits=LIMITS, gates=GATES, cases=cases,
        expected_raw_bound_bytes=bound, java=java, source_and_input_sha256=pins,
        preparation_seconds=time.monotonic()-start, path_mapping=mapping,
        scientific_scope='New PDE recomputation, not recovery of missing historical native arrays',
        historical_comparison=dict(relative_scalar_tolerance=1e-8, source_loss_matrix_tolerance=1e-8,
                                   allow_absolute_error_near_zero=1e-14,
                                   gate='Same grid, properties, contact, circuit, directions and metric definitions'),
        convergence=dict(field_ROI_percent=1, J_contact_voltage_percent=5, power_percent=2,
                         mesh_convergence_validated=False, experimental_validation=False),
        storage=dict(native_location=str(run), persistent_backup_verified=False,
                     retirement_of_old_environment_allowed=False),
        next_decision='Compare baseline to historical scalars/matrices before expanding search; do not promote unconverged designs')
    write(run/'preregistration.json', plan)
    write(run/'controller.json', dict(status='prepared', updated_utc=now()))
    budgetpath = REPO/'runtime/task1-budget.json'
    budgetpath.parent.mkdir(exist_ok=True)
    budget = read(budgetpath) if budgetpath.exists() else dict(limit_seconds=6600, spent_seconds=0., runs=[])
    budget['spent_seconds'] += plan['preparation_seconds']
    budget['runs'].append(dict(run_id=run.name, stage='preparation', seconds=plan['preparation_seconds']))
    write(budgetpath, budget)
    print(json.dumps(dict(status='prepared', run=str(run), cases=ids, bound_bytes=bound), ensure_ascii=False))


class BatchStop(RuntimeError):
    pass


def execute(run):
    paths_check(run)
    pre = read(run/'preregistration.json')
    require(pre['status']=='prepared' and pre['limits']==LIMITS and pre['gates']==GATES, 'Registration mismatch')
    require(not (run/'execution-attempt.json').exists(), 'Prior execution attempt preserved; make a new run')
    lockpath = REPO/'.task1-execution.lock'
    with lockpath.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return execute_locked(run, pre)


def execute_locked(run, pre):
    start = time.monotonic()
    budgetpath = REPO/'runtime/task1-budget.json'
    budgetpath.parent.mkdir(exist_ok=True)
    budget = read(budgetpath) if budgetpath.exists() else dict(limit_seconds=6600, spent_seconds=0., runs=[])
    require(budget['limit_seconds']==6600, 'Cumulative budget cannot be expanded')
    remaining = 6600-budget['spent_seconds']
    require(remaining > 0, 'Cumulative time exhausted')
    for p, expected in pre['source_and_input_sha256'].items():
        require(sha(p)==expected, 'Pinned source/input changed: '+p)
    original_integrity()
    cpu = min(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    sys.path.insert(0, str(SOURCE))
    from selectivity_postprocess import process_case
    deadline = start+remaining
    pid = os.getpid()
    state = dict(status='running', pid=pid, proc_start_ticks=ticks(pid),
                 started_utc=now(), current_case=None, current_config_sha256=None, phase='starting')
    summary = dict(status='running', run_id=run.name, source_commit=pre['source_commit'],
                   registration_sha256=sha(run/'preregistration.json'), cases=[], new_PDE_conditions=0,
                   mesh_convergence_validated=False, experimental_validation=False,
                   persistent_backup_verified=False)
    write(run/'execution-attempt.json', dict(pid=pid, proc_start_ticks=ticks(pid), started_utc=now()))
    child = None
    active = None
    case_start = start
    initial_free = shutil.disk_usage(run).free
    peak = [rss(pid)]
    stop = threading.Event()
    guard_failure = []
    def flush():
        state['updated_utc'] = now()
        write(run/'controller.json', state)
        write(run/'summary.json', summary)
    def interrupt(signum, frame):
        raise BatchStop(guard_failure[0] if guard_failure else f'interrupted_signal_{signum}')
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1):
        signal.signal(sig, interrupt)
    def guard():
        last_write = 0.
        while not stop.wait(.2):
            try:
                t = time.monotonic()
                value = rss(pid)+(rss(child.pid) if child is not None else 0)
                peak[0] = max(peak[0], value)
                require(value <= 3*GIB, 'resource_shortage_aggregate_RSS_3GiB')
                free = shutil.disk_usage(run).free
                require(free >= 2*GIB, 'resource_shortage_disk_reserve_2GiB')
                require(initial_free-free <= 2*GIB, 'resource_shortage_batch_disk_2GiB')
                require(t < deadline, 'resource_shortage_cumulative_6600s')
                require(t-case_start < 600, 'resource_shortage_condition_600s')
                require(not any((run/n).exists() for n in ('STOP','needs_attention','needs_physical_validation')), 'stopped_by_marker')
                if t-last_write >= 5:
                    write(run/'heartbeat.json', dict(pid=pid, proc_start_ticks=state['proc_start_ticks'],
                          phase=state['phase'], current_case=state['current_case'], observed_utc=now(),
                          aggregate_rss_bytes=value, sampled_peak_rss_bytes=peak[0], disk_free_bytes=free,
                          run_elapsed_seconds=t-start, case_elapsed_seconds=t-case_start))
                    last_write=t
            except Exception as error:
                guard_failure.append(str(error)); os.kill(pid, signal.SIGUSR1); return
    monitor = threading.Thread(target=guard, daemon=True, name='bounded-resource-monitor')
    monitor.start()
    try:
        flush()
        for case in pre['cases']:
            active = case['id']; case_start = time.monotonic(); peak[0] = rss(pid)
            for path, expected in pre['source_and_input_sha256'].items():
                require(sha(path) == expected, 'Pinned source/input changed before condition '+path)
            raw = case['cells']*(600 if case['channels']==2 else 340)
            require(shutil.disk_usage(run).free >= 2*GIB+raw, 'resource_shortage_before_solve')
            state.update(current_case=active, current_config_sha256=case['config_sha256'], phase='solving')
            flush()
            basis = run/'bases'/active
            cmd = [pre['java'], '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1', '-cp', str(run/'classes'),
                   case.get('java_class', 'CloudShapeBasis'), '--execute-parent', str(pid), str(state['proc_start_ticks']),
                   case['config_file'], str(basis)]
            with (run/'logs'/(active+'.log')).open('x') as log:
                child = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                         stdin=subprocess.DEVNULL)
                summary['new_PDE_conditions'] += 1
                state['java_pid'] = child.pid; flush()
                code = child.wait(timeout=min(600, deadline-time.monotonic()))
                child = None
                require(code==0, 'solver_exit_'+str(code))
            require((basis/'BASIS_COMPLETE').is_file(), 'Missing BASIS_COMPLETE')
            validation = read(basis/'validation.json')
            for k, cap in GATES.items():
                require(math.isfinite(validation[k]) and 0<=validation[k]<=cap, 'Native gate '+k)
            state.update(phase='postprocessing', java_pid=None); flush()
            processor = process_case
            if case.get('postprocessor') == 'grouped':
                from task1_grouped_postprocess import process_case as processor
            result = processor(basis, case, run/'postprocess'/active, min(deadline, case_start+600))
            if case.get('requires_original_producer_regression_before_next'):
                from task1_producer_regression import compare_producer
                reference = pre['producer_regression']['reference']
                regression = compare_producer(Path(reference['basis_dir']), basis)
                write(run/'producer-regression.json', regression)
                require(regression['status'] == 'passed', 'New producer regression failed; remaining geometries not run')
            if case.get('requires_full_reference_comparison_before_next'):
                from task1_reference_registration import compare_reference
                comparison = compare_reference(run, case, result)
                write(run/'reference-comparison.json', comparison)
                require(comparison['status'] == 'passed', 'Historical Best1 mismatch; C1 not run before investigation')
            if case.get('requires_coupled_comparison_after_postprocess'):
                from task1_coupled_registration import compare_coupled
                comparison = compare_coupled(run, case, result)
                write(run/'coupled-comparison.json', comparison)
            for path, expected in pre['source_and_input_sha256'].items():
                require(sha(path) == expected, 'Pinned source/input changed during condition '+path)
            record = dict(id=active, status=result['status'], config_sha256=case['config_sha256'],
                          circuit=case['circuit'], validation=validation, cache_signature=case.get('cache_signature'),
                          postprocess_path=str(run/'postprocess'/active/'summary.json'),
                          postprocess_sha256=sha(run/'postprocess'/active/'summary.json'),
                          wall_seconds=time.monotonic()-case_start,
                          sampled_peak_aggregate_rss_bytes=peak[0],
                          native_files={p.name:dict(bytes=p.stat().st_size, sha256=sha(p)) for p in basis.iterdir() if p.is_file()})
            write(run/'cases'/(active+'.json'), record)
            summary['cases'].append(record)
            gc.collect(); flush()
            print(json.dumps(dict(completed=active, seconds=record['wall_seconds'], peak_rss=peak[0])), flush=True)
        summary['status']='complete'
        state.update(status='complete', phase='finished')
    except BaseException as error:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=5)
        reason = str(error)
        status = 'resource_shortage' if 'resource_shortage' in reason or isinstance(error, (TimeoutError, subprocess.TimeoutExpired)) else 'error'
        summary.update(status=status, failed_case=active, error_type=type(error).__name__, error=reason,
                       partial_evidence_preserved=True, automatic_retry=False)
        state.update(status=status, phase='stopped')
        write(run/'failure.json', summary)
    finally:
        stop.set(); monitor.join(timeout=1)
        summary['wall_seconds']=time.monotonic()-start
        summary['finished_utc']=now()
        summary['not_run']=[c['id'] for c in pre['cases'] if c['id'] not in {x['id'] for x in summary['cases']} and c['id']!=summary.get('failed_case')]
        budget['spent_seconds'] += summary['wall_seconds']
        budget['runs'].append(dict(run_id=run.name, stage='execution', status=summary['status'], seconds=summary['wall_seconds']))
        write(budgetpath, budget)
        flush()
    print(json.dumps(dict(status=summary['status'], cases=len(summary['cases']), wall_seconds=summary['wall_seconds'])), flush=True)
    return 0 if summary['status']=='complete' else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--execute', action='store_true')
    mode.add_argument('--verify-originals', action='store_true')
    p.add_argument('--output', type=Path)
    p.add_argument('--case', action='append', default=[])
    p.add_argument('--grouped-plan', type=Path)
    p.add_argument('--validation-receipt', type=Path)
    p.add_argument('--reference-plan', action='store_true')
    p.add_argument('--coupled-plan', action='store_true')
    p.add_argument('--coupled-c1-plan', action='store_true')
    args = p.parse_args()
    if args.verify_originals:
        print(json.dumps(original_integrity(), indent=2)); return 0
    require(args.output is not None, '--output is required')
    raw_output = args.output.absolute()
    require(raw_output == args.output.resolve(), 'Output path must be canonical without symlink or .. aliases')
    run = args.output.resolve()
    if args.prepare:
        with (REPO/'.task1-execution.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(sum((args.reference_plan, args.coupled_plan, args.coupled_c1_plan)) <= 1,
                    'Choose one fixed registration plan')
            if args.coupled_c1_plan:
                require(not args.case and args.grouped_plan is None and args.validation_receipt is None,
                        'Coupled C1 plan has exactly its one predefined condition')
                from task1_c1_coupled_registration import prepare_c1_coupled
                prepare_c1_coupled(run)
            elif args.coupled_plan:
                require(not args.case and args.grouped_plan is None and args.validation_receipt is None,
                        'Coupled plan has exactly its one predefined condition')
                from task1_coupled_registration import prepare_coupled
                prepare_coupled(run)
            elif args.reference_plan:
                require(not args.case and args.grouped_plan is None and args.validation_receipt is None,
                        'Reference plan has exactly its three predefined cases')
                from task1_reference_registration import prepare_reference
                prepare_reference(run)
            elif args.grouped_plan:
                require(args.validation_receipt is not None, 'Grouped adapter validation receipt required')
                from task1_grouped_registration import prepare_grouped
                prepare_grouped(run, args.case, args.grouped_plan, args.validation_receipt)
            else:
                require(args.validation_receipt is None, 'Receipt only applies to grouped registration')
                prepare(run, args.case)
            freeze_sources(run)
        return 0
    require(not args.case, 'execute uses only frozen registration cases')
    require(args.grouped_plan is None and args.validation_receipt is None, 'execute uses only frozen registration')
    require(not args.reference_plan, 'execute uses only frozen reference registration')
    require(not args.coupled_plan, 'execute uses only frozen coupled registration')
    require(not args.coupled_c1_plan, 'execute uses only frozen coupled C1 registration')
    return execute(run)


if __name__=='__main__':
    sys.exit(main())
