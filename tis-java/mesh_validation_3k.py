"""Separate, finite 3 kHz SC/XY validation; original workers stay untouched.

The immutable ten-input preparation is the only accepted physical experiment.
Preparation compiles a private classpath and runs analytic tests, never a full
phantom. --execute requires the separately recorded user execution authorization.
Completed historical baseline data are reused; partial/failed jobs are not retried.
"""
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
import argparse
import copy
import fcntl
import gc
import gzip
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import time

import mesh_validation as common
from explore_tis import ROOT, JAVAC, MATERIALS, atomic, config_text, load_basis, summarize

PREPARATION = ROOT / 'runs/leader-validation-3k-preparation-20261018T0448Z/preregistration.json'
PREPARATION_SHA = '81a92c5be563cbe47d1bfd57768ec5e069454549e331867046efd062773d7833'
FREQUENCIES = (3000, 3030, 9000, 9090)
BASELINES = {'leader': '03542-1', 'reference': 'reference-3k-from-02342-0-geometry'}
AUTHORIZATION = '새 결과를 만드는 작업을 시작하도록'
GIB = 1024 ** 3
LIMITS = dict(max_cells=800000, max_cases=10, max_diagnostic_java_processes=1,
    per_case_wall_seconds=600, total_wall_seconds=6600, max_RSS_bytes=3 * GIB,
    java_heap='2g', java_active_processors=1, java_gc='SerialGC', minimum_free_disk_bytes=2 * GIB)
NUMERICAL = dict(max_residual=2e-7, max_power_error=2e-7, max_current_error=2e-6,
                 max_relative_electrode_area_error=1e-10)
SOURCES = ('TisSweep.java', 'ExploreBasis.java', 'Validation3kBasis.java')
DEPENDENCIES = ('mesh_validation_3k.py', 'mesh_validation.py', 'explore_tis.py',
    'explore_inputs.py', 'fit_ngg_eis.py', 'update_ngg_eis.py',
    'ValidationBasis.java', 'leader_spatial_diagnostics.py',
    'validation_3k_postprocess.py', 'layered_probe_analysis.py', 'native_probe_followup.py')


def now():
    return datetime.now(timezone.utc).isoformat()


def startticks(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])


def validate_spec(spec):
    """Independent 3k registration gate; never mutates the 2k module globals."""
    if common.sha256(PREPARATION) != PREPARATION_SHA:
        raise ValueError('Pinned input preparation changed')
    if spec != json.loads(PREPARATION.read_text()):
        raise ValueError('Registered physical/source/mesh/config conditions changed')
    if spec['baseline_cases'] != BASELINES or tuple(spec['source_conditions']['carrier_Hz']) != (3000, 3030):
        raise ValueError('Only the prepared 3k leader/reference identities are allowed')
    if spec['resource_limits'] != dict(LIMITS, on_limit=spec['resource_limits']['on_limit']):
        raise ValueError('Registered resource limits changed')
    if spec['solver_validation_limits'] != NUMERICAL:
        raise ValueError('Registered conservation or area gates changed')
    if spec['baseline_reproduction_relative_tolerance'] != 2e-7:
        raise ValueError('Baseline reproduction tolerance changed')
    if spec['convergence_relative_limits'] != {k: v / 100 for k, v in common.THRESHOLDS.items()}:
        raise ValueError('Registered per-metric convergence gates changed')
    if spec['mesh_plan']['bulk_z_counts'] != [14, 14, 40]:
        raise ValueError('Bulk-z refinement is a separate experiment')
    plan = spec['case_plan']
    expected = common.case_plan()
    if len(plan) != 10 or len({c['config_sha256'] for c in plan}) != 10:
        raise ValueError('Exactly ten unique prepared configs are required')
    for case, wanted in zip(plan, expected):
        if any(case.get(k) != v for k, v in wanted.items()):
            raise ValueError('Independent SC/XY geometry, order, or mesh changed')
        if case['frequencies_Hz'] != list(FREQUENCIES):
            raise ValueError('Prepared frequencies changed')
        if hashlib.sha256(case['config_text'].encode()).hexdigest() != case['config_sha256']:
            raise ValueError('Prepared config bytes changed')
    return plan


def ensure_xy120_dependencies(cases):
    for geometry in ('reference', 'leader'):
        matched = [c for c in cases if c.get('id') == 'xy100-' + geometry]
        if len(matched) != 1:
            raise ValueError('Both unique XY.5 cases must pass before XY50/120')
        case = matched[0]
        if case.get('status') != 'complete' or case.get('postprocess', {}).get('status') != 'complete':
            raise ValueError('XY.5 producer and postprocessing must both complete')
        validation, resources = case.get('validation', {}), case.get('resources', {})
        for key, limit in NUMERICAL.items():
            if key == 'max_relative_electrode_area_error':
                key = 'max_area_relative_error'
            value = float(validation.get(key, math.inf))
            if not math.isfinite(value) or not 0 <= value <= limit:
                raise ValueError('XY.5 numerical or area gate failed')
        if resources.get('status') != 'complete':
            raise ValueError('XY.5 resource gate failed')
        for key, limit in [('case_wall_seconds', 600), ('peak_rss_bytes', 3 * GIB)]:
            value = float(resources.get(key, math.inf))
            if not math.isfinite(value) or not 0 <= value <= limit:
                raise ValueError('XY.5 resource gate failed: ' + key)


def audit_sources(spec):
    source = Path(spec['source_run']).resolve()
    profile_path = source / 'inputs/eis-profiles.json'
    if common.sha256(profile_path) != spec['source_conditions']['EIS']['profile_sha256']:
        raise ValueError('EIS input hash differs from preparation')
    xlsx = ROOT.parent / spec['source_conditions']['EIS']['source_XLSX']
    if common.sha256(xlsx) != spec['source_conditions']['EIS']['source_XLSX_sha256']:
        raise ValueError('Original EIS XLSX hash changed')
    guards = [PREPARATION, profile_path, xlsx, source / 'solver-sources.json']
    for name, expected in spec['source_hashes'].items():
        for path in (ROOT / name, source / 'inputs' / name):
            if common.sha256(path) != expected:
                raise ValueError('Original source hash changed: ' + str(path))
            guards.append(path)
    profile = json.loads(profile_path.read_text())['0']
    for geometry, task in [('leader', '03542'), ('reference', '02342')]:
        path = source / 'cases' / (task + '.json')
        case = json.loads(path.read_text())
        row = case['candidates'][1 if geometry == 'leader' else 0]
        design = spec['designs'][geometry]
        for k, target in [('xy_mm', 'xy_mm'), ('size_mm', 'pad_size_mm'), ('channels', 'output_channels')]:
            if design[k] != row[target]:
                raise ValueError('Retained geometry changed')
        config = source / 'configs' / (row['basis_id'] + '.properties')
        if common.sha256(config)[:18] != row['basis_id']:
            raise ValueError('Original config/basis identity changed')
        guards.extend((path, config))
    leader = json.loads((source / 'cases/03542.json').read_text())
    row = leader['candidates'][1]
    baseline = source / 'bases' / row['basis_id']
    if not (baseline / 'BASIS_COMPLETE').is_file():
        raise ValueError('Completed leader cache missing; do not regenerate it')
    common.check_numerical_gates(leader['validation'],
        [baseline / f'contacts-{f}.csv' for f in FREQUENCIES], 15)
    raw = common.parse_properties((source / 'configs' / (row['basis_id'] + '.properties')).read_text())
    regenerated = common.parse_properties(config_text(spec['designs']['leader'], profile, .625))
    if raw != regenerated:
        raise ValueError('Retained 3k leader material/contact/source properties differ')
    native_receipt = ROOT / 'runs/depth-probe-20261017T200912Z/cases/tis-03542-1.json'
    native = json.loads(native_receipt.read_text())
    if native['status'] != 'complete' or native['reproduction']['status'] != 'exact':
        raise ValueError('Existing leader native export is not verified')
    common.assert_hashes_unchanged(native['output_hashes'])
    for filename, expected in native['reproduction']['files'].items():
        if common.sha256(baseline / filename) != expected:
            raise ValueError('Original leader and verified native cache no longer match')
    guards.extend(p for p in baseline.iterdir() if p.is_file())
    guards.extend(Path(p) for p in native['output_hashes'])
    guards.append(native_receipt)
    return source, profile_path, baseline, Path(native['basis_dir']), guards


def java_command(manifest):
    return [manifest['java'], '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1',
            '-cp', manifest['classes'], 'Validation3kBasis']


def validate_execution_manifest(manifest):
    output = Path(manifest['output_run']).resolve()
    if output.parent != ROOT / 'runs' or not output.name.startswith('leader-validation-3k-'):
        raise ValueError('Execution output identity differs')
    if manifest.get('status') != 'prepared' or manifest.get('preparation_sha256') != PREPARATION_SHA:
        raise ValueError('Private 3k preparation is not complete')
    spec = json.loads(PREPARATION.read_text())
    validate_spec(spec)
    registration = json.loads((output / 'preregistration.json').read_text())
    if common.sha256(output/'preregistration.json') != manifest['preregistration_sha256']:
        raise ValueError('Execution preregistration hash changed')
    if registration.get('authorization', {}).get('user_instruction') != AUTHORIZATION or registration.get('maximum_new_PDE_cases') != 9:
        raise ValueError('Separate finite execution authorization is absent')
    if manifest.get('resource_limits') != LIMITS or manifest.get('numerical_gates') != NUMERICAL:
        raise ValueError('Execution limits changed')
    if manifest.get('designs') != spec['designs'] or manifest.get('source_run') != spec['source_run']:
        raise ValueError('Execution physical/source identity changed')
    expected_plan = copy.deepcopy(spec['case_plan'])
    for case in expected_plan:
        case.pop('config_text')
        case.update(config_file=str(output/'configs'/(case['id']+'.properties')),
                    execution_action='reuse_verified_complete_basis' if case['id']=='baseline-leader' else 'new_private_solve')
    if manifest.get('plan') != expected_plan or manifest.get('classes') != str(output/'classes'):
        raise ValueError('Execution plan/config/action/classpath changed')
    if manifest.get('baseline_basis_dir') != str(Path(spec['source_run'])/'bases/1ce65b9c7827742bc7'):
        raise ValueError('Reused leader basis identity changed')
    if manifest.get('baseline_native_dir') != str(ROOT/'runs/depth-probe-20261017T200912Z/bases/tis-03542-1'):
        raise ValueError('Reused native leader identity changed')
    for path, expected in registration.get('execution_source_hashes', {}).items():
        if manifest['guard_hashes'].get(path) != expected:
            raise ValueError('Execution code hash namespace differs from preregistration')
    required = [output/'preregistration.json', *[ROOT/n for n in SOURCES+DEPENDENCIES]]
    required += [Path(c['config_file']) for c in expected_plan]
    required += list((output/'private-src').iterdir()) + list((output/'classes').iterdir())
    if any(str(p) not in manifest.get('guard_hashes', {}) for p in required if p.is_file()):
        raise ValueError('Execution source/class/config guards are incomplete')
    common.assert_hashes_unchanged(manifest['guard_hashes'])
    return True


def prepare(output):
    started = time.monotonic()
    output = Path(output).resolve()
    if common.sha256(PREPARATION) != PREPARATION_SHA:
        raise ValueError('Pinned input preparation changed')
    spec = json.loads(PREPARATION.read_text())
    validate_spec(spec)
    source, profile_path, baseline, native, guarded = audit_sources(spec)
    if output.exists():
        manifest = json.loads((output / 'manifest.json').read_text())
        validate_execution_manifest(manifest)
        return manifest
    if output.parent != ROOT / 'runs' or not output.name.startswith('leader-validation-3k-'):
        raise ValueError('Use a new separate leader-validation-3k-* run')
    profile = json.loads(profile_path.read_text())['0']
    for case in spec['case_plan']:
        generated = common.make_config(config_text(spec['designs'][case['geometry']], profile, case['h_xy_mm']),
                                       case['h_xy_mm'], case['sc_cells'])
        if common.parse_properties(generated) != common.parse_properties(case['config_text']):
            raise ValueError('Prepared config no longer reproduces original EIS/materials')
    javac = shutil.which('javac') or (str(JAVAC) if JAVAC.is_file() else None)
    if not javac:
        raise RuntimeError('Installed JDK compiler unavailable')
    java = str(Path(javac).resolve().parent / 'java')
    if not Path(java).is_file():
        raise RuntimeError('Matching JDK runtime unavailable')
    output.mkdir()
    for directory in ('private-src', 'classes', 'inputs', 'configs', 'bases', 'cases', 'logs', 'postprocess'):
        (output / directory).mkdir()
    registration = copy.deepcopy(spec)
    registration.update(status='execution_authorized_preregistered', created_utc=now(),
        preparation_preregistration_sha256=PREPARATION_SHA,
        authorization=dict(user_instruction=AUTHORIZATION, scope='Separate finite3kHz ten-condition SC/XY diagnosis',
            original_worker_restart=False, membrane_model_or_biological_experiment=False),
        completed_basis_reuse={'baseline-leader': str(baseline)}, maximum_new_PDE_cases=9,
        original_physical_hold_preserved=True,
        native_export='Same solve only; full native phi and actual mesh metadata, no extra solve',
        cost=dict(maximum_case_seconds=600, maximum_total_seconds=6600,
                  interpretation='Hard ceilings, not a predicted runtime; includes preparation and postprocessing'))
    registration['execution_policy']['execution_in_this_run'] = True
    registration['execution_policy']['execution_in_this_preparation'] = False
    registration['execution_source_hashes'] = {str(ROOT/name):common.sha256(ROOT/name) for name in SOURCES+DEPENDENCIES}
    atomic(output / 'preregistration.json', registration)
    shutil.copy2(PREPARATION, output / 'inputs/preparation-preregistration.json')
    shutil.copy2(profile_path, output / 'inputs/eis-profiles.json')
    plan = copy.deepcopy(spec['case_plan'])
    for case in plan:
        path = output / 'configs' / (case['id'] + '.properties')
        path.write_text(case.pop('config_text'))
        case.update(config_file=str(path), execution_action='reuse_verified_complete_basis' if case['id'] == 'baseline-leader' else 'new_private_solve')
        guarded.append(path)
    for name in SOURCES:
        shutil.copy2(ROOT / name, output / 'private-src' / name)
    guarded.extend(ROOT / name for name in SOURCES + DEPENDENCIES)
    guarded.extend(ROOT.glob('*.class'))
    guarded.extend((output / 'private-src').iterdir())
    guarded.extend((output / 'inputs').iterdir())
    guarded.append(output / 'preregistration.json')
    guards = {str(p): common.sha256(p) for p in guarded}
    manifest = dict(schema_version=1, created_utc=now(), status='preparing', output_run=str(output),
        preparation_sha256=PREPARATION_SHA, preregistration_sha256=common.sha256(output / 'preregistration.json'),
        source_run=str(source), baseline_basis_dir=str(baseline), baseline_native_dir=str(native),
        plan=plan, resource_limits=LIMITS, numerical_gates=NUMERICAL,
        convergence_thresholds_percent=common.THRESHOLDS, designs=spec['designs'],
        java=java, javac=javac, classes=str(output / 'classes'), guard_hashes=guards)
    atomic(output / 'manifest.json', manifest)
    try:
        with common.diagnostic_lock():
            compiler = common.run_guarded([javac, '-J-Xmx512m', '-J-XX:ActiveProcessorCount=1', '-encoding', 'UTF-8',
                '-d', str(output / 'classes'), '-classpath', str(output / 'classes'),
                '-sourcepath', str(output / 'private-src')] + [str(output / 'private-src' / name) for name in SOURCES],
                output / 'logs/compile.log', timeout_s=120)
            test = common.run_guarded(java_command(manifest) + ['--selftest'], output / 'logs/selftest.log', timeout_s=120)
        manifest['guard_hashes'].update({str(p): common.sha256(p) for p in (output / 'classes').iterdir() if p.is_file()})
        common.assert_hashes_unchanged(manifest['guard_hashes'])
        manifest.update(status='prepared', compiler=compiler, selftest=test,
                        preparation_wall_seconds=time.monotonic() - started)
    except BaseException as error:
        manifest.update(status='preparation_failed', error=str(error), preparation_wall_seconds=time.monotonic()-started)
        atomic(output / 'manifest.json', manifest)
        raise
    atomic(output / 'manifest.json', manifest)
    validate_execution_manifest(manifest)
    return manifest


def mesh_metadata(case, manifest):
    counts = case['layer_counts']
    faces, at = [0.], 0.
    for count, thickness in zip(counts, (.1, 5., 5., 15.)):
        for _ in range(count):
            at += thickness / count
            faces.append(at)
    return dict(h_xy_mm=case['h_xy_mm'], layer_counts=counts, z_faces_mm=faces,
        config_path=case['config_file'], config_sha256=case['config_sha256'], exporter_kind='validation_native',
        source_run_id=Path(manifest['output_run']).name, source_condition_id=case['id'], source_hashes=manifest['guard_hashes'],
        metadata_origin='Prepared fixed stack; checked against actual producer grid and mesh-metadata when available')


def reproduction(metrics, manifest, folder):
    source_case = dict(basis_dir=manifest['baseline_basis_dir'],
                       case_file=str(Path(manifest['source_run']) / 'cases/03542.json'))
    common.check_baseline_reproduction({'id': 'baseline-leader'}, metrics, folder, source_case)
    return dict(status='passed', source_candidate='03542-1', grid_SHA_exact=True,
                raw_metric_relative_tolerance=2e-7, reference_normalization='New same-mesh3k reference; historical2k-normalized rows preserved')


def execute(manifest):
    validate_execution_manifest(manifest)
    output = Path(manifest['output_run'])
    if manifest['status'] != 'prepared':
        raise ValueError('Private preparation failed or is incomplete')
    state_path = output / 'controller.json'
    with common.diagnostic_lock(), (output / '.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / 'summary.json').exists():
            previous = json.loads((output / 'summary.json').read_text())
            common.assert_hashes_unchanged(manifest['guard_hashes'])
            if previous['status'] == 'complete':
                return previous
            raise ValueError('Previous execution/partial/failure exists: preserve without automatic retry')
        started = time.monotonic()
        prior = manifest['preparation_wall_seconds']
        deadline = started + LIMITS['total_wall_seconds'] - prior
        summary = dict(schema_version=1, status='running', source_run=manifest['source_run'],
            preregistration_sha256=manifest['preregistration_sha256'], created_utc=now(),
            resource_limits=LIMITS, cases=[], new_PDE_count=0, new_PDE_started=0, reused_complete_basis_count=0,
            original_physical_hold_preserved=True, convergence=common.review_convergence([]))
        state = dict(pid=os.getpid(), proc_start_ticks=startticks(os.getpid()), status='running', started_utc=now(),
            command=Path('/proc/self/cmdline').read_bytes().replace(b'\0', b' ').decode().strip(),
            current_case=None, completed_cases=0, new_PDE_started=0, maximum_new_PDE_cases=9)
        watch = {'started': None}
        def persist():
            summary.update(updated_utc=now(), total_wall_seconds=prior + time.monotonic() - started,
                convergence=common.review_convergence(summary['cases']),
                adjacent_trends=common.adjacent_trends(summary['cases']),
                geometry_comparisons=common.geometry_comparisons(summary['cases']))
            atomic(output / 'summary.json', summary)
            state.update(updated_utc=now(), completed_cases=len(summary['cases']))
            atomic(state_path, state)
        def watchdog(signum, frame):
            t = time.monotonic()
            reason = ('total_timeout' if t >= deadline else
                'case_timeout' if watch['started'] is not None and t-watch['started'] > 600 else
                'driver_rss_limit' if common.process_rss_bytes(os.getpid()) > 3*GIB else
                'disk_reserve' if common.available_disk_bytes(output) < 2*GIB else None)
            if reason:
                signal.setitimer(signal.ITIMER_REAL, 0)
                raise common.ValidationStop(reason, {'status': reason})
        old_handler = signal.signal(signal.SIGALRM, watchdog)
        signal.setitimer(signal.ITIMER_REAL, .5, .5)
        active_case = None
        try:
            persist()
            profile = json.loads((output / 'inputs/eis-profiles.json').read_text())['0']
            for case in manifest['plan']:
                active_case = case
                watch['started'] = time.monotonic()
                common.assert_hashes_unchanged(manifest['guard_hashes'])
                state.update(current_case=case['id'], phase='source_validation')
                persist()
                gc.collect()
                reused = case['execution_action'] == 'reuse_verified_complete_basis'
                folder = Path(manifest['baseline_basis_dir']) if reused else output / 'bases' / case['id']
                if not reused:
                    if folder.exists():
                        raise ValueError('Partial basis exists; never overwrite or retry it')
                    if case['mesh_id'] == 'xy120':
                        ensure_xy120_dependencies(summary['cases'])
                    expected_bytes = case['cells'] * 680
                    if common.available_disk_bytes(output) < 2*GIB + expected_bytes:
                        raise common.ValidationStop('disk_reserve', {'expected_output_bytes': expected_bytes})
                    state.update(phase='solving', new_PDE_started=state['new_PDE_started']+1)
                    summary['new_PDE_started'] = state['new_PDE_started']
                    persist()
                    resources = common.run_guarded(java_command(manifest) + [case['config_file'], str(folder)],
                        output / 'logs' / (case['id']+'.log'), total_deadline=deadline,
                        timeout_s=600-(time.monotonic()-watch['started']))
                    summary['new_PDE_count'] += 1
                else:
                    resources = dict(status='reused_verified_complete_basis', new_PDE=False)
                    summary['reused_complete_basis_count'] += 1
                common.assert_hashes_unchanged(manifest['guard_hashes'])
                validation = json.loads((folder / 'validation.json').read_text())
                areas = common.check_numerical_gates(validation, [folder/f'contacts-{f}.csv' for f in FREQUENCIES],
                                                     manifest['designs'][case['geometry']]['size_mm'])
                if validation['cells'] != case['cells'] or not (folder / 'BASIS_COMPLETE').is_file():
                    raise ValueError('Complete basis or actual/preflight cell count mismatch')
                state.update(phase='electrical_postprocessing')
                persist()
                basis = load_basis(folder, 2, FREQUENCIES)
                design = manifest['designs'][case['geometry']]
                producer_sha = manifest['guard_hashes'][str(ROOT/('ExploreBasis.java' if reused else 'Validation3kBasis.java'))]
                key = hashlib.sha256((case['config_sha256']+producer_sha).encode()).hexdigest()[:18]
                if case['geometry'] == 'reference':
                    reference = next(r for r in summarize(basis, design, profile, key, case['h_xy_mm']) if r['waveform'] == 'sine')
                else:
                    ref_case = next(c for c in summary['cases'] if c['geometry']=='reference' and c['mesh_id']==case['mesh_id'])
                    reference = next(r for r in ref_case['metrics'] if r['waveform']=='sine')
                metrics = summarize(basis, design, profile, key, case['h_xy_mm'], reference=reference)
                del basis
                gc.collect()
                result = dict(case, status='complete', basis_dir=str(folder), validation=validation, metrics=metrics,
                    physical_pad_areas_m2=areas, resources=resources, baseline_reproduced=False,
                    producer_source_sha256=producer_sha,
                    producer_kind='reused_original_ExploreBasis' if reused else 'private_Validation3kBasis',
                    analysis_code_sha256=manifest['guard_hashes'][str(ROOT/'mesh_validation_3k.py')],
                    output_hashes={str(p):common.sha256(p) for p in folder.iterdir() if p.is_file()})
                if reused:
                    result.update(baseline_reproduced=True, baseline_reproduction=reproduction(metrics, manifest, folder))
                atomic(output / 'cases' / (case['id']+'.json'), result)
                summary['cases'].append(result)
                state.update(phase='native_and_spatial_postprocessing')
                persist()
                from validation_3k_postprocess import analyze_case
                try:
                    metadata = mesh_metadata(case, manifest)
                    post = analyze_case(folder, metrics, metadata,
                        potential_dir=manifest['baseline_native_dir'] if reused else None)
                    with gzip.open(output/'postprocess'/(case['id']+'.json.gz'), 'wt', encoding='utf-8') as stream:
                        json.dump(post, stream, ensure_ascii=False, allow_nan=False)
                    spatial_complete = all(w['spatial'].get('status') == 'complete' for w in post['waveforms'])
                    result['postprocess'] = dict(status='complete', native_probe_status='complete',
                        spatial_status='complete' if spatial_complete else 'incomplete_or_failed',
                        combined_status=post['status'], path=str(output/'postprocess'/(case['id']+'.json.gz')),
                        sha256=common.sha256(output/'postprocess'/(case['id']+'.json.gz')))
                except BaseException as error:
                    result['postprocess'] = dict(status='failed', error=str(error))
                    atomic(output/'cases'/(case['id']+'.json'), result)
                    summary.update(status='postprocessing_failed', error=str(error), failed_case=case['id'])
                    raise
                resources.update(case_wall_seconds=time.monotonic()-watch['started'], driver_peak_rss_bytes=common.process_rss_bytes(os.getpid()))
                atomic(output/'cases'/(case['id']+'.json'), result)
                common.assert_hashes_unchanged(manifest['guard_hashes'])
                persist()
                print(json.dumps({'case':case['id'], 'status':'complete', 'new_PDE':not reused,
                    'case_wall_seconds':resources['case_wall_seconds']}), flush=True)
            summary['status'] = 'complete'
            state.update(status='complete', phase='finished', current_case=None)
        except BaseException as error:
            if summary['status'] != 'postprocessing_failed':
                summary['status'] = 'interrupted' if isinstance(error, (KeyboardInterrupt, SystemExit)) else 'stopped'
            summary.update(error=str(error), failed_case=active_case['id'] if active_case else None)
            if isinstance(error, common.ValidationStop):
                summary['failed_resources'] = error.resources
            state.update(status=summary['status'], error=str(error))
            persist()
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
        persist()
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute:
        manifest = json.loads((args.output / 'manifest.json').read_text())
        common.assert_hashes_unchanged(manifest['guard_hashes'])
        receipt = json.loads((args.output / 'execution-publication.json').read_text())
        if receipt.get('status') != 'published_before_PDE' or receipt.get('preregistration_sha256') != manifest['preregistration_sha256']:
            raise ValueError('Reviewed execution preregistration must be published before a full PDE')
        if receipt.get('manifest_sha256') != common.sha256(args.output/'manifest.json'):
            raise ValueError('Published execution manifest hash differs')
        result = execute(manifest)
        print(json.dumps({'status':result['status'], 'cases':len(result['cases']), 'convergence':result['convergence']['status']}))
    else:
        result = prepare(args.output)
        print(json.dumps({'status':result['status'], 'cases':len(result['plan']), 'full_phantom_PDE':0}))


if __name__ == '__main__':
    main()
