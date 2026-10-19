"""Engineering amplitude extrapolation of existing validated linear AC cases.

Literature treatment-current numbers are comparisons, not activation thresholds.
No solver, material change, CV safety window, or device compliance is implied.
"""
from pathlib import Path
import hashlib
import json
import math
import re

import numpy as np

from explore_tis import WAVES, atomic, design_frequencies


SCHEMA_VERSION = 1
_LIMITS = {'max_residual': 2e-7, 'max_power_error': 2e-7,
           'max_current_error': 2e-6}
_LINEAR = ('target20_total_E_RMS_V_m', 'target20_modulation_V_m',
           'surface_J_RMS_max_A_m2', 'contact_voltage_RMS_max_V',
           'charge_excursion_upper_mC_cm2')
_QUADRATIC = ('SC_power_W', 'contact_power_W', 'skin_power_W',
              'source_power_W', 'tissue_contact_power_W')
_CURRENT_ARRAYS = ('source_current_RMS_by_output_mA',
                   'source_current_peak_lower_by_output_mA',
                   'source_current_peak_upper_by_output_mA')
_CURRENT_MAXIMA = ('max_source_current_RMS_mA',
                   'max_source_current_peak_lower_mA',
                   'max_source_current_peak_upper_mA')


def peak_bounds(frequencies, currents):
    """Certified periodic waveform peak brackets for peak complex phasors.

    `currents` is frequency by output.  Lower bounds are sampled absolute maxima.
    The second derivative bound supplies an upper bound between sample points;
    the triangle inequality gives an independent, sometimes tighter upper bound.
    """
    frequencies = np.asarray(frequencies, dtype=float)
    currents = np.asarray(currents, dtype=np.complex128)
    if currents.ndim != 2 or len(frequencies) != len(currents):
        raise ValueError('Expected frequency-by-output current phasors')
    if not np.isfinite(currents).all() or not np.isfinite(frequencies).all():
        raise ValueError('Non-finite current spectrum')
    if np.any(frequencies <= 0) or not np.array_equal(frequencies, np.round(frequencies)):
        raise ValueError('Periodic peak reconstruction requires positive integer Hz')
    active = np.any(abs(currents) > 0, axis=1)
    frequencies = frequencies[active].astype(np.int64)
    currents = currents[active]
    if not len(frequencies):
        zero = np.zeros(currents.shape[1])
        return zero, zero, {'period_s': None, 'samples': 0, 'dt_s': None}
    divisor = math.gcd(*frequencies.tolist())
    count = int(math.ceil(64 * int(frequencies.max()) / divisor))
    period = 1.0 / divisor
    dt = period / count
    time = np.arange(count) * dt
    waveform = np.zeros((count, currents.shape[1]))
    for frequency, current in zip(frequencies, currents):
        waveform += np.real(np.exp(2j * np.pi * frequency * time[:, None]) * current)
    lower = np.max(abs(waveform), axis=0)
    triangle = np.sum(abs(currents), axis=0)
    derivative2 = np.sum((2*np.pi*frequencies[:, None])**2 * abs(currents), axis=0)
    # Floating-point reconstruction may exceed the triangle bound by roundoff.
    rounding = 32 * np.finfo(float).eps * np.maximum(triangle, np.finfo(float).tiny)
    upper = np.maximum(lower, np.minimum(triangle + rounding,
                                       lower + derivative2 * dt**2 / 8 + rounding))
    return lower, upper, {'period_s': period, 'samples': count, 'dt_s': dt,
                          'peak_bound_method': 'sampled lower; min(sum(abs(I_f)), '
                                               'lower+sum((2*pi*f)^2*abs(I_f))*dt^2/8) upper'}


def _validate(validation):
    for name, limit in _LIMITS.items():
        value = float(validation[name])
        if not math.isfinite(value) or value < 0 or value > limit:
            raise ValueError(f'Invalid amplitude basis validation: {name}={value}')


def _base(run, row):
    folder = run / 'bases' / row['basis_id']
    frequencies = design_frequencies(row)
    files = ['BASIS_COMPLETE', 'validation.json'] + [
        f'{kind}-{f}.bin' for f in frequencies for kind in ('source', 'loss')]
    if not all((folder / name).is_file() for name in files):
        return None
    _validate(json.loads((folder / 'validation.json').read_text()))
    normalized = dict(row)
    normalized['target20_modulation_V_m'] = row.get('target20_modulation_V_m',
                                                    row.get('target20_TI10_V_m', 0))
    stable_keys = ('basis_id', 'h_mm', 'output_channels', 'waveform', 'carrier_group',
                   'phase_deg', 'carrier_Hz', 'beat_Hz') + _LINEAR + _QUADRATIC + (
                       'max_source_current_RMS_mA',)
    identity = {key: normalized[key] for key in stable_keys if key in normalized}
    hasher = hashlib.sha256(json.dumps(identity, sort_keys=True,
                                       allow_nan=False).encode())
    binary = {}
    for name in files[1:]:
        binary[name] = (folder / name).read_bytes()
        hasher.update(name.encode())
        hasher.update(binary[name])
    fingerprint = hasher.hexdigest()
    identifier = str(row.get('id', row['basis_id']))
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', identifier):
        raise ValueError('Invalid amplitude cache case identifier')
    cache_path = run / 'amplitude-cache' / (identifier + '.json')
    if cache_path.is_file():
        cache = json.loads(cache_path.read_text())
        if cache.get('schema_version') == SCHEMA_VERSION and cache.get('fingerprint') == fingerprint:
            return cache['base']
    channels = int(row['output_channels'])
    if not 1 <= channels <= 4:
        raise ValueError('At most four output channels')
    group = np.asarray(row['carrier_group'])
    phase = np.deg2rad(row['phase_deg'])
    if group.shape != (channels,) or phase.shape != group.shape or not np.isfinite(phase).all():
        raise ValueError('Invalid output group/phase arrays')
    if not np.isin(group, (0, 1)).all():
        raise ValueError('Invalid carrier groups')
    carrier0 = int(row.get('carrier_Hz', 2000))
    carrier1 = carrier0 + int(row.get('beat_Hz', 10))
    fundamental, third = WAVES[row['waveform']]
    current_spectrum = []
    source_power = 0.0
    for f in frequencies:
        harmonic = 1 if f in (carrier0, carrier1) else 3
        carrier = 0 if f in (carrier0, 3*carrier0) else 1
        coefficient = (-1j * (group == carrier) * np.exp(1j*harmonic*phase) *
                       (fundamental if harmonic == 1 else third))
        source = np.frombuffer(binary[f'source-{f}.bin'], dtype='<c16').reshape(channels, channels)
        loss = np.frombuffer(binary[f'loss-{f}.bin'], dtype='<c16').reshape(6, channels, channels)
        if not np.isfinite(source).all() or not np.isfinite(loss).all():
            raise ValueError('Non-finite amplitude source/loss basis')
        if not np.allclose(loss, loss.conj().transpose(0, 2, 1), atol=1e-12):
            raise ValueError('Non-Hermitian amplitude loss basis')
        current = source @ coefficient
        expected = .25 * np.vdot(coefficient, current).real
        actual = np.einsum('i,kij,j->', coefficient.conj(), loss, coefficient).real
        if abs(actual-expected) > 2e-7 * max(abs(expected), 1e-20):
            raise ValueError('Amplitude combined-source power conservation failed')
        source_power += float(expected)
        current_spectrum.append(current)
    spectrum = np.array(current_spectrum)
    rms = np.sqrt(np.sum(abs(spectrum)**2, axis=0) / 2) * 1000
    if not math.isclose(float(rms.max()), row['max_source_current_RMS_mA'],
                        rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError('Reconstructed source current differs from saved result')
    if not math.isclose(source_power, row['source_power_W'], rel_tol=1e-9, abs_tol=1e-15):
        raise ValueError('Reconstructed source power differs from saved result')
    lower, upper, sampling = peak_bounds(frequencies, spectrum)
    base = {key: float(normalized[key]) for key in _LINEAR + _QUADRATIC if key in normalized}
    base.update(source_Vpp=1.0, h_mm=float(row['h_mm']),
                source_current_RMS_by_output_mA=rms.tolist(),
                source_current_peak_lower_by_output_mA=(lower*1000).tolist(),
                source_current_peak_upper_by_output_mA=(upper*1000).tolist(),
                max_source_current_RMS_mA=float(rms.max()),
                max_source_current_peak_lower_mA=float(lower.max()*1000),
                max_source_current_peak_upper_mA=float(upper.max()*1000),
                current_peak_sampling=sampling,
                current_spectrum_frequencies_Hz=list(frequencies))
    cache_path.parent.mkdir(exist_ok=True)
    atomic(cache_path, {'schema_version': SCHEMA_VERSION, 'fingerprint': fingerprint,
                        'base': base})
    return base


def _baselines(run, references):
    result = {}
    for path in sorted(run.glob('reference*.json')):
        row = json.loads(path.read_text())
        if 'h_mm' in row:
            result[float(row['h_mm'])] = row
    for key in ('baselines', 'baseline_by_h_mm'):
        provided = references.get(key, {})
        for h, row in provided.items():
            result[float(h)] = row
    return result


def _scale(base, source_vpp, baseline):
    scale = float(source_vpp)
    if not math.isfinite(scale) or scale < 0:
        raise ValueError('Amplitude scale must be nonnegative and finite')
    result = {'source_Vpp': scale, 'source_open_circuit_peak_V': .5*scale,
              'high_amplitude_extrapolation_not_validated': scale > 1,
              'device_compliance': 'unverified'}
    result.update({key: base[key]*scale for key in _LINEAR + _CURRENT_MAXIMA if key in base})
    result.update({key: base[key]*scale**2 for key in _QUADRATIC if key in base})
    result.update({key: (np.asarray(base[key])*scale).tolist() for key in _CURRENT_ARRAYS})
    if baseline is not None:
        for label, key in (('J', 'surface_J_RMS_max_A_m2'), ('SC', 'SC_power_W'),
                           ('contact', 'contact_power_W'), ('voltage', 'contact_voltage_RMS_max_V')):
            if key in result and float(baseline.get(key, 0)) > 0:
                result['ratio_to_baseline_burden_' + label] = result[key]/float(baseline[key])
        result['baseline_h_mm'] = float(baseline['h_mm'])
    return result


def build_comparison(run: Path, rows: list, references: dict) -> dict:
    """Compare reported current magnitudes through two explicit hypotheses.

    References contain sources [{id, reported_currents_mA: [...]}].  Unknown
    peak/RMS meaning is retained; neither hypothesis is an activation threshold.
    Only stable original-case metrics are cached.  Reference options and scaled
    comparisons are rebuilt on every call.
    """
    run = Path(run)
    baselines = _baselines(run, references)
    sources = references.get('sources', [])
    cases = []
    for row in rows:
        identifier = str(row.get('id', row['basis_id']))
        base = _base(run, row)
        if base is None:
            cases.append({'id': identifier, 'status': 'unavailable',
                          'reason': 'complete validated source/loss transfer cache unavailable'})
            continue
        baseline = baselines.get(float(row['h_mm']))
        comparisons = []
        for reference in sources:
            for current in reference.get('reported_currents_mA', []):
                current = float(current)
                if not math.isfinite(current) or current <= 0:
                    raise ValueError('Reported comparison current must be positive and finite')
                peak_lower = base['max_source_current_peak_lower_mA']
                peak_upper = base['max_source_current_peak_upper_mA']
                rms = base['max_source_current_RMS_mA']
                for interpretation in ('reportednumber_as_max_output_peak',
                                       'reportednumber_as_max_output_RMS'):
                    if interpretation.endswith('_peak'):
                        if peak_lower <= 0:
                            comparisons.append({'reference_id': reference['id'],
                                                'reported_current_mA': current,
                                                'comparison_basis': interpretation,
                                                'status': 'unavailable',
                                                'reason': 'zero reconstructed source current'})
                            continue
                        interval = [current/peak_upper, current/peak_lower]
                    else:
                        if rms <= 0:
                            comparisons.append({'reference_id': reference['id'],
                                                'reported_current_mA': current,
                                                'comparison_basis': interpretation,
                                                'status': 'unavailable',
                                                'reason': 'zero reconstructed source current'})
                            continue
                        interval = [current/rms, current/rms]
                    conservative = interval[1]
                    comparisons.append({'reference_id': reference['id'],
                                        'reported_current_mA': current,
                                        'comparison_basis': interpretation,
                                        'status': 'available',
                                        'hypothetical_interpretation': True,
                                        'activation_threshold_available': False,
                                        'required_source_Vpp_interval': interval,
                                        'conservative_source_Vpp': conservative,
                                        'scaled_at_conservative_Vpp': _scale(base, conservative, baseline)})
        cases.append({'id': identifier, 'status': 'available', 'base': base,
                      'engineering_sweep': [_scale(base, vpp, baseline)
                                            for vpp in (1, 2, 5, 10, 20)],
                      'comparisons': comparisons})
    return {'schema_version': SCHEMA_VERSION,
            'activation_threshold_available': False,
            'scope': 'treatment-current magnitude comparison ONLY, not activation threshold or waveform equivalence',
            'source_references': sources,
            'engineering_amplitude_sweep_Vpp': [1, 2, 5, 10, 20],
            'engineering_sweep_note': 'engineering extrapolation; not a clinical recommendation',
            'current_definition': 'per-output current includes induced current through inactive 0 V/50 ohm terminations; maxima are across outputs, not their sum',
            'model_limits': ['fixed small-signal EIS boundaries and fixed phantom properties',
                             'large-amplitude interface linearity, heating and device compliance unvalidated',
                             'CV does not establish a CIC or a safe voltage window',
                             'reported treatment current peak/RMS meaning is unreported; both interpretations are hypothetical',
                             'different pulse/carrier frequency and waveform do not imply neural or diaphragm equivalence'],
            'cases': cases,
            'unavailable_count': sum(c['status'] == 'unavailable' for c in cases)}
