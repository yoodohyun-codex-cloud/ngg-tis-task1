"""Pinned native spatial comparison: current f35 TIS versus a true C1 pair.

No CLI, execution lock, budget write or research read occurs on import. The
caller owns one finite run. C1's shared square-wave NPZ supplies masks ONLY;
its pure-3000Hz sine RMS is reconstructed from the one-output complex field.
"""
from __future__ import annotations
import base64
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import numpy as np
import task1_top5_build as display
import task1_top5_contact_export as contact

ROOT = Path(__file__).resolve().parents[1]
RUN = 'cloud-mesh-c1-20261019T190000Z'
C1_ID = 'baseline-square15-C1pair0-xy80'
F35_ID = 'rounded-expand-f35b23a22166'
TOP5_PLAN = 'docs/task1-top5-context-20261022/preregistration-v2.json'
C1_CACHE = 'docs/cloud-rounded-single-pair-20261021T212000Z/summary.json'
REGIONS = ('primary_r5_depth15_20', 'surface_0_5', 'primary_complement', 'total')
RELATIVE = .0005
ABSOLUTE = 3.1e-8
EPS0 = 8.8541878128e-12
MAX_BYTES = 64*1024**2
require = contact.require


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pick(summary, name):
    found = [p for p in summary['input_sha256'] if Path(p).name in (name, name+'.gz')]
    require(len(found) == 1, 'One exact native input required: '+name)
    return Path(found[0])


def _metadata(root):
    """Only bounded JSON metadata is read here; raw digests are declarations."""
    root = Path(root).resolve()
    refs = {}
    def read(path, expected=None):
        path = Path(path)
        require(path.is_absolute() and path == path.resolve() and path.is_relative_to(root) and path.suffix == '.json' and
                path.is_file() and not path.is_symlink() and path.stat().st_size <= 4*1024**2, 'Bounded canonical JSON metadata required')
        raw = path.read_bytes(); digest = _sha(raw)
        require(expected is None or digest == expected, 'Metadata identity changed: '+str(path))
        refs[str(path)] = digest
        return json.loads(raw)
    top5 = read(root/TOP5_PLAN)
    row = next(r for r in top5['catalog']['selected_layouts'] if r['condition_id'] == F35_ID)
    require(row['source_case_id'] == 'rounded-fullface225-xy80' and row['circuit']['n_pads'] == 4 and
            row['circuit']['n_outputs'] == 2 and row['circuit']['n_return_nodes'] == 1, 'Exact current rounded f35 TIS reference required')
    condition = read(row['condition_source']['path'], row['condition_source']['SHA256'])
    require(condition['id'] == F35_ID and condition['status'] == 'calculated_unadopted' and
            condition['configuration_sha256'] == row['configuration_sha256'] and condition['candidate_adopted'] is False,
            'Exact saved f35 coefficient/configuration identity required')
    cache = read(root/C1_CACHE)
    unit = cache['single_stimulation']
    run = root/'data-native'/RUN
    pre = read(run/'preregistration.json')
    case = next(c for c in pre['cases'] if c['id'] == C1_ID)
    post_path = run/'postprocess'/C1_ID/'summary.json'
    post = read(post_path)
    record = read(run/'cases'/(C1_ID+'.json'))
    meta = post['mesh_metadata']; circuit = case['circuit']
    require(post['status'] == record['status'] == 'complete' and post['id'] == C1_ID and
            record['postprocess_sha256'] == refs[str(post_path)] and record['config_sha256'] == case['config_sha256'],
            'Completed exact C1 native receipt required')
    require(circuit['n_pads'] == 2 and circuit['n_outputs'] == meta['channels'] == 1 and circuit['n_return_nodes'] == 1 and
            circuit['pad_to_node'] == {'0':'out0','1':'GND'} and circuit['source_peak_V'] == .5 and circuit['source_resistance_ohm'] == 50,
            'C1 must be one actual source/return pair, not a disabled four-pad circuit')
    for key, value in (('h_xy_mm', .625), ('sc_cells', 2), ('bulk_layer_counts', [14,14,40]), ('cells', 351680),
                       ('radius_mm', 25), ('total_depth_mm', 25.1), ('phasor_convention', 'peak,+jomega_t')):
        require(meta[key] == value and row['mesh_metadata'][key] == value, 'Same nominal fine SC2 mesh required: '+key)
    require(case['source_coating_nm'] == 10 and case['source_Rs_fit_window_Hz'] == 500 and
            meta['config_sha256'] == case['config_sha256'], 'Nominal PBS/Rs-fit500 contact/config required')
    require(post['validation'] == record['validation'] and pre['gates'] == contact.NATIVE_GATES,
            'Original five native validation definitions must agree')
    for key, limit in contact.NATIVE_GATES.items():
        require(0 <= post['validation'][key] <= limit, 'C1 native gate failed: '+key)
    require(cache['status'] == 'calculated_unadopted' and cache['inputs_unchanged'] is True and
            cache['input_sha256'][str(post_path)] == refs[str(post_path)] and cache['input_sha256'][case['config_file']] == case['config_sha256'] and
            unit['case_id'] == C1_ID and unit['source_run_id'] == RUN and unit['frequency_Hz'] == 3000 and unit['raw_source_Vpp'] == 1.,
            'Exact completed one-volt pure-sine C1 unit cache required')
    sine = next(c for c in post['conditions'] if c['waveform'] == 'sine' and c['actual_fundamental_Hz'] == [3000])
    require(all(r['frequency_Hz'] == 3000 or all(v == 0 for k in ('real_A','imaginary_A') for v in r[k])
                for r in sine['metrics']['source_current_spectrum']), 'C1 must have no active non-3000Hz source')
    refs.update(row['source_refs'])
    refs.update(contact.required_contact_paths(row))
    for key in ('grid','scalar_archive'):
        refs[row[key]['path']] = row[key]['SHA256']
    for name in ('BASIS_COMPLETE','validation.json','mesh-metadata.json','grid.csv','field-3000.bin',
                 'density-3000.bin','source-3000.bin','loss-3000.bin','contacts-3000.csv'):
        path = _pick(post, name); refs[str(path)] = post['input_sha256'][str(path)]
    refs[case['config_file']] = case['config_sha256']; refs[case['mask_file']] = case['mask_sha256']
    weights_path = post_path.parent/sine['native_volume_archive']
    refs[str(weights_path)] = post['artifacts']['files'][sine['native_volume_archive']]['SHA256']
    for name in ('task1_top5_build.py','task1_top5_contact_export.py','task1_bounded_continuation.py','task1_resource_policy.py'):
        path = str(root/'tools'/name); refs[path] = top5['implementation_sha256'][path]
    require(all(Path(p).is_absolute() and Path(p) == Path(p).resolve() and Path(p).is_relative_to(root) for p in refs),
            'Every declared native/source path must remain in this repository')
    return dict(row=row, case=case, post=post, unit=unit, sine=sine, weights_path=weights_path), refs


def required_inputs(root=ROOT):
    """Return absolute path:SHA pins, reading JSON metadata and no raw arrays."""
    return _metadata(root)[1]


def weighted_stats(values, weights):
    values, weights = np.asarray(values, float), np.asarray(weights, float)
    require(values.ndim == weights.ndim == 1 and values.shape == weights.shape and np.isfinite(values).all() and
            np.isfinite(weights).all() and np.all(values >= 0) and np.all(weights >= 0), 'Finite scalar RMS and nonnegative volume weights required')
    use = weights > 0; v, w = values[use], weights[use]
    require(len(v) and float(w.sum()) > 0, 'Positive represented region volume required')
    order = np.argsort(v, kind='stable'); cumulative = np.cumsum(w[order]); volume = float(w.sum())
    mean = float(v@w/volume); std = math.sqrt(float(((v-mean)**2)@w/volume)); energy = math.sqrt(float((v*v)@w/volume))
    quantile = lambda q: float(v[order[min(int(np.searchsorted(cumulative, q*cumulative[-1], side='left')), len(v)-1)]])
    return dict(mean=mean, p10=quantile(.1), p95=quantile(.95), min=float(v.min()), max=float(v.max()), std=std,
                CV=std/mean if mean else 0., p10_over_mean=quantile(.1)/mean if mean else 0., volume_m3=volume,
                energy_RMS_V_m=energy, positive_weight_cells=int(len(v)))


def scalar_shape_comparison(tis, c1, weights, tis_scale, c1_scale):
    require(math.isfinite(tis_scale) and tis_scale > 0 and math.isfinite(c1_scale) and c1_scale > 0,
            'Actual positive matching amplitudes required')
    tis, c1, weights = np.asarray(tis, float)*tis_scale, np.asarray(c1, float)*c1_scale, np.asarray(weights, float)
    require(tis.shape == c1.shape == weights.shape and np.isfinite(tis).all() and np.isfinite(c1).all() and
            np.all(tis >= 0) and np.all(c1 >= 0) and np.isfinite(weights).all() and np.all(weights >= 0) and np.any(weights > 0),
            'Same-grid finite scalar RMS with physical target weights required')
    volume = float(weights.sum()); energy = math.sqrt(float((tis*tis)@weights/volume))
    require(energy > 0, 'Positive TIS target energy RMS required')
    difference = math.sqrt(float(((c1-tis)**2)@weights/volume))
    fraction = float(weights[abs(c1-tis) <= .1*abs(tis)].sum()/volume)
    return dict(weighted_RMS_difference_V_m=difference, relative_RMS_difference_to_TIS_ROI_energy=difference/energy,
        target_fraction_within_10_percent_of_TIS=fraction, TIS_ROI_energy_RMS_V_m=energy,
        definition='sqrt(sum(target_volume*(C1_local_RMS*A_C1 - TIS_local_RMS*A_TIS)^2)/sum(target_volume)); denominator=TIS ROI energy RMS. Fraction uses abs(diff)<=0.1*abs(TIS); a zero TIS cell passes only if C1 is also zero.',
        scalar_RMS_only=True, vector_or_waveform_equality=False, numerical_10_percent_comparison_not_activation_threshold=True)


def pure_sine_rms(field):
    field = np.asarray(field, complex)
    require(field.ndim == 2 and field.shape[1] == 3 and np.isfinite(field).all(), 'Finite three-component peak complex field required')
    return np.sqrt(np.sum(abs(field)**2, axis=1)/2)


def _sample_complex(field, grid):
    axes = [np.unique(grid[:,k]) for k in range(3)]; pairs = []
    for axis, point in zip(axes, (0.,0.,20.)):
        j = int(np.searchsorted(axis, point)); require(0 < j < len(axis), 'Interior native centre interpolation required')
        t = (point-axis[j-1])/(axis[j]-axis[j-1]); pairs.append(((axis[j-1],1-t),(axis[j],t)))
    result = np.zeros(3, complex)
    for x, wx in pairs[0]:
        for y, wy in pairs[1]:
            for z, wz in pairs[2]:
                use = np.flatnonzero((grid[:,0] == x)&(grid[:,1] == y)&(grid[:,2] == z))
                require(len(use) == 1, 'Unique native centre stencil required'); result += field[use[0]]*wx*wy*wz
    return result


def half_values(values):
    values = np.asarray(values, float); half = values.astype('<f2'); use = np.isfinite(values)
    require(not np.isinf(values).any() and not np.isinf(half).any(), 'Finite display values must fit Float16')
    error = abs(half.astype(float)[use]-values[use])
    require(np.all(error <= ABSOLUTE+RELATIVE*abs(values[use])), 'Float16 display exceeds raw Float64 rounding bound')
    return half, dict(values=int(values.size), passed=True, maximum_absolute_error=float(error.max()) if len(error) else 0.,
                     relative_bound=RELATIVE, absolute_bound=ABSOLUTE, scope='Raw display samples only; absolute term scales with applied amplitude A')


def _planes(values, axes):
    half, proof = half_values(values)
    encoded = display.scalar_planes(half.astype(float), axes)
    def one(value):
        # These Float32 intermediates contain exact representable Float16 values.
        return base64.b64encode(np.frombuffer(base64.b64decode(value), dtype='<f4').astype('<f2').tobytes()).decode()
    return dict(xy=[one(v) for v in encoded['xy']], xz=one(encoded['xz']), yz=one(encoded['yz'])), proof


def _contact_display(pads, x, y, areas, jrms, case, axes):
    n = case['circuit']['n_pads']; require(set(pads) == set(range(n)), 'All actual physical pads required')
    ix, iy = np.searchsorted(axes['x'], x), np.searchsorted(axes['y'], y)
    require(np.all(ix < len(axes['x'])) and np.all(iy < len(axes['y'])) and
            np.allclose(axes['x'][ix], x, rtol=0, atol=1e-9) and np.allclose(axes['y'][iy], y, rtol=0, atol=1e-9) and
            len(np.unique(iy*len(axes['x'])+ix)) == len(pads), 'Unique actual native contact cells required')
    image = np.full((len(axes['y']),len(axes['x'])), np.nan); image[iy,ix] = jrms
    mask = np.full(image.shape, -1, dtype='<i2'); mask[iy,ix] = pads
    half, precision = half_values(image); centres, outlines = [], []
    for p in range(n):
        use = pads == p; area = float(areas[use].sum()); expected = case['expected_pad_areas_m2'][p]
        require(math.isclose(area, expected, rel_tol=1e-10, abs_tol=1e-16), 'Native pad area differs from registered physical area')
        node = case['circuit']['pad_to_node'][str(p)]
        centres.append(dict(pad=p, node=node, x_mm=float(x[use]@areas[use]/area), y_mm=float(y[use]@areas[use]/area), area_mm2=area*1e6))
        pad = next(a for a in case['design']['pads'] if a['pad'] == p)
        outlines.append(dict(pad=p, node=node, polygon_mm=pad['polygon_mm'], area_mm2=expected*1e6))
    return dict(contactJ=base64.b64encode(half.tobytes()).decode(), pad_mask_b64=base64.b64encode(mask.tobytes()).decode(),
                pad_centres=centres, physical_outlines=outlines), precision


def export_spatial(analysis, pins, guard):
    """One guarded RAM-only native export; caller owns locks/budget/output."""
    bundle, declared = _metadata(ROOT)
    require(all(pins.get(p) == digest for p,digest in declared.items()), 'Preregister every exact spatial input before decoding')
    used = {}
    def read(path):
        guard(); path = Path(path)
        require(str(path) in pins and path == path.resolve() and path.is_relative_to(ROOT) and path.is_file() and
                not path.is_symlink() and path.stat().st_size <= MAX_BYTES, 'Bounded preregistered repository input required')
        raw = path.read_bytes(); digest = _sha(raw)
        require(digest == pins[str(path)], 'Pinned spatial input changed: '+str(path)); used[str(path)] = digest; guard()
        return raw
    def binary(path, shape):
        raw = read(path); expected = math.prod(shape)*16
        if Path(path).suffix == '.gz':
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream: raw = stream.read(expected+1)
        require(len(raw) == expected, 'Exact little-endian complex128 dimensions required')
        values = np.frombuffer(raw, dtype='<c16').reshape(shape)
        require(np.isfinite(values).all(), 'Finite native complex basis required'); return values
    def grid(path):
        raw = read(path)
        if Path(path).suffix == '.gz':
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream: raw = stream.read(MAX_BYTES+1)
        require(len(raw) <= MAX_BYTES, 'Bounded native grid required')
        return np.loadtxt(io.BytesIO(raw), delimiter=',', skiprows=1)
    def archive(path, include_rms):
        with np.load(io.BytesIO(read(path)), allow_pickle=False) as data:
            keys = ('region_target_m3','region_surface_0_5_m3','region_total_m3')+ (('RMS',) if include_rms else ())
            result = {k:np.array(data[k], copy=True) for k in keys}
        require(all(a.shape == (351680,) and a.dtype.kind == 'f' and a.dtype.itemsize == 8 and
                    np.isfinite(a).all() and np.all(a >= 0) for a in result.values()), 'Original Float64 scalar/weight archive required')
        return result
    row, case, post, unit, sine = (bundle[k] for k in ('row','case','post','unit','sine'))
    cgrid = grid(_pick(post,'grid.csv')); tgrid = grid(row['grid']['path'])
    require(np.array_equal(cgrid, tgrid), 'C1 and TIS must have exactly identical native grid columns/order')
    axes = display.axes_and_indices(cgrid, post['mesh_metadata'])
    ca = archive(bundle['weights_path'], False); ta = archive(row['scalar_archive']['path'], True)
    require(all(np.array_equal(ca[k], ta[k]) for k in ca), 'Exact common fractional target/surface/total masks required')
    target, surface, total = (ca[k] for k in ('region_target_m3','region_surface_0_5_m3','region_total_m3'))
    require(np.all(total > 0) and np.all(target <= total) and np.all(surface <= total), 'Fractional regions must be contained in actual native volume')
    weights = dict(zip(REGIONS, (target,surface,total-target,total)))
    field = -1j*binary(_pick(post,'field-3000.bin'), (1,351680,3))[0]
    crms = pure_sine_rms(field); trms = ta['RMS']; centre = float(pure_sine_rms(_sample_complex(field,cgrid)[None,:])[0])
    cstats = {r:weighted_stats(crms,w) for r,w in weights.items()}; tstats = {r:weighted_stats(trms,w) for r,w in weights.items()}
    checks = {}
    def check(name, actual, expected, relative=1e-10, absolute=1e-12):
        require(math.isfinite(actual) and math.isfinite(expected) and math.isclose(actual,expected,rel_tol=relative,abs_tol=absolute),
                'Raw native reproduction failed: '+name)
        checks[name] = dict(actual=actual, saved=expected, passed=True)
    check('C1_centre20_RMS', centre, unit['raw_centre20_E_RMS_V_m'])
    check('C1_sine_saved_centre20_RMS', centre, sine['metrics']['target20_total_E_RMS_V_m'])
    check('C1_ROI_energy_RMS', cstats[REGIONS[0]]['energy_RMS_V_m'], unit['raw_ROI_energy_RMS_V_m'])
    for region in REGIONS:
        saved = row['normalizations']['raw_1Vpp']['regions'][region]['RMS']
        for key in ('mean','p10','p95','max','std','volume_m3'):
            check('TIS_'+region+'_'+key,tstats[region][key],saved[key],absolute=1e-25 if key=='volume_m3' else 1e-12)
    raw = read(_pick(post,'contacts-3000.csv'))
    contacts = np.genfromtxt(io.BytesIO(raw), delimiter=',', names=True)
    pads, x, y, area = (contacts[k].astype(int if k=='pad' else float) for k in ('pad','x_mm','y_mm','area_m2'))
    require(np.all(area > 0) and np.isfinite(area).all() and len(area) <= contact.MAX_PATCHES, 'Positive bounded C1 contact patches required')
    density = -1j*binary(_pick(post,'density-3000.bin'), (1,len(area)))[0]
    transfer = binary(_pick(post,'source-3000.bin'), (1,1))[0,0]
    loss = binary(_pick(post,'loss-3000.bin'), (6,1,1))[:,0,0]
    require(np.max(abs(loss.imag)) < 1e-12 and np.all(loss.real >= -1e-12), 'Passive six-compartment C1 loss basis required')
    current = -1j*transfer; supplied = .25*transfer.real
    require(abs(np.sum(density*area))/max(float(np.sum(abs(density)*area)),1e-30) <= 2e-6 and
            abs(np.sum(density[pads==0]*area[pads==0])-current) <= 2e-6*abs(current) and
            abs(loss.real.sum()-supplied) <= 2e-7*abs(supplied), 'C1 actual current/power conservation failed')
    saved_current = next(r for r in sine['metrics']['source_current_spectrum'] if r['frequency_Hz'] == 3000)
    saved_metal = next(r for r in sine['metrics']['loaded_metal_voltage_spectrum'] if r['frequency_Hz'] == 3000)
    metal = -.5j-50*current
    for name, value, saved in (('source_current_real_A',current.real,saved_current['real_A'][0]),
        ('source_current_imag_A',current.imag,saved_current['imaginary_A'][0]),
        ('loaded_metal_real_V',metal.real,saved_metal['real_V'][0]),
        ('loaded_metal_imag_V',metal.imag,saved_metal['imaginary_V'][0])):
        check('C1_'+name,float(value),saved,absolute=1e-14)
    config = {}
    for line in read(case['config_file']).decode().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            k,v = line.split('=',1); config[k.strip()] = v.strip()
    tconfig = {}
    for line in read(row['native_config']['path']).decode().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            k,v = line.split('=',1); tconfig[k.strip()] = v.strip()
    require(all(tconfig.get(k) == v for k,v in config.items() if k.startswith('z.') or k.endswith(('.sigma','.epsilon_r'))),
            'Same nominal tissue and specific-contact impedance required')
    jrms = abs(density)/math.sqrt(2); za = complex(float(config['z.3000.re']),float(config['z.3000.im']))
    layers = cgrid[:,3].astype(int); require(np.array_equal(cgrid[:,3],layers) and set(layers) == {0,1,2,3}, 'Four actual layer IDs required')
    gamma = np.asarray([complex(float(config[k+'.sigma']),2*math.pi*3000*EPS0*float(config[k+'.epsilon_r'])) for k in ('sc','dermis','fat','muscle')])
    skin = layers <= 1; jskin = abs(gamma[layers])*crms
    def old_p95(v,w):
        order=np.argsort(v,kind='stable'); return float(v[order[min(int(np.searchsorted(np.cumsum(w[order]),.95*w.sum())),len(v)-1)]])
    burdens = dict(source_current_RMS_mA=float(abs(current)/math.sqrt(2)*1000),source_current_peak_mA=float(abs(current)*1000),
        contact_J_RMS_max_A_m2=float(jrms.max()),contact_J_RMS_p95_A_m2=old_p95(jrms,area),
        contact_voltage_RMS_max_V=float((abs(density*za)/math.sqrt(2)).max()),
        bulk_skin_J_RMS_max_A_m2=float(jskin[skin].max()),bulk_skin_J_RMS_p95_A_m2=old_p95(jskin[skin],total[skin]),
        SC_power_W=float(loss[0].real),dermis_power_W=float(loss[1].real),skin_SC_plus_dermis_power_W=float(loss[0].real+loss[1].real),
        fat_power_W=float(loss[2].real),muscle_power_W=float(loss[3].real),contact_power_W=float(loss[4].real),
        tissue_contact_power_W=float(loss[:5].real.sum()),source_resistor_power_W=float(loss[5].real),source_power_W=float(supplied),
        loaded_metal_Vpp=float(2*abs(-.5j-50*current)))
    for key,value in unit['raw_burdens'].items(): check('C1_'+key,burdens[key],value)
    mask_rows = csv.DictReader(io.StringIO(read(case['mask_file']).decode()))
    mask = {(int(r['pad']),int(r['i']),int(r['j'])):float(r['area_m2']) for r in mask_rows}
    actual = {(int(p),round((xx+25)/.625-.5),round((yy+25)/.625-.5)):float(a) for p,xx,yy,a in zip(pads,x,y,area)}
    require(len(actual) == len(area) and actual.keys() == mask.keys() and
            all(math.isclose(a,mask[k],rel_tol=1e-12,abs_tol=1e-24) for k,a in actual.items()), 'C1 native contacts must match the registered mask')
    guard(); tiscontact = contact.export_contact(row,required_pins=pins)
    cdisplay, cjproof = _contact_display(pads,x,y,area,jrms,case,axes)
    tdisplay, tjproof = _contact_display(tiscontact['pad'],tiscontact['x_mm'],tiscontact['y_mm'],tiscontact['area_m2'],
                                       tiscontact['raw_J_RMS_A_m2'],row['case'],axes)
    cdisplay['RMS'], cproof = _planes(crms,axes); tdisplay['RMS'], tproof = _planes(trms,axes)
    shape = {}
    for mode,data in analysis['modes'].items():
        require(mode in ('raw_1Vpp','skin_contact_only') and data['reference_amplitude_scale'] == row['normalizations'][mode]['amplitude_scale'],
                'Only exact saved raw/skin8 reference amplitudes required')
        require(set(data['matches']) == {'centre20_E_RMS','ROI_energy_RMS'}, 'Both distinct C1 matching criteria required')
        shape[mode] = {}
        for match,matched in data['matches'].items():
            expected_scale = (row['electrical_metrics']['target20_total_E_RMS_V_m']*data['reference_amplitude_scale']/centre
                if match == 'centre20_E_RMS' else
                tstats[REGIONS[0]]['energy_RMS_V_m']*data['reference_amplitude_scale']/cstats[REGIONS[0]]['energy_RMS_V_m'])
            check('matching_'+mode+'_'+match+'_amplitude',matched['amplitude_scale'],expected_scale)
            shape[mode][match] = scalar_shape_comparison(trms,crms,target,data['reference_amplitude_scale'],matched['amplitude_scale'])
    require(set(shape) == {'raw_1Vpp','skin_contact_only'}, 'Both comparison modes required')
    for path,digest in {**declared,**tiscontact['input_sha256']}.items():
        read(path)
    guard(); a=axes
    return dict(grid=dict(x_edges_mm=a['x_edges'].tolist(),y_edges_mm=a['y_edges'].tolist(),z_faces_mm=a['z_faces'].tolist(),
        XY_requested_depths_mm=list(display.DEPTHS),XY_actual_depths_mm=[float(a['z'][np.argmin(abs(a['z']-d))]) for d in display.DEPTHS],
        XZ_actual_y_mm=float(a['y'][np.argmin(abs(a['y']))]),YZ_actual_x_mm=float(a['x'][np.argmin(abs(a['x']))])),
        TIS=tdisplay,C1=cdisplay,regions=dict(TIS=tstats,C1=cstats),shape_comparison=shape,
        proofs=dict(raw_native_reproduction=checks,TIS_contact_regression=tiscontact['regression'],
            display_precision=dict(TIS_RMS=tproof,C1_RMS=cproof,TIS_contact=tjproof,C1_contact=cjproof),
            exact_grid_and_fractional_masks=True,C1_NPZ_RMS_used=False,C1_only_active_frequency_Hz=3000,
            C1_raw_burdens=burdens,inputs_unchanged=True,input_sha256=used,new_PDE=0,
            same_rounded_two_pad_case_available=False,held='C1 uses two original square225mm2 pads/one output/450mm2; f35 uses four rounded-mask225mm2 pads/two outputs/commonGND/900mm2. No equal-footprint, vector/waveform, activation, safety or convergence equivalence.',
            coordinate_system='x,y horizontal mm; z positive depth from the top z=0; actual nonuniform native faces; cell-plane display, no interpolation'))
