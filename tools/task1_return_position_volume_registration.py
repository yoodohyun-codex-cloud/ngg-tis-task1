"""Register the fixed five-row cached return-position volume audit; no arrays.

This metadata-only command neither solves nor runs postprocessing. NPZ/grid
digests come from completed source manifests; the actual volume audit rehashes
and decodes those files later under its own finite resource controls.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

try:
    import task1_resource_policy as policy
except ModuleNotFoundError as error:
    if error.name != 'task1_resource_policy':
        raise
    from tools import task1_resource_policy as policy

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = 'docs/cloud-continuation-20261021/volume-asymmetric-plan.json'
NEW_RUN = 'cloud-return-position-20261021T104500Z'
CASE_TABLE = (
    ('cloud-mesh-c1-20261019T190000Z', 'baseline-square15-xy80'),
    ('cloud-asymmetric-20261021T051000Z', 'asym-cross281p25-return168p75-xy80'),
    ('cloud-return-role-20261021T090200Z', 'return-cross281p25-signal168p75-xy80'),
    (NEW_RUN, 'asym-return-out0p625-xy80'),
    (NEW_RUN, 'asym-return-in0p625-xy80'),
)
SOURCES = ('tools/task1_return_position_volume_registration.py',
    'tests/test_task1_return_position_volume_registration.py',
    'tools/task1_volume_selectivity.py', 'tools/task1_results_view.py',
    'tools/task1_candidate_ranking.py', 'tools/task1_resource_policy.py')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def _regular(path, root):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve() and path.is_relative_to(root)
            and path.is_file() and not path.is_symlink(), 'Canonical local regular input required: '+str(path))
    return path


def _pin(path, refs, root, expected=None):
    path = _regular(path, root)
    digest = sha(path)
    require(expected is None or digest == expected, 'Completed metadata SHA mismatch: '+str(path))
    require(str(path) not in refs or refs[str(path)] == digest, 'Conflicting input SHA')
    refs[str(path)] = digest
    return digest


def _committed_sources(root):
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    refs = {}
    for name in SOURCES:
        path = _regular(root/name, root)
        require(subprocess.check_output(['git', 'show', commit+':'+name], cwd=root) == path.read_bytes(),
                'Commit consumed implementation/helpers/tests before registration: '+name)
        refs[str(path)] = sha(path)
    return commit, refs


def _signature(meta, config):
    values = {k: meta.get(k) for k in ('h_xy_mm', 'radius_mm', 'total_depth_mm', 'sc_cells',
        'bulk_layer_counts', 'z_faces_mm', 'tissue_boundaries_mm', 'field_reconstruction', 'source_resistance_ohm')}
    values['physical_models'] = {k: v for k, v in config.items()
        if k.endswith(('.sigma', '.epsilon_r')) or k.startswith('z.')}
    values['target'] = 'r<=5mm; surface-depth15<=z<=20mm; fractional native volume'
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def _properties(path):
    return {k.strip(): v.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#') for k, v in [line.split('=', 1)]}


def _case(root, run_id, ident, refs):
    run = root/'data-native'/run_id
    summary_path = run/'postprocess'/ident/'summary.json'
    receipt_path, pre_path = run/'cases'/(ident+'.json'), run/'preregistration.json'
    summary_sha = _pin(summary_path, refs, root)
    _pin(receipt_path, refs, root); _pin(pre_path, refs, root)
    summary, receipt, pre = read(summary_path), read(receipt_path), read(pre_path)
    matches = [c for c in pre['cases'] if c['id'] == ident]
    require(len(matches) == 1, 'One exact registered case required')
    case = matches[0]
    meta = summary['mesh_metadata']
    require(summary.get('id') == receipt.get('id') == ident and
        summary.get('status') == receipt.get('status') == 'complete' and
        receipt.get('postprocess_path') == str(summary_path) and receipt.get('postprocess_sha256') == summary_sha,
        'Original controller-completed summary receipt required: '+ident)
    require(receipt.get('config_sha256') == case['config_sha256'] == meta['config_sha256'], 'Config identity mismatch')
    reference_path = run/'reference-comparison.json'
    if reference_path.is_file():
        reference = read(reference_path)
        if reference.get('case_id') == ident:
            _pin(reference_path, refs, root)
            require(reference.get('status') == 'passed', 'Historical reference hold must remain excluded')
    config_path, mask_path = Path(case['config_file']), Path(case['mask_file'])
    _pin(config_path, refs, root, case['config_sha256']); _pin(mask_path, refs, root, case['mask_sha256'])
    require((run/'bases'/ident/'BASIS_COMPLETE').is_file(), 'Complete native basis marker required')
    require(meta.get('h_xy_mm') == .625 and meta.get('sc_cells') == 2 and
        meta.get('bulk_layer_counts') == [14, 14, 40] and meta.get('cells') == 351680,
        'Fixed same-grid h.625 SC2 bulk14/14/40 cohort required')
    circuit = case['circuit']
    require(circuit.get('n_pads') == 4 and circuit.get('n_outputs') == 2 and
        circuit.get('pad_to_node') == {'0': 'out0', '1': 'out1', '2': 'GND', '3': 'GND'} and
        circuit.get('source_resistance_ohm') == 50., 'Four-pad two-output common-ground circuit required')
    rows = [c for c in summary['conditions'] if c.get('waveform') == 'square_3h']
    require(len(rows) == 1, 'One square_3h condition required')
    condition = rows[0]
    require(condition.get('actual_fundamental_Hz') == [3000, 3030] and
        condition.get('phase_deg') == [0., 0.] and condition.get('source_Vpp_per_output') == 1. and
        condition.get('native_volume_archive') == 'volume.npz', 'Frozen raw drive/scalar definition required')
    native = summary['input_sha256']
    validations = []
    for name, digest in native.items():
        path = _regular(Path(name), root)
        require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'Native SHA256 required')
        if path.name in ('mesh-metadata.json', 'validation.json', 'BASIS_COMPLETE'):
            _pin(path, refs, root, digest)
            if path.name == 'validation.json':
                validations.append(read(path))
        elif path.name in ('grid.csv', 'grid.csv.gz'):
            refs[str(path)] = digest  # no grid bytes read by metadata registration
    native_meta = [Path(p) for p in native if Path(p).name == 'mesh-metadata.json']
    require(sum(Path(p).name in ('grid.csv', 'grid.csv.gz') for p in native) == 1, 'One native grid provenance entry required')
    require(len(native_meta) == 1 and read(native_meta[0]) == meta, 'Native/summary mesh metadata mismatch')
    require(len(validations) == 1 and all(type(validations[0].get(k)) in (int, float) and
        math.isfinite(validations[0][k]) and 0 <= validations[0][k] <= limit
        for k, limit in pre['gates'].items()), 'Completed native numerical gate evidence required')
    npz = summary_path.parent/'volume.npz'
    _regular(npz, root)  # existence only; digest is from completed artifact manifest
    npz_sha = summary['artifacts']['files']['volume.npz']['SHA256']
    require(isinstance(npz_sha, str) and re.fullmatch('[0-9a-f]{64}', npz_sha), 'Completed NPZ manifest SHA256 required')
    refs[str(npz)] = npz_sha
    probe = summary_path.parent/summary['artifacts']['probes_json']
    _pin(probe, refs, root, summary['artifacts']['files'][probe.name]['SHA256'])
    full_skin = []
    for audit in sorted((run/'audit').glob('*.json')):
        obj = read(audit)
        if obj.get('case_id') != ident or obj.get('summary_sha256') != summary_sha:
            continue
        _pin(audit, refs, root)
        if (obj.get('status') == 'computed_spatial_and_skinJ_audit' and obj.get('native_inputs_unchanged') is True and
            obj.get('registration_sha256') == refs[str(pre_path)] and obj.get('config_sha256') == case['config_sha256'] and
            obj.get('source_commit') == pre['source_commit']):
            for row in obj.get('conditions', []):
                if row.get('condition_id') == condition['id'] and 'bulk_skin_J' in row and 'layer_contact_source_losses' in row:
                    full_skin.append(dict(path=str(audit), SHA256=refs[str(audit)], summary_sha256=summary_sha))
    require(len(full_skin) == 1, 'One source-bound completed full-skin current/loss audit required: '+ident)
    manifest_path = run/'frozen-source-manifest.json'
    _pin(manifest_path, refs, root)
    manifest = read(manifest_path)
    require(manifest['source_commit'] == pre['source_commit'] and manifest['files'], 'Frozen source commit/manifest required')
    for original, frozen in manifest['files'].items():
        frozen_path = Path(frozen['path'])
        if not frozen_path.is_absolute():
            require('..' not in frozen_path.parts, 'Frozen source path cannot escape repository')
            frozen_path = root/frozen_path
        require(frozen_path.is_relative_to(run/'frozen-source') and
            pre['source_and_input_sha256'].get(original) == frozen['sha256'], 'Frozen source pin mismatch')
        _pin(frozen_path, refs, root, frozen['sha256'])
    signature = _signature(meta, _properties(config_path))
    return dict(run_id=run_id, case_id=ident, n_pads=4, n_outputs=2, circuit=circuit,
        summary=str(summary_path), summary_sha256=summary_sha, volume_npz=str(npz), volume_npz_sha256=npz_sha,
        basis_folder=str(run/'bases'/ident), registration=str(pre_path), case_receipt=str(receipt_path),
        config_sha256=case['config_sha256'], mask_sha256=case['mask_sha256'], native_expected_input_sha256=native,
        source_commit=pre['source_commit'], mesh={k: meta[k] for k in ('h_xy_mm', 'sc_cells', 'bulk_layer_counts', 'cells')},
        comparison_signature=signature, source_bound_full_skin_audit=full_skin[0],
        stored_primary_raw_statistics={m: {k: condition['volume_metrics']['regions']['target']['statistics'][m][k]
            for k in ('mean', 'p10')} for m in ('maxTIS', 'fixedTIS', 'RMS')},
        frozen_source_manifest=dict(path=str(manifest_path), SHA256=refs[str(manifest_path)])), pre


def make_preregistration(output, *, root=ROOT):
    """Write one new fixed five-case metadata plan. Never start its audit."""
    root, output = Path(root).resolve(), Path(output)
    require(output.is_absolute() and output == output.resolve() and output.is_relative_to(root/'docs')
        and output.parent.is_dir() and not output.exists() and not output.is_symlink(), 'New canonical docs plan path required')
    commit, refs = _committed_sources(root)
    ledger = policy.load_ledger(root/'runtime/task1-budget.json')
    require(policy.effective_limit(ledger) == 13800, 'Validated approved13800s policy required')
    refs.update(policy.policy_refs(ledger))
    template = root/TEMPLATE; _pin(template, refs, root)
    plan = copy.deepcopy(read(template))
    for path, digest in plan.get('frozen_definition_source_refs', {}).items():
        _pin(Path(path), refs, root, digest)
    cases, pres = [], []
    for run, ident in CASE_TABLE:
        case, pre = _case(root, run, ident, refs); cases.append(case); pres.append(pre)
    require(len({c['comparison_signature'] for c in cases}) == 1, 'All five cases require the same grid/material/contact/ROI cohort')
    baseline = cases[0]
    for case in cases:
        case.update(baseline_case_id=baseline['case_id'], baseline_summary_path=baseline['summary'],
                    baseline_summary_sha256=baseline['summary_sha256'])
    feedback = pres[-1].get('source_feedback')
    require(isinstance(feedback, dict) and feedback.get('path') and feedback.get('SHA256'), 'New return-position feedback context required')
    _pin(Path(feedback['path']), refs, root, feedback['SHA256'])
    plan.update(created_utc=datetime.now(timezone.utc).isoformat(), status='preregistered_not_executed',
        initial_case_count=5, cases=cases, baseline_case_id=baseline['case_id'],
        baseline_case_ids=[baseline['case_id']], baseline_summary_paths=[baseline['summary']],
        input_sha256=refs, purpose='Fixed return-position contrasts versus original four-square, asymmetric delta0 and role controls',
        continuation_batch_kind='fixed_return_position_cached_volume_audit',
        normalization_baseline_selection='Only original nominalRs500 h.625 SC2 four-square baseline; parent/role are comparison rows',
        new_feedback_context=dict(phase='S4', source=feedback, original_S1_audit_schema_retained=True),
        geometry_comparison_contract=dict(kind='return_position_only_with_fixed_asymmetric_shapes_areas_roles',
            new_coordinate_shifts_mm=[.625, -.625], parent_coordinate_shift_mm=0.,
            parent_and_role_controls_are_normalization_baselines=False, candidate_adopted=False),
        frozen_source_validation=dict(scope='each case frozen_source_manifest verified against its original preregistration',
            manifests=[c['frozen_source_manifest'] for c in cases]),
        implementation_source_commit=commit, resource_policy_immutable_refs=policy.policy_refs(ledger))
    plan['resources'].update(cumulative_budget_limit_seconds=13800, observed_spent_seconds=ledger['spent_seconds'],
        observed_remaining_seconds=policy.remaining_seconds(ledger), native_scalar_cell_cache_sum=5*351680,
        conservative_cached_native_bytes_estimate=5*351680*256,
        estimated_cached_plus_overhead_bytes=5*351680*256+512*1024**2, nonbaseline_case_count=4,
        budget_policy='Use validated user-approved13800s cumulative policy; charge actual audit wall time; no further automatic expansion')
    argv = ['python', str(root/'tools/task1_volume_selectivity.py'), '--preregistration', str(output),
            '--baseline-summary', baseline['summary']]
    for case in cases:
        argv += ['--summary', case['summary']]
    argv += ['--output', str(output.with_name(output.stem.removesuffix('-plan')+'.json'))]
    plan['resume_command_argv'] = argv
    plan['metadata_registration_scope'].update(native_E_phi_array_reads=False, native_grid_array_reads=False,
        volume_NPZ_decode_or_byte_read=False, new_ROI_or_normalization_calculation=False)
    final_commit, final_sources = _committed_sources(root)
    require(final_commit == commit and all(refs.get(p) == digest for p, digest in final_sources.items()),
            'Committed implementation changed during metadata registration')
    for path, digest in refs.items():
        if Path(path).name not in ('volume.npz', 'grid.csv', 'grid.csv.gz'):
            require(sha(path) == digest, 'Consumed metadata changed during registration: '+path)
    with output.open('x') as stream:
        json.dump(plan, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = make_preregistration(args.output)
    print(json.dumps(dict(status=plan['status'], cases=[c['case_id'] for c in plan['cases']],
        output=str(args.output), actual_audit_started=False, resume_command_argv=plan['resume_command_argv'])))


if __name__ == '__main__':
    main()
