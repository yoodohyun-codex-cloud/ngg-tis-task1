"""Time-aligned measurement representations from validated saved spectra.

This is a pure postprocessor: no PDE, cache mutation, E-to-potential inference,
new stimulation waveform or physiological validation is performed.
"""
from pathlib import Path
import hashlib
import math

import numpy as np
from depth_probe_comparison import DEFAULT_POINTS
from explore_amplitude import peak_bounds
from single_vs_tis import (_coefficients, _electrical, _material_signature,
                           loaded_terminal_vpp_bounds)

SCHEMA_VERSION = 1
MAX_PLOT_SAMPLES = 16385
CONDITION_KEYS = ('output_channels', 'pad_count', 'pad_size_mm', 'h_mm', 'xy_mm',
                  'waveform', 'carrier_Hz', 'beat_Hz', 'carrier_group', 'phase_deg',
                  'thickness_nm', 'boundary_mode')
LIMITATIONS = [
    'Four measurement representations are not four new stimulation waveforms.',
    'Peak complex phasors use Re(sum(qhat_f*exp(+j2pi*f*t))); all panels share t=0.',
    'Signed instantaneous voltage, analytic-envelope amplitude and direction-maximized E modulation are distinct quantities.',
    'Fundamental analytic envelopes exclude third harmonics; total waveforms/RMS/extrema include every saved active harmonic.',
    'Plot samples are bounded display samples; their extrema never replace certified whole-period statistics.',
    'Native tip potential is not inferred from RMS, electric field or a line integral.',
    '50x/500x BNC and matching scope-factor conversions are nominal; actual settings, probe loading, noise and calibration remain unverified.',
    'Numerical extremum brackets are not mesh/probe confidence intervals, safety limits or neural activation thresholds.',
    'Matching centre20mm total E RMS does not establish waveform, spatial, neural or diaphragm-response equivalence.',
    'No existing mesh/contact/physical/physiological validation hold is cleared.']


def _sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def _properties(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            if key in result:
                raise ValueError('Duplicate basis config property')
            result[key.strip()] = value.strip()
    return result


def coherent_spectrum(frequencies, phasors):
    """Sum coincident frequencies as complex vectors before RMS or extrema."""
    frequencies, values = np.asarray(frequencies, float), np.asarray(phasors, complex)
    if values.ndim == 1:
        values = values[:, None]
    if values.ndim != 2 or len(values) != len(frequencies) or not len(values):
        raise ValueError('Expected a nonempty frequency-by-signal complex spectrum')
    if (not np.isfinite(values).all() or not np.isfinite(frequencies).all()
            or np.any(frequencies <= 0) or not np.array_equal(frequencies, np.round(frequencies))):
        raise ValueError('Finite complex phasors and positive integer Hz are required')
    unique = sorted(set(map(int, frequencies)))
    return unique, np.asarray([values[frequencies == f].sum(axis=0) for f in unique])


def signed_waveform(frequencies, phasors, times):
    frequencies, values = coherent_spectrum(frequencies, phasors)
    times = np.asarray(times, float)
    if times.ndim != 1 or not np.isfinite(times).all():
        raise ValueError('Finite one-dimensional shared time coordinates required')
    return np.real(np.exp(2j*np.pi*times[:, None]*np.asarray(frequencies))@values)


def spectral_statistics(frequencies, phasors, unit):
    """Parseval RMS and certified signed extrema over the whole common period."""
    frequencies, values = coherent_spectrum(frequencies, phasors)
    lower, upper, metadata = loaded_terminal_vpp_bounds(frequencies, values)
    plo, phi, _ = peak_bounds(frequencies, values)
    rms = np.sqrt(np.sum(abs(values)**2, axis=0)/2)
    maximum = metadata.get('sampled_max_by_output_V', [0.]*values.shape[1])
    minimum = metadata.get('sampled_min_by_output_V', [0.]*values.shape[1])
    dt = metadata.get('dt_s') or 0.
    curvature = np.sum((2*np.pi*np.asarray(frequencies)[:, None])**2*abs(values), axis=0)
    rounding = 64*np.finfo(float).eps*np.sum(abs(values), axis=0)
    error = curvature*dt*dt/8+rounding
    stats = [dict(unit=unit, RMS=float(rms[i]), absolute_peak_lower=float(plo[i]),
        absolute_peak_upper=float(phi[i]), peak_to_peak_lower=float(lower[i]), peak_to_peak_upper=float(upper[i]),
        signed_max_lower=float(maximum[i]), signed_max_upper=float(maximum[i]+error[i]),
        signed_min_lower=float(minimum[i]-error[i]), signed_min_upper=float(minimum[i]))
        for i in range(values.shape[1])]
    return stats, dict(metadata, minimal_repetition_period_s=metadata.get('period_s'),
        units_of_values=unit, interpretation='whole minimal repetition period; identical extrema/RMS on any integer-multiple shared period',
        uncertainty='deterministic numerical time-sampling brackets only; no physical/mesh/probe uncertainty included')


def fundamental_envelope(frequencies, phasors, fundamentals, times):
    """Exact positive-frequency analytic-envelope trajectory, with signed carrier."""
    frequencies, values = coherent_spectrum(frequencies, phasors)
    if values.shape[1] != 1:
        raise ValueError('One signed directional voltage spectrum is required')
    fundamentals = list(dict.fromkeys(map(int, fundamentals)))
    if not 1 <= len(fundamentals) <= 2:
        raise ValueError('One or two explicitly identified fundamental carriers required')
    if not set(fundamentals).issubset(frequencies):
        raise ValueError('Required fundamental is absent from native spectrum')
    selected = np.asarray([values[frequencies.index(f), 0] for f in fundamentals])
    time = np.asarray(times, float)
    analytic = np.exp(2j*np.pi*time[:, None]*np.asarray(fundamentals))@selected
    envelope = abs(analytic)
    amplitudes = abs(selected)
    maximum = float(amplitudes.sum())
    minimum = float(abs(amplitudes[0]-amplitudes[1])) if len(selected) == 2 else maximum
    return dict(frequencies_Hz=fundamentals, signed_voltage_V=analytic.real.tolist(),
        analytic_envelope_V=envelope.tolist(), analytic_min_V=minimum, analytic_max_V=maximum,
        modulation_width_V=maximum-minimum, single_carrier_TIS_zero=len(selected) == 1,
        definition='signed Re(sum fundamental ΔPhi exp(+jwt)); envelope abs(sum fundamental ΔPhi exp(+jwt))',
        third_harmonics_excluded=True, is_direction_maximized_field_TIS=False)


def _spectrum(frequencies, values, unit):
    return [dict(frequency_Hz=f, real=float(value.real), imag=float(value.imag),
                 peak_amplitude=float(abs(value)), phase_deg=float(np.angle(value, deg=True)), unit=unit)
            for f, value in zip(frequencies, values)]


def _signals(frequencies, values, full_time, short_time, unit):
    frequencies, values = coherent_spectrum(frequencies, values)
    stats, sampling = spectral_statistics(frequencies, values, unit)
    full, short = signed_waveform(frequencies, values, full_time), signed_waveform(frequencies, values, short_time)
    return [dict(index=i, spectrum=_spectrum(frequencies, values[:, i], unit), stats=stats[i],
        full_period_values=full[:, i].tolist(), short_window_values=short[:, i].tolist())
        for i in range(values.shape[1])], sampling


def _basis(entry, descriptor):
    row = entry['conditions']
    if entry.get('status') != 'available' or entry.get('verification', {}).get('numerical_basis_passed') is not True:
        raise ValueError('A validated available case entry is required')
    folder, config = Path(descriptor['basis_dir']), Path(descriptor['config_path'])
    expected_config = descriptor.get('config_sha256')
    if not isinstance(expected_config, str) or _sha(config) != expected_config:
        raise ValueError('Explicit basis config hash is missing or does not match')
    values = _properties(config)
    channels = int(row['output_channels'])
    if int(values['channels']) != channels or float(values['size_mm']) != row['pad_size_mm']:
        raise ValueError('Basis config output count/physical size differs from selected entry')
    if not math.isclose(float(values['h_mm']), row['h_mm'], rel_tol=1e-12):
        raise ValueError('Basis config mesh differs from selected entry')
    for index, point in enumerate(row['xy_mm']):
        if any(float(values[f'pad.{index}.{axis}_mm']) != coordinate for axis, coordinate in zip(('x', 'y'), point)):
            raise ValueError('Basis config pad coordinates differ from selected entry')
    material = _material_signature({'config_path': str(config)}, row)
    if material is None or material != entry['verification'].get('material_signature'):
        raise ValueError('Basis config material identity differs or is unverified')
    if row.get('source_R_ohm', 50) != 50:
        raise ValueError('The retained source resistance is50ohm')
    frequencies = list(map(int, values['frequencies'].split(',')))
    coefficients = _coefficients(row, frequencies)
    hashes = {'config.properties': expected_config}
    expected = entry['verification'].get('input_sha256', {})
    for frequency in frequencies:
        for kind in ('source', 'loss'):
            name = f'{kind}-{frequency}.bin'
            actual = _sha(folder/name)
            if expected.get(name) != actual:
                raise ValueError('Saved case/basis matrix hash join failed: '+name)
            hashes[name] = actual
    electrical, verification = _electrical(row, folder, frequencies)
    source = np.asarray([.5*coefficients[f] for f in frequencies])
    current = np.asarray([np.fromfile(folder/f'source-{f}.bin', dtype='<c16').reshape(channels, channels)@coefficients[f]
                          for f in frequencies])
    return frequencies, source, current, source-50*current, dict(
        electrical=verification, input_sha256=hashes, actual_metrics_at_1Vpp=electrical,
        config_identity_verified=True, matrix_identity_verified=True)


def _check_probe(probe, entry, scale):
    if probe is None:
        return None
    if probe.get('status') != 'complete' or probe.get('id') != entry['id']:
        raise ValueError('Native probe status/case identity does not match selected entry')
    if probe.get('probe_kind') != 'depth_differential_potential':
        raise ValueError('Native depth potential is required; terminal voltage is not a substitute')
    if not math.isclose(float(probe['source_Vpp_per_output']), scale, rel_tol=1e-12):
        raise ValueError('Native probe source amplitude differs from selected comparison')
    verification = probe.get('verification', {})
    if (verification.get('potential_export_available') is not True or verification.get('source_loss_verified') is not True
            or verification.get('phi_E_consistency', {}).get('passed') is not True):
        raise ValueError('Native potential/electrical/phi-E validation is missing')
    for key in CONDITION_KEYS:
        if key in probe.get('conditions', {}) and probe['conditions'][key] != entry['conditions'].get(key):
            raise ValueError('Native probe waveform/phase/geometry identity differs: '+key)
    if set(probe['axes']) != {'X', 'Y'}:
        raise ValueError('Both central X/Y depth probe axes are required')
    for axis, points in DEFAULT_POINTS.items():
        for side in ('plus_mm', 'minus_mm'):
            if not np.array_equal(probe['axes'][axis][side], points[side]):
                raise ValueError('Native probe endpoint coordinates differ from20mm/5mm definition')
        if float(probe['axes'][axis]['spacing_mm']) != 5:
            raise ValueError('Native probe spacing differs')
    return probe


def build_measurement_waveforms(tis_entry, single_entry, comparison, row_bases, *,
                                native_probes=None, max_plot_samples=4097):
    """Build four aligned representations for one fixed-TIS/same-RMS pair.

    row_bases[id] requires basis_dir/config_path/config_sha256. Source/loss
    matrix hashes must also match the selected immutable entry's verification.
    Native probes default to comparison.depth_probe; missing native data is
    explicit, while invalid supplied probe data raises instead of being replaced.
    """
    if not isinstance(max_plot_samples, int) or not 65 <= max_plot_samples <= MAX_PLOT_SAMPLES:
        raise ValueError('Bounded plot sample count must be65..16385')
    if comparison.get('status') != 'complete' or comparison.get('tis_id') != tis_entry['id'] or comparison.get('single_id') != single_entry['id']:
        raise ValueError('Selected comparison/case IDs do not join')
    if single_entry['conditions']['output_channels'] != 1 or tis_entry['conditions']['output_channels'] < 2:
        raise ValueError('A TIS reference and genuine one-output control are required')
    target = float(tis_entry['metrics_at_1Vpp']['target20_total_E_RMS_V_m'])
    single_response = float(single_entry['metrics_at_1Vpp']['target20_total_E_RMS_V_m'])
    scale = float(comparison['match']['required_single_source_Vpp'])
    if not all(math.isfinite(value) for value in (target, single_response, scale)):
        raise ValueError('Finite target/control RMS and source amplitude are required')
    if min(target, single_response, scale) <= 0 or not math.isclose(target/single_response, scale, rel_tol=1e-12):
        raise ValueError('Same20mm total RMS scale does not match the selected entries')
    if comparison['match'].get('tis_source_Vpp_per_output') != 1:
        raise ValueError('Original TIS anchor must remain1Vpp per output')
    if float(single_entry['metrics_at_1Vpp']['target20_modulation_V_m']) != 0:
        raise ValueError('A single-carrier control must have zero TIS')
    native = native_probes if native_probes is not None else comparison.get('depth_probe', {})
    probe_tis = _check_probe(native.get('tis_1Vpp'), tis_entry, 1.)
    probe_single = _check_probe(native.get('single_at_match', native.get('single_sameRMS')), single_entry, scale)
    specifications = [('tis_fixed_1Vpp', tis_entry, 1., probe_tis), ('single_same_RMS', single_entry, scale, probe_single)]
    prepared, active_frequencies = [], set()
    for role, entry, factor, probe in specifications:
        f, source, current, loaded, verification = _basis(entry, row_bases[entry['id']])
        for frequency, a, b in zip(f, source, current):
            if np.any(a) or np.any(b):
                active_frequencies.add(frequency)
        prepared.append((role, entry, factor, probe, f, source, current, loaded, verification))
    divisor = math.gcd(*sorted(active_frequencies))
    period, highest = 1./divisor, max(active_frequencies)
    full_count = min(max_plot_samples, max(65, int(math.ceil(64*highest*period))))
    full_time = np.arange(full_count)*period/full_count
    short_duration = min(.002, period)
    short_count = min(max_plot_samples, int(math.ceil(64*highest*short_duration))+1)
    short_time = np.linspace(0, short_duration, short_count)
    result = dict(schema_version=SCHEMA_VERSION, status='complete', comparison_id=comparison['id'],
        tis_id=tis_entry['id'], single_id=single_entry['id'],
        shared_time=dict(origin_s=0., common_period_s=period, common_frequency_Hz=divisor,
            full_period_time_s=full_time.tolist(), short_window_time_s=short_time.tolist(),
            short_window_duration_s=short_duration, full_period_endpoint_included=False,
            full_period_plot_samples=full_count, samples_per_highest_cycle=full_count/(highest*period),
            plot_samples_define_extrema=False,
            convention='all panels use the same original phases and positive exp(+j2pi*f*t); no per-panel rephasing'),
        roles={}, no_PDE_executed=True, new_physical_validation_performed=False,
        activation_equivalence_established=False, limitations=LIMITATIONS)
    for role, entry, factor, probe, frequencies, source, current, loaded, verification in prepared:
        source, current, loaded = source*factor, current*factor, loaded*factor
        source_outputs, source_sampling = _signals(frequencies, source, full_time, short_time, 'V')
        loaded_outputs, loaded_sampling = _signals(frequencies, loaded, full_time, short_time, 'V')
        current_outputs, current_sampling = _signals(frequencies, current, full_time, short_time, 'A')
        data = dict(id=entry['id'], conditions=entry['conditions'], source_Vpp_per_output=factor,
            source=dict(definition='open-circuit HighZ Thevenin command before50ohm; .5Vpeak times complex drive coefficients',
                        outputs=source_outputs, extrema_sampling=source_sampling),
            loaded=dict(definition='signal metal relative to common ideal returnGND0V; source voltage minus50ohm times actual branch current',
                        outputs=loaded_outputs, current_outputs=current_outputs,
                        voltage_extrema_sampling=loaded_sampling, current_extrema_sampling=current_sampling),
            native_probe={'status': 'unavailable', 'axes': {}},
            field_direction_max_TIS=dict(value_V_m=factor*entry['metrics_at_1Vpp']['target20_modulation_V_m'],
                definition='stored max_n 2min(abs(n dot E_f0),abs(n dot E_f1)); centre20mm fundamental-vector direction search',
                direction_samples=2074, quantity='electric field envelope width, not native voltage envelope',
                single_output_zero=entry['conditions']['output_channels'] == 1,
                is_neural_threshold=False, third_harmonics_excluded=True), verification=verification)
        if probe is None:
            result['status'] = 'partial_native_unavailable'
        else:
            native_axes = {}
            row = entry['conditions']
            fundamentals = [int(row['carrier_Hz'])]+([int(row['carrier_Hz'])+int(row['beat_Hz'])] if row['output_channels'] > 1 else [])
            for axis, original in probe['axes'].items():
                f = [item['frequency_Hz'] for item in original['spectrum']]
                phi = [complex(item['delta_potential_re_V'], item['delta_potential_im_V']) for item in original['spectrum']]
                if not set(f).issubset(frequencies):
                    raise ValueError('Native potential spectrum frequency differs from selected source basis')
                signals, sampling = _signals(f, phi, full_time, short_time, 'V')
                signal = signals[0]
                for saved, actual in (('RMS_V', 'RMS'), ('Vpp_lower_V', 'peak_to_peak_lower'), ('Vpp_upper_V', 'peak_to_peak_upper')):
                    if not math.isclose(float(original[saved]), signal['stats'][actual], rel_tol=1e-9, abs_tol=1e-14):
                        raise ValueError('Native saved spectrum/statistic identity differs: '+saved)
                native_axes[axis] = dict(signal, plus_mm=original['plus_mm'], minus_mm=original['minus_mm'], spacing_mm=5.,
                    voltage_definition='phi_plus-minus_phi_minus', extrema_sampling=sampling,
                    fundamental_full_period=fundamental_envelope(f, phi, fundamentals, full_time),
                    fundamental_short_window=fundamental_envelope(f, phi, fundamentals, short_time),
                    nominal_attenuation=[dict(hardware_A=a, matching_scope_K=a,
                        BNC_RMS_V=signal['stats']['RMS']/a,
                        BNC_Vpp_lower_V=signal['stats']['peak_to_peak_lower']/a,
                        BNC_Vpp_upper_V=signal['stats']['peak_to_peak_upper']/a,
                        matched_display_Vpp_lower_V=signal['stats']['peak_to_peak_lower'],
                        matched_display_Vpp_upper_V=signal['stats']['peak_to_peak_upper'],
                        actual_setting_confirmed=False, measurement_success_guaranteed=False) for a in (50, 500)])
            data['native_probe'] = dict(status='complete', axes=native_axes, verification=probe['verification'],
                source_normalization=probe.get('source_normalization'),
                definition='native unloaded20mm X/Y5mm differential tissue potential, not metal terminal voltage')
        result['roles'][role] = data
    return result
