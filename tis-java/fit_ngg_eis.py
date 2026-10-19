"""Estimate the initial bare-NGG series resistance and subtract it from EIS.

The selected Rs+CPE fit is local to 1-10 kHz, encompassing both TIS carriers.
Rs is an effective high-frequency series resistance, not uniquely proven to
be electrolyte alone. No dry-contact validation is implied.
"""
from pathlib import Path
import json
import math
import numpy as np
from update_ngg_eis import interpolate_complex

ROOT = Path(__file__).resolve().parent


def fit_series_cpe(f, z, cutoff):
    mask = f >= cutoff
    omega, obs = 2 * np.pi * f[mask], z[mask]
    weight = 1 / np.abs(obs)
    target = np.r_[obs.real * weight, obs.imag * weight]

    def solve(n):
        basis = (1j * omega) ** (-n)
        design = np.column_stack((np.r_[weight, np.zeros(len(obs))],
                                  np.r_[basis.real * weight, basis.imag * weight]))
        rs, k = np.linalg.lstsq(design, target, rcond=None)[0]
        error = design @ np.array([rs, k]) - target
        cost = float(error @ error) if rs >= 0 and k > 0 else math.inf
        return cost, float(rs), float(k)

    grid = np.linspace(.2, 1.0, 801)
    index = min(range(len(grid)), key=lambda i: solve(grid[i])[0])
    left, right = grid[max(index - 1, 0)], grid[min(index + 1, len(grid) - 1)]
    # A bounded scalar search after a global grid; linear coefficients solved
    # exactly for every exponent. Objective sum |Zmodel-Zobs|^2/|Zobs|^2.
    ratio = (math.sqrt(5) - 1) / 2
    for _ in range(70):
        a, b = right - ratio * (right-left), left + ratio * (right-left)
        if solve(a)[0] < solve(b)[0]: right = b
        else: left = a
    n = float((left + right) / 2)
    cost, rs, k = solve(n)
    predicted = rs + k * (1j * omega) ** (-n)
    relative = np.abs(predicted - obs) / np.abs(obs)
    return {
        "nominal_lower_frequency_Hz": cutoff,
        "actual_frequency_range_Hz": [float(f[mask].min()), float(f[mask].max())],
        "n_points": int(mask.sum()), "Rs_ohm": rs,
        "Q_S_s_power_n": 1 / k, "n": n,
        "weighted_SSE": cost,
        "relative_complex_RMS_percent": float(np.sqrt(np.mean(relative**2)) * 100),
        "relative_complex_max_percent": float(relative.max() * 100),
        "subtraction_nonnegative_real_over_full_measured_band": bool(np.all(z.real-rs >= 0)),
    }


def main():
    profile_path = ROOT / 'electrode-data/bare-ngg-eis.json'
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    sample = next(s for s in profile['spectra'] if s['state'] == 'initial')
    points = sample['points']
    f = np.array([p['frequency_Hz'] for p in points])
    z = np.array([complex(p['Z_real_ohm'], p['Z_imag_ohm']) for p in points])
    fits = [fit_series_cpe(f, z, cutoff) for cutoff in (1, 100, 500, 1000, 2000)]
    chosen = next(v for v in fits if v['nominal_lower_frequency_Hz'] == 1000)
    local = [v['Rs_ohm'] for v in fits if v['nominal_lower_frequency_Hz'] >= 500]
    rs = chosen['Rs_ohm']
    if not chosen['subtraction_nonnegative_real_over_full_measured_band']:
        raise ValueError('Selected series subtraction produces negative real impedance')
    estimated = []
    for p in points:
        re, im = p['Z_real_ohm']-rs, p['Z_imag_ohm']
        estimated.append({
            'frequency_Hz': p['frequency_Hz'], 'source_range': p['source_range'],
            'measured_real_ohm': p['Z_real_ohm'], 'measured_imag_ohm': im,
            'electrode_real_ohm': re, 'electrode_imag_ohm': im,
            'electrode_magnitude_ohm': math.hypot(re, im),
            'electrode_phase_deg': math.degrees(math.atan2(im, re)),
        })
    carriers = []
    props = ['# Initial bare NGG, estimated PBS interface surrogate for TIS.',
             '# Z_electrode = log-frequency interpolated measured Z - fitted Rs.',
             '# All Z below are lumped ohms for the measured 1 cm^2 electrode.',
             '# Java multiplies by area once; no division by two.',
             'measurement.area_m2=0.0001', f'fit.Rs_ohm={rs:.16g}',
             f'fit.Rs_low_ohm={min(local):.16g}', f'fit.Rs_high_ohm={max(local):.16g}']
    for freq in (2000, 2010):
        measured = interpolate_complex(points, freq)
        re, im = measured['Z_real_ohm']-rs, measured['Z_imag_ohm']
        carriers.append({
            'frequency_Hz': freq, 'measured_real_ohm': measured['Z_real_ohm'],
            'measured_imag_ohm': im, 'electrode_real_ohm': re,
            'electrode_imag_ohm': im, 'electrode_magnitude_ohm': math.hypot(re, im),
            'electrode_phase_deg': math.degrees(math.atan2(im, re)),
            'area_real_ohm_m2': re*1e-4, 'area_imag_ohm_m2': im*1e-4,
            'source_ranges': measured['source_ranges'],
            'bracket_frequency_Hz': measured['bracket_frequency_Hz'],
        })
        props.extend((f'measured.{freq}.real_ohm={measured["Z_real_ohm"]:.16g}',
                      f'measured.{freq}.imag_ohm={im:.16g}'))
    result = {
        'schema_version': 1, 'source_file': sample['source_file'],
        'source_sha256': sample['source_sha256'], 'source_sheet': sample['sheet'],
        'source_range': sample['source_range'], 'measurement': profile['measurement'],
        'method': 'Rs + 1/(Q*(j*2*pi*f)^n), relative-complex least squares',
        'selected_fit': chosen, 'window_fits': fits,
        'selection_reason': '1-10 kHz spans both 2000/2010 Hz carriers with 8 points; the full-band single-CPE fit has systematic residuals and implies negative high-frequency real impedance after subtraction.',
        'Rs_window_sensitivity_ohm': [min(local), max(local)],
        'sensitivity_note': '500 Hz, 1 kHz, 2 kHz lower cutoffs; model/window sensitivity, not a confidence interval.',
        'boundary_method': 'Subtract the selected frequency-independent real Rs from measured complex Z, interpolate real and imaginary parts versus log(f), then multiply by the exposed area.',
        'carriers': carriers, 'estimated_spectrum': estimated,
        'limitations': [
            'Rs is an effective series term; lead, film, or spreading resistance cannot be uniquely separated from electrolyte resistance with these data alone.',
            'No high-frequency intercept was directly reached; 10 kHz still has a nonzero imaginary part.',
            'The CPE model is local to the selected band and is not asserted to explain the entire spectrum.',
            'PBS interface impedance is used as a dry NGG-SC boundary surrogate by user request, not as validated dry-contact impedance.',
            'No additional dry-contact resistance is added; this is an optimistic contact assumption.',
            'Tissue dielectric properties and common-ground topology retain previous assumptions.',
        ],
        'reference': 'https://www.gamry.com/application-notes/eis/basics-of-electrochemical-impedance-spectroscopy',
    }
    path = ROOT / 'electrode-data/bare-ngg-initial-fit.json'
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    (ROOT/'electrode-data/bare-ngg-initial.properties').write_text('\n'.join(props)+'\n', encoding='ascii')
    print(json.dumps({'Rs_ohm': rs, 'fit_RMS_percent': chosen['relative_complex_RMS_percent'],
                      'Rs_sensitivity': [min(local), max(local)], 'carriers': carriers}, indent=2))
    return result


if __name__ == '__main__':
    main()
