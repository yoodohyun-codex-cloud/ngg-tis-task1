#!/usr/bin/env python3
"""Finite unloaded native-probe voltage conversions using user hardware specs.

Input admittances are reported without inventing phantom port impedances.
Neither nominal attenuation nor an optional assumed one-pole transfer is a
loaded or experimentally validated prediction.  No PDE or research imports.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import numpy as np

from task1_waveform_check import coherent, signed_statistics, two_carrier_check


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT/'configs/task1_instrument_ETA5001_DSOX1202A.json'
DISK_RESERVE = 2*1024**3


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            result.update(block)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def validate_actual_request(summary_path, output):
    """CLI gate: a completed case record, even inside a stopped failed run."""
    summary_path, output = Path(summary_path).resolve(), Path(output).resolve()
    run = summary_path.parents[2]
    supplements = ROOT/'docs/cloud-restart-20261020/instruments'
    if (run.parent != ROOT/'data-native' or not run.name.startswith('cloud-')
            or not summary_path.is_relative_to(run/'postprocess')
            or not (output.is_relative_to(run/'audit') or output.is_relative_to(supplements))
            or output.exists()):
        raise ValueError('Use a unique output under the matching run/audit or docs/cloud-restart-20261020/instruments')
    summary = read(summary_path)
    case_id = summary_path.parent.name
    record_path = run/'cases'/(case_id+'.json')
    if not record_path.is_file():
        raise ValueError('A complete case execution record is required; complete postprocessing alone is insufficient')
    record = read(record_path)
    if (summary.get('id') != case_id or record.get('id') != case_id
            or summary.get('status') != 'complete' or record.get('status') != 'complete'):
        raise ValueError('Case execution record and postprocess summary must both be complete with matching IDs')
    if (record.get('postprocess_sha256') != sha(summary_path)
            or Path(record.get('postprocess_path', '')).resolve() != summary_path):
        raise ValueError('Completed case postprocess SHA/path differs from the requested summary')
    registration = read(run/'preregistration.json')
    registered = [case for case in registration['cases'] if case['id'] == case_id]
    if len(registered) != 1:
        raise ValueError('One exact preregistered case required')
    expected = registered[0]['config_sha256']
    config_path = Path(registered[0]['config_file']).resolve()
    if (record.get('config_sha256') != expected
            or summary.get('mesh_metadata', {}).get('config_sha256') != expected
            or not config_path.is_file() or sha(config_path) != expected):
        raise ValueError('Completed case/config/native metadata SHA values must match')
    controller, state = read(run/'controller.json'), read(run/'summary.json')
    status = controller.get('status')
    if (status not in ('complete', 'error', 'resource_shortage', 'stopped')
            or state.get('status') != status
            or status != 'complete' and controller.get('phase') != 'stopped'):
        raise ValueError('Source run must have matching terminal statuses; active source state is ineligible')
    return run, dict(case_record_path=str(record_path), case_record_sha256=sha(record_path),
        case_execution_status='complete', source_run_original_terminal_status=status,
        registered_config_sha256=expected,
        output_is_git_supplement=output.is_relative_to(supplements),
        failed_run_promoted_to_complete=False)


def check_disk_reserve(output, additional_bytes=0):
    parent = Path(output).parent
    while not parent.exists():
        parent = parent.parent
    if shutil.disk_usage(parent).free < DISK_RESERVE+additional_bytes:
        raise ValueError('Output plus unchanged 2GiB disk reserve unavailable')


def complex_record(value, unit):
    return dict(real=float(np.real(value)), imaginary=float(np.imag(value)),
                magnitude=float(abs(value)), phase_deg=float(np.angle(value, deg=True)), unit=unit)


def validate_config(config):
    if config['schema'] != 'task1-instrument-user-spec-v1':
        raise ValueError('Unsupported instrument configuration schema')
    probe, scope = config['probe'], config['scope']
    each, differential = probe['each_input_to_ground'], probe['between_inputs']
    positive = [each['resistance_ohm'], each['capacitance_F'], differential['resistance_ohm'],
        differential['capacitance_F'], probe['bandwidth_Hz'], scope['input_resistance_ohm'],
        scope['input_capacitance_F']]
    if any(not math.isfinite(value) or value <= 0 for value in positive):
        raise ValueError('Finite positive user R/C and bandwidth values required')
    if (not math.isclose(differential['resistance_ohm'], 2*each['resistance_ohm'], rel_tol=1e-12)
            or not math.isclose(differential['capacitance_F'], each['capacitance_F']/2, rel_tol=1e-12, abs_tol=0)):
        raise ValueError('Differential specification must be the equivalent of two input-to-ground shunts; no extra branch')
    if probe['attenuation_options'] != [50, 500]:
        raise ValueError('Both explicit matched 50x and 500x voltage conversions must be preserved')
    if (not 0 <= scope['input_resistance_relative_tolerance'] < 1
            or not 0 <= scope['input_capacitance_absolute_tolerance_F'] < scope['input_capacitance_F']):
        raise ValueError('Scope R/C tolerance must preserve positive values')
    if config['provenance']['independent_manufacturer_verification_performed'] is not False:
        raise ValueError('This predictor must preserve user-spec provenance without claiming manufacturer verification')


def input_admittances(frequency, config):
    """Two shunts only; differential and common-mode values are derived views."""
    frequency = float(frequency)
    if not math.isfinite(frequency) or frequency <= 0:
        raise ValueError('Positive finite frequency required')
    each, scope = config['probe']['each_input_to_ground'], config['scope']
    omega = 2*np.pi*frequency
    y = 1/each['resistance_ohm']+1j*omega*each['capacitance_F']
    y_diff, y_common = y/2, 2*y
    r0, c0 = scope['input_resistance_ohm'], scope['input_capacitance_F']
    corners = []
    for r_scale in (1-scope['input_resistance_relative_tolerance'], 1+scope['input_resistance_relative_tolerance']):
        for delta_c in (-scope['input_capacitance_absolute_tolerance_F'], scope['input_capacitance_absolute_tolerance_F']):
            r, c = r0*r_scale, c0+delta_c
            corners.append(dict(resistance_ohm=r, capacitance_F=c,
                                impedance=complex_record(1/(1/r+1j*omega*c), 'ohm')))
    return dict(frequency_Hz=frequency,
        each_tip_to_reference_ground_admittance=complex_record(y, 'S'),
        each_tip_to_reference_ground_impedance=complex_record(1/y, 'ohm'),
        differential_port_admittance=complex_record(y_diff, 'S'),
        differential_port_impedance=complex_record(1/y_diff, 'ohm'),
        differential_definition='I_diff=(I_plus-I_minus)/2, V_diff=V_plus-V_minus; Y_diff=Y_each/2',
        common_mode_pair_admittance=complex_record(y_common, 'S'),
        common_mode_pair_impedance=complex_record(1/y_common, 'ohm'),
        common_mode_definition='both tips at V_cm to probe reference; I_plus+I_minus=2*Y_each*V_cm',
        network='two equal input-to-ground shunts only; differential spec is not another parallel load',
        downstream_scope_input=dict(nominal_impedance=complex_record(1/(1/r0+1j*omega*c0), 'ohm'),
            user_tolerance_corners=corners, phantom_parallel_load=False,
            output_loading_effect='held: probe output impedance and transfer/load reference are unverified'))


def loading_prediction(open_tip_potentials=None, port_impedance=None, tip_admittances=None):
    """Explicit port formula, usable with synthetic data without inventing ports.

    The CLI supplies no port matrix: actual loaded values remain unavailable.
    For supplied synthetic/extracted port data the algebra is exact only for
    the declared linear finite-port circuit, not a certification of that model.
    """
    equations = dict(first_order_tip_change='delta_V = -Z_port @ diag(Y_plus,Y_minus) @ V_open',
        first_order_differential_change='[1,-1] @ delta_V',
        exact_linear_port_solution='V_loaded = solve(I + Z_port @ diag(Y_plus,Y_minus), V_open)')
    if open_tip_potentials is None or port_impedance is None or tip_admittances is None:
        return dict(status='held_missing_native_port_response', equations=equations,
            missing=['per-frequency 2x2 complex finite-tip-port impedance Z_port',
                     'both native open-circuit tip potentials relative to actual probe reference ground',
                     'verified tip/contact regularization, ground connection and native circuit response'],
            loaded_Vpp_V=None, loaded_RMS_V=None, loaded_prediction_validated=False,
            full_PDE_probe_loading_recomputed=False)
    v0, z, y = np.asarray(open_tip_potentials, complex), np.asarray(port_impedance, complex), np.asarray(tip_admittances, complex)
    if (v0.shape != (2,) or z.shape != (2, 2) or y.shape != (2,)
            or not all(np.isfinite(value).all() for value in (v0, z, y))):
        raise ValueError('Two finite complex tip potentials, 2x2 port Z, and two tip admittances required')
    operator = z@np.diag(y)
    delta = -operator@v0
    loaded = np.linalg.solve(np.eye(2)+operator, v0)
    q = float(np.linalg.norm(operator, ord=2))
    return dict(status='algebra_computed_for_explicit_supplied_linear_port_model', equations=equations,
        first_order_change=[complex_record(value, 'V') for value in delta],
        exact_linear_port_voltages=[complex_record(value, 'V') for value in loaded],
        exact_linear_port_differential_voltage=complex_record(loaded[0]-loaded[1], 'V'),
        first_order_expansion_norm=q, convergent_neumann_series_bound_available=q < 1,
        first_order_remainder_norm_upper_V=float(q*q*np.linalg.norm(v0)/(1-q)) if q < 1 else None,
        actual_tip_model_validated=False, full_PDE_probe_loading_recomputed=False)


def assumed_one_pole_transfer(frequencies, config):
    frequencies = np.asarray(frequencies, float)
    if not np.isfinite(frequencies).all() or np.any(frequencies <= 0):
        raise ValueError('Positive actual frequencies required for assumed transfer')
    probe_cutoff = config['probe']['bandwidth_Hz']
    scope_cutoff = config['recommended_start_configuration']['scope_bandwidth_limit_Hz']
    return 1/(1+1j*frequencies/probe_cutoff)/(1+1j*frequencies/scope_cutoff)


def spectral_report(frequencies, values, fundamentals):
    frequencies, values = coherent(frequencies, values)
    stats = signed_statistics(frequencies, values)
    envelope = two_carrier_check(frequencies, values, fundamentals)
    return dict(spectrum=[dict(frequency_Hz=int(f), peak_voltage=complex_record(value, 'V'))
                          for f, value in zip(frequencies, values)],
        RMS_V=stats['spectral_RMS'], Vpp_lower_V=stats['signed_Vpp_lower'], Vpp_upper_V=stats['signed_Vpp_upper'],
        common_period_s=stats['common_period_s'], statistics_samples=stats['samples'],
        waveform_RMS_reconstruction_relative_error=stats['RMS_relative_error'],
        fundamental_envelope=dict(minimum_V=envelope['exact_minimum'], maximum_V=envelope['exact_maximum'],
            variation_width_V=envelope['exact_width'], frequencies_Hz=envelope['fundamental_frequencies_Hz'],
            third_harmonics_excluded=True, direction_max_field_TIS=False),
        all_frequency_analytic_envelope=dict(sampled_width_lower_V=stats['all_frequency_analytic_envelope_width_lower'],
            missed_range_upper_bound_V=stats['all_frequency_envelope_missed_range_upper_bound'],
            label='all-saved-frequency analytic magnitude; distinct from fundamental envelope'),
        definition='Re(sum_f(Vhat_f exp(+j2pi f t))); phasors are peak complex volts; signed whole-period Vpp')


def matched_conversions(report, config):
    """Nominal output/scope conversion, not a phantom load or measured gain."""
    result = []
    for attenuation in config['probe']['attenuation_options']:
        result.append(dict(hardware_attenuation=attenuation, scope_probe_factor=attenuation,
            actual_switches_verified=False,
            BNC_RMS_V=report['RMS_V']/attenuation,
            BNC_Vpp_lower_V=report['Vpp_lower_V']/attenuation,
            BNC_Vpp_upper_V=report['Vpp_upper_V']/attenuation,
            displayed_input_referred_RMS_V=report['RMS_V'],
            displayed_input_referred_Vpp_lower_V=report['Vpp_lower_V'],
            displayed_input_referred_Vpp_upper_V=report['Vpp_upper_V'],
            BNC_complex_spectrum_factor=1/attenuation, display_complex_spectrum_factor=1.,
            nominal_transfer_only=True, scope_input='1Mohm high impedance, DC; no external 50ohm termination',
            probe_output_impedance_loading_effect_included=False))
    return result


def time_plot(frequencies, values, fundamentals):
    """Bounded 2ms display; full common-period statistics remain separate."""
    frequencies, values = coherent(frequencies, values)
    count = min(1025, max(65, math.ceil(32*max(frequencies)*.002)+1))
    times = np.linspace(0., .002, count)
    selected = [list(frequencies).index(f) for f in fundamentals]
    divisor = math.gcd(*map(int, frequencies))
    beat_times = np.linspace(0., 1/divisor, 257)
    return dict(time_ms=(times*1000).tolist(), signed_tip_voltage_V=np.real(np.exp(2j*np.pi*times[:, None]*frequencies)@values).tolist(),
        fundamental_envelope_full_period=dict(time_ms=(beat_times*1000).tolist(),
            envelope_V=abs(np.exp(2j*np.pi*beat_times[:, None]*frequencies[selected])@values[selected]).tolist()),
        extrema_and_RMS_use_full_period_statistics=True, display_samples_do_not_replace_Vpp_bounds=True)


def probe_prediction(row, config, illustrative_one_pole=False, include_plots=False):
    if row['status'] != 'complete':
        raise ValueError('A complete native complex differential probe is required')
    frequencies = [item['frequency_Hz'] for item in row['spectrum']]
    values = [complex(item['real_V'], item['imaginary_V']) for item in row['spectrum']]
    frequencies, values = coherent(frequencies, values)
    fundamentals = row['fundamental_fixed_axis_envelope']['frequencies_Hz']
    base = spectral_report(frequencies, values, fundamentals)
    if (not math.isclose(base['RMS_V'], row['RMS_V'], rel_tol=2e-12, abs_tol=1e-15)
            or max(base['Vpp_lower_V'], row['Vpp_lower_V']) > min(base['Vpp_upper_V'], row['Vpp_upper_V'])+1e-14):
        raise ValueError('Saved native probe statistics disagree with actual phasors')
    scenarios = [dict(id='nominal_unfiltered_unloaded_conversion',
        status='unloaded_native_tissue_voltage_with_nominal_conversion_only',
        transfer_assumption='unity complex voltage transfer before nominal 50x/500x attenuation; actual response unverified',
        tip_equivalent_output=base, matched_options=matched_conversions(base, config),
        phantom_input_loading_included=False, actual_instrument_transfer_validated=False)]
    if include_plots:
        scenarios[0]['time_plot'] = time_plot(frequencies, values, fundamentals)
    if illustrative_one_pole:
        transfer = assumed_one_pole_transfer(frequencies, config)
        filtered = spectral_report(frequencies, values*transfer, fundamentals)
        scenario = dict(id='illustrative_assumed_15MHz_20MHz_one_pole_cascade',
            status='assumed_not_measured_unloaded_voltage_transfer',
            transfer_assumption=config['illustrative_filter_option']['status'],
            complex_transfer=[dict(frequency_Hz=int(f), H=complex_record(h, 'dimensionless'))
                              for f, h in zip(frequencies, transfer)],
            tip_equivalent_output=filtered, matched_options=matched_conversions(filtered, config),
            phantom_input_loading_included=False, actual_instrument_transfer_validated=False,
            actual_scope_bandwidth_option_known=False, actual_20MHz_switch_known=False)
        if include_plots:
            scenario['time_plot'] = time_plot(frequencies, values*transfer, fundamentals)
        scenarios.append(scenario)
    return dict(probe_id=row['id'], centre_mm=row['centre_mm'], plus_mm=row['plus_mm'], minus_mm=row['minus_mm'],
        depth_from_skin_surface_mm=row['depth_from_skin_surface_mm'], axis=row['axis'],
        differential_tip_gap_mm=row['tip_gap_mm'], plus_centre_pitch_mm=row['plus_centre_pitch_mm'],
        open_circuit_native_spectrum=base['spectrum'], scenarios=scenarios,
        actual_loaded_prediction=loading_prediction())


def build_prediction(summary_path, config_path=DEFAULT_CONFIG, waveform='square_3h',
                     illustrative_one_pole=False, include_plots=False, deadline=None):
    summary_path, config_path = Path(summary_path).resolve(), Path(config_path).resolve()
    input_hashes = {str(summary_path): sha(summary_path), str(config_path): sha(config_path)}
    config, summary = read(config_path), read(summary_path)
    source_run_context = dict(source_commit=None, terminal_status=None,
                              status='not_present_in_standalone_synthetic_fixture')
    registration_path = summary_path.parents[2]/'preregistration.json'
    controller_path = summary_path.parents[2]/'controller.json'
    if registration_path.is_file():
        registration = read(registration_path)
        input_hashes[str(registration_path)] = sha(registration_path)
        source_run_context = dict(source_commit=registration.get('source_commit'),
            historical_source_commit=registration.get('historical_source_commit'),
            run_id=summary_path.parents[2].name, status='source_registration_linked', terminal_status=None)
        if controller_path.is_file():
            source_run_context['terminal_status'] = read(controller_path)['status']
            input_hashes[str(controller_path)] = sha(controller_path)
    validate_config(config)
    if summary['status'] != 'complete':
        raise ValueError('Exact completed candidate postprocessing required; no mutable result prediction')
    probes_path = summary_path.parent/summary['artifacts']['probes_json']
    expected = summary['artifacts']['files'][summary['artifacts']['probes_json']]['SHA256']
    if sha(probes_path) != expected:
        raise ValueError('Native probes SHA differs from completed candidate summary')
    input_hashes[str(probes_path)] = expected
    probes = read(probes_path)
    selected = [condition for condition in summary['conditions'] if condition['waveform'] == waveform]
    if not selected:
        raise ValueError('Requested actual waveform condition is unavailable')
    reports, all_frequencies = [], set()
    for condition in selected:
        matches = [item for item in probes['conditions'] if item['id'] == condition['id']]
        if len(matches) != 1:
            raise ValueError('Unique probe condition ID must match candidate ID')
        probe = matches[0]['probe40']
        if (probe['status'] != 'complete' or probe['counts']['complete'] != 40
                or len(probe['measurements']) != 40 or probe['expected_waveform_count'] != 40):
            raise ValueError('All 40 native cross probes are required')
        seen = set()
        predictions = []
        centers = {'centre': (0., 0.), 'x_plus': (5., 0.), 'x_minus': (-5., 0.), 'y_plus': (0., 5.), 'y_minus': (0., -5.)}
        for row in probe['measurements']:
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError('Finite instrument postprocessing deadline exceeded')
            key = (row['depth_from_skin_surface_mm'], row['position'], row['axis'])
            if (key in seen or key[0] not in (5., 10., 15., 20.) or key[1] not in centers
                    or key[2] not in ('X', 'Y') or row['tip_gap_mm'] != 5. or row['plus_centre_pitch_mm'] != 5.):
                raise ValueError('Native probe layout differs from fixed four-depth/5-center/two-axis contract')
            center = np.array([*centers[key[1]], key[0]])
            offset = np.array([2.5, 0., 0.]) if key[2] == 'X' else np.array([0., 2.5, 0.])
            if not all(np.allclose(row[name], value, rtol=0, atol=1e-12)
                       for name, value in [('centre_mm', center), ('plus_mm', center+offset), ('minus_mm', center-offset)]):
                raise ValueError('Native probe center and/or tip endpoints differ')
            seen.add(key)
            all_frequencies.update(item['frequency_Hz'] for item in row['spectrum'])
            predictions.append(probe_prediction(row, config, illustrative_one_pole, include_plots))
        provenance = probe['provenance']
        primary_candidate = condition['id'].removesuffix('-'+waveform)+'-square_3h'
        if provenance['source_candidate_id'] not in (condition['id'], primary_candidate):
            raise ValueError('Native probe candidate provenance differs from condition identity')
        reports.append(dict(candidate_id=condition['id'], waveform=waveform,
            source_run_id=provenance['source_run_id'], source_condition_id=provenance['source_condition_id'],
            native_provenance=provenance, source_Vpp_per_output=condition['source_Vpp_per_output'],
            coordinate_system=probe['coordinate_system'], measurement_grid=probe['measurement_grid'],
            complete_probes=len(predictions), probes=predictions))
    if any(sha(path) != expected for path, expected in input_hashes.items()):
        raise ValueError('Native/config input changed during read-only instrument prediction')
    return dict(schema='task1-instrument-prediction-v1', status='unloaded_prediction_and_nominal_instrument_conversion',
        generated_utc=datetime.now(timezone.utc).isoformat(), case_id=summary['id'],
        summary_path=str(summary_path), summary_sha256=sha(summary_path), probes_sha256=sha(probes_path),
        instrument_config_path=str(config_path), instrument_config_sha256=sha(config_path),
        predictor_sha256=sha(__file__), waveform_helper_sha256=sha(ROOT/'tools/task1_waveform_check.py'),
        input_sha256=input_hashes,
        source_run_context=source_run_context,
        native_source_metadata=dict(mesh=summary.get('mesh_metadata'),
            source_normalization=summary.get('source_normalization'),
            native_postprocessor_sha256=summary.get('postprocessor_sha256'),
            input_manifest_sha256=summary.get('input_manifest_sha256'),
            numerical_gate_status=summary.get('validation_gate_status')),
        hardware_provenance=config['provenance'], actual_hardware_settings_verified=False,
        input_network_frequency_response=[input_admittances(frequency, config) for frequency in sorted(all_frequencies)],
        recommended_start_configuration=config['recommended_start_configuration'],
        optional_one_pole_assumption_enabled=illustrative_one_pole,
        actual_loaded_prediction=loading_prediction(),
        scope_bandwidth=dict(actual_option_Hz=None, user_possible_options_Hz=config['scope']['possible_bandwidth_options_Hz']),
        conditions=reports, new_PDE=0, original_native_inputs_unchanged=True,
        limitations=['Bandwidth numbers alone do not specify the actual complex instrument transfer function.',
            'Probe 8Mohm/3.5pF differential specification is derived from two 4Mohm/7pF ground shunts; never add both.',
            'Scope 1Mohm/16pF is downstream of the probe; it is not an extra phantom shunt.',
            'Only differential open-circuit potentials are saved here. Two tip-to-ground potentials and a native 2x2 port impedance are missing.',
            'Nominal conversions and an assumed filter do not validate probe loading, detectability, common-mode rejection, noise, calibration, activation or safety.',
            'Existing saved results remain unloaded and experimentally unvalidated.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--waveform', choices=['square_3h', 'sine', 'triangle_3h'], default='square_3h')
    parser.add_argument('--illustrative-one-pole', action='store_true')
    parser.add_argument('--include-time-plots', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    summary, output = args.summary.resolve(), args.output.resolve()
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run, eligibility = validate_actual_request(summary, output)
        check_disk_reserve(output)
        ledger_path = ROOT/'runtime/task1-budget.json'
        ledger = read(ledger_path)
        if ledger['limit_seconds'] != 6600:
            raise ValueError('Existing global 6600-second budget must be preserved')
        seconds = min(120., 6600-ledger['spent_seconds'])
        if seconds <= 0:
            raise ValueError('No remaining existing research time budget')
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        output.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        def timeout(signum, frame):
            raise TimeoutError('Instrument prediction exceeded finite 120s/remaining global budget')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        status = 'failed'
        try:
            result = build_prediction(summary, args.config, args.waveform, args.illustrative_one_pole,
                                      args.include_time_plots, start+seconds)
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            if peak > 3*1024**3:
                raise MemoryError('Instrument audit exceeded existing 3GiB RSS limit')
            result['resources'] = dict(wall_seconds=time.monotonic()-start, max_seconds=seconds,
                peak_process_RSS_bytes=peak, CPU_count=1, simultaneous_jobs=1)
            result['source_case_eligibility'] = eligibility
            _, final_eligibility = validate_actual_request(summary, output)
            if eligibility != final_eligibility:
                raise ValueError('Completed source case eligibility changed during prediction')
            payload = json.dumps(result, indent=2, allow_nan=False)+'\n'
            check_disk_reserve(output, len(payload.encode('utf-8')))
            with output.open('x') as stream:
                stream.write(payload)
            status = result['status']
            print(json.dumps(dict(status=status, output=str(output), conditions=len(result['conditions']),
                probes=sum(condition['complete_probes'] for condition in result['conditions']),
                true_loaded_prediction='held_missing_native_port_response')))
        except Exception as error:
            failure = output.with_name(output.stem+'.failure.json')
            failure_payload = json.dumps(dict(status='failed', error_type=type(error).__name__, error=str(error),
                new_PDE=0, original_inputs_preserved=True), indent=2)+'\n'
            try:
                check_disk_reserve(failure, len(failure_payload.encode('utf-8')))
                with failure.open('x') as stream:
                    stream.write(failure_payload)
            except Exception as evidence_error:
                error.add_note('Failure sidecar was not written: '+str(evidence_error))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-start
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=run.name, stage='instrument_unloaded_prediction',
                seconds=elapsed, status=status, finished_utc=datetime.now(timezone.utc).isoformat()))
            temporary = ledger_path.with_name('task1-budget.json.partial')
            temporary.write_text(json.dumps(ledger, indent=2)+'\n')
            temporary.replace(ledger_path)


if __name__ == '__main__':
    main()
