"""Fixed physical-region diagnostics from complete stored complex E bases.

No PDE, compilation, source-input update, worker operation, or objective change.
Regional/axis metrics use 2074 sampled directions consistently.  The centre's
2074/8218/32794-direction sensitivity is a separate, uncertified diagnostic.
For bounded BLAS cost launch with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import os

import numpy as np
from explore_tis import WAVES, atomic, design_frequencies, directions


REGIONAL_FIBONACCI_COUNT = 2048
CENTER_FIBONACCI_COUNTS = (2048, 8192, 32768)
DIRECTION_GATE = .001
QUADRATURE_SUBDIVISIONS = 64
NUMERICAL_LIMITS = dict(max_residual=2e-7, max_power_error=2e-7,
                        max_current_error=2e-6)


class CacheUnavailable(RuntimeError):
    pass


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def region_probes(inner_radius_mm, outer_radius_mm, step_mm, subdivisions=64):
    """Fixed square cells with deterministic circle/annulus overlap weights.

    The probe is the centroid of inside subcell centres; if that centroid is
    outside a nonconvex annulus, use its nearest inside subcell centre explicitly.
    No empty/outside probe is used and no physical area is counted twice.
    """
    if not (0 <= inner_radius_mm < outer_radius_mm and step_mm > 0
            and isinstance(subdivisions, int) and subdivisions > 0):
        raise ValueError('Invalid physical region or quadrature')
    count = round(2*outer_radius_mm/step_mm)
    if not math.isclose(count*step_mm, 2*outer_radius_mm, abs_tol=1e-10):
        raise ValueError('Fixed sample cells must tile the region bounding square')
    centres = -outer_radius_mm+(np.arange(count)+.5)*step_mm
    offsets = ((np.arange(subdivisions)+.5)/subdivisions-.5)*step_mm
    oy, ox = np.meshgrid(offsets, offsets, indexing='ij')
    ox, oy = ox.ravel(), oy.ravel()
    result = []
    for y in centres:
        for x in centres:
            sx, sy = x+ox, y+oy
            radius2 = sx*sx+sy*sy
            inside = (radius2 < outer_radius_mm**2) & (radius2 >= inner_radius_mm**2)
            hits = int(inside.sum())
            if not hits:
                continue
            px, py = float(sx[inside].mean()), float(sy[inside].mean())
            kind = 'overlap_subcell_centroid'
            if not inner_radius_mm**2 <= px*px+py*py < outer_radius_mm**2:
                nearest = np.argmin((sx[inside]-px)**2+(sy[inside]-py)**2)
                px, py = float(sx[inside][nearest]), float(sy[inside][nearest])
                kind = 'nearest_inside_subcell_to_centroid'
            result.append(dict(cell_center_xy_mm=[float(x), float(y)],
                               probe_xy_mm=[px, py],
                               area_mm2=hits*(step_mm/subdivisions)**2,
                               inside_subcell_count=hits, probe_method=kind))
    return result


def weighted_summary(values, weights):
    """Quantile = first sorted value reaching the requested cumulative area."""
    values, weights = np.asarray(values, float), np.asarray(weights, float)
    if values.ndim != 1 or values.shape != weights.shape or not len(values):
        raise ValueError('One positive area per finite physical probe is required')
    if not np.isfinite(values).all() or not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError('Incomplete/nonfinite probes must not be silently averaged')
    order = np.argsort(values, kind='stable')
    sorted_values, cumulative = values[order], np.cumsum(weights[order])
    result = {'min': float(values.min()),
              'area_weighted_mean': float(values@weights/weights.sum())}
    for name, fraction in (('p05', .05), ('p25', .25), ('p50', .5), ('p95', .95)):
        index = min(int(np.searchsorted(cumulative, fraction*cumulative[-1], side='left')),
                    len(values)-1)
        result[name] = float(sorted_values[index])
    return result


class ComplexSampler:
    """Full source-grid interpolation; fields stay read-only memory mapped."""
    def __init__(self, grid, fields, row):
        self.grid, self.fields, self.row = grid, fields, row
        self.axes = [np.unique(grid[key]) for key in ('x_mm', 'y_mm', 'z_mm')]
        if any(len(axis) < 2 for axis in self.axes):
            raise ValueError('At least two physical cell centres per axis are needed')
        xs, ys, zs = self.axes
        self.lookup = np.full((len(zs), len(ys), len(xs)), -1, dtype=np.int64)
        iz, iy, ix = [np.searchsorted(axis, grid[key]) for axis, key in
                      zip((zs, ys, xs), ('z_mm', 'y_mm', 'x_mm'))]
        linear_indices = np.ravel_multi_index((iz, iy, ix), self.lookup.shape)
        if len(np.unique(linear_indices)) != len(grid):
            raise ValueError('Duplicate physical grid coordinates')
        self.lookup[iz, iy, ix] = np.arange(len(grid))
        channels = int(row['output_channels'])
        group, phase = np.asarray(row['carrier_group']), np.deg2rad(row['phase_deg'])
        if group.shape != (channels,) or phase.shape != group.shape or not np.isfinite(phase).all():
            raise ValueError('Invalid output group/phase arrays')
        if not np.isin(group, (0, 1)).all():
            raise ValueError('Invalid carrier group')
        f0 = int(row.get('carrier_Hz', 2000))
        f1 = f0+int(row.get('beat_Hz', 10))
        self.fundamentals = (f0, f1)
        a1, a3 = WAVES[row['waveform']]
        self.coefficients = {}
        for f, field in fields.items():
            if field.shape != (channels, len(grid), 3, 2):
                raise ValueError('Invalid complex field shape')
            harmonic = 1 if f in (f0, f1) else 3
            carrier = 0 if f in (f0, 3*f0) else 1
            self.coefficients[f] = (-1j*(group == carrier)*np.exp(1j*harmonic*phase)
                                    *(a1 if harmonic == 1 else a3))
        if not all(f in fields for f in self.fundamentals):
            raise ValueError('Both fundamental basis frequencies must be available')

    def sample(self, points_mm):
        points = np.asarray(points_mm, float)
        if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
            raise ValueError('Expected finite xyz physical coordinates')
        brackets, fractions = [], []
        valid = points[:, 0]**2+points[:, 1]**2 < 25**2
        for axis, values in zip(self.axes, points.T):
            valid &= (values >= axis[0]-1e-12) & (values <= axis[-1]+1e-12)
            lo = np.clip(np.searchsorted(axis, values, side='right')-1, 0, len(axis)-2)
            fraction = (values-axis[lo])/(axis[lo+1]-axis[lo])
            brackets.append(lo)
            fractions.append(np.clip(fraction, 0, 1))
        result = {f: np.zeros((len(points), 3), complex) for f in self.fields}
        for dz in (0, 1):
            for dy in (0, 1):
                for dx in (0, 1):
                    weight = np.ones(len(points))
                    for offset, t in zip((dx, dy, dz), fractions):
                        weight *= t if offset else 1-t
                    indices = self.lookup[brackets[2]+dz, brackets[1]+dy, brackets[0]+dx]
                    valid &= (weight <= 1e-14) | (indices >= 0)
                    safe = np.maximum(indices, 0)
                    for f, field in self.fields.items():
                        for channel in np.flatnonzero(self.coefficients[f]):
                            values = field[channel, safe]
                            complex_values = values[..., 0]+1j*values[..., 1]
                            result[f] += (self.coefficients[f][channel]*weight[:, None]*complex_values)
        for field in result.values():
            field[~valid] = np.nan
        return result, valid


def field_metrics(spectra, fundamentals, fibonacci_count=2048):
    """Same-frequency fields are already summed; interpolate before calling."""
    rms = np.sqrt(sum(np.sum(abs(field)**2, axis=1)/2 for field in spectra.values()))
    a, b = spectra[fundamentals[0]], spectra[fundamentals[1]]
    ti = np.zeros(len(rms))
    dirs = directions(fibonacci_count)
    # All-zero carrier stays exactly zero, including single-output controls.
    if np.any(abs(a) > 0) and np.any(abs(b) > 0):
        for start in range(0, len(rms), 64):
            aa, bb = a[start:start+64], b[start:start+64]
            ti[start:start+64] = 2*np.minimum(abs(aa@dirs.T), abs(bb@dirs.T)).max(axis=1)
    invalid = ~np.isfinite(rms)
    ti[invalid] = np.nan
    if np.any(ti[~invalid] > 2*rms[~invalid]+1e-10):
        raise ValueError('Directional modulation exceeds physical RMS bound')
    return {'total_E_RMS_V_m': rms, 'fundamental_modulation_V_m': ti}


def load_sampler(folder, row):
    folder = Path(folder)
    frequencies = design_frequencies(row)
    files = ['BASIS_COMPLETE', 'validation.json', 'grid.csv']+[f'field-{f}.bin' for f in frequencies]
    if not all((folder/name).is_file() for name in files):
        raise CacheUnavailable('Complete full complex E cache is unavailable: '+str(folder))
    validation = json.loads((folder/'validation.json').read_text())
    for key, limit in NUMERICAL_LIMITS.items():
        value = float(validation[key])
        if not math.isfinite(value) or value < 0 or value > limit:
            raise ValueError(f'Existing basis validation failed: {key}={value}')
    grid = np.genfromtxt(folder/'grid.csv', delimiter=',', names=True)
    if len(grid) > 800000 or len(grid) != validation['cells']:
        raise ValueError('Missing/mismatched full grid or registered 800000-cell limit exceeded')
    if not all(np.isfinite(grid[key]).all() for key in ('x_mm', 'y_mm', 'z_mm')):
        raise ValueError('Non-finite physical grid coordinates')
    if validation['channels'] != row['output_channels']:
        raise ValueError('Basis output count mismatch')
    fields, hashes = {}, {name: sha256(folder/name) for name in ('grid.csv', 'validation.json')}
    shape = (row['output_channels'], len(grid), 3, 2)
    for f in frequencies:
        name = f'field-{f}.bin'
        if (folder/name).stat().st_size != math.prod(shape)*8:
            raise ValueError('Complex E binary size mismatch: '+name)
        values = np.memmap(folder/name, dtype='<f8', mode='r', shape=shape)
        flat = values.reshape(-1)
        digest = hashlib.sha256()
        for start in range(0, len(flat), 1024*1024):
            block = flat[start:start+1024*1024]
            if not np.isfinite(block).all():
                raise ValueError('Non-finite full complex E basis: '+name)
            digest.update(block.view(np.uint8))
        hashes[name] = digest.hexdigest()
        fields[f] = values
    return ComplexSampler(grid, fields, row), {'validation': validation,
                                               'basis_dir': str(folder.resolve()),
                                               'input_sha256': hashes}


def _json_values(values):
    return [float(v) if math.isfinite(v) else None for v in values]


def _ratio(numerator, denominator):
    return numerator/denominator if (numerator is not None and denominator is not None
                                     and math.isfinite(numerator) and math.isfinite(denominator)
                                     and denominator != 0) else None


def _relative_change(old, new):
    if old == 0:
        return 0.0 if new == 0 else None
    return abs(new-old)/abs(old)


def analyze_sampler(sampler, row, regional_count=REGIONAL_FIBONACCI_COUNT,
                    center_counts=CENTER_FIBONACCI_COUNTS):
    regions = {}
    definitions = [('target20_disk', 0, 5, .5, 20.),
                   ('superficial_disk', 0, 5, .5, .025),
                   ('offtarget20_annulus', 10, 20, 1., 20.)]
    for name, inner, outer, step, depth in definitions:
        probes = region_probes(inner, outer, step, QUADRATURE_SUBDIVISIONS)
        points = [p['probe_xy_mm']+[depth] for p in probes]
        spectra, valid = sampler.sample(points)
        metrics = field_metrics(spectra, sampler.fundamentals, regional_count)
        weights = np.array([p['area_mm2'] for p in probes])
        complete = bool(valid.all())
        regions[name] = {'depth_mm': depth, 'inner_radius_mm': inner,
                         'outer_radius_mm': outer, 'sample_step_mm': step,
                         'overlap_quadrature': '64x64 deterministic subcell centres',
                         'analytic_area_mm2': math.pi*(outer**2-inner**2),
                         'quadrature_area_mm2': float(weights.sum()),
                         'valid_area_mm2': float(weights[valid].sum()),
                         'status': 'complete' if complete else 'incomplete_no_missing_fill',
                         'probes': probes, 'valid': valid.tolist(),
                         'values': {key: _json_values(v) for key, v in metrics.items()},
                         'statistics': {key: weighted_summary(v, weights)
                                        for key, v in metrics.items()} if complete else None}
    zs = sorted(set(sampler.axes[2].tolist()+[20., .025]))
    spectra, valid = sampler.sample([[0, 0, z] for z in zs])
    axis_metrics = field_metrics(spectra, sampler.fundamentals, regional_count)
    axis = [{'z_mm': z, 'valid': bool(valid[i]),
             'is_solver_z_center': bool(np.any(np.isclose(sampler.axes[2], z, rtol=0, atol=1e-12))),
             **{key: float(values[i]) if valid[i] else None for key, values in axis_metrics.items()}}
            for i, z in enumerate(zs)]
    center_index, near_index = zs.index(20.), zs.index(.025)
    center_spectra = {f: field[center_index:center_index+1] for f, field in spectra.items()}
    resolution = []
    for count in center_counts:
        metric = field_metrics(center_spectra, sampler.fundamentals, count)
        resolution.append({'fibonacci_count': count, 'actual_direction_count': count+26,
                           **{key: float(value[0]) if valid[center_index] else None
                              for key, value in metric.items()}})
    change = None
    if len(resolution) >= 2 and valid[center_index]:
        change = _relative_change(resolution[-2]['fundamental_modulation_V_m'],
                                  resolution[-1]['fundamental_modulation_V_m'])
    ratios = {}
    for metric in axis_metrics:
        means = {name: region['statistics'][metric]['area_weighted_mean']
                 if region['statistics'] is not None else None for name, region in regions.items()}
        ratios[metric] = {
            'center20_over_fixed_superficial_center': _ratio(axis[center_index][metric], axis[near_index][metric]),
            'target_mean_over_superficial_mean': _ratio(means['target20_disk'], means['superficial_disk']),
            'target_mean_over_offtarget_annulus_mean': _ratio(means['target20_disk'], means['offtarget20_annulus'])}
    reproduction = {}
    for stored, metric in (('target20_total_E_RMS_V_m', 'total_E_RMS_V_m'),
                            ('target20_modulation_V_m', 'fundamental_modulation_V_m')):
        if stored in row and valid[center_index]:
            got, expected = axis[center_index][metric], float(row[stored])
            reproduction[stored] = {'saved': expected, 'reconstructed_2074': got,
                                    'matches_relative_2e_7': math.isclose(got, expected, rel_tol=2e-7, abs_tol=1e-12)}
            if not reproduction[stored]['matches_relative_2e_7']:
                raise ValueError('Stored target metric reconstruction failed: '+stored)
    return {'status': 'complete' if all(r['status'] == 'complete' for r in regions.values())
                                      and bool(valid.all()) else 'incomplete_no_missing_fill',
            'regions': regions, 'axis_profile': axis,
            'first_solver_cell_center_depth_mm': float(sampler.axes[2][0]),
            'fixed_superficial_depth_mm': .025,
            'center20': axis[center_index], 'fixed_superficial_center': axis[near_index],
            'ratios_consistent_direction_count': regional_count+26, 'ratios': ratios,
            'source_metric_reproduction': reproduction,
            'center_direction_resolution': {
                'values': resolution, 'final_adjacent_relative_change': change,
                'relative_gate': DIRECTION_GATE,
                'passed': change is not None and change <= DIRECTION_GATE,
                'interpretation': 'sampled resolution sensitivity; no rigorous global-direction certificate'},
            'regional_direction_estimate': {'fibonacci_count': regional_count,
                                             'actual_direction_count': regional_count+26,
                                             'resolution_certified': False}}


def analyze_case(row, basis_dir):
    sampler, evidence = load_sampler(basis_dir, row)
    result = analyze_sampler(sampler, row)
    result.update(id=row['id'], conditions=row, evidence=evidence)
    return result


def build_report(source_run, case_ids, mesh_summary=None, waveforms=None):
    source_run = Path(source_run).resolve()
    jobs = []
    for identifier in case_ids:
        task, index = identifier.rsplit('-', 1)
        case = json.loads((source_run/'cases'/f'{task}.json').read_text())
        row = dict(case['candidates'][int(index)], id=identifier)
        row.setdefault('target20_modulation_V_m', row.get('target20_TI10_V_m', 0))
        jobs.append((row, source_run/'bases'/row['basis_id']))
    if mesh_summary is not None:
        summary = json.loads(Path(mesh_summary).read_text())
        for case in summary['cases']:
            if case.get('status') != 'complete':
                continue
            for metric in case['metrics']:
                if waveforms is None or metric['waveform'] in waveforms:
                    row = dict(metric, id=case['id']+':'+metric['waveform'],
                               mesh_case_id=case['id'], mesh_axis=case['axis'],
                               mesh_id=case['mesh_id'], geometry=case['geometry'],
                               h_xy_mm=case['h_xy_mm'], sc_cells=case['sc_cells'])
                    jobs.append((row, Path(case['basis_dir'])))
    results = []
    for row, folder in jobs:
        try:
            results.append(analyze_case(row, folder))
        except CacheUnavailable as error:
            results.append({'id': row['id'], 'status': 'unavailable', 'reason': str(error)})
        except (ValueError, KeyError) as error:
            results.append({'id': row['id'], 'status': 'validation_failed', 'reason': str(error)})
    return {'schema_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'complete' if results and all(r['status'] == 'complete' for r in results)
                      else 'needs_attention',
            'source_run': str(source_run), 'mesh_summary': str(mesh_summary) if mesh_summary else None,
            'no_PDE_executed': True, 'objective_promoted': False,
            'purpose': 'fixed physical phantom concentration diagnostics; no anatomical mask or activation inference',
            'regional_direction_count': 2074,
            'weighted_quantile_definition': 'first sorted sampled value whose cumulative overlap area reaches q',
            'cases': results,
            'limitations': ['2074-direction regional/axis values are sampled estimates, not directional certificates.',
                            'Centre finest-direction result is separate; ratios consistently use2074 directions.',
                            'Area weights use64x64 deterministic subcells; no analytical area or full-field maximum is claimed.',
                            'Probe minimum is a sampled minimum, not a continuous-region lower bound.',
                            'Point/ROI ratios do not establish spatial concentration success, neural activation or a new objective.',
                            'Unavailable full bases or unsupported probes are disclosed and never filled or solved.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', required=True, type=Path)
    parser.add_argument('--case', nargs='+', default=[])
    parser.add_argument('--mesh-summary', type=Path)
    parser.add_argument('--waveform', nargs='+', choices=tuple(WAVES))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not args.case and args.mesh_summary is None:
        parser.error('Provide --case and/or --mesh-summary')
    output = args.output.resolve()
    if output.is_relative_to(args.source_run.resolve()):
        parser.error('Diagnostic output must be separate from the active source run')
    report = build_report(args.source_run, args.case, args.mesh_summary, args.waveform)
    report['process_blas_thread_environment'] = {name: os.environ.get(name)
        for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS')}
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic(output, report)
    print(json.dumps({'status': report['status'], 'cases': len(report['cases']),
                      'output': str(output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
