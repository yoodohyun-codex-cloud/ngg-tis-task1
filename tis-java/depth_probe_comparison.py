"""Ideal differential probe predictions from newly exported tissue potential.

No extracellular potential is inferred from E, RMS, a line integral or a GUI.
All functions are read-only and do not invoke a solver or write cache files.
"""
from pathlib import Path
import hashlib
import math

import numpy as np
from explore_amplitude import peak_bounds
from single_vs_tis import (_coefficients, _electrical, _frequencies,
                           CacheUnavailable, loaded_terminal_vpp_bounds)


SCHEMA_VERSION = 1
DEFAULT_POINTS = {
    'X': {'plus_mm': [2.5, 0., 20.], 'minus_mm': [-2.5, 0., 20.]},
    'Y': {'plus_mm': [0., 2.5, 20.], 'minus_mm': [0., -2.5, 20.]}}
HARDWARE_ASSUMPTIONS = {
    'measurement_kind': 'tissue depth differential probe tip-input voltage',
    'connection': 'plus and minus endpoints specified per axis; not signal metal-to-return terminals',
    'points_user_confirmed': 'central20mm depth,5mm spacing alongX andY',
    'ideal_high_impedance_no_additional_loading': True,
    'probe_model': None, 'input_R_ohm': None, 'input_C_F': None,
    'bandwidth_Hz': None, 'probe_attenuation': None,
    'scope_input_ohm': None, 'scope_probe_factor': None,
    'scope_display_prediction': 'unavailable until actual probe and scope transfer/settings are known',
    'tissue_sensor_size_and_perturbation_modelled': False}


def _sha256(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


class PotentialSampler:
    """Structured-grid stencils, retaining original cylindrical missing cells."""
    def __init__(self, grid):
        self.grid = grid
        if not all(np.isfinite(grid[k]).all() for k in ('x_mm', 'y_mm', 'z_mm')):
            raise ValueError('Nonfinite physical grid')
        self.axes = [np.unique(grid[k]) for k in ('x_mm', 'y_mm', 'z_mm')]
        if any(len(axis) < 2 for axis in self.axes):
            raise ValueError('Insufficient grid for complex trilinear interpolation')
        x, y, z = self.axes
        self.lookup = np.full((len(z), len(y), len(x)), -1, dtype=np.int64)
        self.ix, self.iy, self.iz = [np.searchsorted(axis, grid[key]) for axis, key in
                                    zip(self.axes, ('x_mm', 'y_mm', 'z_mm'))]
        linear = np.ravel_multi_index((self.iz, self.iy, self.ix), self.lookup.shape)
        if len(np.unique(linear)) != len(grid):
            raise ValueError('Duplicate potential grid coordinates')
        self.lookup[self.iz, self.iy, self.ix] = np.arange(len(grid))

    def stencil(self, point_mm):
        point = np.asarray(point_mm, float)
        if point.shape != (3,) or not np.isfinite(point).all() or point[0]**2+point[1]**2 >= 625:
            raise ValueError('Probe endpoint outside supported cylindrical phantom')
        low, fraction = [], []
        for axis, value in zip(self.axes, point):
            if not axis[0] <= value <= axis[-1]:
                raise ValueError('Probe interpolation would extrapolate beyond cell centres')
            lo = min(max(int(np.searchsorted(axis, value, side='right'))-1, 0), len(axis)-2)
            low.append(lo)
            fraction.append((value-axis[lo])/(axis[lo+1]-axis[lo]))
        indices, weights = [], []
        for dz in (0, 1):
            for dy in (0, 1):
                for dx in (0, 1):
                    weight = math.prod(t if side else 1-t for t, side in zip(fraction, (dx, dy, dz)))
                    if weight <= 1e-14:
                        continue
                    index = self.lookup[low[2]+dz, low[1]+dy, low[0]+dx]
                    if index < 0:
                        raise ValueError('Missing source cell at probe interpolation stencil')
                    indices.append(int(index))
                    weights.append(float(weight))
        if not math.isclose(sum(weights), 1, abs_tol=1e-12):
            raise ValueError('Probe interpolation weights do not sum to one')
        return np.array(indices, int), np.array(weights)

    @staticmethod
    def interpolate(potential, stencil):
        indices, weights = stencil
        return potential[:, indices]@weights


def phi_e_consistency(sampler, potential, field, nodes,
                       relative_tolerance=2e-10, absolute_tolerance_V_m=1e-10):
    """Match Net.field's half-face-gradient average in homogeneous muscle.

    In nonuniform z this is the average of two face gradients, not a generic
    three-point polynomial derivative.  Only full interior muscle stencils pass.
    """
    grid, lookup = sampler.grid, sampler.lookup
    checked, missing = [], []
    for node in sorted(set(map(int, nodes))):
        i, j, k = sampler.ix[node], sampler.iy[node], sampler.iz[node]
        if ('layer' not in grid.dtype.names or int(grid['layer'][node]) != 3 or
                i == 0 or j == 0 or k == 0 or i == lookup.shape[2]-1 or
                j == lookup.shape[1]-1 or k == lookup.shape[0]-1):
            missing.append(node)
            continue
        neighbours = [(lookup[k, j, i-1], lookup[k, j, i+1]),
                      (lookup[k, j-1, i], lookup[k, j+1, i]),
                      (lookup[k-1, j, i], lookup[k+1, j, i])]
        flat = np.array(neighbours).ravel()
        if np.any(flat < 0) or np.any(grid['layer'][flat] != 3):
            missing.append(node)
            continue
        checked.append((node, neighbours))
    differences, reference = [], []
    component_checks = True
    for node, neighbours in checked:
        gradients = []
        for key, (before, after) in zip(('x_mm', 'y_mm', 'z_mm'), neighbours):
            left = (grid[key][node]-grid[key][before])/1000
            right = (grid[key][after]-grid[key][node])/1000
            if left <= 0 or right <= 0:
                raise ValueError('Unordered physical neighbour coordinates')
            gradients.append(.5*((potential[:, before]-potential[:, node])/left
                                  +(potential[:, node]-potential[:, after])/right))
        reconstructed = np.stack(gradients, axis=1)
        stored = field[:, node]
        error = abs(reconstructed-stored)
        component_checks &= bool(np.all(error <= absolute_tolerance_V_m+relative_tolerance*abs(stored)))
        differences.append(error.ravel())
        reference.append(abs(stored).ravel())
    max_error = float(np.concatenate(differences).max()) if differences else None
    max_field = float(np.concatenate(reference).max()) if reference else None
    relative = max_error/max_field if max_field else (0. if max_error == 0 else None)
    return {'passed': bool(checked) and not missing and component_checks,
            'checked_cell_count': len(checked), 'unsupported_cell_indices': missing,
            'checked_cell_indices': [node for node, _ in checked],
            'max_absolute_error_V_m': max_error,
            'max_error_relative_to_max_stored_component': relative,
            'relative_tolerance': relative_tolerance,
            'absolute_tolerance_V_m': absolute_tolerance_V_m,
            'rule': 'each complex component abs(error)<=1e-10V/m+2e-10*abs(storedE)',
            'stencil': 'homogeneous muscle interior; average of negative potential differences across left/right faces',
            'normalization': 'unscaled0.5Vpeak basis responses before waveform coefficients',
            'is_new_PDE_validation_or_physiology': False}


def _time_plot(frequencies, phasors, duration_s):
    if duration_s is None:
        return None
    duration = float(duration_s)
    if not math.isfinite(duration) or not 0 < duration <= .002:
        raise ValueError('Optional short plot is bounded to at most2ms')
    count = int(math.ceil(64*max(frequencies)*duration))+1
    time = np.linspace(0, duration, count)
    voltage = np.real(sum(value*np.exp(2j*np.pi*f*time) for f, value in zip(frequencies, phasors)))
    return {'duration_s': duration, 'time_ms': (time*1000).tolist(),
            'voltage_V': voltage.tolist(),
            'Vpp_from_full_period_not_plot': True,
            'interpretation': 'short illustrative window; its extrema do not define reported full-periodVpp'}


def evaluate_depth_probe(basis_dir, row, points=None, amplitude=1., plot_duration_s=.002):
    """Return X/Y tissue Δphi measurements; never infer missing potential.

    A complete dedicated export is required: potential-f.bin is peak complex
    little-endian[C,N], in grid.csv order and common-return0V gauge.  `amplitude`
    scales the unchanged source1Vpp basis (e.g.1.488314... for matched single).
    """
    base = {'schema_version': SCHEMA_VERSION, 'id': row['id'],
            'probe_kind': 'depth_differential_potential',
            'source_Vpp_per_output': float(amplitude), 'conditions': dict(row),
            'potential_reference': 'exported tissue potential relative to common ideal returnGND=0V',
            'source_normalization': 'each basis is0.5Vpeak through50ohm; coefficient phases useexp(+jwt)',
            'hardware_assumptions': dict(HARDWARE_ASSUMPTIONS), 'axes': {},
            'limitations': ['This is an ideal unloaded tissue differential tip-input voltage, not a calibrated scope display.',
                'The5mm baseline is a spatial voltage difference. Its RMS is not the centre total vector E RMS.',
                'Full-periodVpp is computed separately from the2ms illustration; twice absolutepeak is not substituted.',
                'Finite potential cancellation may approach solver error; no arbitrary zeroing or biological threshold is applied.',
                'No potential is reconstructed from old E/RMS caches; absent nativepotential exports remain unavailable.']}
    try:
        scale = float(amplitude)
        if not math.isfinite(scale) or scale < 0:
            raise ValueError('Source amplitude must be finite and nonnegative')
        folder = Path(basis_dir)
        frequencies = tuple(row.get('basis_frequencies_Hz') or _frequencies(row))
        coefficients = _coefficients(row, frequencies)
        for f in frequencies:
            if not (folder/f'potential-{f}.bin').is_file():
                raise CacheUnavailable('Native tissue potential export is missing: '+str(folder/f'potential-{f}.bin'))
        electrical, electrical_verification = _electrical(row, folder, frequencies)
        grid = np.genfromtxt(folder/'grid.csv', delimiter=',', names=True)
        if len(grid) != electrical_verification['validation'].get('cells', len(grid)):
            raise ValueError('Potential/grid cell count mismatch')
        sampler = PotentialSampler(grid)
        selected_points = points if points is not None else DEFAULT_POINTS
        stencils, endpoints, nodes = {}, {}, set()
        for name, definition in selected_points.items():
            plus, minus = definition['plus_mm'], definition['minus_mm']
            distance = float(np.linalg.norm(np.asarray(plus, float)-np.asarray(minus, float)))
            if distance <= 0:
                raise ValueError('Differential probe endpoints must be distinct')
            stencils[name] = {'plus': sampler.stencil(plus), 'minus': sampler.stencil(minus)}
            endpoints[name] = {'plus_mm': list(map(float, plus)), 'minus_mm': list(map(float, minus)),
                               'spacing_mm': distance}
            for stencil in stencils[name].values():
                nodes.update(stencil[0].tolist())
        # Centre is included independently of endpoint stencils.
        nodes.update(sampler.stencil([0, 0, 20])[0].tolist())
        spectra = {name: [] for name in selected_points}
        check_results, hashes = {}, {'grid.csv': _sha256(folder/'grid.csv')}
        channels, cells = int(row['output_channels']), len(grid)
        for f in frequencies:
            phi_path, field_path = folder/f'potential-{f}.bin', folder/f'field-{f}.bin'
            if phi_path.stat().st_size != channels*cells*16 or field_path.stat().st_size != channels*cells*3*16:
                raise ValueError('Potential or complex E file shape mismatch')
            potential = np.memmap(phi_path, dtype='<c16', mode='r', shape=(channels, cells))
            field = np.memmap(field_path, dtype='<c16', mode='r', shape=(channels, cells, 3))
            for name, values in ((phi_path.name, potential), (field_path.name, field)):
                digest = hashlib.sha256()
                flat = values.reshape(-1)
                for start in range(0, len(flat), 512*1024):
                    block = flat[start:start+512*1024]
                    if not np.isfinite(block).all():
                        raise ValueError('Nonfinite native potential/E cache')
                    digest.update(block.view(np.uint8))
                hashes[name] = digest.hexdigest()
            check_results[str(f)] = phi_e_consistency(sampler, potential, field, nodes)
            for name, endpoint_stencils in stencils.items():
                plus = sampler.interpolate(potential, endpoint_stencils['plus'])
                minus = sampler.interpolate(potential, endpoint_stencils['minus'])
                spectra[name].append(scale*np.dot(coefficients[f], plus-minus))
        all_checks = all(check['passed'] for check in check_results.values())
        base['verification'] = {'potential_export_available': True,
                                'source_loss_verified': True,
                                'electrical': electrical_verification,
                                'phi_E_consistency': {'passed': all_checks, 'per_frequency': check_results},
                                'input_sha256': hashes,
                                'new_PDE_executed_by_postprocessor': False}
        if not all_checks:
            base.update(status='validation_failed', reason='Native potential and storedE stencil consistency failed')
            return base
        for name, values in spectra.items():
            phasors = np.array(values)
            rms = math.sqrt(float(np.sum(abs(phasors)**2)/2))
            lo, hi, period = loaded_terminal_vpp_bounds(frequencies, phasors[:, None])
            peaklo, peakhi, _ = peak_bounds(frequencies, phasors[:, None])
            base['axes'][name] = dict(endpoints[name],
                voltage_definition='phi_plus-minus_phi_minus', RMS_V=rms,
                absolute_peak_lower_V=float(peaklo[0]), absolute_peak_upper_V=float(peakhi[0]),
                Vpp_lower_V=float(lo[0]), Vpp_upper_V=float(hi[0]),
                spectrum=[{'frequency_Hz': int(f), 'delta_potential_re_V': float(value.real),
                           'delta_potential_im_V': float(value.imag), 'peak_amplitude_V': float(abs(value)),
                           'phase_deg': float(np.angle(value, deg=True))}
                          for f, value in zip(frequencies, phasors)],
                full_period=period, time_plot=_time_plot(frequencies, phasors, plot_duration_s))
        base['center20_total_E_RMS_V_m'] = scale*row['target20_total_E_RMS_V_m'] if 'target20_total_E_RMS_V_m' in row else None
        base.update(status='complete', frequencies_Hz=list(frequencies))
        return base
    except (CacheUnavailable, FileNotFoundError) as error:
        base.update(status='unavailable', reason=str(error))
    except (ValueError, KeyError) as error:
        base.update(status='validation_failed', reason=str(error))
    return base
