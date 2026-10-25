"""Recover fine grouped-pad metadata registration using explicit public feedback."""
from __future__ import annotations

import argparse
import copy
import hashlib
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import subprocess

try:
    import task1_return_position_volume_registration as inherited
except ModuleNotFoundError as error:
    if error.name != 'task1_return_position_volume_registration':
        raise
    from tools import task1_return_position_volume_registration as inherited

ROOT = Path(__file__).resolve().parents[1]
NEW_RUN = 'cloud-grouped-fine-20261021T160000Z'
COUNTS = (4, 8, 12, 16)
CASE_IDS = tuple(f'grouped-strip225-gap1-p{n:02d}-xy80' for n in COUNTS)
CASE_TABLE = (inherited.CASE_TABLE[0], *((NEW_RUN, ident) for ident in CASE_IDS))
SOURCES = ('tools/task1_grouped_fine_volume_recovery_registration.py',
    'tests/test_task1_grouped_fine_volume_recovery_registration.py',
    'tools/task1_queue_feedback.py',
    'tools/task1_grouped_fine_volume_registration.py','tests/test_task1_grouped_fine_volume_registration.py',
    'tools/task1_grouped_fine_registration.py', 'tests/test_task1_grouped_fine_registration.py',
    'tools/task1_grouped_geometry.py', 'tools/task1_grouped_postprocess.py',
    'tools/java/GroupedPadBasis.java', *inherited.SOURCES)
require, read, sha = inherited.require, inherited.read, inherited.sha
_regular, _pin, _properties, _signature = inherited._regular, inherited._pin, inherited._properties, inherited._signature
GATES = dict(max_residual=2e-7, max_power_error=2e-7, max_current_error=2e-6,
    max_area_relative_error=1e-10, max_interface_normal_current_relative_error=2e-7)


def _validate_grouped_contract(case, meta, config, n):
    """Check physical pads separately from source outputs, using metadata only."""
    require(n in COUNTS and case.get('n_pads') == n and case.get('n_outputs') == case.get('channels') == 2 and
        case.get('n_return_nodes') == 1 and case.get('java_class') == case.get('exporter_class') == 'GroupedPadBasis' and
        case.get('postprocessor') == 'grouped' and case.get('area_mode') == 'equal_total_area_900mm2' and
        case.get('source_coating_nm') == 10 and case.get('source_Rs_fit_window_Hz') == 500 and
        case.get('frequencies_Hz') == [3000,3030,9000,9090], 'Fixed fine grouped physical-pad/contact/frequency scope differs')
    m=n//4;nodes=[0]*m+[1]*m+[-1]*(2*m)
    require(case.get('pad_node_ids') == nodes and meta.get('pad_node_ids') == nodes and
        meta.get('exporter_class') == 'GroupedPadBasis' and meta.get('exporter_kind') == 'grouped_native' and
        meta.get('numerical_base_class') == 'SelectivityShapeBasis' and meta.get('n_pads') == n and
        meta.get('channels') == meta.get('n_outputs') == 2 and meta.get('n_return_nodes') == 1 and
        meta.get('return_topology') == 'common_GND' and meta.get('frequencies_Hz') == [3000,3030,9000,9090] and
        meta.get('source_peak_V') == .5 and meta.get('source_resistance_ohm') == 50,
        'Honest grouped exporter/physical-pad-node metadata differs')
    require(config.get('channels') == config.get('n_outputs') == '2' and config.get('n_pads') == str(n) and
        config.get('n_return_nodes') == '1' and config.get('return_topology') == 'common_GND' and
        config.get('frequencies') == '3000,3030,9000,9090' and float(config['h_mm']) == .625 and
        config.get('validation.sc_cells') == '2' and config.get('bulk.counts') == '14,14,40' and
        all(config.get(f'pad.node.{p}') == str(node) for p,node in enumerate(nodes)),
        'Actual fine grouped config mesh/frequencies/pad-node mapping differs')
    circuit=case['circuit'];mapping={str(p):'GND' if node<0 else f'out{node}' for p,node in enumerate(nodes)}
    require(circuit.get('n_pads') == n and circuit.get('n_outputs') == 2 and circuit.get('n_return_nodes') == 1 and
        circuit.get('pad_to_node') == mapping and circuit.get('return_topology') == 'all_return_pads_ideal_common_GND' and
        circuit.get('source_resistance_ohm') == 50 and circuit.get('source_peak_V') == .5 and
        circuit.get('source_Vpp_each') == 1 and circuit.get('source_phase_deg') == [0.,0.] and
        circuit.get('carrier_assignment_Hz') == [3000,3030] and circuit.get('harmonics_Hz') == [9000,9090] and
        circuit.get('exclusive_source_return_pair_assumed') is False and
        circuit.get('inactive_source_at_other_frequencies','').replace(' ','') == '0Vthrough50ohm',
        'Exactly2outputs/commonGND/50ohm inactive termination must remain explicit')
    areas=case.get('expected_pad_areas_m2',[]);target=900/n*1e-6
    require(len(areas) == n and all(type(a) in (int,float) and math.isfinite(a) and
        abs(a/target-1) <= 1e-10 for a in areas) and
        all(abs(float(config[f'pad.{p}.represented_area_m2'])/areas[p]-1) <= 1e-10 for p in range(n)) and
        all(abs(math.fsum(areas[g*m:(g+1)*m])/.000225-1) <= 1e-10 for g in range(4)),
        'Fixed900mm2 physical contact total and225mm2 electrical parent-group areas required')
    pads=case.get('pads',[]);width=225/13/m;outer=m*width+(m-1)
    require(len(pads) == n and case.get('control') ==
        ('new_four_rectangle_geometry_control' if n == 4 else 'physical_strip_count'),
        'Four-strip geometry control must not masquerade as original four-square normalization baseline')
    centres=((-10.7,-7.),(10.7,7.),(10.7,-7.),(-10.7,7.))
    for p,pad in enumerate(pads):
        group,strip=divmod(p,m);cx,cy=centres[group];x=cx-outer/2+width/2+strip*(width+1)
        require(pad.get('pad_id') == p and pad.get('parent_group') == group and pad.get('node') == nodes[p] and
            pad.get('shape') == 'rectangle' and pad.get('attachment') == 'top_z0' and pad.get('rotation_deg') == 0 and
            all(type(pad.get(k)) in (int,float) and math.isfinite(pad[k]) and math.isclose(pad[k],v,rel_tol=1e-12,abs_tol=1e-12)
                for k,v in (('width_mm',width),('height_mm',13.),('x_mm',x),('y_mm',cy),('area_mm2',900/n))),
            'Fine family must retain registered strip geometry, position, parent and area')
        require(config.get(f'pad.{p}.shape') == 'rectangle' and all(math.isclose(float(config[f'pad.{p}.{k}']),pad[k],rel_tol=1e-12,abs_tol=1e-12)
            for k in ('width_mm','height_mm','rotation_deg','x_mm','y_mm')) and
            math.isclose(float(config[f'pad.{p}.analytic_area_mm2']),pad['area_mm2'],rel_tol=1e-12,abs_tol=1e-12),
            'Config/registered physical strip geometry differs')
        require(all((x+sx*width/2)**2+(cy+sy*13/2)**2 < 625 for sx in (-1,1) for sy in (-1,1)),
            'Physical fine strip leaves fixedD50 phantom')


def _grouped_case(root, run_id, ident, refs, n):
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
    require(pre['gates'] == GATES, 'Grouped native numerical gates must remain unchanged')
    _validate_grouped_contract(case, meta, _properties(config_path), n)
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
    return dict(run_id=run_id, case_id=ident, n_pads=n, n_outputs=2, circuit=circuit,
        summary=str(summary_path), summary_sha256=summary_sha, volume_npz=str(npz), volume_npz_sha256=npz_sha,
        basis_folder=str(run/'bases'/ident), registration=str(pre_path), case_receipt=str(receipt_path),
        config_sha256=case['config_sha256'], mask_sha256=case['mask_sha256'], native_expected_input_sha256=native,
        source_commit=pre['source_commit'], mesh={k: meta[k] for k in ('h_xy_mm', 'sc_cells', 'bulk_layer_counts', 'cells')},
        comparison_signature=signature, source_bound_full_skin_audit=full_skin[0],
        stored_primary_raw_statistics={m: {k: condition['volume_metrics']['regions']['target']['statistics'][m][k]
            for k in ('mean', 'p10')} for m in ('maxTIS', 'fixedTIS', 'RMS')},
        frozen_source_manifest=dict(path=str(manifest_path), SHA256=refs[str(manifest_path)])), pre



def _committed_sources(root):
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    refs = {}
    for name in SOURCES:
        path = inherited._regular(root/name, root)
        inherited.require(subprocess.check_output(['git', 'show', commit+':'+name], cwd=root) == path.read_bytes(),
                          'Commit consumed implementation/helpers/tests before registration: '+name)
        refs[str(path)] = inherited.sha(path)
    return commit, refs


def _verified_feedback(feedback_path, refs, root):
    path=Path(feedback_path)
    _pin(path,refs,root)
    obj=read(path)
    require(obj.get('schema') == 'task1-queue-feedback-v1' and obj.get('status') == 'read_only_feedback_checked' and
        obj.get('error') is None and obj.get('public_GitHub_only') is True and
        type(obj.get('messages_sent')) is int and obj['messages_sent'] == 0 and
        type(obj.get('new_PDE')) is int and obj['new_PDE'] == 0,
        'Explicit successful read-only public GitHub GET receipt required')
    observed=datetime.fromisoformat(obj['observed_utc'].replace('Z','+00:00'))
    require(observed.tzinfo is not None,'Timezone-aware feedback GET observation required')
    receipts=obj.get('receipts',[]);expected=set()
    for pull in (1,2):
        expected.add((pull,'head',f'repos/yoodohyun-codex-cloud/ngg-tis-task1/pulls/{pull}'))
        expected.add((pull,'comments',f'repos/yoodohyun-codex-cloud/ngg-tis-task1/issues/{pull}/comments'))
    require(len(receipts) == 4 and {(r.get('pull'),r.get('kind'),r.get('endpoint')) for r in receipts} == expected,
        'Complete exact public PR1/PR2 head/comments GET receipt endpoints required')
    incoming=[]
    known={6280443738:'5018db8befa0a5f46c5f6460c28c4781b88eaf4e42d3280e2c5a8c3f6f3a9be8',
           6297472037:'5041b6cd0e507edb6cee630e70bc243674e7746c2b52b4c4fe6a3f9859a4d2e0',
           6308380231:'e8c566e0dc696693b257995e14449d3f5b33f26428f7c87471b6ec8effd5caf9',
           6308699569:'d30b761d73f7722dbe9d8033dad17510d748ccb00ec1722cbd53858790ec1050',
           6309148063:'9094121aaa4977872875bdb5f2a62ba1266b6708d2ceb21aaf1d438fee9f6d85',
           6312627319:'3583a8242c06641b58be4d770f73c9aca435354ee7e759eace6d622148871287',
           6314921372:'e17fde46d81f9567f945bf3899df200ba4470b038f461ae071ac7f3fd6b09b66',
           6319669306:'1ae49731956a4ec11d048bc995996f67c48d2778790892478a70d2609ab083ab',
           6320375305:'600efd51ec21ce3923b7e1f3f1c3d577d32a58a78ceb88e412399f0f6532aa00'}
    for receipt in receipts:
        timestamp=datetime.fromisoformat(receipt['observed_utc'].replace('Z','+00:00'))
        require(timestamp.tzinfo is not None and timestamp <= observed,'Invalid GET receipt observation time')
        evidence=receipt.get('evidence')
        if receipt['kind'] == 'head':
            require(isinstance(evidence,dict) and isinstance(evidence.get('head_sha'),str) and
                re.fullmatch('[0-9a-f]{40}',evidence['head_sha']), 'Actual public PR head SHA required')
            continue
        require(isinstance(evidence,list),'Actual public comment GET list required')
        for comment in evidence:
            body=comment.get('body')
            require(isinstance(body,str) and hashlib.sha256(body.encode()).hexdigest() == comment.get('body_sha256'),
                'Public GET comment body SHA mismatch')
            ident=comment.get('id')
            if receipt['pull'] == 2 and ident in known:
                require(comment.get('body_sha256') == known[ident] and comment.get('author') == 'yoodohyun-codex-cloud' and
                    comment.get('html_url') == f'https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-{ident}',
                    'Stable incoming T1-F010 source identity/body differs')
                incoming.append(dict(parent_feedback_id='T1-F010',source_comment_id=ident,
                    source_comment_url=comment['html_url'],body_sha256=known[ident]))
    require(len(incoming) == len(known) and {r['source_comment_id'] for r in incoming} == set(known),
        'All known incoming T1-F010 sources required; outbound status comments are not peer approval')
    return dict(path=str(path),SHA256=refs[str(path)],status=obj['status'],observed_utc=obj['observed_utc'],
        stable_incoming_sources=incoming,whole_public_GET_receipt_SHA_verified=True,
        public_receipt_scope='Existing queue GET success/endpoint/body-hash evidence; no fictional raw HTTP response SHA field',
        root_selected_fine_comparison=True,peer_requested_specific_geometry=False,
        latest_review_scope=dict(reviewed_publication_exit_and_byte_equal_substeps_only=6319669306,
            strip_XY_diagnostic_followup_with_convergence_hold=6320375305,
            numerical_or_target_feasibility_endorsement=False,gap1mm_at_h0p625_is_only1p6_cells_not_convergence=True,
            separately_pending_evidence=['per-mask represented area and effective gap','per-physical-pad complex currents',
                'skin current hotspot and active eight-cap limiter','ranking stability under common burden caps'],
            existing_volume_registration_blocked_by_separate_new_hotspot_audit=False),
        interpretation='Read-only feedback context; this does not claim peer approval of grouped fine geometry')


def _verified_root_decision(pre, refs, root):
    selected=pre.get('root_selection_decision')
    require(isinstance(selected,dict) and selected.get('path') and selected.get('SHA256'),
        'Original fine preregistration root-selection decision pin required')
    path=Path(selected['path']);_pin(path,refs,root,selected['SHA256']);decision=read(path)
    require(decision.get('schema') == 'task1-grouped-fine-root-decision-v1' and
        decision.get('status') == 'selected_not_executed' and isinstance(decision.get('question'),str) and
        bool(decision['question'].strip()) and decision.get('new_PDE') == 4 and decision.get('new_native_RHS') == 32 and
        decision.get('reuse_original4squarefine') is True and decision.get('no_duplicate_baseline') is True and
        decision.get('independent_outputs') == 2 and decision.get('physical_pads') == list(COUNTS) and
        decision.get('fixed_total_area_mm2') == 900 and decision.get('coarse_to_fine_each_case_geometry_unchanged') is True and
        decision.get('candidate_adopted') is False, 'Original root-selected finite fine-comparison decision differs')
    for name,digest in decision.get('input_sha256',{}).items():
        require(Path(name).suffix in ('.json','.md'),'Root decision metadata-only evidence required')
        _pin(Path(name),refs,root,digest)
    return dict(path=str(path),SHA256=refs[str(path)],original_status=decision['status'],
        question=decision['question'],selection_owner='root',peer_geometry_approval_claimed=False)


def make_preregistration(output, feedback_path, *, root=ROOT):
    """Write one metadata plan only after all four fine PDE/full-skin receipts exist."""
    root, output = Path(root).resolve(), Path(output)
    inherited.require(output.is_absolute() and output == output.resolve() and output.is_relative_to(root/'docs')
        and output.name.endswith('-plan.json') and output.parent.is_dir() and not output.exists() and not output.is_symlink(),
        'New canonical docs -plan.json path required; report must not overwrite its plan')
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
        case, pre = (inherited._case(root, run, ident, refs) if ident == CASE_TABLE[0][1]
            else _grouped_case(root, run, ident, refs, COUNTS[CASE_IDS.index(ident)]))
        cases.append(case); pres.append(pre)
    inherited.require(len({c['comparison_signature'] for c in cases}) == 1,
                      'All five cases require the same grid/material/contact/ROI cohort')
    baseline = cases[0]
    for case in cases:
        case.update(baseline_case_id=baseline['case_id'], baseline_summary_path=baseline['summary'],
                    baseline_summary_sha256=baseline['summary_sha256'])
    feedback = _verified_feedback(feedback_path, refs, root)
    decision = _verified_root_decision(pres[-1], refs, root)
    observed = datetime.fromisoformat(feedback['observed_utc'].replace('Z','+00:00'))
    prepared = datetime.fromisoformat(pres[-1]['created_utc'].replace('Z','+00:00'))
    require(observed >= prepared, 'Explicit feedback snapshot predates the selected fine batch')
    plan.update(created_utc=datetime.now(timezone.utc).isoformat(), status='preregistered_not_executed',
        initial_case_count=5, cases=cases, baseline_case_id=baseline['case_id'],
        baseline_case_ids=[baseline['case_id']], baseline_summary_paths=[baseline['summary']], input_sha256=refs,
        purpose='Compare original4square baseline and fine4strip/8/12/16 physical pads at fixed900mm2 and exactly2outputs',
        continuation_batch_kind='fixed_fine_grouped_pad_count_cached_volume_recovery_audit',
        metadata_recovery=dict(reason='Completed fine preregistration has root_selection_decision but no source_feedback; explicit refreshed public GET snapshot is supplied separately',
            original_stage_failure_preserved=True, original_preregistration_modified=False, original_registrar_modified=False, new_PDE=0),
        normalization_baseline_selection='Only original nominalRs500 h.625 SC2 four-square baseline; no candidate baseline substitution',
        new_feedback_context=dict(phase='root_selected_fine_comparison_metadata_recovery', source=feedback,
            root_selected_fine_comparison=True, peer_requested_specific_geometry=False,
            original_S1_audit_schema_retained=True, operational_context=dict(root_selection_decision=decision,
            execution_owner='root', actual_volume_audit_started=False)),
        geometry_comparison_contract=dict(kind='fixed900mm2_grouped_strip_count_with_separate_four_rectangle_control',
            physical_pad_counts=[4,4,8,12,16], independent_outputs_each=2, common_GND_return_nodes_each=1,
            strip_parent_group_area_mm2=225.,physical_total_area_mm2=900.,
            four_square_is_only_normalization_baseline=True,four_strip_is_geometry_control=True,
            comparison_scope='Fixed strip family subdivision; original4square versus4strip also changes outline/placement',
            per_pad_area_mm2_by_count={str(n):900/n for n in COUNTS}, candidate_adopted=False,
            existing_XY_SC_bulk_edge_contact_holds_preserved=True),
        frozen_source_validation=dict(scope='Inherited strict frozen manifest validation without source rewriting',
            manifests=[c['frozen_source_manifest'] for c in cases]),
        implementation_source_commit=commit, resource_policy_immutable_refs=inherited.policy.policy_refs(ledger))
    plan['resources'].update(cumulative_budget_limit_seconds=13800, observed_spent_seconds=ledger['spent_seconds'],
        observed_remaining_seconds=inherited.policy.remaining_seconds(ledger), native_scalar_cell_cache_sum=5*351680,
        conservative_cached_native_bytes_estimate=5*351680*256,
        estimated_cached_plus_overhead_bytes=5*351680*256+512*1024**2, nonbaseline_case_count=4,
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
    parser.add_argument('--feedback', type=Path, required=True)
    args = parser.parse_args()
    plan = make_preregistration(args.output,args.feedback)
    print(json.dumps(dict(status=plan['status'], cases=[c['case_id'] for c in plan['cases']],
        output=str(args.output), actual_audit_started=False, resume_command_argv=plan['resume_command_argv'])))


if __name__ == '__main__':
    main()
