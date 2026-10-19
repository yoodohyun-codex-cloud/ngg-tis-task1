"""Finite eight-window EIS input sensitivity analysis, never a field solve.

Old 1kHz/bare fits remain referenced. Only PEDOT10/30/50/100nm at500/2000Hz
are fitted, with at most one legacy-method constrained fallback per case.
Run --prepare separately, publish exact code/registration, then execute once.
"""
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
import re
import signal
import sys
import time

if '--execute' in sys.argv or '--worker' in sys.argv:
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[_name] = '1'
    if hasattr(os, 'sched_getaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

import numpy as np
from fit_ngg_eis import fit_series_cpe
import mesh_validation as guard

ROOT = Path(__file__).resolve().parent
PREPARATION = ROOT / 'runs/eis-rs-window-preparation-20261019T122759Z/preregistration.json'
PREPARATION_SHA = '005b1143b32b625b6e65a033a0af1ab591fdac52f2b608694ef04972aeb43daf'
CODE_NAMES = ('eis_rs_window_analysis.py', 'fit_ngg_eis.py', 'update_ngg_eis.py', 'mesh_validation.py')
CASE_IDS = tuple(f'eis{nm:03d}-f{cutoff:04d}' for nm in (10, 30, 50, 100) for cutoff in (500, 2000))
LIMITS = dict(cpu_count=1, max_RSS_bytes=3*1024**3, per_case_wall_seconds=600,
    total_wall_seconds=6600, concurrency=1, minimum_free_disk_bytes=2*1024**3,
    new_PDE=0, Java=0, compile=0)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return guard.sha256(Path(path))


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def atomic(path, value):
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.tmp-' + str(os.getpid()))
    try:
        write_new(temporary, value)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def check_stop(output):
    for name in ('STOP', 'needs_attention', 'needs_physical_validation'):
        if (Path(output) / name).exists():
            raise RequestedStop('New analysis-run stop/attention marker: ' + name)


class RequestedStop(RuntimeError):
    pass


class ResourceStop(RuntimeError):
    """A resource/environment gate, distinct from user stop or fitting failure."""


def validate_points(points, cutoff):
    if cutoff not in (500, 2000):
        raise ValueError('Only the eight new500/2000Hz conditions are executable')
    if len(points) != 30:
        raise ValueError('Exactly thirty original measured points required')
    try:
        f = np.asarray([p['frequency_Hz'] for p in points], float)
        z = np.asarray([complex(p['Z_real_ohm'], p['Z_imag_ohm']) for p in points])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Malformed original measured point') from error
    if (not np.isfinite(f).all() or not np.isfinite(z).all()
        or f[0] != 1 or f[-1] != 10000 or not np.all(np.diff(f) > 0)
        or np.any(z.real < 0) or np.any(abs(z) <= 0) or np.sum(f >= cutoff) < 6):
        raise ValueError('Invalid/nonfinite/duplicate/out-of-band measured spectrum')
    return f, z


def validate_fit(fit):
    for name in ('Rs_ohm', 'Q_S_s_power_n', 'n', 'relative_complex_RMS_percent',
                 'weighted_SSE', 'relative_complex_max_percent'):
        if not isinstance(fit.get(name), (int, float)) or not math.isfinite(fit[name]):
            raise ValueError('Nonfinite/missing fitted parameter: ' + name)
    if fit['Rs_ohm'] < 0 or fit['Q_S_s_power_n'] <= 0 or not .2 <= fit['n'] <= 1 or fit['relative_complex_RMS_percent'] < 0:
        raise ValueError('Invalid fitted Rs/Q/n/cost')
    for name in ('weighted_SSE', 'relative_complex_max_percent'):
        if fit[name] < 0:
            raise ValueError('Nonfinite/negative fitted cost: ' + name)


def constrained_window_fit(f, z, cutoff):
    """Legacy clip/refit/1601n-grid method, with an explicit new window.

    This is not a new constrained optimizer and never changes old source code.
    The Rs upper bound uses all30 measured real values, not the fit subset.
    """
    mask = f >= cutoff
    omega, obs = 2*np.pi*f[mask], z[mask]
    weight = 1 / abs(obs)
    target = np.r_[obs.real*weight, obs.imag*weight]
    bound = float(z.real.min())
    best = None
    for n in np.linspace(.2, 1, 1601):
        basis = (1j*omega)**(-n)
        design = np.column_stack((np.r_[weight, np.zeros(len(obs))],
                                  np.r_[basis.real*weight, basis.imag*weight]))
        rs, k = np.linalg.lstsq(design, target, rcond=None)[0]
        rs = float(np.clip(rs, 0, bound))
        a = design[:, 1]
        k = max(float(a @ (target-design[:, 0]*rs) / (a @ a)), 1e-30)
        residual = design @ np.array([rs, k]) - target
        cost = float(residual @ residual)
        if best is None or cost < best[0]:
            best = (cost, rs, k, float(n))
    cost, rs, k, n = best
    predicted = rs + k*(1j*omega)**(-n)
    relative = abs(predicted-obs) / abs(obs)
    return dict(nominal_lower_frequency_Hz=cutoff,
        actual_frequency_range_Hz=[float(f[mask].min()), float(f[mask].max())],
        n_points=int(mask.sum()), Rs_ohm=rs, Q_S_s_power_n=1/k, n=n,
        weighted_SSE=cost, relative_complex_RMS_percent=math.sqrt(cost/len(obs))*100,
        relative_complex_max_percent=float(relative.max()*100),
        method='Legacy1601n-grid/clipRs/refitk; only cutoff is parameterized',
        Rs_upper_bound_ohm=bound, Rs_at_bound=abs(rs-bound) < 1e-8,
        subtraction_nonnegative_real_over_full_measured_band=bool(np.all(z.real-rs >= 0)))


def analyze_points(points, cutoff, *, after_unconstrained=None, check=None):
    """One new fit and, only if needed, one constrained fallback; no file writes."""
    f, z = validate_points(points, cutoff)
    if check:
        check()
    unconstrained = fit_series_cpe(f, z, cutoff)
    validate_fit(unconstrained)
    passive = bool(np.all(z.real-unconstrained['Rs_ohm'] >= 0))
    if unconstrained.get('subtraction_nonnegative_real_over_full_measured_band', passive) != passive:
        raise ValueError('Reported and actual full-band subtraction passivity differ')
    result = dict(status='unconstrained_saved_before_selection', cutoff_Hz=cutoff,
        actual_frequency_range_Hz=[float(f[f >= cutoff].min()), float(f[f >= cutoff].max())],
        n_points=int(np.sum(f >= cutoff)), unconstrained_fit=unconstrained,
        unconstrained_passive=passive, unconstrained_calls=1, fallback_calls=0,
        model_window_sensitivity_not_confidence_interval=True)
    if after_unconstrained:
        after_unconstrained(copy.deepcopy(result))
    if check:
        check()
    if passive:
        selected, selection = copy.deepcopy(unconstrained), 'unconstrained'
    else:
        result['fallback_calls'] = 1
        try:
            selected = constrained_window_fit(f, z, cutoff)
            validate_fit(selected)
            if selected['Rs_ohm'] > float(z.real.min()) or not np.all(z.real-selected['Rs_ohm'] >= 0):
                raise ValueError('Constrained fallback still nonpassive over all30 points')
        except Exception as error:
            result.update(status='failed_fallback', error_type=type(error).__name__, error=str(error),
                          selected_fit=None, selection='held_failed_fallback')
            return result
        selection = 'passivity_constrained_fallback'
    if check:
        check()
    warnings = []
    if not passive:
        warnings.append('Original unconstrained fit/subtraction is nonpassive and remains preserved; fallback is a surrogate, not physical validation.')
    if selected['n'] < .201 or selected['n'] > .999:
        warnings.append('CPE exponent is at/near the original search bound; Rs/model identifiability remains held.')
    if selected.get('Rs_at_bound'):
        warnings.append('Rs is at the full-measured-band real-Z bound; do not interpret as confidence limit.')
    result.update(status='complete', selected_fit=selected, selection=selection,
        selected_subtraction_passive=True, warnings=warnings,
        original_fullband_min_real_Z_ohm=float(z.real.min()),
        interpretation='Deterministic input-fit/window sensitivity only; no new field/contact/physiological result')
    return result


def spec_and_pins():
    if sha(PREPARATION) != PREPARATION_SHA:
        raise ValueError('Pinned preparation specification changed')
    spec = read(PREPARATION)
    if spec['resource_limits'] != LIMITS or tuple(c['id'] for c in spec['case_plan']) != CASE_IDS:
        raise ValueError('Exact eight conditions/resource caps changed')
    if spec['scope']['new_unconstrained_fit_conditions'] != 8 or spec['scope']['maximum_new_constrained_fallback_calls'] != 8:
        raise ValueError('Exact fit/fallback scope changed')
    for c in spec['case_plan']:
        if c['cutoff_Hz'] not in (500, 2000) or c['thickness_nm'] not in (10, 30, 50, 100):
            raise ValueError('Existing bare/1kHz fits must not be rerun')
    pins = dict(spec['input_file_sha256'])
    pins[str(PREPARATION)] = PREPARATION_SHA
    pins[spec['profile_inventory_path']] = spec['profile_inventory_file_sha256']
    verify(pins)
    return spec, pins


def verify(pins):
    for name, digest in pins.items():
        if sha(name) != digest:
            raise ValueError('Frozen input/code changed: ' + name)


def prepare(output):
    began = time.monotonic()
    output = Path(output).resolve()
    if output.parent != ROOT / 'runs' or not output.name.startswith('eis-rs-window-analysis-') or output.exists():
        raise ValueError('Use a new eis-rs-window-analysis-* run; preserve all previous runs')
    spec, pins = spec_and_pins()
    if guard.available_disk_bytes(output.parent) < LIMITS['minimum_free_disk_bytes']:
        raise ResourceStop('disk_reserve: existing2GiB free space unavailable')
    output.mkdir()
    for name in ('cases', 'logs'):
        (output / name).mkdir()
    registration = dict(schema_version=1, status='prepared_not_executed', created_utc=now(),
        user_authorization='Existing-data finite EIS eight-window analysis; code and preregistration publication required before execution.',
        preparation_path=str(PREPARATION), preparation_file_sha256=PREPARATION_SHA,
        case_plan=spec['case_plan'], resource_limits=LIMITS, maximum_new_unconstrained_fits=8,
        maximum_new_constrained_fallback_fits=8, existing_fits_reused=7,
        existing_50nm_constrained_fit_reused=True, method=spec['method'], acceptance=spec['acceptance'],
        failure_policy=spec['failure_policy'], holds=spec['holds'],
        new_PDE=0, new_field_results=0, original_boundary_operator_modified=False)
    write_new(output / 'preregistration.json', registration)
    code = {str(ROOT / name): sha(ROOT / name) for name in CODE_NAMES}
    manifest = dict(schema_version=1, status='prepared', run_id=output.name, output=str(output),
        preparation_file_sha256=PREPARATION_SHA, preregistration_file_sha256=sha(output / 'preregistration.json'),
        input_file_sha256=pins, code_file_sha256=code, resource_limits=LIMITS,
        case_plan=spec['case_plan'], prepare_wall_seconds=time.monotonic()-began,
        fit_execution_started=False, new_PDE=0, new_field_results=0)
    write_new(output / 'manifest.json', manifest)
    (output / 'README.md').write_text('# EIS Rs window analysis 실행 준비\n\n상태: 준비만 완료/새fit0. '
        'exact8조건(PEDOT10/30/50/100nm×500/2000Hz),조건별최대1fallback/전체최대8,원bare3window/1k기존fit참조다. '
        'root가코드·manifest·사전등록을정상게시하고execution-publication.json의정확byteSHA/40hexcommit을기록한뒤한번호출한다. '
        '원case/기저/코팅결과/GUI/기존fit은불변이며새PDE/전계결과0,통계CI/건식/생리검증이아니다. '
        '1CPU·RSS3GiB·600초/조건(필요fallback포함)·6600초전체·동시1·디스크2GiB,실패/중단/비수동/부분보존·무재시도.\n', encoding='utf-8')
    return manifest


def validate_execution(output, *, require_publication=True):
    output = Path(output).resolve()
    spec, pins = spec_and_pins()
    m = read(output / 'manifest.json')
    if (output.parent != ROOT / 'runs' or not output.name.startswith('eis-rs-window-analysis-')
        or m.get('output') != str(output) or m.get('status') != 'prepared'
        or m.get('preparation_file_sha256') != PREPARATION_SHA or m.get('case_plan') != spec['case_plan']
        or m.get('resource_limits') != LIMITS or m.get('input_file_sha256') != pins
        or set(m.get('code_file_sha256', {})) != {str(ROOT / n) for n in CODE_NAMES}
        or not math.isfinite(m.get('prepare_wall_seconds', -1)) or m.get('prepare_wall_seconds', -1) < 0):
        raise ValueError('Exact manifest/output/resource namespace differs')
    if sha(output / 'preregistration.json') != m['preregistration_file_sha256']:
        raise ValueError('Execution preregistration bytes changed')
    r = read(output / 'preregistration.json')
    if (r.get('case_plan') != spec['case_plan'] or r.get('resource_limits') != LIMITS
        or r.get('maximum_new_unconstrained_fits') != 8 or r.get('maximum_new_constrained_fallback_fits') != 8
        or r.get('method') != spec['method'] or r.get('acceptance') != spec['acceptance']):
        raise ValueError('Registered fitting method/caps changed')
    verify(m['code_file_sha256'])
    if require_publication:
        p = read(output / 'execution-publication.json')
        if (p.get('status') != 'published_before_fitting' or p.get('remote_ref_verified') is not True
            or re.fullmatch('[0-9a-f]{40}', str(p.get('commit'))) is None
            or p.get('manifest_file_sha256') != sha(output / 'manifest.json')
            or p.get('preregistration_file_sha256') != m['preregistration_file_sha256']):
            raise ValueError('Exact code/manifest/preregistration must be published before fitting')
    return spec, m


def startticks(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])


def worker(output, identifier):
    spec, manifest = validate_execution(output)
    state = read(output / 'controller.json')
    parent = state['pid']
    if (state.get('status') != 'running' or state.get('current_case') != identifier
        or os.getppid() != parent or startticks(parent) != state['proc_start_ticks']):
        raise ValueError('Worker lacks exact finite-controller identity')
    argv = [x.decode() for x in Path(f'/proc/{parent}/cmdline').read_bytes().split(b'\0') if x]
    if ('--execute' not in argv or '--worker' in argv or '--output' not in argv
        or Path(argv[argv.index('--output')+1]).resolve() != output
        or not any(Path(a).resolve() == (ROOT / 'eis_rs_window_analysis.py').resolve() for a in argv[1:] if not a.startswith('-'))):
        raise ValueError('Unexpected parent command; direct worker invocation forbidden')
    case = next(c for c in spec['case_plan'] if c['id'] == identifier)
    path = output / 'cases' / (identifier + '.json')
    partial = output / 'cases' / (identifier + '-unconstrained.partial.json')
    if path.exists() or partial.exists():
        raise ValueError('Preserve prior/partial fitting case; no retry')
    with (output / '.execution.lock').open('rb') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            raise ValueError('Finite-controller lock is not held')
    with (output / '.worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        check_stop(output)
        profile = read(spec['profiles_path'])[case['profile_key']]
        if (profile['source_sha256'] != case['source_XLSX_file_sha256']
            or canonical(profile['points']) != case['points_canonical_JSON_sha256']):
            raise ValueError('Original spectrum/XLSX/points namespace differs')
        write_new(output / 'logs' / (identifier + '-process.json'), dict(pid=os.getpid(),
            proc_start_ticks=startticks(os.getpid()), parent_pid=parent, cpu_affinity=sorted(os.sched_getaffinity(0)),
            kind='finite_EIS_input_fit_worker', original_fit_execution=False, new_PDE=0))
        def save_unconstrained(data):
            write_new(partial, dict(data, case_id=identifier, input=case))
            check_stop(output)
        result = analyze_points(profile['points'], case['cutoff_Hz'],
            after_unconstrained=save_unconstrained, check=lambda: check_stop(output))
        if (result['n_points'] != case['expected_points']
            or result['actual_frequency_range_Hz'] != case['actual_fit_frequency_range_Hz']):
            raise ValueError('Prepared and actual fit-window point/range metadata differ')
        result.update(case_id=identifier, input=case, input_profile_path=spec['profiles_path'],
            input_profile_file_sha256=manifest['input_file_sha256'][spec['profiles_path']],
            analysis_code_file_sha256=manifest['code_file_sha256'], new_PDE=0, new_field_results=0)
        write_new(path, result)
        verify(manifest['input_file_sha256']); verify(manifest['code_file_sha256'])
        if result['status'] != 'complete':
            raise ValueError('Preserved incomplete/nonpassive/fallback-failed result')
    return result


def execute(output):
    entered = time.monotonic()
    spec, manifest = validate_execution(output)
    check_stop(output)
    with guard.diagnostic_lock(), (output / '.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / 'controller.json').exists() or (output / 'completion.json').exists() or any((output / 'cases').iterdir()):
            raise ValueError('Existing complete/failed/partial run is preserved; no retry')
        started = time.monotonic()
        prior = manifest['prepare_wall_seconds'] + started-entered
        deadline = started + 6600-prior
        state = dict(status='running', pid=os.getpid(), proc_start_ticks=startticks(os.getpid()),
            command=sys.argv, started_utc=now(), current_case=None, cases=[],
            new_unconstrained_fit_calls=0, new_constrained_fallback_calls=0, resource_limits=LIMITS,
            progress_count_scope='Counts from complete cases only; failed/partial call evidence is separately preserved, never assumed zero.',
            original_inputs_fits_boundary_results_GUI_unchanged=True, new_PDE=0, new_field_results=0)
        def persist():
            state.update(updated_utc=now(), total_wall_seconds=prior+time.monotonic()-started)
            atomic(output / 'controller.json', state)
        def interrupt(signum, frame):
            signal.setitimer(signal.ITIMER_REAL, 0)
            raise KeyboardInterrupt('Finite fit run interrupted by signal ' + str(signum))
        def watch(signum, frame):
            try:
                check_stop(output)
                if time.monotonic() >= deadline:
                    raise ResourceStop('total_timeout: registered6600s budget exhausted')
                if guard.process_rss_bytes(os.getpid()) > LIMITS['max_RSS_bytes']:
                    raise ResourceStop('parent_rss_limit: registered3GiB budget exhausted')
                if guard.available_disk_bytes(output) < LIMITS['minimum_free_disk_bytes']:
                    raise ResourceStop('disk_reserve: registered2GiB reserve exhausted')
            except BaseException:
                # Never interrupt child cleanup/failure preservation again.
                signal.setitimer(signal.ITIMER_REAL, 0)
                raise
        oldterm, oldint = signal.signal(signal.SIGTERM, interrupt), signal.signal(signal.SIGINT, interrupt)
        oldalarm = signal.signal(signal.SIGALRM, watch)
        signal.setitimer(signal.ITIMER_REAL, .5, .5)
        try:
            persist()
            for case in spec['case_plan']:
                case_began = time.monotonic()
                check_stop(output)
                verify(manifest['input_file_sha256']); verify(manifest['code_file_sha256'])
                state.update(current_case=case['id']); persist()
                command = [sys.executable, '-u', str(ROOT / 'eis_rs_window_analysis.py'),
                           '--output', str(output), '--worker', case['id']]
                remaining = 600-(time.monotonic()-case_began)
                if remaining <= 0:
                    raise ResourceStop('case_timeout: input checks exhausted registered600s budget')
                record = guard.run_guarded(command, output / 'logs' / (case['id'] + '.log'),
                    timeout_s=remaining, rss_limit_bytes=LIMITS['max_RSS_bytes'],
                    total_deadline=deadline)
                path = output / 'cases' / (case['id'] + '.json')
                result = read(path)
                if (result.get('status') != 'complete' or result.get('case_id') != case['id']
                    or result.get('unconstrained_calls') != 1 or result.get('fallback_calls') not in (0, 1)):
                    raise ValueError('Complete case count/source namespace differs')
                record['case_wall_seconds'] = time.monotonic()-case_began
                if record['case_wall_seconds'] > 600:
                    raise ResourceStop('case_timeout: registered600s budget exhausted')
                state['new_unconstrained_fit_calls'] += 1
                state['new_constrained_fallback_calls'] += result['fallback_calls']
                state['cases'].append(dict(id=case['id'], status='complete', path=str(path),
                    file_sha256=sha(path), fallback_calls=result['fallback_calls'], resources=record))
                if state['new_constrained_fallback_calls'] > 8:
                    raise ValueError('Registered fallback8 cap exceeded')
                persist()
            check_stop(output)
            verify(manifest['input_file_sha256']); verify(manifest['code_file_sha256'])
            total = prior + time.monotonic()-started
            if total > 6600:
                raise ResourceStop('total_timeout: registered6600s final budget exhausted')
            if len(state['cases']) != 8:
                raise ValueError('Registered final eight-condition count failed')
            inventory = read(spec['profile_inventory_path'])
            completion = dict(status='complete', finished_utc=now(), new_unconstrained_fit_calls=8,
                new_constrained_fallback_calls=state['new_constrained_fallback_calls'],
                total_wall_seconds=total, cases=state['cases'], existing_fit_reference_inventory=inventory,
                input_code_unchanged=True, source_input_file_sha256=manifest['input_file_sha256'],
                numeric_producer_Python_file_sha256=manifest['code_file_sha256'],
                original_fits_recomputed=0, new_PDE=0, new_field_results=0,
                scope='Eight input-fit windows only; deterministic sensitivity, not statistical CI or field validation',
                holds=spec['holds'])
            write_new(output / 'completion.json', completion)
            state.update(status='complete', current_case=None, finished_utc=now()); persist()
            return completion
        except BaseException as error:
            signal.setitimer(signal.ITIMER_REAL, 0)
            resources = error.resources if isinstance(error, guard.ValidationStop) else {}
            marker = next((n for n in ('STOP', 'needs_attention', 'needs_physical_validation')
                           if (output / n).exists()), None)
            resource_failure = (isinstance(error, ResourceStop)
                or resources.get('status') in ('case_timeout', 'total_timeout', 'rss_limit', 'disk_reserve'))
            status = ('resource_stopped' if resource_failure else
                      'user_stopped' if isinstance(error, RequestedStop) or marker else
                      'interrupted' if isinstance(error, (KeyboardInterrupt, SystemExit))
                          or resources.get('returncode', 0) < 0 else 'fitting_failed')
            state.update(status=status, stop_marker=marker,
                error_type=type(error).__name__, error=str(error), finished_utc=now(),
                partial_and_original_nonpassive_results_preserved=True)
            if isinstance(error, guard.ValidationStop):
                state['failed_resources'] = error.resources
            identifier = state.get('current_case')
            if identifier:
                state['failed_case_artifacts'] = {str(p): sha(p) for p in
                    (output / 'cases').glob(identifier + '*.json') if p.is_file()}
            persist()
            write_new(output / 'failure.json', state)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, oldalarm)
            signal.signal(signal.SIGTERM, oldterm); signal.signal(signal.SIGINT, oldint)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', action='store_true')
    group.add_argument('--execute', action='store_true')
    group.add_argument('--worker', metavar='CASE')
    args = parser.parse_args()
    output = args.output.resolve()
    result = prepare(output) if args.prepare else execute(output) if args.execute else worker(output, args.worker)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
