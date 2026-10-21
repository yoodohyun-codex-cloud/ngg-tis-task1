"""Register the completed four-pad square/cross by source-adjacency factorial; no arrays."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import hashlib
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
NEW_RUN = 'cloud-adjacent-cross-20261021T164000Z'
CASE_ID = 'balancedcross225-adjacent-sources-xy80'
CASE_TABLE = (
    ('cloud-mesh-c1-20261019T190000Z', 'baseline-square15-xy80'),
    ('cloud-finite-loop-20261020T002600Z-fine', 'adjacent-square15-xy80'),
    ('cloud-cross-allocation-20261021T150000Z', 'crossalloc-source225-return225-xy80'),
    (NEW_RUN, CASE_ID),
)
FEEDBACK_REL = 'docs/cloud-grouped-fine-recovery-20261021T161000Z/feedback-before.json'
COMMENT_ID = 6320375305
COMMENT_BODY_SHA256 = '600efd51ec21ce3923b7e1f3f1c3d577d32a58a78ceb88e412399f0f6532aa00'
SOURCES = ('tools/task1_adjacent_source_volume_registration.py',
    'tests/test_task1_adjacent_source_volume_registration.py',
    'tools/task1_adjacent_source_registration.py', 'tests/test_task1_adjacent_source_registration.py', *inherited.SOURCES)


def _feedback_comment(value):
    found=[]
    def walk(item):
        if isinstance(item,dict):
            if item.get('id')==COMMENT_ID:found.append(item)
            for child in item.values():walk(child)
        elif isinstance(item,list):
            for child in item:walk(child)
    walk(value)
    inherited.require(found and all(row.get('body_sha256')==COMMENT_BODY_SHA256 and
        isinstance(row.get('body'),str)and hashlib.sha256(row['body'].encode()).hexdigest()==COMMENT_BODY_SHA256 for row in found),
        'Actual peer comment6320375305 body and SHA must be present; no wiring endorsement is inferred')
    return found[0]


def _validate_factorial_contract(item,pre,config):
    original=next(row for row in pre['cases']if row['id']==item['case_id'])
    index=next(index for index,(_,identifier)in enumerate(CASE_TABLE)if identifier==item['case_id'])
    circuit=original['circuit'];cross=index>=2;adjacent=index in (1,3)
    inherited.require(circuit.get('n_pads')==4 and circuit.get('n_outputs')==2 and circuit.get('n_return_nodes')==1 and
        circuit.get('source_resistance_ohm')==50 and circuit.get('source_peak_V')==.5 and circuit.get('source_Vpp_each')==1 and
        circuit.get('return_topology')=='all_return_pads_ideal_common_GND'and
        circuit.get('pad_to_node')=={'0':'out0','1':'out1','2':'GND','3':'GND'}and
        circuit.get('carrier_assignment_Hz')==[3000,3030]and
        circuit.get('inactive_source_at_other_frequencies','').replace(' ','')=='0Vthrough50ohm',
        'Unchanged four-pad/two-output/commonGND/50ohm circuit required')
    areas=original.get('expected_pad_areas_m2',[])
    inherited.require(len(areas)==4 and all(math.isclose(area,.000225,rel_tol=1e-12,abs_tol=1e-16)for area in areas)and
        original.get('source_coating_nm')==10 and original.get('source_Rs_fit_window_Hz')==500,
        'Four equal225mm2 nominalPBS10nmRs500 contacts required')
    inherited.require(config.get('h_mm')=='0.625'and config.get('channels')=='2'and
        config.get('frequencies')=='3000,3030,9000,9090'and config.get('validation.sc_cells')=='2'and
        config.get('bulk.counts')=='14,14,40','Fixed fine grid/four spectral lines required')
    coords=((-10.,-10.),(10.,-10.),(10.,10.),(-10.,10.))if adjacent else ((-10.,-10.),(10.,10.),(10.,-10.),(-10.,10.))
    for pad,(x,y)in enumerate(coords):
        prefix=f'pad.{pad}.';length=16.25 if cross else 15.
        inherited.require(config.get(prefix+'shape')==('cross'if cross else'rectangle')and
            all(math.isclose(float(config[prefix+key]),value,rel_tol=0,abs_tol=1e-12)for key,value in
                (('width_mm',length),('height_mm',length),('rotation_deg',0.),('analytic_area_mm2',225.),('x_mm',x),('y_mm',y)))and
            (not cross or float(config[prefix+'arm_width_mm'])==10.),'Exact square/cross shape and opposite/adjacent source assignment required')
    if index==3:
        inherited.require(original.get('original_physical_pad_by_solver_pad')==[0,2,1,3]and
            original.get('wiring_only_contrast')is True and original.get('source_adjacency')=='adjacent_bottom_row',
            'New cross must be physical-pad permutation only, without geometry changes')


def _validate_probe40(item,refs,root):
    summary=inherited.read(Path(item['summary']));probe_path=Path(item['summary']).parent/summary['artifacts']['probes_json']
    probes=inherited.read(probe_path)
    rows=[row for row in probes.get('conditions',[])if row.get('id')==item['case_id']+'-square_3h'and row.get('waveform')=='square_3h']
    inherited.require(probes.get('status')=='complete'and len(rows)==1,'One completed native square_3h probe set required')
    probe=rows[0]['probe40'];measurements=probe['measurements']
    inherited.require(probe.get('status')=='complete'and probe.get('unloaded_prediction')is True and
        probe['numerical_checks']['all_passed']is True and probe['measurement_grid']['tip_gap_mm']==5 and
        len(measurements)==len({row['id']for row in measurements})==40 and
        {row['depth_from_skin_surface_mm']for row in measurements}=={5,10,15,20}and
        {row['axis']for row in measurements}=={'X','Y'}and all(row['tip_gap_mm']==5 for row in measurements),
        'Forty native unloaded probes at four depths/two axes/5mm tip gap required')


def _committed_sources(root):
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    refs = {}
    for name in SOURCES:
        path = inherited._regular(root/name, root)
        inherited.require(subprocess.check_output(['git', 'show', commit+':'+name], cwd=root) == path.read_bytes(),
                          'Commit consumed implementation/helpers/tests before registration: '+name)
        refs[str(path)] = inherited.sha(path)
    return commit, refs


def make_preregistration(output, *, root=ROOT, decision_path=None, feedback_path=None):
    """Write a unique metadata plan after all four cached/full-skin receipts exist."""
    root, output = Path(root).resolve(), Path(output)
    inherited.require(output.is_absolute() and output == output.resolve() and output.is_relative_to(root/'docs')
        and output.name.endswith('-plan.json') and output.parent.is_dir() and not output.exists() and not output.is_symlink(),
        'New canonical docs -plan.json path required')
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
    for case, pre in zip(cases, pres):
        original = next(row for row in pre['cases'] if row['id'] == case['case_id'])
        _validate_factorial_contract(case, pre, inherited._properties(Path(original['config_file'])))
        _validate_probe40(case, refs, root)
    baseline = cases[0]
    for case in cases:
        case.update(baseline_case_id=baseline['case_id'], baseline_summary_path=baseline['summary'],
                    baseline_summary_sha256=baseline['summary_sha256'])
    selection = pres[-1].get('root_selection_decision', {})
    decision_path = Path(decision_path) if decision_path is not None else Path(selection.get('path', ''))
    decision_sha = inherited._pin(decision_path, refs, root)
    decision = inherited.read(decision_path)
    inherited.require(selection.get('path') == str(decision_path) and selection.get('SHA256') == decision_sha and
        decision.get('schema') == 'task1-adjacent-source-decision-v1' and decision.get('status') == 'preregistered_not_started' and
        decision.get('case_ids') == [CASE_ID] and isinstance(decision.get('chosen_question'), str) and bool(decision['chosen_question'].strip()),
        'New native root-selection decision must bind the exact wiring question and SHA')
    allocation_ref=decision.get('cross_allocation_report',{})
    inherited.require(isinstance(allocation_ref.get('sha256'),str)and len(allocation_ref['sha256'])==64,
        'Completed allocation report needs an explicit immutable SHA256')
    allocation_path=Path(allocation_ref.get('path',''))
    allocation_sha=inherited._pin(allocation_path,refs,root,allocation_ref.get('sha256'))
    allocation=inherited.read(allocation_path)
    inherited.require(allocation.get('status')=='calculated_unadopted'and allocation.get('inputs_unchanged')is True and
        len(allocation.get('cases',[]))==4 and
        {row['case_id']for row in allocation.get('cases',[])}=={CASE_TABLE[0][1],
            'crossalloc-source200-return250-xy80',CASE_TABLE[2][1],'crossalloc-source250-return200-xy80'}and
        all(any(row.get('case_id')==case['case_id']and row.get('summary_path')==case['summary']for row in allocation['cases'])and
            allocation['inputs_sha256'].get(case['summary'])==case['summary_sha256']for case in (cases[0],cases[2])),
        'Actual completed allocation report must bind the cached original baseline and balanced-cross control')
    feedback_path = Path(feedback_path) if feedback_path is not None else root/FEEDBACK_REL
    feedback_sha = inherited._pin(feedback_path, refs, root)
    feedback = inherited.read(feedback_path)
    comment = _feedback_comment(feedback)
    historical_feedback = pres[-1].get('source_feedback')
    if isinstance(historical_feedback, dict) and historical_feedback.get('path'):
        inherited._pin(Path(historical_feedback['path']), refs, root, historical_feedback.get('SHA256'))
    feedback_context = dict(path=str(feedback_path), SHA256=feedback_sha, comment_id=COMMENT_ID,
        body_SHA256=COMMENT_BODY_SHA256, html_url=comment.get('html_url'), peer_specific_wiring_endorsement_inferred=False)
    plan.update(created_utc=datetime.now(timezone.utc).isoformat(), status='preregistered_not_executed',
        initial_case_count=4, cases=cases, baseline_case_id=baseline['case_id'],
        baseline_case_ids=[baseline['case_id']], baseline_summary_paths=[baseline['summary']], input_sha256=refs,
        purpose='Compare completed square/cross by opposite/adjacent source assignments at fixed225mm2 per pad and900mm2 total',
        continuation_batch_kind='fixed_fourpad_shape_by_source_adjacency_cached_volume_audit',
        normalization_baseline_selection='Only original nominalRs500 h.625 SC2 four-square baseline; no candidate baseline substitution',
        new_feedback_context=dict(phase='shape_source_adjacency_factorial', source=feedback_context,
            inherited_source_feedback_context=historical_feedback, original_S1_audit_schema_retained=True,
            root_selection=dict(path=str(decision_path), SHA256=decision_sha, chosen_question=decision['chosen_question']),
            completed_allocation_report=dict(path=str(allocation_path),SHA256=allocation_sha),
            peer_specific_wiring_endorsement_inferred=False, execution_owner='root', actual_volume_audit_started=False),
        geometry_comparison_contract=dict(kind='two_by_two_square_cross_by_opposite_adjacent_sources',
            factors=dict(shape=['square15','balanced_cross16p25_arm10'],source_assignment=['opposite_diagonal','adjacent_bottom_row']),
            cells=[dict(case_id=case['case_id'],shape='square' if index<2 else 'cross',
                source_assignment='opposite_diagonal' if index in (0,2) else 'adjacent_bottom_row') for index,case in enumerate(cases)],
            physical_pad_counts=[4]*4, independent_outputs_each=2, common_GND_return_nodes_each=1,
            physical_per_pad_area_mm2=225.,physical_total_area_mm2=900.,
            new_cross_old_physical_pad_by_solver_pad=[0,2,1,3],
            physical_contacts_unchanged_within_each_shape=True,
            original_square_opposite_is_only_normalization_baseline=True,
            aligned_full_face_geometry_descriptors=True, numerical_mesh_or_contact_convergence_claimed=False,
            candidate_adopted=False),
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
    parser.add_argument('--decision', type=Path, required=True)
    parser.add_argument('--feedback', type=Path, required=True)
    args = parser.parse_args()
    plan = make_preregistration(args.output, decision_path=args.decision, feedback_path=args.feedback)
    print(json.dumps(dict(status=plan['status'], cases=[c['case_id'] for c in plan['cases']],
        output=str(args.output), actual_audit_started=False, resume_command_argv=plan['resume_command_argv'])))


if __name__ == '__main__':
    main()
