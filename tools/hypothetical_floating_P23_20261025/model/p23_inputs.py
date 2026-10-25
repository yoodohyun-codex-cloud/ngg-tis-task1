"""Metadata-only authentic input contract for a separately admitted comparison.

No file reads or scientific imports execute at import. Source preparation is
not admission. make_spec/required_inputs reject a missing explicit root choice.
Canonical source paths are literal; no __file__-derived identity is used.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

SOURCE = Path('/dev/shm/task1-floating-P23-comparison-20261025/source')
FAILED = Path('/dev/shm/task1-peripheral-fourpad-20261025-run')
RECOVERY = Path('/dev/shm/task1-peripheral-recovery-20261025-run')
COARSE = Path('/dev/shm/task1-design-screen-coarse-20261025-run')
PHASE1 = Path('/dev/shm/task1-layer-dtn-20261025-run')
P23 = 'P23p5-peripheral-polyomino225'
B0 = 'B0-square15-c10-diagonal'
FLOATING_ID = P23 + '__hypothetical-floating-pairs02-13'
FAILURE_PUBLICATION = Path('/dev/shm/task1-local-lease-and-cloud-failure-20261025-run/failure-publication/result-publication.json')
FAILURE_PUBLICATION_SHA = '2cae4bdbc3580ec14653eb5b23e1b48ca15c2851323bf89386e2e02e52040a07'
FAILURE_COMMIT = '2d8ad63f714e549c60e1db4d78792a193ed83c2c'
RECOVERY_PUBLICATION_SHA = '5da8f476cacd4ee323d781f08f3a0a89e7e02d64c1b3a1674069d10ee1eb698d'
RECOVERY_COMMIT = 'b30e7b7bd200170ff2b45f2a103c37ddff582a3f'
COARSE_PUBLICATION_SHA = 'd20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159'
CATALOG_SHA = '123c580b2c9ec1128174ddb9c5840fb6f27b6d4ba351cc0039fff77cc56bcdf0'
MASK_SHA = '09f29590ff68d7768550a20013ce3748e8ff5ea2df71af746eb42577b703540d'
MASK_RECEIPT_SHA = '03cdc589407f50753dbf1203723909bc1bf4f8581b915e77027da5658d26634e'
PHASE_SUMMARY_SHA = '086053634ae8329c422b16d7bd1b4777395a6925467e47c6dda254f32ad3632f'
PHASE_ARRAYS_SHA = 'f17d6962e9a1c564de85e0734c5549281168f5a7ff15bb2df85b71f5b1277154'
CACHE_MANIFEST_SHA = '99753623e06525d86b86cc1c659323e06012d4ddd145e02fd6fc0af514dba4ba'
CAP = 8000000000
FORECAST_CHILD_RSS = 800000000
FORECAST_NEW_OUTPUT = 200000000  # output forecast: 150–200 MB, reserve upper end
MAX_FILE = 80 * 1024**2
FROZEN_SOURCES = {
    'frozen_floating_cem.py': 'b3751e20fe97f6eac334c5af09c9954bfad2646748abe00128d9782524a6b17f',
    'frozen_test_floating_cem.py': '2e6f7b6f033b1d451e904f194d9c2aa92a7cc029a0c41ad650d98cfbd8197c61',
    'frozen_design_screen.py': '82c3c15cbf71ce3588e63f715df18641a3080aa8ed102d8569297745d77df537',
    'frozen_coarse_cem.py': '65567475caf2d5e48ca8959606db4923298b38daa1122e7dd18f3f20c9348323',
    'frozen_layer_dtn_backend.py': 'c470f22b3faf980b05d1e42aca86feed5da57eab3c98d467334f31d76b4ddaf8',
    'frozen_fourier_v1.py': '6d855155d823d165fb51f4ce17b9ac607a23d9850cdd806ec354b3c577d415f5',
    'provisional_field.py': '5cebbe9b18c0b5912de328cc66036e5a6abe015e268261c3a7e974d719df1e87',
    'frozen_screen_metrics.py': 'd761d3fd965f85d1cc121fac9d9fc6addb21810f12d9d18240601e8278834ba0',
    'frozen_allocation_electrical.py': '74778b09dbbbb50e43155eff0a016903d376ff426238afa95963bf86ae7549fd',
}
OWN_SOURCES = ('p23_inputs.py', 'p23_adapter.py', 'p23_comparison.py',
               'test_p23_comparison.py', 'floating_cem.py', 'COMPARISON_CONTRACT.md')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def canonical(path):
    p = Path(path)
    require(p.is_absolute() and p == p.resolve() and p.is_file() and not p.is_symlink(),
            'Canonical existing regular file: ' + str(p))
    return p


def read_json(path, sha):
    p = canonical(path)
    require(0 < p.stat().st_size <= 8 * 1024**2, 'Bounded metadata')
    raw = p.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == sha, 'Exact metadata SHA: ' + str(p))
    return json.loads(raw)


def source_inventory():
    result = {}
    for name in tuple(FROZEN_SOURCES) + OWN_SOURCES:
        path = canonical(SOURCE / name)
        sha = digest(path)
        require(name not in FROZEN_SOURCES or sha == FROZEN_SOURCES[name],
                'Byte-frozen dependency changed: ' + name)
        result[str(path)] = sha
    return result


def validate_admission(value):
    require(type(value) is dict and value.get('schema') == 'task1-floating-P23-comparison-root-admission-v1'
            and value.get('status') == 'selected_finite_hypothetical_P23_topology_comparison'
            and value.get('root_selected') is True, 'New explicit root admission required; proposal is not admission')
    required = dict(new_driven_RHS=2, new_metric_evaluations=1, control_aliases=2,
        new_common_return_RHS=0, new_B0_RHS=0, new_eigen_solves=0,
        candidate_adopted=False, actual_hardware_wiring_claimed=False,
        maximum_effective_CPU=4, total_RSS_plus_all_owned_tmpfs_bytes=CAP,
        maximum_physical_evaluation_cells=800000, physical_evaluation_cells=793860,
        root_reviewed_synthetic_MNA=True, source_allocation_amplitudes=[1.0, 1.0],
        physical_pairs=[[0, 2], [1, 3]], frequency_output_assignment=[[2000, 0], [2010, 1]],
        total_differential_series_ohm_per_output=50.0,
        forecast_child_RSS_bytes=FORECAST_CHILD_RSS, forecast_new_output_bytes=FORECAST_NEW_OUTPUT,
        existing_results_read_only=True, Windows_assignments_unchanged=True)
    for key, expected in required.items():
        require(key in value and value[key] == expected, 'Exact finite root scope: ' + key)
    require(isinstance(value.get('decision_basis'), str) and value['decision_basis'].strip(),
            'Root must record the hypothetical comparison decision')
    require(type(value.get('source_sha256')) is dict and type(value.get('synthetic_test_receipt')) is dict,
            'Explicit source snapshot and reviewed synthetic-test receipt required')
    output = Path(value.get('output_directory', ''))
    require(output.is_absolute() and output == output.resolve() and output.parent == Path('/dev/shm')
            and output.name.startswith('task1-floating-P23-comparison-20261025-run'),
            'Explicit unique root output directory for this comparison')
    return value


def check_resource_forecast(snapshot, *, raw_stage):
    """Pure check of a LIVE root-provided aggregate; absence must block build.

    Snapshot includes ALL RSS and ALL owned task1 tmpfs, including old outputs.
    At entry reserve 800 MB additional child RSS and 200 MB future output.
    The continuous root guard remains responsible for actual live enforcement.
    """
    require(type(snapshot) is dict and snapshot.get('scope') == 'ALL_RSS_plus_ALL_owned_task1_tmpfs'
            and snapshot.get('observations_current') is True, 'Current complete root aggregate resource snapshot required')
    used = snapshot.get('aggregate_bytes')
    require(type(used) is int and 0 <= used <= CAP, 'Finite actual aggregate resource usage')
    extra = FORECAST_CHILD_RSS + FORECAST_NEW_OUTPUT if raw_stage else 0
    require(used + extra <= CAP, 'BLOCKED: resource forecast exceeds unchanged 8e9 aggregate cap')
    return dict(observed_aggregate_bytes=used, reserved_additional_bytes=extra,
                forecast_aggregate_bytes=used + extra, aggregate_cap_bytes=CAP)


def file_proof(publication, root, relative, expected=None):
    require(publication.get('status') == 'published_readback_verified', 'Completed full readback publication')
    matches = [(target, row) for target, row in publication.get('files', {}).items()
               if target.endswith('/' + relative)]
    require(len(matches) == 1, 'Unique direct published identity: ' + relative)
    target, row = matches[0]
    require(row.get('readback_passed') is True and type(row.get('bytes')) is int
            and 0 < row['bytes'] <= MAX_FILE and isinstance(row.get('SHA256'), str)
            and len(row['SHA256']) == 64, 'Direct full readback SHA/byte record')
    require(expected is None or row['SHA256'] == expected, 'Frozen published identity: ' + relative)
    p = canonical(root / relative)
    require(p.stat().st_size == row['bytes'], 'Published local byte count: ' + relative)
    return dict(path=str(p), target=target, bytes=row['bytes'], SHA256=row['SHA256'],
                publication_commit=publication['commit'], readback_passed=True)


def make_spec(admission):
    admission = validate_admission(copy.deepcopy(admission))
    pins = source_inventory()
    require(admission['source_sha256'] == pins, 'Admission must bind exact canonical proposal sources')
    tests = admission['synthetic_test_receipt']
    receipt = read_json(tests['path'], tests['SHA256'])
    require(receipt.get('status') == 'passed' and receipt.get('tests_failed') == 0
            and receipt.get('tests_errors') == 0 and receipt.get('tests_skipped') == 0
            and type(receipt.get('tests_run')) is int and receipt['tests_run'] == 15
            and receipt.get('source_sha256') == pins
            and set(receipt.get('suites', [])) >= {'frozen_test_floating_cem', 'test_p23_comparison'},
            'Reviewed synthetic suites must pass against this exact source snapshot')
    pins[str(canonical(tests['path']))] = tests['SHA256']
    failure = read_json(FAILURE_PUBLICATION, FAILURE_PUBLICATION_SHA)
    require(failure.get('commit') == FAILURE_COMMIT, 'Authentic preserved failure2d publication')
    recovery_path = RECOVERY / 'result-publication/result-publication.json'
    recovery = read_json(recovery_path, RECOVERY_PUBLICATION_SHA)
    require(recovery.get('commit') == RECOVERY_COMMIT, 'Authentic completed P23 metric recovery')
    coarse_path = COARSE / 'result-publication/result-publication.json'
    coarse = read_json(coarse_path, COARSE_PUBLICATION_SHA)
    for p, sha in ((FAILURE_PUBLICATION, FAILURE_PUBLICATION_SHA),
                   (recovery_path, RECOVERY_PUBLICATION_SHA), (coarse_path, COARSE_PUBLICATION_SHA)):
        pins[str(p)] = sha
    proofs = {}

    def record(publication, root, relative, expected=None, parse=False):
        descriptor = file_proof(publication, root, relative, expected)
        pins[descriptor['path']] = descriptor['SHA256']
        proofs[descriptor['path']] = descriptor
        return read_json(descriptor['path'], descriptor['SHA256']) if parse else descriptor

    catalog = record(failure, FAILED, 'catalog-inputs.json', CATALOG_SHA, True)
    require(catalog['frequencies'] == [2000, 2010] and catalog['source_allocation_amplitudes'] == [1., 1.]
            and catalog['grid']['cells'] == 793860, 'Original fixed carriers/amplitudes/grid')
    candidate = next(row for row in catalog['candidates'] if row['candidate_id'] == P23)
    require(candidate['mask_sha256'] == MASK_SHA and candidate['mask_receipt_sha256'] == MASK_RECEIPT_SHA,
            'Original P23 physical geometry, not a later donor-decorated receipt')
    for key, expected in (('mask_path', MASK_SHA), ('mask_receipt_path', MASK_RECEIPT_SHA)):
        relative = Path(candidate[key]).relative_to(FAILED).as_posix()
        descriptor = record(failure, FAILED, relative, expected)
        require(digest(descriptor['path']) == expected, 'Exact physical mask/receipt before proposal')
    for relative in ('input-material.json', 'input-contact.json'):
        descriptor = record(failure, FAILED, relative)
        require(digest(descriptor['path']) == descriptor['SHA256'], 'Exact inherited HREF/contact receipt')
    require(catalog['material_sha256'] == pins[str(FAILED / 'input-material.json')], 'Catalog material receipt identity')
    require(catalog['contact_sha256'] == pins[str(FAILED / 'input-contact.json')], 'Catalog contact receipt identity')
    common = record(failure, FAILED, 'common-grid-and-ROI.npz',
                    'f88e921b2d2877482ff368f39e52fea2bd4217fb70037072cda96892b5891d6b')
    roi_descriptor = record(failure, FAILED, 'ROI-receipt.json',
                            '3b2ea58b3dfb9e25d716e23e6b2f29950512efe25e396dc44560498078799e20')
    roi = read_json(roi_descriptor['path'], roi_descriptor['SHA256'])
    common_raw, common_proofs = {}, {}
    expected_raw = ('9c498ded85ebf36ac0f6eb94e3c5cd07c2bb53ddc361e4d716844c509b91755e',
                    'a1d9319ff4fa9bf38ce2dde0630fe37ebc0abf7240fa5949a4fc9dfb5143ca4b')
    expected_proofs = ('bf922b8d11aef50bfcff9057779fef42e8bdce2fe87240e523be9b64a641f1f3',
                       '7d5cccf0ecd9bd494a9408d6739c93a9e3dfa58dde01662dcd17de92ccfdbd06')
    for i, f in enumerate((2000, 2010)):
        common_raw[str(f)] = record(failure, FAILED, 'rhs/' + P23 + '-' + str(f) + '-raw.npz', expected_raw[i])
        desc = record(failure, FAILED, 'rhs/' + P23 + '-' + str(f) + '-solve-proof.json', expected_proofs[i])
        proof = read_json(desc['path'], desc['SHA256'])
        require(proof.get('passed') is True and proof.get('physical_gates', {}).get('passed') is True
                and proof.get('candidate_id') == P23 and proof.get('frequency_Hz') == f
                and proof.get('driven_output') == i, 'Passed actual frequency/output-specific common P23 solve')
        common_proofs[str(f)] = dict(desc, record=proof)
    p23_desc = record(recovery, RECOVERY, 'candidates/' + P23 + '-summary.json',
                      '6318ddcfe9ed1156c3ce632e54bb2d2939d8f8f41e5f4cb0344fa3fbd90e136b')
    p23_record = read_json(p23_desc['path'], p23_desc['SHA256'])
    require(p23_record['geometry'] == candidate and p23_record['actual_new_RHS'] == 0
            and p23_record['previous_published_RHS_reused'] == 2, 'Exact recovered common P23 identity; no new common solve')
    p23_scalar = record(recovery, RECOVERY, 'candidates/' + P23 + '-scalars.npz',
                        'c0dc6d2490c82432666ec0247474c170184f86393fc83061ff421efdc3b55ef1')
    b0_desc = record(failure, FAILED, 'candidates/' + B0 + '-alias-proof.json',
                     '7d08f6d3fbb46da55e8842647147bb865e3378876321608735cb9bc3a83fb39e')
    b0_record = read_json(b0_desc['path'], b0_desc['SHA256'])
    require(b0_record['actual_new_RHS'] == b0_record['actual_new_metric_evaluations'] == 0
            and b0_record.get('no_field_reconstruction') is True and b0_record.get('no_angular_recalculation') is True,
            'B0 remains an untouched complete original common-return alias')
    b0_raw = {str(f): record(coarse, COARSE, 'rhs/' + B0 + '-' + str(f) + '-raw.npz') for f in (2000, 2010)}
    b0_scalar = record(coarse, COARSE, 'candidates/' + B0 + '-scalars.npz',
                       'b1d33c6875ae54a38468473c2f7b163bc9ad3777d1fc314ee4827a4ed196634f')
    for row in (p23_record, b0_record):
        require(row['metrics']['status'] == 'calculated_provisional_complete'
                and row['normalizations']['status'] == 'complete'
                and all(p.get('passed') is True for p in row['source_physics_proofs']),
                'Cached controls retain completed full metrics and passed source physics')
    phase_summary = read_json(PHASE1 / 'summary.json', PHASE_SUMMARY_SHA)
    manifest = read_json(PHASE1 / 'eigen-cache/manifest.json', CACHE_MANIFEST_SHA)
    require(manifest['shape'] == [7860, 7860] and manifest['dtype'] == '<f8', 'Exact original cached real-Q ABI')
    pins[str(PHASE1 / 'summary.json')] = PHASE_SUMMARY_SHA
    pins[str(PHASE1 / 'arrays.npz')] = PHASE_ARRAYS_SHA
    pins[str(PHASE1 / 'eigen-cache/manifest.json')] = CACHE_MANIFEST_SHA
    for chunk in manifest['chunks']:
        require(Path(chunk['path']).parent == PHASE1 / 'eigen-cache', 'Original local cache chunk location')
        pins[chunk['path']] = chunk['SHA256']
    return dict(schema='task1-hypothetical-floating-P23-inputs-v1', root_admission=admission,
        input_sha256=pins, publication_file_proofs=proofs, catalog=catalog,
        physical_candidate=candidate, floating_candidate_id=FLOATING_ID,
        common_grid_ROI=common, ROI_receipt=roi, phase1_graph=phase_summary['graph'],
        common_P23=dict(record_descriptor=p23_desc, record=p23_record, scalar=p23_scalar,
                        raw_by_frequency=common_raw, solve_proofs_by_frequency=common_proofs),
        common_B0=dict(record_descriptor=b0_desc, record=b0_record, scalar=b0_scalar,
                       raw_by_frequency=b0_raw),
        provenance=dict(failure2d_commit=FAILURE_COMMIT, recovered_metrics_commit=RECOVERY_COMMIT,
                        hypothetical_only=True, actual_wiring_claim=False),
        new_driven_RHS=2, new_metric_evaluations=1, immutable_common_alias_conditions=2)


def required_inputs(admission):
    return dict(make_spec(admission)['input_sha256'])
