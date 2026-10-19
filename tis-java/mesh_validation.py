"""Bounded, preregistered mesh diagnosis; never edits the exploration worker.

Prepare (including small Java selftests) is the default. Phantom PDE execution
requires --run. All compilation and results stay in a new private directory.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
from contextlib import contextmanager
import csv
import fcntl
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import tempfile
import time

import numpy as np
from explore_tis import ROOT, MATERIALS, atomic, config_text, load_basis, summarize


GIB = 1024 ** 3
RESOURCE_LIMITS = dict(max_cells=800000, case_seconds=600, total_seconds=6600,
                       rss_bytes=3 * GIB, minimum_free_bytes=2 * GIB)
THRESHOLDS = {
    'target20_modulation_V_m': 1, 'target20_total_E_RMS_V_m': 1,
    'surface_J_RMS_max_A_m2': 5, 'surface_J_RMS_p95_A_m2': 5,
    'contact_voltage_RMS_max_V': 5, 'SC_power_W': 2, 'contact_power_W': 2,
}
FREQUENCIES = (2000, 2010, 6000, 6030)
WAVEFORMS = ('sine', 'square_3h', 'triangle_3h')
BASELINE_IDS = {'leader': '03522-1', 'reference': '02342-0'}
DESIGNS = {
    'leader': dict(layout='rect-a10-b10-p1', xy_mm=[[-10, -10], [10, 10], [10, -10], [-10, 10]], size_mm=15),
    'reference': dict(layout='reference-a12.5-b12.5-p1', xy_mm=[[-12.5, -12.5], [12.5, 12.5], [12.5, -12.5], [-12.5, 12.5]], size_mm=10),
}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def assert_hashes_unchanged(hashes):
    for path, expected in hashes.items():
        if sha256(path) != expected:
            raise ValueError(f'Pinned source/input changed: {path}')


def parse_properties(text):
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            if key in result:
                raise ValueError(f'Duplicate property: {key}')
            result[key] = value
    return result


def mesh_metadata(h_xy_mm, sc_cells):
    if not math.isfinite(h_xy_mm) or h_xy_mm <= 0 or sc_cells not in (2, 4, 8):
        raise ValueError('Invalid independent mesh controls')
    nx = round(50 / h_xy_mm)
    if nx < 2 or nx > 120 or not math.isclose(nx * h_xy_mm, 50, abs_tol=1e-9, rel_tol=0):
        raise ValueError('Uniform XY must tile the 50 mm diameter')
    h = h_xy_mm / 1000
    nxy = sum((-0.025 + (i + .5) * h) ** 2 + (-0.025 + (j + .5) * h) ** 2 < .025 ** 2
              for j in range(nx) for i in range(nx))
    nz = sc_cells + 68
    cells = nxy * nz
    if cells > RESOURCE_LIMITS['max_cells']:
        raise ValueError('Diagnostic cell limit exceeded')
    return dict(h_xy_mm=h_xy_mm, sc_cells=sc_cells, nx=nx, nxy=nxy, nz=nz,
                cells=cells, layer_counts=[sc_cells, 14, 14, 40],
                cross_section_mm2=nxy * h_xy_mm ** 2)


def make_config(original_text, h_xy_mm, sc_cells):
    mesh_metadata(h_xy_mm, sc_cells)
    values = parse_properties(original_text)
    values.update(h_mm=str(h_xy_mm), **{'validation.sc_cells': str(sc_cells),
                                      'validation.max_cells': str(RESOURCE_LIMITS['max_cells'])})
    return ''.join(f'{key}={value}\n' for key, value in values.items())


def case_plan():
    meshes = [('baseline', 'baseline', .625, 2), ('sc4', 'sc', .625, 4),
              ('sc8', 'sc', .625, 8), ('xy100', 'xy', .5, 2),
              ('xy120', 'xy', 50 / 120, 2)]
    return [dict(mesh_metadata(h, sc), id=f'{mesh_id}-{geometry}', mesh_id=mesh_id,
                 axis=axis, geometry=geometry)
            for mesh_id, axis, h, sc in meshes for geometry in ('reference', 'leader')]


def check_numerical_gates(validation, contacts_paths, pad_size_mm):
    for key, limit in [('max_residual', 2e-7), ('max_power_error', 2e-7), ('max_current_error', 2e-6)]:
        value = float(validation[key])
        if not math.isfinite(value) or value < 0 or value > limit:
            raise ValueError(f'Numerical gate failed: {key}={value}')
    if validation['channels'] != 2 or not 0 < validation['cells'] <= RESOURCE_LIMITS['max_cells']:
        raise ValueError('Invalid diagnostic dimensions')
    expected = pad_size_mm ** 2 * 1e-6
    if not math.isfinite(expected) or expected <= 0 or len(contacts_paths) != 4:
        raise ValueError('Invalid pad area/frequency count')
    result = {}
    for path in contacts_paths:
        areas = {}
        with Path(path).open(newline='') as stream:
            for row in csv.DictReader(stream):
                pad, area = int(row['pad']), float(row['area_m2'])
                if pad not in range(4) or not math.isfinite(area) or area <= 0:
                    raise ValueError('Invalid contact patch')
                areas[pad] = areas.get(pad, 0) + area
        if set(areas) != set(range(4)) or any(abs(area / expected - 1) > 1e-10 for area in areas.values()):
            raise ValueError(f'Physical electrode area not preserved: {path}')
        result[Path(path).name] = areas
    return result


def review_convergence(cases):
    indexed = {(c['mesh_id'], c['geometry']): c for c in cases if c.get('status') == 'complete'}
    rows, incomplete = [], False
    for axis, before_mesh, after_mesh in [('sc', 'sc4', 'sc8'), ('xy', 'xy100', 'xy120')]:
        for geometry in ('reference', 'leader'):
            before, after = indexed.get((before_mesh, geometry)), indexed.get((after_mesh, geometry))
            if before is None or after is None:
                incomplete = True
                continue
            for wave in WAVEFORMS:
                a = next((r for r in before['metrics'] if r['waveform'] == wave), None)
                b = next((r for r in after['metrics'] if r['waveform'] == wave), None)
                if a is None or b is None:
                    incomplete = True
                    continue
                changes = {}
                for metric, limit in THRESHOLDS.items():
                    old, new = float(a[metric]), float(b[metric])
                    finite = math.isfinite(old) and math.isfinite(new)
                    delta = 100 * (new - old) / abs(old) if finite and old else (0 if finite and new == 0 else None)
                    passed = delta is not None and abs(delta) <= limit
                    changes[metric] = dict(before=old if math.isfinite(old) else None,
                                           after=new if math.isfinite(new) else None,
                                           relative_change_percent=delta, limit_percent=limit, passed=passed)
                rows.append(dict(geometry=geometry, waveform=wave, axis=axis,
                                 previous_case=before['id'], current_case=after['id'],
                                 changes=changes, passed=all(v['passed'] for v in changes.values())))
    passed = len(rows) == 12 and not incomplete and all(r['passed'] for r in rows)
    return dict(status='incomplete' if incomplete else 'passed' if passed else 'unconverged',
                all_passed=passed, rows=rows)


def adjacent_trends(cases):
    """Keep every step; only the final step supplies the registered gates."""
    indexed = {(c['mesh_id'], c['geometry']): c for c in cases if c.get('status') == 'complete'}
    trends = []
    for axis, sequence in [('sc', ('baseline', 'sc4', 'sc8')), ('xy', ('baseline', 'xy100', 'xy120'))]:
        for geometry in ('reference', 'leader'):
            for before_mesh, after_mesh in zip(sequence, sequence[1:]):
                a, b = indexed.get((before_mesh, geometry)), indexed.get((after_mesh, geometry))
                if a is None or b is None:
                    continue
                for wave in WAVEFORMS:
                    old = next(r for r in a['metrics'] if r['waveform'] == wave)
                    new = next(r for r in b['metrics'] if r['waveform'] == wave)
                    trends.append(dict(axis=axis, geometry=geometry, waveform=wave,
                        previous_case=a['id'], current_case=b['id'],
                        relative_changes_percent={k: 100 * (new[k] / old[k] - 1) if old[k] else None for k in THRESHOLDS}))
    return trends


def geometry_comparisons(cases):
    pairs = []
    for mesh_id in dict.fromkeys(c['mesh_id'] for c in cases):
        reference = next((c for c in cases if c['mesh_id'] == mesh_id and c['geometry'] == 'reference'), None)
        leader = next((c for c in cases if c['mesh_id'] == mesh_id and c['geometry'] == 'leader'), None)
        if reference is None or leader is None:
            continue
        for wave in WAVEFORMS:
            a = next(r for r in reference['metrics'] if r['waveform'] == wave)
            b = next(r for r in leader['metrics'] if r['waveform'] == wave)
            pairs.append(dict(mesh_id=mesh_id, waveform=wave, reference_case=reference['id'],
                              leader_case=leader['id'], relative_changes_percent={
                                  k: 100 * (b[k] / a[k] - 1) if a[k] else None for k in THRESHOLDS}))
    return pairs


def validate_preregistration(spec):
    if spec.get('schema_version') != 1:
        raise ValueError('Preregistration schema_version must be 1')
    if spec.get('baseline_cases', BASELINE_IDS) != BASELINE_IDS:
        raise ValueError('This diagnostic fixes the two preregistered baseline candidates')
    required_limits = dict(max_cells=800000, max_cases=10, max_diagnostic_java_processes=1,
                           per_case_wall_seconds=600, total_wall_seconds=6600, max_RSS_bytes=3 * GIB,
                           java_heap='2g', java_active_processors=1, java_gc='SerialGC',
                           minimum_free_disk_bytes=2 * GIB)
    for key, expected in required_limits.items():
        if key in spec.get('resource_limits', {}) and spec['resource_limits'][key] != expected:
            raise ValueError(f'Registered resource limit differs: {key}')
    for key, percent in THRESHOLDS.items():
        if key in spec.get('convergence_relative_limits', {}) and not math.isclose(spec['convergence_relative_limits'][key], percent / 100):
            raise ValueError(f'Registered convergence threshold differs: {key}')
    for key, expected in dict(max_residual=2e-7, max_power_error=2e-7, max_current_error=2e-6,
                              max_relative_electrode_area_error=1e-10).items():
        if key in spec.get('solver_validation_limits', {}) and spec['solver_validation_limits'][key] != expected:
            raise ValueError(f'Registered numerical gate differs: {key}')


class ValidationStop(RuntimeError):
    def __init__(self, message, resources):
        super().__init__(message)
        self.resources = resources


def process_rss_bytes(pid):
    try:
        fields = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line)
        return max(int(fields.get(key, '0 kB').split()[0]) for key in ('VmRSS', 'VmHWM')) * 1024
    except (FileNotFoundError, ProcessLookupError):
        return 0


def available_disk_bytes(path):
    return shutil.disk_usage(path).free


@contextmanager
def diagnostic_lock():
    path = Path(tempfile.gettempdir()) / f'ngg-mesh-validation-{os.getuid()}.lock'
    with path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def run_guarded(command, log_path, *, timeout_s=600, rss_limit_bytes=3 * GIB, total_deadline=None):
    timeout_s = min(float(timeout_s), RESOURCE_LIMITS['case_seconds'])
    rss_limit_bytes = min(int(rss_limit_bytes), RESOURCE_LIMITS['rss_bytes'])
    if timeout_s <= 0 or rss_limit_bytes <= 0:
        raise ValueError('Invalid resource limits')
    start = time.monotonic()
    record = dict(command=list(map(str, command)), wall_seconds=0, peak_rss_bytes=0, status='running')
    with Path(log_path).open('w', encoding='utf-8') as stream:
        proc = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        def stop(reason):
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
            record.update(status=reason, wall_seconds=time.monotonic() - start,
                          returncode=proc.returncode)
            raise ValidationStop(reason, record)
        try:
            while True:
                now = time.monotonic()
                record['peak_rss_bytes'] = max(record['peak_rss_bytes'], process_rss_bytes(proc.pid))
                if now - start > timeout_s:
                    stop('case_timeout')
                if total_deadline is not None and now > total_deadline:
                    stop('total_timeout')
                if record['peak_rss_bytes'] > rss_limit_bytes:
                    stop('rss_limit')
                if available_disk_bytes(Path(log_path).parent) < RESOURCE_LIMITS['minimum_free_bytes']:
                    stop('disk_reserve')
                if proc.poll() is not None:
                    break
                time.sleep(.2)
            record.update(wall_seconds=time.monotonic() - start, returncode=proc.returncode,
                          status='complete' if proc.returncode == 0 else 'process_failed')
            if proc.returncode:
                raise ValidationStop('Diagnostic process failed', record)
            return record
        except BaseException as exc:
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)
                except ProcessLookupError:
                    pass
            if isinstance(exc, ValidationStop):
                exc.resources.update(java_wall_seconds=time.monotonic() - start,
                                     java_peak_rss_bytes=record['peak_rss_bytes'])
            raise


def java_command(classes):
    java = os.environ.get('NGG_JAVA') or shutil.which('java')
    if not java:
        raise RuntimeError('Java JDK runtime is required')
    return [java, '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1',
            '-cp', str(classes), 'ValidationBasis']


def validate_source_case(run, geometry, profile):
    identity = BASELINE_IDS[geometry]
    task, index = identity.split('-')
    path = run / 'cases' / f'{task}.json'
    case = json.loads(path.read_text())
    row = case['candidates'][int(index)]
    expected = dict(DESIGNS[geometry], channels=2, carrier_Hz=2000, beat_Hz=10, boundary_mode='measured_minus_Rs')
    for key, value in expected.items():
        other = {'size_mm': 'pad_size_mm', 'channels': 'output_channels'}.get(key, key)
        if row.get(other) != value:
            raise ValueError(f'Fixed geometry changed: {identity} {key}')
    if row['thickness_nm'] != 0 or row['h_mm'] != .625 or row['carrier_group'] != [0, 1] or row['phase_deg'] != [0., 0.]:
        raise ValueError('Fixed baseline drive/coating changed')
    config = run / 'configs' / f"{row['basis_id']}.properties"
    if sha256(config)[:18] != row['basis_id']:
        raise ValueError('Original basis/config identity mismatch')
    # Physical parameters and measured interpolation must reproduce the retained input.
    actual, reproduced = parse_properties(config.read_text()), parse_properties(config_text(expected, profile, .625))
    if actual != reproduced:
        raise ValueError('Original boundary/material/config no longer reproducible')
    basis = run / 'bases' / row['basis_id']
    if not (basis / 'BASIS_COMPLETE').is_file():
        raise ValueError('Retained baseline basis is unavailable; never rerun the live worker')
    contacts = [basis / f'contacts-{f}.csv' for f in FREQUENCIES]
    check_numerical_gates(case['validation'], contacts, row['pad_size_mm'])
    return dict(identity=identity, row=row, design=expected, case_file=str(path),
                config_file=str(config), basis_dir=str(basis))


def prepare(preregistration, output):
    preparation_start = time.monotonic()
    preregistration, output = Path(preregistration).resolve(), Path(output).resolve()
    spec = json.loads(preregistration.read_text())
    validate_preregistration(spec)
    run = Path(spec['source_run']).resolve()
    if output == run or output.is_relative_to(run):
        raise ValueError('Diagnostic output must be separate from the active exploration run')
    if output.exists():
        manifest_path = output / 'manifest.json'
        if not manifest_path.exists():
            raise ValueError('Output directory already exists without a complete preparation')
        manifest = json.loads(manifest_path.read_text())
        if manifest['preregistration_sha256'] != sha256(preregistration):
            raise ValueError('Preregistration changed after preparation')
        assert_hashes_unchanged(manifest['guard_hashes'])
        return manifest
    expected = json.loads((run / 'solver-sources.json').read_text())
    if spec.get('source_hashes', expected) != expected:
        raise ValueError('Preregistered solver hashes differ from the retained run')
    for name in ('TisSweep.java', 'ExploreBasis.java'):
        if sha256(ROOT / name) != expected[name] or sha256(run / 'inputs' / name) != expected[name]:
            raise ValueError(f'Live/run solver source mismatch: {name}')
    profile_path = run / 'inputs/eis-profiles.json'
    profile = json.loads(profile_path.read_text())['0']
    source_cases = {g: validate_source_case(run, g, profile) for g in DESIGNS}
    guard_files = [preregistration, run / 'solver-sources.json', profile_path]
    guard_files += [ROOT / n for n in ('TisSweep.java', 'ExploreBasis.java', 'ValidationBasis.java',
                                      'mesh_validation.py', 'explore_tis.py', 'explore_inputs.py',
                                      'update_ngg_eis.py', 'fit_ngg_eis.py')]
    for case in source_cases.values():
        guard_files.extend([Path(case['case_file']), Path(case['config_file'])])
        guard_files.extend(p for p in Path(case['basis_dir']).iterdir() if p.is_file())
    guard_hashes = {str(p): sha256(p) for p in guard_files}
    output.mkdir(parents=True)
    for name in ('private-src', 'classes', 'configs', 'bases', 'cases', 'logs', 'inputs'):
        (output / name).mkdir()
    for name in ('TisSweep.java', 'ExploreBasis.java', 'ValidationBasis.java'):
        shutil.copy2(ROOT / name, output / 'private-src' / name)
    shutil.copy2(profile_path, output / 'inputs/eis-profiles.json')
    shutil.copy2(preregistration, output / 'inputs/preregistration.json')
    plan = case_plan()
    for case in plan:
        original = Path(source_cases[case['geometry']]['config_file']).read_text()
        path = output / 'configs' / f"{case['id']}.properties"
        path.write_text(make_config(original, case['h_xy_mm'], case['sc_cells']), encoding='utf-8')
        case['config_file'] = str(path)
        case['config_sha256'] = sha256(path)
    javac = shutil.which('javac')
    if not javac:
        from explore_tis import JAVAC
        javac = str(JAVAC) if JAVAC.is_file() else None
    if not javac:
        raise RuntimeError('JDK compiler required for private diagnostic classes')
    private, classes = output / 'private-src', output / 'classes'
    with diagnostic_lock():
        subprocess.run([javac, '-encoding', 'UTF-8', '-d', str(classes), '-classpath', str(classes),
                        '-sourcepath', str(private)] + [str(private / n) for n in ('TisSweep.java', 'ExploreBasis.java', 'ValidationBasis.java')],
                       cwd=private, check=True, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        selftest = run_guarded(java_command(classes) + ['--selftest'], output / 'logs/selftest.log', timeout_s=120)
    for directory in (private, classes, output / 'configs', output / 'inputs'):
        guard_hashes.update({str(p): sha256(p) for p in directory.iterdir() if p.is_file()})
    assert_hashes_unchanged(guard_hashes)
    manifest = dict(schema_version=1, source_run=str(run), preregistration=str(preregistration),
                    preregistration_sha256=sha256(preregistration), created_utc=datetime.now(timezone.utc).isoformat(),
                    guard_hashes=guard_hashes, source_cases=source_cases, plan=plan,
                    resource_limits=RESOURCE_LIMITS, convergence_thresholds_percent=THRESHOLDS,
                    selftest=selftest, preparation_wall_seconds=time.monotonic() - preparation_start,
                    status='prepared')
    atomic(output / 'manifest.json', manifest)
    return manifest


def check_baseline_reproduction(case, metrics, basis_dir, source_case):
    cached = Path(source_case['basis_dir'])
    if sha256(basis_dir / 'grid.csv') != sha256(cached / 'grid.csv'):
        raise ValueError('Baseline grid differs from retained default mesh')
    originals = json.loads(Path(source_case['case_file']).read_text())['candidates']
    for row in metrics:
        old = next(r for r in originals if r['waveform'] == row['waveform']
                   and r['carrier_group'] == row['carrier_group'] and r['phase_deg'] == row['phase_deg'])
        for key in list(THRESHOLDS) + ['source_power_W', 'max_source_current_RMS_mA']:
            if not math.isclose(row[key], old[key], rel_tol=2e-7, abs_tol=1e-14):
                raise ValueError(f'Original baseline reproduction failed: {case["id"]} {row["waveform"]} {key}')


def run_diagnostic(manifest, output):
    output = Path(output).resolve()
    with diagnostic_lock():
        start = time.monotonic()
        summary = dict(schema_version=1, status='running', source_run=manifest['source_run'],
                       preregistration_sha256=manifest['preregistration_sha256'], cases=[],
                       resource_limits=RESOURCE_LIMITS, convergence=review_convergence([]))
        profile = json.loads((output / 'inputs/eis-profiles.json').read_text())['0']
        elapsed_prior = float(manifest.get('preparation_wall_seconds', 0))
        previous = output / 'summary.json'
        if previous.exists():
            retained = json.loads(previous.read_text())
            if retained.get('preregistration_sha256') != manifest['preregistration_sha256']:
                raise ValueError('Existing result belongs to another preregistration')
            elapsed_prior = float(retained.get('total_wall_seconds', 0))
        deadline = start + RESOURCE_LIMITS['total_seconds'] - elapsed_prior
        watch = {'case_start': None}
        # Cover postprocessing and hashing too, rather than timing only Java.
        def watchdog(signum, frame):
            now = time.monotonic()
            reason = None
            if now >= deadline:
                reason = 'total_timeout'
            elif watch['case_start'] is not None and now - watch['case_start'] > RESOURCE_LIMITS['case_seconds']:
                reason = 'case_timeout'
            elif process_rss_bytes(os.getpid()) > RESOURCE_LIMITS['rss_bytes']:
                reason = 'driver_rss_limit'
            elif available_disk_bytes(output) < RESOURCE_LIMITS['minimum_free_bytes']:
                reason = 'disk_reserve'
            if reason:
                signal.setitimer(signal.ITIMER_REAL, 0)
                raise ValidationStop(reason, dict(status=reason, total_wall_seconds=elapsed_prior + now - start,
                                                  driver_peak_rss_bytes=process_rss_bytes(os.getpid())))
        previous_handler = signal.signal(signal.SIGALRM, watchdog)
        previous_timer = signal.setitimer(signal.ITIMER_REAL, .5, .5)
        try:
            for case in manifest['plan']:
                watch['case_start'] = time.monotonic()
                assert_hashes_unchanged(manifest['guard_hashes'])
                if time.monotonic() >= deadline:
                    raise ValidationStop('total_timeout', dict(status='total_timeout'))
                saved = output / 'cases' / f"{case['id']}.json"
                basis_dir = output / 'bases' / case['id']
                if saved.exists():
                    result = json.loads(saved.read_text())
                    if result.get('status') != 'complete' or not (basis_dir / 'BASIS_COMPLETE').exists():
                        raise ValueError('Incomplete prior case: preserve it and use a new diagnostic output')
                    assert_hashes_unchanged(result['output_hashes'])
                    summary['cases'].append(result)
                    continue
                if case['mesh_id'] == 'xy120' and any(not any(c['id'] == f'xy100-{g}' for c in summary['cases']) for g in ('reference', 'leader')):
                    raise ValueError('Both XY0.5 cases must succeed before XY50/120')
                # Reserve the required 2 GiB plus a conservative upper bound for
                # this case's original-format field/grid output before allocation.
                expected_bytes = case['cells'] * 520
                if available_disk_bytes(output) < RESOURCE_LIMITS['minimum_free_bytes'] + expected_bytes:
                    raise ValidationStop('disk_reserve', dict(status='disk_reserve', expected_output_bytes=expected_bytes))
                if basis_dir.exists():
                    raise ValueError(f'Partial basis exists: {basis_dir}; do not overwrite evidence')
                resources = run_guarded(java_command(output / 'classes') + [case['config_file'], str(basis_dir)],
                                        output / 'logs' / f"{case['id']}.log", total_deadline=deadline)
                assert_hashes_unchanged(manifest['guard_hashes'])
                validation = json.loads((basis_dir / 'validation.json').read_text())
                areas = check_numerical_gates(validation, [basis_dir / f'contacts-{f}.csv' for f in FREQUENCIES],
                                               DESIGNS[case['geometry']]['size_mm'])
                if validation['cells'] != case['cells']:
                    raise ValueError('Actual/preflight cell counts disagree')
                source_case = manifest['source_cases'][case['geometry']]
                basis = load_basis(basis_dir, 2, FREQUENCIES)
                design = source_case['design']
                key = hashlib.sha256((case['config_sha256'] + manifest['guard_hashes'][str(ROOT / 'ValidationBasis.java')]).encode()).hexdigest()[:18]
                if case['geometry'] == 'reference':
                    raw = summarize(basis, design, profile, key, case['h_xy_mm'])
                    reference = next(r for r in raw if r['waveform'] == 'sine')
                else:
                    reference_case = next(c for c in summary['cases'] if c['geometry'] == 'reference' and c['mesh_id'] == case['mesh_id'])
                    reference = next(r for r in reference_case['metrics'] if r['waveform'] == 'sine')
                metrics = summarize(basis, design, profile, key, case['h_xy_mm'], reference=reference)
                del basis
                if case['mesh_id'] == 'baseline':
                    check_baseline_reproduction(case, metrics, basis_dir, source_case)
                assert_hashes_unchanged(manifest['guard_hashes'])
                resources.update(case_wall_seconds=time.monotonic() - watch['case_start'],
                                 driver_peak_rss_bytes=process_rss_bytes(os.getpid()))
                result = dict(case, status='complete', basis_dir=str(basis_dir), validation=validation,
                              physical_pad_areas_m2=areas, metrics=metrics, resources=resources,
                              baseline_reproduced=case['mesh_id'] == 'baseline',
                              output_hashes={str(p): sha256(p) for p in basis_dir.iterdir() if p.is_file()})
                atomic(saved, result)
                summary['cases'].append(result)
                summary.update(total_wall_seconds=elapsed_prior + time.monotonic() - start,
                               updated_utc=datetime.now(timezone.utc).isoformat(),
                               convergence=review_convergence(summary['cases']),
                               adjacent_trends=adjacent_trends(summary['cases']),
                               geometry_comparisons=geometry_comparisons(summary['cases']))
                atomic(output / 'summary.json', summary)
            summary['status'] = 'complete'
        except BaseException as exc:
            summary.update(status='stopped', error=str(exc), failed_case=case['id'] if 'case' in locals() else None)
            if isinstance(exc, ValidationStop):
                summary['failed_resources'] = exc.resources
            summary.update(total_wall_seconds=elapsed_prior + time.monotonic() - start,
                           updated_utc=datetime.now(timezone.utc).isoformat(),
                           convergence=review_convergence(summary['cases']),
                           adjacent_trends=adjacent_trends(summary['cases']),
                           geometry_comparisons=geometry_comparisons(summary['cases']))
            atomic(output / 'summary.json', summary)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
            if previous_timer[0]:
                signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        summary.update(total_wall_seconds=elapsed_prior + time.monotonic() - start,
                       updated_utc=datetime.now(timezone.utc).isoformat(),
                       convergence=review_convergence(summary['cases']),
                       adjacent_trends=adjacent_trends(summary['cases']),
                       geometry_comparisons=geometry_comparisons(summary['cases']))
        atomic(output / 'summary.json', summary)
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prereg', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare-only', action='store_true')
    mode.add_argument('--run', action='store_true', help='Explicitly execute the ten preregistered phantom cases')
    args = parser.parse_args()
    manifest = prepare(args.prereg, args.output)
    if args.run:
        summary = run_diagnostic(manifest, args.output)
        print(json.dumps(dict(status=summary['status'], cases=len(summary['cases']),
                              convergence=summary['convergence']['status'], output=str(args.output.resolve()))))
    else:
        print(json.dumps(dict(status='prepared_no_phantom_PDE', cases=len(manifest['plan']),
                              selftest=manifest['selftest']['status'], output=str(args.output.resolve()))))


if __name__ == '__main__':
    main()
