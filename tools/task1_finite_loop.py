#!/usr/bin/env python3
"""One finite, serialized follow-up queue; no resident worker or automatic C1.

The supplied one-to-six-case coarse run must already have terminal status complete.
Children own the shared PDE lock and debit their own actual time.  This process
owns a separate duplicate-coordinator lock and charges only its own overhead.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
import shutil

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
HIST = ROOT/'tis-java/runs/selectivity-design-20261019T155933Z'
BUDGET = ROOT/'runtime/task1-budget.json'
BASELINES = {
    'coarse': ROOT/'data-native/cloud-baseline-20261019T185900Z/postprocess/baseline-square15-coarse/summary.json',
    'xy80': ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json',
    'xy100': ROOT/'data-native/cloud-reference-20261019T192000Z/postprocess/baseline-square15-xy100/summary.json',
    'sc4': ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-sc4/summary.json',
    'bulk': ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-bulk/summary.json',
}


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


def checkpoint(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def ticks(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])


def live_pid(pid, start_ticks):
    try:
        return ticks(int(pid)) == int(start_ticks)
    except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError, TypeError):
        return False


class LockKeeper:
    def __init__(self, path):
        self.path, self.stream = Path(path), None

    def __enter__(self):
        self.stream = self.path.open('a+')
        try:
            fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.lockf(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.stream.close()
            raise
        return self

    def __exit__(self, *unused):
        self.stream.close()


def remaining_budget(path=BUDGET):
    budget = read(path)
    spent = budget['spent_seconds']
    if budget['limit_seconds'] != 6600 or not isinstance(spent, (int, float)) or not math.isfinite(spent) or not 0 <= spent <= 6600:
        raise ValueError('Existing finite6600-second budget invalid; never expand it')
    return 6600-spent


def choose_cases(pool, coarse_ids, selected_designs, mesh_ids, max_designs):
    if not 0 <= max_designs <= 2 or len(selected_designs) > max_designs or len(set(selected_designs)) != len(selected_designs):
        raise ValueError('At most two distinct registered coarse designs may advance')
    if not 1 <= len(coarse_ids) <= 6 or len(set(coarse_ids)) != len(coarse_ids) or any(case not in pool for case in coarse_ids):
        raise ValueError('Unknown or duplicated coarse case')
    if len(set(mesh_ids)) != len(mesh_ids) or any(pool[ident].get('mesh_id') != 'coarse' or
            pool[ident].get('channels') != 2 or pool[ident].get('existing_reference') for ident in coarse_ids):
        raise ValueError('Distinct packaged meshes and two-output coarse TIS cases required')
    allowed = {pool[case]['design_id'] for case in coarse_ids}
    if not set(selected_designs) <= allowed or not set(mesh_ids) <= {'xy80', 'xy100', 'sc4', 'bulk'}:
        raise ValueError('Design or mesh escapes the finite packaged plan')
    result = []
    for design in selected_designs:
        for mesh in mesh_ids:
            matches = [key for key, case in pool.items() if case.get('design_id') == design and case.get('mesh_id') == mesh
                       and not case.get('existing_reference') and case.get('channels', 2) == 2]
            if len(matches) != 1:
                raise ValueError('Exactly one packaged TIS case required: '+design+'/'+mesh)
            result.append(matches[0])
    return result


def validate_coarse_cases(pool, cases):
    ids = [case['id'] for case in cases]
    if not 1 <= len(ids) <= 6 or len(set(ids)) != len(ids):
        raise ValueError('One to six distinct packaged coarse TIS cases required')
    for case in cases:
        expected = pool.get(case['id'])
        if (expected is None or expected.get('existing_reference') or case.get('existing_reference') or
                expected.get('mesh_id') != case.get('mesh_id') or case.get('mesh_id') != 'coarse' or
                expected.get('channels') != 2 or case.get('channels') != 2 or
                expected.get('design_id') != case.get('design_id')):
            raise ValueError('Packaged coarse ID/design/mesh/two-output contract differs')
    if len({pool[ident]['design_id'] for ident in ids}) != len(ids):
        raise ValueError('Duplicate coarse physical design')
    return ids


def source_snapshot(repo=ROOT, extra_paths=()):
    repo = Path(repo)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    paths = {Path(path) for path in extra_paths}
    for pattern in ('tools/task1*.py', 'tools/java/*.java', 'tis-java/*.py', 'tis-java/*.java'):
        paths.update(repo.glob(pattern))
    return dict(source_commit=head, files={str(Path(path).resolve()): sha(path) for path in sorted(paths)})


def core_command(mode, run, ids=()):
    if mode not in ('prepare', 'execute') or mode == 'execute' and ids:
        raise ValueError('Exact core --prepare/--execute contract required')
    command = [PYTHON, str(ROOT/'tools/task1_cloud_batch.py'), '--'+mode, '--output', str(run)]
    for ident in ids:
        command += ['--case', ident]
    return command


class PeerReview(RuntimeError):
    pass


def candidate_mesh_validation(paths):
    import importlib.util
    spec = importlib.util.spec_from_file_location('finite_mesh_report', ROOT/'tools/task1_mesh_report.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # This helper is standard-library only; no solve/import hooks.
    report = module.evaluate({key: paths[key] for key in ('coarse', 'xy80', 'sc4', 'bulk')})
    before, after = read(paths['xy80']), read(paths['xy100'])
    checks = []
    for wave in ('square_3h', 'sine', 'triangle_3h'):
        a = module.metrics(next(row for row in before['conditions'] if row['waveform'] == wave))
        b = module.metrics(next(row for row in after['conditions'] if row['waveform'] == wave))
        rows = []
        for key, limit in report['gates_percent'].items():
            if a[key] <= 0:
                raise ValueError('Positive registered convergence reference required')
            change = 100*(b[key]/a[key]-1)
            rows.append(dict(metric=key, before=a[key], after=b[key], signed_change_percent=change,
                limit_percent=limit, passed=abs(change) <= limit))
        checks.append(dict(axis='XY finer', before='xy80', after='xy100', waveform=wave,
            passed=all(row['passed'] for row in rows), checks=rows))
    report['comparisons'] += checks
    report.update(status='partial_registered_pairs' if all(row['passed'] for row in report['comparisons']) else 'failed_gates',
        source_summaries={key: dict(path=str(path), sha256=sha(path)) for key, path in paths.items()},
        passed_pair_wave=sum(row['passed'] for row in report['comparisons']), total_pair_wave=len(report['comparisons']),
        scalar_checks=sum(len(row['checks']) for row in report['comparisons']),
        whole_3D_convergence_validated=False, candidate_adopted=False,
        decision='Root review required; adjacent-axis gates do not establish joint/contact-model convergence or permit automatic C1.')
    return report


def decode_paginated_arrays(text, max_pages=100, max_bytes=4*1024**2):
    """Decode old gh --paginate output: adjacent JSON arrays, without --slurp."""
    if not isinstance(text, str) or len(text.encode('utf-8')) > max_bytes:
        raise ValueError('Paginated feedback response exceeds4MiB or is not text')
    decoder = json.JSONDecoder()
    cursor, pages, rows = 0, 0, []
    while cursor < len(text):
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor == len(text):
            break
        if pages >= max_pages:
            raise ValueError('Paginated feedback response exceeds100pages')
        page, cursor = decoder.raw_decode(text, cursor)
        if not isinstance(page, list):
            raise ValueError('Every paginated feedback page must be a JSON array')
        rows.extend(page)
        pages += 1
    if pages == 0:
        raise ValueError('Paginated feedback response contains no JSON array')
    return rows


def completed_run(run):
    pre, summary = read(run/'preregistration.json'), read(run/'summary.json')
    if summary.get('status') != 'complete' or summary.get('registration_sha256') != sha(run/'preregistration.json'):
        raise RuntimeError('unexpected_terminal: source batch is not complete with its registered SHA')
    for case in pre['cases']:
        record = read(run/'cases'/(case['id']+'.json'))
        path = run/'postprocess'/case['id']/'summary.json'
        if record.get('status') != 'complete' or record.get('config_sha256') != case['config_sha256'] or record.get('postprocess_sha256') != sha(path):
            raise RuntimeError('unexpected_terminal: completed case/provenance mismatch '+case['id'])
    return pre


def peer_snapshot(deadline):
    """Bounded GETs only; save stable IDs/hashes, never tokens or message sends."""
    result = {}
    commands = {
        'head': ['gh', 'api', 'repos/yoodohyun-codex-cloud/ngg-tis-task1/pulls/1'],
        'comments': ['gh', 'api', '--paginate', 'repos/yoodohyun-codex-cloud/ngg-tis-task1/issues/1/comments'],
        'reviews': ['gh', 'api', '--paginate', 'repos/yoodohyun-codex-cloud/ngg-tis-task1/pulls/1/reviews'],
        'review_comments': ['gh', 'api', '--paginate', 'repos/yoodohyun-codex-cloud/ngg-tis-task1/pulls/1/comments'],
    }
    try:
        for key, command in commands.items():
            seconds = min(15., deadline-time.monotonic())
            if seconds <= 0:
                raise TimeoutError('feedback deadline')
            output = subprocess.check_output(command, cwd=ROOT, text=True, stderr=subprocess.DEVNULL, timeout=seconds)
            data = json.loads(output) if key == 'head' else decode_paginated_arrays(output)
            if key != 'head' and not all(isinstance(row, dict) and 'id' in row for row in data):
                raise ValueError('Paginated feedback rows require stable object IDs')
            result[key] = ({'head_sha': data['head']['sha'], 'updated_at': data['updated_at']} if key == 'head'
                else [{'id': row['id'], 'updated_at': row.get('updated_at', row.get('submitted_at')),
                       'body_sha256': hashlib.sha256((row.get('body') or '').encode()).hexdigest()} for row in data])
        return dict(status='read_only_GitHub_GET_verified', evidence=result)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TimeoutError):
        try:
            seconds = min(15., deadline-time.monotonic())
            if seconds <= 0:
                raise TimeoutError('feedback deadline')
            remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'HEAD'], cwd=ROOT, text=True,
                stderr=subprocess.DEVNULL, timeout=seconds).strip()
            return dict(status='fallback_remote_HEAD_only', evidence=remote,
                limitation='peer comments/reviews unavailable; root review required')
        except (OSError, subprocess.SubprocessError, TimeoutError):
            return dict(status='unavailable', evidence=None, limitation='feedback read failed; root review required')


class FiniteLoop:
    def __init__(self, coarse_run, output):
        self.coarse, self.output = coarse_run.resolve(), output.resolve()
        self.start = time.monotonic()
        self.excluded_seconds = self.debited_seconds = 0.
        self.deadline = self.start+remaining_budget()
        self.state = dict(schema='task1-finite-continuation-v1', status='running', phase='initializing',
            pid=os.getpid(), proc_start_ticks=ticks(os.getpid()), created_utc=now(), updated_utc=now(),
            coarse_run=str(self.coarse), maximum_PDE_conditions=11, maximum_new_PDE_conditions=5,
            source_commit=None, stages=[], current_child=None, next_command=None,
            automatic_C1=False, automatic_adoption=False, background_daemon=False,
            actual_started=False, pde_owner=None, next_registration='not_prepared', next_PDE_command=None,
            next_step_owner='root', planned_new_PDE_conditions=0)

    def ending_receipt(self, status, reason):
        """Record an actual stopped owner and explicit root responsibility, never a fake worker."""
        budget = read(BUDGET)
        remaining_budget(BUDGET)
        queue_finished = self.state.get('all_predefined_PDE_steps_finished') is True
        normal_finish = status == 'completed_predefined_queue_pending_root_selection'
        self.state.update(status=status, phase='finished', completed_utc=now(), actual_started=False,
            pde_owner=None, next_registration='not_prepared', next_PDE_command=None, next_command=None,
            next_step_owner='root', budget=dict(limit_seconds=budget['limit_seconds'],
                spent_seconds=budget['spent_seconds'], remaining_seconds=budget['limit_seconds']-budget['spent_seconds']),
            idle_reason=('no_further_preregistered_cases_in_this_finite_queue' if queue_finished else
                'execution_stopped_before_predefined_queue_finished'),
            execution_blocker=None if normal_finish else dict(classification=status, reason=reason, owner='root'),
            scientific_blocker=dict(classification=('adoption_blocked_by_unresolved_convergence' if queue_finished else
                'scientific_validation_incomplete'), reason=reason, owner='root',
                resolution='Root selects and preregisters the next finite research question within the remaining budget; unresolved adoption gates do not prohibit further exploration'),
            coordinator_owner=dict(pid=os.getpid(), proc_start_ticks=ticks(os.getpid()),
                script=str(Path(__file__).resolve()), resident_worker=False))

    def save(self):
        self.state['updated_utc'] = now()
        checkpoint(self.output/'checkpoint.json', self.state)

    def check(self):
        if time.monotonic() >= self.deadline or remaining_budget() <= 0:
            raise RuntimeError('resource_shortage: finite wall/global time budget exhausted')
        if source_snapshot(extra_paths=self.extra_pins) != self.snapshot:
            raise RuntimeError('source_changed: stop for source/HEAD review')
        if shutil.disk_usage(ROOT).free < 2*1024**3+10*1024**2:
            raise RuntimeError('resource_shortage: 2GiB reserve plus coordinator allowance unavailable')

    def debit_overhead(self):
        value = time.monotonic()-self.start-self.excluded_seconds-self.debited_seconds
        if value <= 0:
            return
        with LockKeeper(ROOT/'.task1-execution.lock'):
            budget = read(BUDGET)
            if value > remaining_budget():
                raise RuntimeError('resource_shortage: coordinator overhead exceeds remaining time')
            budget['spent_seconds'] += value
            budget['runs'].append(dict(run_id=self.output.name, stage='finite_coordinator_overhead', seconds=value, finished_utc=now()))
            checkpoint(BUDGET, budget)
        self.debited_seconds += value
        self.state['coordinator_overhead_seconds'] = self.debited_seconds

    def child(self, stage, command):
        self.check()
        self.state.update(phase=stage, next_command=shlex.join(map(str, command)))
        self.save()
        self.debit_overhead()
        log = self.output/(f'{len(self.state["stages"]):02d}-'+stage+'.log')
        started = time.monotonic()
        process = None
        try:
            with log.open('x') as stream:
                process = subprocess.Popen(list(map(str, command)), cwd=ROOT, stdout=stream,
                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
                self.state['current_child'] = dict(pid=process.pid, proc_start_ticks=ticks(process.pid), command=list(map(str, command)))
                if '--execute' in command and str(ROOT/'tools/task1_cloud_batch.py') in list(map(str, command)):
                    owner = dict(self.state['current_child'], role='PDE_controller', run=str(command[-1]))
                    self.state.update(actual_started=True, pde_owner=owner, last_pde_owner=owner)
                self.save()
                while process.poll() is None:
                    left = self.deadline-time.monotonic()
                    if left <= 0:
                        raise TimeoutError('finite coordinator child deadline')
                    try:
                        process.wait(timeout=min(5., left))
                    except subprocess.TimeoutExpired:
                        self.save()
                code = process.returncode
                if code != 0:
                    raise RuntimeError('child_error: '+stage+' exit '+str(code))
        except BaseException:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            raise
        finally:
            elapsed = time.monotonic()-started
            self.excluded_seconds += elapsed  # Children debit their own actual time.
            self.state['stages'].append(dict(stage=stage, command=list(map(str, command)), log=str(log),
                wall_seconds=elapsed, exit_code=process.returncode if process else None))
            self.state['current_child'] = None
            self.state.update(actual_started=False, pde_owner=None)
            self.save()
        self.check()

    def audit(self, run, ids):
        pre = read(run/'preregistration.json')
        cases = {case['id']: case for case in pre['cases']}
        summaries = []
        for ident in ids:
            case = cases[ident]
            summary = run/'postprocess'/ident/'summary.json'
            summaries.append(summary)
            valid = []
            for path in (run/'audit').glob('*.json'):
                row = read(path)
                if (row.get('status') == 'computed_spatial_and_skinJ_audit' and row.get('case_id') == ident and
                        row.get('summary_sha256') == sha(summary) and row.get('config_sha256') == case['config_sha256'] and
                        row.get('native_inputs_unchanged') is True and row.get('conditions') and
                        all('bulk_skin_J' in condition and 'layer_contact_source_losses' in condition for condition in row['conditions'])):
                    valid.append(path)
            if valid:
                self.state.setdefault('reused_audits', []).append(str(valid[0]))
                self.save()
                continue
            mesh = case['mesh_id']
            output = run/'audit'/(self.output.name+'-'+ident+'.json')
            self.child('audit-'+ident, [PYTHON, ROOT/'tools/task1_spatial_audit.py', '--run', run,
                '--case', ident, '--baseline-summary', BASELINES[mesh], '--output', output])
        return summaries

    def rank(self, name, summaries, count):
        output = self.output/(name+'.json')
        command = [PYTHON, ROOT/'tools/task1_candidate_ranking.py', '--select-max', str(count), '--output', output]
        for baseline in BASELINES.values():
            command += ['--baseline-summary', baseline]
        for summary in summaries:
            command += ['--summary', summary]
        self.child(name, command)
        ranking = read(output)
        if ranking.get('status') != 'calculated_unadopted':
            raise RuntimeError('Unexpected ranking status; no follow-up adopted')
        selected = ranking.get('selected_case_ids', ranking.get('selection', {}).get('selected_case_ids', []))
        available = {read(path)['id'] for path in summaries}
        if not isinstance(selected, list) or len(selected) > count or len(set(selected)) != len(selected) or not set(selected) <= available:
            raise RuntimeError('Ranking selected outside bounded phase inputs')
        return selected

    def execute_phase(self, label, ids):
        if (label not in ('fine', 'confirm') or not ids or len(set(ids)) != len(ids) or
                len(ids) > (2 if label == 'fine' else 3) or
                self.state.get('planned_new_PDE_conditions', 0)+len(ids) > 5):
            raise ValueError('Finite phase exceeds distinct two-fine/three-confirm/five-new condition bounds')
        self.peer_gate(label)
        run = ROOT/'data-native'/('cloud-'+self.output.name+'-'+label)
        prepare = core_command('prepare', run, ids)
        self.state['next_command'] = shlex.join(map(str, prepare))
        self.save()
        if remaining_budget() < len(ids)*600:
            raise RuntimeError('resource_shortage: remaining budget below preregistered '+str(len(ids)*600)+'s phase reserve')
        if run.exists():
            raise RuntimeError('Existing phase path must be preserved; no retry/overwrite')
        self.state['planned_new_PDE_conditions'] = self.state.get('planned_new_PDE_conditions', 0)+len(ids)
        self.state.update(next_registration=str(run/'preregistration.json'),
            next_PDE_command=shlex.join(map(str, core_command('execute', run))), actual_started=False, pde_owner=None)
        self.save()
        self.child('prepare-'+label, prepare)
        self.child('execute-'+label, core_command('execute', run))
        completed_run(run)
        return self.audit(run, ids)

    def peer_gate(self, label):
        self.check()
        snapshot = peer_snapshot(self.deadline)
        self.state.setdefault('peer_phase_checks', []).append(dict(phase=label, checked_utc=now(), snapshot=snapshot))
        self.save()
        initial = self.state['peer_before']
        if (initial['status'] != 'read_only_GitHub_GET_verified' or snapshot['status'] != 'read_only_GitHub_GET_verified' or
                snapshot['evidence'] != initial['evidence']):
            raise PeerReview('peer_review_required: changed or unavailable feedback before '+label+' PDE preparation')

    def execute(self):
        pre = completed_run(self.coarse)  # No adoption of a live worker in this version.
        extra = [Path(__file__), self.coarse/'preregistration.json', self.coarse/'summary.json', HIST/'preregistration.json',
            HIST/'inputs/designs.json', ROOT/'docs/cloud-resume-20261020/fourpad-exploration-plan.json',
            *[Path(case[key]) for case in pre['cases'] for key in ('config_file', 'mask_file')]]
        for baseline in BASELINES.values():
            registration_path = baseline.parents[2]/'preregistration.json'
            registration = read(registration_path)
            case = next(case for case in registration['cases'] if case['id'] == baseline.parent.name)
            extra.extend((baseline, registration_path, Path(case['config_file'])))
        self.extra_pins = tuple(extra)
        self.snapshot = source_snapshot(extra_paths=self.extra_pins)
        self.state['source_commit'] = self.snapshot['source_commit']
        checkpoint(self.output/'source-pins.json', self.snapshot)
        pool = read(HIST/'preregistration.json')['case_pool']
        coarse_ids = validate_coarse_cases(pool, pre['cases'])
        self.state.update(maximum_PDE_conditions=len(coarse_ids)+5, registered_coarse_count=len(coarse_ids))
        self.state['registered_coarse_cases'] = coarse_ids
        self.state['peer_before'] = peer_snapshot(self.deadline)
        self.save()
        all_summaries = coarse = self.audit(self.coarse, coarse_ids)
        selected = self.rank('rank-coarse', coarse, 2)
        if selected:
            designs = [pool[ident]['design_id'] for ident in selected]
            fine_ids = choose_cases(pool, coarse_ids, designs, ['xy80'], 2)
            fine = self.execute_phase('fine', fine_ids)
            all_summaries = coarse+fine
            winner = self.rank('rank-fine', fine, 1)
            if winner:
                design = pool[winner[0]]['design_id']
                confirm_ids = choose_cases(pool, coarse_ids, [design], ['xy100', 'sc4', 'bulk'], 1)
                confirmation = self.execute_phase('confirm', confirm_ids)
                all_summaries += confirmation
                chosen = {}
                for path in all_summaries:
                    ident = read(path)['id']
                    if pool[ident]['design_id'] == design:
                        chosen[pool[ident]['mesh_id']] = path
                self.check()
                validation = candidate_mesh_validation(chosen)
                checkpoint(self.output/'candidate-mesh-validation.json', validation)
                self.state['candidate_mesh_validation'] = dict(path=str(self.output/'candidate-mesh-validation.json'),
                    status=validation['status'], SHA256=sha(self.output/'candidate-mesh-validation.json'))
                self.save()
        self.rank('rank-final', all_summaries, 1)
        self.state['peer_after'] = peer_snapshot(self.deadline)
        changed = self.state['peer_after'] != self.state['peer_before']
        final_status = 'peer_review_required' if changed or self.state['peer_after']['status'] != 'read_only_GitHub_GET_verified' else 'completed_predefined_queue_pending_root_selection'
        self.state.update(status='running', phase='final_feedback_checked',
            numerical_execution_status='complete', all_predefined_PDE_steps_finished=True,
            next_decision='Root must select the next finite numerical question; no candidate has passed joint grid/contact-model convergence.',
            next_command=None, next_PDE_command=None)
        self.save()
        if remaining_budget() < 120:
            self.state['ui_render_status'] = 'not_run_resource_reserve'
        else:
            try:
                self.child('render-final', [PYTHON, ROOT/'tools/task1_results_view.py', '--figures', '--output', ROOT/'docs/CLOUD_RESULTS.html'])
                self.state['ui_render_status'] = 'complete'
            except RuntimeError as error:
                if not str(error).startswith('child_error: render-final '):
                    raise
                self.state.update(ui_render_status='failed_preserved', ui_render_error=str(error))
        self.state.update(status='running', phase='finalizing', next_command=None, next_PDE_command=None)
        self.save()
        self.debit_overhead()
        self.ending_receipt(final_status, 'All PDE cases already defined in this finite geometry/refinement queue are complete. Candidate adoption still requires convergence validation. Root owns selection and registration of the next finite exploration queue, which is not yet prepared by this coordinator.')
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coarse-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output, coarse = args.output.resolve(), args.coarse_run.resolve()
    if output.parent != ROOT/'runtime' or not output.name.startswith('finite-loop-') or output.exists():
        raise ValueError('Fresh runtime/finite-loop-ID required; never overwrite checkpoints')
    if coarse.parent != ROOT/'data-native' or coarse.is_symlink():
        raise ValueError('Existing local registered coarse run required')
    if shutil.disk_usage(ROOT).free < 2*1024**3+10*1024**2:
        raise RuntimeError('resource_shortage: 2GiB reserve plus coordinator allowance unavailable')
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    with LockKeeper(ROOT/'.task1-loop.lock'):
        # Refuse a second PDE owner; no nested acquisition is retained for children.
        with LockKeeper(ROOT/'.task1-execution.lock'):
            pass
        output.mkdir()
        loop = FiniteLoop(coarse, output)
        loop.save()
        def interrupted(signum, frame):
            raise RuntimeError('interrupted_signal_'+str(signum))
        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)
        try:
            loop.execute()
            print(json.dumps(loop.state, ensure_ascii=False))
            return 0
        except BaseException as error:
            text = str(error)
            loop.state.update(status=('peer_review_required' if isinstance(error, PeerReview) else
                'resource_shortage' if 'resource_shortage' in text else
                'unexpected_terminal' if 'unexpected_terminal' in text else 'error'),
                error_type=type(error).__name__, error=text, stopped_utc=now(), partial_evidence_preserved=True)
            try:
                loop.debit_overhead()
            except BaseException as budget_error:
                loop.state['overhead_debit_blocker'] = str(budget_error)
            loop.ending_receipt(loop.state['status'], text)
            loop.save()
            print(json.dumps(loop.state, ensure_ascii=False))
            return 2


if __name__ == '__main__':
    sys.exit(main())
