"""Finite postprocessing of registered SelectivityShapeBasis outputs only.

No solver, compilation, worker, source edits, retry, GUI publication or source
normalization change occurs here. The caller owns execution/resource locks.
All outputs are new case-local artifacts; failed stages remain auditable.
"""
from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import time

import numpy as np

from explore_tis import WAVES, directions
from layered_probe_analysis import (DEFAULT_LAYERS, FIELD_RECONSTRUCTION,
                                    LayeredPotentialSampler, ProbeDataMissing,
                                    evaluate_layered_probe, waveform_statistics)
from selectivity_volume import evaluate_volume, weighted_statistics


FREQUENCIES = (3000, 3030, 9000, 9090)
FUNDAMENTALS = (3000, 3030)
LIMITS = dict(max_residual=2e-7, max_power_error=2e-7,
              max_current_error=2e-6, max_area_relative_error=1e-10,
              max_interface_normal_current_relative_error=2e-7)
NORMALIZATION = dict(source_peak_V=.5, source_Vpp=1.,
                     source_resistance_ohm=50., phasor_exponent='+jomega_t')
EPS0 = 8.8541878128e-12
_DIRECTIONS = directions(2048)
_REPO = Path(__file__).resolve().parent.parent
_REFERENCE_RUN = _REPO/'tis-java/runs/rs-window-tis-validation-20261019T135413Z'
_REFERENCE_ID = 'coat010-f0500-minusRs'
_REFERENCE_CASE_SHA = '9e96bb3a298e94678ccac1a871a5c232449da01ec2bc79ddd14407c7924c1dde'
_REFERENCE_CONFIG_SHA = 'ebd3fa7a62ceeb9e769a32c3e9217ede10548d0b31059cab09287684d892f773'
_REFERENCE_POST_SHA = 'f5cb0ecfb94e64594ed8681cd58cf2071820b0a2c129b270ea9387bc1ee8ac3d'


class PostprocessDeadlineExceeded(TimeoutError):
    pass


def _deadline(value, stage):
    if not math.isfinite(value) or time.monotonic() >= value:
        raise PostprocessDeadlineExceeded('Postprocessing deadline at '+stage)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _sha(path, deadline):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024**2), b''):
            _deadline(deadline, 'input_hash:'+Path(path).name)
            digest.update(block)
    return digest.hexdigest()


def _json(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False)+'\n')
    temporary.replace(path)


def _path(folder, name):
    for path in (folder/name, folder/(name+'.gz')):
        if path.is_file():
            return path
    raise ProbeDataMissing('Complete registered source file missing: '+name)


def _array(path, shape, deadline):
    """Exact little-endian complex array, lossless gzip without disk mutation."""
    result = np.empty(shape, dtype='<c16')
    target = memoryview(result).cast('B')
    opener = gzip.open if path.suffix == '.gz' else open
    at = 0
    with opener(path, 'rb') as stream:
        while at < len(target):
            _deadline(deadline, 'decompress:'+path.name)
            count = stream.readinto(target[at:min(len(target), at+4*1024**2)])
            if not count:
                raise ValueError('Truncated native binary: '+path.name)
            at += count
        if stream.read(1):
            raise ValueError('Native binary exceeds declared dimensions: '+path.name)
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite native transfer array: '+path.name)
    return result


def _properties(path):
    result = {}
    for line in path.read_text().splitlines():
        if '=' not in line or line.lstrip().startswith(('#', '!')):
            continue
        key, value = (v.strip() for v in line.split('=', 1))
        if key in result:
            raise ValueError('Duplicate registered property: '+key)
        result[key] = value
    return result


def _reference_guard(folder,case,deadline):
    """One exact existing Best1 only, never a generic historical adapter."""
    if not case.get('existing_reference'):
        return None
    pins=case.get('existing_reference_pins',{})
    source_case=_REFERENCE_RUN/'cases'/(_REFERENCE_ID+'.json')
    config=_REFERENCE_RUN/'configs'/(_REFERENCE_ID+'.properties')
    post=_REFERENCE_RUN/'postprocess'/(_REFERENCE_ID+'.json.gz')
    original=case.get('source_original_case')
    if isinstance(original,dict):original=original.get('path')
    paths=dict(source_case_path=source_case,source_postprocess_path=post)
    if (case.get('expected_source_exporter')!='RsWindowTisBasis' or
            original is None or Path(original).resolve()!=source_case.resolve() or
            folder.resolve()!=(_REFERENCE_RUN/'bases'/_REFERENCE_ID).resolve() or
            Path(case['config_file']).resolve()!=config.resolve() or
            case.get('id')!='reference-best1-final'):
        raise ValueError('Existing-reference adapter is restricted to exact registered reference-best1-final')
    for key,path in paths.items():
        if Path(pins.get(key,'')).resolve()!=path.resolve():
            raise ValueError('Existing-reference source path is not the exact approved source: '+key)
    for key,expected in (('source_case_sha256',_REFERENCE_CASE_SHA),
                         ('source_postprocess_sha256',_REFERENCE_POST_SHA),
                         ('config_sha256',_REFERENCE_CONFIG_SHA)):
        if pins.get(key)!=expected:raise ValueError('Existing-reference constant source pin mismatch: '+key)
    result={str(p):_sha(p,deadline) for p in (source_case,config,post)}
    for path,expected in ((source_case,_REFERENCE_CASE_SHA),(config,_REFERENCE_CONFIG_SHA),(post,_REFERENCE_POST_SHA)):
        if result[str(path)]!=expected:raise ValueError('Existing-reference source bytes changed: '+str(path))
    original_case=json.loads(source_case.read_text())
    if (original_case.get('status')!='complete' or original_case.get('id')!=_REFERENCE_ID or
            original_case.get('producer_kind')!='private_RsWindowTisBasis' or
            original_case.get('postprocess',{}).get('sha256')!=_REFERENCE_POST_SHA or
            original_case.get('postprocess',{}).get('native_probe_status')!='complete'):
        raise ValueError('Existing-reference original completion/probe provenance mismatch')
    source_hashes={}
    for path,expected in original_case['output_hashes'].items():
        actual=Path(path).resolve()
        if actual.parent!=folder.resolve() or actual.name in source_hashes:
            raise ValueError('Existing-reference source manifest has ambiguous/outside raw files')
        source_hashes[actual.name]=expected
    supplied={}
    for name,expected in pins.get('basis_input_sha256',{}).items():
        path=Path(name)
        if (path.is_absolute() and path.parent.resolve()!=folder.resolve()) or path.name in supplied:
            raise ValueError('Existing-reference provided basis pins have ambiguous/outside files')
        supplied[path.name]=expected
    if supplied!=source_hashes:
        raise ValueError('Existing-reference requires every original raw basis pin, unchanged')
    for name,expected in source_hashes.items():
        path=folder/name;actual=_sha(path,deadline)
        if actual!=expected:raise ValueError('Existing-reference raw source SHA mismatch: '+name)
        result[str(path)]=actual
    return dict(status='exact_source_pins_verified',input_hashes=result,
        original_case_path=str(source_case),original_case_sha256=_REFERENCE_CASE_SHA,
        original_postprocess_path=str(post),original_postprocess_sha256=_REFERENCE_POST_SHA,
        original_config_sha256=_REFERENCE_CONFIG_SHA,expected_source_exporter='RsWindowTisBasis',
        scope='One completed Best1 only; new 3D ROI reference, no source row/PDE rerun',
        source_metadata_modified=False,new_PDE=0)


def _load_basis(folder, case, deadline):
    reference=_reference_guard(folder,case,deadline)
    paths = [_path(folder, name) for name in ('BASIS_COMPLETE', 'validation.json',
                                              'mesh-metadata.json', 'grid.csv')]
    hashes = dict(reference['input_hashes']) if reference else {}
    for path in paths:
        if str(path) not in hashes:hashes[str(path)]=_sha(path,deadline)
    validation = json.loads(paths[1].read_text())
    metadata = json.loads(paths[2].read_text())
    channels = int(case['design']['channels'])
    if channels not in (1, 2) or validation['channels'] != channels:
        raise ValueError('Only registered true two-pad C1 or four-pad C2 bases supported')
    gate_status={}
    for key, limit in LIMITS.items():
        if reference and key=='max_interface_normal_current_relative_error' and key not in validation:
            gate_status[key]=dict(status='not_available_original',meaning='Original exporter did not publish this gate; no zero/pass value is fabricated')
            continue
        value = float(validation[key])
        if not math.isfinite(value) or value < 0 or value > limit:
            raise ValueError(f'Native numerical gate failed: {key}={value}, limit={limit}')
        gate_status[key]=dict(status='passed',value=value,limit=limit)
    config_path = Path(case['config_file']).resolve()
    config = _properties(config_path)
    hashes[str(config_path)] = _sha(config_path, deadline)
    if case.get('config_sha256',hashes[str(config_path)])!=hashes[str(config_path)]:
        raise ValueError('Registered config SHA mismatch')
    if metadata.get('config_sha256') != hashes[str(config_path)]:
        raise ValueError('Native exporter/config SHA mismatch')
    if reference:
        if (metadata.get('exporter_class')!='RsWindowTisBasis' or
                metadata.get('basis_normalization')!=NORMALIZATION or
                metadata.get('field_reconstruction')!=FIELD_RECONSTRUCTION):
            raise ValueError('Exact existing-reference original exporter/normalization/reconstruction required')
        if (channels!=2 or case['h_xy_mm']!=50/120 or case['sc_cells']!=2 or
                list(case['bulk_counts'])!=[14,14,40]):
            raise ValueError('Existing Best1 reference mesh is fixed, not a historical generic adapter')
    elif (metadata.get('exporter_class') != 'SelectivityShapeBasis' or
              metadata.get('source_peak_V') != .5 or metadata.get('source_resistance_ohm') != 50 or
              metadata.get('phasor_convention') != 'peak,+jomega_t' or
              metadata.get('field_reconstruction') != 'half_face_flux; top contact term averaged over full cell face h^2'):
        raise ValueError('Explicit registered exporter/normalization/reconstruction required')
    if (metadata.get('channels') != channels or metadata.get('frequencies_Hz') != list(FREQUENCIES)
            or metadata.get('h_xy_mm') != case['h_xy_mm'] or metadata.get('sc_cells') != case['sc_cells']):
        raise ValueError('Native actual mesh and registered case mismatch')
    opener = gzip.open if paths[3].suffix == '.gz' else open
    with opener(paths[3], 'rt') as stream:
        grid = np.atleast_1d(np.genfromtxt(stream, delimiter=',', names=True))
    _deadline(deadline, 'grid_loaded')
    if len(grid) != validation['cells'] or not 0 < len(grid) <= 800000:
        raise ValueError('Native grid cell count violates registered dimensions/cap')
    expected_areas = np.asarray(case['expected_pad_areas_m2'], float)
    if expected_areas.shape != (2*channels,) or not np.isfinite(expected_areas).all() or np.any(expected_areas <= 0):
        raise ValueError('Explicit polygon represented area required per physical pad')
    for i, area in enumerate(expected_areas):
        registered=(.000225 if reference else float(config[f'pad.{i}.represented_area_m2']))
        if abs(registered/area-1) > 1e-10:
            raise ValueError('Prepared pad area disagrees with registered polygon area')
    frequencies, contact_identity, receipts = {}, None, {}
    for f in FREQUENCIES:
        _deadline(deadline, f'load_frequency:{f}')
        paths_f = {name: _path(folder, f'{name}-{f}.{suffix}') for name, suffix in
                   (('field','bin'), ('potential','bin'), ('density','bin'),
                    ('loss','bin'), ('source','bin'), ('contacts','csv'))}
        for path in paths_f.values():
            if str(path) not in hashes:hashes[str(path)] = _sha(path, deadline)
        opener = gzip.open if paths_f['contacts'].suffix == '.gz' else open
        with opener(paths_f['contacts'], 'rt') as stream:
            contacts = np.atleast_1d(np.genfromtxt(stream, delimiter=',', names=True))
        pad = np.asarray(contacts['pad'], float)
        area = np.asarray(contacts['area_m2'], float)
        if (not np.equal(pad, np.round(pad)).all() or not np.isfinite(area).all() or
                np.any(area <= 0) or set(pad.astype(int)) != set(range(2*channels))):
            raise ValueError('Invalid contact patch IDs/physical overlap area')
        actual_areas = np.bincount(pad.astype(int), weights=area, minlength=2*channels)
        error = float(np.max(abs(actual_areas/expected_areas-1)))
        if error > 1e-10:
            raise ValueError('Registered per-pad represented area is not preserved')
        full_face_error=None
        if reference:
            full_face=(float(metadata['h_xy_mm'])/1000)**2
            full_face_error=float(np.max(abs(area/full_face-1)))
            if full_face_error>1e-10:
                raise ValueError('Existing-reference old I/A and new I/h^2 are not equivalent on a partial face')
        if contact_identity is None:
            contact_identity = contacts.copy()
        elif not np.array_equal(contact_identity, contacts):
            raise ValueError('Contact order/areas differ across carrier/harmonic bases')
        n = len(grid)
        field = _array(paths_f['field'], (channels, n, 3), deadline)
        potential = _array(paths_f['potential'], (channels, n), deadline)
        density = _array(paths_f['density'], (channels, len(contacts)), deadline)
        loss = _array(paths_f['loss'], (6, channels, channels), deadline)
        source = _array(paths_f['source'], (channels, channels), deadline)
        if not np.allclose(loss, loss.conj().transpose(0,2,1), atol=1e-12, rtol=1e-10):
            raise ValueError('Native loss matrix is not Hermitian')
        trial_errors = []
        for seed in range(3):
            c = np.random.default_rng(seed).normal(size=channels)+1j*np.random.default_rng(seed+17).normal(size=channels)
            losses = float(np.einsum('i,kij,j->', c.conj(), loss, c).real)
            supplied = float(.25*np.vdot(c, source@c).real)
            relative = abs(losses-supplied)/max(abs(supplied), 1e-20)
            if relative > 2e-7:
                raise ValueError('Arbitrary complex-output power conservation failed')
            trial_errors.append(relative)
        frequencies[f] = dict(field=field, potential=potential, density=density,
                              loss=loss, source=source, contacts=contacts)
        receipts[str(f)] = dict(expected_pad_area_m2=expected_areas.tolist(),
            represented_pad_area_m2=actual_areas.tolist(), max_relative_area_error=error,
            combined_source_power_test_relative_errors=trial_errors,
            old_full_face_to_new_h_squared_equivalence=(dict(status='passed_full_contact_faces',
                max_relative_contact_area_vs_h_squared_error=full_face_error,
                meaning='Every original contact A equals h²; original I/A and proposed I/h² top-field terms are algebraically identical') if reference else None))
    return dict(grid=grid, f=frequencies, validation=validation, metadata=metadata,
                hashes=hashes, config=config, contact_validation=receipts,
                validation_gate_status=gate_status,existing_reference_adapter=reference)


def _geometry(basis, case):
    metadata, config = basis['metadata'], basis['config']
    counts = [metadata['sc_cells']]+metadata['bulk_layer_counts']
    if list(case['bulk_counts']) != counts[1:]:
        raise ValueError('Actual bulk layer counts differ from registered case')
    gamma = {}
    for f in FREQUENCIES:
        gamma[f] = {i: complex(float(config[name+'.sigma']), 2*np.pi*f*EPS0*float(config[name+'.epsilon_r']))
                    for i, name in enumerate(('sc','dermis','fat','muscle'))}
    geometry = dict(coordinate_system=dict(unit='mm', surface_z_mm=0., depth_axis='+z'),
        radius_mm=25., layers=[dict(layer) for layer in DEFAULT_LAYERS],
        z_faces_mm=metadata['z_faces_mm'], field_reconstruction=FIELD_RECONSTRUCTION,
        basis_normalization=dict(NORMALIZATION), gamma_S_m=gamma,
        reconstruction_adapter=dict(source_exporter_reconstruction=metadata['field_reconstruction'],
            helper_constant=FIELD_RECONSTRUCTION,
            scope='Native interior bulk half-face flux unchanged. Existing phi-E helper rejects surface/bottom/outer boundary stencils; new partial top-face averaging is not certified by this adapter.'))
    if basis.get('existing_reference_adapter'):
        geometry['reconstruction_adapter'].update(existing_reference=basis['existing_reference_adapter'],
            full_top_face_equivalence=basis['contact_validation'],
            scope='Exact existing Best1 original native half-face flux. All source contact A=h² verified; old I/A equals new I/h². Original source metadata is not edited and unpublished interface conservation remains unavailable.')
    volume = dict(case['volume_metadata'], h_xy_mm=metadata['h_xy_mm'], radius_mm=25.,
                  z_faces_mm=metadata['z_faces_mm'], layer_counts=counts,
                  source_provenance=dict(case_id=case['id'], config_sha256=metadata['config_sha256']))
    return geometry, volume


def _coefficients(channels, wave, carrier=None):
    a1, a3 = WAVES[wave]
    group = np.array([0,1]) if channels == 2 else np.array([0 if carrier == 3000 else 1])
    return {f: -1j*(group == (0 if f in (3000,9000) else 1))*(a1 if f in FUNDAMENTALS else a3)
            for f in FREQUENCIES}


def _spectra(basis, coefficients):
    return {f: np.einsum('c,cnk->nk', coefficients[f], basis['f'][f]['field']) for f in FREQUENCIES}


def _electrical(basis, coefficients, geometry, deadline):
    _deadline(deadline, 'electrical_metrics')
    sampler = LayeredPotentialSampler(basis['grid'], geometry)
    n_contacts = len(basis['f'][3000]['contacts'])
    area = basis['f'][3000]['contacts']['area_m2']
    pads = basis['f'][3000]['contacts']['pad'].astype(int)
    channels = len(coefficients[3000])
    j2, polar2, current2, loss = np.zeros(n_contacts), np.zeros(n_contacts), np.zeros(channels), np.zeros(6)
    source_power, centre_spectra, current_errors, power_errors = 0., {}, [], []
    current_spectra, load_spectra = [], []
    for f, c in coefficients.items():
        row = basis['f'][f]
        density = c@row['density']
        current = row['source']@c
        combined_loss = np.einsum('i,kij,j->k', c.conj(), row['loss'], c).real
        supplied = float(.25*np.vdot(c, current).real)
        if np.any(c):
            by_signal = np.array([np.sum(density[pads==i]*area[pads==i]) for i in range(channels)])
            error = float(np.max(abs(by_signal-current))/max(float(np.max(abs(current))), 1e-30))
            balance = float(abs(np.sum(density*area))/max(float(np.sum(abs(density)*area)), 1e-30))
            p_error = float(abs(combined_loss.sum()-supplied)/max(abs(supplied), 1e-20))
            if max(error,balance) > 2e-6 or p_error > 2e-7:
                raise ValueError('Driven output current/power conservation failed')
            current_errors.append(max(error,balance));power_errors.append(p_error)
        stencil = sampler.stencil([0,0,20], geometry['gamma_S_m'][f])
        target_basis = np.einsum('p,cpk->ck', stencil['weights'], row['field'][:,stencil['indices'],:])
        centre_spectra[f] = c@target_basis
        j2 += abs(density)**2/2
        za = complex(float(basis['config'][f'z.{f}.re']), float(basis['config'][f'z.{f}.im']))
        polar2 += abs(density*za)**2/2
        current2 += abs(current)**2/2
        loss += combined_loss
        source_power += supplied
        current_spectra.append(dict(frequency_Hz=f,real_A=current.real.tolist(),imaginary_A=current.imag.tolist()))
        loaded=.5*c-50*current
        load_spectra.append(dict(frequency_Hz=f,real_V=loaded.real.tolist(),imaginary_V=loaded.imag.tolist()))
    jrms = np.sqrt(j2)
    order = np.argsort(jrms,kind='stable')
    cumulative = np.cumsum(area[order])
    p95 = float(jrms[order[min(int(np.searchsorted(cumulative,.95*cumulative[-1])),len(order)-1)]])
    a,b = centre_spectra[3000],centre_spectra[3030]
    modulation = float(2*np.minimum(abs(_DIRECTIONS@a),abs(_DIRECTIONS@b)).max())
    return dict(target20_modulation_V_m=modulation,
        target20_total_E_RMS_V_m=float(np.sqrt(sum(np.vdot(v,v).real for v in centre_spectra.values())/2)),
        surface_J_RMS_max_A_m2=float(jrms.max()), surface_J_RMS_p95_A_m2=p95,
        contact_voltage_RMS_max_V=float(np.sqrt(polar2.max())),
        max_source_current_RMS_mA=float(np.sqrt(current2.max())*1000),
        source_current_RMS_by_output_mA=(np.sqrt(current2)*1000).tolist(),
        SC_power_W=float(loss[0]), contact_power_W=float(loss[4]),
        skin_power_W=float(loss[0]+loss[4]), tissue_contact_power_W=float(sum(loss[:5])),
        source_power_W=source_power, source_resistor_power_W=float(loss[5]),
        source_current_spectrum=current_spectra, loaded_metal_voltage_spectrum=load_spectra,
        centre_field_spectrum=[dict(frequency_Hz=f,real_V_m=v.real.tolist(),imaginary_V_m=v.imag.tolist()) for f,v in centre_spectra.items()],
        driven_max_current_relative_error=max(current_errors,default=0.),
        driven_max_power_relative_error=max(power_errors,default=0.),
        sampled_direction_count=2074)


def _derive_volume(primary, spectra, wave, deadline):
    """No new N×direction projection: fundamental amplitude ratio is exact."""
    _deadline(deadline, 'cached_wave_volume:'+wave)
    factor = WAVES[wave][0]/WAVES['square_3h'][0]
    metrics = copy.deepcopy(primary['metrics'])
    scalars = {key: value*factor for key,value in primary['scalars'].items()
               if key in ('maxTIS','fixedTIS','X_TIS','Y_TIS','Z_TIS')}
    scalars['RMS'] = np.sqrt(sum(np.sum(abs(v)**2,axis=1)/2 for v in spectra.values()))
    for region, weights in primary['region_weights_m3'].items():
        _deadline(deadline, 'cached_wave_region:'+region)
        metrics['regions'][region]['statistics'] = {key:weighted_statistics(v,weights) for key,v in scalars.items()}
        # Those square-wave tissue strata cannot be relabelled as another wave.
        # Primary square statistics remain intact; no duplicate native projection.
        metrics['regions'][region].pop('tissue_statistics',None)
        for threshold_name,threshold in metrics['thresholds'].items():
            metrics['regions'][region]['high_modulation_volume'][threshold_name]={}
            for key in ('maxTIS','fixedTIS'):
                volume=float(weights[scalars[key]>=threshold['value_V_m']].sum())
                metrics['regions'][region]['high_modulation_volume'][threshold_name][key]=dict(volume_m3=volume,volume_mm3=volume*1e9,fraction=volume/float(weights.sum()),comparison_operator='>=')
    for metric in ('maxTIS','fixedTIS','RMS'):
        target=metrics['regions']['target']['statistics'][metric]
        for region in ('surface_0_5','subsurface_5_10','remaining','off_target'):
            other=metrics['regions'][region]['statistics'][metric]
            metrics['ratios'][metric][region]=dict(
                target_mean_over_off_p95=target['mean']/other['p95'] if other['p95'] else None,
                target_p10_over_off_p95=target['p10']/other['p95'] if other['p95'] else None,
                target_mean_over_off_max=target['mean']/other['max'] if other['max'] else None)
    metrics['waveform_reuse']=dict(waveform=wave,full_direction_projection_repeated=False,
        fundamental_factor_over_square=factor,RMS='independent actual-frequency/harmonic quadratic sum',
        tissue_statistics='omitted for derivative waveform; preserved only in the independently evaluated primary square result')
    metrics['frequencies_Hz']=[f for f,v in spectra.items() if np.any(v)]
    return metrics


def _probe_variation(primary, wave, deadline):
    result=copy.deepcopy(primary)
    for row in result['measurements']:
        _deadline(deadline,'probe_waveform:'+wave)
        if row['status']!='complete':
            continue
        frequencies,phasors=[],[]
        for item in row['spectrum']:
            f=item['frequency_Hz'];index=0 if f in FUNDAMENTALS else 1
            factor=WAVES[wave][index]/WAVES['square_3h'][index]
            if factor==0:
                continue
            frequencies.append(f);phasors.append(complex(item['real_V'],item['imaginary_V'])*factor)
        fundamentals=[f for f in frequencies if f in FUNDAMENTALS]
        row.update(waveform_statistics(frequencies,phasors,fundamentals))
        row.pop('time_plot',None)
    result['waveform']=wave
    result['native_gate_reuse']='Same original native phi/E arrays; only exact actual waveform coefficient ratios differ'
    return result


def _phi_gradient(sampler,potential,point,gamma,h_xy_mm):
    """One explicit within-tissue central derivative of original complex phi."""
    point=np.asarray(point,float)
    tissue=sampler.tissue_at(point[2])
    if tissue['is_interface']:
        raise ProbeDataMissing('Exact physical interface has no single normal E value')
    layer=sampler.layer_by_id[tissue['layer_ids'][0]]
    dz=min(.01,(point[2]-layer['z_min_mm'])/4,(layer['z_max_mm']-point[2])/4)
    if dz<=0:
        raise ProbeDataMissing('No within-layer central derivative interval')
    result=np.empty(3,complex)
    for k,delta in enumerate((min(h_xy_mm/4,.1),min(h_xy_mm/4,.1),dz)):
        plus,minus=point.copy(),point.copy();plus[k]+=delta;minus[k]-=delta
        a=sampler.interpolate(potential,sampler.stencil(plus,gamma))[0]
        b=sampler.interpolate(potential,sampler.stencil(minus,gamma))[0]
        result[k]=-(a-b)/(2*delta/1000)
    return result


def _maps(basis, coefficients, geometry, output, deadline):
    """Explicit display-only -grad(native phi), not native-cell score fields."""
    sampler=LayeredPotentialSampler(basis['grid'],geometry)
    axis=np.linspace(-25,25,41)
    z=np.unique(np.r_[sampler.axes[2],5.,10.,15.,20.])
    xx,yy=np.meshgrid(axis,axis,indexing='xy')
    xy=np.array([[x,y,d] for d in (5.,10.,15.,20.) for x,y in zip(xx.ravel(),yy.ravel())])
    zz,xz=np.meshgrid(z,axis,indexing='ij')
    xz_points=np.column_stack((xz.ravel(),np.zeros(xz.size),zz.ravel()))
    points=np.concatenate((xy,xz_points))
    result={f:np.full((len(points),3),np.nan+1j*np.nan) for f in FREQUENCIES}
    active={f:c for f,c in coefficients.items() if np.any(c)}
    phi={f:np.einsum('c,cn->n',c,basis['f'][f]['potential'])[None,:] for f,c in active.items()}
    valid=np.ones(len(points),bool);reasons={}
    delta_xy=min(float(basis['metadata']['h_xy_mm'])/4,.1)
    for p,point in enumerate(points):
        if p%64==0:_deadline(deadline,'display_native_phi_gradient')
        try:
            for f in FREQUENCIES:
                if f not in active:
                    result[f][p]=0
                    continue
                gamma=geometry['gamma_S_m'][f]
                result[f][p]=_phi_gradient(sampler,phi[f],point,gamma,float(basis['metadata']['h_xy_mm']))
        except ProbeDataMissing as error:
            valid[p]=False;reasons[str(error)]=reasons.get(str(error),0)+1
    # NaN marks unsupported map samples; never repurpose native-cell scores.
    for field in result.values():field[~valid]=np.nan
    rms=np.full(len(points),np.nan);tis=rms.copy();fixed=rms.copy()
    good=np.flatnonzero(valid);direction=np.array([1/math.sqrt(2),1/math.sqrt(2),0])
    if len(good):
        rms[good]=np.sqrt(sum(np.sum(abs(v[good])**2,axis=1)/2 for v in result.values()))
        for at in range(0,len(good),128):
            _deadline(deadline,'display_direction_projection')
            ids=good[at:at+128];a=result[3000][ids];b=result[3030][ids]
            tis[ids]=2*np.minimum(abs(a@_DIRECTIONS.T),abs(b@_DIRECTIONS.T)).max(axis=1)
            fixed[ids]=2*np.minimum(abs(a@direction),abs(b@direction))
    archive=dict(points_mm=points,valid=valid,xy_axis_mm=axis,xy_depths_mm=np.array([5.,10.,15.,20.]),
                 xy_shape=np.array([4,41,41]),xz_z_mm=z,xz_shape=np.array([len(z),41]),
                 square_RMS_V_m=rms,square_maxTIS_V_m=tis,square_fixedTIS_V_m=fixed)
    for f,field in result.items():archive[f'actual_square_E_{f}_V_m']=field
    _deadline(deadline,'maps_archive')
    np.savez_compressed(output/'maps.npz',**archive)
    _deadline(deadline,'maps_archive_completed')
    return dict(status='complete_with_explicit_unsupported_samples',file='maps.npz',
        XY_depths_mm=[5.,10.,15.,20.],XZ_y_mm=0.,sample_count=len(points),valid_samples=int(valid.sum()),
        unsupported_samples=int((~valid).sum()),unsupported_reasons=reasons,
        method='Display-only E=-central finite difference of layer-aware native complex phi; not interpolated native-cell E scores',
        delta_xy_mm=delta_xy,delta_z_mm='min(0.01, distance to either actual layer plane / 4)',
        physical_interfaces_mm=[0,.1,5.1,10.1,25.1],single_normal_E_at_exact_interface='held',
        native_volume_metrics_replaced=False,spatial_gradient_or_map_convergence_validated=False,
        phasor_convention='peak +jomega_t; source/harmonic/phase coefficients applied before differencing')


def process_case(folder:Path,case:dict,output:Path,deadline_monotonic:float)->dict:
    """Consume one completed registered native basis and write new artifacts.

    ``output`` is a new case directory. C1 bases generate both actual carrier
    controls without additional PDE; waveform controls use the same loaded basis.
    Failures are recorded and raised. Existing partial outputs are not retried.
    """
    folder,output=Path(folder).resolve(),Path(output).resolve()
    if output==folder or output.is_relative_to(folder):raise ValueError('Outputs must not overwrite native basis')
    if output.exists() and any(output.iterdir()):raise FileExistsError('Refuse retry/overwrite of existing case postprocessing')
    output.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();stages=[];input_hashes={}
    def stage(name):
        _deadline(deadline_monotonic,name);stages.append(dict(stage=name,elapsed_seconds=time.monotonic()-started))
        _json(output/'progress.json',dict(status='running',id=case['id'],stages=stages))
    try:
        stage('load_and_native_validation')
        basis=_load_basis(folder,case,deadline_monotonic);input_hashes=basis['hashes']
        geometry,volume_meta=_geometry(basis,case)
        stage('waveform_and_native_volume')
        conditions=[];probe_conditions=[];maps=[];scaling_checks=[];channels=int(case['design']['channels'])
        carriers=[None] if channels==2 else list(FUNDAMENTALS)
        hashes_digest=_digest(input_hashes);code_hash=_sha(Path(__file__),deadline_monotonic)
        for carrier in carriers:
            suffix='' if carrier is None else f'-C1-{carrier}Hz'
            primary_coefficients=_coefficients(channels,'square_3h',carrier)
            primary_spectra=_spectra(basis,primary_coefficients)
            volume=evaluate_volume(primary_spectra,basis['grid'],volume_meta,
                fundamental_frequencies_Hz=FUNDAMENTALS,
                thresholds=case.get('thresholds'),fibonacci_count=2048,chunk_cells=256,
                deadline_monotonic=deadline_monotonic)
            _deadline(deadline_monotonic,'primary_volume_completed')
            volume_name='volume'+suffix+'.npz'
            np.savez_compressed(output/volume_name,**{**{k:v for k,v in volume['scalars'].items()
                if k in ('maxTIS','fixedTIS','RMS','maxTIS_direction_index')},
                **{'region_'+k+'_m3':v for k,v in volume['region_weights_m3'].items()}})
            stage('native_40_probe'+suffix)
            active={f:c for f,c in primary_coefficients.items() if np.any(c)}
            fundamentals=[f for f in active if f in FUNDAMENTALS]
            provenance=dict(source_run_id=case.get('source_run_id',folder.parent.parent.name),
                source_condition_id=case['id'],source_candidate_id=case['id']+suffix+'-square_3h',
                input_sha256=hashes_digest,code_sha256=code_hash,result_sha256=_digest(basis['validation']))
            primary_probe=evaluate_layered_probe(basis['grid'],
                {f:basis['f'][f]['potential'] for f in active},
                {f:basis['f'][f]['field'] for f in active},geometry,active,
                provenance=provenance,fundamental_frequencies_Hz=fundamentals)
            for row in primary_probe['measurements']:row.pop('time_plot',None)
            if primary_probe['status']!='complete' or not primary_probe['numerical_checks']['all_passed']:
                _json(output/('probe-failure'+suffix+'.json'),primary_probe)
                raise ValueError('Native 40-probe phi-E gate incomplete/failed; no substitute potential allowed')
            for wave in ('square_3h','sine','triangle_3h'):
                _deadline(deadline_monotonic,'wave:'+wave+suffix)
                coefficients=_coefficients(channels,wave,carrier)
                spectra=primary_spectra if wave=='square_3h' else _spectra(basis,coefficients)
                metrics=_electrical(basis,coefficients,geometry,deadline_monotonic)
                if wave=='square_3h':
                    # Re-evaluate the stored transfer operators with a distinct
                    # actual coefficient amplitude, rather than only scaling
                    # the already computed metric scalars.
                    amplitude=.73
                    changed=_electrical(basis,{f:c*amplitude for f,c in coefficients.items()},geometry,deadline_monotonic)
                    linear=('target20_modulation_V_m','target20_total_E_RMS_V_m',
                            'surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2',
                            'contact_voltage_RMS_max_V','max_source_current_RMS_mA')
                    quadratic=('SC_power_W','contact_power_W','source_power_W')
                    checks={}
                    for key in (*linear,*quadratic):
                        expected=metrics[key]*(amplitude if key in linear else amplitude**2)
                        error=abs(changed[key]/expected-1) if expected else abs(changed[key])
                        if error>2e-12:raise ValueError('Actual transfer amplitude scaling failed: '+key)
                        checks[key]=dict(expected=expected,actual=changed[key],relative_error=error,passed=True)
                    scaling_checks.append(dict(actual_carrier_Hz=carrier,amplitude=amplitude,
                        source_transfer_re_evaluated=True,new_PDE=0,checks=checks))
                volume_metrics=volume['metrics'] if wave=='square_3h' else _derive_volume(volume,spectra,wave,deadline_monotonic)
                probe=primary_probe if wave=='square_3h' else _probe_variation(primary_probe,wave,deadline_monotonic)
                identity=case['id']+suffix+'-'+wave
                conditions.append(dict(id=identity,waveform=wave,actual_fundamental_Hz=fundamentals,
                    carrier_group=[0,1] if channels==2 else [0 if carrier==3000 else 1],
                    phase_deg=[0.]*channels,source_Vpp_per_output=1.,metrics=metrics,
                    volume_metrics=volume_metrics,native_volume_archive=volume_name,
                    probe_status=probe['status'],probe_count=probe['counts']['complete'],
                    C1_two_carrier_TIS=0. if channels==1 else None))
                probe_conditions.append(dict(id=identity,waveform=wave,probe40=probe))
                _json(output/'conditions.partial.json',conditions)
                _json(output/'probes.partial.json',dict(status='partial_stage_preserved',conditions=probe_conditions,
                    time_plots_saved=False,phasors_and_full_period_statistics_saved=True))
            stage('native_phi_display_maps'+suffix)
            map_output=output if carrier is None else output/f'maps-C1-{carrier}'
            map_output.mkdir(exist_ok=True)
            maps.append(dict(actual_carrier_Hz=carrier,**_maps(basis,primary_coefficients,geometry,map_output,deadline_monotonic),
                             directory=str(map_output.relative_to(output))))
        _json(output/'probes.json',dict(status='complete',conditions=probe_conditions,
              time_plots_saved=False,phasors_and_full_period_statistics_saved=True,
              hardware='ETA5001 nominal 50x/500x with matching DSOX1202A factor, 1Mohm DC; actual switch/loading/noise/calibration held'))
        stage('source_preservation_audit')
        for path,expected in input_hashes.items():
            if _sha(Path(path),deadline_monotonic)!=expected:raise ValueError('Native source changed during postprocessing: '+path)
        square=next(c for c in conditions if c['waveform']=='square_3h')
        target=square['volume_metrics']['regions']['target']['statistics']['maxTIS']
        superficial=square['volume_metrics']['regions']['surface_0_5']['statistics']['maxTIS']
        selection_metrics=(dict(roi_p10_TIS_V_m=target['p10'],roi_mean_TIS_V_m=target['mean'],
            target_superficial_p95_ratio=target['mean']/superficial['p95'] if superficial['p95'] else None,
            surface_J_RMS_max_A_m2=square['metrics']['surface_J_RMS_max_A_m2'],
            source_power_W=square['metrics']['source_power_W']) if channels==2 else None)
        artifacts={str(p.relative_to(output)):dict(SHA256=_sha(p,deadline_monotonic),bytes=p.stat().st_size)
                   for p in sorted(output.rglob('*')) if p.is_file() and p.suffix in ('.npz','.json')
                   and p.name not in ('progress.json','failure.json')}
        result=dict(schema_version=1,status='complete',id=case['id'],
            source_normalization=NORMALIZATION,validation=basis['validation'],
            validation_gate_status=basis['validation_gate_status'],
            existing_reference_adapter=basis.get('existing_reference_adapter'),
            contact_area_validation=basis['contact_validation'],input_sha256=input_hashes,
            input_manifest_sha256=hashes_digest,postprocessor_sha256=code_hash,
            mesh_metadata=basis['metadata'],geometry_adapter=geometry['reconstruction_adapter'],
            selection_metrics=selection_metrics,conditions=conditions,maps=maps,
            actual_transfer_amplitude_scaling_checks=scaling_checks,
            artifacts=dict(probes_json='probes.json',files=artifacts),
            stages=stages,elapsed_seconds=time.monotonic()-started,
            new_PDE=0,new_Java=0,source_inputs_unchanged=True,
            holds=['Numerical conservation/native phi-E do not certify independent surface or whole-3D convergence.',
                'PBS-minus-Rs remains a dry-contact surrogate; tissue dispersion, physical/physiological response and instrumentation held.',
                'Native cell volume selectivity and display-only phi-gradient maps have separate definitions.',
                'C1 centre-RMS/ROI-RMS matching is separate downstream scaling; C1 TIS remains zero.'])
        _json(output/'summary.json',result)
        _json(output/'progress.json',dict(status='complete',id=case['id'],stages=stages))
        return result
    except Exception as error:
        failure_status=('postprocessing_timeout' if isinstance(error,TimeoutError)
                        else getattr(error,'status',None) or 'postprocessing_failed')
        _json(output/'failure.json',dict(status=failure_status,id=case.get('id'),
            error_type=type(error).__name__,error=str(error),stages=stages,
            input_sha256=input_hashes,elapsed_seconds=time.monotonic()-started,
            partial_artifacts_preserved=True,automatic_retry_authorized=False,new_PDE=0))
        raise
