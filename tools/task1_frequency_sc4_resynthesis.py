#!/usr/bin/env python3
"""Two actual-frequency sine readbacks of the genuine SC4 baseline; no PDE.

SC4 square/sine burden references remain SC4 references.  Cross-mesh high-field
volumes use the exact original SC2 cutoffs; SC4's own cutoffs are saved separately
and never substituted into those comparisons.  A third, explicitly named SC2
square-cap cohort matches absolute SC2 burdens across meshes. No frozen module
is patched.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import threading
import time

import numpy as np
import task1_frequency_resynthesis as frequency

ROOT = frequency.ROOT
GIB = frequency.GIB
SCHEMA = 'task1-frequency-sc4-sensitivity-preregistration-v1'
SC4_CASE = 'baseline-square15-sc4'
SOURCE_RUN = 'cloud-mesh-c1-20261019T190000Z'
SC4_SUMMARY = ROOT/'data-native'/SOURCE_RUN/'postprocess'/SC4_CASE/'summary.json'
SC2_SUMMARY = ROOT/'data-native'/SOURCE_RUN/'postprocess/baseline-square15-xy80/summary.json'
SC2_CUTOFF_SOURCE = ROOT/'docs/cloud-next-frequency-20261021T104000Z/sine-3000-3030-beat30/condition.json'
SC4_SQUARE_COHORT = 'cached_SC4_square_3000_3030_caps'
SC2_SQUARE_COHORT = 'cached_SC2_square_3000_3030_caps'
COHORTS = [SC4_SQUARE_COHORT, SC2_SQUARE_COHORT, 'fresh_sine_3000_3030_caps']
require = frequency.require
view = frequency.view
volume = frequency.volume
core = frequency.core
drive = frequency.drive


def validate_sc4_identity(item):
    meta = item['summary']['mesh_metadata']
    require(item['summary']['id'] == SC4_CASE and item['case']['id'] == SC4_CASE
        and item['run'].name == SOURCE_RUN and item['circuit']['n_pads'] == 4
        and item['circuit']['n_outputs'] == 2 and meta['h_xy_mm'] == .625
        and meta['sc_cells'] == 4 and meta['bulk_layer_counts'] == [14, 14, 40]
        and meta['cells'] == 361728 and meta['radius_mm'] == 25.
        and meta['total_depth_mm'] == 25.1 and meta['channels'] == 2
        and meta['frequencies_Hz'] == [3000, 3030, 9000, 9090],
        'Only the genuine fixed-D50 SC4 h.625 baseline is registered')
    require(frequency.drive.ranking.baseline_identity(item), 'Original four-square physical baseline required')
    drive.ranking.condition(item)
    volume.burdens(item, item['conditions'][0])
    return item


def source_item(path):
    require(Path(path).resolve() == SC4_SUMMARY.resolve(), 'Exact SC4 source summary path required')
    return validate_sc4_identity(view.load_case(path))


def refinement_contract(sc4_item, sc2_item):
    before, after = sc2_item['config'], sc4_item['config']
    changed = sorted(key for key in set(before)|set(after) if before.get(key) != after.get(key))
    allowed = ['validation.sc_cells']
    alias = None
    if before.get('mask.path') != after.get('mask.path'):
        require(before.get('mask.sha256') == after.get('mask.sha256') and before.get('mask.sha256'),
            'Mask path aliases require exactly the same declared byte digest')
        paths = [Path(before['mask.path']), Path(after['mask.path'])]
        for path in paths:
            require(path.is_absolute() and path == path.resolve() and path.is_relative_to(ROOT)
                and path.is_file() and not path.is_symlink()
                and view.sha(path) == before['mask.sha256'],
                'Both mask path aliases must be verified byte-identical local files')
        allowed.append('mask.path')
        alias = dict(original_path=str(paths[0]), SC4_path=str(paths[1]),
            SHA256=before['mask.sha256'], both_bytes_verified=True,
            scope='Byte-identical contact-mask path alias only; no contact geometry relaxation')
    require(changed == sorted(allowed) and before['validation.sc_cells'] == '2'
        and after['validation.sc_cells'] == '4' and sc4_item['circuit'] == sc2_item['circuit'],
        'SC2-to-SC4 comparison may change only SC cell count, never contact/geometry/circuit/materials')
    return dict(changed_config_fields=changed, original_SC_cells=2, new_SC_cells=4,
        geometry_contact_material_circuit_unchanged=True, mask_path_alias=alias)


def sc2_square_cap_reference(item):
    """Read actual source summary and full-skin audit JSON, never sine burdens."""
    condition = drive.ranking.condition(item)
    burden, current = volume.burdens(item, condition)
    return dict(id=condition['id'], burdens=burden, currents=current,
        waveform='square_3h', actual_fundamental_Hz=[3000, 3030], source_mesh_SC_cells=2,
        source_summary=str(item['path']), source_summary_sha256=view.sha(item['path']),
        provenance_scope='Actual original SC2 square summary and its source-bound completed full-skin JSON audit; not sine normalized burdens')


def fixed_sc2_cutoffs(receipt):
    provenance = receipt['source_provenance']
    require(receipt['status'] == 'calculated_unadopted'
        and provenance['case_id'] == 'baseline-square15-xy80'
        and provenance['run_id'] == SOURCE_RUN
        and receipt['actual_fundamental_Hz'] == [3000, 3030],
        'Actual original SC2 sine readback with square-cutoff provenance required')
    result = receipt['shared_square_baseline_cutoffs_V_m']
    require(set(result) == set(volume.METRICS), 'All three native scalar cutoff definitions required')
    names = {r+'_'+s for r in (volume.PRIMARY, volume.SLAB) for s in ('mean', 'p10')}
    for metric, values in result.items():
        require(set(values) == names and all(type(v) in (float, int) and math.isfinite(v) and v > 0
            for v in values.values()), 'Finite positive primary/supplemental mean/P10 cutoffs required')
    return json.loads(json.dumps(result))


def implementation_receipt():
    inherited = frequency.implementation_receipt()
    commit = inherited['implementation_git_commit']
    pins = dict(inherited['implementation_files_sha256'])
    for path in (Path(__file__).resolve(), ROOT/'tests/test_task1_frequency_sc4_resynthesis.py'):
        require(subprocess.check_output(['git', 'show', commit+':'+path.relative_to(ROOT).as_posix()], cwd=ROOT)
            == path.read_bytes(), 'SC4 source/tests must match committed HEAD: '+str(path))
        pins[str(path)] = view.sha(path)
    return dict(implementation_git_commit=commit, implementation_files_sha256=pins)


def make_preregistration(baseline_summary, output):
    """Metadata and source hashes only; no arrays or basis computation."""
    item = source_item(baseline_summary)
    sc2_item = drive.baseline_item(SC2_SUMMARY)
    refinement = refinement_contract(item, sc2_item)
    case, summary, run = item['case'], item['summary'], item['run']
    refs = drive.ranking.input_refs(item)
    refs.update(drive.ranking.input_refs(sc2_item))
    refs[str(Path(sc2_item['case']['mask_file']))] = sc2_item['case']['mask_sha256']
    refs.update(summary['input_sha256'])
    for name in ('volume.npz', summary['artifacts']['probes_json']):
        refs[str(item['path'].parent/name)] = summary['artifacts']['files'][name]['SHA256']
    refs[str(Path(case['mask_file']))] = case['mask_sha256']
    manifest_path = run/'frozen-source-manifest.json'
    refs[str(manifest_path)] = view.sha(manifest_path)
    manifest, resolved = view.read(manifest_path)['files'], {}
    for original, expected in item['registration']['source_and_input_sha256'].items():
        snapshot = manifest.get(original)
        chosen = ROOT/snapshot['path'] if snapshot else Path(original)
        require(chosen.is_file() and view.sha(chosen) == expected, 'Frozen source/input missing: '+original)
        refs[str(chosen.resolve())] = expected
        resolved[original] = str(chosen.resolve())
    cutoffs = fixed_sc2_cutoffs(view.read(SC2_CUTOFF_SOURCE))
    refs[str(SC2_CUTOFF_SOURCE)] = view.sha(SC2_CUTOFF_SOURCE)
    policy = frequency.policy_module()
    ledger = policy.load_ledger(ROOT/'runtime/task1-budget.json')
    policy_refs = policy.policy_refs(ledger)
    implementation = implementation_receipt()
    refs.update(implementation['implementation_files_sha256'])
    refs.update(policy_refs)
    return dict(schema=SCHEMA, status='preregistered_not_executed', created_utc=core.now(),
        feedback_id='T1-F010-frequency-GH6312627319', parent_feedback_id='T1-F010',
        source_comment_id=6312627319,
        source_comment_url='https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6312627319',
        baseline_summary=str(item['path']), baseline_summary_sha256=view.sha(item['path']),
        SC2_comparator_summary=str(sc2_item['path']), refinement_contract=refinement,
        SC2_square_cap_reference=sc2_square_cap_reference(sc2_item),
        output_directory=str(Path(output).resolve()), conditions=[dict(row) for row in frequency.CONDITIONS],
        native_input_sha256=summary['input_sha256'], input_sha256=refs,
        frozen_source_resolution=resolved, source_case_id=SC4_CASE, source_run_id=SOURCE_RUN,
        new_PDE_conditions=0, waveform='sine', cohorts=COHORTS.copy(),
        fixed_SC2_cutoffs_V_m=cutoffs,
        cutoff_reference=dict(path=str(SC2_CUTOFF_SOURCE), SHA256=refs[str(SC2_CUTOFF_SOURCE)],
            case_id='baseline-square15-xy80', mesh_SC_cells=2,
            scope='Unchanged numerical high-field cutoffs across SC2 and SC4, never physiological thresholds'),
        burden_reference_scope='SC4 square/fresh sine caps are same-grid references; separately named SC2 square caps give absolute cross-mesh burden matching',
        resource_policy_refs=policy_refs,
        resource_limits=dict(CPU_count=1, per_condition_seconds=180, total_seconds=480,
            preparation_seconds=60, finalization_seconds=60, RSS_bytes=3*GIB,
            disk_reserve_bytes=2*GIB, cumulative_budget_seconds=policy.effective_limit(ledger)),
        scope='SC2-to-SC4 negative-result sensitivity using exactly two SC4 sine re-syntheses and no new PDE',
        holds=['SC refinement sensitivity is not full SC/XY/bulk/edge/contact convergence or candidate adoption',
            'Carrier and beat both change30to90Hz; no physiological equivalence or carrier-only causal interpretation',
            '2074 sampled directions remain an angular lower bound; no continuum maximum claim',
            'Forty probe predictions are unloaded; no instrument-loading, human-safety, experiment or COMSOL claim'],
        **implementation)


def verify_plan(path, baseline_summary, output, expected=None):
    digest, plan = view.sha(path), view.read(path)
    require(expected is None or expected == digest, 'SC4 preregistration changed during execution')
    require(plan['schema'] == SCHEMA and plan['status'] == 'preregistered_not_executed'
        and plan['new_PDE_conditions'] == 0 and plan['waveform'] == 'sine'
        and plan['conditions'] == [dict(row) for row in frequency.CONDITIONS]
        and plan['baseline_summary'] == str(Path(baseline_summary).resolve())
        and plan['output_directory'] == str(Path(output).resolve())
        and plan['source_case_id'] == SC4_CASE and plan['cohorts'] == COHORTS,
        'Exact SC4 source and two actual sine conditions/output required')
    sc4_item = source_item(baseline_summary)
    sc2_item = drive.baseline_item(SC2_SUMMARY)
    require(plan['refinement_contract'] == refinement_contract(sc4_item, sc2_item), 'SC refinement contract changed')
    require(plan['SC2_square_cap_reference'] == sc2_square_cap_reference(sc2_item), 'SC2 square cap JSON reference changed')
    require(plan['fixed_SC2_cutoffs_V_m'] == fixed_sc2_cutoffs(view.read(SC2_CUTOFF_SOURCE)),
        'SC2 cutoff provenance or values changed')
    for name, expected_hash in plan['input_sha256'].items():
        source = Path(name)
        require(source.is_absolute() and source == source.resolve() and source.is_relative_to(ROOT)
            and source.is_file() and not source.is_symlink() and view.sha(source) == expected_hash,
            'Pinned SC4 input changed: '+name)
    require(view.read(baseline_summary)['input_sha256'] == plan['native_input_sha256'], 'SC4 native input manifest differs')
    require(implementation_receipt()['implementation_files_sha256'] == plan['implementation_files_sha256'],
        'SC4 implementation changed')
    return plan, digest


def execute(plan, baseline_summary, output, deadline, checkpoint):
    item = source_item(baseline_summary)
    cached = volume.load_native(item)
    post, scalar, probe = drive.import_frozen(item['run'], plan)
    basis = post._load_basis(item['run']/'bases'/item['case']['id'], item['case'], min(deadline, time.monotonic()+60))
    require(basis['hashes'] == plan['native_input_sha256'], 'Loaded SC4 native digest differs')
    geometry, volume_meta = post._geometry(basis, item['case'])
    require(np.array_equal(basis['grid'], cached['grid']), 'SC4 scalar/native grid mismatch')
    burden, current = volume.burdens(item, cached['condition'])
    references = {SC4_SQUARE_COHORT:dict(id=cached['condition']['id'], burdens=burden,
        currents=current, waveform='square_3h', actual_fundamental_Hz=[3000, 3030]),
        SC2_SQUARE_COHORT:plan['SC2_square_cap_reference']}
    own_cutoffs = {m:{r+'_'+s:volume.weighted_statistics(cached['arrays'][m], cached['regions'][r])[s]
        for r in (volume.PRIMARY, volume.SLAB) for s in ('mean', 'p10')} for m in volume.METRICS}
    own_receipt = dict(schema='task1-SC4-own-cutoff-reference-v1', source_case_id=SC4_CASE,
        source_summary=str(item['path']), source_summary_sha256=view.sha(item['path']),
        SC4_own_square_cutoffs_V_m=own_cutoffs, cross_mesh_fixed_SC2_cutoffs_V_m=plan['fixed_SC2_cutoffs_V_m'],
        SC4_own_cutoffs_used_for_high_volume_comparison=False,
        burden_reference_scope=plan['burden_reference_scope'])
    drive.write_json(output/'SC4-own-cutoff-reference.json', own_receipt)
    results = []
    for declared in plan['conditions']:
        condition_deadline = min(deadline, time.monotonic()+180)
        signal.setitimer(signal.ITIMER_REAL, max(.001, condition_deadline-time.monotonic()))
        folder = output/declared['id']
        folder.mkdir()
        checkpoint('condition_start', condition_id=declared['id'])
        results.append(frequency.derive(basis, geometry, volume_meta, cached, None, declared,
            post, scalar, probe, folder, condition_deadline, references, plan['fixed_SC2_cutoffs_V_m'], checkpoint))
        checkpoint('condition_complete', condition_id=declared['id'])
    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline-time.monotonic()))
    return dict(schema='task1-frequency-sc4-sensitivity-audit-v1', status='calculated_unadopted',
        conditions=results, actual_frequency_pairs=[list(x) for x in frequency.PAIRS], actual_beat_frequencies_Hz=[30, 90],
        waveform='sine', new_PDE=0, source_case_id=SC4_CASE, source_mesh_SC_cells=4,
        source_summary=str(item['path']), comparison_cohorts=COHORTS.copy(),
        SC2_square_cap_reference=plan['SC2_square_cap_reference'],
        fixed_cross_mesh_SC2_cutoffs_V_m=plan['fixed_SC2_cutoffs_V_m'],
        SC4_own_cutoff_reference=dict(path=str(output/'SC4-own-cutoff-reference.json'),
            SHA256=view.sha(output/'SC4-own-cutoff-reference.json')),
        burden_reference_scope=plan['burden_reference_scope'], holds=plan['holds'],
        candidate_adopted=False, numerical_validation_promoted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-summary', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT/'docs') and output.relative_to(ROOT/'docs').parts[0].startswith('cloud-next'),
        'New docs/cloud-next... output required')
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not output.exists(), 'Never overwrite attempted SC4 resynthesis')
        policy = frequency.policy_module()
        ledger_path = ROOT/'runtime/task1-budget.json'
        ledger = policy.load_ledger(ledger_path)
        require(policy.remaining_seconds(ledger) >= 480, 'SC4 admission requires finite480s in authorized policy')
        require(shutil.disk_usage(output.parent).free >= 2*GIB+256*1024**2, 'Preserve2GiB reserve plus256MiB artifacts')
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        output.mkdir()
        started = time.monotonic()
        deadline = started+480
        status, failure, state, counter = 'failed_preserved', None, {}, 0
        mutex, stop = threading.RLock(), threading.Event()
        def checkpoint(phase, **extra):
            nonlocal counter
            with mutex:
                require(core.rss(os.getpid()) < 3*GIB, 'SC4 existing3GiB RSS cap exceeded')
                require(shutil.disk_usage(output).free >= 2*GIB, 'SC4 existing2GiB disk reserve exhausted')
                counter += 1
                state.update(phase=phase, status=status if phase == 'complete' else 'running', pid=os.getpid(),
                    proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now(),
                    elapsed_seconds=time.monotonic()-started, **extra)
                drive.write_json(output/f'checkpoint-{counter:03d}-{phase}.json', dict(state))
                core.write(output/'heartbeat.json', state)
        def heartbeat():
            while not stop.wait(5.):
                with mutex:
                    core.write(output/'heartbeat.json', dict(state, updated_utc=core.now(), elapsed_seconds=time.monotonic()-started))
        def timeout(signum, frame):
            raise TimeoutError('SC4 finite180s condition/480s total deadline exceeded')
        def interrupted(signum, frame):
            raise RuntimeError('SC4 controlled signal '+str(signum))
        previous = {s:signal.getsignal(s) for s in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT)}
        signal.signal(signal.SIGALRM, timeout)
        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)
        signal.setitimer(signal.ITIMER_REAL, 60)
        thread = threading.Thread(target=heartbeat, daemon=True)
        try:
            thread.start()
            checkpoint('verify_plan')
            plan, digest = verify_plan(args.plan.resolve(), args.baseline_summary, output)
            result = execute(plan, args.baseline_summary, output, deadline, checkpoint)
            verify_plan(args.plan.resolve(), args.baseline_summary, output, expected=digest)
            result.update(implementation_receipt(), preregistration=dict(path=str(args.plan.resolve()), SHA256=digest),
                input_sha256=plan['input_sha256'], inputs_unchanged=True, wall_seconds=time.monotonic()-started,
                resources=dict(CPU_count=1, authorized_cumulative_seconds=policy.effective_limit(ledger),
                    max_batch_seconds=480, max_condition_seconds=180,
                    peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
            drive.write_json(output/'summary.json', result)
            status = result['status']
            checkpoint('complete')
        except BaseException as error:
            failure = type(error).__name__+': '+str(error)
            drive.write_json(output/'failure.json', dict(status=status, error=failure, new_PDE=0, partial_artifacts_preserved=True))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            stop.set()
            if thread.ident is not None:
                thread.join(timeout=1)
            elapsed = time.monotonic()-started
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=output.name, stage='actual_frequency_SC4_sensitivity', seconds=elapsed,
                status=status, error=failure, finished_utc=core.now()))
            core.write(ledger_path, ledger)
            with mutex:
                core.write(output/'heartbeat.json', dict(state, status=status, error=failure, updated_utc=core.now(), elapsed_seconds=elapsed))
            for signum, handler in previous.items():
                signal.signal(signum, handler)
        print(json.dumps(dict(status=status, output=str(output), new_PDE=0)))


if __name__ == '__main__':
    main()
