"""Validate the one authorized Task 1 time extension without changing physics.

Importing this module never reads or changes the live budget.  Old 6600-second
receipts remain valid.  Expansion is a separate, dual-lock-protected amendment;
it does not debit time, erase history, or authorize paid resources.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time

REPO = Path(__file__).resolve().parents[1]
LEGACY_LIMIT = 6600
APPROVED_LIMIT = 13800
INCREMENT = 7200
GIB = 1024**3
CAPS = dict(cpu=1, concurrent_solves=1, max_cells=800000,
            per_condition_seconds=600, java_heap_bytes=2*GIB,
            aggregate_rss_bytes=3*GIB, minimum_free_disk_bytes=2*GIB,
            max_batch_added_bytes=2*GIB)


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _canonical(path, *, exists=True):
    _require(isinstance(path, (str, os.PathLike)), 'Policy path must be a string or path')
    path = Path(path)
    _require(path.is_absolute() and path == path.resolve(),
             'Policy paths must be absolute, canonical, and free of symlinks')
    if exists:
        _require(path.is_file() and not path.is_symlink(), 'Regular policy file required: '+str(path))
    else:
        _require(path.parent.is_dir() and not path.exists() and not path.is_symlink(),
                 'New policy output must not already exist: '+str(path))
    return path


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text())


def _limits(obj):
    for key, value in (('previous_limit_seconds', LEGACY_LIMIT),
                       ('increment_seconds', INCREMENT),
                       ('new_limit_seconds', APPROVED_LIMIT)):
        _require(type(obj.get(key)) is int and obj[key] == value, 'Invalid authorized time extension: '+key)


def _approval(path):
    obj = _read(_canonical(path))
    _require(isinstance(obj, dict) and obj.get('schema') == 'task1-resource-policy-approval-v1' and
             obj.get('status') == 'approved', 'Approved resource-policy metadata required')
    _limits(obj)
    _require(obj.get('caps') == CAPS and all(type(v) is int for v in obj['caps'].values()),
             'Time extension must preserve all numerical resource caps')
    _require(obj.get('external_paid_resources') is False, 'Paid resources are not authorized')
    instruction = obj.get('user_instruction', {})
    _require(isinstance(instruction, dict) and instruction.get('source') == 'current_user_thread' and
             instruction.get('id_kind') == 'local_authorization_record' and
             all(isinstance(instruction.get(k), str) and instruction[k].strip() for k in ('id', 'text')),
             'Explicit user authorization metadata is required')
    return obj


def _pinned(path, expected):
    _require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected) is not None,
             'Invalid immutable policy SHA256')
    path = _canonical(path)
    _require(_sha(path) == expected, 'Immutable policy SHA256 mismatch: '+str(path))
    return path


def _validate(ledger):
    _require(isinstance(ledger, dict), 'Budget ledger must be an object')
    limit = ledger.get('limit_seconds')
    spent = ledger.get('spent_seconds')
    _require(type(limit) is int and limit in (LEGACY_LIMIT, APPROVED_LIMIT), 'Unsupported budget limit')
    _require(type(spent) in (int, float) and math.isfinite(spent) and spent >= 0,
             'Budget spent_seconds must be finite and nonnegative')
    _require(isinstance(ledger.get('runs'), list), 'Budget run history must be a list')
    # Overspend is retained as evidence; remaining_seconds then becomes negative.
    _canonical_sha(ledger['runs'])
    refs = ledger.get('resource_policy')
    if limit == LEGACY_LIMIT:
        _require(refs is None, 'Legacy budget cannot contain an expanded policy')
        return LEGACY_LIMIT, {}
    _require(isinstance(refs, dict), 'Expanded budget requires immutable approval and amendment')
    approval_path = _pinned(refs.get('approval_path'), refs.get('approval_sha256'))
    amendment_path = _pinned(refs.get('amendment_path'), refs.get('amendment_sha256'))
    ledger_path = _canonical(refs.get('ledger_path'))
    approval = _approval(approval_path)
    amendment = _read(amendment_path)
    _require(isinstance(amendment, dict) and amendment.get('schema') == 'task1-resource-budget-amendment-v1' and
             amendment.get('status') == 'applied', 'Applied budget amendment required')
    _limits(amendment)
    _require(amendment.get('ledger_path') == str(ledger_path) and
             amendment.get('approval_path') == str(approval_path) and
             amendment.get('approval_sha256') == refs['approval_sha256'] and
             amendment.get('caps') == CAPS and
             amendment.get('user_instruction') == approval['user_instruction'],
             'Amendment does not match authorization and ledger')
    count, baseline = amendment.get('baseline_runs_count'), amendment.get('baseline_spent_seconds')
    _require(type(count) is int and 0 <= count <= len(ledger['runs']) and
             type(baseline) in (int, float) and math.isfinite(baseline) and baseline >= 0 and spent >= baseline,
             'Expanded ledger cannot reduce historical spending or run count')
    _require(_canonical_sha(ledger['runs'][:count]) == amendment.get('baseline_runs_sha256'),
             'Historical run prefix changed after budget amendment')
    _require(isinstance(amendment.get('previous_ledger_sha256'), str) and
             re.fullmatch('[0-9a-f]{64}', amendment['previous_ledger_sha256']) is not None,
             'Previous ledger SHA256 is required')
    return limit, {str(approval_path): refs['approval_sha256'], str(amendment_path): refs['amendment_sha256']}


def effective_limit(ledger):
    """Return 6600 or the SHA-validated authorized 13800-second limit."""
    return _validate(ledger)[0]


def remaining_seconds(ledger):
    return effective_limit(ledger) - ledger['spent_seconds']


def policy_refs(ledger):
    """Immutable path:SHA pins for new registrations; never pin mutable ledger bytes."""
    return _validate(ledger)[1]


immutable_policy_refs = policy_refs


def load_ledger(path=REPO/'runtime/task1-budget.json'):
    """Read an existing ledger; missing files never silently reset its spending."""
    path = _canonical(Path(path).absolute())
    ledger = _read(path)
    effective_limit(ledger)
    if ledger.get('resource_policy'):
        _require(ledger['resource_policy']['ledger_path'] == str(path), 'Expanded ledger path mismatch')
    return ledger


def _owned_locks(path):
    found = set()
    for fd in Path('/proc/self/fd').iterdir():
        try:
            if not os.path.samefile(fd, path):
                continue
            for line in (Path('/proc/self/fdinfo')/fd.name).read_text().splitlines():
                words = line.split()
                if (len(words) == 9 and words[0] == 'lock:' and
                        words[2] in ('FLOCK', 'POSIX') and
                        words[3:6] == ['ADVISORY', 'WRITE', str(os.getpid())] and words[7:] == ['0', 'EOF']):
                    found.add(words[2])
        except (OSError, FileNotFoundError):
            continue
    return found


@contextmanager
def execution_lock(ledger_path, lock_path=None):
    """Acquire both global lock namespaces, or retain both already held by caller."""
    expected = ledger_path.parent.parent/'.task1-execution.lock'
    lock_path = _canonical(Path(lock_path) if lock_path is not None else expected)
    _require(lock_path == expected, 'Budget amendment requires this repository global execution lock')
    owned = _owned_locks(lock_path)
    if owned:
        _require(owned == {'FLOCK', 'POSIX'}, 'Caller must own both execution lock namespaces')
        yield
        return
    # Never open/close a second descriptor when the caller already holds POSIX locks.
    fd = os.open(lock_path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        _require(stat.S_ISREG(os.fstat(fd).st_mode), 'Regular execution lock required')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def expand_ledger(ledger_path, approval_path, amendment_path, lock_path=None):
    """Apply the sole +7200s authorization, preserving spent_seconds and runs.

    Writes a fresh immutable amendment before atomically replacing the ledger.
    On failure any created amendment/partial remains evidence; it is not deleted.
    """
    ledger_path = _canonical(Path(ledger_path).absolute())
    approval_path = _canonical(Path(approval_path).absolute())
    amendment_path = Path(amendment_path).absolute()
    with execution_lock(ledger_path, lock_path):
        _canonical(amendment_path, exists=False)
        old = load_ledger(ledger_path)
        _require(old['limit_seconds'] == LEGACY_LIMIT, 'Budget extension may be applied only once')
        approval = _approval(approval_path)
        approval_sha = _sha(approval_path)
        amendment = dict(schema='task1-resource-budget-amendment-v1', status='applied',
            previous_limit_seconds=LEGACY_LIMIT, increment_seconds=INCREMENT,
            new_limit_seconds=APPROVED_LIMIT, ledger_path=str(ledger_path),
            approval_path=str(approval_path), approval_sha256=approval_sha,
            previous_ledger_sha256=_sha(ledger_path), baseline_spent_seconds=old['spent_seconds'],
            baseline_runs_count=len(old['runs']), baseline_runs_sha256=_canonical_sha(old['runs']),
            caps=CAPS, user_instruction=approval['user_instruction'],
            applied_utc=datetime.now(timezone.utc).isoformat(), operator_pid=os.getpid(),
            operator_start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]))
        with amendment_path.open('x') as stream:
            json.dump(amendment, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        new = copy.deepcopy(old)
        new['limit_seconds'] = APPROVED_LIMIT
        new['resource_policy'] = dict(ledger_path=str(ledger_path), approval_path=str(approval_path),
            approval_sha256=approval_sha, amendment_path=str(amendment_path), amendment_sha256=_sha(amendment_path))
        effective_limit(new)
        partial = ledger_path.with_name(ledger_path.name+f'.policy-{os.getpid()}-{time.time_ns()}.partial')
        with partial.open('x') as stream:
            json.dump(new, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, ledger_path)
        return new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--approval', type=Path, required=True)
    parser.add_argument('--amendment', type=Path, required=True)
    parser.add_argument('--lock', type=Path)
    args = parser.parse_args()
    ledger = expand_ledger(args.ledger, args.approval, args.amendment, args.lock)
    print(json.dumps(dict(status='applied', limit_seconds=effective_limit(ledger),
                         spent_seconds=ledger['spent_seconds'], remaining_seconds=remaining_seconds(ledger),
                         immutable_policy_refs=policy_refs(ledger)), ensure_ascii=False))


if __name__ == '__main__':
    main()
