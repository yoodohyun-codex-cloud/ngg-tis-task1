"""Separate, voltage-unbounded engineering comparison of one pair and TIS.

All functions only consume existing bases/rows.  They never solve a PDE, mutate
the exploration run, cap voltage at 1 Vpp, or infer physiological equivalence.
"""
from pathlib import Path
import hashlib
import json
import math

import numpy as np
from explore_amplitude import peak_bounds
from explore_tis import MATERIALS, WAVES, design_frequencies
from update_ngg_eis import interpolate_complex


SCHEMA_VERSION = 1
LINEAR = ('target20_total_E_RMS_V_m', 'target20_modulation_V_m',
          'surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2',
          'contact_voltage_RMS_max_V', 'charge_excursion_upper_mC_cm2',
          'max_source_current_RMS_mA', 'max_source_current_peak_lower_mA',
          'max_source_current_peak_upper_mA', 'max_source_load_voltage_RMS_V',
          'max_source_load_voltage_peak_lower_V', 'max_source_load_voltage_peak_upper_V',
          'max_source_load_voltage_Vpp_lower_V', 'max_source_load_voltage_Vpp_upper_V')
QUADRATIC = ('SC_power_W', 'contact_power_W', 'skin_power_W',
             'source_power_W', 'tissue_contact_power_W')
ARRAY_METRICS = ('source_current_RMS_by_output_mA',
                 'source_current_peak_lower_by_output_mA',
                 'source_current_peak_upper_by_output_mA',
                 'source_load_voltage_RMS_by_output_V',
                 'source_load_voltage_peak_lower_by_output_V',
                 'source_load_voltage_peak_upper_by_output_V',
                 'source_load_voltage_Vpp_lower_by_output_V',
                 'source_load_voltage_Vpp_upper_by_output_V')
BURDEN = ('surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2',
          'contact_voltage_RMS_max_V', 'SC_power_W', 'contact_power_W',
          'skin_power_W', 'source_power_W', 'max_source_current_RMS_mA')
LIMITS = [
    'Primary match is actual20mm total vector E RMS, not fundamental envelope width.',
    'One pair means two pads and one physical output; its TIS envelope width is zero.',
    'TIS1Vpp/output anchors remain unchanged. Sweep scaling is a separate engineering comparison.',
    'Numerical required open-circuit Vpp is not capped at1Vpp; instrument voltage/current compliance is unverified.',
    'Fixed small-signal PBS interface extrapolation does not establish large-amplitude linearity, heating or safety.',
    'Matching total E RMS does not match waveform, neural activation, spatial selectivity or diaphragm recruitment.',
    'Pad size/total area and layout may differ and are explicitly disclosed, not normalized away.',
    'ProbeVpp is an ideal, unattenuated differential tip-input prediction; actual probe model, connection and scope settings remain unverified.',
    'Surface maxima and p95 retain original mesh limitations; no safety threshold or CV-derived CIC is imposed.']
PROBE_ASSUMPTIONS = {
    'quantity': 'differential probe tip-input voltage, signal metal terminal minus common return GND',
    'connection_status': 'provisional default; actual probe model and connection points not yet supplied',
    'ideal_high_impedance_no_additional_loading': True,
    'actual_hardware_model': None, 'actual_connection_confirmed': False,
    'input_R_ohm': None, 'input_C_F': None, 'bandwidth_Hz': None,
    'probe_attenuation': None, 'scope_input_ohm': None, 'scope_probe_factor': None,
    'scope_display_voltage_prediction': 'unavailable without actual hardware/settings',
    'source_vs_tip': 'command open-circuit sourceVpp and loaded differential tipVpp are distinct',
    'not_instrument_calibration': True}


class CacheUnavailable(RuntimeError):
    pass


def loaded_terminal_vpp_bounds(frequencies, voltages):
    """Full-period max-minus-min brackets for peak complex voltage phasors.

    The sampled range is a lower bound.  Each extremum can lie dt/2 from its
    nearest sample; the sum of the two D2*dt²/8 errors bounds the range error.
    It is generally incorrect to substitute twice the absolute waveform peak.
    """
    frequencies, voltages = np.asarray(frequencies, float), np.asarray(voltages, complex)
    if voltages.ndim != 2 or len(frequencies) != len(voltages):
        raise ValueError('Expected frequency-by-output voltage phasors')
    if not np.isfinite(voltages).all() or not np.isfinite(frequencies).all():
        raise ValueError('Nonfinite loaded-voltage spectrum')
    if np.any(frequencies <= 0) or not np.array_equal(frequencies, np.round(frequencies)):
        raise ValueError('Loaded-voltage period requires positive integer Hz')
    active = np.any(abs(voltages) > 0, axis=1)
    frequencies, voltages = frequencies[active].astype(np.int64), voltages[active]
    if not len(frequencies):
        zeros = np.zeros(voltages.shape[1])
        return zeros, zeros, {'period_s': None, 'samples': 0, 'dt_s': None,
                              'quantity': 'full-period maximum minus minimum'}
    divisor = math.gcd(*frequencies.tolist())
    count = int(math.ceil(64*int(frequencies.max())/divisor))
    period, dt = 1./divisor, 1./divisor/count
    time = np.arange(count)*dt
    waveform = np.zeros((count, voltages.shape[1]))
    for f, voltage in zip(frequencies, voltages):
        waveform += np.real(np.exp(2j*np.pi*f*time[:, None])*voltage)
    lower = waveform.max(axis=0)-waveform.min(axis=0)
    amplitudes = np.sum(abs(voltages), axis=0)
    derivative2 = np.sum((2*np.pi*frequencies[:, None])**2*abs(voltages), axis=0)
    rounding = 64*np.finfo(float).eps*np.maximum(amplitudes, np.finfo(float).tiny)
    upper = np.maximum(lower, np.minimum(2*amplitudes+rounding,
                                        lower+derivative2*dt**2/4+rounding))
    return lower, upper, {
        'period_s': period, 'samples': count, 'dt_s': dt,
        'quantity': 'full-period maximum minus minimum',
        'positive_exponent_phasor_convention': 'Re(sum(Vhat_f*exp(+j2pi*f*t)))',
        'bound_method': 'sampled max-min lower; min(2*sum(abs(Vhat)), lower+sum((2*pi*f)^2*abs(Vhat))*dt^2/4) upper',
        'sampled_max_by_output_V': waveform.max(axis=0).tolist(),
        'sampled_min_by_output_V': waveform.min(axis=0).tolist()}


def _hash(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def _validate(folder, channels):
    folder = Path(folder)
    if not (folder/'BASIS_COMPLETE').is_file() or not (folder/'validation.json').is_file():
        raise CacheUnavailable('Complete validated basis unavailable: '+str(folder))
    validation = json.loads((folder/'validation.json').read_text())
    for name, limit in (('max_residual', 2e-7), ('max_power_error', 2e-7),
                         ('max_current_error', 2e-6)):
        value = float(validation[name])
        if not math.isfinite(value) or value < 0 or value > limit:
            raise ValueError('Basis numerical validation failed: '+name)
    if int(validation.get('channels', channels)) != channels:
        raise ValueError('Basis output-count mismatch')
    return validation


def _coefficients(row, frequencies):
    channels = int(row['output_channels'])
    group = np.asarray(row['carrier_group'])
    phase = np.deg2rad(row['phase_deg'])
    if group.shape != (channels,) or phase.shape != group.shape or not np.isfinite(phase).all():
        raise ValueError('Invalid output phases/groups')
    if not np.isin(group, (0, 1)).all():
        raise ValueError('Invalid carrier group')
    f0 = int(row['carrier_Hz'])
    f1 = f0+int(row.get('beat_Hz', 10))
    a1, a3 = WAVES[row['waveform']]
    result = {}
    for f in frequencies:
        if channels == 1:
            if f not in (f0, 3*f0):
                raise ValueError('Single-pair basis must use driven f and optional3f only')
            harmonic, carrier = (1 if f == f0 else 3), 0
        else:
            if f not in design_frequencies(row):
                raise ValueError('Unexpected TIS basis frequency')
            harmonic = 1 if f in (f0, f1) else 3
            carrier = 0 if f in (f0, 3*f0) else 1
        result[f] = (-1j*(group == carrier)*np.exp(1j*harmonic*phase)
                     *(a1 if harmonic == 1 else a3))
    return result


def _frequencies(row):
    if row['output_channels'] == 1:
        f = int(row['carrier_Hz'])
        return (f,) if row['waveform'] == 'sine' else (f, 3*f)
    return tuple(design_frequencies(row))


def _electrical(row, folder, frequencies=None):
    """Small source/loss matrices only; no amplitude-cache writes."""
    folder = Path(folder)
    channels = int(row['output_channels'])
    validation = _validate(folder, channels)
    frequencies = tuple(frequencies or _frequencies(row))
    coefficients = _coefficients(row, frequencies)
    currents, loaded, power_parts = [], [], np.zeros(6)
    source_power = 0.0
    hashes = {'validation.json': _hash(folder/'validation.json')}
    for f in frequencies:
        matrices = []
        for name, shape in ((f'source-{f}.bin', (channels, channels)),
                             (f'loss-{f}.bin', (6, channels, channels))):
            path = folder/name
            if not path.is_file():
                raise CacheUnavailable('Required electrical transfer matrix missing: '+str(path))
            values = np.fromfile(path, dtype='<c16')
            if values.size != math.prod(shape) or not np.isfinite(values).all():
                raise ValueError('Invalid electrical transfer matrix: '+name)
            matrices.append(values.reshape(shape))
            hashes[name] = _hash(path)
        source, loss = matrices
        if not np.allclose(loss, loss.conj().transpose(0, 2, 1), atol=1e-12):
            raise ValueError('Non-Hermitian loss matrices')
        c = coefficients[f]
        current = source@c
        parts = np.einsum('i,kij,j->k', c.conj(), loss, c).real
        expected = float(.25*np.vdot(c, current).real)
        if abs(parts.sum()-expected) > 2e-7*max(abs(expected), 1e-20):
            raise ValueError('Combined-source power conservation failed')
        if np.any(parts < -1e-13):
            raise ValueError('Negative passive-region loss')
        currents.append(current)
        loaded.append(.5*c-50*current)
        power_parts += parts
        source_power += expected
    current, voltage = np.array(currents), np.array(loaded)
    rms = np.sqrt(np.sum(abs(current)**2, axis=0)/2)*1000
    vrms = np.sqrt(np.sum(abs(voltage)**2, axis=0)/2)
    lo, hi, sampling = peak_bounds(frequencies, current)
    vlo, vhi, _ = peak_bounds(frequencies, voltage)
    vpplo, vpphi, vpp_sampling = loaded_terminal_vpp_bounds(frequencies, voltage)
    vpp_sampling['spectrum_normalization_source_Vpp'] = 1.0
    result = dict(max_source_current_RMS_mA=float(rms.max()),
                  source_current_RMS_by_output_mA=rms.tolist(),
                  source_current_peak_lower_by_output_mA=(lo*1000).tolist(),
                  source_current_peak_upper_by_output_mA=(hi*1000).tolist(),
                  max_source_current_peak_lower_mA=float(lo.max()*1000),
                  max_source_current_peak_upper_mA=float(hi.max()*1000),
                  source_load_voltage_RMS_by_output_V=vrms.tolist(),
                  max_source_load_voltage_RMS_V=float(vrms.max()),
                  source_load_voltage_peak_lower_by_output_V=vlo.tolist(),
                  source_load_voltage_peak_upper_by_output_V=vhi.tolist(),
                  max_source_load_voltage_peak_lower_V=float(vlo.max()),
                  max_source_load_voltage_peak_upper_V=float(vhi.max()),
                  source_load_voltage_Vpp_lower_by_output_V=vpplo.tolist(),
                  source_load_voltage_Vpp_upper_by_output_V=vpphi.tolist(),
                  max_source_load_voltage_Vpp_lower_V=float(vpplo.max()),
                  max_source_load_voltage_Vpp_upper_V=float(vpphi.max()),
                  source_power_W=source_power,
                  SC_power_W=float(power_parts[0]),
                  contact_power_W=float(power_parts[4]),
                  skin_power_W=float(power_parts[0]+power_parts[4]),
                  tissue_contact_power_W=float(power_parts[:5].sum()))
    for key in ('max_source_current_RMS_mA',)+QUADRATIC:
        if key in row and not math.isclose(result[key], float(row[key]), rel_tol=1e-9, abs_tol=1e-14):
            raise ValueError('Saved metric differs from transfer cache: '+key)
    verification = dict(numerical_basis_passed=True, validation=validation,
                        current_RMS_matches_saved='max_source_current_RMS_mA' in row,
                        loss_power_matches_saved='source_power_W' in row,
                        input_sha256=hashes, frequencies_Hz=list(frequencies),
                        current_peak_sampling=sampling, device_compliance='unverified',
                        loaded_voltage_Vpp_sampling=vpp_sampling,
                        differential_probe_assumptions=dict(PROBE_ASSUMPTIONS),
                        loaded_voltage_definition='metal signal terminal relative to commonGND; RMS, absolutepeak bounds and independently reconstructed full-period max-min Vpp; distinct from interface voltage and command sourceVpp')
    return result, verification


def _center_weights(grid, depth=20.):
    axes = [np.unique(grid[key]) for key in ('x_mm', 'y_mm', 'z_mm')]
    brackets = []
    for axis, value in zip(axes, (0., 0., depth)):
        if len(axis) < 2 or not axis[0] <= value <= axis[-1]:
            raise ValueError('Centre20mm requires supported interpolation without extrapolation')
        lo = min(max(int(np.searchsorted(axis, value, side='right'))-1, 0), len(axis)-2)
        brackets.append(((axis[lo], axis[lo+1]), (value-axis[lo])/(axis[lo+1]-axis[lo])))
    weights = np.zeros(len(grid))
    for iz in (0, 1):
        for iy in (0, 1):
            for ix in (0, 1):
                weight = 1.0
                mask = np.ones(len(grid), bool)
                for key, (values, t), side in zip(('x_mm', 'y_mm', 'z_mm'), brackets, (ix, iy, iz)):
                    weight *= t if side else 1-t
                    mask &= grid[key] == values[side]
                if weight > 1e-14 and mask.sum() != 1:
                    raise ValueError('Centre interpolation cell is missing or duplicated')
                weights[mask] += weight
    if not math.isclose(weights.sum(), 1, abs_tol=1e-12):
        raise ValueError('Centre interpolation weights do not sum to one')
    return weights


def evaluate_single_basis(basis_dir, design, profile, wave):
    """Evaluate a genuine C1/two-pad basis at f and optional3f; never solve.

    design uses channels=1,carrier_Hz,size_mm,xy_mm,layout, optional h_mm,
    boundary_mode,config_path,id. profile is an existing EIS profile dictionary.
    The returned row is normalized to source1Vpp and can enter build_comparison.
    """
    folder = Path(basis_dir)
    if design.get('channels', 1) != 1 or len(design['xy_mm']) != 2:
        raise ValueError('A single pair means exactly two pads and one output')
    if wave not in WAVES:
        raise ValueError('Unknown band-limited waveform')
    f = int(design['carrier_Hz'])
    row = dict(id=design.get('id', folder.name+'-'+wave), basis_id=folder.name,
               layout=design['layout'], thickness_nm=profile['thickness_nm'],
               output_channels=1, pad_count=2, pad_size_mm=design['size_mm'],
               xy_mm=design['xy_mm'], waveform=wave, carrier_Hz=f, beat_Hz=0,
               carrier_group=[0], phase_deg=[0.],
               boundary_mode=design.get('boundary_mode', 'measured_minus_Rs'),
               source_R_ohm=50, target20_modulation_V_m=0.0,
               source_Vpp=1.0, coating_model_warnings=profile.get('warnings', []))
    if design.get('config_path'):
        row['config_path'] = str(design['config_path'])
    frequencies = _frequencies(row)
    electrical, verification = _electrical(row, folder, frequencies)
    grid_path = folder/'grid.csv'
    if not grid_path.is_file():
        raise CacheUnavailable('Full spatial grid unavailable')
    grid = np.genfromtxt(grid_path, delimiter=',', names=True)
    if len(grid) != verification['validation'].get('cells', len(grid)):
        raise ValueError('Full-grid cell count mismatch')
    if not all(np.isfinite(grid[k]).all() for k in ('x_mm', 'y_mm', 'z_mm')):
        raise ValueError('Nonfinite source-grid coordinates')
    x = np.unique(grid['x_mm'])
    h = float(np.median(np.diff(x)))
    if 'h_mm' in design and not math.isclose(h, float(design['h_mm']), rel_tol=1e-8):
        raise ValueError('Design/grid XY spacing mismatch')
    row['h_mm'] = float(design.get('h_mm', h))
    weights = _center_weights(grid)
    selected = np.flatnonzero(weights)
    target_rms2, j2, polar2, charge = 0., None, None, None
    contact_power_from_density, current_balance_errors = 0., []
    area_reference, contacts_reference = None, None
    coefficients = _coefficients(row, frequencies)
    for frequency in frequencies:
        field_path, contacts_path, density_path = (folder/f'{kind}-{frequency}.{ext}'
            for kind, ext in (('field', 'bin'), ('contacts', 'csv'), ('density', 'bin')))
        if not all(p.is_file() for p in (field_path, contacts_path, density_path)):
            raise CacheUnavailable('Single-pair field/contact/density cache incomplete')
        if field_path.stat().st_size != len(grid)*3*2*8:
            raise ValueError('Single-output complex E binary shape mismatch')
        field = np.memmap(field_path, dtype='<f8', mode='r', shape=(1, len(grid), 3, 2))
        for start in range(0, field.size, 1024*1024):
            if not np.isfinite(field.reshape(-1)[start:start+1024*1024]).all():
                raise ValueError('Nonfinite full complex E basis')
        data = field[0, selected]
        target = weights[selected]@(data[..., 0]+1j*data[..., 1])
        target *= coefficients[frequency][0]
        target_rms2 += float(np.vdot(target, target).real/2)
        contacts = np.atleast_1d(np.genfromtxt(contacts_path, delimiter=',', names=True))
        area = contacts['area_m2']
        if not np.isfinite(area).all() or np.any(area <= 0):
            raise ValueError('Invalid physical contact areas')
        for pad in (0, 1):
            if not math.isclose(float(area[contacts['pad'] == pad].sum()),
                                design['size_mm']**2*1e-6, rel_tol=1e-10, abs_tol=1e-14):
                raise ValueError('Single-pair electrode area is not preserved')
        if set(contacts['pad'].astype(int)) != {0, 1}:
            raise ValueError('Expected exactly two physical contact pads')
        if contacts_reference is not None and not np.array_equal(contacts, contacts_reference):
            raise ValueError('Contact ordering differs between frequencies')
        density = np.fromfile(density_path, dtype='<c16')
        if density.shape != area.shape or not np.isfinite(density).all():
            raise ValueError('Single-output density shape/values invalid')
        current_density = coefficients[frequency][0]*density
        pad_currents = [np.sum(current_density[contacts['pad'] == pad]*area[contacts['pad'] == pad])
                        for pad in (0, 1)]
        source_current = np.fromfile(folder/f'source-{frequency}.bin', dtype='<c16')[0]*coefficients[frequency][0]
        current_scale = max(sum(abs(value) for value in pad_currents), abs(source_current), 1e-30)
        current_error = max(abs(sum(pad_currents)), abs(pad_currents[0]-source_current))/current_scale
        if current_error > 2e-6:
            raise ValueError('Single-pair source/pad current conservation failed')
        current_balance_errors.append(float(current_error))
        point = interpolate_complex(profile['points'], frequency)
        rs = 0 if row['boundary_mode'] == 'full_measured' else profile['selected_fit']['Rs_ohm']
        real = point['Z_real_ohm']-rs
        if real < -1e-9:
            raise ValueError('Nonpassive measured-minus-Rs interface')
        z_area = complex(max(0, real), point['Z_imag_ohm'])*1e-4
        contact_power_from_density += float(.5*np.sum(abs(current_density)**2*z_area.real*area))
        if j2 is None:
            j2, polar2, charge = (np.zeros(len(area)) for _ in range(3))
        j2 += abs(current_density)**2/2
        polar2 += abs(current_density*z_area)**2/2
        charge += 2*abs(current_density)/(2*np.pi*frequency)*.1
        area_reference, contacts_reference = area, contacts
    jrms = np.sqrt(j2)
    if not math.isclose(contact_power_from_density, electrical['contact_power_W'],
                        rel_tol=2e-7, abs_tol=1e-15):
        raise ValueError('Profile/density contact power differs from loss basis')
    verification.update(contact_density_power_matches_loss=True,
                        contact_source_current_max_relative_error=max(current_balance_errors))
    order = np.argsort(jrms)
    index = min(np.searchsorted(np.cumsum(area_reference[order]), area_reference.sum()*.95), len(order)-1)
    row.update(electrical, target20_total_E_RMS_V_m=math.sqrt(target_rms2),
               surface_J_RMS_max_A_m2=float(jrms.max()),
               surface_J_RMS_p95_A_m2=float(jrms[order[index]]),
               contact_voltage_RMS_max_V=float(np.sqrt(polar2).max()),
               charge_excursion_upper_mC_cm2=float(charge.max()),
               basis_frequencies_Hz=list(frequencies), active_frequencies_Hz=list(frequencies),
               max_residual=verification['validation']['max_residual'],
               max_power_error=verification['validation']['max_power_error'],
               electrical_verification=verification)
    return row


def scale_metrics(metrics, vpp):
    """Common open-circuit source amplitude scaling with no1Vpp/device cap."""
    value = float(vpp)
    if not math.isfinite(value) or value < 0:
        raise ValueError('Source Vpp must be nonnegative and finite')
    result = {'source_Vpp': value, 'source_open_circuit_peak_V': .5*value,
              'device_compliance': 'unverified',
              'high_amplitude_extrapolation_not_validated': value > 1}
    result.update({key: float(metrics[key])*value for key in LINEAR if key in metrics})
    result.update({key: float(metrics[key])*value**2 for key in QUADRATIC if key in metrics})
    result.update({key: (np.asarray(metrics[key])*value).tolist() for key in ARRAY_METRICS if key in metrics})
    return result


def _material_signature(descriptor, row):
    if 'material_signature' in descriptor:
        return descriptor['material_signature']
    path = descriptor.get('config_path', row.get('config_path'))
    if not path:
        return None
    values = {}
    for line in Path(path).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()
    if not all(key in values for key in MATERIALS):
        return None
    return {key: float(values[key]) for key in MATERIALS}


def _entry(row, row_bases):
    row = dict(row)
    row.setdefault('carrier_Hz', 2000)
    row.setdefault('beat_Hz', 10)
    row.setdefault('boundary_mode', 'measured_minus_Rs')
    row.setdefault('target20_modulation_V_m', row.get('target20_TI10_V_m', 0))
    identifier = row['id']
    descriptor = row_bases.get(identifier)
    if descriptor is None:
        return {'id': identifier, 'status': 'unavailable', 'reason': 'Explicit basis path missing'}
    descriptor = dict(descriptor) if isinstance(descriptor, dict) else {'basis_dir': str(descriptor)}
    folder = Path(descriptor['basis_dir'])
    try:
        if row['pad_count'] != 2*row['output_channels'] or len(row['xy_mm']) != row['pad_count']:
            raise ValueError('Physical pad count/coordinates disagree with output count')
        if row['output_channels'] == 1:
            if row['pad_count'] != 2 or row['target20_modulation_V_m'] != 0:
                raise ValueError('Single control must have2pads/1output and exactly zero TIS')
        elif row['output_channels'] < 2 or set(row['carrier_group']) != {0, 1}:
            raise ValueError('TIS reference must use two active fundamental groups')
        required = ('target20_total_E_RMS_V_m', 'surface_J_RMS_max_A_m2',
                    'surface_J_RMS_p95_A_m2', 'contact_voltage_RMS_max_V',
                    'SC_power_W', 'contact_power_W', 'source_power_W',
                    'max_source_current_RMS_mA')
        if not all(key in row and math.isfinite(float(row[key])) and float(row[key]) >= 0 for key in required):
            raise ValueError('Missing or nonfinite/negative source metrics')
        electrical, verification = _electrical(row, folder, descriptor.get('frequencies_Hz'))
        if not (folder/'grid.csv').is_file():
            raise CacheUnavailable('Full-grid identity unavailable')
        verification['full_grid_sha256'] = _hash(folder/'grid.csv')
        verification['material_signature'] = _material_signature(descriptor, row)
        metrics = {key: float(row[key]) for key in LINEAR+QUADRATIC if key in row}
        metrics.update(electrical)
        size = float(row['pad_size_mm'])
        conditions = dict(row, pad_area_cm2=size**2/100,
                          total_electrode_area_cm2=row['pad_count']*size**2/100,
                          active_frequencies_Hz=([int(row['carrier_Hz'])] if row['output_channels'] == 1 and row['waveform'] == 'sine'
                            else [f for f, c in _coefficients(row, verification['frequencies_Hz']).items() if np.any(c)]),
                          source_R_ohm=float(row.get('source_R_ohm', 50)))
        if conditions['source_R_ohm'] != 50:
            raise ValueError('The retained bases model50ohm source branches')
        return {'id': identifier, 'status': 'available', 'conditions': conditions,
                'metrics_at_1Vpp': scale_metrics(metrics, 1), 'verification': verification}
    except CacheUnavailable as error:
        return {'id': identifier, 'status': 'unavailable', 'reason': str(error)}
    except (ValueError, KeyError) as error:
        return {'id': identifier, 'status': 'validation_failed', 'reason': str(error)}


def _compatibility(tis, single):
    a, b = tis['conditions'], single['conditions']
    result = {}
    for key, required in (('h_mm', True), ('thickness_nm', True),
                           ('boundary_mode', True), ('waveform', True),
                           ('pad_size_mm', False), ('total_electrode_area_cm2', False)):
        av, bv = a.get(key), b.get(key)
        matched = math.isclose(float(av), float(bv), rel_tol=1e-10, abs_tol=1e-12) if key == 'h_mm' else av == bv
        result[key] = {'matched': matched, 'tis': av, 'single': bv, 'required': required}
    for key, field in (('full_grid', 'full_grid_sha256'), ('material', 'material_signature')):
        av, bv = tis['verification'][field], single['verification'][field]
        result[key] = {'matched': None if av is None or bv is None else av == bv,
                       'tis': av, 'single': bv, 'required': True}
    carrier = b['carrier_Hz']
    choices = [a['carrier_Hz'], a['carrier_Hz']+a['beat_Hz']]
    result['single_carrier_matches_tis_f1_or_f2'] = {
        'matched': carrier in choices, 'tis': choices, 'single': carrier, 'required': True}
    result['layout'] = {'matched': a.get('xy_mm') == b.get('xy_mm'),
                        'tis': {'name': a.get('layout'), 'xy_mm': a.get('xy_mm')},
                        'single': {'name': b.get('layout'), 'xy_mm': b.get('xy_mm')},
                        'required': False}
    return result


def build_comparison(references, single_controls, row_bases, target_fields_V_m=None):
    """Return comparisons; row_bases maps ID to basis_dir/config_path metadata.

    Material, physical grid, nominal XY mesh, coating, boundary, waveform and
    carrier-group membership must match.  Different pad area/layout is allowed
    and disclosed.  Missing material identity holds a pair rather than silently
    treating it as a matched-physics comparison.  No files are written.
    """
    refs = [_entry(row, row_bases) for row in references]
    controls = [_entry(row, row_bases) for row in single_controls]
    comparisons = []
    for tis in refs:
        for single in controls:
            pair = {'id': tis['id']+'__'+single['id'], 'tis_id': tis['id'], 'single_id': single['id']}
            if tis['status'] != 'available' or single['status'] != 'available':
                pair.update(status='unavailable', reason='Both validated electrical rows/bases are required')
                comparisons.append(pair)
                continue
            pair['conditions'] = {'tis': tis['conditions'], 'single': single['conditions']}
            compatible = _compatibility(tis, single)
            pair['compatibility'] = compatible
            failures = [key for key, item in compatible.items() if item['required'] and item['matched'] is not True]
            if failures:
                pair.update(status='held_incompatible', reason='Unmatched/unverified required conditions: '+', '.join(failures))
                comparisons.append(pair)
                continue
            tm, sm = tis['metrics_at_1Vpp'], single['metrics_at_1Vpp']
            target, response = tm['target20_total_E_RMS_V_m'], sm['target20_total_E_RMS_V_m']
            if target <= 0 or response <= 0:
                pair.update(status='invalid_response', reason='Positive target and single-pair response are required')
                comparisons.append(pair)
                continue
            required_vpp = target/response
            matched_tis, matched_single = scale_metrics(tm, 1), scale_metrics(sm, required_vpp)
            if not math.isclose(matched_single['target20_total_E_RMS_V_m'], target, rel_tol=1e-12):
                raise ValueError('Same-RMS scaling failed')
            if target_fields_V_m is None:
                sweep = np.linspace(0, max(5., 2.5*target), 51).tolist()
            else:
                sweep = [float(v) for v in target_fields_V_m]
                if not all(math.isfinite(v) and v >= 0 for v in sweep):
                    raise ValueError('Target E RMS sweep must be nonnegative and finite')
            sweep = sorted(set(sweep+[0., target, response]))
            ratios = {key: (matched_single[key]/matched_tis[key] if matched_tis[key] else None)
                      for key in BURDEN if key in matched_single and key in matched_tis}
            pair.update(status='complete',
                match={'metric': 'target20_total_E_RMS_V_m', 'target_E_RMS_V_m': target,
                       'required_single_source_Vpp': required_vpp, 'tis_source_Vpp_per_output': 1,
                       'source_Vpp_definition': 'open-circuit command Vpp with50ohm Thevenin source; HighZdisplay convention',
                       'envelope_match_possible': False},
                metrics_at_match={'tis': matched_tis, 'single': matched_single},
                burden_ratios=ratios,
                curves={'target_E_RMS_V_m': sweep,
                        'tis': [scale_metrics(tm, e/target) for e in sweep],
                        'single': [scale_metrics(sm, e/response) for e in sweep]},
                markers={'tis_1Vpp': scale_metrics(tm, 1), 'single_1Vpp': scale_metrics(sm, 1)},
                verification={'same_E_RMS_achieved': True, 'single_TIS_envelope_V_m': 0,
                              'numerical_basis_passed': bool(tis['verification']['numerical_basis_passed']
                                                             and single['verification']['numerical_basis_passed']),
                              'loaded_voltage_Vpp_sampling': {
                                  'tis': tis['verification']['loaded_voltage_Vpp_sampling'],
                                  'single': single['verification']['loaded_voltage_Vpp_sampling']},
                              'differential_probe_assumptions': dict(PROBE_ASSUMPTIONS),
                              'source_voltage_cap_applied': False, 'device_compliance': 'unverified',
                              'activation_equivalence_established': False,
                              'TIS_task1_fixed_1Vpp_anchor_unchanged': True},
                limits=LIMITS)
            comparisons.append(pair)
    return {'schema_version': SCHEMA_VERSION, 'match_metric': 'target20_total_E_RMS_V_m',
            'status': 'complete' if comparisons and any(p['status'] == 'complete' for p in comparisons)
                      else 'no_valid_comparisons',
            'references': refs, 'single_controls': controls, 'comparisons': comparisons,
            'no_PDE_executed': True, 'original_worker_inputs_results_unchanged': True,
            'activation_threshold_available': False,
            'differential_probe_assumptions': dict(PROBE_ASSUMPTIONS), 'limits': LIMITS}
