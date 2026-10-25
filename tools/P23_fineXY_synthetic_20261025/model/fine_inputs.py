"""Deferred metadata-only input contract for the finite B0/P23 fine-XY screen.

Import performs no I/O or scientific import. Neither public API reads masks,
native archives or Q chunks. The numerical owner authenticates those bytes
before decoding them. Canonical source identity never depends on __file__.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import re
from pathlib import Path

SOURCE = Path('/dev/shm/task1-P23-fineXY-20261025/source')
FINE = Path('/dev/shm/task1-layer-dtn-xy102-cem-20261025-run')
FINE_GRAPH = Path('/dev/shm/task1-layer-dtn-xy102-20261025-run')
COARSE_GRAPH = Path('/dev/shm/task1-layer-dtn-20261025-run')
COARSE_CEM = Path('/dev/shm/task1-layer-dtn-cem-20261025-run')
FIRST8 = Path('/dev/shm/task1-design-screen-coarse-20261025-run')
P23_RUN = Path('/dev/shm/task1-peripheral-fourpad-20261025-run')
RECOVERY = Path('/dev/shm/task1-peripheral-recovery-20261025-run')
U19 = Path('/dev/shm/task1-vs19-uniform-2000-20261025-run')
B0 = 'B0-square15-c10-diagonal'
P23 = 'P23p5-peripheral-polyomino225'
REMOTE_Q_COMMIT = 'd725ee29ee568ef26a4b7579e9dfc55d23e0681a'
MATERIAL_SHA = 'cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
CONTACT_SHA = 'cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
P23_MASK_SHA = '09f29590ff68d7768550a20013ce3748e8ff5ea2df71af746eb42577b703540d'
MAX_METADATA = 8 * 1024 ** 2
PUBLICATIONS = {
 'fine_source': (FINE/'source-publication/result-publication.json', '2927efe5653244fd690c03560c48494d815c5d13dce6d3929816fe761df594c6', '6e5e4de75d9330a60e0eb1340497c9be8318b64f'),
 'fine_result': (FINE/'result-publication/result-publication.json', '75e54e9db463091f9ab25ba357e8b6f1745225872dfbe1987dc8c7c31e3e8645', 'd2456af62d0686e06555d9e6664ee5d3504d8c64'),
 'fine_graph': (FINE_GRAPH/'result-publication/result-publication.json', '0f37e116bb0cecb17c7f9bec0c1500b41aa4b79eb415ae017a5f64eb6d71edee', 'ea11fdd9198a7e0c82d91d87f594a5063087486a'),
 'coarse_graph': (COARSE_GRAPH/'result-publication/result-publication.json', '41e21c0eb3551b628083aa8e32c5f4ddcb4a8407cfa0202f9e46ddfd064eba1f', '815327e978ec5e3976ba9a462510d6faac6f318a'),
 'coarse_cem': (COARSE_CEM/'result-publication/result-publication.json', 'd9eb06ea685eea8b00e89336d8394e34f994ef4672c453fa0844ff9aa1a8826a', 'e4c09902bf529b4111c006dd4b4fb6681ca81252'),
 'first8': (FIRST8/'result-publication/result-publication.json', 'd20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159', '4d6207caa60ae16ab7a7e997022ac72653b97ec3'),
 'first8_source': (FIRST8/'source-publication/result-publication.json', 'cb8939fdd21b3c4d7103eeb26c3591037402553d4369aa195888e30930b1eb49', 'c8e5f2f9d4fbba5646944772d526533ecedbbab1'),
 'P23_source': (P23_RUN/'source-publication/result-publication.json', 'd73f9f51cca8909849c66de98ee75bf4b4533ef07160cd098d16d7cb332f4753', '3329379d39bd8632dc75308e32dc4e30fb9296e7'),
 'P23_partial': (Path('/dev/shm/task1-local-lease-and-cloud-failure-20261025-run/failure-publication/result-publication.json'), '2cae4bdbc3580ec14653eb5b23e1b48ca15c2851323bf89386e2e02e52040a07', '2d8ad63f714e549c60e1db4d78792a193ed83c2c'),
 'P23_recovery': (RECOVERY/'result-publication/result-publication.json', '5da8f476cacd4ee323d781f08f3a0a89e7e02d64c1b3a1674069d10ee1eb698d', 'b30e7b7bd200170ff2b45f2a103c37ddff582a3f'),
 'u19_source': (U19/'source-publication.json', '5383ce0b17c9569d35af758de7fb1067ca383bf78ba2e6484441fdfe95019c78', None),
 'Q_remote': (Path('/dev/shm/task1-transfer-20261025/cache-publication-normalized.json'), 'f05f5eb7f37aabdba649ca1c445217aed82663c3bbf875b7193afd7031e35a4f', REMOTE_Q_COMMIT),
}
ORIGINAL_Q_RECEIPT = Path('/dev/shm/task1-cache-retention-20261025-run/public-receipt.json')
ORIGINAL_Q_RECEIPT_SHA = '589dad62a301761c930e03f7a74fd33d53caf550e3e5613fbcd10143c4dfd634'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''):
            h.update(block)
    return h.hexdigest()


def read_metadata(path, expected):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve() and path.is_file()
            and not path.is_symlink() and 0 < path.stat().st_size < MAX_METADATA,
            'Bounded canonical metadata: ' + str(path))
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, 'Metadata full SHA mismatch: ' + str(path))
    return json.loads(raw)


def source_inventory():
    """Canonical original source pins, stable when imported from a frozen copy."""
    require(SOURCE.is_dir() and not SOURCE.is_symlink(), 'Canonical prepared source directory')
    excluded = {'root-admission.json', 'synthetic-test-receipt.json', 'tests-receipt.json'}
    paths = sorted(p for p in SOURCE.iterdir() if p.is_file() and p.suffix in ('.py', '.json', '.md')
                   and p.name not in excluded)
    require(any(p.name == 'fine_inputs.py' for p in paths), 'Canonical input-contract source present')
    require(all(not p.is_symlink() and p.stat().st_size < MAX_METADATA for p in paths), 'Bounded regular source files')
    return {str(p): digest(p) for p in paths}


def validate_admission(admission):
    require(type(admission) is dict
            and admission.get('schema') == 'task1-P23-fineXY-root-admission-v1'
            and admission.get('status') == 'admitted_finite_P23_B0_fineXY'
            and admission.get('root_review_positive') is True
            and admission.get('sole_NUM_owner') is True, 'New explicit positive sole-root fine-XY admission required')
    fixed = dict(maximum_new_driven_RHS=3, reused_B0_2000_RHS=1,
        automatic_fourth_RHS_fallback=False, new_eigen_solves=0,
        common_depth_layer_counts=[4, 19, 18, 56], CPU_limit=4,
        total_RSS_plus_all_owned_tmpfs_bytes=8000000000,
        max_physical_evaluation_cells=800000, candidate_adopted=False,
        full_angular_metric_evaluations=2, SC4_only_angular_metric_evaluations=2,
        coarse93_bulk_angular_evaluations=0, duplicate_full_coarse_scalar_archives=False,
        old_13_of_14_failures_per_basis_preserved=True,
        source_peak_V=.5, source_high_impedance_Vpp=1., source_resistance_ohm=50.,
        physical_pairs_common_return=[[0, 2], [1, 3]],
        active_frequency_output_assignment=[[2000, 0], [2010, 1]],
        fine_B0_reuse_failure_blocks_before_new_RHS=True)
    for key, expected in fixed.items():
        require(key in admission and admission[key] == expected and type(admission[key]) is type(expected),
                'Unchanged prospective finite scope: ' + key)
    require(type(admission.get('source_sha256')) is dict, 'Root must bind exact complete canonical sources')
    require(isinstance(admission.get('decision_basis'), str) and admission['decision_basis'].strip(), 'Root decision basis')
    return admission


def published_file(publication, path, *, relative=None, expected=None, proof=None):
    """Metadata descriptor only: no file content read, including masks/Q/raw."""
    require(publication.get('status') == 'published_readback_verified'
            and re.fullmatch('[0-9a-f]{40}', publication.get('commit', '')), 'Verified actual publication')
    path = Path(path)
    require(path.is_absolute() and path == path.resolve() and not path.is_symlink(), 'Canonical descriptor path')
    tail = relative or path.name
    matches = [(key, row) for key, row in publication['files'].items() if key.endswith('/' + tail)]
    require(len(matches) == 1, 'Unique actual direct file proof: ' + tail)
    target, row = matches[0]
    require(row.get('readback_passed') is True and type(row.get('bytes')) is int and row['bytes'] > 0
            and re.fullmatch('[0-9a-f]{64}', row.get('SHA256', '')), 'Actual direct full SHA/bytes readback')
    require(expected is None or row['SHA256'] == expected, 'Expected original file identity: ' + tail)
    return dict(path=str(path), SHA256=row['SHA256'], bytes=row['bytes'], publication_target=target,
                publication_commit=publication['commit'], publication_proof=proof,
                readback_passed=True, decoded_here=False)


def validate_chunk_receipts(manifest, normalized, original, *, n, grid_name):
    """Pure proof-chain validation; never overwrites historical manifest flags."""
    require(normalized.get('status') == 'published_readback_verified'
            and normalized.get('commit') == REMOTE_Q_COMMIT
            and normalized.get('original_public_receipt_SHA256') == ORIGINAL_Q_RECEIPT_SHA,
            'Actual standard retained-Q publication receipt')
    require(original.get('schema') == 'task1-retained-cache-public-readback-receipt-v1'
            and original.get('commit') == REMOTE_Q_COMMIT and isinstance(original.get('files'), list),
            'Original retained-Q receipt list and fixed commit')
    require(manifest['shape'] == [n, n] and manifest['dtype'] == '<f8'
            and manifest['order'] == 'F', 'Exact original real-Q matrix ABI')
    original_files = {row['repo_relative_path']: row for row in original['files']}
    require(len(original_files) == len(original['files']), 'Unique original remote file proofs')
    at, total, proofs = 0, 0, []
    for chunk in manifest['chunks']:
        require(chunk['row_start'] == 0 and chunk['row_stop'] == n
                and chunk['column_start'] == at and at < chunk['column_stop'] <= n
                and chunk['dtype'] == '<f8' and chunk['order'] == 'F'
                and chunk['bytes'] == n * (chunk['column_stop'] - at) * 8,
                'Ordered disjoint complete original Q chunk ABI')
        target = 'data-native/retained-eigen-cache-20261025/' + grid_name + '/' + Path(chunk['path']).name
        require(target in normalized['files'] and target in original_files, 'Every actual Q chunk needs direct remote proof')
        a, b = normalized['files'][target], original_files[target]
        require(a['readback_passed'] is True and b['readback_passed'] is True
                and b['commit'] == REMOTE_Q_COMMIT
                and a['SHA256'] == b['SHA256'] == chunk['SHA256']
                and a['bytes'] == b['bytes'] == chunk['bytes']
                and a['Git_blob_SHA'] == b['Git_blob_SHA'], 'Exact remote Q full SHA/bytes/Git blob readback')
        proofs.append(dict(path=chunk['path'], SHA256=chunk['SHA256'], bytes=chunk['bytes'],
                           publication_target=target, publication_commit=REMOTE_Q_COMMIT,
                           Git_blob_SHA=a['Git_blob_SHA'], readback_passed=True))
        total += chunk['bytes']
        at = chunk['column_stop']
    require(at == n and total == n * n * 8, 'All Q columns/bytes authenticated without decoding')
    return proofs


def _load_publications(pins):
    publications, proof_descriptors = {}, {}
    for name, (path, sha, commit) in PUBLICATIONS.items():
        value = read_metadata(path, sha)
        require(value.get('status') == 'published_readback_verified'
                and (commit is None or value.get('commit') == commit), 'Exact original publication chain: ' + name)
        publications[name] = value
        pins[str(path)] = sha
        proof_descriptors[name] = dict(path=str(path), SHA256=sha, commit=value['commit'])
    return publications, proof_descriptors


def make_spec(admission=None):
    """Deferred small-metadata reads only; absent admission blocks first."""
    if admission is None:
        path = SOURCE / 'root-admission.json'
        require(path.is_file(), 'Positive root admission absent; fine-XY numerical work blocked')
        require(path.stat().st_size < MAX_METADATA and not path.is_symlink(), 'Bounded root admission')
        admission = json.loads(path.read_bytes())
    admission = validate_admission(copy.deepcopy(admission))
    sources = source_inventory()
    require(admission['source_sha256'] == sources, 'Admission must bind exact complete canonical source snapshot')
    pins = dict(sources)
    admission_path = SOURCE / 'root-admission.json'
    if admission_path.exists():
        require(admission_path.is_file() and not admission_path.is_symlink()
                and admission_path == admission_path.resolve()
                and 0 < admission_path.stat().st_size < MAX_METADATA,
                'Bounded canonical root decision file')
        admission_sha = digest(admission_path)
        require(read_metadata(admission_path, admission_sha) == admission,
                'Supplied and canonical root admission must agree exactly')
        pins[str(admission_path)] = admission_sha
    publications, publication_descriptors = _load_publications(pins)
    proofs = {}

    def record(pubname, path, expected=None, parse=False, relative=None):
        descriptor = published_file(publications[pubname], path, relative=relative, expected=expected,
                                    proof=publication_descriptors[pubname])
        pins[descriptor['path']] = descriptor['SHA256']
        proofs[descriptor['path']] = descriptor
        return read_metadata(path, descriptor['SHA256']) if parse else descriptor

    fine_spec = record('fine_source', FINE/'spec.json', '98840b84c321ea57ff255fec56e565277765cafda3c2aa84a96ebc28931e556c', True)
    fine_reference = record('fine_result', FINE/'reference-summary.json', '03ab3f3b269b7ddb602146d6627501d88d2a7f9efe35e0b57dcf26cb0553a507', True)
    require(fine_reference['spec'] == fine_spec and fine_reference['physical_gates_passed'] is True
            and fine_reference['actual_new_CEM_RHS'] == 2 and fine_reference['condition_frequency_Hz'] == 2000,
            'Actual completed fine B0 two-basis reference, not 2010 carrier')
    fine_raw = record('fine_result', FINE/'reference-arrays.npz', '4896db8ab0b8f873b87c09188d8b38548a470c00c68033bcdc047ccc0504b07b')
    fine_proofs = {}
    for basis in (0, 1):
        path = FINE/('rhs%d-solve-proof.json' % basis)
        descriptor = record('fine_result', path)
        proof = read_metadata(path, descriptor['SHA256'])
        require(proof['basis'] == basis and proof['passed'] is True
                and proof['physical_gates']['passed'] is True, 'Passed exact fine B0 source basis proof')
        fine_proofs[str(basis)] = dict(descriptor=descriptor, record=proof)
    old_screen_descriptor = record('fine_result', FINE/'comparison-summary.json', '29b0b4d505b770fb51e650385c03d03733b2808db5d517d9e6f0377e31165b7e')
    old_screen = read_metadata(old_screen_descriptor['path'], old_screen_descriptor['SHA256'])
    require(old_screen['old_failed_QA_flags_retained'] is True
            and old_screen['criteria_relaxed'] is False and old_screen['new_PDE_in_comparison'] == 0,
            'Original failed comparisons are retained, never cleared by this input contract')
    fine_mask = record('fine_source', FINE/'fine-mask.csv', fine_spec['mask_sha256'])
    fine_mask_receipt = record('fine_source', FINE/'fine-mask-receipt.json', fine_spec['mask_receipt_sha256'])
    fine_mask_receipt_value = read_metadata(fine_mask_receipt['path'], fine_mask_receipt['SHA256'])
    require(fine_mask_receipt_value['mask_sha256'] == fine_mask['SHA256']
            and fine_mask_receipt_value['contact_area_gate_passed'] is True, 'Actual exact fine B0 fractional geometry receipt')
    fine_faces = record('fine_source', Path(fine_spec['z_faces_path']), fine_spec['z_faces_sha256'])
    fine_faces_value = read_metadata(fine_faces['path'], fine_faces['SHA256'])
    require(fine_faces_value['layer_counts'] == [4, 19, 18, 56]
            and fine_faces_value['evaluation_cells'] == 793848
            and len(fine_faces_value['z_faces_m']) == 98,
            'Actual fine97 physical evaluation depth receipt')
    first8_spec = record('first8_source', FIRST8/'spec.json', 'c10bd163e9f8470e07a97e8adb0e8e81cdb7b0dc1b6bd9270d20bbb86ee6af4f', True)
    catalog = first8_spec['catalog']
    first8_summary_descriptor = record('first8', FIRST8/'summary.json', '1a05816b0358ecf1f6f31590c90ffb3bc7552c3b60c7a9828b1a999bf5337422')
    first8_summary = read_metadata(first8_summary_descriptor['path'], first8_summary_descriptor['SHA256'])
    b0 = next(row for row in first8_summary['candidates'] if row['candidate_id'] == B0)
    original_catalog = record('P23_partial', P23_RUN/'catalog-inputs.json', '123c580b2c9ec1128174ddb9c5840fb6f27b6d4ba351cc0039fff77cc56bcdf0', True)
    donor = next(row for row in original_catalog['candidates'] if row['candidate_id'] == P23)
    require(donor['mask_sha256'] == P23_MASK_SHA, 'Exact original P23 physical union, no donor-decorated substitution')
    p23_mask = record('P23_partial', Path(donor['mask_path']), P23_MASK_SHA)
    record('P23_source', Path(donor['mask_path']), P23_MASK_SHA)
    p23_mask_receipt = record('P23_partial', Path(donor['mask_receipt_path']), donor['mask_receipt_sha256'])
    p23_record_descriptor = record('P23_recovery', RECOVERY/'candidates'/(P23+'-summary.json'), '6318ddcfe9ed1156c3ce632e54bb2d2939d8f8f41e5f4cb0344fa3fbd90e136b')
    p23_record = read_metadata(p23_record_descriptor['path'], p23_record_descriptor['SHA256'])
    require(p23_record['geometry'] == donor and p23_record['actual_new_RHS'] == 0
            and p23_record['previous_published_RHS_reused'] == 2, 'Authentic P23 recovered metrics without new controls')
    material = record('P23_partial', P23_RUN/'input-material.json', MATERIAL_SHA)
    contact = record('P23_partial', P23_RUN/'input-contact.json', CONTACT_SHA)
    material_value = read_metadata(material['path'], material['SHA256'])
    contact_value = read_metadata(contact['path'], contact['SHA256'])
    require(catalog['material_sha256'] == original_catalog['material_sha256'] == fine_spec['material_receipt_sha256'] == MATERIAL_SHA
            and catalog['contact_sha256'] == original_catalog['contact_sha256'] == fine_spec['contact_receipt_sha256'] == CONTACT_SHA,
            'Same actually executed HREF-MIX/PBS material/contact receipts at both grid sizes')
    require(catalog['gamma_by_frequency'] == original_catalog['gamma_by_frequency']
            and catalog['z_by_frequency'] == original_catalog['z_by_frequency']
            and [r['gamma_S_m'] for r in fine_spec['material_rows']] == catalog['gamma_by_frequency']['2000']
            and fine_spec['contact_specific_impedance_ohm_m2'] == catalog['z_by_frequency']['2000'],
            'Original distinct frequency-specific gamma/contact, no 2000-to2010 copy')
    require(contact_value['Rs_subtractions'] == 1 and contact_value['measurement_area_multiplications'] == 1
            and contact_value['division_by_two'] is False, 'Contact conversion exactly once')
    coarse_raw = {name: {} for name in ('B0', 'P23')}
    coarse_proofs = {name: {} for name in ('B0', 'P23')}
    for name, cid, pubname, run in (('B0', B0, 'first8', FIRST8), ('P23', P23, 'P23_partial', P23_RUN)):
        for frequency, output in ((2000, 0), (2010, 1)):
            coarse_raw[name][str(frequency)] = record(pubname, run/'rhs'/(cid+'-'+str(frequency)+'-raw.npz'))
            path = run/'rhs'/(cid+'-'+str(frequency)+'-solve-proof.json')
            descriptor = record(pubname, path)
            proof = read_metadata(path, descriptor['SHA256'])
            require(proof['passed'] is True and proof['physical_gates']['passed'] is True
                    and proof['candidate_id'] == cid and proof['frequency_Hz'] == frequency
                    and proof['driven_output'] == output, 'Authentic actual coarse carrier/output source proof')
            coarse_proofs[name][str(frequency)] = dict(descriptor=descriptor, record=proof)
    b0_scalar = record('first8', FIRST8/'candidates'/(B0+'-scalars.npz'), b0['scalar_arrays']['SHA256'])
    p23_scalar = record('P23_recovery', RECOVERY/'candidates'/(P23+'-scalars.npz'), p23_record['scalar_arrays']['SHA256'])
    common_grid = record('first8', FIRST8/'common-grid-and-ROI.npz', 'f88e921b2d2877482ff368f39e52fea2bd4217fb70037072cda96892b5891d6b')
    roi = record('first8', FIRST8/'ROI-receipt.json', '3b2ea58b3dfb9e25d716e23e6b2f29950512efe25e396dc44560498078799e20')
    coarse_reference = record('coarse_cem', COARSE_CEM/'reference-summary.json', 'bfe77b2968dc65255f8fcee276166d11508428cb4e68278332a4ab21929bea63', True)
    coarse_faces = record('u19_source', Path(coarse_reference['spec']['z_faces_path']), coarse_reference['spec']['z_faces_sha256'])
    coarse_faces_value = read_metadata(coarse_faces['path'], coarse_faces['SHA256'])
    require(coarse_faces_value['layer_counts'] == [8,19,18,56]
            and len(coarse_faces_value['z_faces_m']) == 102,
            'Original coarse101 receipt retained separately from new common97 sampling')
    manifests, graph_arrays, graph_summaries, remote_chunks = {}, {}, {}, {}
    original_q = read_metadata(ORIGINAL_Q_RECEIPT, ORIGINAL_Q_RECEIPT_SHA)
    pins[str(ORIGINAL_Q_RECEIPT)] = ORIGINAL_Q_RECEIPT_SHA
    for name, grid_name, run, pubname, n, manifest_sha in (
        ('fine', 'xy102', FINE_GRAPH, 'fine_graph', 8184, '26da99d7edfcb24a418ab56e1091bab5cb156eccd998653631d5852108c683aa'),
        ('coarse', 'xy100', COARSE_GRAPH, 'coarse_graph', 7860, '99753623e06525d86b86cc1c659323e06012d4ddd145e02fd6fc0af514dba4ba')):
        descriptor = record(pubname, run/'summary.json')
        summary = read_metadata(descriptor['path'], descriptor['SHA256'])
        manifest_path = run/'eigen-cache/manifest.json'
        manifest = read_metadata(manifest_path, manifest_sha)
        record(pubname, manifest_path, manifest_sha, relative='local-eigen-cache-manifest.json')
        require(summary['eigen']['cache'] == manifest and summary['analytic']['passed'] is True, 'Actual graph/eigen/analytic metadata success')
        graph_arrays[name] = record(pubname, run/'arrays.npz')
        if name == 'fine':
            require(graph_arrays[name]['SHA256'] == fine_spec['phase1_arrays_sha256']
                    and publications[pubname]['commit'] == fine_spec['phase1_commit'],
                    'Fine CEM and reused fine eigen graph identity')
        graph_summaries[name] = summary
        manifests[name] = manifest
        remote_chunks[name] = validate_chunk_receipts(manifest, publications['Q_remote'], original_q, n=n, grid_name=grid_name)
        for row in remote_chunks[name]:
            require(Path(row['path']).parent == run/'eigen-cache', 'Original local cache chunk directory')
            pins[row['path']] = row['SHA256']
    original_science = {}
    for filename in ('layer_dtn_cem.py', 'frozen_layer_dtn_backend.py', 'frozen_fourier_v1.py', 'cem_compare.py', 'cem_fit.py', 'physical_projector.py'):
        original_science[filename] = record('fine_source', FINE/'source'/filename)
    return dict(schema='task1-P23-fineXY-inputs-v1', root_admission=admission,
        source_sha256=sources, input_sha256=pins, publication_file_proofs=proofs,
        publication_metadata=publication_descriptors, fine_spec=fine_spec,
        first8catalog=catalog, P23record=p23_record, P23donor=donor,
        coarse_B0_record=b0, first8_summary_descriptor=first8_summary_descriptor,
        fine_B0_raw=fine_raw, fine_B0_reference_summary=fine_reference,
        fine_B0_solve_proofs=fine_proofs, fine_B0_reuse_basis=0,
        fine_B0_mask=fine_mask, fine_B0_mask_receipt=fine_mask_receipt,
        fine_B0_mask_receipt_value=fine_mask_receipt_value,
        P23_mask=p23_mask, P23_mask_receipt=p23_mask_receipt,
        P23record_descriptor=p23_record_descriptor,
        coarse_raw=coarse_raw, coarse_solve_proofs=coarse_proofs,
        coarse_scalars=dict(B0=b0_scalar, P23=p23_scalar),
        common_grid_original=common_grid, original_ROI_receipt=roi,
        original_ROI_receipt_value=read_metadata(roi['path'], roi['SHA256']),
        cache_manifests=manifests, remote_Q_chunk_proofs=remote_chunks,
        graph_arrays=graph_arrays, graph_summaries=graph_summaries,
        eval_faces=dict(fine=fine_faces, coarse=coarse_faces),
        eval_face_receipts=dict(fine=fine_faces_value, coarse=coarse_faces_value),
        original_material_contact_receipts=dict(material=material, contact=contact),
        original_material_contact_values=dict(material=material_value, contact=contact_value),
        gamma_by_frequency=catalog['gamma_by_frequency'], z_by_frequency=catalog['z_by_frequency'],
        original_science_sources=original_science,
        old_fine_electrical_screen_descriptor=old_screen_descriptor,
        old_fine_electrical_screen=old_screen,
        execution_contract=dict(maximum_new_driven_RHS=3, reused_B0_2000_RHS=1,
            reuse_failure_blocks_before_any_new_RHS=True, automatic_fourth_RHS_fallback=False,
            new_eigen_solves=0, shared_depth_layer_counts=[4,19,18,56],
            fine_cells=793848, coarse_common97_cells=762420, max_physical_evaluation_cells=800000,
            coarse_common97_storage='New SC4 supplement only; bulk93 planes referenced from original coarse101 archives after exact physical-depth identity checks',
            scalar_storage='Fine full97 four scalars; coarse newSC4-only four-scalar patches plus authenticated original93-bulk scalar references',
            full_angular_metric_evaluations=2,SC4_only_angular_metric_evaluations=2,
            coarse93_bulk_angular_evaluations=0,duplicate_full_coarse_scalar_archives=False,
            original_coarse101_preserved=True, original_manifest_flags_preserved=True,
            original_Q_receipt_SHA256=ORIGINAL_Q_RECEIPT_SHA, remote_Q_commit=REMOTE_Q_COMMIT,
            old_13_of_14_failures_per_basis_preserved=True, candidate_adopted=False))


def required_inputs(admission=None):
    return dict(make_spec(admission)['input_sha256'])
