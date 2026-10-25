"""SHA-bound task1 execution caps. Import performs no I/O or configuration.

8 GB means 8,000,000,000 bytes, not an 8 GiB Java heap. This helper reports
visible constraints; hidden ancestor cgroups and available capacity are not
certified. The caller still owns locks, finite timeouts and aggregate accounting.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import sys

ROOT = Path('/workspace/ngg-tis-task1')
ACTIVE_POLICY = ROOT / 'runtime/task1-execution-resource-policy.json'
HELPER_VERSION = 'task1-execution-policy-2.0'
POLICY_SCHEMA = 'task1-execution-resources-v2'
SNAPSHOT_SCHEMA = 'task1-execution-environment-snapshot-v1'
APPROVAL_SCHEMA = 'task1-compute-resources-approval-v1'
REQUESTED_CPU = 4
REQUESTED_MEMORY = 8_000_000_000
JAVA_HEAP = 2_147_483_648
THREAD_KEYS = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
               'NUMEXPR_NUM_THREADS', 'NUMEXPR_MAX_THREADS')


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _read_optional(path):
    try:
        return Path(path).read_text(encoding='utf-8').strip()
    except (OSError, UnicodeError):
        return None


def _cpuset(value):
    """Parse a Linux CPU list; malformed/unavailable input has no inferred limit."""
    if not value:
        return None
    result = set()
    for item in value.split(','):
        match = re.fullmatch(r'(\d+)(?:-(\d+))?', item.strip())
        if match is None:
            return None
        lo = int(match[1]); hi = int(match[2] or match[1])
        if hi < lo or hi > 1_000_000:
            return None
        result.update(range(lo, hi + 1))
    return sorted(result) or None


def _positive_limit(value):
    if value in (None, 'max'):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def inspect_environment():
    """Read nonsecret CPU/memory metadata only; no benchmark or NumPy import."""
    try:
        affinity = sorted(os.sched_getaffinity(0))
        affinity_status = 'observed'
    except (AttributeError, OSError):
        affinity = []
        affinity_status = 'unavailable'
    cpu_max = _read_optional('/sys/fs/cgroup/cpu.max')
    quota = period = None
    quota_status = 'unavailable'
    if cpu_max is not None:
        parts = cpu_max.split()
        if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) > 0:
            period = int(parts[1])
            if parts[0] == 'max':
                quota_status = 'visible_unlimited'
            elif parts[0].isdigit() and int(parts[0]) > 0:
                quota = int(parts[0]); quota_status = 'visible_finite'
    cpuset_raw = _read_optional('/sys/fs/cgroup/cpuset.cpus.effective')
    memory_raw = _read_optional('/sys/fs/cgroup/memory.max')
    current_raw = _read_optional('/sys/fs/cgroup/memory.current')
    memory_limit = _positive_limit(memory_raw)
    memory_current = int(current_raw) if current_raw and current_raw.isdigit() else None
    host_available = None
    meminfo = _read_optional('/proc/meminfo')
    if meminfo is not None:
        match = re.search(r'^MemAvailable:\s+(\d+)\s+kB$', meminfo, re.MULTILINE)
        if match:
            host_available = int(match[1]) * 1024
    return dict(
        schema=SNAPSHOT_SCHEMA, helper_version=HELPER_VERSION,
        python_version=platform.python_version(),
        cgroup_version=2 if cpu_max is not None or memory_raw is not None else 'unverified',
        affinity_cpus=affinity, affinity_status=affinity_status,
        visible_cpuset_cpus=_cpuset(cpuset_raw),
        visible_cpu_quota_us=quota, visible_cpu_period_us=period,
        visible_cpu_quota_cores=(quota / period if quota is not None else None),
        visible_cpu_quota_status=quota_status,
        visible_cgroup_memory_limit_bytes=memory_limit,
        visible_cgroup_memory_limit_status=('visible_unlimited' if memory_raw == 'max' else
                                           'visible_finite' if memory_limit is not None else 'unavailable'),
        visible_cgroup_memory_current_bytes=memory_current,
        visible_cgroup_memory_headroom_bytes=(max(0, memory_limit-memory_current)
            if memory_limit is not None and memory_current is not None else None),
        host_MemAvailable_bytes=host_available,
        hidden_ancestor_limits_verified=False,
        capacity_guaranteed=False,
        measurement_scope='Current process affinity and visible cgroup v2 mount only; host availability is informational')


def _document(path, expected_sha=None):
    path = Path(path)
    _require(path.is_absolute() and path == path.resolve() and path.is_file()
             and not path.is_symlink(), 'Canonical regular policy document required')
    _require(path.stat().st_size <= 2*1024*1024, 'Policy metadata exceeds 2 MiB')
    raw = path.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None:
        _require(isinstance(expected_sha, str) and re.fullmatch(r'[0-9a-f]{64}', expected_sha)
                 and digest == expected_sha, 'Immutable policy document SHA256 mismatch')
    obj = json.loads(raw)
    _require(isinstance(obj, dict), 'Policy document must be an object')
    return obj, digest, str(path)


def _equal_fields(obj, fields, kind):
    for key, expected in fields.items():
        _require(type(obj.get(key)) is type(expected) and obj[key] == expected,
                 'Invalid '+kind+' field: '+key)


def load_active_policy(path=ACTIVE_POLICY):
    """Validate the active document and byte-pinned approval/environment snapshot.

    The returned private metadata keys are operational and are not policy inputs.
    The recorded snapshot is provenance; resolve_limits always inspects live limits.
    """
    policy, digest, canonical = _document(path)
    _equal_fields(policy, dict(schema=POLICY_SCHEMA,
        requested_cpu_limit=REQUESTED_CPU, requested_total_memory_bytes=REQUESTED_MEMORY,
        max_cells=800000, concurrent_solves=1, numerical_owners=1,
        java_heap_bytes=JAVA_HEAP, blas_threads=4, java_active_processor_count=4,
        cumulative_time_unlimited=True, finite_batch_timeouts_required=True), 'execution policy')
    for key in ('approval_sha256', 'environment_snapshot_sha256'):
        _require(isinstance(policy.get(key), str) and re.fullmatch(r'[0-9a-f]{64}', policy[key]),
                 'Explicit immutable SHA256 pin required: '+key)
    approval, approval_sha, approval_path = _document(policy.get('approval_path', ''),
                                                        policy.get('approval_sha256'))
    _equal_fields(approval, dict(schema=APPROVAL_SCHEMA, status='approved',
        source='explicit_current_user_instruction', cpu_limit=4,
        total_memory_bytes=REQUESTED_MEMORY, max_cells=800000,
        concurrent_solves=1, numerical_owners=1, finite_batch_timeouts_required=True,
        external_paid_resources_authorized=False,
        security_installation_merge_permissions_changed=False,
        service_limits_bypass_authorized=False), 'approval')
    snapshot, snapshot_sha, snapshot_path = _document(policy.get('environment_snapshot_path', ''),
                                                        policy.get('environment_snapshot_sha256'))
    _require(snapshot.get('schema') == SNAPSHOT_SCHEMA
             and snapshot.get('hidden_ancestor_limits_verified') is False
             and snapshot.get('capacity_guaranteed') is False,
             'Bound environment snapshot must preserve visible-only limitations')
    _require(isinstance(snapshot.get('affinity_cpus'), list)
             and all(type(v) is int and v >= 0 for v in snapshot['affinity_cpus']),
             'Environment snapshot affinity metadata required')
    return {**policy, '_policy_path': canonical, '_policy_sha256': digest,
            '_approval': approval, '_environment_snapshot': snapshot,
            '_immutable_refs': {canonical: digest, approval_path: approval_sha,
                                snapshot_path: snapshot_sha}}


def _validated_policy(policy):
    if policy is None:
        return load_active_policy()
    _require(isinstance(policy, dict) and '_policy_path' in policy
             and '_policy_sha256' in policy, 'Use load_active_policy result, not unverified dict')
    loaded = load_active_policy(policy['_policy_path'])
    _require(loaded['_policy_sha256'] == policy['_policy_sha256'],
             'Active policy bytes changed after validation')
    return loaded


def resolve_limits(policy=None):
    """Resolve requested caps against fresh visible constraints, without mutation.

    A fractional CPU quota is floored for the worker/thread count (at least one
    thread); kernel throttling still enforces sub-CPU quotas. Headroom is reported
    separately and must not be represented as guaranteed worker memory.
    """
    policy = _validated_policy(policy); env = inspect_environment()
    visible_affinity = env['affinity_cpus']
    _require(visible_affinity, 'Cannot configure CPU affinity: current affinity is unavailable')
    cpuset = env['visible_cpuset_cpus']
    eligible = sorted(set(visible_affinity) & set(cpuset)) if cpuset is not None else visible_affinity
    _require(eligible, 'No CPU remains in observed affinity/cpuset intersection')
    cpu = min(policy['requested_cpu_limit'], len(eligible))
    quota = env['visible_cpu_quota_cores']
    if quota is not None:
        cpu = min(cpu, max(1, math.floor(quota)))
    memory_limit = env['visible_cgroup_memory_limit_bytes']
    memory = min(policy['requested_total_memory_bytes'], memory_limit) if memory_limit is not None else policy['requested_total_memory_bytes']
    return dict(schema='task1-resolved-execution-limits-v2',
        cpu_limit=cpu, effective_cpu_limit=cpu, affinity_cpus=eligible[:cpu],
        total_memory_bytes=memory, effective_total_memory_bytes=memory,
        requested_cpu_limit=policy['requested_cpu_limit'],
        requested_total_memory_bytes=policy['requested_total_memory_bytes'],
        requested_total_memory_GiB=policy['requested_total_memory_bytes']/1024**3,
        java_heap_bytes=policy['java_heap_bytes'],
        java_heap_fits_effective_total_cap=policy['java_heap_bytes'] < memory,
        java_active_processor_count=min(policy['java_active_processor_count'], cpu),
        blas_threads=min(policy['blas_threads'], cpu),
        max_cells=policy['max_cells'], concurrent_solves=policy['concurrent_solves'],
        numerical_owners=policy['numerical_owners'],
        cumulative_time_unlimited=True, finite_batch_timeouts_required=True,
        memory_accounting_scope='Aggregate owned process RSS plus all task1-owned tmpfs bytes; caller must enforce',
        visible_cgroup_memory_headroom_bytes=env['visible_cgroup_memory_headroom_bytes'],
        host_MemAvailable_bytes=env['host_MemAvailable_bytes'],
        environment=env, immutable_policy_refs=dict(policy['_immutable_refs']),
        hidden_ancestor_limits_verified=False, capacity_guaranteed=False)


def configure_process(limits):
    """Apply affinity/thread environment BEFORE any NumPy/BLAS import.

    This changes neither Java GC nor heap. Callers pass the returned Java flags
    to a future worker explicitly; an already running process is never reconfigured.
    """
    _require(isinstance(limits, dict) and limits.get('schema') == 'task1-resolved-execution-limits-v2',
             'Resolved execution limits required')
    _require(not any(name == 'numpy' or name.startswith('numpy.') for name in sys.modules),
             'configure_process must run before NumPy import')
    cpu = limits.get('cpu_limit'); threads = limits.get('blas_threads'); cpus = limits.get('affinity_cpus')
    _require(type(cpu) is int and 1 <= cpu <= 4 and type(threads) is int
             and 1 <= threads <= cpu and isinstance(cpus, list) and len(cpus) == cpu
             and len(set(cpus)) == cpu and all(type(v) is int and v >= 0 for v in cpus),
             'Finite validated CPU/thread/affinity caps required')
    current = set(os.sched_getaffinity(0))
    _require(set(cpus) <= current, 'Resolved CPUs are no longer available to this process')
    os.sched_setaffinity(0, set(cpus))
    observed = sorted(os.sched_getaffinity(0))
    _require(observed == sorted(cpus), 'Applied process affinity readback mismatch')
    for key in THREAD_KEYS:
        os.environ[key] = str(threads)
    return dict(status='configured_before_numpy_import', affinity_cpus=observed,
                thread_environment={key: os.environ[key] for key in THREAD_KEYS},
                actual_BLAS_threads_verified=False,
                java_active_processor_count=limits['java_active_processor_count'],
                java_heap_bytes=limits['java_heap_bytes'], java_GC_policy='unchanged; caller retains existing SerialGC')


def execution_policy_refs(policy=None):
    """Return immutable path -> SHA256 pins, including active policy bytes."""
    return dict(_validated_policy(policy)['_immutable_refs'])
