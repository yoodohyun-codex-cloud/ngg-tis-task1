"""Read-only, layer-aware analysis of native complex tissue potential.

This module never runs a solver, infers potential from E, or writes a cache or
GUI pointer.  Callers must supply the actual cell-centred grid, z faces, layer
planes, per-frequency complex admittivity and original peak basis arrays.
The original ExploreBasis/ValidationBasis exporters are deliberately unchanged.

Within a layer, interpolation is linear in each coordinate.  Across one flat
horizontal interface, the z interpolant uses the two half-cell impedances:
phi(z)=phi(lo)+(phi(hi)-phi(lo))*integral_lo^z(dz/gamma)/
integral_lo^hi(dz/gamma).  This is a local finite-volume face reconstruction,
not proof of continuum, mesh, loading, or physiological convergence.
"""
from dataclasses import asdict, dataclass
from functools import reduce
import math
import re

import numpy as np


SCHEMA_VERSION = 1
PHASOR_CONVENTION = 'Re(sum(Vhat_f*exp(+j*2*pi*f*t))); Vhat is peak complex amplitude'
FIELD_RECONSTRUCTION = 'finite_volume_half_face_flux'
DEFAULT_LAYERS = (
    dict(id=0, name='sc', z_min_mm=0., z_max_mm=.1),
    dict(id=1, name='dermis', z_min_mm=.1, z_max_mm=5.1),
    dict(id=2, name='fat', z_min_mm=5.1, z_max_mm=10.1),
    dict(id=3, name='muscle', z_min_mm=10.1, z_max_mm=25.1))


class ProbeDataMissing(ValueError):
    """Required original data or metadata are unavailable; do not substitute."""


@dataclass(frozen=True)
class SamplingLimits:
    """Explicit postprocessing limits only; no PDE/resource setting is changed."""
    samples_per_highest_cycle: int = 128
    max_statistics_samples: int = 262144
    max_period_s: float = 1.
    plot_duration_s: float = .002
    max_plot_samples: int = 4097

    def validate(self):
        for key in ('samples_per_highest_cycle', 'max_statistics_samples', 'max_plot_samples'):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 2:
                raise ValueError('Invalid postprocessing sampling limit: ' + key)
        if self.samples_per_highest_cycle < 16:
            raise ValueError('At least 16 samples per highest-frequency cycle required')
        if not math.isfinite(self.max_period_s) or self.max_period_s <= 0:
            raise ValueError('Invalid maximum common period')
        if not math.isfinite(self.plot_duration_s) or not 0 < self.plot_duration_s <= .002:
            raise ValueError('Illustrative plot must be positive and at most 2 ms')


def probe_layout(depths_mm=(5., 10., 15., 20.), plus_pitch_mm=5., tip_gap_mm=5.):
    """Return explicit 4-depth x 5-centre x 2-axis endpoints, all in mm.

    The plus-array centre pitch and differential tip separation are independent.
    +x/+y are local phantom axes, without an anatomical front/back assignment.
    """
    depths = np.asarray(depths_mm, float)
    if depths.shape != (4,) or not np.isfinite(depths).all() or np.any(depths <= 0):
        raise ValueError('Four finite positive surface-referenced depths required')
    if len(set(depths.tolist())) != 4:
        raise ValueError('Probe depths must be distinct')
    pitch, gap = float(plus_pitch_mm), float(tip_gap_mm)
    if not math.isfinite(pitch) or not math.isfinite(gap) or min(pitch, gap) <= 0:
        raise ValueError('Centre pitch and tip gap must be separate positive lengths')
    centres = [('centre', 0., 0.), ('x_plus', pitch, 0.), ('x_minus', -pitch, 0.),
               ('y_plus', 0., pitch), ('y_minus', 0., -pitch)]
    result = []
    for depth in depths:
        for position, x, y in centres:
            for axis, offset in [('X', (gap / 2, 0.)), ('Y', (0., gap / 2))]:
                result.append(dict(id=f'd{depth:g}-{position}-{axis}',
                    depth_from_skin_surface_mm=float(depth), position=position,
                    axis=axis, centre_mm=[x, y, float(depth)],
                    plus_mm=[x + offset[0], y + offset[1], float(depth)],
                    minus_mm=[x - offset[0], y - offset[1], float(depth)],
                    plus_centre_pitch_mm=pitch, tip_gap_mm=gap,
                    voltage_definition='phi(plus_mm)-phi(minus_mm)'))
    return result


class LayeredPotentialSampler:
    """Cell-centred cylindrical structured grid; preserve cylindrical holes.

    ``geometry`` must explicitly identify skin z=0, +z depth, layer bounds,
    every actual z face and the original field reconstruction.  No faces,
    conductivities, tissue labels or missing cells are guessed from an old run.
    """
    def __init__(self, grid, geometry):
        self.grid = np.asarray(grid)
        names = set(self.grid.dtype.names or ())
        if not {'x_mm', 'y_mm', 'z_mm', 'layer'} <= names:
            raise ProbeDataMissing('Actual grid requires x_mm,y_mm,z_mm,layer')
        if self.grid.ndim != 1 or not len(self.grid):
            raise ValueError('Actual grid must be a nonempty one-dimensional cell list')
        if not all(np.isfinite(self.grid[key]).all() for key in ('x_mm', 'y_mm', 'z_mm', 'layer')):
            raise ValueError('Nonfinite grid coordinate or tissue label')
        coords = geometry.get('coordinate_system', {})
        if (coords.get('unit') != 'mm' or coords.get('surface_z_mm') != 0 or
                coords.get('depth_axis') != '+z'):
            raise ProbeDataMissing('Require explicit skin surface z=0 mm and repository +z depth')
        if geometry.get('field_reconstruction') != FIELD_RECONSTRUCTION:
            raise ProbeDataMissing('Original finite-volume field reconstruction must be explicit')
        self.radius = float(geometry.get('radius_mm', math.nan))
        if not math.isfinite(self.radius) or self.radius <= 0:
            raise ProbeDataMissing('Explicit positive cylinder radius required')
        self.layers = list(geometry.get('layers', ()))
        if not self.layers:
            raise ProbeDataMissing('Actual layer planes are required')
        ids = set()
        for index, layer in enumerate(self.layers):
            if not {'id', 'name', 'z_min_mm', 'z_max_mm'} <= layer.keys():
                raise ProbeDataMissing('Incomplete layer plane metadata')
            start, end = float(layer['z_min_mm']), float(layer['z_max_mm'])
            label = layer['id']
            if (isinstance(label, bool) or not isinstance(label, int) or label in ids or
                    not layer['name'] or not math.isfinite(start + end) or start >= end):
                raise ValueError('Invalid or duplicate physical layer')
            if index == 0 and start != 0:
                raise ValueError('Layer stack must start at the skin surface')
            if index and not math.isclose(start, self.layers[index-1]['z_max_mm'], abs_tol=1e-10, rel_tol=0):
                raise ValueError('Layer planes contain a gap or overlap')
            ids.add(label)
        self.layer_by_id = {layer['id']: layer for layer in self.layers}
        if not np.array_equal(self.grid['layer'], np.round(self.grid['layer'])):
            raise ValueError('Noninteger cell tissue label')
        if not set(map(int, np.unique(self.grid['layer']))) <= ids:
            raise ValueError('Unknown tissue label in actual grid')
        self.axes = [np.unique(self.grid[key]) for key in ('x_mm', 'y_mm', 'z_mm')]
        if any(len(axis) < 2 for axis in self.axes):
            raise ValueError('Insufficient grid extent for complex interpolation')
        self.faces = np.asarray(geometry.get('z_faces_mm', ()), float)
        if self.faces.shape != (len(self.axes[2]) + 1,) or not np.isfinite(self.faces).all():
            raise ProbeDataMissing('Every actual z face is required, including SC refinement')
        if np.any(np.diff(self.faces) <= 0):
            raise ValueError('Actual z faces must be strictly increasing')
        if (not math.isclose(self.faces[0], 0, abs_tol=1e-10) or
                not math.isclose(self.faces[-1], self.layers[-1]['z_max_mm'], abs_tol=1e-10)):
            raise ValueError('Actual z faces and physical layer stack disagree')
        if not np.allclose((self.faces[:-1] + self.faces[1:]) / 2,
                           self.axes[2], atol=1e-9, rtol=0):
            raise ValueError('Actual z centres do not match supplied finite-volume faces')
        self.ix, self.iy, self.iz = [np.searchsorted(axis, self.grid[key]) for axis, key in
                                    zip(self.axes, ('x_mm', 'y_mm', 'z_mm'))]
        self.lookup = np.full(tuple(len(a) for a in self.axes[::-1]), -1, np.int64)
        linear = np.ravel_multi_index((self.iz, self.iy, self.ix), self.lookup.shape)
        if len(np.unique(linear)) != len(self.grid):
            raise ValueError('Duplicate potential grid coordinates')
        self.lookup[self.iz, self.iy, self.ix] = np.arange(len(self.grid))
        self.z_layers = []
        for k, z in enumerate(self.axes[2]):
            selected = self.grid['layer'][self.iz == k]
            if len(np.unique(selected)) != 1:
                raise ValueError('A horizontal plane has conflicting tissue labels')
            label = int(selected[0])
            layer = self.layer_by_id[label]
            if not (layer['z_min_mm']-1e-10 <= self.faces[k] < z < self.faces[k+1] <= layer['z_max_mm']+1e-10):
                raise ValueError('Cell tissue label or cell faces cross a physical interface')
            self.z_layers.append(label)
        for layer in self.layers:
            for plane in (layer['z_min_mm'], layer['z_max_mm']):
                if not np.any(np.isclose(self.faces, plane, atol=1e-10, rtol=0)):
                    raise ValueError('A physical interface is absent from actual cell faces')

    def validate_gamma(self, gamma):
        try:
            values = {label: complex(gamma[label] if label in gamma else gamma[str(label)])
                      for label in self.layer_by_id}
        except (KeyError, TypeError) as error:
            raise ProbeDataMissing('Per-layer complex admittivity is required at every frequency') from error
        if any(not np.isfinite(value) or value.real <= 0 or value.imag < 0 for value in values.values()):
            raise ValueError('Admittivity must be finite and passive under exp(+jwt)')
        return values

    def tissue_at(self, depth_mm):
        """Point tissue, distinct from tissues touched by an interpolation stencil."""
        touched = [layer for layer in self.layers
                   if layer['z_min_mm'] <= depth_mm <= layer['z_max_mm']]
        if not touched:
            raise ProbeDataMissing('Point lies outside physical tissue stack')
        return dict(layer_ids=[layer['id'] for layer in touched],
                    layer_names=[layer['name'] for layer in touched],
                    is_interface=len(touched) > 1)

    def _impedance_length(self, z0, z1, gamma):
        """Area-specific series impedance across actual planes, in ohm m²."""
        if not z0 < z1:
            raise ValueError('Unordered normal-flux reconstruction interval')
        total, covered = 0j, 0.
        for layer in self.layers:
            length = max(0., min(z1, layer['z_max_mm']) - max(z0, layer['z_min_mm']))
            total += length / 1000 / gamma[layer['id']]
            covered += length
        if not math.isclose(covered, z1-z0, abs_tol=1e-10, rel_tol=0) or total == 0:
            raise ValueError('Normal-flux interval leaves declared tissue stack')
        return total

    def stencil(self, point_mm, gamma):
        point = np.asarray(point_mm, float)
        gamma = self.validate_gamma(gamma)
        if point.shape != (3,) or not np.isfinite(point).all():
            raise ValueError('Finite XYZ endpoint required')
        if point[0]**2 + point[1]**2 >= self.radius**2:
            raise ProbeDataMissing('Probe endpoint outside supported cylinder interior')
        brackets = []
        for axis, value in zip(self.axes, point):
            if not axis[0] <= value <= axis[-1]:
                raise ProbeDataMissing('Probe endpoint requires extrapolation beyond cell centres')
            exact = np.flatnonzero(np.isclose(axis, value, rtol=0, atol=1e-10))
            if len(exact):
                brackets.append([(int(exact[0]), 1.+0j)])
            else:
                hi = int(np.searchsorted(axis, value))
                lo = hi - 1
                fraction = (value-axis[lo])/(axis[hi]-axis[lo])
                if len(brackets) == 2 and self.z_layers[lo] != self.z_layers[hi]:
                    # Only the actual adjacent flat interface is supported.
                    interface = self.faces[hi]
                    if not axis[lo] < interface < axis[hi]:
                        raise ValueError('Invalid interface between adjacent cell centres')
                    fraction = self._impedance_length(axis[lo], value, gamma) / self._impedance_length(axis[lo], axis[hi], gamma)
                brackets.append([(lo, 1-fraction), (hi, fraction)])
        indices, weights = [], []
        for k, wz in brackets[2]:
            for j, wy in brackets[1]:
                for i, wx in brackets[0]:
                    cell = int(self.lookup[k, j, i])
                    if cell < 0:
                        raise ProbeDataMissing('Missing cylindrical cell at endpoint stencil')
                    indices.append(cell)
                    weights.append(wx*wy*wz)
        if not np.isclose(sum(weights), 1, atol=1e-12, rtol=0):
            raise ValueError('Complex interpolation weights do not preserve constant potential')
        touched = sorted({int(self.grid['layer'][cell]) for cell in indices})
        return dict(indices=np.asarray(indices, int), weights=np.asarray(weights, complex),
                    layer_ids=touched, crosses_interface=len(touched) > 1,
                    method='bilinear XY; linear z within tissue; series-impedance z across planar interface')

    @staticmethod
    def interpolate(potential, stencil):
        return potential[:, stencil['indices']] @ stencil['weights']

    def phi_e_consistency(self, potential, field, nodes, gamma,
                          relative_tolerance=2e-10, absolute_tolerance_V_m=1e-10):
        """Reproduce Net.field's half-face flux average in every sampled layer.

        Interior adjacent-interface cells use each cell's own gamma.  Top/bottom
        contacts, outer cylinder boundaries or missing neighbour cells are held;
        an unmodelled boundary is never replaced with nearest-cell extrapolation.
        """
        gamma = self.validate_gamma(gamma)
        potential, field = np.asarray(potential), np.asarray(field)
        if potential.ndim != 2 or potential.shape[1] != len(self.grid) or field.shape != (*potential.shape, 3):
            raise ValueError('Native potential/E dimensions must be [channel,cell] and [channel,cell,xyz]')
        if not np.isfinite(potential).all() or not np.isfinite(field).all():
            raise ValueError('Nonfinite original native potential or complex E')
        checked, unsupported, failed, layers, interface_cells = [], [], [], {}, 0
        max_error = 0.
        for node in sorted(set(map(int, nodes))):
            if not 0 <= node < len(self.grid):
                raise ValueError('Invalid verification cell index')
            i, j, k = self.ix[node], self.iy[node], self.iz[node]
            if min(i, j, k) == 0 or i == self.lookup.shape[2]-1 or j == self.lookup.shape[1]-1 or k == self.lookup.shape[0]-1:
                unsupported.append(node)
                continue
            neighbours = [(int(self.lookup[k, j, i-1]), int(self.lookup[k, j, i+1])),
                          (int(self.lookup[k, j-1, i]), int(self.lookup[k, j+1, i])),
                          (int(self.lookup[k-1, j, i]), int(self.lookup[k+1, j, i]))]
            if any(n < 0 for pair in neighbours for n in pair):
                unsupported.append(node)
                continue
            label = int(self.grid['layer'][node])
            reconstructed = []
            adjacent_interface = False
            for axis, key, (before, after) in zip(range(3), ('x_mm', 'y_mm', 'z_mm'), neighbours):
                a, b, c = self.grid[key][before], self.grid[key][node], self.grid[key][after]
                if axis == 2:
                    left, right = self._impedance_length(a, b, gamma), self._impedance_length(b, c, gamma)
                    adjacent_interface |= int(self.grid['layer'][before]) != label or int(self.grid['layer'][after]) != label
                else:
                    if int(self.grid['layer'][before]) != label or int(self.grid['layer'][after]) != label:
                        raise ValueError('Nonplanar tissue boundary is unsupported')
                    left, right = (b-a)/1000/gamma[label], (c-b)/1000/gamma[label]
                if left == 0 or right == 0:
                    raise ValueError('Degenerate cell spacing')
                reconstructed.append(.5*((potential[:, before]-potential[:, node])/left +
                                          (potential[:, node]-potential[:, after])/right)/gamma[label])
            predicted = np.stack(reconstructed, axis=1)
            error = abs(predicted-field[:, node])
            if not np.all(error <= absolute_tolerance_V_m + relative_tolerance*abs(field[:, node])):
                failed.append(node)
            max_error = max(max_error, float(error.max()))
            checked.append(node)
            layers[str(label)] = layers.get(str(label), 0) + 1
            interface_cells += int(adjacent_interface)
        return dict(passed=bool(checked) and not unsupported and not failed,
                    checked_cell_count=len(checked), checked_cell_indices=checked,
                    unsupported_cell_indices=unsupported, failed_cell_indices=failed,
                    checked_cells_by_layer=layers, interface_adjacent_cell_count=interface_cells,
                    max_absolute_error_V_m=max_error if checked else None,
                    relative_tolerance=relative_tolerance, absolute_tolerance_V_m=absolute_tolerance_V_m,
                    method=FIELD_RECONSTRUCTION,
                    meaning='algebraic native-phi/stored-E agreement only; not continuum, mesh, physiology or hardware validation')


def _frequency(value):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value <= 0:
        raise ProbeDataMissing('Exact positive integer-Hz frequencies required; no frequency rounding')
    return int(value)


def coherent_spectrum(frequencies, phasors):
    """Sum all channel/contribution phasors at the same actual frequency first."""
    values = np.asarray(phasors, complex)
    if values.ndim < 1 or len(frequencies) != len(values) or not np.isfinite(values).all():
        raise ValueError('Invalid peak complex spectrum')
    combined = {}
    for frequency, value in zip(frequencies, values):
        f = _frequency(frequency)
        combined[f] = combined.get(f, np.zeros_like(value)) + value
    ordered = sorted(combined)
    return ordered, np.asarray([combined[f] for f in ordered])


def waveform_statistics(frequencies, phasors, fundamental_frequencies_Hz, sampling=SamplingLimits()):
    """Full common-period max-minus-min bounds and exact spectral RMS.

    Uniform samples give the Vpp lower bound.  D2*dt²/4 bounds the two missed
    extrema combined.  This never substitutes 2*max(abs(v)) or 2*sqrt(2)*RMS.
    """
    sampling.validate()
    frequencies, values = coherent_spectrum(frequencies, phasors)
    if values.ndim != 1 or not frequencies:
        raise ValueError('One nonempty scalar differential spectrum required')
    divisor = reduce(math.gcd, frequencies)
    period = 1. / divisor
    count = max(16, math.ceil(sampling.samples_per_highest_cycle*max(frequencies)/divisor))
    if period > sampling.max_period_s or count > sampling.max_statistics_samples:
        raise ProbeDataMissing('Exact common-period reconstruction exceeds declared postprocessing limits')
    time = np.arange(count)*period/count
    wave = np.zeros(count)
    for f, value in zip(frequencies, values):
        wave += np.real(value*np.exp(2j*np.pi*f*time))
    derivative2 = sum((2*np.pi*f)**2*abs(value) for f, value in zip(frequencies, values))
    amplitude_sum = float(sum(abs(values)))
    rounding = 64*np.finfo(float).eps*max(amplitude_sum, np.finfo(float).tiny)
    extremum_error = derivative2*(period/count)**2/8 + rounding
    minimum, maximum = float(wave.min()), float(wave.max())
    vpp = maximum-minimum
    upper = max(vpp, min(2*amplitude_sum+rounding, vpp+2*extremum_error))
    fundamentals = sorted({_frequency(f) for f in fundamental_frequencies_Hz})
    if not fundamentals or not set(fundamentals) <= set(frequencies) or len(fundamentals) > 2:
        raise ValueError('Declare one or two actual fundamental carrier frequencies in the spectrum')
    fundamental_values = [values[frequencies.index(f)] for f in fundamentals]
    amplitudes = list(map(float, abs(np.asarray(fundamental_values))))
    envelope_max = sum(amplitudes)
    envelope_min = abs(amplitudes[0]-amplitudes[1]) if len(amplitudes) == 2 else amplitudes[0]
    envelope_range = envelope_max-envelope_min
    plot_count = math.ceil(sampling.samples_per_highest_cycle*max(frequencies)*sampling.plot_duration_s)+1
    if plot_count > sampling.max_plot_samples:
        raise ProbeDataMissing('Illustrative waveform exceeds declared plot sample limit')
    plot_time = np.linspace(0., sampling.plot_duration_s, plot_count)
    plot_wave = np.real(sum(v*np.exp(2j*np.pi*f*plot_time) for f, v in zip(frequencies, values)))
    plot_envelope = abs(sum(v*np.exp(2j*np.pi*f*plot_time) for f, v in zip(fundamentals, fundamental_values)))
    return dict(RMS_V=math.sqrt(float(np.sum(abs(values)**2)/2)),
        Vpp_lower_V=vpp, Vpp_upper_V=float(upper),
        sampled_min_V=minimum, sampled_max_V=maximum,
        extrema_interpolation_error_bound_V=float(extremum_error),
        spectrum=[dict(frequency_Hz=f, real_V=float(v.real), imaginary_V=float(v.imag),
                       peak_amplitude_V=float(abs(v)), phase_deg=float(np.angle(v, deg=True)))
                  for f, v in zip(frequencies, values)],
        common_period=dict(period_s=period, samples=count, dt_s=period/count,
                           definition='exact frequency common period; sampled max-minus-min lower and second-derivative upper bound'),
        fundamental_fixed_axis_envelope=dict(frequencies_Hz=fundamentals,
            definition='absolute analytic sum of only the declared fundamental differential-voltage phasors; not direction-max electric-field TIS',
            minimum_V=envelope_min, maximum_V=envelope_max, variation_range_V=envelope_range,
            modulation_index=envelope_range/(envelope_max+envelope_min) if envelope_max else None,
            is_activation_or_safety_metric=False),
        time_plot=dict(time_ms=(plot_time*1000).tolist(), voltage_V=plot_wave.tolist(),
                       fundamental_envelope_V=plot_envelope.tolist(),
                       duration_s=sampling.plot_duration_s, t0_s=0.,
                       statistics_use_full_common_period=True),
        nominal_instrument=[dict(probe='ETA5001', scope='KEYSIGHT DSOX1202A',
            attenuation=attenuation, scope_probe_factor=attenuation,
            BNC_RMS_V=math.sqrt(float(np.sum(abs(values)**2)/2))/attenuation,
            BNC_Vpp_lower_V=vpp/attenuation, BNC_Vpp_upper_V=float(upper)/attenuation,
            displayed_RMS_V=math.sqrt(float(np.sum(abs(values)**2)/2)),
            displayed_Vpp_lower_V=vpp, displayed_Vpp_upper_V=float(upper),
            scope_input='1 Mohm, DC; nominal matched probe factor',
            is_actual_switch_setting=False, unloaded_prediction=True,
            loading_noise_calibration_frequency_response_validated=False)
            for attenuation in (50, 500)])


def evaluate_layered_probe(grid, potentials, fields, geometry, drive_coefficients, *,
                           provenance, fundamental_frequencies_Hz,
                           plus_pitch_mm=5., tip_gap_mm=5., depths_mm=(5., 10., 15., 20.),
                           sampling=SamplingLimits()):
    """Analyse 40 probe waveforms without invoking or modifying a producer.

    potentials: {integer_Hz: complex[channel,cell]}, same original grid order.
    fields: {integer_Hz: complex[channel,cell,xyz]}, native matching export.
    drive_coefficients: {integer_Hz: complex[channel]}, including waveform,
      actual carrier assignment, harmonic phase and sine/cosine convention.
    geometry['gamma_S_m']: {integer_Hz: {layer_id: complex_admittivity_S_m}}.
    Original peak basis normalization must be explicit: 0.5 V peak/50 ohm,
    source Vpp=1, positive exponent.  A coefficient is dimensionless, not an
    inferred potential.  Input file hashes are the caller's responsibility.

    Errors in an individual spatial stencil remain visible in its row; missing
    arrays/metadata raise ProbeDataMissing so a registry can record a held case.
    """
    layout = probe_layout(depths_mm, plus_pitch_mm, tip_gap_mm)
    sampling.validate()
    required = ('source_run_id', 'source_condition_id', 'source_candidate_id',
                'input_sha256', 'code_sha256', 'result_sha256')
    if any(not isinstance(provenance.get(key), str) or not provenance[key] for key in required):
        raise ValueError('Source run/condition/candidate and input/code/result provenance required')
    if any(not re.fullmatch('[0-9a-fA-F]{64}', provenance[key]) for key in required[-3:]):
        raise ValueError('Input/code/result provenance must use SHA-256')
    normalization = geometry.get('basis_normalization', {})
    if normalization != dict(source_peak_V=.5, source_Vpp=1., source_resistance_ohm=50., phasor_exponent='+jomega_t'):
        raise ProbeDataMissing('Explicit unchanged 0.5 Vpeak/1 Vpp/50 ohm/+jwt native basis required')
    sampler = LayeredPotentialSampler(grid, geometry)
    frequencies = sorted(_frequency(f) for f in drive_coefficients)
    if not frequencies or set(frequencies) - set(potentials) or set(frequencies) - set(fields):
        raise ProbeDataMissing('Every driven frequency requires native complex potential and matching E')
    gamma_by_frequency = geometry.get('gamma_S_m', {})
    stencils, failures = {}, {}
    checks, spectra = {}, {row['id']: [] for row in layout}
    for frequency in frequencies:
        if frequency not in gamma_by_frequency:
            raise ProbeDataMissing('Frequency-specific layer admittivity metadata missing')
        gamma = sampler.validate_gamma(gamma_by_frequency[frequency])
        potential, field = np.asarray(potentials[frequency]), np.asarray(fields[frequency])
        coefficients = np.asarray(drive_coefficients[frequency], complex)
        if (potential.ndim != 2 or potential.shape[1] != len(grid) or
                field.shape != (*potential.shape, 3) or coefficients.shape != (potential.shape[0],)):
            raise ValueError('Inconsistent native grid, channels, E or drive coefficient dimensions')
        if not np.isfinite(coefficients).all():
            raise ValueError('Nonfinite actual waveform/phase coefficient')
        nodes = set()
        for row in layout:
            try:
                pair = {end: sampler.stencil(row[end+'_mm'], gamma) for end in ('plus', 'minus')}
                stencils[frequency, row['id']] = pair
                for stencil in pair.values():
                    nodes.update(stencil['indices'].tolist())
            except ProbeDataMissing as error:
                failures[row['id']] = dict(status='held_data_missing', reason=str(error))
        check = sampler.phi_e_consistency(potential, field, nodes, gamma)
        checks[str(frequency)] = check
        bad = set(check['failed_cell_indices'])
        unsupported = set(check['unsupported_cell_indices'])
        for row in layout:
            pair = stencils.get((frequency, row['id']))
            if pair is None:
                continue
            cells = set(pair['plus']['indices']) | set(pair['minus']['indices'])
            if cells & bad:
                failures[row['id']] = dict(status='validation_failed', reason='Layer-aware native phi/stored E algebraic gate failed')
            elif cells & unsupported:
                failures.setdefault(row['id'], dict(status='held_data_missing', reason='Native phi/E boundary neighbour stencil unavailable'))
            delta = sampler.interpolate(potential, pair['plus']) - sampler.interpolate(potential, pair['minus'])
            spectra[row['id']].append(np.dot(coefficients, delta))
    rows = []
    for definition in layout:
        row = dict(definition)
        row['tissue_at_probe_depth'] = sampler.tissue_at(row['depth_from_skin_surface_mm'])
        row['interpolation'] = [dict(frequency_Hz=f, **{end: {
            'layer_ids': stencil['layer_ids'], 'crosses_interface': stencil['crosses_interface'],
            'method': stencil['method'], 'cell_indices': stencil['indices'].tolist()}
            for end, stencil in stencils[f, row['id']].items()})
            for f in frequencies if (f, row['id']) in stencils]
        if row['id'] in failures:
            row.update(failures[row['id']])
        else:
            try:
                row.update(waveform_statistics(frequencies, spectra[row['id']], fundamental_frequencies_Hz, sampling), status='complete')
            except ProbeDataMissing as error:
                row.update(status='held_data_missing', reason=str(error))
        rows.append(row)
    complete = [row for row in rows if row['status'] == 'complete']
    limits = None
    if complete:
        limits = [min(row['sampled_min_V']-row['extrema_interpolation_error_bound_V'] for row in complete),
                  max(row['sampled_max_V']+row['extrema_interpolation_error_bound_V'] for row in complete)]
    counts = {status: sum(row['status'] == status for row in rows)
              for status in ('complete', 'held_data_missing', 'validation_failed')}
    return dict(schema_version=SCHEMA_VERSION,
        status='complete' if len(complete) == 40 else 'validation_failed' if counts['validation_failed'] else 'held_data_missing',
        provenance=dict(provenance), expected_waveform_count=40, counts=counts,
        coordinate_system=dict(unit='mm', surface_z_mm=0., depth_axis='+z',
            x_y_axes='local phantom coordinates; no anatomical anterior/posterior assignment',
            displayed_depth='positive distance from skin surface, not from SC bottom'),
        measurement_grid=dict(depths_mm=list(map(float, depths_mm)), plus_centre_pitch_mm=float(plus_pitch_mm),
                              tip_gap_mm=float(tip_gap_mm), centres_per_depth=5, directions_per_centre=2),
        source_basis_normalization=dict(normalization), phasor_convention=PHASOR_CONVENTION,
        drive_coefficients=[dict(frequency_Hz=f,
            real_by_basis_channel=np.asarray(drive_coefficients[f]).real.tolist(),
            imaginary_by_basis_channel=np.asarray(drive_coefficients[f]).imag.tolist(),
            definition='dimensionless coefficients applied coherently to unchanged 0.5 Vpeak basis')
            for f in frequencies],
        numerical_checks=dict(per_frequency=checks, all_passed=all(c['passed'] for c in checks.values())),
        postprocessing_sampling_limits=asdict(sampling),
        shared_plot_axes=dict(time_ms=[0., sampling.plot_duration_s*1000], voltage_V=limits,
                              same_time_origin_s=0., required_for_all_depth_position_panels=True),
        measurements=rows, unloaded_prediction=True, new_PDE_executed=False,
        limitations=['40 finite probe directions do not locate the whole-volume maximum or prove physiological selectivity.',
            'Spatial reconstruction is cell-centred and interface-aware; sampled phi-E agreement does not prove mesh convergence.',
            'No tip contact, probe R/C loading, calibration, actual attenuation switch, noise or detectability is validated.',
            'Fixed-axis fundamental tip-voltage envelope is not the original direction-max electric-field TIS objective.',
            'Waveform RMS matching is not equal neural recruitment, direct muscle excitation, force or safety.'])
