#!/usr/bin/env python3
"""Preregister exactly four fine-grid grouped-strip conditions; no baseline solve.

The geometry generator and numerical grouped producer are unchanged. A new
readiness receipt records the sole historical orchestration hash exception;
the old readiness and its coarse producer regression remain immutable evidence.
"""
from __future__ import annotations
import ast
import copy
import math
import os
from pathlib import Path
import shutil
import subprocess
import time

import task1_cloud_batch as core
import task1_grouped_geometry as geometry
import task1_grouped_registration as grouped
import task1_resource_policy as policy

CASE_IDS = tuple(f'grouped-strip225-gap1-p{n:02d}-xy80' for n in (4, 8, 12, 16))
EXPECTED_CELLS = 351680
EXPECTED_RAW_BOUND_BYTES = 4*EXPECTED_CELLS*600
MAX_NEW_PDE = 4
MAX_NATIVE_RHS = 32
MIN_REMAINING_SECONDS = 4200
PREPARATION_SECONDS = 120
REVIEWED_CORE_SHA256 = 'b1107c57d9c7a501e441a5f1d72d08756af15b301c4245d46a2399099fd69459'
LEGACY_CORE_SHA256 = 'cdd12655650e9b2b3ad0a4f6e2361edec2701dd4c4c496cf3df96943af2558ce'
LEGACY_RUN = 'cloud-grouped-20261019T191500Z'
BASELINE_RUN = 'cloud-mesh-c1-20261019T190000Z'
BASELINE_ID = 'baseline-square15-xy80'


def _canonical(p):
    p = Path(p)
    core.require(p.is_absolute() and p == p.resolve() and p.is_relative_to(core.REPO) and
                 p.is_file() and not p.is_symlink(), 'Canonical repository evidence required')
    return p


def _pin(p, refs, expected=None):
    p = _canonical(p); actual = core.sha(p)
    core.require(expected is None or actual == expected, 'Pinned grouped evidence drift: '+str(p))
    refs[str(p)] = actual
    return p


def validate_readiness():
    """Read metadata/source hashes only; never repeats a PDE or imports arrays."""
    root = core.REPO; refs = {}
    receipt_path = _pin(root/'docs/cloud-restart-20261020/grouped-readiness.json', refs)
    receipt = core.read(receipt_path)
    core.require(receipt.get('status') == 'passed' and all(receipt.get('checks', {}).get(k) is True
        for k in grouped.RECEIPT_CHECKS), 'Original grouped readiness checks must all pass')
    codes = receipt['code_sha256']
    drift = []
    for relative in grouped.RECEIPT_CODE_FILES:
        current = _pin(root/relative, refs)
        if relative == 'tools/task1_cloud_batch.py':
            core.require(codes[relative] == LEGACY_CORE_SHA256 and core.sha(current) == REVIEWED_CORE_SHA256,
                'Only the explicitly reviewed orchestration version can supersede old core hash')
            manifest_path = _pin(root/'data-native'/LEGACY_RUN/'frozen-source-manifest.json', refs)
            manifest = core.read(manifest_path)
            old = _pin(Path(manifest['files'][str(current)]['path']), refs, LEGACY_CORE_SHA256)
            before, after = ast.parse(old.read_text()), ast.parse(current.read_text())
            definitions = lambda tree: {node.name: ast.dump(node, include_attributes=False) for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
            a, b = definitions(before), definitions(after)
            changed = sorted(k for k in set(a)|set(b) if a.get(k) != b.get(k))
            core.require(changed == ['effective_limits', 'execute', 'execute_locked', 'main', 'operator_signature', 'prepare', 'source_pins'],
                'Unexpected orchestration function drift')
            drift.append(dict(path=relative, old_sha256=codes[relative], current_sha256=core.sha(current),
                frozen_old_source=str(old), changed_functions=changed,
                scope='Reviewed budget/registration/producer routing only; grouped numerical Java and grouped postprocessor unchanged'))
        else:
            core.require(core.sha(current) == codes.get(relative), 'Grouped numerical/geometry/test code changed: '+relative)
    for row in receipt['test_logs']:
        _pin(Path(row['path']), refs, row['sha256'])
    regression_path = _pin(root/'docs/cloud-restart-20261020/grouped-producer-regression.json', refs)
    regression = core.read(regression_path)
    expected = {f'{kind}-{freq}.bin' for kind in ('field', 'potential', 'density', 'source', 'loss')
                for freq in (3000, 3030, 9000, 9090)}
    rows = regression.get('comparisons', [])
    core.require(regression.get('status') == 'passed' and len(rows) == 20 and
        {r['file'] for r in rows} == expected and all(r.get('passed') is True and
            math.isfinite(r['max_absolute_error']) and math.isfinite(r['max_relative_global_error'])
            for r in rows) and regression.get('relative_global_norm_tolerance') == 1e-8 and
        regression.get('absolute_tolerance') == 1e-14, 'All20 cached grouped producer comparisons must pass')
    for run, ident in (('cloud-baseline-20261019T185900Z', 'baseline-square15-coarse'),
                       (LEGACY_RUN, 'grouped-historical-square15-xy40')):
        r = root/'data-native'/run; pre_path = _pin(r/'preregistration.json', refs)
        record_path = _pin(r/'cases'/(ident+'.json'), refs); record = core.read(record_path)
        core.require(record['status'] == 'complete', 'Cached producer case must be complete')
        case = next(c for c in core.read(pre_path)['cases'] if c['id'] == ident)
        _pin(Path(case['config_file']), refs, case['config_sha256'])
        _pin(Path(case['mask_file']), refs, case['mask_sha256'])
        _pin(Path(record['postprocess_path']), refs, record['postprocess_sha256'])
    return dict(schema='task1-grouped-fine-readiness-v1', status='passed_for_finite_fine_exploration',
        original_readiness=dict(path=str(receipt_path), SHA256=core.sha(receipt_path), original_bytes_modified=False),
        inherited_cached_producer_regression=dict(path=str(regression_path), SHA256=core.sha(regression_path),
            passed_comparisons=20, array_comparison_repeated=False, new_PDE=0, independent_solver=False),
        explicitly_reviewed_orchestration_drift=drift, numerical_grouped_implementation_unchanged=True,
        geometry_generator_unchanged=True, fine_mesh_convergence_validated=False,
        raw_native_bytes_rehashed_in_this_readiness=False), refs


def reused_baseline(refs):
    root = core.REPO/'data-native'/BASELINE_RUN
    registration = _pin(root/'preregistration.json', refs)
    receipt = _pin(root/'cases'/(BASELINE_ID+'.json'), refs)
    summary = _pin(root/'postprocess'/BASELINE_ID/'summary.json', refs)
    pre, rec, result = core.read(registration), core.read(receipt), core.read(summary)
    case = next(c for c in pre['cases'] if c['id'] == BASELINE_ID)
    core.require(rec['status'] == result['status'] == 'complete' and rec['postprocess_sha256'] == core.sha(summary)
        and rec['config_sha256'] == case['config_sha256'] and case['h_xy_mm'] == .625 and case['sc_cells'] == 2
        and case['bulk_counts'] == [14, 14, 40] and case['cells'] == EXPECTED_CELLS, 'Completed same-grid original four-square required')
    _pin(Path(case['config_file']), refs, case['config_sha256']); _pin(Path(case['mask_file']), refs, case['mask_sha256'])
    return dict(case_id=BASELINE_ID, summary_path=str(summary), summary_sha256=core.sha(summary),
        case_receipt_path=str(receipt), case_receipt_sha256=core.sha(receipt),
        registration_path=str(registration), registration_sha256=core.sha(registration),
        new_PDE=0, reuse_existing_native_result=True, physical_pads=4, independent_outputs=2)


def select_cases(plan, run):
    """Only same physical strip geometry on the fixed fine grid can be admitted."""
    cases = plan['cases']; pool = {c['id']: c for c in cases}
    core.require(len(cases) == len(pool) == 5 and set(pool) == set(CASE_IDS)|{'grouped-historical-square15-xy80'},
                 'Exact five geometry-only controls required; duplicate or foreign case rejected')
    source = _canonical(plan['input_source_config'])
    core.require(core.sha(source) == plan['input_source_config_sha256'], 'Same tissue/contact source configuration required')
    source_properties = geometry.read_properties(source)
    selected = []
    for ident, n in zip(CASE_IDS, (4, 8, 12, 16)):
        case = copy.deepcopy(pool[ident]); pads = geometry.rectangles(n)
        core.require(case['pads'] == pads and case['n_pads'] == n and case['n_outputs'] == 2 and
            case['n_return_nodes'] == 1 and case['pad_node_ids'] == [p['node'] for p in pads] and
            case['h_xy_mm'] == .625 and case['sc_cells'] == 2 and case['bulk_counts'] == [14, 14, 40] and
            case['frequencies_Hz'] == [3000, 3030, 9000, 9090] and
            case['area_mode'] == 'equal_total_area_900mm2' and case['exporter_class'] == 'GroupedPadBasis',
            'Same grouped-strip physical geometry/circuit/fine mesh required')
        geometry.geometry_receipt(pads)
        expected_rows, expected_areas = geometry.mask_rows(pads, .625)
        expected_bytes = ('pad,i,j,area_m2\n'+''.join(f'{p},{i},{j},{a:.17g}\n' for p, i, j, a in expected_rows)).encode()
        old_mask, old_config = Path(case['mask_file']), Path(case['config_file'])
        core.require(core.sha(old_mask) == case['mask_sha256'] and old_mask.read_bytes() == expected_bytes and
            core.sha(old_config) == case['config_sha256'] and case['expected_pad_areas_m2'] == expected_areas,
            'Exact fractional intersections, no area renormalization or clipped geometry allowed')
        expected_config = {k: v for k, v in source_properties.items() if not k.startswith('pad.')}
        expected_config.update(h_mm='0.625', channels='2', n_outputs='2', n_pads=str(n), n_return_nodes='1',
            return_topology='common_GND', **{'mask.path':str(old_mask), 'mask.sha256':case['mask_sha256'],
                                         'grouped.geometry.version':'strip225-gap1-v1'})
        for pad, area in zip(pads, expected_areas):
            e = pad['pad_id']; expected_config[f'pad.node.{e}'] = str(pad['node'])
            expected_config[f'pad.{e}.represented_area_m2'] = format(area, '.17g')
            for key in ('shape', 'width_mm', 'height_mm', 'rotation_deg', 'x_mm', 'y_mm'):
                expected_config[f'pad.{e}.{key}'] = str(pad[key])
            expected_config[f'pad.{e}.analytic_area_mm2'] = str(pad['area_mm2'])
        core.require(geometry.read_properties(old_config) == expected_config,
                     'Generated configuration changes tissue/contact/circuit/geometry outside fixed family')
        case.update(grouped._mesh(case)); core.require(case['cells'] == EXPECTED_CELLS, 'Fixed351680cell mesh required')
        nodes = case['pad_node_ids']
        case.update(source_run_id=Path(run).name, channels=2, java_class='GroupedPadBasis', postprocessor='grouped',
            status='preregistered_not_executed', source_coating_nm=10, source_Rs_fit_window_Hz=500,
            design_id=ident.removesuffix('-xy80'), mesh_id='grouped_xy80_sc2',
            requires_original_producer_regression_before_next=False,
            design=dict(id=ident.removesuffix('-xy80'), channels=2, pads=copy.deepcopy(pads), xy_mm=[[p['x_mm'], p['y_mm']] for p in pads]),
            circuit=dict(n_pads=n, n_outputs=2, n_signal_pads=n//2, n_return_pads=n//2, n_return_nodes=1,
                return_topology='all_return_pads_ideal_common_GND', source_Vpp_each=1., source_peak_V=.5,
                source_resistance_ohm=50., source_phase_deg=[0., 0.], carrier_assignment_Hz=[3000, 3030],
                harmonics_Hz=[9000, 9090], pad_to_node={str(i): 'GND' if node < 0 else f'out{node}' for i, node in enumerate(nodes)},
                inactive_source_at_other_frequencies='0 V through50 ohm', exclusive_source_return_pair_assumed=False))
        selected.append(case)
    return selected


def prepare(run, decision_path=None):
    started = time.monotonic(); run = Path(run); core.paths_check(run)
    core.require(run.is_absolute() and run == run.resolve() and not run.exists(), 'New unique canonical fine grouped run required')
    grouped._caller_owns_execution_lock(); os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    budget_path = core.REPO/'runtime/task1-budget.json'; budget = policy.load_ledger(budget_path)
    core.require(policy.effective_limit(budget) == 13800 and policy.remaining_seconds(budget) >= MIN_REMAINING_SECONDS,
        'Need approved policy and4200s reserve for4PDE+audits+volume+publication+preparation')
    core.require(shutil.disk_usage(run.parent).free >= 2*core.GIB+EXPECTED_RAW_BOUND_BYTES+20*1024**2,
                 'Four raw bases plus2GiB reserve and20MiB geometry/classes unavailable')
    pins = core.source_pins(budget)
    for p in (Path(__file__).resolve(), core.REPO/'tests/test_task1_grouped_fine_registration.py',
              Path(geometry.__file__).resolve(), core.REPO/'tools/java/GroupedPadBasis.java'):
        pins[str(p)] = core.sha(p)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=core.REPO, text=True).strip()
    for name, digest in pins.items():
        p = Path(name)
        if p.suffix in ('.py', '.java'):
            core.require(subprocess.check_output(['git', 'show', commit+':'+p.relative_to(core.REPO).as_posix()], cwd=core.REPO) == p.read_bytes(), 'Commit consumed sources before preparation: '+name)
    run.mkdir(); succeeded = False
    try:
        for d in ('configs', 'masks', 'bases', 'cases', 'postprocess', 'logs', 'classes'):
            (run/d).mkdir()
        def guard(phase):
            remaining = min(PREPARATION_SECONDS-(time.monotonic()-started), policy.remaining_seconds(budget)-(time.monotonic()-started)-4080)
            core.require(remaining > 0 and core.rss(os.getpid()) < 3*core.GIB and shutil.disk_usage(run).free >= 2*core.GIB,
                         'Fine grouped preparation time/RSS/reserve exhausted')
            core.write(run/'controller.json', dict(status='preparing', phase=phase, pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now()))
            return remaining
        guard('integrity_and_readiness'); integrity = core.original_integrity()
        readiness, old_pins = validate_readiness(); pins.update(old_pins)
        baseline = reused_baseline(pins)
        if decision_path is not None: _pin(decision_path, pins)
        core.write(run/'fine-readiness.json', readiness); pins[str(run/'fine-readiness.json')] = core.sha(run/'fine-readiness.json')
        guard('generate_exact_geometry'); plan = geometry.generate_family(run/'geometry-source', h_mm=.625)
        selected = select_cases(plan, run); core.require(len(selected) == MAX_NEW_PDE, 'Exactly4new grouped conditions required')
        mapping = []
        for case in selected:
            old_mask, old_config = Path(case['mask_file']), Path(case['config_file'])
            mask = run/'masks'/old_mask.name; shutil.copy2(old_mask, mask)
            raw = old_config.read_bytes(); token = b'mask.path='+str(old_mask).encode()
            core.require(raw.count(token) == 1, 'Unique generated mask path required')
            updated = raw.replace(token, b'mask.path='+str(mask).encode())
            config = run/'configs'/old_config.name; config.write_bytes(updated)
            case.update(mask_file=str(mask), mask_sha256=core.sha(mask), config_file=str(config), config_sha256=core.sha(config))
            case['cache_signature'] = core.check_cached_operator(case, run)
            mapping.append(dict(original_config=str(old_config), original_sha256=core.sha(old_config), new_config=str(config),
                new_sha256=core.sha(config), changed_fields=['mask.path'], mask_sha256=core.sha(mask)))
        guard('compile_and_selftest')
        jdk = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
        javac = shutil.which('javac') or str(jdk/'javac'); java = str(Path(javac).resolve().parent/'java')
        core.require(Path(javac).is_file() and Path(java).is_file(), 'Matching installed Java compiler/runtime required')
        with (run/'logs/compile-selftest.log').open('x') as log:
            def command(args): subprocess.run(args, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=guard('compile_or_selftest'))
            command([javac, '-J-Xmx2g', '-J-XX:ActiveProcessorCount=1', '-encoding', 'UTF-8', '-d', str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'), str(core.SOURCE/'ExploreBasis.java'), str(core.SOURCE/'SelectivityShapeBasis.java'),
                str(core.REPO/'tools/java/CloudShapeBasis.java'), str(core.REPO/'tools/java/GroupedPadBasis.java')])
            for adapter in ('CloudShapeBasis', 'GroupedPadBasis'):
                command([java, '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1', '-cp', str(run/'classes'), adapter, '--selftest'])
        for folder in ('configs', 'masks', 'classes', 'geometry-source'):
            for p in (run/folder).rglob('*'):
                if p.is_file(): pins[str(p)] = core.sha(p)
        for name, digest in pins.items(): core.require(core.sha(name) == digest, 'Fine grouped input drift: '+name)
        registration = dict(schema='task1-cloud-finite-v1', batch_kind='grouped_fine_physical_pads', status='prepared',
            created_utc=core.now(), source_commit=commit, package_integrity=integrity, limits=core.effective_limits(budget),
            gates=copy.deepcopy(core.GATES), cases=selected, java=java, source_and_input_sha256=pins,
            preparation_seconds=time.monotonic()-started, expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,
            new_PDE_conditions_maximum=MAX_NEW_PDE, maximum_native_RHS=MAX_NATIVE_RHS,
            reused_baseline_reference=baseline, reused_coarse_grouped_run=LEGACY_RUN, path_mapping=mapping,
            resource_policy_immutable_refs=policy.policy_refs(budget),
            original_geometry_control_generated_only=dict(case_id='grouped-historical-square15-xy80', new_PDE=0, selected_for_execution=False),
            readiness=dict(path=str(run/'fine-readiness.json'), SHA256=core.sha(run/'fine-readiness.json')),
            scientific_question='At fixed900mm2/2outputs, how do4strip/8/12/16 change absolute deep ROI and shallow/offtarget burden when h1.25 is refined to h0.625?',
            fixed_comparisons='Always include cached original4square and new4strip geometrycontrol; same ROI, units, display ranges, source/circuit and five separate normalization modes',
            planned_normalizations=['raw_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power', 'skin_contact_only', 'legacy_composite_full_skin'],
            contact_scope='PBS10nmRs500 surrogate unchanged; no actualskinvalidation; Rs subtracted once and area scaling once',
            geometry_scope='Exact rectangle intersections; no outer clipping, area renormalization or changed physical gaps',
            candidate_adopted=False, mesh_convergence_validated=False, experimental_validation=False,
            storage=dict(native_location=str(run), persistent_backup_verified=False, retirement_of_old_environment_allowed=False),
            next_decision='Audit actual fullskinJ/losses and common-cutoff volumes under5normalizations; compare coarse/fine before any further mesh/SC/contact gate or adoption')
        if decision_path is not None:
            registration['root_selection_decision'] = dict(path=str(Path(decision_path).resolve()), SHA256=core.sha(decision_path))
        core.write(run/'preregistration.json', registration); core.write(run/'controller.json', dict(status='prepared', updated_utc=core.now())); succeeded = True
    except BaseException as error:
        core.write(run/'preparation-failure.json', dict(status='preparation_failed_preserved', error_type=type(error).__name__, error=str(error), observed_utc=core.now(), partial_evidence_preserved=True, automatic_retry=False))
        raise
    finally:
        elapsed = time.monotonic()-started; budget['spent_seconds'] += elapsed
        budget['runs'].append(dict(run_id=run.name, stage='grouped_fine_preparation', seconds=elapsed, status='prepared' if succeeded else 'preparation_failed_preserved'))
        core.write(budget_path, budget)
    return registration


def main():
    import argparse
    import fcntl
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--prepare', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--decision', type=Path); args = parser.parse_args()
    with (core.REPO/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB); fcntl.lockf(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        result = prepare(args.output, args.decision); core.freeze_sources(args.output)
    print(dict(status=result['status'], run=str(args.output), cases=list(CASE_IDS), new_PDE_maximum=4))


if __name__ == '__main__': main()
