"""Guarded, read-only native-complex E slice exporter; no I/O on import.

A caller must own the sole research execution lock, source/input preregistration,
resource accounting and all output. This module never solves or writes a file.
Float32 vectors are display samples; source statistics remain Float64 evidence.
"""
from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re

import numpy as np

ROOT = Path('/workspace/ngg-tis-task1')
CURRENT = Path('/dev/shm/task1-centered-c1-y0-20261025-final-r4')
C1_BASE = Path('/dev/shm/task1-centered-c1-y0-20261025-run-r2/bases/centered-square15-C1-y0-xy80-f3000')
TOP5_PLAN = ROOT/'docs/task1-top5-context-20261022/preregistration-v2.json'
REFERENCE_COMMIT = 'b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe'
TIS_ID = 'rounded-expand-f35b23a22166'
C1_ID = 'centered-square15-C1-y0-xy80-f3000'
CELLS = 351680
MAX_BYTES = 64*1024**2
ABS_DISPLAY = 1e-6
REL_DISPLAY = 2e-7
GATES = dict(max_residual=2e-7, max_power_error=2e-7, max_current_error=2e-6,
             max_area_relative_error=1e-10, max_interface_normal_current_relative_error=2e-7)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _metadata():
    """Bounded metadata only; native hashes are declarations until build()."""
    refs = {}
    def js(p):
        p = Path(p)
        require(p == p.resolve() and p.is_file() and not p.is_symlink() and p.suffix == '.json' and
                p.stat().st_size <= 4*1024**2 and (p.is_relative_to(ROOT) or p.is_relative_to(CURRENT)),
                'Bounded explicit canonical metadata required')
        raw = p.read_bytes(); refs[str(p)] = sha(raw)
        return json.loads(raw)
    publication = js(CURRENT/'immutable-result-publication.json')
    require(publication['status'] == 'published_readback_verified' and publication['commit'] == REFERENCE_COMMIT,
            'Immutable centered result identity required')
    for target, entry in publication['files'].items():
        require(entry['readback_passed'] is True and re.fullmatch('[0-9a-f]{64}', entry['SHA256']) is not None,
                'All source result files must have verified immutable readback')
    proof_by_path = {v['path']: v for v in publication['files'].values()}
    analysis = js(CURRENT/'results/analysis.json')
    cvalidation = js(CURRENT/'results/validation.json')
    stats = js(CURRENT/'results/statistics.json')
    html_path = CURRENT/'results/index.html'
    for p in (CURRENT/'results/analysis.json', CURRENT/'results/validation.json', CURRENT/'results/statistics.json', html_path):
        expected = proof_by_path[str(p)]['SHA256']
        if p.suffix == '.json': require(refs[str(p)] == expected, 'Published source metadata changed')
        refs[str(p)] = expected
    require(analysis['reference']['candidate_id'] == TIS_ID and analysis['single_pair']['case_id'] == C1_ID and
            analysis['single_pair']['source_commit'] == '2339c6b4d638294cb615d1eafa7d806b9a838f74' and
            stats['unit']['raw_source_Vpp'] == 1. and stats['unit']['frequency_Hz'] == 3000 and
            cvalidation['inputs_unchanged'] is True, 'Exact centered C1 and f35 controls required')
    plan = js(TOP5_PLAN)
    row = next(r for r in plan['catalog']['selected_layouts'] if r['condition_id'] == TIS_ID)
    condition = js(row['condition_source']['path'])
    require(refs[row['condition_source']['path']] == row['condition_source']['SHA256'] and
            condition['id'] == TIS_ID and condition['status'] == 'calculated_unadopted' and
            condition['coefficient_vectors'] == row['coefficient_vectors'], 'Frozen exact f35 complex coefficients required')
    for mapping, folder, names in (
        (cvalidation['native_files_sha256'], C1_BASE,
         ('BASIS_COMPLETE', 'mesh-metadata.json', 'validation.json', 'grid.csv.gz', 'field-3000.bin.gz')),
        (row['declared_native_inputs'], Path(row['grid']['path']).parent,
         ('BASIS_COMPLETE', 'mesh-metadata.json', 'validation.json', 'grid.csv.gz', 'field-3000.bin.gz', 'field-3030.bin.gz')),
    ):
        for name in names:
            p = str(folder/name); refs[p] = mapping[p]
    refs[row['scalar_archive']['path']] = row['scalar_archive']['SHA256']
    refs[str(Path(__file__).resolve())] = sha(Path(__file__).read_bytes())
    return dict(row=row, condition=condition, analysis=analysis, cvalidation=cvalidation, unit=stats['unit'], html_path=html_path), refs


def required_inputs():
    """Return preregistration pins without reading native arrays or importing research code."""
    return _metadata()[1]


def combine_outputs(native, coefficients):
    native = np.asarray(native, dtype=np.complex128)
    coefficients = np.asarray(coefficients, dtype=np.complex128)
    require(native.ndim == 3 and native.shape[2] == 3 and coefficients.shape == (native.shape[0],) and
            np.isfinite(native).all() and np.isfinite(coefficients).all(), 'Finite channel/native/coefficient ABI required')
    # Same-frequency output fields interfere coherently before RMS.
    return np.einsum('c,cnj->nj', coefficients, native, optimize=False)


def rms_from_components(components):
    require(len(components) > 0, 'At least one actual carrier required')
    first = np.asarray(components[0], dtype=np.complex128)
    require(first.ndim == 2 and first.shape[1] == 3, 'One vector per native cell required')
    energy = np.zeros(first.shape[0], dtype=np.float64)
    for value in components:
        value = np.asarray(value, dtype=np.complex128)
        require(value.shape == first.shape and np.isfinite(value).all(), 'Finite coherent carrier fields required')
        energy += .5*np.sum(value.real*value.real + value.imag*value.imag, axis=1)
    return np.sqrt(energy)


def instantaneous(components, time_s):
    """Independent pure reference for tests/receipts, peak +jomega*t convention."""
    require(math.isfinite(time_s) and components, 'Finite waveform time and carriers required')
    result = None
    for f, value in components.items():
        value = np.asarray(value, dtype=np.complex128)
        require(float(f) > 0 and value.ndim == 2 and value.shape[1] == 3 and np.isfinite(value).all(), 'Finite peak vectors required')
        out = value.real*math.cos(2*math.pi*float(f)*time_s)-value.imag*math.sin(2*math.pi*float(f)*time_s)
        result = out if result is None else result+out
    return result


def encode_display(value, native_indices):
    """Pack [v,u,xyz,re/im] Float32; only -1 phantom exterior is binary NaN."""
    value = np.asarray(value, dtype=np.complex128); indices = np.asarray(native_indices, dtype=int)
    require(value.ndim == 2 and value.shape[1] == 3 and np.isfinite(value).all() and indices.ndim == 2 and
            np.all((indices >= -1) & (indices < len(value))), 'Bounded slice indices and finite native E required')
    use = indices >= 0
    raw = np.full(indices.shape+(3,2), np.nan, dtype=np.float64)
    raw[use, :, 0] = value[indices[use]].real
    raw[use, :, 1] = value[indices[use]].imag
    packed = raw.astype('<f4')
    err = np.abs(packed[use].astype(np.float64)-raw[use])
    require(np.isfinite(packed[use]).all() and np.all(err <= ABS_DISPLAY+REL_DISPLAY*np.abs(raw[use])),
            'Float32 display rounding bound failed')
    return dict(shape=list(packed.shape), dtype='<f4', data_base64=base64.b64encode(packed.tobytes()).decode(),
                precision=dict(passed=True, maximum_absolute_error_V_m=float(err.max()) if err.size else 0.,
                               relative_bound=REL_DISPLAY, absolute_bound_V_m=ABS_DISPLAY,
                               scope='Display complex components only; Float64 native fields/statistics are authoritative; bounds scale with selected amplitude'))


def make_planes(grid, z_faces):
    grid = np.asarray(grid, float)
    require(grid.shape == (CELLS,5) and np.isfinite(grid).all(), 'Exact five-column native grid required')
    x,y,z = (np.unique(grid[:,i]) for i in range(3))
    require((len(x),len(y),len(z)) == (80,80,70), 'Exact h0.625/SC2/bulk14,14,40 native axes required')
    ix,iy,iz = (np.searchsorted(a,grid[:,i]) for i,a in enumerate((x,y,z)))
    linear = (iz*len(y)+iy)*len(x)+ix
    require(len(np.unique(linear)) == len(grid), 'Native grid coordinates must be unique')
    lookup = np.full((len(z),len(y),len(x)), -1, dtype=np.int32); lookup[iz,iy,ix] = np.arange(len(grid),dtype=np.int32)
    x_edges = np.r_[x-.3125, x[-1]+.3125]
    y_edges = np.r_[y-.3125, y[-1]+.3125]
    require(len(z_faces) == len(z)+1 and np.all(np.diff(z_faces)>0), 'Exact native nonuniform z faces required')
    planes = []
    def item(pid, kind, ua, va, fixed_axis, fixed_mm, requested_mm, indices):
        return dict(id=pid,kind=kind,u_label=('x [mm]' if ua is x else 'y [mm]'),
                    v_label=('depth z [mm]' if va is z else 'y [mm]'),u_mm=ua.tolist(),v_mm=va.tolist(),
                    u_edges_mm=(x_edges if ua is x else y_edges).tolist(),
                    v_edges_mm=list(z_faces) if va is z else y_edges.tolist(),
                    fixed_axis=fixed_axis,fixed_mm=float(fixed_mm),requested_mm=float(requested_mm),
                    native_indices=indices.reshape(-1).tolist(),fields={'TIS':{},'C1':{}},
                    shape=list(indices.shape),_indices=indices)
    yi = int(np.argmin(abs(y))); xi = int(np.argmin(abs(x)))
    planes.append(item('XZ','XZ',x,z,'y',y[yi],0.,lookup[:,yi,:]))
    planes.append(item('YZ','YZ',y,z,'x',x[xi],0.,lookup[:,:,xi]))
    for requested in (5.,10.,15.,17.5,20.):
        zi = int(np.argmin(abs(z-requested)))
        planes.append(item('XY_'+format(requested,'g'),'XY',x,y,'z',z[zi],requested,lookup[zi,:,:]))
    return planes,dict(x_mm=x.tolist(),y_mm=y.tolist(),z_mm=z.tolist(),z_faces_mm=list(z_faces))


def build(guard, pins=None):
    """Decode three SHA-pinned field bases under caller-owned finite guard, no writes."""
    guard(); meta, declared = _metadata(); pins = declared if pins is None else dict(pins)
    require(all(pins.get(p) == h for p,h in declared.items()), 'Preregister every exact metadata/native input before array decode')
    used = {}
    def read(p):
        guard(); p = Path(p)
        require(str(p) in pins and p == p.resolve() and p.is_file() and not p.is_symlink() and
                p.stat().st_size <= MAX_BYTES and (p.is_relative_to(ROOT) or p.is_relative_to(CURRENT) or p.is_relative_to(C1_BASE) or p==Path(__file__).resolve()),
                'Bounded canonical preregistered source/native input required')
        raw = p.read_bytes(); require(sha(raw) == pins[str(p)], 'Preregistered input changed: '+str(p)); used[str(p)] = pins[str(p)]; guard(); return raw
    def decoded(p, expected=None):
        raw = read(p); limit = MAX_BYTES if expected is None else expected
        if Path(p).suffix == '.gz':
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream: raw = stream.read(limit+1)
        require(len(raw) <= limit and (expected is None or len(raw) == expected), 'Exact bounded little-endian native size required')
        return raw
    def binary(p, shape):
        value = np.frombuffer(decoded(p,math.prod(shape)*16), dtype='<c16').reshape(shape)
        require(np.isfinite(value).all(), 'Finite actual complex128 field basis required'); return value
    def grid(p):
        result = np.loadtxt(io.BytesIO(decoded(p)), delimiter=',', skiprows=1)
        require(result.shape == (CELLS,5) and np.isfinite(result).all(), 'Native grid ABI required'); return result
    def js(p): return json.loads(read(p))
    row, condition, analysis = meta['row'],meta['condition'],meta['analysis']
    tb = Path(row['grid']['path']).parent
    for folder in (C1_BASE,tb):
        read(folder/'BASIS_COMPLETE'); validation = js(folder/'validation.json'); mesh = js(folder/'mesh-metadata.json')
        require(mesh['cells'] == CELLS and mesh['h_xy_mm'] == .625 and mesh['sc_cells'] == 2 and mesh['bulk_layer_counts'] == [14,14,40] and
                mesh['phasor_convention'] == 'peak,+jomega_t' and mesh['source_peak_V'] == .5 and mesh['source_resistance_ohm'] == 50,
                'Frozen exact mesh, circuit and peak phasor convention required')
        for key, limit in GATES.items(): require(0 <= validation[key] <= limit, 'Original native gate failed: '+key)
    cg = grid(C1_BASE/'grid.csv.gz'); tg = grid(tb/'grid.csv.gz')
    require(np.array_equal(cg,tg), 'Centered C1 and frozen TIS native grid/order must be exactly equal')
    planes,axes = make_planes(cg,row['mesh_metadata']['z_faces_mm']); del tg
    with np.load(io.BytesIO(read(row['scalar_archive']['path'])),allow_pickle=False) as archive:
        rms_saved = np.array(archive['RMS'],copy=True); weights = np.array(archive['region_target_m3'],copy=True)
    require(rms_saved.shape == weights.shape == (CELLS,) and rms_saved.dtype == weights.dtype == np.dtype('<f8') and
            np.isfinite(rms_saved).all() and np.isfinite(weights).all() and np.all(weights>=0) and weights.sum()>0,
            'Frozen Float64 RMS/fractional target masks required')
    proofs = {}; tis_energy = np.zeros(CELLS,float); coefficient_proof = {}
    selected = np.unique(np.asarray([i for plane in planes for i in plane['native_indices'] if i>=0],dtype=int))
    sample_indices = selected[np.linspace(0,len(selected)-1,17,dtype=int)]
    sample_time_s = 1./12000.
    tis_samples = {}
    # A zero coefficient at 9000/9090 means no active harmonic; no fabricated load or data.
    require(all(all(v == 0 for vector in row['coefficient_vectors'][str(f)].values() for v in vector) for f in (9000,9090)),
            'Latest f35 must be genuinely two-tone only')
    for frequency in (3000,3030):
        guard(); record = row['coefficient_vectors'][str(frequency)]
        coefficients = np.asarray(record['real'])+1j*np.asarray(record['imaginary'])
        field = combine_outputs(binary(tb/('field-'+str(frequency)+'.bin.gz'),(2,CELLS,3)),coefficients)
        tis_energy += .5*np.sum(field.real*field.real+field.imag*field.imag,axis=1)
        tis_samples[frequency] = np.array(field[sample_indices],copy=True)
        for plane in planes:
            guard(); plane['fields']['TIS'][str(frequency)] = encode_display(field,plane['_indices'])
        coefficient_proof[str(frequency)] = copy.deepcopy(record)
        del field
    tis_rms = np.sqrt(tis_energy); difference = abs(tis_rms-rms_saved)
    require(np.all(difference <= 1e-12+1e-10*abs(rms_saved)), 'Coherent two-tone vector RMS differs from frozen Float64 scalar RMS')
    proofs['TIS_full_volume_RMS_reconstruction'] = dict(passed=True,cells=CELLS,maximum_absolute_error_V_m=float(difference.max()),
        relative_tolerance=1e-10,absolute_tolerance_V_m=1e-12,definition='sqrt(sum_f sum_xyz |sum_output c_f,output E_f,output|^2 /2)')
    proofs['TIS_waveform_reference'] = dict(time_s=sample_time_s,formula='Re(sum_f E_peak,f exp(+j2pi f t))',
        native_indices=sample_indices.tolist(),field_V_m=instantaneous(tis_samples,sample_time_s).tolist())
    del tis_rms,tis_energy,difference,rms_saved,tis_samples
    field = -1j*binary(C1_BASE/'field-3000.bin.gz',(1,CELLS,3))[0]
    c1_rms = rms_from_components([field]); energy = math.sqrt(float((c1_rms*c1_rms)@weights/weights.sum()))
    expected = meta['unit']['raw_ROI_energy_RMS_V_m']
    require(math.isclose(energy,expected,rel_tol=1e-10,abs_tol=1e-12), 'Centered Float64 native ROI RMS proof changed')
    proofs['C1_ROI_energy_RMS_reconstruction'] = dict(passed=True,actual_V_m=energy,saved_V_m=expected,relative_tolerance=1e-10,absolute_tolerance_V_m=1e-12)
    for plane in planes:
        guard(); plane['fields']['C1']['3000'] = encode_display(field,plane['_indices'])
    # Save independent waveform samples for downstream browser reference assertions.
    proofs['C1_waveform_reference'] = dict(time_s=sample_time_s,formula='Re(E_peak exp(+j2pi f t))',
        native_indices=sample_indices.tolist(),field_V_m=instantaneous({3000:field[sample_indices]},sample_time_s).tolist())
    del field,c1_rms,weights
    # Verify all metadata through the same pinned reader; do not trust arbitrary labels.
    for p,h in declared.items():
        if p not in used: read(p)
    raw = read(meta['html_path']).decode('utf-8'); match = re.search(r'<script\s+id=["\']packed["\'][^>]*>([^<]+)</script>',raw)
    require(match is not None, 'Frozen centered GUI packed payload required')
    packed = base64.b64decode(match.group(1).strip(),validate=True)
    with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream: unpacked = stream.read(16*1024**2+1)
    require(len(unpacked)<=16*1024**2, 'Bounded source payload required'); source = json.loads(unpacked)
    require(source['analysis'] == analysis, 'Frozen GUI and published analysis mismatch')
    cases = {}
    for key, cid, pads, outputs, fs in (('TIS',TIS_ID,4,2,[3000,3030]),('C1',C1_ID,2,1,[3000])):
        spatial = source['spatial'][key]
        cases[key] = dict(case_id=cid,n_pads=pads,n_outputs=outputs,
            return_topology='common_GND_two_return_pads' if key=='TIS' else 'one_actual_return_pad_at_GND',
            pad_centres=copy.deepcopy(spatial['pad_centres']),physical_outlines=copy.deepcopy(spatial['physical_outlines']),
            frequencies_Hz=fs,source_resistance_ohm=50,unit='V/m')
    for plane in planes: plane.pop('_indices')
    guard()
    return dict(schema='task1-native-field-shape-display-v1',reference_result_commit=REFERENCE_COMMIT,
        new_PDE=0,analysis=copy.deepcopy(analysis),cases=cases,planes=planes,axes=axes,
        coordinate_system='x,y horizontal mm; z=0 top surface; +z is depth into fixed D50mm phantom',
        layers=[dict(name=n,z0_mm=a,z1_mm=b)for n,a,b in(('SC',0.,.1),('dermis',.1,5.1),('fat',5.1,10.1),('muscle',10.1,25.1))],
        target_ROI=dict(radius_mm=5.,depth_mm=[15.,20.]),
        field_definition='Peak complex vector E. Instantaneous arrows: Re(sum_f E_f exp(+j2pi f t)); within-frequency outputs coherently summed before time or RMS.',
        display_definition='Native cell-centre slice samples; no vector field-line interpolation; XY nearest actual cell plane is explicit; color is full-vector magnitude and arrows show the in-plane projection.',
        scale_definition='TIS raw f35 coefficients already applied exactly once; multiply only reference_amplitude_scale. C1 unit1Vpp uses -j pure sine; multiply only matched amplitude_scale or required_source_Vpp.',
        proofs=dict(**proofs,coefficient_vectors_applied_once=coefficient_proof,C1_coefficient=dict(real=0.,imaginary=-1.),
                    exact_native_grid=True,inputs_unchanged=True,native_cells=CELLS,new_PDE=0),
        source_sha256=used,
        holds=['Full SC/XY/bulk/edge/contact convergence not established; existing failures remain',
               'Nominal PBS contact is not validated skin contact; instrument loading and experiments unverified',
               'RMS equality is not waveform, modulation, vector-field, activation or safety equivalence',
               'Native layer-interface and SC maxima do not establish deep focus; direction arrows are not activation paths',
               'No new fat-validation baseline or bulk PDE is performed by this visualization export'])
