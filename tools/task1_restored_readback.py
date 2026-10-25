"""Representative metrics/probes from independently restored NEW cloud bytes.

This uses the archived frozen research helpers without editing their source,
exporter identity, configuration bytes or hashes. It never solves a PDE or
reads the live numerical source tree. The first supported case is the compact
four-pad coarse baseline; grouped-pad relocation requires a separate reviewed
adapter because its loader follows the preserved absolute mask.path value.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import sys
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
RELATIVE_TOLERANCE = 1e-10
ABSOLUTE_TOLERANCE = 1e-14
SUPPORTED_CASE = 'baseline-square15-coarse'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def atomic(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def rss():
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('VmRSS:'):
            return int(line.split()[1])*1024
    return 0


def compare_value(label, expected, actual):
    expected, actual = float(expected), float(actual)
    require(math.isfinite(expected) and math.isfinite(actual), 'Finite restored metric required: '+label)
    error = abs(actual-expected)
    return dict(metric=label, expected=expected, actual=actual, absolute_error=error,
                relative_error=error/max(abs(expected), 1e-300),
                passed=error <= ABSOLUTE_TOLERANCE+RELATIVE_TOLERANCE*abs(expected))


def square_values(metrics, volume):
    target = volume['regions']['target']['statistics']
    superficial = volume['regions']['surface_0_5']['statistics']['maxTIS']
    return dict(roi_mean_TIS_V_m=target['maxTIS']['mean'], roi_P10_TIS_V_m=target['maxTIS']['p10'],
        roi_mean_E_RMS_V_m=target['RMS']['mean'], central20_TIS_V_m=metrics['target20_modulation_V_m'],
        central20_E_RMS_V_m=metrics['target20_total_E_RMS_V_m'],
        Jmax_A_m2=metrics['surface_J_RMS_max_A_m2'], J95_A_m2=metrics['surface_J_RMS_p95_A_m2'],
        contact_voltage_RMS_V=metrics['contact_voltage_RMS_max_V'], SC_power_W=metrics['SC_power_W'],
        contact_power_W=metrics['contact_power_W'], source_power_W=metrics['source_power_W'],
        surface_0_5_P95_TIS_V_m=superficial['p95'], surface_0_5_max_TIS_V_m=superficial['max'])


def readback(restored_run, case_id, deadline):
    require(case_id == SUPPORTED_CASE, 'First readback supports only baseline-square15-coarse; grouped loader not remapped')
    restored_run = Path(restored_run)
    restore_root = restored_run.parent
    manifest_path = restore_root/'ARCHIVE_MANIFEST.json'
    restore_receipt_path = restore_root/'CLEAN_RESTORE_RECEIPT.json'
    require(manifest_path.is_file() and restore_receipt_path.is_file(),
            'Archive embedded manifest and clean restore receipt must be beside restored run')
    manifest, receipt = read(manifest_path), read(restore_receipt_path)
    require(manifest.get('schema') == 'task1-new-native-archive-v1' and
            manifest.get('run_id') == receipt.get('run_id') == restored_run.name,
            'Restored archive/run identity differs')
    require(receipt.get('clean_restored_file_hash_verification') == 'passed' and
            receipt.get('byte_hash_verification') == 'passed' and
            isinstance(receipt.get('archive_sha256'), str) and len(receipt['archive_sha256']) == 64,
            'A prior pinned archive and full clean file-hash restore receipt is required')
    files = {}
    for item in manifest['files']:
        p = PurePosixPath(item['path'])
        require(not p.is_absolute() and '\\' not in item['path'] and
                all(part not in ('', '.', '..') for part in item['path'].split('/')),
                'Unsafe embedded archive path')
        require(item['path'] not in files, 'Duplicate embedded file path')
        files[item['path']] = item
    verified = {}

    def verify(relative):
        require(time.monotonic() < deadline, 'Restore readback deadline during hash checks')
        relative = Path(relative).as_posix()
        require(relative in files, 'Restored input absent from embedded manifest: '+relative)
        path = restored_run/relative
        item = files[relative]
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(restored_run) and
                path.stat().st_size == item['bytes'] and sha(path) == item['sha256'],
                'Restored file SHA/size/path differs: '+relative)
        verified[relative] = item['sha256']
        return path

    pre_path = verify('preregistration.json')
    require(sha(pre_path) == manifest['preregistration_sha256'], 'Restored preregistration top-level pin differs')
    pre = read(pre_path)
    cases = [case for case in pre['cases'] if case['id'] == case_id]
    require(len(cases) == 1, 'One exact restored baseline registration required')
    original_case = cases[0]
    require(original_case['channels'] == 2 and original_case['h_xy_mm'] == 1.25 and
            original_case['sc_cells'] == 2 and original_case['bulk_counts'] == [14, 14, 40],
            'Representative baseline physical mesh differs')
    old_run = Path(original_case['config_file']).parent.parent
    config = verify('configs/'+Path(original_case['config_file']).name)
    mask = verify('masks/'+Path(original_case['mask_file']).name)
    require(sha(config) == original_case['config_sha256'] and sha(mask) == original_case['mask_sha256'],
            'Restored config or physical mask registration SHA differs')
    record = read(verify('cases/'+case_id+'.json'))
    post_path = verify('postprocess/'+case_id+'/summary.json')
    probes_path = verify('postprocess/'+case_id+'/probes.json')
    require(record['status'] == 'complete' and sha(post_path) == record['postprocess_sha256'],
            'Restored original completed postprocess pin differs')
    original_post = read(post_path)
    require(original_post['status'] == 'complete' and original_post['id'] == case_id,
            'Restored complete matching baseline postprocess required')
    basis_relative = 'bases/'+case_id
    native_names = [name for name in files if name.startswith(basis_relative+'/')]
    require(bool(native_names), 'Archived raw native inputs missing')
    for relative in native_names:
        verify(relative)
        old_path = str(old_run/relative)
        if old_path in original_post['input_sha256']:
            require(original_post['input_sha256'][old_path] == verified[relative],
                    'Archived raw input differs from original numerical provenance: '+relative)
    require(original_post['input_sha256'].get(str(old_run/'configs'/config.name)) == sha(config),
            'Restored numerical/config join differs')
    frozen_manifest = read(verify('frozen-source-manifest.json'))
    frozen_root = restored_run/'frozen-source/tis-java'
    for source, item in frozen_manifest['files'].items():
        parts = PurePosixPath(item['path']).parts
        require(parts.count('frozen-source') == 1, 'Unique frozen source directory marker required')
        relative = Path(*parts[parts.index('frozen-source'):])
        frozen = verify(relative)
        require(sha(frozen) == item['sha256'] == pre['source_and_input_sha256'][source],
                'Frozen source/preexecution registration SHA differs: '+source)
    require(frozen_root.is_dir(), 'Frozen archived research directory unavailable')
    require(not any(frozen_root.rglob('*.pyc')) and not any(frozen_root.rglob('*.pyo')),
            'Frozen readback must import recorded Python source, without preexisting bytecode')

    # No .pyc files may be created in restored evidence. No live numerical data
    # or source files may be accessed, even when preserved absolute paths exist.
    sys.dont_write_bytecode = True
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    forbidden = (ROOT/'data-native', ROOT/'tis-java')
    source_access_attempts = []

    def audit(event, args):
        if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.path.abspath(os.fsdecode(args[0])))
            if any(path == directory or path.is_relative_to(directory) for directory in forbidden):
                source_access_attempts.append(str(path))
                raise RuntimeError('Live source/native fallback is forbidden during restored readback: '+str(path))
            if path == restore_root or path.is_relative_to(restore_root):
                mode = args[1] if len(args) > 1 else None
                flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
                writing = (isinstance(mode, str) and any(letter in mode for letter in 'wax+')) or bool(
                    flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
                if writing:
                    raise RuntimeError('Restored evidence writes are forbidden: '+str(path))
        if event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.rename'):
            for arg in args[:2]:
                if isinstance(arg, (str, bytes, os.PathLike)):
                    path = Path(os.path.abspath(os.fsdecode(arg)))
                    if path == restore_root or path.is_relative_to(restore_root):
                        raise RuntimeError('Restored evidence mutation is forbidden: '+str(path))

    sys.addaudithook(audit)
    sys.path.insert(0, str(frozen_root))
    require('selectivity_postprocess' not in sys.modules, 'Readback requires a fresh interpreter without live research imports')
    h = importlib.import_module('selectivity_postprocess')
    evaluate_volume = importlib.import_module('selectivity_volume').evaluate_volume
    evaluate_layered_probe = importlib.import_module('layered_probe_analysis').evaluate_layered_probe
    np = importlib.import_module('numpy')
    imported = {}
    for name in ('selectivity_postprocess', 'selectivity_volume', 'layered_probe_analysis',
                 'explore_tis', 'explore_inputs', 'fit_ngg_eis', 'update_ngg_eis'):
        module = sys.modules[name]
        path = Path(module.__file__).resolve()
        require(path.is_relative_to(frozen_root), 'Research helper was not loaded from archived frozen source: '+name)
        verify(path.relative_to(restored_run))
        imported[name] = dict(path=str(path), sha256=sha(path))
    case = copy.deepcopy(original_case)
    case['config_file'], case['mask_file'] = str(config), str(mask)
    basis = h._load_basis(restored_run/basis_relative, case, deadline)
    geometry, volume_meta = h._geometry(basis, case)
    coefficients = h._coefficients(2, 'square_3h')
    spectra = h._spectra(basis, coefficients)
    volume = evaluate_volume(spectra, basis['grid'], volume_meta,
        fundamental_frequencies_Hz=(3000, 3030), thresholds=case.get('thresholds'),
        fibonacci_count=2048, chunk_cells=256, deadline_monotonic=deadline)
    metrics = h._electrical(basis, coefficients, geometry, deadline)
    old_conditions = [item for item in original_post['conditions'] if item['waveform'] == 'square_3h']
    require(len(old_conditions) == 1, 'Unique original square_3h condition required')
    old_condition = old_conditions[0]
    old_values = square_values(old_condition['metrics'], old_condition['volume_metrics'])
    new_values = square_values(metrics, volume['metrics'])
    metric_checks = [compare_value(name, old_values[name], value) for name, value in new_values.items()]
    require(len(metric_checks) == 13, 'All13 representative restored metrics required')
    probe = evaluate_layered_probe(basis['grid'],
        {f: basis['f'][f]['potential'] for f in (3000, 3030, 9000, 9090)},
        {f: basis['f'][f]['field'] for f in (3000, 3030, 9000, 9090)}, geometry, coefficients,
        provenance=dict(source_run_id=restored_run.name, source_condition_id=case_id,
            source_candidate_id=case_id+'-square_3h', input_sha256=h._digest(basis['hashes']),
            code_sha256=imported['selectivity_postprocess']['sha256'], result_sha256=h._digest(basis['validation'])),
        fundamental_frequencies_Hz=(3000, 3030))
    require(probe['status'] == 'complete' and probe['counts']['complete'] == 40 and
            probe['numerical_checks']['all_passed'], 'Restored nativephi/E or40-probe numerical gate failed')
    old_probe_conditions = [item for item in read(probes_path)['conditions'] if item['waveform'] == 'square_3h']
    require(len(old_probe_conditions) == 1, 'Unique original square_3h probe bundle required')
    old_probe = old_probe_conditions[0]['probe40']
    require(old_probe['status'] == 'complete' and old_probe['counts']['complete'] == 40,
            'Complete original40-probe source required')
    old_by_id = {row['id']: row for row in old_probe['measurements']}
    require(len(old_by_id) == 40 and {row['id'] for row in probe['measurements']} == set(old_by_id),
            'Original/restored physical probe layout IDs differ')
    probe_checks = []
    for row in probe['measurements']:
        previous = old_by_id[row['id']]
        checks = [compare_value(name, previous[name], row[name])
                  for name in ('Vpp_lower_V', 'Vpp_upper_V', 'RMS_V')]
        before = {item['frequency_Hz']: item for item in previous['spectrum']}
        after = {item['frequency_Hz']: item for item in row['spectrum']}
        require(set(before) == set(after) == {3000, 3030, 9000, 9090}, 'Restored actual-frequency spectrum differs')
        for frequency in sorted(before):
            for name in ('real_V', 'imaginary_V'):
                checks.append(compare_value(str(frequency)+'Hz_'+name, before[frequency][name], after[frequency][name]))
        probe_checks.append(dict(probe_id=row['id'], checks=checks, passed=all(item['passed'] for item in checks)))
    for relative, expected in list(verified.items()):
        require(sha(restored_run/relative) == expected, 'Restored evidence changed during readback: '+relative)
    passed = all(item['passed'] for item in metric_checks+probe_checks)
    return dict(schema='task1-restored-new-native-metric-readback-v1',
        status='passed' if passed else 'failed_metric_readback', restored_run=str(restored_run),
        run_id=restored_run.name, case_id=case_id, source_commit=pre['source_commit'],
        archive_sha256=receipt['archive_sha256'], embedded_manifest_sha256=sha(manifest_path),
        clean_restore_receipt_sha256=sha(restore_receipt_path),
        representative_waveform='square_3h', scalar_checks=metric_checks, scalar_check_count=13,
        probe_checks=probe_checks, complete_probe_count=40, probe_numeric_check_count=440,
        comparison_relative_tolerance=RELATIVE_TOLERANCE, comparison_absolute_tolerance_SI=ABSOLUTE_TOLERANCE,
        frozen_imports=imported, python_version=sys.version, numpy_version=np.__version__,
        verified_restored_file_sha256=verified,
        path_adapter=dict(changed_in_memory_case_fields=['config_file', 'mask_file'],
            config_bytes_changed=False, original_internal_mask_path_preserved=True,
            exporter_identity_changed=False, native_config_hash_unchanged=True,
            purpose='Resolve copied case file locations only; frozen four-pad loader never reads internalmask.path'),
        live_source_access_forbidden=True, attempted_live_source_accesses=source_access_attempts,
        restored_evidence_write_guard_enabled=True, restored_evidence_bytes_unchanged=True,
        native_phi_E_numerical_checks=probe['numerical_checks'],
        coordinates=dict(surface_z_mm=0, depth_axis='+z', probe_gap_mm=5,
                         probe_centre_pitch_mm=5, depths_mm=[5, 10, 15, 20]),
        scope='Representative recalculation from restored NEW cloud raw E/phi with archived frozen code; not recovery of missing historical raw data',
        new_PDE=0, independent_solver_validation=False, mesh_convergence_validated=False,
        experimental_validation=False, external_storage_independence_verified_by_this_script=False,
        original_environment_retirement_allowed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restored-run', type=Path, required=True)
    parser.add_argument('--case', default=SUPPORTED_CASE)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    restored = args.restored_run.absolute()
    output = args.output.absolute()
    require(restored == restored.resolve() and restored.is_dir() and not restored.is_relative_to(ROOT/'data-native'),
            'Canonical independent restored inspection directory required')
    require(output == output.resolve() and not output.exists() and output.parent.is_dir() and
            not output.is_relative_to(restored.parent), 'New output outside restored evidence is required')
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        budgetpath = ROOT/'runtime/task1-budget.json'
        require(budgetpath.is_file(), 'Existing cumulative Task1 budget ledger required')
        budget = read(budgetpath)
        require(budget['limit_seconds'] == 6600 and 0 <= budget['spent_seconds'] < 6600,
                'Cumulative6600s budget exhausted or changed')
        start = time.monotonic()
        seconds = min(180., 6600-budget['spent_seconds'])
        deadline = start+seconds
        stopped = threading.Event()
        guard_error = []
        peak = [rss()]

        def interrupt(signum, frame):
            raise RuntimeError(guard_error[0] if guard_error else 'Restored readback180s or cumulative deadline')

        signal.signal(signal.SIGALRM, interrupt)
        signal.signal(signal.SIGUSR1, interrupt)
        signal.setitimer(signal.ITIMER_REAL, seconds)

        def monitor():
            while not stopped.wait(.2):
                try:
                    current = rss()
                    peak[0] = max(peak[0], current)
                    require(current <= 3*GIB, 'Restored readback RSS exceeds3GiB')
                    require(shutil.disk_usage(output.parent).free >= 2*GIB and
                            shutil.disk_usage(restored).free >= 2*GIB, 'Restored readback2GiB reserve unavailable')
                    require(time.monotonic() < deadline, 'Restored readback bounded deadline')
                except BaseException as error:
                    guard_error.append(str(error)); os.kill(os.getpid(), signal.SIGUSR1); return

        watcher = threading.Thread(target=monitor, daemon=True, name='bounded-restored-readback')
        watcher.start()
        result = dict(status='failed_readback', run_id=restored.name, case_id=args.case)
        try:
            require(shutil.disk_usage(output.parent).free >= 2*GIB and shutil.disk_usage(restored).free >= 2*GIB,
                    'Restored readback unchanged2GiB reserve unavailable')
            result = readback(restored, args.case, deadline)
        except BaseException as error:
            result.update(status='failed_readback', error_type=type(error).__name__, error=str(error),
                          original_and_partial_evidence_preserved=True, automatic_retry=False,
                          new_PDE=0, original_environment_retirement_allowed=False)
        finally:
            stopped.set(); watcher.join(timeout=1)
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-start
            budget['spent_seconds'] += elapsed
            budget['runs'].append(dict(run_id=restored.name, case_id=args.case,
                stage='restored_new_native_metric_readback', status=result['status'], seconds=elapsed))
            atomic(budgetpath, budget)
        result.update(observed_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=elapsed,
            sampled_peak_RSS_bytes=peak[0], CPU_count=1, per_readback_seconds_limit=180,
            cumulative_seconds_limit=6600, disk_reserve_bytes=2*GIB, tool_sha256=sha(__file__))
        with output.open('x') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
        print(json.dumps(dict(status=result['status'], output=str(output), seconds=elapsed), ensure_ascii=False))
        return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    sys.exit(main())
