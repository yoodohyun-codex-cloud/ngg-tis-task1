#!/usr/bin/env python3
"""Run one immutable, finite Task 1 queue; never a resident worker or retry loop.

Each child owns the numerical execution lock and records its actual budget use.
The coordinator owns the separate loop lock and debits only time outside children.
An attempted queue is immutable evidence: resumption requires a newly reviewed plan.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import time

import task1_resource_policy as policy

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
SCHEMA = 'task1-bounded-continuation-v1'
ALLOWED = {
    'task1_cloud_batch.py': {'--execute', '--output'},
    'task1_spatial_audit.py': {'--run', '--case', '--baseline-summary', '--output'},
    'task1_volume_selectivity.py': {'--summary', '--baseline-summary', '--preregistration', '--output'},
    'task1_return_position_volume_registration.py': {'--output'},
    'task1_frequency_sc4_resynthesis.py': {'--baseline-summary', '--plan', '--output'},
    'task1_queue_feedback.py': {'--output'},
    'task1_cross_allocation_volume_registration.py': {'--output'},
    'task1_grouped_fine_volume_registration.py': {'--output'},
    'task1_grouped_fine_volume_recovery_registration.py': {'--feedback', '--output'},
    'task1_adjacent_source_volume_registration.py': {'--feedback', '--decision', '--output'},
    'task1_candidate_screen.py': {'--preregistration', '--report', '--output'},
    'task1_batch_publish.py': {'--spec', '--output'},
    'task1_lower_carrier.py': {'--execute', '--output'},
    'task1_lower_carrier_recovery.py': {'--execute', '--output'},
    'task1_mid_high_carrier.py': {'--execute', '--output'},
    'task1_coherent_drive_scout.py': {'--preregistration', '--output'},
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    temporary.replace(path)


def canonical(path, root=ROOT):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve() and path.is_relative_to(root),
            'Canonical repository path required: '+str(path))
    return path


@contextmanager
def dual_lock(path):
    with Path(path).open('a+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def ticks(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])


def live(pid, start):
    try:
        row = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return int(row[19]) == start and row[0] not in ('Z', 'X')
    except (OSError, ValueError):
        return False


def owned_descendants(pid, start, known=None):
    """Track startticks-proven descendants even when Java calls setsid()."""
    snapshot = {}
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            row = (proc/'stat').read_text().rsplit(')', 1)[1].split()
            snapshot[int(proc.name)] = (int(row[1]), int(row[19]))
        except (OSError, ValueError, IndexError):
            continue
    owned = {p: t for p, t in (known or {}).items() if p in snapshot and snapshot[p][1] == t}
    if pid in snapshot and snapshot[pid][1] == start:
        owned[pid] = start
    changed = True
    while changed:
        changed = False
        for child, (parent, child_start) in snapshot.items():
            if child not in owned and parent in owned and child_start >= owned[parent]:
                owned[child] = child_start
                changed = True
    return owned


def rss(pid):
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return int(line.split()[1])*1024
    except OSError:
        pass
    return 0


def validate_stage(stage, root=ROOT):
    require(isinstance(stage, dict) and isinstance(stage.get('id'), str) and
            stage['id'].replace('-', '').replace('_', '').isalnum(), 'Safe stage ID required')
    argv = stage.get('argv')
    require(isinstance(argv, list) and len(argv) >= 4 and all(isinstance(x, str) for x in argv), 'argv string array required')
    require(argv[0] == str(Path(sys.executable).resolve()), 'Exact current Python interpreter required')
    tool = canonical(argv[1], root)
    require(tool.parent == root/'tools' and tool.name in ALLOWED, 'Unregistered child tool')
    flags = ALLOWED[tool.name]
    seen = []
    i = 2
    while i < len(argv):
        flag = argv[i]
        require(flag in flags, 'Unexpected child flag: '+flag)
        seen.append(flag)
        i += 1
        if flag == '--execute':
            continue
        require(i < len(argv) and not argv[i].startswith('--'), 'Missing flag value')
        if flag == '--case':
            require(argv[i].replace('-', '').replace('_', '').replace('.', '').isalnum(), 'Safe case ID required')
        else:
            canonical(argv[i], root)
        i += 1
    require('--output' in seen and seen.count('--output') == 1, 'One child output required')
    if tool.name == 'task1_cloud_batch.py':
        require(seen == ['--execute', '--output'], 'Only frozen core execution allowed')
    if tool.name in ('task1_lower_carrier.py', 'task1_lower_carrier_recovery.py', 'task1_mid_high_carrier.py'):
        require(seen == ['--execute', '--output'], 'Only frozen lower-carrier execution allowed')
    if tool.name == 'task1_spatial_audit.py':
        require(set(seen) == flags and len(seen) == len(flags), 'Exact spatial audit flags required')
    if tool.name in ('task1_cross_allocation_volume_registration.py', 'task1_grouped_fine_volume_registration.py', 'task1_grouped_fine_volume_recovery_registration.py', 'task1_adjacent_source_volume_registration.py', 'task1_coherent_drive_scout.py', 'task1_candidate_screen.py', 'task1_batch_publish.py'):
        require(set(seen) == flags and len(seen) == len(flags), 'Exact new metadata/publication stage flags required')
    seconds = stage.get('max_seconds')
    require(type(seconds) in (int, float) and math.isfinite(seconds) and 0 < seconds <= 2400,
            'Finite stage cap <=600s, or registered four-case grouped cap <=2400s, required')
    if seconds > 600:
        require(tool.name == 'task1_cloud_batch.py', 'Finite stage cap >600s reserved for exact four-case grouped core')
        run = canonical(argv[-1], root)
        pre = read(canonical(str(run/'preregistration.json'), root))
        cases = pre.get('cases', [])
        require(pre.get('schema') == 'task1-cloud-finite-v1' and pre.get('status') == 'prepared' and
                pre.get('batch_kind') == 'grouped_fine_physical_pads' and
                pre.get('limits', {}).get('per_condition_seconds') == 600 and
                len(cases) == 4 and {c.get('n_pads') for c in cases} == {4, 8, 12, 16} and
                all(c.get('n_outputs') == c.get('channels') == 2 and c.get('java_class') == 'GroupedPadBasis' and
                    c.get('postprocessor') == 'grouped' and c.get('h_xy_mm') == .625 and
                    c.get('sc_cells') == 2 and c.get('bulk_counts') == [14, 14, 40] for c in cases),
                'Finite long stage requires exact four grouped fine cases and unchanged600s native limits')
        require(stage.get('completion') == dict(path=str(run/'summary.json'), statuses=['complete']) and
                stage.get('must_not_exist') == str(run/'execution-attempt.json'),
                'Long grouped stage requires exact native completion and attempt paths')
    completion = stage.get('completion', {})
    canonical(completion.get('path', ''), root)
    require(isinstance(completion.get('statuses'), list) and completion['statuses'] and
            all(isinstance(s, str) for s in completion['statuses']), 'Explicit completion statuses required')
    marker = stage.get('must_not_exist')
    canonical(marker, root)
    return tool


def implementation(root=ROOT):
    paths = [root/'tools/task1_bounded_continuation.py', root/'tests/test_task1_bounded_continuation.py',
             root/'tools/task1_resource_policy.py']
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    for path in paths:
        require(subprocess.check_output(['git', 'show', commit+':'+path.relative_to(root).as_posix()], cwd=root) == path.read_bytes(),
                'Coordinator implementation must match committed HEAD: '+str(path))
    return {'implementation_git_commit': commit, 'implementation_sha256': {str(p): sha(p) for p in paths}}


def make_preregistration(spec, root=ROOT):
    """Metadata only. Caller supplies reviewed stages and pins; never starts a child."""
    output = canonical(spec['output_directory'], root)
    require(not output.exists() and output.parent.is_dir(), 'New queue output under existing parent required')
    stages = spec['stages']
    require(isinstance(stages, list) and 1 <= len(stages) <= 10, 'One to ten finite stages required')
    require(len({s['id'] for s in stages}) == len(stages), 'Distinct stages required')
    tools = [validate_stage(s, root) for s in stages]
    ledger = policy.load_ledger(root/'runtime/task1-budget.json')
    maximum = spec['max_total_seconds']
    require(type(maximum) in (int, float) and math.isfinite(maximum) and
            sum(s['max_seconds'] for s in stages)+60 <= maximum <= min(7200, policy.remaining_seconds(ledger)),
            'Reserve each stage plus60s overhead inside remaining authorized time')
    receipt = implementation(root)
    refs = dict(spec.get('input_sha256', {}))
    refs.update(receipt['implementation_sha256'])
    refs.update(policy.policy_refs(ledger))
    for tool in tools:
        require(subprocess.check_output(['git', 'show', receipt['implementation_git_commit']+':'+tool.relative_to(root).as_posix()], cwd=root) == tool.read_bytes(),
                'Child tool must match committed HEAD')
        refs[str(tool)] = sha(tool)
    require(str(root/'runtime/task1-budget.json') not in refs, 'Mutable ledger must not be hash-pinned')
    for p, digest in refs.items():
        require(sha(canonical(p, root)) == digest, 'Input hash mismatch: '+p)
    for stage in stages:
        require(not canonical(stage['must_not_exist'], root).exists(), 'Prior child attempt exists')
    return dict(schema=SCHEMA, status='preregistered_not_executed', created_utc=now(),
        output_directory=str(output), max_total_seconds=maximum, stages=stages,
        input_sha256=refs, resource_policy_limit_seconds=policy.effective_limit(ledger),
        caps=dict(CPU_count=1, concurrent_children=1, aggregate_RSS_bytes=3*GIB, minimum_free_disk_bytes=2*GIB),
        candidate_adopted=False, background_daemon=False, automatic_retries=False, **receipt)


def verify_plan(path, expected=None, root=ROOT):
    require(expected is None or sha(path) == expected, 'Queue plan changed')
    plan = read(path)
    require(plan.get('schema') == SCHEMA and plan.get('status') == 'preregistered_not_executed', 'Preregistered finite queue required')
    require(plan.get('caps') == dict(CPU_count=1, concurrent_children=1, aggregate_RSS_bytes=3*GIB, minimum_free_disk_bytes=2*GIB), 'Queue resource caps changed')
    require(1 <= len(plan['stages']) <= 10 and len({s['id'] for s in plan['stages']}) == len(plan['stages']), 'Distinct bounded stages required')
    for stage in plan['stages']:
        validate_stage(stage, root)
    require(sum(s['max_seconds'] for s in plan['stages'])+60 <= plan['max_total_seconds'] <= 7200,
            'Queue stages exceed total finite cap')
    for p, digest in plan['input_sha256'].items():
        require(str(root/'runtime/task1-budget.json') != p, 'Mutable ledger must not be hash-pinned')
        require(sha(canonical(p, root)) == digest, 'Pinned queue source changed: '+p)
    ledger = policy.load_ledger(root/'runtime/task1-budget.json')
    require(policy.effective_limit(ledger) == plan['resource_policy_limit_seconds'], 'Resource policy differs')
    return plan


class Coordinator:
    def __init__(self, plan_path, *, root=ROOT):
        self.root, self.path = root, Path(plan_path)
        self.plan_sha = sha(self.path)
        self.plan = verify_plan(self.path, root=root)
        self.output = canonical(self.plan['output_directory'], root)
        self.started = time.monotonic()
        self.deadline = self.started+self.plan['max_total_seconds']
        self.child_seconds = self.debited = 0.
        self.unrecorded_child_seconds = 0.
        self.current = None
        self.known_members = {}
        self.state = dict(schema=SCHEMA, status='running', pid=os.getpid(), proc_start_ticks=ticks(os.getpid()),
            created_utc=now(), phase='admission', stages=[], current_child=None, plan_path=str(self.path),
            plan_sha256=self.plan_sha, background_daemon=False, candidate_adopted=False)

    def save(self):
        self.state.update(updated_utc=now(), elapsed_seconds=time.monotonic()-self.started)
        write(self.output/'heartbeat.json', self.state)

    def check(self):
        verify_plan(self.path, self.plan_sha, self.root)
        require(time.monotonic() < self.deadline, 'Finite queue wall deadline exhausted')
        require(shutil.disk_usage(self.root).free >= 2*GIB, 'Preserve2GiB disk reserve')
        ledger = policy.load_ledger(self.root/'runtime/task1-budget.json')
        # An active child has not debited its live elapsed time yet.
        active = time.monotonic()-self.active_started if self.current is not None else 0.
        overhead = max(0., time.monotonic()-self.started-self.child_seconds-self.debited-active)
        require(policy.remaining_seconds(ledger) > overhead+active, 'Authorized cumulative time exhausted')

    def debit(self):
        require(self.current is None, 'Never debit while a child can own the ledger')
        amount = max(0., time.monotonic()-self.started-self.child_seconds-self.debited)
        with dual_lock(self.root/'.task1-execution.lock'):
            ledger = policy.load_ledger(self.root/'runtime/task1-budget.json')
            require(policy.remaining_seconds(ledger) >= amount, 'Overhead exceeds authorized remaining budget')
            ledger['spent_seconds'] += amount
            ledger['runs'].append(dict(run_id=self.output.name, stage='bounded_coordinator_reconciliation', seconds=amount,
                unrecorded_child_wall_seconds=self.unrecorded_child_seconds,
                coordinator_wall_seconds=max(0., amount-self.unrecorded_child_seconds), finished_utc=now()))
            write(self.root/'runtime/task1-budget.json', ledger)
        self.debited += amount
        self.unrecorded_child_seconds = 0.
        self.state['coordinator_overhead_seconds'] = self.debited

    def stop_child(self):
        child = self.current
        if child is None:
            return
        # A live, startticks-matched leader is the process group we created.
        record = self.state.get('current_child') or {}
        if record.get('proc_start_ticks') is not None:
            self.known_members.update(owned_descendants(child.pid, record['proc_start_ticks'], self.known_members))
        # Core's Java child creates its own session. Signal only the exact
        # startticks-proven tree, rather than assuming one process group.
        for pid, start in self.known_members.items():
            if live(pid, start):
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        for pid, start in self.known_members.items():
            if live(pid, start):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        child.wait(timeout=5)

    def reconcile_child(self, before, elapsed):
        """Exclude only proven ledger debits; retain genuinely uncharged wall time."""
        require(self.current is not None and self.current.poll() is not None, 'Child must be stopped before reconciliation')
        record = self.state.get('current_child') or {}
        members = owned_descendants(self.current.pid, record.get('proc_start_ticks'), self.known_members)
        # Reaped leader may leave briefly visible zombie descendants. They consume
        # no resources and cannot hold/write the ledger; live members are blockers.
        for pid in members:
            try:
                state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
            except FileNotFoundError:
                continue
            require(state == 'Z', 'Owned child group still live; do not reconcile ledger')
        with dual_lock(self.root/'.task1-execution.lock'):
            after = policy.load_ledger(self.root/'runtime/task1-budget.json')
            require(policy.effective_limit(before) == policy.effective_limit(after) and
                    after['spent_seconds'] >= before['spent_seconds'] and
                    after['runs'][:len(before['runs'])] == before['runs'],
                    'Child budget history must be append-only under same policy')
            delta = after['spent_seconds']-before['spent_seconds']
        recorded = min(elapsed, delta)
        unrecorded = elapsed-recorded
        self.child_seconds += recorded
        self.unrecorded_child_seconds += unrecorded
        return dict(child_wall_seconds=elapsed, child_ledger_delta_seconds=delta,
                    excluded_already_recorded_seconds=recorded, unrecorded_child_wall_seconds=unrecorded)

    def run_stage(self, stage):
        self.check()
        marker = canonical(stage['must_not_exist'], self.root)
        require(not marker.exists(), 'Prior child attempt preserved; no retry')
        self.debit()
        # Test both global lock namespaces before creating a child; the child must
        # still acquire them itself, so any race fails in the child, not overlaps.
        with dual_lock(self.root/'.task1-execution.lock'):
            budget_before = policy.load_ledger(self.root/'runtime/task1-budget.json')
        self.state.update(phase=stage['id'], next_command=shlex.join(stage['argv']))
        self.save()
        self.active_started = time.monotonic()
        code = None
        try:
            with (self.output/(stage['id']+'.log')).open('x') as log:
                self.current = subprocess.Popen(stage['argv'], cwd=self.root, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                self.state['current_child'] = dict(pid=self.current.pid, proc_start_ticks=ticks(self.current.pid), argv=stage['argv'])
                self.known_members = {}
                self.save()
                while self.current.poll() is None:
                    members = owned_descendants(self.current.pid, self.state['current_child']['proc_start_ticks'], self.known_members)
                    self.known_members.update(members)
                    require(time.monotonic()-self.active_started < stage['max_seconds'], 'Finite stage deadline exceeded')
                    total_rss = rss(os.getpid())+sum(rss(pid) for pid in members)
                    require(total_rss < 3*GIB, 'Aggregate3GiB RSS cap exceeded')
                    self.state.update(aggregate_rss_bytes=total_rss, current_child_members=members)
                    self.check()
                    try:
                        self.current.wait(timeout=min(5., max(.001, stage['max_seconds']-(time.monotonic()-self.active_started))))
                    except subprocess.TimeoutExpired:
                        self.save()
                code = self.current.returncode
                require(code == 0, 'Child exit failure: '+str(code))
                result = read(canonical(stage['completion']['path'], self.root))
                require(result.get('status') in stage['completion']['statuses'], 'Unexpected child terminal status')
        except BaseException:
            self.stop_child()
            raise
        finally:
            elapsed = time.monotonic()-self.active_started
            accounting = self.reconcile_child(budget_before, elapsed) if self.current is not None else dict(
                child_wall_seconds=0., spawn_failure_wall_seconds=elapsed)
            self.state['stages'].append(dict(id=stage['id'], elapsed_seconds=elapsed, exit_code=code,
                completion=stage['completion'], accounting=accounting))
            self.current = None
            self.state['current_child'] = None
            self.save()
        self.check()

    def execute(self):
        with dual_lock(self.root/'.task1-loop.lock'):
            require(not self.output.exists(), 'Never overwrite an attempted queue')
            ledger = policy.load_ledger(self.root/'runtime/task1-budget.json')
            require(policy.remaining_seconds(ledger) >= self.plan['max_total_seconds'], 'Queue reservation exceeds remaining authorized time')
            self.output.mkdir()
            os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
            status, reason = 'failed_preserved', None
            old_handlers = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
            def interrupted(signum, frame):
                raise InterruptedError('Controlled coordinator signal '+str(signum))
            for sig in old_handlers:
                signal.signal(sig, interrupted)
            self.save()
            try:
                for stage in self.plan['stages']:
                    self.run_stage(stage)
                status = 'completed_preregistered_queue'
            except BaseException as error:
                reason = type(error).__name__+': '+str(error)
                self.state['failure'] = reason
                raise
            finally:
                previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set(old_handlers))
                self.stop_child()
                try:
                    self.debit()
                except BaseException as error:
                    status = 'blocked_overhead_debit_preserved'
                    reason = (reason+'; ' if reason else '')+type(error).__name__+': '+str(error)
                self.state.update(status=status, phase='finished', stopped_utc=now(), stop_reason=reason or 'All predefined stages completed; root selects next finite scientific question',
                    next_step_owner='root', resume_condition='Do not rerun attempted queue; inspect evidence and preregister a new unique output',
                    resume_command=None, next_inspection_command='cat '+shlex.quote(str(self.output/'heartbeat.json')),
                    numerical_validation_promoted=False)
                self.save()
                write(self.output/'summary.json', self.state)
                for sig, handler in old_handlers.items():
                    signal.signal(sig, handler)
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        return self.state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--spec', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    require(args.prepare != args.execute, 'Choose exactly one of --prepare/--execute')
    if args.prepare:
        require(args.spec is not None and not args.plan.exists(), 'New plan and explicit reviewed spec required')
        with dual_lock(ROOT/'.task1-execution.lock'):
            started = time.monotonic()
            status = 'failed_preserved'
            try:
                plan = make_preregistration(read(args.spec))
                with args.plan.open('x') as stream:
                    stream.write(json.dumps(plan, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
                status = plan['status']
            finally:
                ledger = policy.load_ledger(ROOT/'runtime/task1-budget.json')
                elapsed = time.monotonic()-started
                ledger['spent_seconds'] += elapsed
                ledger['runs'].append(dict(run_id=args.plan.stem, stage='bounded_coordinator_preregistration', seconds=elapsed, status=status, finished_utc=now()))
                write(ROOT/'runtime/task1-budget.json', ledger)
        print(json.dumps(dict(status=plan['status'], plan=str(args.plan))))
    else:
        require(args.spec is None, '--execute consumes frozen plan only')
        result = Coordinator(args.plan.resolve()).execute()
        print(json.dumps(dict(status=result['status'], output=read(args.plan)['output_directory'])))


if __name__ == '__main__':
    main()
