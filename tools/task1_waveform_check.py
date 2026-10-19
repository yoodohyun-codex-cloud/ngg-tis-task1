#!/usr/bin/env python3
"""Independent bounded waveform audit; no research imports, PDE or source writes.

Check saved peak/+jwt spectra by reconstructing their signed time signals.  The
two-carrier TIS quantity is the range of the *fundamental-only* analytic envelope
after projection onto a real unit direction.  An all-harmonic analytic envelope
is reported separately and is not substituted for that quantity.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def coherent(frequencies, values):
    frequencies = np.asarray(frequencies, float)
    values = np.asarray(values, complex)
    if (frequencies.ndim != 1 or not len(frequencies) or values.ndim < 1
            or values.shape[0] != len(frequencies)
            or not np.isfinite(frequencies).all() or not np.isfinite(values).all()
            or np.any(frequencies <= 0) or not np.equal(frequencies, np.round(frequencies)).all()):
        raise ValueError('Finite positive integer-Hz peak complex spectra required')
    unique = np.unique(frequencies.astype(int))
    return unique, np.asarray([values[frequencies == f].sum(axis=0) for f in unique])


def directions(count=2048):
    """Explicit independent reconstruction of the historical 26+2048 set."""
    result = [np.asarray(v, float)/np.linalg.norm(v)
              for v in itertools.product((-1, 0, 1), repeat=3) if any(v)]
    for index in range(count):
        z = 1-2*(index+.5)/count
        phase = index*np.pi*(3-np.sqrt(5))
        radius = np.sqrt(1-z*z)
        result.append([radius*np.cos(phase), radius*np.sin(phase), z])
    return np.asarray(result)


def two_carrier_check(frequencies, values, fundamentals, samples=65536):
    """Audit a scalar projection by actual complex-envelope time reconstruction.

    Only one or two distinct carriers are accepted.  Three or more carriers
    require their actual multi-frequency waveform, never an extrapolated 2min.
    Uniform beat samples give an envelope-range lower bound.  The Lipschitz
    bound covers missed extrema without claiming physical uncertainty.
    """
    frequencies, values = coherent(frequencies, values)
    if values.ndim != 1:
        raise ValueError('Scalar directional phasors required')
    fundamentals = list(fundamentals)
    if (not 1 <= len(fundamentals) <= 2 or len(set(fundamentals)) != len(fundamentals)
            or not set(fundamentals) <= set(frequencies)):
        raise ValueError('One or two distinct declared fundamental frequencies required')
    selected = np.asarray([values[list(frequencies).index(f)] for f in fundamentals])
    amplitudes = abs(selected)
    expected = float(2*amplitudes.min()) if len(selected) == 2 else 0.
    maximum = float(amplitudes.sum())
    minimum = float(abs(amplitudes[0]-amplitudes[1])) if len(selected) == 2 else maximum
    beat = abs(fundamentals[-1]-fundamentals[0]) if len(selected) == 2 else 1
    times = np.arange(samples)/(samples*beat)
    # Factoring out the first carrier preserves the exact analytic magnitude
    # while avoiding high-frequency roundoff in this slow-envelope check.
    offsets = np.asarray(fundamentals)-fundamentals[0]
    envelope = abs(np.exp(2j*np.pi*times[:, None]*offsets)@selected)
    sampled_range = float(np.ptp(envelope))
    lipschitz = float(np.sum(2*np.pi*abs(offsets)*amplitudes))
    numerical_bound = lipschitz/(samples*beat)+256*np.finfo(float).eps*max(maximum, 1e-30)
    if sampled_range > expected+numerical_bound or expected > sampled_range+numerical_bound:
        raise ValueError('Two-carrier formula disagrees with reconstructed analytic envelope')
    return dict(definition='fundamental-only scalar analytic-envelope maximum minus minimum',
                fundamental_frequencies_Hz=list(map(int, fundamentals)),
                exact_minimum=minimum, exact_maximum=maximum, exact_width=expected,
                reconstructed_width_lower=sampled_range,
                missed_range_upper_bound=numerical_bound, samples=samples,
                third_harmonics_excluded=True, passed=True)


def signed_statistics(frequencies, values, samples_per_highest_cycle=256):
    """Actual signed waveform and exact spectral RMS over one common period."""
    frequencies, values = coherent(frequencies, values)
    if values.ndim not in (1, 2):
        raise ValueError('Scalar or vector peak spectrum required')
    divisor = math.gcd(*map(int, frequencies))
    samples = max(16, math.ceil(samples_per_highest_cycle*max(frequencies)/divisor))
    if samples > 262144:
        raise ValueError('Reconstruction exceeds fixed 262144-sample audit budget')
    period = 1/divisor
    times = np.arange(samples)*period/samples
    phase = np.exp(2j*np.pi*times[:, None]*frequencies)
    signed = np.real(phase@values)
    spectral_rms = float(np.sqrt(np.sum(abs(values)**2)/2))
    time_rms = float(np.sqrt(np.mean(signed**2 if values.ndim == 1 else np.sum(signed**2, axis=1))))
    relative_error = abs(time_rms-spectral_rms)/max(spectral_rms, 1e-30)
    if relative_error > 2e-12:
        raise ValueError('Actual signed-waveform RMS disagrees with coherent spectral RMS')
    result = dict(spectral_RMS=spectral_rms, reconstructed_RMS=time_rms,
                  RMS_relative_error=relative_error, common_period_s=period,
                  samples=samples, all_saved_frequencies_included=True, passed=True)
    if values.ndim == 1:
        vpp = float(np.ptp(signed))
        bound = float(np.sum((2*np.pi*frequencies)**2*abs(values))*(period/samples)**2/4)
        envelope = abs(phase@values)
        baseband_lipschitz = float(np.sum(2*np.pi*abs(frequencies-frequencies[0])*abs(values)))
        result.update(signed_Vpp_lower=vpp, signed_Vpp_upper=vpp+bound,
                      all_frequency_analytic_envelope_width_lower=float(np.ptp(envelope)),
                      all_frequency_envelope_missed_range_upper_bound=baseband_lipschitz*period/samples,
                      all_frequency_envelope_label='descriptive all-frequency analytic envelope; not two-carrier TIS')
    return result


def temporal_convergence(frequencies, values):
    """Bounded 64/128/256 samples/cycle check of the actual scalar waveform.

    The relative 0.1% criterion is a time-discretization diagnostic only.  The
    all-frequency envelope may contain fast harmonic structure and is never
    labeled as a physiological beat envelope or two-carrier TIS.
    """
    rows = [dict(samples_per_highest_cycle=count,
                 **signed_statistics(frequencies, values, count)) for count in (64, 128, 256)]
    denominator = max(float(np.sum(abs(coherent(frequencies, values)[1]))), 1e-30)
    for previous, row in zip(rows, rows[1:]):
        row['signed_Vpp_change_over_sum_peak'] = abs(row['signed_Vpp_lower']-previous['signed_Vpp_lower'])/denominator
        row['all_frequency_envelope_width_change_over_sum_peak'] = abs(
            row['all_frequency_analytic_envelope_width_lower']-
            previous['all_frequency_analytic_envelope_width_lower'])/denominator
    last = rows[-1]
    passed = max(last['signed_Vpp_change_over_sum_peak'],
                 last['all_frequency_envelope_width_change_over_sum_peak']) <= .001
    return dict(levels=rows, relative_temporal_diagnostic_tolerance=.001,
                status='converged_temporal_diagnostic' if passed else 'not_converged_temporal_diagnostic',
                passed=passed, physical_mesh_and_instrument_convergence=False)


def field_check(condition):
    metrics = condition['metrics']
    spectrum = metrics['centre_field_spectrum']
    frequencies = [row['frequency_Hz'] for row in spectrum]
    values = np.asarray([np.asarray(row['real_V_m'])+1j*np.asarray(row['imaginary_V_m']) for row in spectrum])
    frequencies, values = coherent(frequencies, values)
    if values.shape != (len(frequencies), 3):
        raise ValueError('Three-component centre field required')
    fundamentals = condition['actual_fundamental_Hz']
    if not 1 <= len(fundamentals) <= 2:
        raise ValueError('This audit does not extend two-tone TIS to three or more carriers')
    selected = np.asarray([values[list(frequencies).index(f)] for f in fundamentals])
    direction_set = directions()
    widths = 2*np.min(abs(selected@direction_set.T), axis=0) if len(selected) == 2 else np.zeros(len(direction_set))
    winner = int(np.argmax(widths))
    direction = direction_set[winner]
    expected = float(widths[winner])
    saved = float(metrics['target20_modulation_V_m'])
    if not math.isclose(expected, saved, rel_tol=2e-12, abs_tol=1e-15):
        raise ValueError('Saved centre TIS differs from independent 2074-direction check')
    waveform = signed_statistics(frequencies, values)
    if not math.isclose(waveform['spectral_RMS'], metrics['target20_total_E_RMS_V_m'], rel_tol=2e-12, abs_tol=1e-15):
        raise ValueError('Saved centre vector RMS differs from signed waveform')
    directional_values = values@direction
    return dict(condition_id=condition['id'], waveform=condition['waveform'],
                saved_direction_max_TIS_V_m=saved, direction=direction.tolist(),
                direction_index=winner, direction_count=len(direction_set),
                angular_scope='lower bound from finite real unit directions; no continuum maximum claim',
                vector_waveform=waveform,
                winning_direction_fundamental_envelope=two_carrier_check(frequencies, directional_values, fundamentals),
                winning_direction_actual_signed_waveform=signed_statistics(frequencies, directional_values),
                actual_harmonic_waveform_temporal_convergence=temporal_convergence(frequencies, directional_values),
                passed=True)


def probe_check(condition):
    probe = condition['probe40']
    if probe['status'] != 'complete' or len(probe['measurements']) != 40:
        raise ValueError('Complete 40-probe result required')
    seen = set()
    rms_errors, envelope_errors, gaps, temporal = [], [], [], []
    centers = {'centre': (0., 0.), 'x_plus': (5., 0.), 'x_minus': (-5., 0.),
               'y_plus': (0., 5.), 'y_minus': (0., -5.)}
    for row in probe['measurements']:
        depth, axis, position = row['depth_from_skin_surface_mm'], row['axis'], row['position']
        key = (depth, position, axis)
        if depth not in (5, 10, 15, 20) or axis not in ('X', 'Y') or position not in centers or key in seen:
            raise ValueError('Duplicate or unexpected cross-probe location')
        seen.add(key)
        center = np.array([*centers[position], depth])
        offset = np.array([2.5, 0., 0.]) if axis == 'X' else np.array([0., 2.5, 0.])
        if not all(np.allclose(row[name], expected, rtol=0, atol=1e-12)
                   for name, expected in [('centre_mm', center), ('plus_mm', center+offset), ('minus_mm', center-offset)]):
            raise ValueError('Probe center pitch and/or 5mm tip gap differ from contract')
        frequencies = [item['frequency_Hz'] for item in row['spectrum']]
        values = [complex(item['real_V'], item['imaginary_V']) for item in row['spectrum']]
        actual = signed_statistics(frequencies, values)
        error = abs(actual['spectral_RMS']-row['RMS_V'])/max(row['RMS_V'], 1e-30)
        if error > 2e-12:
            raise ValueError('Saved differential probe RMS differs from complex spectrum')
        saved_lo, saved_hi = row['Vpp_lower_V'], row['Vpp_upper_V']
        gap = max(saved_lo, actual['signed_Vpp_lower'])-min(saved_hi, actual['signed_Vpp_upper'])
        if gap > 1e-14:
            raise ValueError('Saved and independently reconstructed signed Vpp brackets do not overlap')
        declared = row['fundamental_fixed_axis_envelope']
        envelope = two_carrier_check(frequencies, values, declared['frequencies_Hz'])
        envelope_error = abs(envelope['exact_width']-declared['variation_range_V'])
        if envelope_error > 1e-12*max(envelope['exact_maximum'], 1e-12):
            raise ValueError('Saved fixed-axis voltage envelope differs from reconstruction')
        rms_errors.append(error); envelope_errors.append(envelope_error); gaps.append(max(0., gap))
        convergence = temporal_convergence(frequencies, values)
        temporal.append(dict(probe_id=row['id'], status=convergence['status'],
            signed_Vpp_change_over_sum_peak=convergence['levels'][-1]['signed_Vpp_change_over_sum_peak'],
            all_frequency_envelope_width_change_over_sum_peak=convergence['levels'][-1]['all_frequency_envelope_width_change_over_sum_peak']))
    return dict(condition_id=condition['id'], expected_count=40, complete_count=len(seen),
                max_RMS_relative_error=max(rms_errors), max_fundamental_envelope_error_V=max(envelope_errors),
                max_Vpp_bracket_nonoverlap_V=max(gaps),
                coordinates='z=0 skin surface, +z depth; X/Y local phantom axes',
                centre_pitch_mm=5., differential_tip_gap_mm=5.,
                loading_status='unloaded; instrument R/C, bandwidth, switch and calibration unvalidated',
                actual_waveform_temporal_diagnostics=temporal,
                temporal_diagnostic_tolerance=.001, passed=True)


def bulk_skin_current_density(spectra, grid, gamma_by_frequency):
    """Pure loaded-array helper; no native imports, file access or solver.

    Report volume-weighted native cell J vector RMS in SC, dermis, and their
    union.  Total current gamma*E and conductive current Re(gamma)*E are distinct.
    These values do not replace contact-face, area-weighted normal J statistics.
    """
    layer, weights = np.asarray(grid['layer']), np.asarray(grid['volume_m3'], float)
    if (not len(layer) or weights.shape != layer.shape or not np.isfinite(weights).all()
            or np.any(weights <= 0) or not np.isin(layer, [0, 1, 2, 3]).all()):
        raise ValueError('Native positive cell volumes and known tissue IDs required')
    squared = dict(total=np.zeros(len(layer)), conductive=np.zeros(len(layer)))
    if not spectra:
        raise ValueError('Actual coherently combined field spectra required')
    for frequency, field in spectra.items():
        field = np.asarray(field, complex)
        if field.shape != (len(layer), 3) or not np.isfinite(field).all():
            raise ValueError('Finite native vector field required at every actual frequency')
        gamma = np.array([complex(gamma_by_frequency[frequency][int(value)]) for value in layer])
        if not np.isfinite(gamma).all() or np.any(gamma.real <= 0) or np.any(gamma.imag < 0):
            raise ValueError('Finite passive peak/+jwt tissue admittivity required')
        magnitude2 = np.sum(abs(field)**2, axis=1)/2
        squared['total'] += abs(gamma)**2*magnitude2
        squared['conductive'] += gamma.real**2*magnitude2
    result = {}
    for region, selector in [('SC', layer == 0), ('dermis', layer == 1), ('skin_SC_plus_dermis', layer <= 1)]:
        if not np.any(selector):
            raise ValueError('Missing required native skin tissue '+region)
        w = weights[selector]
        result[region] = {}
        for kind, values in squared.items():
            values = np.sqrt(values[selector])
            order = np.argsort(values, kind='stable')
            index = min(int(np.searchsorted(np.cumsum(w[order]), .95*w.sum())), len(order)-1)
            result[region][kind] = dict(J_vector_RMS_max_A_m2=float(values.max()),
                J_vector_RMS_p95_A_m2=float(values[order[index]]),
                J_vector_RMS_volume_mean_A_m2=float(values@w/w.sum()),
                region_energy_RMS_A_m2=float(np.sqrt((values**2)@w/w.sum())),
                tissue_volume_m3=float(w.sum()))
    return dict(regions=result,
                definition='native cell vector RMS sqrt(sum_f ||gamma_f E_f||^2/2); volume-weighted P95',
                conductive_definition='replace complex gamma with Re(gamma); excludes displacement current',
                skin_definition='SC 0–0.1mm plus dermis 0.1–5.1mm; distinct from depth 0–5mm non-target region',
                contact_face_J_definition='existing contact J uses I/overlap-area and contact-area-weighted P95; preserved separately',
                scope='native sampled finite-volume reconstructed E; not converged surface maxima or safety limits')


def _verified_config(summary):
    expected = summary['mesh_metadata']['config_sha256']
    options = [Path(path) for path, digest in summary['input_sha256'].items()
               if path.endswith('.properties') and digest == expected]
    for path in options:
        if path.is_file() and sha256(path) == expected:
            result = {}
            for line in path.read_text().splitlines():
                if '=' in line and not line.lstrip().startswith('#'):
                    key, value = line.split('=', 1)
                    result[key.strip()] = value.strip()
            return result
    raise ValueError('Native config missing or changed; cannot certify C1 material/contact identity')


def _roi_energy_rms(summary_path, summary, condition):
    # The exporter archives native per-cell RMS only for primary square_3h.
    # Derived sine/triangle summaries point at that archive too; using it for
    # their ROI energy would silently include wrong harmonic coefficients.
    if condition['waveform'] != 'square_3h':
        raise ValueError('ROI energy RMS archive exists for square_3h only; recompute other actual spectra explicitly')
    name = condition['native_volume_archive']
    path = Path(summary_path).parent/name
    expected = summary['artifacts']['files'][name]['SHA256']
    if sha256(path) != expected:
        raise ValueError('Native volume archive SHA differs from completed summary')
    with np.load(path, allow_pickle=False) as archive:
        values = archive['RMS']
        weights = archive['region_target_m3']
    if (values.shape != weights.shape or values.ndim != 1 or not np.isfinite(values).all()
            or not np.isfinite(weights).all() or np.any(values < 0) or np.any(weights < 0) or weights.sum() <= 0):
        raise ValueError('Invalid native ROI RMS/volume weights')
    return float(np.sqrt((values**2)@weights/weights.sum())), weights, dict(path=str(path.resolve()), SHA256=expected)


_LINEAR_METRICS = ('target20_modulation_V_m', 'target20_total_E_RMS_V_m',
                   'surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2',
                   'contact_voltage_RMS_max_V', 'max_source_current_RMS_mA')
_POWER_METRICS = ('SC_power_W', 'contact_power_W', 'skin_power_W',
                  'tissue_contact_power_W', 'source_power_W', 'source_resistor_power_W')


def c1_report(tis_path, single_path, waveform='square_3h'):
    """Same-point, ROI energy RMS and mean-local-RMS matches without a PDE."""
    tis_path, single_path = Path(tis_path).resolve(), Path(single_path).resolve()
    tis, single = (json.loads(path.read_text()) for path in (tis_path, single_path))
    if tis['status'] != 'complete' or single['status'] != 'complete':
        raise ValueError('Both TIS and genuine C1 summaries must be complete')
    tm, sm = tis['mesh_metadata'], single['mesh_metadata']
    if tm['channels'] != 2 or sm['channels'] != 1:
        raise ValueError('Require four-pad/two-output TIS and true two-pad/one-output C1')
    same_keys = ('h_xy_mm', 'radius_mm', 'total_depth_mm', 'sc_cells', 'bulk_layer_counts',
                 'z_faces_mm', 'tissue_boundaries_mm', 'source_peak_V', 'source_resistance_ohm',
                 'phasor_convention', 'field_reconstruction')
    for key in same_keys:
        if key not in tm or key not in sm or tm[key] != sm[key]:
            raise ValueError('C1 matching requires identical mesh/circuit/reconstruction: '+key)
    if tis['source_normalization'] != single['source_normalization']:
        raise ValueError('Source normalizations differ')
    configs = [_verified_config(summary) for summary in (tis, single)]
    relevant = {key for key in configs[0] if key.endswith(('.sigma', '.epsilon_r')) or key.startswith('z.')}
    if not relevant or any(configs[0].get(key) != configs[1].get(key) for key in relevant):
        raise ValueError('TIS/C1 material or area-specific complex contact differs')
    references = [row for row in tis['conditions'] if row['waveform'] == waveform]
    controls = [row for row in single['conditions'] if row['waveform'] == waveform]
    if len(references) != 1 or not controls:
        raise ValueError('One explicit TIS waveform reference and C1 controls required')
    reference = references[0]
    pairs, archives = [], {}
    for control in controls:
        if (len(control['actual_fundamental_Hz']) != 1
                or control['actual_fundamental_Hz'][0] not in reference['actual_fundamental_Hz']
                or control['metrics']['target20_modulation_V_m'] != 0):
            raise ValueError('Genuine same-carrier C1 must have zero two-carrier TIS')
        for row in (reference, control):
            if row['source_Vpp_per_output'] != 1:
                raise ValueError('C1 downstream matching requires unchanged 1Vpp anchors')
        t_roi, tw, tarchive = _roi_energy_rms(tis_path, tis, reference)
        s_roi, sw, sarchive = _roi_energy_rms(single_path, single, control)
        archives[tarchive['path']] = tarchive
        archives[sarchive['path']] = sarchive
        if not np.array_equal(tw, sw):
            raise ValueError('TIS/C1 native target ROI weights differ')
        matches = [('centre20_vector_E_RMS', reference['metrics']['target20_total_E_RMS_V_m'],
                    control['metrics']['target20_total_E_RMS_V_m']),
                   ('ROI_energy_E_RMS', t_roi, s_roi),
                   ('ROI_mean_local_E_RMS', reference['volume_metrics']['regions']['target']['statistics']['RMS']['mean'],
                    control['volume_metrics']['regions']['target']['statistics']['RMS']['mean'])]
        for criterion, target, response in matches:
            if not math.isfinite(target+response) or min(target, response) <= 0:
                raise ValueError('Positive finite RMS target/control response required')
            scale = target/response
            scaled = {key: float(control['metrics'][key]*scale) for key in _LINEAR_METRICS}
            scaled.update({key: float(control['metrics'][key]*scale**2) for key in _POWER_METRICS})
            scaled['source_current_RMS_by_output_mA'] = (np.asarray(control['metrics']['source_current_RMS_by_output_mA'])*scale).tolist()
            scaled['ROI_energy_E_RMS_V_m'] = s_roi*scale
            scaled['ROI_mean_local_E_RMS_V_m'] = control['volume_metrics']['regions']['target']['statistics']['RMS']['mean']*scale
            pairs.append(dict(tis_condition_id=reference['id'], single_condition_id=control['id'],
                criterion=criterion, target_RMS_V_m=target, required_single_open_circuit_Vpp=scale,
                tis_source_open_circuit_Vpp_per_output=1., single_n_pads=2, single_n_outputs=1,
                single_fundamental_Hz=control['actual_fundamental_Hz'], single_metrics_at_match=scaled,
                tis_metrics_at_1Vpp={key: reference['metrics'][key] for key in (*_LINEAR_METRICS, *_POWER_METRICS)},
                exact_linear_scaling=True, additional_PDE=0, envelope_or_physiological_equivalence=False))
    return dict(tis_case_id=tis['id'], single_case_id=single['id'], waveform=waveform,
                tis_summary_sha256=sha256(tis_path), single_summary_sha256=sha256(single_path),
                tis_config_sha256=tm['config_sha256'], single_config_sha256=sm['config_sha256'],
                native_ROI_archives=list(archives.values()),
                RMS_definitions=dict(centre20='sqrt(sum_f ||Ehat_f(0,0,20mm)||^2/2)',
                    ROI_energy='sqrt(sum_cells w_i * E_RMS_i^2 / sum_cells w_i)',
                    ROI_mean_local='sum_cells w_i * E_RMS_i / sum_cells w_i; distinct from ROI energy RMS'),
                return_definition='single signal pad plus one physical return pad; retained 50ohm source to ideal ground',
                pairs=pairs, status='computed_downstream_scaling',
                numerical_spatial_validation='inherited from source summaries; scaling is not new mesh convergence',
                physical_validation='unvalidated', new_PDE=0)


def audit_summary(path):
    path = Path(path).resolve()
    summary = json.loads(path.read_text())
    if summary['status'] != 'complete':
        raise ValueError('Only completed postprocess summaries can be audited')
    probes_path = path.parent/summary['artifacts']['probes_json']
    probes = json.loads(probes_path.read_text())
    conditions = summary['conditions']
    fields = [field_check(condition) for condition in conditions]
    expected = {row['id'] for row in conditions}
    if {row['id'] for row in probes['conditions']} != expected:
        raise ValueError('Probe condition IDs differ from summary IDs')
    return dict(summary_path=str(path), summary_sha256=sha256(path),
                probes_sha256=sha256(probes_path), case_id=summary['id'],
                postprocessor_sha256=summary['postprocessor_sha256'],
                fields=fields, probes=[probe_check(condition) for condition in probes['conditions']],
                scope='independent spectral/time audit of saved phasors; no PDE or mesh reproduction', passed=True)


def self_test():
    checks = []
    for a, b in [(1+.3j, -.6+.2j), (1j, 1), (0, 2j), (1, -1)]:
        checks.append(two_carrier_check([2000, 2010], [a, b], [2000, 2010])['passed'])
    f, v = coherent([2000, 2000, 6000], [1j, -1j, .4])
    checks.append(bool(np.array_equal(f, [2000, 6000]) and np.allclose(v, [0, .4])))
    single = two_carrier_check([3000, 9000], [1j, .2], [3000])
    checks.append(single['exact_width'] == 0 and signed_statistics([3000, 9000], [1j, .2])['spectral_RMS'] > 0)
    base = two_carrier_check([3000, 3030, 9000, 9090], [1j, .6, .5, -.3j], [3000, 3030])
    full = signed_statistics([3000, 3030, 9000, 9090], [1j, .6, .5, -.3j])
    checks.append(abs(base['exact_width']-full['all_frequency_analytic_envelope_width_lower']) > .01)
    try:
        two_carrier_check([10, 11, 12], [1, 1, 1], [10, 11, 12])
    except ValueError:
        checks.append(True)
    else:
        checks.append(False)
    # Polarized complex vectors require projection of the complete complex E,
    # not its real part.  This case has a zero real part for one whole carrier.
    a, b = np.array([1j, .2j, 0]), np.array([.3, .8j, 0])
    unit = np.array([1, 1, 0])/math.sqrt(2)
    polarized = two_carrier_check([3000, 3030], [a@unit, b@unit], [3000, 3030])
    checks.append(polarized['exact_width'] > 0)
    if not all(checks):
        raise ValueError('Synthetic independent waveform audit failed')
    return dict(passed=True, checks=len(checks), new_PDE=0,
                covered=['arbitrary phase', 'complex vector polarization', 'zero carrier',
                         'coincident-frequency cancellation', 'single carrier nonzero RMS/zero TIS',
                         'third-harmonic envelope differs', 'three-carrier 2min extension rejected'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--summary', type=Path, action='append', default=[])
    parser.add_argument('--match-tis', type=Path)
    parser.add_argument('--match-single', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if bool(args.match_tis) != bool(args.match_single):
        parser.error('--match-tis and --match-single must be supplied together')
    if not args.self_test and not args.summary and not args.match_tis:
        parser.error('Choose --self-test, --summary and/or --match-tis/--match-single')
    report = dict(schema_version=1, audit_code_sha256=sha256(__file__), new_PDE=0,
                  validation_scope='waveform algebra only; no mesh, physical, activation or safety certification')
    if args.self_test:
        report['synthetic'] = self_test()
    report['summaries'] = [audit_summary(path) for path in args.summary]
    report['C1_matches'] = [c1_report(args.match_tis, path) for path in args.match_single]
    text = json.dumps(report, indent=2, allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as stream:
            stream.write(text)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
