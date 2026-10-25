"""Pure scalar-projection mathematics for a paper-inspired field display.

A complex number here is a PEAK phasor of E projected onto one fixed real spatial
unit direction. It is not a complex vector or a directional-maximum algorithm.
The two-tone modulation is the envelope's peak-to-trough variation; the carrier
RMS is a separate quantity. Import performs no I/O, validation run or data read.
"""
from __future__ import annotations

import math

import numpy as np

VALIDATION_RELATIVE_TOLERANCE = 1e-10
VALIDATION_ABSOLUTE_TOLERANCE = 1e-10
DENSE_PHASE_SAMPLES = 10001


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _phasors(a, b):
    """Use ordinary NumPy broadcasting; inputs must be finite peak phasors."""
    a, b = np.broadcast_arrays(np.asarray(a, dtype=np.complex128),
                               np.asarray(b, dtype=np.complex128))
    _require(np.isfinite(a).all() and np.isfinite(b).all(), 'Finite scalar peak phasors required')
    return a, b


def _result(value):
    value = np.asarray(value)
    _require(np.isfinite(value).all(), 'Finite mathematical result required')
    return float(value) if value.ndim == 0 else value


def directional_modulation(a, b):
    """Envelope max-min for two DISTINCT tones projected onto a fixed direction.

    For finite complex peak scalar projections a,b, max envelope=|a|+|b| and min
    envelope=||a|-|b|| over a complete beat. Their difference is2min(|a|,|b|).
    The phases determine when the extrema occur; taking only real components is
    invalid. This is not the maximum over all spatial directions or a threshold.
    """
    a, b = _phasors(a, b)
    return _result(2*np.minimum(np.abs(a), np.abs(b)))


def _oscillation(a, b, t, f1, f2):
    a, b = _phasors(a, b)
    t = np.asarray(t, dtype=np.float64)
    _require(np.isfinite(t).all() and np.isscalar(f1) and np.isscalar(f2) and
             math.isfinite(float(f1)) and math.isfinite(float(f2)) and float(f1)>0 and float(f2)>0,
             'Finite time and positive finite carrier frequencies required')
    # NumPy broadcasting is explicit; callers wanting an outer time×space grid
    # should add those axes themselves. No heuristic reshaping occurs here.
    return a*np.exp(2j*math.pi*float(f1)*t)+b*np.exp(2j*math.pi*float(f2)*t)


def envelope(a, b, t, f1=3000, f2=3030):
    """Magnitude of the actual two-tone analytic scalar waveform [same units as E]."""
    return _result(np.abs(_oscillation(a,b,t,f1,f2)))


def signal(a, b, t, f1=3000, f2=3030):
    """Instantaneous scalar E: real(a exp(+j2πf1t)+b exp(+j2πf2t))."""
    return _result(np.real(_oscillation(a,b,t,f1,f2)))


def distinct_tone_rms(a, b):
    """RMS of scalar projections at DISTINCT nonzero frequencies over full periods.

    Coherent contributions at a shared frequency must be summed FIRST; they must
    not be passed as a,b to this distinct-tone energy expression.
    """
    a,b = _phasors(a,b)
    return _result(np.sqrt((np.abs(a)**2+np.abs(b)**2)/2))


def same_frequency_rms(a, b):
    """Coherent same-frequency scalar RMS, used to expose cancellation explicitly."""
    a,b = _phasors(a,b)
    return _result(np.abs(a+b)/math.sqrt(2))


def _envelope_relative_phase(a, b, phase):
    """Factor out carrier1's unit rotation; numerically isolate the beat phase."""
    return np.abs(a+b*np.exp(1j*np.asarray(phase, dtype=np.float64)))


def mathematical_validation():
    """Small public analytic/waveform proof; caller owns its execution budget.

    We report a10001-point uniform beat grid separately, without treating its
    missed extrema as formula error. Adding the analytic alignment/opposition
    phase points tests the actual complex envelope extrema against the formula
    using the fixed tolerances declared above. No data-dependent gate is chosen.
    """
    cases = (
        ('equal_in_phase',1+0j,1+0j),
        ('unequal_in_phase',2+0j,.5+0j),
        ('quadrature_equal',1+0j,1j),
        ('arbitrary_complex_phase',1.2-.7j,-.4+1.1j),
        ('one_carrier_only',3-4j,0j),
        ('other_carrier_only',0j,-2+1j),
        ('both_zero',0j,0j),
    )
    dense_phase = np.linspace(0,2*math.pi,DENSE_PHASE_SAMPLES,endpoint=False)
    rows = []
    for label,a,b in cases:
        aa,bb = abs(a),abs(b)
        expected_max,expected_min = aa+bb,abs(aa-bb)
        expected_mod = float(directional_modulation(a,b))
        dense = _envelope_relative_phase(a,b,dense_phase)
        # Zero-amplitude cases are constant in beat phase; phase0 is sufficient.
        aligned = float((np.angle(a)-np.angle(b))%(2*math.pi)) if aa and bb else 0.
        opposed = float((aligned+math.pi)%(2*math.pi))
        with_exact_phase = np.r_[dense,_envelope_relative_phase(a,b,[aligned,opposed])]
        actual_max = float(with_exact_phase.max()); actual_min = float(with_exact_phase.min())
        actual_mod = actual_max-actual_min
        comparisons = []
        for name,actual,expected in (('envelope_max',actual_max,expected_max),
                                     ('envelope_min',actual_min,expected_min),
                                     ('envelope_peak_to_trough',actual_mod,expected_mod)):
            limit = VALIDATION_ABSOLUTE_TOLERANCE+VALIDATION_RELATIVE_TOLERANCE*abs(expected)
            passed = abs(actual-expected)<=limit
            _require(passed,'Fixed analytic complex-envelope validation failed: '+label+'/'+name)
            comparisons.append(dict(quantity=name,actual=actual,expected=expected,
                                    absolute_error=abs(actual-expected),absolute_error_limit=limit,passed=bool(passed)))
        # The scalar total carrier RMS is an energy reference, not modulation.
        rms = float(distinct_tone_rms(a,b))
        # Over1/30s, carriers3000/3030 complete100/101 periods.4096uniform
        # samples resolve both sinusoids and integrate these products exactly
        # apart from floating-point roundoff, with no envelope-extrema claim.
        time = np.arange(4096,dtype=float)/(4096*30.)
        wave_rms = float(np.sqrt(np.mean(np.asarray(signal(a,b,time))**2)))
        rms_limit = VALIDATION_ABSOLUTE_TOLERANCE+VALIDATION_RELATIVE_TOLERANCE*abs(rms)
        _require(abs(wave_rms-rms)<=rms_limit,'Fixed actual-waveform RMS validation failed: '+label)
        rows.append(dict(label=label,a_peak=dict(real=a.real,imaginary=a.imag),b_peak=dict(real=b.real,imaginary=b.imag),
            frequencies_Hz=[3000,3030],alignment_relative_phase_rad=aligned,opposition_relative_phase_rad=opposed,
            actual_complex_envelope_checks=comparisons,
            dense_grid_only=dict(phase_samples=DENSE_PHASE_SAMPLES,phase_endpoint_included=False,
                minimum=float(dense.min()),maximum=float(dense.max()),peak_to_trough=float(dense.max()-dense.min()),
                modulation_absolute_error=float(abs(dense.max()-dense.min()-expected_mod)),
                status='diagnostic_not_gated_sampled_extrema_may_be_missed'),
            scalar_carrier_RMS=dict(analytic=rms,time_waveform_RMS=wave_rms,absolute_error=abs(wave_rms-rms),
                absolute_error_limit=rms_limit,sample_count=4096,window_seconds=1/30.,passed=True),
            envelope_modulation=expected_mod,passed=True))
    invalid_real_only = 2*min(abs((1+0j).real),abs((1j).real))
    valid_quadrature = float(directional_modulation(1+0j,1j))
    one_tone_mod = float(directional_modulation(3-4j,0j)); one_tone_rms = float(distinct_tone_rms(3-4j,0j))
    canceled_coherent_rms = float(same_frequency_rms(1,-1))
    wrongly_incoherent_rms = float(distinct_tone_rms(1,-1))
    _require(valid_quadrature==2 and invalid_real_only==0 and one_tone_mod==0 and one_tone_rms>0 and
             canceled_coherent_rms==0 and wrongly_incoherent_rms==1,
             'Scalar projection, one-carrier and same-frequency distinctions failed')
    return dict(schema='task1-complex-scalar-envelope-mathematics-v1',status='passed',
        scope='Synthetic analytic scalar projections only; no native field, new PDE or biological interpretation',
        input_convention='Complex peak phasors with+jomega_t; one fixed real spatial projection direction',
        formula='two-distinct-tone envelope max-min=2min(|a|,|b|)',
        relative_tolerance=VALIDATION_RELATIVE_TOLERANCE,absolute_tolerance=VALIDATION_ABSOLUTE_TOLERANCE,
        exact_phase_augmented_extrema_gate=True,dense_grid_extrema_gated=False,cases=rows,
        quadrature_counterexample=dict(a_peak=dict(real=1.,imaginary=0.),b_peak=dict(real=0.,imaginary=1.),
            correct_complex_scalar_modulation=valid_quadrature,invalid_real_components_only_result=invalid_real_only,
            interpretation='Dropping phasor imaginary parts is invalid; this does not invalidate real-field paper derivations'),
        single_carrier_control=dict(envelope_modulation=one_tone_mod,scalar_carrier_RMS=one_tone_rms,
            interpretation='Zero beat-envelope variation can coexist with nonzero field RMS'),
        same_frequency_control=dict(a_peak=1.,b_peak=-1.,coherent_RMS=canceled_coherent_rms,
            incorrectly_treated_as_distinct_tones_RMS=wrongly_incoherent_rms,
            interpretation='Sum outputs coherently at each frequency before computing RMS'),
        new_PDE=0,native_data_read=False,activation_validated=False,safety_validated=False)
