"""Pure saved-phasor output-power bookkeeping; no files, native arrays or PDE."""
import math

RELATIVE_TOLERANCE = 2e-12
ABSOLUTE_TOLERANCE = 1e-15


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _number(value):
    _require(type(value) in (int, float) and math.isfinite(value), 'Finite numeric phasor/scalar required')
    return float(value)


def _spectrum(rows, unit):
    result = {}
    _require(isinstance(rows, list) and bool(rows), 'Nonempty saved frequency spectrum required')
    for row in rows:
        frequency = row['frequency_Hz']
        _require(type(frequency) is int and frequency > 0 and frequency not in result, 'Unique positive integer-Hz frequencies required')
        real, imaginary = row['real_'+unit], row['imaginary_'+unit]
        _require(len(real) == len(imaginary) == 2, 'Exactly two physical source output phasors required')
        result[frequency] = [complex(_number(a), _number(b)) for a, b in zip(real, imaginary)]
    return result


def output_power_evidence(metrics, *, amplitude_scale=1.):
    """Recover signed per-output powers from completed saved peak/+jwt spectra.

    Validate the unscaled aggregate against saved powers/current-vector first.
    A common amplitude factor then scales every actual output phasor/current
    linearly and every power quadratically. Frequencies are never summed before
    RMS/power evaluation; negative delivered power is retained verbatim.
    """
    scale = _number(amplitude_scale)
    _require(scale >= 0, 'Nonnegative common amplitude scale required')
    currents = _spectrum(metrics['source_current_spectrum'], 'A')
    voltages = _spectrum(metrics['loaded_metal_voltage_spectrum'], 'V')
    _require(set(currents) == set(voltages), 'Current and metal-voltage frequency sets differ')
    outputs = [dict(output_index=i, ideal_source_power_W=0., metal_delivered_power_W=0.,
        source_resistor_loss_W=0., current_squared_A2=0., spectrum=[]) for i in range(2)]
    for frequency in sorted(currents):
        for index, row in enumerate(outputs):
            current, metal = currents[frequency][index], voltages[frequency][index]
            ideal = metal+50.*current
            p_source = .5*(ideal*current.conjugate()).real
            p_metal = .5*(metal*current.conjugate()).real
            p_resistor = 25.*abs(current)**2
            _require(all(math.isfinite(v) for v in (p_source, p_metal, p_resistor)), 'Nonfinite phasor product')
            row['ideal_source_power_W'] += p_source
            row['metal_delivered_power_W'] += p_metal
            row['source_resistor_loss_W'] += p_resistor
            row['current_squared_A2'] += abs(current)**2/2
            row['spectrum'].append(dict(frequency_Hz=frequency,
                current_peak_A=dict(real=current.real*scale, imaginary=current.imag*scale),
                metal_voltage_peak_V=dict(real=metal.real*scale, imaginary=metal.imag*scale),
                ideal_voltage_peak_V=dict(real=ideal.real*scale, imaginary=ideal.imag*scale),
                ideal_source_power_W=p_source*scale**2,
                metal_delivered_power_W=p_metal*scale**2, source_resistor_loss_W=p_resistor*scale**2))
    checks = {}
    actual = dict(source_power_W=sum(row['ideal_source_power_W'] for row in outputs),
        source_resistor_power_W=sum(row['source_resistor_loss_W'] for row in outputs))
    actual['source_current_RMS_by_output_mA'] = [math.sqrt(row['current_squared_A2'])*1000 for row in outputs]
    for key, computed in actual.items():
        saved = metrics[key]
        if isinstance(computed, list):
            _require(isinstance(saved, list) and len(saved) == 2, 'Saved output RMS vector dimension differs')
        values = list(zip(computed, saved)) if isinstance(computed, list) else [(computed, saved)]
        entries = []
        for value, expected in values:
            expected = _number(expected)
            difference = abs(value-expected)
            entries.append(dict(recomputed=value, saved=expected, absolute_difference=difference,
                passed=difference <= RELATIVE_TOLERANCE*abs(expected)+ABSOLUTE_TOLERANCE))
        checks[key] = entries
    _require(all(entry['passed'] for entries in checks.values() for entry in entries), 'Saved output powers/current RMS do not match phasor reconstruction')
    for row in outputs:
        row['current_RMS_A'] = math.sqrt(row.pop('current_squared_A2'))*scale
        row['current_RMS_mA'] = row['current_RMS_A']*1000
        for key in ('ideal_source_power_W', 'metal_delivered_power_W', 'source_resistor_loss_W'):
            row[key] *= scale**2
    return dict(schema='task1-output-power-evidence-v1', common_amplitude_scale=scale,
        source_resistance_ohm=50., outputs=outputs,
        totals={key:sum(row[key] for row in outputs) for key in
            ('ideal_source_power_W', 'metal_delivered_power_W', 'source_resistor_loss_W')},
        unscaled_saved_metric_verification=checks,
        verification_tolerance=dict(relative=RELATIVE_TOLERANCE, absolute=ABSOLUTE_TOLERANCE,
            units='W for power and mA for stored output current vector'),
        definition='Peak phasors: Videal=Vmetal+50I; P=.5Re(V*conj(I)); resistor=50|I|^2/2; RMS=sqrt(sum_f|I|^2/2)',
        signed_power_scope='Metal delivered power includes passive-output absorption; no negative value clamped',
        current_scope='Each physical source output RMS over distinct frequencies; not common-GND return current',
        new_PDE=0, numerical_or_experimental_validation_promoted=False)
