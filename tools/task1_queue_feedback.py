#!/usr/bin/env python3
"""Finite public GitHub feedback GETs after a Task 1 queue, without messaging."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import task1_cloud_batch as core
import task1_resource_policy as policy
from task1_finite_loop import decode_paginated_arrays


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output
    core.require(output.is_absolute() and output == output.resolve()
                 and output.is_relative_to(core.REPO/'docs') and not output.exists(),
                 'New canonical docs feedback receipt required')
    with (core.REPO/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger = policy.load_ledger()
        core.require(policy.remaining_seconds(ledger) >= 60, 'Reserve60s for feedback GETs')
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        started = time.monotonic()
        status, error, receipts = 'failed_preserved', None, []
        def timeout(*args):
            raise TimeoutError('Finite60s public feedback GET deadline exceeded')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, 60)
        try:
            for number in (1, 2):
                prefix = 'repos/yoodohyun-codex-cloud/ngg-tis-task1/'
                for kind, endpoint in [('head', f'pulls/{number}'),
                                       ('comments', f'issues/{number}/comments')]:
                    command = ['gh', 'api'] + (['--paginate'] if kind == 'comments' else []) + [prefix+endpoint]
                    raw = subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL,
                        timeout=min(12., max(.001, started+60-time.monotonic())))
                    data = json.loads(raw) if kind == 'head' else decode_paginated_arrays(raw)
                    value = dict(head_sha=data['head']['sha'], updated_at=data['updated_at']) if kind == 'head' else [
                        dict(id=row['id'], updated_at=row['updated_at'], author=row['user']['login'],
                             body_sha256=hashlib.sha256((row.get('body') or '').encode()).hexdigest(),
                             body=row.get('body') or '', html_url=row['html_url']) for row in data]
                    receipts.append(dict(pull=number, kind=kind, endpoint=prefix+endpoint,
                                         observed_utc=core.now(), evidence=value))
            status = 'read_only_feedback_checked'
        except BaseException as exc:
            error = type(exc).__name__+': '+str(exc)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-started
            core.write(output, dict(schema='task1-queue-feedback-v1', status=status,
                observed_utc=core.now(), error=error, receipts=receipts,
                new_feedback_automatically_adopted=False, peer_agreement_inferred=False,
                next_step='Root compares stable IDs/body hashes and chooses next finite scientific batch',
                resources=dict(wall_seconds=elapsed, max_seconds=60, CPU_count=1),
                public_GitHub_only=True, messages_sent=0, new_PDE=0))
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=output.stem, stage='queue_feedback_GET',
                status=status, seconds=elapsed, error=error, finished_utc=core.now()))
            core.write(core.REPO/'runtime/task1-budget.json', ledger)
    print(json.dumps(dict(status=status, output=str(output))))


if __name__ == '__main__':
    main()
