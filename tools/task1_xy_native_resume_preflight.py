#!/usr/bin/env python3
"""Finite metadata-only inspection of two possible finer canonical XY grids.

No solver, registration, native arrays, installation, deletion or Git command.
The receipt is an inspection, never an authorization to execute a native basis.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import time

import task1_resource_policy as policy

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
POST_RESERVE_BYTES = 128*1024**2
NATIVE_BYTES_PER_CELL = 600
NEXT_BATCH_SECONDS = 960
MAX_INSPECTION_SECONDS = 60
MAX_CELLS = 800000
NATIVE_MAX_NX = 120
SCIENTIFIC_NEXT = ('Finer XY diagnostic followed by bulk, electrode-edge and contact-model gates; '
                   'the failed current two-level XY comparison remains held; no candidate adoption.')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def grid_counts(nx):
    """Integer center-mask count. Even nx makes boundary equality impossible."""
    require(type(nx) is int and nx > 0 and nx % 2 == 0, 'Positive even integer nx required')
    require(nx <= 1000, 'Bound this pure integer diagnostic to nx<=1000')
    count = sum((2*i-(nx-1))**2+(2*j-(nx-1))**2 <= nx*nx
                for j in range(nx) for i in range(nx))
    return dict(nx=nx, xy_active_cells=count, nz=70, cells=count*70)


def admission(free_bytes, remaining_seconds, cells, *, nx=120):
    require(type(free_bytes) is int and free_bytes >= 0, 'Nonnegative integer free bytes required')
    require(type(cells) is int and cells > 0, 'Positive integer cells required')
    require(type(nx) is int and nx > 0 and nx % 2 == 0 and nx <= 1000,
            'Bounded positive even integer nx required')
    require(type(remaining_seconds) in (int, float) and math.isfinite(remaining_seconds)
            and remaining_seconds >= 0, 'Finite nonnegative remaining seconds required')
    required = 2*GIB+cells*NATIVE_BYTES_PER_CELL+POST_RESERVE_BYTES
    storage, budget = free_bytes >= required, remaining_seconds >= NEXT_BATCH_SECONDS
    cap, supported = cells <= MAX_CELLS, nx <= NATIVE_MAX_NX
    blockers = ([] if storage else ['insufficient_disk_for_native_post_and_2GiB_reserve'])
    if not budget:
        blockers.append('remaining_approved_time_below_960_seconds')
    if not cap:
        blockers.append('approved_800000_cell_cap_exceeded')
    if not supported:
        blockers.append('frozen_Java_ValidationMesh_nx_above_120')
    return dict(required_free_bytes=required, conservative_native_bound_bytes=cells*NATIVE_BYTES_PER_CELL,
                postprocessing_reserve_bytes=POST_RESERVE_BYTES, preserved_free_disk_bytes=2*GIB,
                deficit_bytes=max(0, required-free_bytes), storage_pass=storage, time_pass=budget,
                cells_pass=cap, native_grid_supported=supported,
                resource_admission_passed=not blockers, blockers=blockers)


def live_process(pid, startticks, proc_root=Path('/proc')):
    if type(pid) is not int or pid <= 0 or type(startticks) is not int or startticks <= 0:
        return False
    try:
        stat = (Path(proc_root)/str(pid)/'stat').read_text()
        fields = stat.rsplit(')', 1)[1].split()
        return fields[0] not in ('Z', 'X') and int(fields[19]) == startticks
    except (OSError, ValueError, IndexError):
        return False


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_small(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 2*1024**2,
            'Regular small metadata file required: '+str(path))
    return json.loads(path.read_text())


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


@contextmanager
def dual_lock(path):
    require(path.is_file() and not path.is_symlink(), 'Existing regular global lock required')
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def head_from_metadata():
    """Read HEAD metadata without invoking Git or inspecting repository objects."""
    location = ROOT/'.git'
    if location.is_file():
        location = (ROOT/location.read_text().strip().split(': ', 1)[1]).resolve()
    head = (location/'HEAD').read_text().strip()
    if head.startswith('ref: '):
        name = head[5:]
        ref = location/name
        if ref.is_file():
            head = ref.read_text().strip()
        else:
            packed = location/'packed-refs'
            matches = [line.split()[0] for line in packed.read_text().splitlines()
                       if line and not line.startswith(('#', '^')) and line.split()[1] == name]
            require(len(matches) == 1, 'HEAD reference missing from metadata')
            head = matches[0]
    require(len(head) == 40 and all(c in '0123456789abcdef' for c in head), 'Invalid HEAD metadata')
    return head


def implementation():
    names = ('tools/task1_xy_native_resume_preflight.py', 'tests/test_task1_xy_native_resume_preflight.py',
             'tools/task1_resource_policy.py', 'tis-java/SelectivityShapeBasis.java')
    pins = {str(ROOT/name): sha(ROOT/name) for name in names}
    java = (ROOT/'tis-java/SelectivityShapeBasis.java').read_text()
    require('nx<2||nx>120||' in java and 'nxy*nz>MAX_CELLS' in java,
            'Frozen Java grid guards require a fresh source review')
    require(policy.CAPS['max_cells'] == MAX_CELLS, 'Approved cell cap changed; fresh review required')
    return dict(source_commit=head_from_metadata(), source_and_guard_sha256=pins,
                committed_source_bytes_independently_verified=False,
                policy_cap_source=str(ROOT/'tools/task1_resource_policy.py'),
                native_grid_guard_source=str(ROOT/'tis-java/SelectivityShapeBasis.java'))


def controller_inventory():
    paths = set((ROOT/'data-native').glob('*/controller.json'))
    for folder in (ROOT/'docs').glob('cloud-original-*'):
        paths.update(folder.glob('heartbeat.json'))
        paths.update(folder.glob('*/heartbeat.json'))
    rows = []
    for path in sorted(paths):
        obj = read_small(path)
        pid, ticks = obj.get('pid'), obj.get('proc_start_ticks')
        rows.append(dict(path=str(path), status=obj.get('status'), pid=pid, proc_start_ticks=ticks,
                         live=live_process(pid, ticks), metadata_sha256=sha(path)))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    out = parser.parse_args().output
    require(out.is_absolute() and out == out.resolve() and out.is_relative_to(ROOT/'docs')
            and out.parent.is_dir() and not out.exists() and not out.is_symlink(),
            'Unique absolute canonical docs JSON output required')
    with ExitStack() as locks:
        locks.enter_context(dual_lock(ROOT/'.task1-loop.lock'))
        locks.enter_context(dual_lock(ROOT/'.task1-execution.lock'))
        require(not out.exists(), 'Output appeared while acquiring locks; preserve it')
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        started = time.monotonic()
        ledger_path = ROOT/'runtime/task1-budget.json'
        ledger = policy.load_ledger(ledger_path)
        status, error = 'failed_preserved', None
        result = dict(schema='task1-finer-XY-native-resume-preflight-v1', new_PDE=0,
                      native_arrays_read=False, native_execute_command_registered=False,
                      candidate_adopted=False, observed_utc=now())
        previous = {s: signal.getsignal(s) for s in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT)}
        def stopped(signum, frame):
            raise TimeoutError('Controlled finite metadata inspection stop: '+str(signum))
        for s in previous:
            signal.signal(s, stopped)
        signal.setitimer(signal.ITIMER_REAL, MAX_INSPECTION_SECONDS)
        try:
            require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 < 3*GIB, '3GiB RSS cap exceeded')
            sources = implementation()
            sources['immutable_resource_policy_sha256'] = policy.policy_refs(ledger)
            controllers = controller_inventory()
            remaining = policy.remaining_seconds(ledger)
            free = shutil.disk_usage(ROOT).free
            grids = []
            for nx in (120, 160):
                row = grid_counts(nx)
                row.update(h_xy_mm=50/nx, sc_cells=2, bulk_layer_counts=[14, 14, 40],
                           native_basis_RHS_solves=8, frequencies_Hz=[3000, 3030, 9000, 9090],
                           integer_mask_criterion='u=2*i-(nx-1); u*u+v*v<=nx*nx; equality impossible for even nx',
                           prospective_square_faces_per_side=3*nx//10,
                           prospective_full_faces_per_pad=(3*nx//10)**2,
                           admission=admission(free, max(0, remaining-(time.monotonic()-started)), row['cells'], nx=nx),
                           actual_native_config_prepared=False, actual_native_registration_reviewed=False,
                           actual_memory_runtime_and_install_feasibility='unverified')
                grids.append(row)
            blockers = list(grids[0]['admission']['blockers'])
            if any(r['live'] for r in controllers):
                blockers.append('recorded_native_or_original_drive_process_still_live')
            if policy.effective_limit(ledger) != 13800:
                blockers.append('approved_13800_second_policy_not_present')
            require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 < 3*GIB, '3GiB RSS cap exceeded')
            status = ('preferred_grid_blocked_storage_pending_registration' if blockers ==
                      ['insufficient_disk_for_native_post_and_2GiB_reserve'] else
                      'preferred_grid_blocked_pending_registration' if blockers else
                      'resources_available_registration_still_required')
            result = dict(schema='task1-finer-XY-native-resume-preflight-v1', status=status, observed_utc=now(),
                **sources, pid=os.getpid(), proc_start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
                both_global_lock_namespaces_owned=True, prior_controller_inventory=controllers,
                filesystem=dict(actual_free_bytes=free, original_or_failure_data_deleted=False),
                budget=dict(approved_limit_seconds=policy.effective_limit(ledger), remaining_seconds_before_check=remaining,
                            minimum_next_batch_seconds=NEXT_BATCH_SECONDS, expanded=False),
                preferred_grid=grids[0], alternative_unapproved_grid=grids[1], blockers=blockers,
                fixed_model=dict(phantom_diameter_mm=50, layers_mm=[.1, 5, 5, 15], top_only=True,
                                 n_pads=4, n_outputs=2, common_GND=True, source_resistance_ohm=50,
                                 pad_size_mm=[15, 15], total_contact_area_mm2=900),
                scientific_next=SCIENTIFIC_NEXT, candidate_adopted=False, previous_XY_failures_closed=False,
                new_PDE=0, native_arrays_read=False, native_execute_command_registered=False,
                resume_condition='Resource gates AND a unique reviewed actual native configuration/registration/reproducibility '
                    'checks must pass. Preferred nx120 stays within existing800k/nx120 caps; nx160 requires unapproved '
                    'cap/producer changes. This receipt never executes or automatically resumes a solver.',
                next_inspection_command='python tools/task1_xy_native_resume_preflight.py --output '+
                    str(out.with_name(out.stem+'-next-'+str(time.time_ns())+'.json')))
        except BaseException as exc:
            error = type(exc).__name__+': '+str(exc)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-started
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=out.stem, stage='finer_XY_metadata_resume_preflight',
                seconds=elapsed, status=status, error=error, finished_utc=now()))
            partial = ledger_path.with_name(ledger_path.name+'.xy-preflight-'+str(os.getpid())+'-'+str(time.time_ns())+'.partial')
            write_new(partial, ledger)
            partial.replace(ledger_path)
            result.update(status=status, error=error, wall_seconds=elapsed, CPU_count=1,
                          max_inspection_seconds=60, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                          budget_debit_seconds=elapsed, remaining_seconds_after_check=policy.remaining_seconds(ledger))
            write_new(out, result)
            for s, handler in previous.items():
                signal.signal(s, handler)
    print(json.dumps(dict(status=status, output=str(out), blockers=result['blockers'], new_PDE=0)))


if __name__ == '__main__':
    main()
