"""Metadata-only registration of six cached source/return-position results."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

try:
    import task1_return_position_volume_registration as inherited
except ModuleNotFoundError as error:
    if error.name != 'task1_return_position_volume_registration':
        raise
    from tools import task1_return_position_volume_registration as inherited

ROOT = Path(__file__).resolve().parents[1]
NEW_RUN = 'cloud-source-position-20261021T110000Z'
CASE_TABLE = (*inherited.CASE_TABLE[:2], *inherited.CASE_TABLE[3:],
    (NEW_RUN, 'asym-source-in0p625-xy80'), (NEW_RUN, 'asym-source-in1p25-xy80'))
SOURCES = ('tools/task1_source_position_volume_registration.py',
    'tests/test_task1_source_position_volume_registration.py', *inherited.SOURCES)
RETURN_REPORT = 'docs/cloud-extended-20261021T102700Z/volume-return-position.json'


def _committed_sources(root):
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    refs = {}
    for name in SOURCES:
        path = inherited._regular(root/name, root)
        inherited.require(subprocess.check_output(['git', 'show', commit+':'+name], cwd=root) == path.read_bytes(),
                          'Commit consumed implementation/helpers/tests before registration: '+name)
        refs[str(path)] = inherited.sha(path)
    return commit, refs


def make_preregistration(output, *, root=ROOT):
    root, output = Path(root).resolve(), Path(output)
    inherited.require(output.is_absolute() and output == output.resolve() and output.is_relative_to(root/'docs')
        and output.parent.is_dir() and not output.exists() and not output.is_symlink(), 'New canonical docs plan path required')
    commit, refs = _committed_sources(root)
    ledger = inherited.policy.load_ledger(root/'runtime/task1-budget.json')
    inherited.require(inherited.policy.effective_limit(ledger) == 13800, 'Validated approved13800s policy required')
    refs.update(inherited.policy.policy_refs(ledger))
    template = root/inherited.TEMPLATE
    inherited._pin(template, refs, root)
    plan = copy.deepcopy(inherited.read(template))
    for path, digest in plan.get('frozen_definition_source_refs', {}).items():
        inherited._pin(Path(path), refs, root, digest)
    cases, pres = [], []
    for run, ident in CASE_TABLE:
        case, pre = inherited._case(root, run, ident, refs)
        cases.append(case); pres.append(pre)
    inherited.require(len({c['comparison_signature'] for c in cases}) == 1,
                      'All six cases require the same grid/material/contact/ROI cohort')
    report_path = root/RETURN_REPORT
    inherited._pin(report_path, refs, root)
    report = inherited.read(report_path)
    inherited.require(report.get('status') == 'calculated_unadopted' and report.get('inputs_unchanged') is True,
                      'Completed unchanged return-position volume evidence required')
    for case in cases[2:4]:
        inherited.require(any(c.get('case_id') == case['case_id'] and c.get('summary_path') == case['summary']
            for c in report.get('cases', [])) and report['inputs_sha256'].get(case['summary']) == case['summary_sha256'],
            'Completed return report must bind the selected return source summaries')
    baseline = cases[0]
    for case in cases:
        case.update(baseline_case_id=baseline['case_id'], baseline_summary_path=baseline['summary'],
                    baseline_summary_sha256=baseline['summary_sha256'])
    feedback = pres[-1].get('source_feedback')
    inherited.require(isinstance(feedback, dict) and feedback.get('path') and feedback.get('SHA256'),
                      'Source-position feedback context required')
    inherited._pin(Path(feedback['path']), refs, root, feedback['SHA256'])
    plan.update(created_utc=datetime.now(timezone.utc).isoformat(), status='preregistered_not_executed',
        initial_case_count=6, cases=cases, baseline_case_id=baseline['case_id'],
        baseline_case_ids=[baseline['case_id']], baseline_summary_paths=[baseline['summary']], input_sha256=refs,
        purpose='Compare completed inward-source contrasts with fixed baseline, asymmetric parent and return-position controls',
        continuation_batch_kind='fixed_source_return_position_cached_volume_audit',
        normalization_baseline_selection='Only original nominalRs500 h.625 SC2 four-square baseline; parent and return cases are comparison rows',
        new_feedback_context=dict(phase='source_position_continuation', source=feedback,
            original_S1_audit_schema_retained=True, completed_return_report=dict(path=str(report_path), SHA256=refs[str(report_path)])),
        geometry_comparison_contract=dict(kind='separate_source_or_return_position_contrasts_from_same_asymmetric_parent',
            source_coordinate_shifts_mm=[-.625, -1.25], return_coordinate_shifts_mm=[.625, -.625],
            parent_coordinate_shift_mm=0., joint_source_and_return_shift_tested=False,
            parent_and_return_controls_are_normalization_baselines=False, candidate_adopted=False),
        frozen_source_validation=dict(scope='Inherited strict per-case frozen manifest validation; canonical absolute and repository-relative paths supported without rewriting',
            manifests=[c['frozen_source_manifest'] for c in cases]),
        implementation_source_commit=commit, resource_policy_immutable_refs=inherited.policy.policy_refs(ledger))
    plan['resources'].update(cumulative_budget_limit_seconds=13800, observed_spent_seconds=ledger['spent_seconds'],
        observed_remaining_seconds=inherited.policy.remaining_seconds(ledger), native_scalar_cell_cache_sum=6*351680,
        conservative_cached_native_bytes_estimate=6*351680*256,
        estimated_cached_plus_overhead_bytes=6*351680*256+512*1024**2, nonbaseline_case_count=5,
        budget_policy='Use validated user-approved13800s policy; charge actual audit wall time; no automatic expansion')
    argv = ['python', str(root/'tools/task1_volume_selectivity.py'), '--preregistration', str(output),
            '--baseline-summary', baseline['summary']]
    for case in cases:
        argv += ['--summary', case['summary']]
    plan['resume_command_argv'] = argv+['--output', str(output.with_name(output.stem.removesuffix('-plan')+'.json'))]
    plan['metadata_registration_scope'].update(native_E_phi_array_reads=False, native_grid_array_reads=False,
        volume_NPZ_decode_or_byte_read=False, new_ROI_or_normalization_calculation=False)
    final_commit, final_sources = _committed_sources(root)
    inherited.require(final_commit == commit and all(refs.get(p) == digest for p, digest in final_sources.items()),
                      'Committed implementation changed during metadata registration')
    for path, digest in refs.items():
        if Path(path).name not in ('volume.npz', 'grid.csv', 'grid.csv.gz'):
            inherited.require(inherited.sha(path) == digest, 'Consumed metadata changed during registration: '+path)
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
