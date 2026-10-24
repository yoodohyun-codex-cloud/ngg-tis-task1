"""Pure metadata/math comparison of current best1 with a true one-output pair.

No CLI, files, native arrays, worker, API, ledger or Git operations. Consumed
frozen helpers were inspected: their imports define functions/constants only
and do not read research inputs or execute scientific calculations.
"""
from __future__ import annotations

import copy
import math

import task1_rounded_single_pair as frozen

SCHEMA = 'task1-best1-single-pair-comparison-v1'
REFERENCE_ID = 'rounded-expand-f35b23a22166'
REFERENCE_CASE = 'rounded-fullface225-xy80'
PRIMARY = 'primary_r5_depth15_20'
MODES = ('raw_1Vpp', 'skin_contact_only')
BURDEN_SOURCE_KEYS = {
    'surface_J_RMS_max_A_m2': 'contact_J_RMS_max_A_m2',
    'surface_J_RMS_p95_A_m2': 'contact_J_RMS_p95_A_m2',
    'contact_voltage_RMS_max_V': 'contact_voltage_RMS_max_V',
    'SC_power_W': 'SC_power_W',
    'contact_power_W': 'contact_power_W',
    'source_power_W': 'source_power_W',
    'bulk_skin_J_vector_RMS_max_A_m2': 'bulk_skin_J_RMS_max_A_m2',
    'bulk_skin_J_vector_RMS_p95_A_m2': 'bulk_skin_J_RMS_p95_A_m2',
    'skin_SC_plus_dermis_power_W': 'skin_SC_plus_dermis_power_W',
}
BURDEN_DEFINITIONS = {
    'surface_J_RMS_max_A_m2': 'Contact-normal patch current-density RMS maximum; not bulk vector J',
    'surface_J_RMS_p95_A_m2': 'Contact-area weighted contact-normal patch current-density RMS P95',
    'contact_voltage_RMS_max_V': 'Maximum electrode-interface voltage RMS',
    'SC_power_W': 'Stratum-corneum tissue loss only',
    'contact_power_W': 'Electrode-interface real loss only',
    'source_power_W': 'Ideal-source average real power including tissue, contact and source-resistor losses',
    'bulk_skin_J_vector_RMS_max_A_m2': 'SC plus dermis volume vector-current-density RMS maximum',
    'bulk_skin_J_vector_RMS_p95_A_m2': 'SC plus dermis volume-weighted vector-current-density RMS P95',
    'skin_SC_plus_dermis_power_W': 'SC plus dermis tissue loss; excludes electrode-interface loss',
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(value, *, positive=False):
    require(type(value) in (int, float) and math.isfinite(value) and
            (value > 0 if positive else value >= 0), 'Finite nonnegative scalar required')
    return float(value)


def intervals(value):
    require(isinstance(value, (list, tuple)) and len(value) == 2,
            'Two physical-output whole-waveform Vpp intervals required')
    result = []
    for pair in value:
        require(isinstance(pair, (list, tuple)) and len(pair) == 2,
                'Source Vpp interval requires lower/upper endpoints')
        lo, hi = (number(x, positive=True) for x in pair)
        require(lo <= hi, 'Ordered positive source Vpp interval required')
        result.append([lo, hi])
    return result


def canonical_single_burdens(raw):
    return {key: number(raw[source]) for key, source in BURDEN_SOURCE_KEYS.items()}


def ratio(numerator, denominator):
    return numerator / denominator if denominator > 0 else None


def inverse_interval_ratio(numerator, interval):
    return dict(lower=numerator / interval[1], upper=numerator / interval[0])


def build_comparison(reference_condition, single_unit, single_electrical_metrics, raw_probe=None):
    """Return new f35-specific matches; never relabel historical C1 target rows.

    Arguments are already parsed, externally source-verified metadata. This
    function validates physical counts and algebra, but cannot certify hashes,
    grid identity, model provenance, numerical convergence or actual hardware.
    """
    ref, unit = reference_condition, single_unit
    require(ref.get('id') == REFERENCE_ID and ref.get('source_case_id') == REFERENCE_CASE,
            'Current f35 rounded best1 identity required; historical e7 rows cannot be relabelled')
    circuit = ref['source_circuit']
    require(circuit.get('n_pads') == 4 and circuit.get('n_outputs') == 2 and
            circuit.get('n_return_nodes') == 1 and circuit.get('source_resistance_ohm') == 50 and
            circuit.get('pad_to_node') == {'0': 'out0', '1': 'out1', '2': 'GND', '3': 'GND'},
            'Reference must retain four physical pads, two outputs and common GND/50ohm')
    pair = unit['circuit']
    require(unit.get('case_id') == 'centered-square15-C1-y0-xy80-f3000' and
            pair.get('n_pads') == 2 and pair.get('n_outputs') == 1 and
            pair.get('n_return_nodes') == 1 and pair.get('source_resistance_ohm') == 50 and
            pair.get('pad_to_node') == {'0': 'out0', '1': 'GND'} and
            unit.get('frequency_Hz') == 3000 and unit.get('raw_source_Vpp') == 1.,
            'C1 must be an actual one-output source/return pair at 1Vpp/3000Hz; disabling a four-pad output is invalid')
    raw = unit['raw_burdens']
    canonical_single_burdens(raw)
    unit_centre = number(unit['raw_centre20_E_RMS_V_m'], positive=True)
    unit_roi = number(unit['raw_ROI_energy_RMS_V_m'], positive=True)
    centre = number(ref['electrical_metrics']['target20_total_E_RMS_V_m'], positive=True)
    raw_vpp = intervals(ref['source_waveform']['source_Vpp_intervals_V'])
    # The frozen power helper validates actual one-output current/metal phasors
    # and source/resistor powers, without coherent summation across frequencies.
    unit_power = frozen.single_signed_power(single_electrical_metrics)
    require(any(row['frequency_Hz'] == 3000 for row in single_electrical_metrics['source_current_spectrum']) and
            all(row['frequency_Hz'] == 3000 or all(x == 0 for key in ('real_A', 'imaginary_A') for x in row[key])
                for row in single_electrical_metrics['source_current_spectrum']) and
            all(row['frequency_Hz'] == 3000 or all(x == 0 for key in ('real_V', 'imaginary_V') for x in row[key])
                for row in single_electrical_metrics['loaded_metal_voltage_spectrum']),
            'Only one actual 3000Hz sinusoid may be reused for C1')
    for key, value in (('source_power_W', unit_power['ideal_source_power_W']),
                       ('source_resistor_power_W', unit_power['source_resistor_loss_W']),
                       ('source_current_RMS_mA', unit_power['output_current_RMS_mA'])):
        require(math.isclose(number(raw[key]), value, rel_tol=1e-10, abs_tol=1e-14),
                'C1 unit burden and saved electrical metrics disagree: ' + key)
    current_row = next(row for row in single_electrical_metrics['source_current_spectrum']
                       if row['frequency_Hz'] == 3000)
    metal_row = next(row for row in single_electrical_metrics['loaded_metal_voltage_spectrum']
                     if row['frequency_Hz'] == 3000)
    peak_current = complex(current_row['real_A'][0], current_row['imaginary_A'][0])
    metal_voltage = complex(metal_row['real_V'][0], metal_row['imaginary_V'][0])
    require(math.isclose(2 * abs(metal_voltage + 50 * peak_current), 1., rel_tol=1e-10, abs_tol=1e-12),
            'C1 actual ideal-source phasor must represent the declared whole-waveform 1Vpp')
    require(math.isclose(number(raw['source_current_peak_mA']), abs(peak_current) * 1000,
                         rel_tol=1e-10, abs_tol=1e-12) and
            math.isclose(number(raw['loaded_metal_Vpp']), 2 * abs(metal_voltage),
                         rel_tol=1e-10, abs_tol=1e-12),
            'C1 saved peak current/loaded metal Vpp differ from the actual 3000Hz phasors')
    raw_stats = ref['normalizations']['raw_1Vpp']['regions'][PRIMARY]['RMS']
    raw_roi = frozen.energy_rms_from_statistics(raw_stats)
    result_modes = {}
    for name in MODES:
        mode = ref['normalizations'][name]
        scale = number(mode['amplitude_scale'], positive=True)
        require(name != 'raw_1Vpp' or scale == 1., 'Raw mode must preserve declared source drive')
        stats = mode['regions'][PRIMARY]['RMS']
        target_roi = frozen.energy_rms_from_statistics(stats)
        require(math.isclose(stats['volume_m3'], raw_stats['volume_m3'], rel_tol=1e-12, abs_tol=1e-25) and
                math.isclose(target_roi, raw_roi * scale, rel_tol=1e-10, abs_tol=1e-12),
                'Saved weighted energy RMS and physical ROI volume must preserve common amplitude scaling')
        vpp = intervals(mode.get('actual_source_Vpp_intervals_V',
                                 [[x * scale for x in pair] for pair in raw_vpp]))
        require(all(math.isclose(x, y * scale, rel_tol=1e-10, abs_tol=1e-12)
                    for actual, original in zip(vpp, raw_vpp) for x, y in zip(actual, original)),
                'Normalized source Vpp intervals disagree with actual full-waveform common scale')
        burden = {key: number(mode['normalized_burdens'][key]) for key in BURDEN_SOURCE_KEYS}
        current = mode['source_output_RMS_by_output_mA']
        require(isinstance(current, (list, tuple)) and len(current) == 2,
                'Two actual reference-output RMS currents required')
        current = [number(x) for x in current]
        if raw_probe is None:
            matches = frozen.old.matched_single(centre * scale, target_roi, unit_centre, unit_roi, raw)
        else:
            matches = frozen.target_matches(centre * scale, target_roi, unit_centre, unit_roi, raw, raw_probe)
        output_matches = {}
        for criterion, match in matches.items():
            k = match['amplitude_scale']
            all_burdens = match['burdens']
            mapped = canonical_single_burdens(all_burdens)
            single_current = number(all_burdens['source_current_RMS_mA'])
            maximum_vpp_interval = [max(p[0] for p in vpp), max(p[1] for p in vpp)]
            row = dict(required_source_Vpp=k, amplitude_scale=k, source_peak_V=.5 * k,
                achieved_centre20_E_RMS_V_m=match['achieved_centre20_E_RMS_V_m'],
                achieved_ROI_energy_RMS_V_m=match['achieved_ROI_energy_RMS_V_m'], burdens=mapped,
                additional_burdens=copy.deepcopy(all_burdens), source_current_RMS_mA=single_current,
                source_current_peak_mA=number(all_burdens['source_current_peak_mA']),
                loaded_metal_Vpp=number(all_burdens['loaded_metal_Vpp']),
                signed_output_power_evidence=frozen.single_signed_power(single_electrical_metrics, k),
                ratios_vs_reference=dict(burdens={key: ratio(mapped[key], burden[key]) for key in mapped},
                    source_Vpp_to_max_TIS_output_interval=inverse_interval_ratio(k, maximum_vpp_interval),
                    source_Vpp_to_each_TIS_output_interval=[inverse_interval_ratio(k, p) for p in vpp],
                    current_RMS_to_each_TIS_output=[ratio(single_current, x) for x in current],
                    current_RMS_to_sum_output_RMS_bookkeeping=ratio(single_current, sum(current)),
                    output_current_sum_is_physical_common_return_current=False,
                    source_Vpp_reference='Maximum individual physical-output whole-waveform Vpp, not the sum of source Vpp'),
                fundamental_envelope_variation_V_m=0.,
                single_frequency_modulation_definition='For one frequency, each fixed real-direction analytic envelope has zero variation; electric-field RMS is nonzero and activation equivalence is not implied',
                probe_scope='Unloaded native-phi probe evidence only; actual instrument loading unverified')
            if raw_probe is not None:
                row['unloaded_probe40'] = copy.deepcopy(match['unloaded_probe40'])
            else:
                row['unloaded_probe40'] = None
                row['raw_probe_reference'] = copy.deepcopy(unit.get('unloaded_probe_reference'))
            output_matches[criterion] = row
        result_modes[name] = dict(reference_amplitude_scale=scale,
            reference_source_Vpp_intervals_V=vpp, reference_burdens=burden,
            reference_output_RMS_by_output_mA=current,
            reference_output_RMS_sum_bookkeeping_mA=sum(current),
            reference_signed_output_power_evidence=copy.deepcopy(mode.get('signed_per_output_power_evidence')),
            reference_layer_contact_source_losses_W={key: number(value) * scale**2
                for key, value in ref.get('layer_contact_source_losses', {}).get('metrics', {}).items()
                if key.endswith('_W')},
            reference_primary_RMS_statistics=copy.deepcopy(stats),
            reference_primary_maxTIS_statistics=copy.deepcopy(mode['regions'][PRIMARY].get('maxTIS')),
            target_ROI_energy_RMS_V_m=target_roi, target_centre20_E_RMS_V_m=centre * scale,
            matches=output_matches)
    return dict(schema=SCHEMA, status='calculated_unadopted',
        reference=dict(candidate_id=ref['id'], source_case_id=ref['source_case_id'],
            source_run_id=ref.get('source_run_id'), source_commit=ref.get('source_commit'),
            configuration_sha256=ref.get('configuration_sha256')),
        single_pair=dict(case_id=unit.get('case_id'), source_run_id=unit.get('source_run_id'),
            circuit=copy.deepcopy(pair), frequency_Hz=3000, raw_source_Vpp=1.,
            unit_centre20_E_RMS_V_m=unit_centre, unit_ROI_energy_RMS_V_m=unit_roi,
            physical_pad_centres_mm=copy.deepcopy(unit.get('physical_pad_centres_mm'))),
        geometry_comparison=dict(TIS_pads=4, C1_pads=2, TIS_outputs=2, C1_outputs=1,
            TIS_total_contact_area_mm2=900., C1_total_contact_area_mm2=450., same_pad_shape=False,
            TIS_shape='Rounded stepped native full-face union,225mm2 per pad',
            C1_shape='Two15x15mm square pads,225mm2 per pad including return',
            hold='Shape, pad count, return geometry and total contact footprint differ; this is not a shape-matched two-rounded-pad control'),
        ROI_definition=dict(primary_radius_mm=5., depth_from_surface_mm=[15., 20.],
            coordinate_system='Surface z=0; +z is depth; x/y horizontal',
            energy_RMS='sqrt(weighted mean(E_RMS squared)) = hypot(weighted mean(E_RMS),weighted population std(E_RMS)); not mean(E_RMS)'),
        burden_definitions=copy.deepcopy(BURDEN_DEFINITIONS), modes=result_modes,
        input_verification_scope='Caller must bind source JSON/config/grid/model/probe hashes; this pure function performs metadata and algebra checks only',
        native_array_reads=0, new_PDE=0, candidate_adopted=False, full_convergence_validated=False,
        instrument_loading_validated=False, experimentally_validated=False,
        holds=['Centre20 and ROIenergy RMS are separate matching criteria; other burdens are not simultaneously matched',
               'Single-frequency zero envelope variation is not zero field or equivalent physiological activation',
               'Ideal-source Vpp is before50ohm; loaded metal Vpp and contact voltage are distinct',
               'Output RMS sums are bookkeeping, not the common-GND physical return current',
               'PBS-to-skin contact, shape/edge/SC/XY/bulk convergence, source compliance and instrument loading remain unverified'])
