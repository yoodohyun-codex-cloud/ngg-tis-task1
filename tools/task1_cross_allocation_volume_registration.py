"""Register four completed cached cross-allocation rows; never run analysis."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess

try:
    import task1_return_position_volume_registration as inherited
except ModuleNotFoundError as error:
    if error.name != 'task1_return_position_volume_registration':
        raise
    from tools import task1_return_position_volume_registration as inherited

ROOT = Path(__file__).resolve().parents[1]
NEW_RUN = 'cloud-cross-allocation-20261021T150000Z'
ALLOCATIONS_MM2 = (200., 225., 250.)
CASE_IDS = ('crossalloc-source200-return250-xy80', 'crossalloc-source225-return225-xy80',
            'crossalloc-source250-return200-xy80')
CASE_TABLE = (inherited.CASE_TABLE[0], *((NEW_RUN, ident) for ident in CASE_IDS))
SOURCES = ('tools/task1_cross_allocation_volume_registration.py',
    'tests/test_task1_cross_allocation_volume_registration.py', *inherited.SOURCES)


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
    """Write a unique metadata plan after all three PDE/full-skin receipts exist."""
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
                      'All four cases require the same grid/material/contact/ROI cohort')
    for ident, area, pre in zip(CASE_IDS, ALLOCATIONS_MM2, pres[1:]):
        original = next(c for c in pre['cases'] if c['id'] == ident)
        expected = [area*1e-6, area*1e-6, (450.-area)*1e-6, (450.-area)*1e-6]
        areas = original.get('expected_pad_areas_m2', [])
        inherited.require(len(areas) == 4 and all(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-16)
            for a, b in zip(areas, expected)), 'Fixed per-pad allocation and total900mm2 required')
    baseline = cases[0]
    for case in cases:
        case.update(baseline_case_id=baseline['case_id'], baseline_summary_path=baseline['summary'],
                    baseline_summary_sha256=baseline['summary_sha256'])
    feedback = pres[-1].get('source_feedback')
    inherited.require(isinstance(feedback, dict) and feedback.get('path') and feedback.get('SHA256'),
                      'Cross-allocation feedback context required')
    inherited._pin(Path(feedback['path']), refs, root, feedback['SHA256'])
    decision = pres[-1].get('root_selection_decision')
    if isinstance(decision, dict) and decision.get('path'):
        digest = decision.get('SHA256', decision.get('sha256'))
        inherited.require(isinstance(digest, str), 'Root decision SHA256 required')
        inherited._pin(Path(decision['path']), refs, root, digest)
    plan.update(created_utc=datetime.now(timezone.utc).isoformat(), status='preregistered_not_executed',
        initial_case_count=4, cases=cases, baseline_case_id=baseline['case_id'],
        baseline_case_ids=[baseline['case_id']], baseline_summary_paths=[baseline['summary']], input_sha256=refs,
        purpose='Compare three completed all-cross source/return area allocations at fixed total900mm2',
        continuation_batch_kind='fixed_cross_allocation_cached_volume_audit',
        normalization_baseline_selection='Only original nominalRs500 h.625 SC2 four-square baseline; no candidate baseline substitution',
        new_feedback_context=dict(phase='cross_allocation_continuation', source=feedback,
            original_S1_audit_schema_retained=True, operational_context=dict(root_selection_decision=decision,
            execution_owner='root', actual_volume_audit_started=False)),
        geometry_comparison_contract=dict(kind='joint_source_return_cross_length_area_allocation_at_fixed_total_area',
            arm_width_mm=10., source_return_lengths_mm=[[15.,17.5],[16.25,16.25],[17.5,15.]],
            source_per_pad_area_mm2=list(ALLOCATIONS_MM2), return_per_pad_area_mm2=[250.,225.,200.],
            physical_total_area_mm2=900., fixed_centres_mm=[[-10.,-10.],[10.,10.],[10.,-10.],[-10.,10.]],
            isolated_area_effect_claimed=False, candidate_adopted=False),
        frozen_source_validation=dict(scope='Inherited strict frozen manifest validation without source rewriting',
            manifests=[c['frozen_source_manifest'] for c in cases]),
        implementation_source_commit=commit, resource_policy_immutable_refs=inherited.policy.policy_refs(ledger))
    plan['resources'].update(cumulative_budget_limit_seconds=13800, observed_spent_seconds=ledger['spent_seconds'],
        observed_remaining_seconds=inherited.policy.remaining_seconds(ledger), native_scalar_cell_cache_sum=4*351680,
        conservative_cached_native_bytes_estimate=4*351680*256,
        estimated_cached_plus_overhead_bytes=4*351680*256+512*1024**2, nonbaseline_case_count=3,
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
