"""Frequency-native readback v2; narrowly bounded full-face float roundoff.

The caller owns both execution locks, deadlines and the resource ledger. This
module reads immutable native arrays only when called and never relabels their
actual frequencies. A legacy exporter is accepted solely by the regression
comparison, not by the public frequency-native loader.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

BUNDLES=((3000,3030),(1000,1030,2000,2030))
PRODUCERS={BUNDLES[0]:('CloudFrequencyBasis','frequency_native'),
           BUNDLES[1]:('CloudFrequencyRecoveryBasis','frequency_recovery_native')}
GATES=dict(max_residual=2e-7,max_power_error=2e-7,max_current_error=2e-6,
    max_area_relative_error=1e-10,max_interface_normal_current_relative_error=2e-7)
RECONSTRUCTION='half_face_flux; top contact term averaged over full cell face h^2'
EPS0=8.8541878128e-12
REGRESSION_RELATIVE=2e-10
REGRESSION_ABSOLUTE=1e-12
NORMALIZATION=dict(source_peak_V=.5,source_Vpp=1.,source_resistance_ohm=50.,phasor_exponent='+jomega_t')
LAYERS=tuple(dict(id=i,name=name,z_min_mm=lo,z_max_mm=hi) for i,name,lo,hi in
    ((0,'sc',0.,.1),(1,'dermis',.1,5.1),(2,'fat',5.1,10.1),(3,'muscle',10.1,25.1)))


def _require(ok,message):
    if not ok:raise ValueError(message)


def _deadline(deadline,phase):
    if time.monotonic() >= deadline:raise TimeoutError('Native readback deadline: '+phase)


def _sha(path,deadline):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while True:
            _deadline(deadline,'hash:'+str(path));block=stream.read(4*1024**2)
            if not block:break
            digest.update(block)
    return digest.hexdigest()


def _path(folder,name):
    choices=[p for p in (folder/name,folder/(name+'.gz')) if p.is_file()]
    _require(len(choices) == 1 and not choices[0].is_symlink(),'One canonical native file required: '+name)
    return choices[0]


def _open(path,mode='rb'):
    return gzip.open(path,mode) if path.suffix == '.gz' else path.open(mode)


def _properties(path):
    result={}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith(('#','!')):continue
        _require('=' in line,'Explicit key=value configuration required')
        key,value=(s.strip() for s in line.split('=',1))
        _require(key and key not in result,'Duplicate or empty configuration field')
        result[key]=value
    return result


def _array(path,shape,deadline):
    _deadline(deadline,'array:'+str(path));expected=math.prod(shape)*16
    with _open(path) as stream:raw=stream.read(expected+1)
    _require(len(raw) == expected,'Exact native complex128 byte count differs: '+str(path))
    values=np.frombuffer(raw,dtype='<c16').reshape(shape)
    _require(np.isfinite(values).all(),'Nonfinite native complex array: '+str(path))
    return values


def _csv(path):
    with _open(path,'rt') as stream:rows=np.atleast_1d(np.genfromtxt(stream,delimiter=',',names=True))
    _require(rows.dtype.names and all(np.isfinite(rows[k]).all() for k in rows.dtype.names),'Nonfinite native CSV')
    return rows


def _frequency_diagnostics(row,expected_areas):
    contacts,density,source,loss=(row[k] for k in ('contacts','density','source','loss'))
    pads=contacts['pad'].astype(int);area=contacts['area_m2']
    actual=np.bincount(pads,weights=area,minlength=4)
    area_error=float(np.max(abs(actual/expected_areas-1)))
    _require(area_error <= 1e-10,'Registered physical contact area changed')
    signals=np.asarray([np.sum(density[:,pads == p]*area[pads == p],axis=1) for p in (0,1)])
    signal_error=float(np.max(abs(signals-source))/max(float(np.max(abs(source))),1e-30))
    balance_error=float(np.max(abs(np.sum(density*area,axis=1))/np.maximum(np.sum(abs(density)*area,axis=1),1e-30)))
    _require(max(signal_error,balance_error) <= 2e-6,'Source/current common-GND conservation failed')
    hermitian=float(np.max(abs(loss-loss.conj().transpose(0,2,1))))
    _require(np.allclose(loss,loss.conj().transpose(0,2,1),rtol=1e-10,atol=1e-12),'Native loss matrices are not Hermitian')
    eigenvalues=np.linalg.eigvalsh((loss+loss.conj().transpose(0,2,1))/2)
    floor=1e-14+1e-10*float(np.max(abs(loss)))
    _require(float(eigenvalues.min()) >= -floor,'Native layer loss matrix is not numerically passive')
    coefficients=[np.asarray(c,complex) for c in ((1,0),(0,1),(1,1),(1,1j),(.7+.2j,-.3+.9j))]
    coefficients += [np.random.default_rng(seed).normal(size=2)+1j*np.random.default_rng(seed+17).normal(size=2) for seed in range(3)]
    errors=[]
    for c in coefficients:
        supplied=float(.25*np.vdot(c,source@c).real)
        dissipated=float(np.einsum('i,kij,j->',c.conj(),loss,c).real)
        error=abs(supplied-dissipated)/max(abs(supplied),1e-20)
        _require(supplied >= -floor and error <= 2e-7,'Arbitrary complex coefficient energy conservation failed')
        errors.append(error)
    defect=loss.sum(axis=0)-.125*(source+source.conj().T)
    return dict(expected_pad_area_m2=expected_areas.tolist(),represented_pad_area_m2=actual.tolist(),
        max_relative_area_error=area_error,signal_node_current_relative_error=signal_error,
        all_contact_current_balance_relative_error=balance_error,
        loss_Hermitian_max_abs_error_W=hermitian,loss_eigenvalues_W=eigenvalues.tolist(),
        passivity_numerical_floor_W=floor,combined_source_power_test_relative_errors=errors,
        source_power_operator_defect_max_abs_W=float(np.max(abs(defect))),
        paired_return_current_assumption=False,native_residual_independently_recomputed=False)


def _validate_full_face_mask(mask_rows):
    """Accept only a four-epsilon representation error of exact full faces.

    The original CSV remains byte-identical. No sliver is discarded and no
    area is snapped, clipped, replaced or renormalized before the operator,
    contact current or loss calculations. This guard is stricter than the
    unchanged native1e-10 per-pad area gate and does not relax any PDE gate.
    """
    full=(.625/1000)**2
    tolerance=4*np.finfo(float).eps
    _require(mask_rows.dtype.names is not None and
        set(mask_rows.dtype.names) == {'pad','i','j','area_m2'} and len(mask_rows) == 2304 and
        all(np.isfinite(mask_rows[k]).all() for k in mask_rows.dtype.names) and
        all(np.equal(mask_rows[k],np.round(mask_rows[k])).all() for k in ('pad','i','j')) and
        np.all(mask_rows['area_m2']>0) and
        np.all(abs(mask_rows['area_m2']-full) <= tolerance*full),
        'Exact original full-face square mask required within four machine epsilons')
    keys={(int(p),int(i),int(j)) for p,i,j in zip(mask_rows['pad'],mask_rows['i'],mask_rows['j'])}
    intended=set()
    for p,(x,y) in enumerate(((-10.,-10.),(10.,10.),(10.,-10.),(-10.,10.))):
        cx,cy=round((x+25)/.625),round((y+25)/.625)
        intended.update((p,i,j) for j in range(cy-12,cy+12) for i in range(cx-12,cx+12))
    _require(keys == intended and len(keys) == 2304,'Native frequency mask changes original physical contact indices')
    return dict(schema='task1-full-face-mask-roundoff-v2',status='passed',contact_count=2304,
        full_face_area_m2=full,full_face_relative_tolerance=float(tolerance),full_face_absolute_tolerance=0.,
        maximum_relative_area_error=float(np.max(abs(mask_rows['area_m2']-full))/full),
        represented_pad_area_m2=[float(np.sum(mask_rows['area_m2'][mask_rows['pad'] == p])) for p in range(4)],
        unchanged_exact_original_indices=True,area_values_modified=False,area_renormalized=False,
        zero_or_partial_faces_accepted=False,native_numerical_gates_unchanged=True)


def _load(folder,case,deadline,*,legacy_reference=False):
    folder=Path(folder)
    _require(folder.is_absolute() and folder == folder.resolve() and folder.is_dir(),'Canonical native folder required')
    _require(case['channels'] == case.get('n_outputs',2) == 2 and case.get('n_pads',4) == 4 and
        case['h_xy_mm'] == .625 and case['sc_cells'] == 2 and list(case['bulk_counts']) == [14,14,40],
        'FixedD50 SC2/XY0.625/bulk14,14,40 four-pad/two-output case required')
    paths={n:_path(folder,n) for n in ('BASIS_COMPLETE','validation.json','mesh-metadata.json','grid.csv')}
    metadata=json.loads(paths['mesh-metadata.json'].read_text());validation=json.loads(paths['validation.json'].read_text())
    frequencies=tuple(metadata.get('frequencies_Hz',[]))
    if legacy_reference:
        _require(metadata.get('exporter_class') == 'SelectivityShapeBasis' and frequencies == (3000,3030,9000,9090),
                 'Only exact original cached four-frequency SelectivityShapeBasis regression accepted')
        selected=(3000,3030)
    else:
        _require(frequencies in BUNDLES and all(type(f) is int for f in frequencies) and
            (metadata.get('exporter_class'),metadata.get('exporter_kind')) == PRODUCERS.get(frequencies) and
            metadata.get('numerical_base_class') == 'SelectivityShapeBasis.ShapeNet', 'Honest frequency-native exporter and exact bundle required')
        _require(metadata.get('channels') == metadata.get('n_outputs') == 2 and metadata.get('n_pads') == 4 and
            metadata.get('pad_node_ids') == [0,1,-1,-1] and metadata.get('n_return_nodes') == 1 and
            metadata.get('return_topology') == 'common_GND' and metadata.get('actual_basis_RHS_solves') == 2*len(frequencies) and
            metadata.get('potential_export_basis_vectors') == 2*len(frequencies) and metadata.get('extra_potential_export_solves') == 0,
            'Actual two-output topology/RHS/potential-export accounting differs')
        _require(tuple(case.get('frequencies_Hz',frequencies)) == frequencies,'Case/native frequency bundle differs')
        selected=frequencies
        for n in ('basis-progress.json','runtime-wrapper.json'):paths[n]=_path(folder,n)
        progress=json.loads(paths['basis-progress.json'].read_text())
        wrapper=json.loads(paths['runtime-wrapper.json'].read_text())
        _require(progress.get('schema') == 'task1-frequency-basis-progress-v1' and progress.get('status') == 'complete' and
            progress.get('requested_basis_RHS_solves') == progress.get('completed_basis_RHS_solves') == 2*len(frequencies) and
            progress.get('last_frequency_Hz') == frequencies[-1] and progress.get('last_basis_channel') == 1 and
            progress.get('extra_potential_export_solves') == 0,'Incomplete actual per-RHS frequency progress receipt')
        _require(wrapper.get('runtime_wrapper_class') == PRODUCERS[frequencies][0] and
            wrapper.get('numerical_base_class') == 'SelectivityShapeBasis.ShapeNet' and
            wrapper.get('numerical_operator_modified') is False and wrapper.get('dynamic_frequency_extension') is True and
            wrapper.get('original_sources_modified') is False,'Actual frequency runtime-wrapper identity differs')
    _require(metadata.get('source_peak_V') == .5 and metadata.get('source_resistance_ohm') == 50 and
        metadata.get('phasor_convention') == 'peak,+jomega_t' and metadata.get('field_reconstruction') == RECONSTRUCTION and
        metadata.get('radius_mm') == 25 and metadata.get('total_depth_mm') == 25.1 and
        metadata.get('tissue_boundaries_mm') == [0,.1,5.1,10.1,25.1] and metadata.get('channels') == 2 and
        metadata.get('h_xy_mm') == .625 and metadata.get('sc_cells') == 2 and metadata.get('bulk_layer_counts') == [14,14,40],
        'Fixed physical geometry/normalization/mesh metadata differs')
    faces=np.asarray(metadata.get('z_faces_mm',[]),float)
    _require(faces.shape == (71,) and np.isfinite(faces).all() and faces[0] == 0 and faces[-1] == 25.1 and
        np.all(np.diff(faces)>0) and np.allclose(faces[[0,2,16,30,70]],[0,.1,5.1,10.1,25.1],rtol=0,atol=1e-12),
        'Actual fixed-layer depth faces differ')
    gates={}
    for key,limit in GATES.items():
        value=validation[key]
        _require(type(value) in (int,float) and math.isfinite(value) and 0 <= value <= limit,'Native numerical gate failed: '+key)
        gates[key]=dict(status='passed',value=value,limit=limit)
    config=Path(case['config_file']);mask=Path(case['mask_file'])
    _require(all(p.is_absolute() and p == p.resolve() and p.is_file() and not p.is_symlink() for p in (config,mask)),
             'Canonical registered config/mask required')
    hashes={str(p):_sha(p,deadline) for p in (*paths.values(),config,mask,Path(__file__).resolve())}
    _require(hashes[str(config)] == case['config_sha256'] == metadata.get('config_sha256') and
        hashes[str(mask)] == case['mask_sha256'],'Native/registered config or mask SHA differs')
    properties=_properties(config)
    _require(properties.get('frequencies') == ','.join(map(str,frequencies)) and properties.get('channels') == '2' and
        float(properties['h_mm']) == .625 and properties.get('validation.sc_cells') == '2' and
        properties.get('bulk.counts') == '14,14,40' and Path(properties['mask.path']).resolve() == mask and
        properties.get('mask.sha256') == case['mask_sha256'],'Actual native config fields differ')
    expected=np.asarray(case['expected_pad_areas_m2'],float)
    _require(expected.shape == (4,) and np.isfinite(expected).all() and np.all(abs(expected/.000225-1) <= 1e-10) and
        all(abs(float(properties[f'pad.{p}.represented_area_m2'])/expected[p]-1) <= 1e-10 for p in range(4)),
        'Four225mm2 physical contacts required')
    centres=((-10.,-10.),(10.,10.),(10.,-10.),(-10.,10.))
    for p,(x,y) in enumerate(centres):
        _require(properties.get(f'pad.{p}.shape') == 'rectangle' and
            float(properties[f'pad.{p}.width_mm']) == float(properties[f'pad.{p}.height_mm']) == 15 and
            float(properties[f'pad.{p}.x_mm']) == x and float(properties[f'pad.{p}.y_mm']) == y and
            float(properties[f'pad.{p}.rotation_deg']) == 0 and float(properties[f'pad.{p}.analytic_area_mm2']) == 225,
            'Only original fixed four-square225mm2 physical geometry is registered')
    mask_rows=_csv(mask)
    mask_receipt=_validate_full_face_mask(mask_rows)
    for f in frequencies:
        za=complex(float(properties[f'z.{f}.re']),float(properties[f'z.{f}.im']))
        _require(math.isfinite(za.real) and math.isfinite(za.imag) and za.real > 0,'Passive finite actual-frequency specific contactZ required')
    grid=_csv(paths['grid.csv']);n=len(grid)
    _require(set(grid.dtype.names) == {'x_mm','y_mm','z_mm','layer','volume_m3'} and
        n == case['cells'] == metadata['cells'] == validation['cells'] and 0 < n <= 800000 and
        validation['channels'] == 2 and np.all(grid['volume_m3']>0) and
        np.all(grid['x_mm']**2+grid['y_mm']**2 < 625) and np.all((grid['z_mm']>0)&(grid['z_mm']<25.1)) and
        np.array_equal(grid['layer'],np.searchsorted([.1,5.1,10.1],grid['z_mm'],side='right')),
        'Native actual grid dimensions/volumes/layers leave fixed phantom')
    rows={};contact_identity=None;receipts={}
    for f in selected:
        _deadline(deadline,'frequency:'+str(f))
        pf={kind:_path(folder,f'{kind}-{f}.{suffix}') for kind,suffix in
            (('field','bin'),('potential','bin'),('density','bin'),('source','bin'),('loss','bin'),('contacts','csv'))}
        hashes.update({str(p):_sha(p,deadline) for p in pf.values()})
        contacts=_csv(pf['contacts'])
        _require(set(contacts.dtype.names) == {'pad','x_mm','y_mm','area_m2'} and
            np.equal(contacts['pad'],np.round(contacts['pad'])).all() and set(contacts['pad'].astype(int)) == {0,1,2,3} and
            np.all(contacts['area_m2']>0) and np.all(contacts['x_mm']**2+contacts['y_mm']**2 < 625), 'Invalid native physical contacts')
        _require(len(contacts) == len(mask_rows) and np.array_equal(contacts['pad'],mask_rows['pad']) and
            np.array_equal(contacts['x_mm'],-25+(mask_rows['i']+.5)*.625) and
            np.array_equal(contacts['y_mm'],-25+(mask_rows['j']+.5)*.625) and
            np.array_equal(contacts['area_m2'],mask_rows['area_m2']), 'Exported physical contacts differ from registered mask order/coordinates/areas')
        xy=np.column_stack((contacts['x_mm'],contacts['y_mm']));_,indices=np.unique(xy,axis=0,return_inverse=True)
        _require(np.all(np.bincount(indices,weights=contacts['area_m2']) <= (.625/1000)**2*(1+1e-10)),
                 'Contact patches exceed native top face area')
        if contact_identity is None:contact_identity=contacts.copy()
        else:_require(np.array_equal(contact_identity,contacts),'Contact identities/order differ across actual frequencies')
        shapes=dict(field=(2,n,3),potential=(2,n),density=(2,len(contacts)),source=(2,2),loss=(6,2,2))
        row={kind:_array(pf[kind],shape,deadline) for kind,shape in shapes.items()};row['contacts']=contacts
        receipts[str(f)]=_frequency_diagnostics(row,expected);rows[f]=row
    return dict(grid=grid,f=rows,validation=validation,metadata=metadata,hashes=hashes,config=properties,
        contact_validation=receipts,validation_gate_status=gates,mask_validation=mask_receipt,case=copy.deepcopy(case),
        loader_contract='frequency-native-v2-four-epsilon-mask-roundoff' if not legacy_reference else 'legacy-regression-reference-only-v2',
        interpretation='Decoded field readback and existing numerical guards; no independently recomputed PDE residual, mesh or experimental validation')


def load_basis(folder,case,deadline):
    return _load(folder,case,deadline)


def geometry(basis,case):
    metadata,config=basis['metadata'],basis['config']
    _require(tuple(metadata['frequencies_Hz']) in BUNDLES and
        (metadata['exporter_class'],metadata['exporter_kind']) == PRODUCERS[tuple(metadata['frequencies_Hz'])],
             'Geometry requires honest actual-frequency native data')
    gamma={f:{i:complex(float(config[name+'.sigma']),2*np.pi*f*EPS0*float(config[name+'.epsilon_r']))
        for i,name in enumerate(('sc','dermis','fat','muscle'))} for f in metadata['frequencies_Hz']}
    _require(all(math.isfinite(g.real) and math.isfinite(g.imag) and g.real>0 for layers in gamma.values() for g in layers.values()),
             'Positive finite actual-frequency tissue admittivity required')
    result=dict(coordinate_system=dict(unit='mm',surface_z_mm=0.,depth_axis='+z'),radius_mm=25.,layers=copy.deepcopy(list(LAYERS)),
        z_faces_mm=metadata['z_faces_mm'],field_reconstruction='finite_volume_half_face_flux',basis_normalization=dict(NORMALIZATION),
        gamma_S_m=gamma,reconstruction_adapter=dict(source_exporter_reconstruction=RECONSTRUCTION,helper_constant='finite_volume_half_face_flux',
            actual_exporter_class=metadata['exporter_class'],frequencies_Hz=metadata['frequencies_Hz'],
            scope='Same native half-face bulk reconstruction; boundary stencils and actual skin contact remain unvalidated'))
    volume=dict(case['volume_metadata'],h_xy_mm=metadata['h_xy_mm'],radius_mm=25.,z_faces_mm=metadata['z_faces_mm'],
        layer_counts=[2,14,14,40],source_provenance=dict(case_id=case['id'],config_sha256=metadata['config_sha256']))
    return result,volume


def strict_regression_compare(newbasis,cachedbaselinefolder,deadline):
    """Compare decoded3000/3030 arrays to one completed immutable baseline."""
    _require(tuple(newbasis['metadata']['frequencies_Hz']) == BUNDLES[0] and
        newbasis['metadata']['exporter_class'] == 'CloudFrequencyBasis','Only3000/3030 producer regression is supported')
    folder=Path(cachedbaselinefolder);run=folder.parent.parent;pre=run/'preregistration.json'
    registration=json.loads(pre.read_text());matches=[c for c in registration['cases'] if c['id'] == folder.name]
    _require(len(matches) == 1,'One exact cached regression case required')
    case=matches[0];record_path=run/'cases'/(case['id']+'.json');record=json.loads(record_path.read_text())
    _require(record['status'] == 'complete' and all(record['validation'][k] <= limit for k,limit in GATES.items()),
             'Cached regression native gates must already pass')
    old=_load(folder,case,deadline,legacy_reference=True)
    pins=dict(old['hashes']);pins.update({str(p):_sha(p,deadline) for p in (pre,record_path)})
    summary=Path(record['postprocess_path']);pins[str(summary)]=_sha(summary,deadline)
    _require(pins[str(summary)] == record['postprocess_sha256'] and json.loads(summary.read_text())['status'] == 'complete',
             'Cached completed summary hash differs')
    excluded={'frequencies','mask.path','mask.sha256'}
    a,b=newbasis['config'],old['config']
    common={k for k in a if k not in excluded and not k.startswith('z.')}
    _require(common == {k for k in b if k not in excluded and not k.startswith('z.')} and all(a[k] == b[k] for k in common) and
        newbasis['case']['mask_sha256'] == case['mask_sha256'] and
        all(a[f'z.{f}.{part}'] == b[f'z.{f}.{part}'] for f in BUNDLES[0] for part in ('re','im')),
        'Regression physical operator differs beyond frequencies/config references')
    _require(np.array_equal(newbasis['grid'],old['grid']),'Regression decoded grid differs')
    comparisons=[]
    for f in BUNDLES[0]:
        _require(np.array_equal(newbasis['f'][f]['contacts'],old['f'][f]['contacts']),'Regression physical contact rows differ')
        for kind in ('field','potential','density','source','loss'):
            actual,reference=newbasis['f'][f][kind],old['f'][f][kind]
            _require(actual.shape == reference.shape,'Regression array dimensions differ')
            aa=np.ascontiguousarray(actual).view('<f8');bb=np.ascontiguousarray(reference).view('<f8')
            error=abs(aa-bb);allowed=REGRESSION_ABSOLUTE+REGRESSION_RELATIVE*abs(bb)
            comparisons.append(dict(frequency_Hz=f,array_kind=kind,shape=list(actual.shape),
                decoded_binary_byte_equal=bool(np.array_equal(aa.view('<u8'),bb.view('<u8'))),
                max_abs_component_error=float(error.max()),maximum_reference_component_abs=float(abs(bb).max()),
                failed_component_count=int(np.count_nonzero(error>allowed)),passed=bool(np.all(error<=allowed)),
                tolerance=dict(relative=REGRESSION_RELATIVE,absolute=REGRESSION_ABSOLUTE,
                    units={'field':'V/m','potential':'V','density':'A/m2','source':'A','loss':'W'}[kind])))
    hashes={**newbasis['hashes'],**pins}
    unchanged=all(_sha(Path(p),deadline) == expected for p,expected in hashes.items())
    _require(unchanged,'Native regression input changed during readback')
    return dict(schema='task1-lower-carrier-regression-v1',status='passed' if all(c['passed'] for c in comparisons) else 'failed',
        comparisons=comparisons,decoded_grid_and_contact_identity=True,input_sha256=hashes,inputs_unchanged=unchanged,
        actual_frequencies_Hz=list(BUNDLES[0]),legacy_exporter_accepted_only_as_reference=True,
        interpretation='Producer decoded-array regression only; not independent solver, skin, convergence or experimental validation')
