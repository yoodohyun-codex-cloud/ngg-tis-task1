"""Root-admitted, finite single-pair comparison. Import is inert and stdlib only.

No solver, array, eigen, worker, lock, lease or Git action is performed here on
import. The sole numerical owner supplies its guard and resource watchdog.
"""
from __future__ import annotations
import bisect
import gc
import hashlib
import importlib
import json
import math
import sys
import time
from pathlib import Path

SOURCE = Path('/dev/shm/task1-single-pair-refresh-20261025/source')
MODEL = Path('/dev/shm/task1-design-screen-coarse-20261025-run/source/model')
BASE_RUN = Path('/dev/shm/task1-design-screen-coarse-20261025-run')
PHASE = Path('/dev/shm/task1-layer-dtn-20261025-run')
SPEC_SHA = 'c10bd163e9f8470e07a97e8adb0e8e81cdb7b0dc1b6bd9270d20bbb86ee6af4f'
PHASE_SUMMARY_SHA = '086053634ae8329c422b16d7bd1b4777395a6925467e47c6dda254f32ad3632f'
PHASE_ARRAY_SHA = 'f17d6962e9a1c564de85e0734c5549281168f5a7ff15bb2df85b71f5b1277154'
CACHE_SHA = '99753623e06525d86b86cc1c659323e06012d4ddd145e02fd6fc0af514dba4ba'
SCIENCE_SHA = {
    'design_screen.py': '82c3c15cbf71ce3588e63f715df18641a3080aa8ed102d8569297745d77df537',
    'frozen_coarse_cem.py': '65567475caf2d5e48ca8959606db4923298b38daa1122e7dd18f3f20c9348323',
    'frozen_layer_dtn_backend.py': 'c470f22b3faf980b05d1e42aca86feed5da57eab3c98d467334f31d76b4ddaf8',
    'frozen_fourier_v1.py': '6d855155d823d165fb51f4ce17b9ac607a23d9850cdd806ec354b3c577d415f5',
    'provisional_field.py': '5cebbe9b18c0b5912de328cc66036e5a6abe015e268261c3a7e974d719df1e87',
}
COUNTS = (8, 19, 18, 56)
INTERFACES_MM = (0., .1, 5.1, 10.1, 25.1)
LAYERS = ('sc', 'dermis', 'fat', 'muscle')
REGIONS = ('total', 'target', 'surface_0_5', 'subsurface_5_10', 'remaining', 'off_target')
LINEAR_BURDENS = ('contact_normal_J_RMS_max_A_m2', 'contact_normal_J_RMS_P95_A_m2',
                  'contact_voltage_RMS_max_V', 'skin_vector_J_RMS_max_A_m2',
                  'skin_vector_J_RMS_P95_A_m2')
POWER_BURDENS = ('SC_power_W', 'skin_power_W', 'contact_power_W')
BASELINE_IDS = ('B0-square15-c10-diagonal', 'G1-square12-c10-diagonal',
                'G2-square15-c8-diagonal', 'G3-square16-c9p5-diagonal',
                'G4-equalarea-rect12p5x18-c9p75x9p5-diagonal',
                'G5-signal200-return250', 'G6-signal250-return200',
                'G7-square15-c10-adjacent')
MAX_ARCHIVE_BYTES = 80 * 1024 ** 2


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''):
            h.update(block)
    return h.hexdigest()


def read_metadata(path, expected=None):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve() and path.is_file()
            and not path.is_symlink() and path.stat().st_size < 8 * 1024 ** 2,
            'Bounded canonical metadata required: ' + str(path))
    raw = path.read_bytes()
    require(expected is None or sha_bytes(raw) == expected, 'Metadata SHA mismatch: ' + str(path))
    return json.loads(raw)


def new_json(path, value):
    with Path(path).open('xb') as stream:
        stream.write(encoded(value))


def check(guard, deadline):
    guard()
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError('Single-pair comparison incomplete; deadline reached')


def complex_value(value):
    return complex(value['real'], value['imaginary'])


def complex_pair(value):
    return dict(real=float(complex(value).real), imaginary=float(complex(value).imag))


def geometries():
    return [dict(candidate_id='single-pair-square15-c%g-y0' % centre,
                 physical_pads=2, connected_sources=1, total_contact_area_mm2=450.,
                 pads=[dict(physical_pad_id=p, center_mm=[sign * centre, 0.],
                            width_mm=15., height_mm=15., area_mm2=225.,
                            node='source0' if p == 0 else 'GND', top_only=True)
                       for p, sign in ((0, -1.), (1, 1.))])
            for centre in (12.5, 15.)]


def _descriptor(value):
    require(isinstance(value, dict) and set(('path', 'SHA256')).issubset(value),
            'Actual file path/SHA256 descriptor required')
    path = Path(value['path'])
    require(path.is_absolute() and path == path.resolve() and not path.is_symlink(),
            'Canonical immutable input path required')
    require(len(value['SHA256']) == 64 and all(c in '0123456789abcdef' for c in value['SHA256']),
            'Full lowercase SHA256 required')
    return value


def _published_descriptor(value, refs):
    """Authenticate raw identities through actual small publication metadata."""
    _descriptor(value)
    proof = _descriptor(value['publication_proof'])
    publication = read_metadata(proof['path'], proof['SHA256'])
    require(publication['status'] == 'published_readback_verified'
            and publication['commit'] == value['publication_commit'], 'Actual publication commit/readback proof')
    row = publication['files'][value['publication_target']]
    require(row['SHA256'] == value['SHA256'] and row['readback_passed'] is True,
            'Actual full file SHA readback proof: ' + value['publication_target'])
    if 'bytes' in value:
        require(row['bytes'] == value['bytes'], 'Published input byte length')
    refs[proof['path']] = proof['SHA256']
    refs[value['path']] = value['SHA256']


def _admission(admission):
    if admission is None:
        path = SOURCE / 'root-admission.json'
        require(path.is_file(), 'Positive sole-root admission is not provided; numerical work blocked')
        admission = read_metadata(path)
    elif isinstance(admission, (bytes, str)):
        admission = json.loads(admission)
    require(isinstance(admission, dict)
            and admission.get('schema') == 'task1-single-pair-refresh-root-admission-v1'
            and admission.get('status') == 'admitted_single_pair_comparison'
            and admission.get('root_review_positive') is True
            and admission.get('sole_NUM_owner') is True
            and admission.get('maximum_new_driven_RHS') == 2
            and admission.get('CPU_limit') == 4
            and admission.get('total_RSS_plus_all_owned_tmpfs_bytes') == 8000000000
            and admission.get('max_physical_evaluation_cells') == 800000
            and admission.get('candidate_adopted') is False,
            'Explicit positive root admission and unchanged whole-task resource limits required')
    selected = admission['selected_TIS_reference']
    require(selected.get('selection_completed_by_root') is True
            and selected.get('candidate_id') and selected.get('publication_commit'),
            'Root must select the actual latest admitted TIS candidate before execution')
    _descriptor(selected['summary'])
    require(isinstance(selected.get('record_pointer'), list), 'Explicit selected-record JSON pointer list required')
    require(set(selected['raw_by_frequency']) == {'2000', '2010'}, 'Exactly two existing TIS carrier descriptors')
    for row in selected['raw_by_frequency'].values():
        _descriptor(row)
    for key in ('common_grid', 'ROI_receipt', 'baseline8_summary'):
        _descriptor(admission[key])
    require(admission['common_grid'].get('publication_commit') == '4d6207caa60ae16ab7a7e997022ac72653b97ec3',
            'Original published first-eight common grid/ROI required')
    require(admission['common_grid']['SHA256'] == 'f88e921b2d2877482ff368f39e52fea2bd4217fb70037072cda96892b5891d6b',
            'Exact original common-grid/ROI archive required')
    return admission


def _at(value, pointer):
    for key in pointer:
        value = value[key]
    return value


def _metadata_inputs(admission):
    catalog = read_metadata(BASE_RUN / 'spec.json', SPEC_SHA)['catalog']
    refs = {str(BASE_RUN / 'spec.json'): SPEC_SHA}
    for filename in ('single_pair_refresh.py', 'test_single_pair_refresh.py', 'contract.json'):
        path = SOURCE / filename
        require(path.is_file() and not path.is_symlink(), 'Fixed canonical source identity')
        refs[str(path)] = file_sha(path)
    for key in ('material', 'contact'):
        path, expected = catalog[key + '_path'], catalog[key + '_sha256']
        read_metadata(path, expected)
        refs[path] = expected
    config = Path('/dev/shm/task1-vs19-uniform-2000-20261025-run/configs/baseline-square15-human-sine2000-sc8-vs19uniform-bulk19-18-56-xy100.properties')
    require(config.is_file() and not config.is_symlink() and config.stat().st_size < 8 * 1024 ** 2
            and file_sha(config) == 'a20334ff9788323b065c89968cd18d764e813beb4017879bdc390f19a4db6445',
            'Exact executed original configuration body')
    refs[str(config)] = 'a20334ff9788323b065c89968cd18d764e813beb4017879bdc390f19a4db6445'
    phase = read_metadata(PHASE / 'summary.json', PHASE_SUMMARY_SHA)
    manifest = read_metadata(PHASE / 'eigen-cache/manifest.json', CACHE_SHA)
    publication = read_metadata(PHASE / 'result-publication/result-publication.json')
    require(publication['status'] == 'published_readback_verified'
            and publication['commit'] == '815327e978ec5e3976ba9a462510d6faac6f318a',
            'Original published graph/eigen cache identity')
    for name, expected in (('summary.json', PHASE_SUMMARY_SHA), ('arrays.npz', PHASE_ARRAY_SHA),
                           ('local-eigen-cache-manifest.json', CACHE_SHA)):
        proof = publication['files']['data-native/cloud-layer-dtn-phase1-20261025/' + name]
        require(proof['SHA256'] == expected and proof['readback_passed'] is True,
                'Actual full publication proof required: ' + name)
    require(manifest['shape'] == [7860, 7860] and manifest['dtype'] == '<f8'
            and manifest['order'] == 'F' and phase['eigen']['cache'] == manifest,
            'Same real cached graph basis, without eigen work')
    for path, expected in ((PHASE / 'summary.json', PHASE_SUMMARY_SHA),
                           (PHASE / 'arrays.npz', PHASE_ARRAY_SHA),
                           (PHASE / 'eigen-cache/manifest.json', CACHE_SHA)):
        refs[str(path)] = expected
    refs[str(PHASE / 'result-publication/result-publication.json')] = file_sha(PHASE / 'result-publication/result-publication.json')
    for row in manifest['chunks']:
        refs[row['path']] = row['SHA256']  # metadata proof only; no raw cache read
    for filename, expected in SCIENCE_SHA.items():
        require(file_sha(MODEL / filename) == expected, 'Pinned existing science source differs')
        refs[str(MODEL / filename)] = expected
    for key in ('common_grid', 'ROI_receipt', 'baseline8_summary'):
        row = admission[key]
        _published_descriptor(row, refs)
        if key != 'common_grid':
            read_metadata(row['path'], row['SHA256'])
    selected = admission['selected_TIS_reference']
    _published_descriptor(selected['summary'], refs)
    record = _at(read_metadata(selected['summary']['path'], selected['summary']['SHA256']), selected['record_pointer'])
    require(record['candidate_id'] == selected['candidate_id'], 'Selected record identity')
    require(record['metrics']['frequencies_Hz'] == [2000, 2010], 'Actual two-carrier reference')
    refs[selected['summary']['path']] = selected['summary']['SHA256']
    for row in selected['raw_by_frequency'].values():
        _published_descriptor(row, refs)  # actual publication proof, never read raw input here
    baselines = read_metadata(admission['baseline8_summary']['path'], admission['baseline8_summary']['SHA256'])
    rows = _at(baselines, admission.get('baseline8_records_pointer', ['candidates']))
    require(tuple(row['candidate_id'] for row in rows) == BASELINE_IDS, 'Original eight burden references, fixed order')
    return catalog, phase, manifest, refs


def required_inputs(admission=None):
    """Metadata-only input inventory. No scientific imports or archive reads."""
    admitted = _admission(admission)
    _, _, _, refs = _metadata_inputs(admitted)
    return refs


def make_spec(admission=None):
    """Freeze root selection, actual gamma/contact bytes and two y=0 geometries."""
    admitted = _admission(admission)
    catalog, _, _, refs = _metadata_inputs(admitted)
    return dict(schema='task1-single-pair-refresh-spec-v1', admission=admitted,
                admission_sha256=sha_bytes(encoded(admitted)), input_sha256=refs,
                geometries=geometries(), source=dict(connected_sources=1, physical_pads=2,
                    frequency_Hz=2000, high_impedance_Vpp=1., peak_V=.5, series_resistance_ohm=50.,
                    return_node='GND', other_instrument_channel='not attached to any physical pad'),
                gamma_by_frequency=catalog['gamma_by_frequency'], z_by_frequency=catalog['z_by_frequency'],
                material_sha256=catalog['material_sha256'], contact_sha256=catalog['contact_sha256'],
                original_config_sha256='a20334ff9788323b065c89968cd18d764e813beb4017879bdc390f19a4db6445',
                original_config_body=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run/configs/baseline-square15-human-sine2000-sc8-vs19uniform-bulk19-18-56-xy100.properties').read_text(),
                science_source_sha256=dict(SCIENCE_SHA), original_source_commits=dict(
                    graph='815327e978ec5e3976ba9a462510d6faac6f318a',
                    physical_top_CEM='e4c09902bf529b4111c006dd4b4fb6681ca81252',
                    baseline8='4d6207caa60ae16ab7a7e997022ac72653b97ec3',
                    P23_recovery='b30e7b7bd200170ff2b45f2a103c37ddff582a3f'),
                grid=dict(radius_mm=25., h_mm=.5, nxy=7860, planes=101,
                          layer_counts=list(COUNTS), layer_thickness_mm=[.1, 5., 5., 15.],
                          cells=793860, maximum_cells=800000),
                centre_xyz_mm=[0., 0., 20.], maximum_new_driven_RHS=2,
                no_existing_PDE_repeat=True, new_eigen_solves=0,
                raw_frame_rule='One case/frequency Q frame writes state/phi/E/proof, returns, GC, then RMS/J metrics; no Q during metrics',
                modulation=dict(single_carrier_envelope_AM_10Hz_V_m=0., angular_search_performed=False,
                                carrier_RMS_is_not_TIS_modulation=True, activation_equivalence_claimed=False),
                holds=dict(provisional_discrete_XY_field=True, full_convergence=False,
                           experimental_validation=False, anatomical_validation=False,
                           safety_claim=False, activation_claim=False, old_failures_preserved=True,
                           candidate_adopted=False))


def one_source_contact_equations(tissue, phi, metal, physical_pads, cells, areas, z, resistance=50.):
    """Small scalar reference for physical two-pad signed CEM contract tests."""
    require(len(tissue) == len(phi) and resistance > 0 and complex(z).real > 0, 'Passive scalar contract')
    surface, by_pad = list(tissue), [0j, 0j]
    for pad, cell, area in zip(physical_pads, cells, areas):
        require(pad in (0, 1) and area > 0, 'Exactly physical source0/return1 contacts')
        outward = area / z * (phi[cell] - (metal if pad == 0 else 0j))
        surface[cell] += outward
        by_pad[pad] += outward
    return surface, metal / resistance - by_pad[0], by_pad


def field_vector_rms(vectors):
    """Long-time vector RMS from distinct-frequency complex peak vectors."""
    return math.sqrt(sum(sum(abs(complex(v)) ** 2 for v in field) for field in vectors) / 2.)


def roi_rms_from_stats(mean, std):
    require(mean >= 0 and std >= 0 and math.isfinite(mean + std), 'Finite RMS-field mean and std')
    return math.hypot(mean, std)


def scaled_electrical(electrical, scale):
    """Only amplitude rescaling; it cannot simultaneously match eight burdens."""
    require(scale > 0 and math.isfinite(scale), 'Finite positive amplitude scale')
    linear = set(LINEAR_BURDENS) | {'sum_output_current_RMS_A_bookkeeping',
             'source_current_RMS_A', 'return_current_RMS_A', 'source_Vpp_each'}
    powers = set(POWER_BURDENS) | {'source_power_W', 'source_resistor_power_W', 'skin_plus_contact_power_W'}
    result = {}
    for key, value in electrical.items():
        if key in linear:
            result[key] = float(value) * scale
        elif key in powers:
            result[key] = float(value) * scale ** 2
        elif key == 'layers_power_W':
            result[key] = {name: float(v) * scale ** 2 for name, v in value.items()}
        elif key in ('source_current_RMS_by_output_A', 'physical_pad_current_RMS_A'):
            result[key] = [float(v) * scale for v in value]
        elif key in ('source_current_peak_A', 'return_current_peak_A'):
            result[key] = complex_pair(complex_value(value) * scale)
        else:
            result[key] = value
    result['amplitude_scale_from_1Vpp'] = scale
    return result


def _science():
    """Lazy scientific import occurs only inside the admitted numerical frame."""
    for filename, expected in SCIENCE_SHA.items():
        require(file_sha(MODEL / filename) == expected, 'Science source changed before NUM')
    sys.path.insert(0, str(MODEL))
    frozen = importlib.import_module('design_screen')
    for module in (frozen, frozen.base, frozen.base.kernel, frozen.base.kernel.f, frozen.provisional_field):
        name = Path(module.__file__).name
        require(name in SCIENCE_SHA and file_sha(module.__file__) == SCIENCE_SHA[name],
                'Loaded scientific module must have exact pinned source bytes')
    return frozen


def _archive(np, path, **arrays):
    with Path(path).open('xb') as stream:
        np.savez_compressed(stream, **arrays)
    require(Path(path).stat().st_size < MAX_ARCHIVE_BYTES, 'Raw archive exceeds 80 MiB bound')
    return dict(path=str(path), bytes=Path(path).stat().st_size, SHA256=file_sha(path))


def _load_archive(np, descriptor):
    _descriptor(descriptor)
    path = Path(descriptor['path'])
    require(path.is_file() and path.stat().st_size < MAX_ARCHIVE_BYTES
            and file_sha(path) == descriptor['SHA256'], 'Full raw archive SHA before decode')
    return np.load(path, allow_pickle=False)


def _contacts(np, xy, geometry):
    pads, cells, areas = [], [], []
    for pad in geometry['pads']:
        cx, cy = pad['center_mm']
        require(cy == 0. and pad['width_mm'] == pad['height_mm'] == 15., 'Corrected y=0 square geometry')
        require(all(x * x + y * y < 25. ** 2 for x in (cx - 7.5, cx + 7.5)
                    for y in (-7.5, 7.5)), 'Whole rectangles inside the D50 top')
        mask = ((xy[:, 0] * 1000 > cx - 7.5) & (xy[:, 0] * 1000 < cx + 7.5)
                & (xy[:, 1] * 1000 > -7.5) & (xy[:, 1] * 1000 < 7.5))
        selected = np.flatnonzero(mask)
        require(len(selected) == 900, '900 exact full .5mm faces per 225mm2 pad')
        pads.extend([0 if pad['physical_pad_id'] == 0 else 2] * len(selected))
        cells.extend(selected.tolist())
        areas.extend([.0005 ** 2] * len(selected))
    require(len(set(cells)) == 1800, 'Exactly two disjoint pads')
    return np.asarray(pads, np.int32), np.asarray(cells, np.int32), np.asarray(areas, float)


def _raw_frame(spec, geometry, guard, deadline, out):
    """Own every Q/profile/field reference in this one raw-production frame."""
    check(guard, deadline)
    import numpy as np
    frozen = _science()
    phase, manifest = frozen.base._phase1_metadata()
    Q, cacheproof = frozen.base._load_cache(np, manifest, guard, deadline)
    require(file_sha(PHASE / 'arrays.npz') == PHASE_ARRAY_SHA, 'Exact graph/eigen raw SHA')
    with np.load(PHASE / 'arrays.npz', allow_pickle=False) as saved:
        eigen = np.array(saved['eigenvalues_per_m2'], copy=True)
        xy = np.array(saved['XY_m'], copy=True)
        ij = np.array(saved['ij'], copy=True)
    require(Q.shape == (7860, 7860) and eigen.shape == (7860,) and xy.shape == ij.shape == (7860, 2), 'Frozen graph ABI')
    require(sha_bytes(xy.astype('<f8', copy=False).tobytes()) == phase['graph']['XY_float64_le_SHA256']
            and sha_bytes(ij.astype('<i4', copy=False).tobytes()) == phase['graph']['ij_int32_le_SHA256'], 'Exact graph ordering')
    _, _, zs = frozen.base.kernel.f.make_grid(.5, 8, [19, 18, 56])
    zs = np.asarray(zs, float)
    layerids = np.repeat(np.arange(4), COUNTS)
    require(len(zs) == 101 and len(zs) * len(xy) == 793860, 'Registered physical cell cap')
    pads, cells, areas = _contacts(np, xy, geometry)
    profile = frozen._profiles(np, Q, eigen, [complex_value(v) for v in spec['gamma_by_frequency']['2000']], zs, guard, deadline)
    solution = frozen._solve(np, Q, profile, pads, cells, areas,
                             complex_value(spec['z_by_frequency']['2000']), 0, guard, deadline)
    physical = np.where(pads == 0, 0, 1).astype(np.int32)
    by_pad = [complex(solution['contact_current'][physical == p].sum()) for p in (0, 1)]
    dummy_metal = complex(solution['metal'][1])
    dummy_current = complex(solution['source_current'][1])
    logical_absent_currents = [complex(solution['contact_current'][pads == p].sum()) for p in (1, 3)]
    scale = max(abs(by_pad[0]), abs(by_pad[1]), 1e-12)
    topology = dict(physical_pad_ids=[0, 1], electrical_nodes=['source0', 'GND'],
                    physical_pad_current_into_tissue_peak_A=[complex_pair(v) for v in by_pad],
                    unused_dummy_metal_peak_V=complex_pair(dummy_metal),
                    unused_dummy_output_current_peak_A=complex_pair(dummy_current),
                    absent_logical1_and3_contact_current_peak_A=[complex_pair(v) for v in logical_absent_currents],
                    relative_physical_return_KCL=abs(sum(by_pad)) / scale,
                    connected_sources=1, original_other_instrument_channel_attached=False,
                    no_logical1_or3_contact_patches=not bool(np.any((pads == 1) | (pads == 3))),
                    unused_dummy_unknown_explanation='Unattached algebraic unknown at zero through 50ohm; no second physical output connected')
    topology['passed'] = (abs(dummy_metal) <= 1e-14 and abs(dummy_current) <= 1e-16
                          and topology['relative_physical_return_KCL'] <= 2e-6
                          and topology['no_logical1_or3_contact_patches']
                          and all(v == 0j for v in logical_absent_currents))
    proof = dict(solution['proof'], candidate_id=geometry['candidate_id'], frequency_Hz=2000,
                 physical_topology=topology, connected_sources=1, physical_pads=2)
    proof['legacy_solver_source_current_peak_A_including_unattached_dummy'] = proof.pop('source_current_peak_A')
    proof['connected_source_current_peak_A'] = [complex_pair(solution['source_current'][0])]
    proof.pop('two_basis_reciprocity', None)
    proof['two_basis_reciprocity'] = 'not applicable to one connected source; no extra RHS run'
    new_json(out / (geometry['candidate_id'] + '-solve-proof.json'), proof)
    state = _archive(np, out / (geometry['candidate_id'] + '-surface-state.npz'),
                     phi_surface_peak_V=solution['phi_surface'],
                     connected_source_metal_peak_V=solution['metal'][:1],
                     unused_dummy_metal_peak_V=solution['metal'][1:],
                     source_current_peak_A=solution['source_current'][:1],
                     unused_dummy_current_peak_A=solution['source_current'][1:],
                     modal_surface_coeff=solution['coeff'],
                     contact_current_peak_A=solution['contact_current'],
                     contact_physical_pad_id=physical,
                     contact_electrical_node_code=np.where(physical == 0, 0, -1),
                     contact_xy_index=cells, contact_area_m2=areas)
    require(proof['passed'] and topology['passed'], 'Unchanged CEM gates and one-source topology must pass; raw iterate retained')
    phi, E, interface = frozen._fields(np, Q, profile, solution, ij, layerids, guard, deadline)
    raw = _archive(np, out / (geometry['candidate_id'] + '-2000-raw.npz'),
                   phi_peak_V=phi, E_peak_V_m=E,
                   interface_downward_J_peak_A_m2=interface,
                   modal_surface_coeff=solution['coeff'],
                   phi_surface_peak_V=solution['phi_surface'],
                   connected_source_metal_peak_V=solution['metal'][:1],
                   unused_dummy_metal_peak_V=solution['metal'][1:],
                   source_current_peak_A=solution['source_current'][:1],
                   contact_current_peak_A=solution['contact_current'],
                   contact_normal_J_peak_A_m2=solution['contact_J'],
                   contact_drop_peak_V=solution['contact_drop'],
                   contact_physical_pad_id=physical,
                   contact_electrical_node_code=np.where(physical == 0, 0, -1),
                   legacy_solver_contact_code=pads, contact_xy_index=cells,
                   contact_area_m2=areas, layer_complex_power_W=solution['layer_power'])
    for row in cacheproof:
        check(guard, deadline)
        require(file_sha(row['path']) == row['SHA256'], 'Q cache SHA after frame')
        row['after_passed'] = True
    receipt = dict(candidate_id=geometry['candidate_id'], actual_new_driven_RHS=1,
                   state=state, raw=raw, proof=proof, cache_proof=cacheproof,
                   Q_references_returned=False, raw_frame_complete=True)
    new_json(out / (geometry['candidate_id'] + '-raw-receipt.json'), receipt)
    return receipt  # no Q, array, profile, solution or field escapes this frame


def _axis_stencil(axis, value):
    nearest = min(range(len(axis)), key=lambda i: abs(axis[i] - value))
    if abs(axis[nearest] - value) <= 1e-9:
        return [(nearest, 1.)]
    high = bisect.bisect_right(axis, value)
    require(0 < high < len(axis), 'Point interpolation forbids extrapolation')
    low = high - 1
    fraction = (value - axis[low]) / (axis[high] - axis[low])
    return [(low, 1. - fraction), (high, fraction)]


def centre_stencil(np, grid):
    """Physical same-layer trilinear E weights; centre is never nearest-cell E."""
    require(grid.shape == (793860, 5), 'Original full common-grid ABI')
    xy = grid[:7860, :2]
    zs = [float(v) for v in grid[::7860, 2]]
    layers = [int(v) for v in grid[::7860, 3]]
    require(np.array_equal(grid[:, :2], np.tile(xy, (101, 1)))
            and np.array_equal(grid[:, 2], np.repeat(zs, 7860))
            and np.array_equal(grid[:, 3], np.repeat(layers, 7860)), 'Depth-major matched actual XY nodes')
    xs = sorted(set(float(v) for v in xy[:, 0]))
    ys = sorted(set(float(v) for v in xy[:, 1]))
    xw, yw = _axis_stencil(xs, 0.), _axis_stencil(ys, 0.)
    indices = [i for i, layer in enumerate(layers) if layer == 3]
    zw_local = _axis_stencil([zs[i] for i in indices], 20.)
    zw = [(indices[i], w) for i, w in zw_local]
    require(all(10.1 < zs[i] < 25.1 for i, _ in zw), 'Centre interpolation stays in muscle')
    lookup = {(round(float(x), 9), round(float(y), 9)): i for i, (x, y) in enumerate(xy)}
    rows = []
    for iz, wz in zw:
        for iy, wy in yw:
            for ix, wx in xw:
                key = (round(xs[ix], 9), round(ys[iy], 9))
                require(key in lookup, 'All trilinear physical corners represented')
                rows.append(dict(native_cell_index=iz * 7860 + lookup[key],
                                 weight=wz * wy * wx, xyz_mm=[xs[ix], ys[iy], zs[iz]], layer=3))
    require(abs(sum(r['weight'] for r in rows) - 1.) < 1e-12, 'Unit interpolation weight sum')
    return rows


def sample_field_vector(E, stencil):
    return [sum(row['weight'] * complex(E[row['native_cell_index'], component])
                for row in stencil) for component in range(3)]


def _weighted_stats(np, values, weights):
    use = np.flatnonzero(weights > 0)
    require(len(use) > 0 and np.isfinite(values).all() and np.isfinite(weights).all()
            and np.all(weights >= 0), 'Finite values and positive weighted volume')
    w = weights[use]
    v = values[use]
    total = float(w.sum())
    mean = float(np.dot(w, v) / total)
    order = np.argsort(v, kind='stable')
    cumulative = np.cumsum(w[order])
    result = dict(volume_m3=total, mean=mean,
                  std=float(np.sqrt(np.dot(w, (v - mean) ** 2) / total)),
                  rms=float(np.sqrt(np.dot(w, v * v) / total)),
                  min=float(v.min()), max=float(v.max()))
    for name, fraction in (('p10', .1), ('p95', .95)):
        k = min(int(np.searchsorted(cumulative, fraction * total, side='left')), len(order) - 1)
        result[name] = float(v[order[k]])
    return result


def _load_grid(np, admission):
    with _load_archive(np, admission['common_grid']) as saved:
        grid = np.array(saved['grid'], copy=True)
        weights = {region: np.array(saved[region + '_volume_weight_m3'], copy=True) for region in REGIONS}
    require(grid.shape == (793860, 5) and np.isfinite(grid).all(), 'Actual original full grid')
    require(np.allclose(weights['total'], grid[:, 4], rtol=1e-12, atol=1e-25)
            and np.allclose(weights['off_target'], weights['total'] - weights['target'], rtol=1e-12, atol=1e-25),
            'Original fractional volume weights preserved')
    return grid, weights


def _tis_reference_metrics(np, spec, grid, weights, stencil, guard, deadline):
    selected = spec['admission']['selected_TIS_reference']
    record = _at(read_metadata(selected['summary']['path'], selected['summary']['SHA256']), selected['record_pointer'])
    squared = np.zeros(len(grid), float)
    centre_vectors = []
    for frequency in ('2000', '2010'):
        check(guard, deadline)
        descriptor = selected['raw_by_frequency'][frequency]
        with _load_archive(np, descriptor) as saved:
            E = np.array(saved[descriptor.get('E_key', 'E_peak_V_m')], copy=True)
        require(E.shape == (len(grid), 3) and np.isfinite(E).all(), 'Actual selected two-carrier vector field')
        centre_vectors.append(sample_field_vector(E, stencil))
        squared += np.sum(abs(E) ** 2, axis=1) / 2.
        del E
    roi = math.sqrt(float(np.dot(weights['target'], squared) / weights['target'].sum()))
    stored = record['metrics']['regions']['target']['statistics']['RMS']
    from_stats = roi_rms_from_stats(float(stored['mean']), float(stored['std']))
    require(abs(roi - from_stats) <= 1e-10 + 1e-9 * roi, 'TIS ROI RMS raw field and stored mean/std agree')
    return dict(candidate_id=selected['candidate_id'], publication_commit=selected['publication_commit'],
                centre_vector_RMS_V_m=field_vector_rms(centre_vectors), target_volume_RMS_V_m=roi,
                target_RMS_from_stored_mean_std_V_m=from_stats,
                centre_carrier_peak_vectors_V_m=[[complex_pair(v) for v in row] for row in centre_vectors],
                electrical=record['metrics']['electrical'], actual_new_driven_RHS=0,
                angular_computation_performed=False)


def _single_metrics(np, spec, geometry, receipt, grid, weights, stencil, guard, deadline, out):
    check(guard, deadline)
    with _load_archive(np, receipt['raw']) as saved:
        E = np.array(saved['E_peak_V_m'], copy=True)
        J = np.array(saved['contact_normal_J_peak_A_m2'], copy=True)
        drop = np.array(saved['contact_drop_peak_V'], copy=True)
        areas = np.array(saved['contact_area_m2'], copy=True)
        physical = np.array(saved['contact_physical_pad_id'], copy=True)
        currents = np.array(saved['contact_current_peak_A'], copy=True)
        layer_power = np.array(saved['layer_complex_power_W'], copy=True)
    require(E.shape == (len(grid), 3) and np.isfinite(E).all(), 'Complete single carrier E')
    centre = sample_field_vector(E, stencil)
    rms = np.sqrt(np.sum(abs(E) ** 2, axis=1) / 2.)
    del E
    layers = grid[:, 3].astype(int)
    gamma = np.asarray([complex_value(v) for v in spec['gamma_by_frequency']['2000']])
    jrms = abs(gamma[layers]) * rms
    regions = {region: _weighted_stats(np, rms, w) for region, w in weights.items()}
    skin = _weighted_stats(np, jrms, weights['total'] * (layers <= 1))
    contact = _weighted_stats(np, abs(J) / math.sqrt(2.), areas)
    by_pad = [complex(currents[physical == pad].sum()) for pad in (0, 1)]
    proof = receipt['proof']
    electrical = dict(source_Vpp_each=1., source_current_RMS_A=abs(by_pad[0]) / math.sqrt(2.),
        return_current_RMS_A=abs(by_pad[1]) / math.sqrt(2.),
        source_current_RMS_by_output_A=[abs(by_pad[0]) / math.sqrt(2.)],
        physical_pad_current_RMS_A=[abs(v) / math.sqrt(2.) for v in by_pad],
        source_current_peak_A=complex_pair(by_pad[0]), return_current_peak_A=complex_pair(by_pad[1]),
        sum_output_current_RMS_A_bookkeeping=abs(by_pad[0]) / math.sqrt(2.),
        source_power_W=float(proof['source_complex_power_W']['real']),
        source_resistor_power_W=float(proof['source_resistor_power_W']),
        contact_power_W=float(proof['contact_complex_power_W']['real']),
        layers_power_W={name: float(layer_power[i].real) for i, name in enumerate(LAYERS)},
        SC_power_W=float(layer_power[0].real), skin_power_W=float(layer_power[:2].real.sum()),
        skin_plus_contact_power_W=float(layer_power[:2].real.sum()) + float(proof['contact_complex_power_W']['real']),
        contact_normal_J_RMS_max_A_m2=contact['max'], contact_normal_J_RMS_P95_A_m2=contact['p95'],
        contact_voltage_RMS_max_V=float(abs(drop).max() / math.sqrt(2.)),
        skin_vector_J_RMS_max_A_m2=skin['max'], skin_vector_J_RMS_P95_A_m2=skin['p95'])
    scalars = _archive(np, out / (geometry['candidate_id'] + '-RMS-J-scalars.npz'),
                       RMS_V_m=rms, Jtotal_vector_RMS_A_m2=jrms)
    return dict(candidate_id=geometry['candidate_id'], geometry=geometry,
                centre_vector_RMS_V_m=field_vector_rms([centre]),
                centre_carrier_peak_vector_V_m=[complex_pair(v) for v in centre],
                target_volume_RMS_V_m=regions['target']['rms'], regions=regions,
                electrical=electrical, scalars=scalars, raw=receipt['raw'], state=receipt['state'],
                source_physics_proof=proof, actual_new_driven_RHS=1,
                single_carrier_envelope_AM_10Hz_V_m=0., TIS_angular_computation_performed=False,
                carrier_RMS_is_not_TIS_modulation=True, candidate_adopted=False)


def _burden_ratios(electrical, references):
    rows = []
    for reference in references:
        baseline = reference['metrics']['electrical']
        ratios = {}
        for key in LINEAR_BURDENS + POWER_BURDENS:
            require(float(baseline[key]) > 0., 'Positive original baseline burden denominator')
            ratios[key] = float(electrical[key]) / float(baseline[key])
        rows.append(dict(candidate_id=reference['candidate_id'], ratios=ratios,
                         all_eight_burdens_no_larger=all(v <= 1. for v in ratios.values())))
    return rows


def build(spec, guard, deadline_monotonic=None, output_dir=None):
    """Called only by the admitted sole NUM owner with external aggregate guard."""
    require(callable(guard) and spec == make_spec(spec.get('admission')), 'Exact frozen spec and owner guard')
    check(guard, deadline_monotonic)
    require(output_dir is not None, 'Explicit new owner-created output directory')
    out = Path(output_dir)
    require(out.is_absolute() and out == out.resolve() and out.is_dir()
            and not out.is_symlink() and out.parent == Path('/dev/shm'), 'Canonical unique tmpfs run directory')
    require(not (out / 'summary.json').exists(), 'Never overwrite a prior run')
    raw_receipts = []
    release = []
    for geometry in spec['geometries']:
        raw_receipts.append(_raw_frame(spec, geometry, guard, deadline_monotonic, out))
        collected = gc.collect()  # frame and every Q reference have exited before metrics
        release.append(dict(candidate_id=geometry['candidate_id'], raw_frame_returned=True,
                            GC_collections=collected, Q_passed_to_metrics=False))
        new_json(out / (geometry['candidate_id'] + '-Q-release-boundary.json'), release[-1])
        check(guard, deadline_monotonic)
    require(sum(row['actual_new_driven_RHS'] for row in raw_receipts) == 2, 'Exactly two new physical RHS')
    import numpy as np
    grid, weights = _load_grid(np, spec['admission'])
    stencil = centre_stencil(np, grid)
    new_json(out / 'centre-physical-interpolation.json', dict(
        physical_point_xyz_mm=[0., 0., 20.], method='same-layer physical-coordinate trilinear complex vector E interpolation',
        z_positive='down from physical top', components_interpolated_before_magnitude=True,
        potential_difference_substituted_for_field=False, nearest_cell_substituted=False, stencil=stencil))
    reference = _tis_reference_metrics(np, spec, grid, weights, stencil, guard, deadline_monotonic)
    base = spec['admission']['baseline8_summary']
    baselines = _at(read_metadata(base['path'], base['SHA256']), spec['admission'].get('baseline8_records_pointer', ['candidates']))
    records = []
    for geometry, receipt in zip(spec['geometries'], raw_receipts):
        record = _single_metrics(np, spec, geometry, receipt, grid, weights, stencil, guard, deadline_monotonic, out)
        record['fixed_1Vpp_joint_burdens_vs_baseline8'] = _burden_ratios(record['electrical'], baselines)
        matches = {}
        for label, metric in (('same_centre20mm_vector_RMS', 'centre_vector_RMS_V_m'),
                              ('same_target_volume_RMS', 'target_volume_RMS_V_m')):
            require(record[metric] > 0 and reference[metric] > 0, 'Positive distinct RMS match criteria')
            scale = reference[metric] / record[metric]
            electrical = scaled_electrical(record['electrical'], scale)
            matches[label] = dict(amplitude_scale=scale, required_source_high_impedance_Vpp=scale,
                source_setting_reference='Original single-pair 1Vpp preserved',
                centre_vector_RMS_V_m=record['centre_vector_RMS_V_m'] * scale,
                target_volume_RMS_V_m=record['target_volume_RMS_V_m'] * scale,
                electrical=electrical,
                all_eight_burdens_vs_each_original_baseline=_burden_ratios(electrical, baselines),
                equal_RMS_does_not_imply_equal_TIS_modulation_or_activation=True,
                single_carrier_envelope_AM_10Hz_V_m=0.)
        record['separate_RMS_matches_to_selected_TIS'] = matches
        record['fixed_1Vpp_ratios_to_selected_TIS'] = {
            key: record[key] / reference[key] for key in ('centre_vector_RMS_V_m', 'target_volume_RMS_V_m')}
        new_json(out / (geometry['candidate_id'] + '-summary.json'), record)
        records.append(record)
        gc.collect()
        check(guard, deadline_monotonic)
    summary = dict(schema='task1-single-pair-refresh-result-v1',
        status='calculated_provisional_single_pair_comparison_unadopted', spec=spec,
        selected_TIS_reference=reference, candidates=records, actual_new_driven_RHS=2,
        new_eigen_solves=0, existing_PDE_repeated=False, TIS_angular_computation_performed=False,
        Q_release_boundaries=release, Q_resident_during_metrics=False,
        ROI_receipt=read_metadata(spec['admission']['ROI_receipt']['path'], spec['admission']['ROI_receipt']['SHA256']),
        definitions=dict(single_centre_RMS='norm(interpolated complex E2000 peak)/sqrt(2)',
            TIS_centre_RMS='sqrt((norm(interpolated E2000)^2+norm(interpolated E2010)^2)/2)',
            target_volume_RMS='sqrt(sum(target_fractional_volume*carrier_vector_RMS^2)/sum(target_fractional_volume))',
            TIS_ROI_mean_std_identity='target_volume_RMS=sqrt(mean(RMS_field)^2+std(RMS_field)^2)',
            scaling='All E/phi/current/contact-voltage quantities linear; source/contact/tissue/50ohm power quadratic',
            single_carrier_AM='Zero 10Hz envelope modulation; single-carrier RMS never labelled TIS modulation',
            burden_comparison='Eight separate original joint burden constraints; an RMS match does not automatically match burdens'),
        holds=spec['holds'], candidate_adopted=False, Windows_saved_verified=False)
    new_json(out / 'summary.json', summary)
    return dict(summary=summary, arrays={})
