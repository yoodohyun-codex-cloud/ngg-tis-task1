#!/usr/bin/env python3
"""Locked, finite read-only audit of newly computed Task 1 native outputs.

No PDE, original edits, retries or source scaling.  Native cell maxima and
depth curves supplement process_case, whose stored statistics omit locations.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import numpy as np

from task1_waveform_check import bulk_skin_current_density, _verified_config, layer_losses_from_matrices


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO/'tis-java'
GIB = 1024**3
INTERFACES = np.array([0., .1, 5.1, 10.1, 25.1])


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def statistics(values, weights):
    use = np.asarray(weights) > 0
    v, w = np.asarray(values)[use], np.asarray(weights)[use]
    if (not len(v) or not np.isfinite(v).all() or not np.isfinite(w).all()
            or np.any(w <= 0)):
        raise ValueError('Complete finite native samples with positive volume required')
    order = np.argsort(v, kind='stable')
    cumulative = np.cumsum(w[order])
    result = dict(mean=float(v@w/w.sum()), min=float(v.min()), max=float(v.max()),
                  represented_volume_m3=float(w.sum()), cells=len(v))
    for name, fraction in [('p10', .1), ('p95', .95)]:
        index = min(int(np.searchsorted(cumulative, fraction*cumulative[-1])), len(v)-1)
        result[name] = float(v[order[index]])
    return result


def maximum_location(grid, values, weights):
    ids = np.flatnonzero(np.asarray(weights) > 0)
    if not len(ids):
        raise ValueError('Required maximum region has no represented volume')
    selected = ids[int(np.argmax(values[ids]))]
    xyz = [float(grid[name][selected]) for name in ('x_mm', 'y_mm', 'z_mm')]
    tied = ids[values[ids] == values[selected]]
    return dict(value_V_m=float(values[selected]), first_native_cell_index=int(selected),
                cell_centre_mm=xyz, tissue_id=int(grid['layer'][selected]),
                exact_tied_maximum_cells=len(tied),
                tied_cell_centre_bounds_mm={name: [float(grid[name][tied].min()), float(grid[name][tied].max())]
                                           for name in ('x_mm', 'y_mm', 'z_mm')},
                distance_to_nearest_physical_layer_boundary_mm=float(np.min(abs(INTERFACES-xyz[2]))),
                centre_inside_nominal_target=math.hypot(*xyz[:2]) <= 5 and 15 <= xyz[2] <= 20,
                scope='cell-constant maximum over positive-overlap native cells; not continuum/interpolated maximum')


def spatial_from_arrays(grid, scalars, weights, central_column_weights, thresholds):
    """Pure native scalar/location audit, independently testable without imports."""
    result = dict(global_maxima={}, target_maxima={}, layer_maxima={}, depth_planes=[], high_modulation={})
    for name, values in scalars.items():
        if values.shape != (len(grid),) or not np.isfinite(values).all() or np.any(values < 0):
            raise ValueError('Nonnegative finite complete scalar field required: '+name)
        result['global_maxima'][name] = maximum_location(grid, values, weights['total'])
        result['target_maxima'][name] = maximum_location(grid, values, weights['target'])
        result['layer_maxima'][name] = {
            str(layer): maximum_location(grid, values, weights['total']*(grid['layer'] == layer))
            for layer in np.unique(grid['layer'])}
    for depth in np.unique(grid['z_mm']):
        use = grid['z_mm'] == depth
        result['depth_planes'].append(dict(depth_from_surface_mm=float(depth),
            tissue_id=int(grid['layer'][use][0]),
            whole_plane={name: statistics(values[use], weights['total'][use]) for name, values in scalars.items()},
            central_r5_column={name: statistics(values[use], central_column_weights[use]) for name, values in scalars.items()}))
    for name, cutoff in thresholds.items():
        result['high_modulation'][name] = dict(cutoff_V_m=float(cutoff),
            interpretation='fixed same-grid baseline-relative electrical map cutoff; not activation or safety limit',
            regions={})
        for region in ('total', 'target', 'surface_0_5', 'off_target'):
            w = weights[region]
            high = (scalars['maxTIS'] >= cutoff) & (w > 0)
            locations = np.column_stack([grid[key][high] for key in ('x_mm', 'y_mm', 'z_mm')])
            result['high_modulation'][name]['regions'][region] = dict(
                volume_mm3=float(w[high].sum()*1e9), fraction=float(w[high].sum()/w.sum()),
                cell_centre_bounds_mm=(np.column_stack((locations.min(axis=0), locations.max(axis=0))).tolist()
                                       if len(locations) else None),
                bounding_box_axis_order=['x', 'y', 'depth_z'],
                maximum_scope='bounding extent of qualifying overlap cells; not connected-component focus')
    for metric in scalars:
        winner = max(result['depth_planes'], key=lambda row: row['central_r5_column'][metric]['mean'])
        result.setdefault('central_column_peak_mean_depth', {})[metric] = dict(
            depth_mm=winner['depth_from_surface_mm'], value_V_m=winner['central_r5_column'][metric]['mean'],
            tissue_id=winner['tissue_id'], in_target_depth_15_20=15 <= winner['depth_from_surface_mm'] <= 20)
    result['definitions'] = dict(coordinates='z=0 skin surface; +z depth; local phantom X/Y',
        target='r<=5mm, z15–20mm with fractional XY area and exact depth overlap',
        central_column='r<=5mm fractional XY disk overlap, all depths',
        depth_plane_weighting='native represented cell volumes within each actual z plane',
        maxTIS='fundamental-only two-carrier finite 2074-direction envelope width',
        RMS='all-active-harmonic vector E RMS',
        boundary_warning='High E at material interfaces/contact edges is not evidence of deep focusing',
        success_status='no deep-focus or convergence success inferred by this audit')
    return result


def _same_grid_baseline(summary, baseline):
    keys = ('h_xy_mm', 'radius_mm', 'total_depth_mm', 'sc_cells', 'bulk_layer_counts',
            'z_faces_mm', 'tissue_boundaries_mm', 'field_reconstruction', 'source_resistance_ohm')
    if any(summary['mesh_metadata'].get(key) != baseline['mesh_metadata'].get(key) for key in keys):
        raise ValueError('Baseline-relative threshold requires identical mesh and field reconstruction')
    a, b = _verified_config(summary), _verified_config(baseline)
    relevant = {key for key in a if key.endswith(('.sigma', '.epsilon_r')) or key.startswith('z.')}
    if not relevant or any(a.get(key) != b.get(key) for key in relevant):
        raise ValueError('Baseline tissue/contact physical models differ')


def audit(run, case_id, baseline_summary_path, deadline):
    registration_path = run/'preregistration.json'
    pre = read(registration_path)
    matches = [case for case in pre['cases'] if case['id'] == case_id]
    if len(matches) != 1:
        raise ValueError('One exact preregistered case required')
    case = matches[0]
    summary_path = run/'postprocess'/case_id/'summary.json'
    summary = read(summary_path)
    if summary['status'] != 'complete' or summary['id'] != case_id:
        raise ValueError('Only the exact completed case can be audited')
    record = read(run/'cases'/(case_id+'.json'))
    if record['postprocess_sha256'] != sha(summary_path):
        raise ValueError('Postprocess summary differs from completed case record')
    baseline = read(baseline_summary_path)
    if baseline['status'] != 'complete' or baseline['mesh_metadata']['channels'] != 2:
        raise ValueError('Completed four-pad TIS baseline required')
    _same_grid_baseline(summary, baseline)
    baseline_square = [row for row in baseline['conditions'] if row['waveform'] == 'square_3h']
    if len(baseline_square) != 1:
        raise ValueError('One explicit baseline square_3h required')
    bt = baseline_square[0]['volume_metrics']['regions']['target']['statistics']['maxTIS']
    thresholds = dict(baseline_ROI_P10=bt['p10'], half_baseline_ROI_mean=.5*bt['mean'])
    if min(thresholds.values()) <= 0:
        raise ValueError('Positive baseline relative thresholds required')
    # Imports are intentionally inside the locked execution path, after checking
    # actual complete provenance; never import research code for inventory.
    frozen = read(run/'frozen-source-manifest.json') if (run/'frozen-source-manifest.json').exists() else {'files': {}}
    for path, expected in pre['source_and_input_sha256'].items():
        if sha(path) != expected:
            snapshot = frozen['files'].get(path)
            if snapshot is None or sha(snapshot['path']) != expected:
                raise ValueError('Pinned source/input changed without exact frozen copy: '+path)
    frozen_research = run/'frozen-source/tis-java'
    sys.path.insert(0, str(frozen_research if frozen_research.is_dir() else SOURCE))
    from selectivity_postprocess import _load_basis, _geometry, _coefficients, _spectra
    from selectivity_volume import _disk_fractions
    basis = _load_basis(run/'bases'/case_id, case, deadline)
    if basis['hashes'] != summary['input_sha256']:
        raise ValueError('Loaded native inputs differ from completed postprocess provenance')
    geometry, _ = _geometry(basis, case)
    grid = basis['grid']
    xy, inverse = np.unique(np.column_stack((grid['x_mm'], grid['y_mm'])), axis=0, return_inverse=True)
    fractions, _ = _disk_fractions(xy, basis['metadata']['h_xy_mm'])
    outputs, archives = [], {}
    for condition in summary['conditions']:
        if condition['waveform'] != 'square_3h':
            continue
        if time.monotonic() >= deadline:
            raise TimeoutError('Spatial audit deadline exceeded')
        name = condition['native_volume_archive']
        path = summary_path.parent/name
        digest = sha(path)
        if digest != summary['artifacts']['files'][name]['SHA256']:
            raise ValueError('Native scalar archive SHA differs from complete result')
        with np.load(path, allow_pickle=False) as archive:
            scalars = {name: archive[name] for name in ('maxTIS', 'fixedTIS', 'RMS')}
            weights = {region: archive['region_'+region+'_m3'] for region in ('total', 'target', 'surface_0_5', 'off_target')}
        if any(weights[region].shape != (len(grid),) for region in weights):
            raise ValueError('Grid and native scalar weights differ')
        column_weights = weights['total']*fractions[inverse]
        carrier = None if case['channels'] == 2 else condition['actual_fundamental_Hz'][0]
        coefficients = _coefficients(case['channels'], 'square_3h', carrier)
        spectra = _spectra(basis, coefficients)
        outputs.append(dict(condition_id=condition['id'], source_Vpp_per_output=1.,
            spatial=spatial_from_arrays(grid, scalars, weights, column_weights, thresholds),
            bulk_skin_J=bulk_skin_current_density(spectra, grid, geometry['gamma_S_m']),
            layer_contact_source_losses=layer_losses_from_matrices(
                {frequency: row['loss'] for frequency, row in basis['f'].items()},
                {frequency: row['source'] for frequency, row in basis['f'].items()},
                coefficients, condition['metrics'])))
        archives[name] = dict(SHA256=digest, path=str(path))
        del spectra
        gc.collect()
    for path, expected in basis['hashes'].items():
        if sha(path) != expected:
            raise ValueError('Original native input changed during read-only spatial audit')
    return dict(schema_version=1, status='computed_spatial_and_skinJ_audit', run_id=run.name,
        case_id=case_id, source_commit=pre['source_commit'], config_sha256=case['config_sha256'],
        audit_code_sha256=sha(__file__), waveform_helper_sha256=sha(REPO/'tools/task1_waveform_check.py'),
        registration_sha256=sha(registration_path), summary_sha256=sha(summary_path),
        baseline_summary_path=str(baseline_summary_path), baseline_summary_sha256=sha(baseline_summary_path),
        baseline_condition_id=baseline_square[0]['id'], native_scalar_archives=archives,
        circuit=case['circuit'], conditions=outputs, new_PDE=0,
        execution_lock='.task1-execution.lock flock plus lockf exclusive',
        native_inputs_unchanged=True, numerical_spatial_validation='not established; native samples only',
        experimental_validation=False, safety_or_physiological_validation=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline-summary', type=Path)
    args = parser.parse_args()
    run, output = args.run.resolve(), args.output.resolve()
    if not output.is_relative_to(run/'audit') or output.exists():
        raise ValueError('Use a new result under this run/audit; never overwrite evidence')
    baseline = (args.baseline_summary or run/'postprocess/baseline-square15-coarse/summary.json').resolve()
    with (REPO/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        budget_path = REPO/'runtime/task1-budget.json'
        budget = read(budget_path)
        if budget['limit_seconds'] != 6600:
            raise ValueError('Existing 6600-second budget must be preserved')
        remaining = 6600-budget['spent_seconds']
        if remaining <= 0 or (run/'summary.json').is_file() and read(run/'summary.json')['status'] == 'running':
            raise ValueError('No remaining budget or source run still marked running')
        output.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        seconds = min(180., remaining)
        cpu = min(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {cpu})
        def timeout(signum, frame):
            raise TimeoutError('Finite spatial audit exceeded registered 180s/remaining global budget')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        status = 'failed'
        try:
            result = audit(run, args.case, baseline, start+seconds)
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            if peak > 3*GIB:
                raise MemoryError('Spatial audit exceeded existing aggregate 3GiB RSS limit')
            result['resources'] = dict(wall_seconds=time.monotonic()-start, max_seconds=seconds,
                peak_process_RSS_bytes=peak, CPU_count=1, simultaneous_jobs=1)
            write_new(output, result)
            status = result['status']
            print(json.dumps(dict(status=status, case_id=args.case, output=str(output),
                                  wall_seconds=result['resources']['wall_seconds'])))
        except Exception as error:
            failure = output.with_name(output.stem+'.failure.json')
            write_new(failure, dict(status='failed', error_type=type(error).__name__, error=str(error),
                case_id=args.case, new_PDE=0, source_preserved=True,
                elapsed_seconds=time.monotonic()-start, retry_requires_new_output=True))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-start
            budget['spent_seconds'] += elapsed
            budget['runs'].append(dict(run_id=run.name, stage='spatial_and_skinJ_audit', case_id=args.case,
                seconds=elapsed, status=status, finished_utc=datetime.now(timezone.utc).isoformat()))
            temporary = budget_path.with_name('task1-budget.json.partial')
            temporary.write_text(json.dumps(budget, indent=2)+'\n')
            temporary.replace(budget_path)


if __name__ == '__main__':
    main()
