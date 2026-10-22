#!/usr/bin/env python3
"""Finite JSON-only eight-gate candidate screen; never adopt or read fields."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

import task1_resource_policy as policy

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
SCHEMA = 'task1-candidate-screen-preregistration-v1'
TEMPLATE = ROOT/'docs/cloud-next-20261021T085200Z/return-role-screen.json'
DEFINITION_VOLUME = ROOT/'docs/cloud-next-20261021T085200Z/return-role-volume.json'
BASELINE_ID = 'baseline-square15-xy80'
BASELINE_SUMMARY = ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess'/BASELINE_ID/'summary.json'
PRIMARY = 'primary_r5_depth15_20'
MODES = ('raw_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power',
    'skin_contact_only', 'legacy_composite_full_skin')
NATIVE_GATES = dict(max_residual=2e-7, max_power_error=2e-7, max_current_error=2e-6,
    max_area_relative_error=1e-10, max_interface_normal_current_relative_error=2e-7)
CAP_DEGREES = dict(surface_J_RMS_max_A_m2=1, surface_J_RMS_p95_A_m2=1,
    contact_voltage_RMS_max_V=1, SC_power_W=2, contact_power_W=2,
    bulk_skin_J_vector_RMS_max_A_m2=1, bulk_skin_J_vector_RMS_p95_A_m2=1,
    skin_SC_plus_dermis_power_W=2)
GATE_DEFINITIONS = [dict(name='primary_maxTIS_'+stat, unit='V/m', required_direction='greater')
    for stat in ('mean', 'p10')]
for _region in ('surface_0_5', 'primary_complement'):
    GATE_DEFINITIONS.append(dict(name=_region+'_maxTIS_p95', unit='V/m', required_direction='less'))
    GATE_DEFINITIONS.extend(dict(name=_region+'_high_volume_at_'+PRIMARY+'_'+stat,
        unit='m3', required_direction='less') for stat in ('mean', 'p10'))


def require(ok, message):
    if not ok: raise ValueError(message)


def now(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def number(x): return type(x) in (int, float) and math.isfinite(x)
def tolerance(baseline, unit='V/m'): return (1e-18 if unit == 'm3' else 1e-12)+1e-10*abs(baseline)


def new_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def local(path):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve() and path.is_relative_to(ROOT)
        and path.is_file() and not path.is_symlink(), 'Existing absolute local non-symlink input required: '+str(path))
    return path


def metadata_hash(path):
    path = local(path)
    require(path.suffix in ('.json', '.py', '.java', '.properties', '.csv')
        and path.name not in ('grid.csv',), 'Screen never opens native fields, potentials or array archives: '+str(path))
    return sha(path)


def comparison_signature(summary, config_path):
    config = {}
    for line in Path(config_path).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1); config[key.strip()] = value.strip()
    mesh = summary['mesh_metadata']
    values = {key:mesh.get(key) for key in ('h_xy_mm', 'radius_mm', 'total_depth_mm', 'sc_cells',
        'bulk_layer_counts', 'z_faces_mm', 'tissue_boundaries_mm', 'field_reconstruction', 'source_resistance_ohm')}
    values['physical_models'] = {key:value for key, value in config.items()
        if key.endswith(('.sigma', '.epsilon_r')) or key.startswith('z.')}
    values['target'] = 'r<=5mm; surface-depth15<=z<=20mm; fractional native volume'
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def bind(path, refs):
    path = local(path)
    require(refs.get(str(path)) == metadata_hash(path), 'Source metadata missing or changed in volume report: '+str(path))
    return read(path) if path.suffix == '.json' else path


def implementation_refs():
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    refs = {}
    for p in (Path(__file__).resolve(), ROOT/'tests/test_task1_candidate_screen.py', Path(policy.__file__).resolve()):
        require(subprocess.check_output(['git', 'show', commit+':'+p.relative_to(ROOT).as_posix()], cwd=ROOT)
            == p.read_bytes(), 'Screen implementation/tests/policy must match committed HEAD: '+str(p))
        refs[str(p)] = sha(p)
    return dict(source_commit=commit, implementation_files_sha256=refs)


def gate_values(row):
    regions = row['normalizations']['skin_contact_only']['regions']
    values = {d['name']:regions[PRIMARY]['maxTIS'][d['name'].removeprefix('primary_maxTIS_')]
        for d in GATE_DEFINITIONS[:2]}
    for region in ('surface_0_5', 'primary_complement'):
        metric = regions[region]['maxTIS']
        values[region+'_maxTIS_p95'] = metric['p95']
        for stat in ('mean', 'p10'):
            cutoff = PRIMARY+'_'+stat
            values[region+'_high_volume_at_'+cutoff] = metric['fixed_baseline_threshold_volume'][cutoff]['volume_m3']
    return values


def screen_checks(candidate, baseline):
    a, b = gate_values(candidate), gate_values(baseline)
    checks = []
    for definition in GATE_DEFINITIONS:
        key, unit = definition['name'], definition['unit']
        require(number(a[key]) and a[key] >= 0 and number(b[key]) and b[key] > 0,
            'Finite candidate and positive baseline screen values required')
        eps = tolerance(b[key], unit)
        passed = a[key] >= b[key]-eps if definition['required_direction'] == 'greater' else a[key] <= b[key]+eps
        checks.append(dict(definition, baseline=b[key], candidate=a[key], passed=passed,
            relative_change_percent=100*(a[key]/b[key]-1), arithmetic_tolerance=eps))
    return checks


def make_preregistration(run, candidate_ids, baseline_summary=BASELINE_SUMMARY):
    """Metadata-only registration; invoke after source preparation, before PDE."""
    run, baseline_summary = Path(run).resolve(), Path(baseline_summary).resolve()
    require(baseline_summary == BASELINE_SUMMARY.resolve(), 'Exact original h.625 SC2 four-pad baseline required')
    pre = read(local(run/'preregistration.json'))
    require(pre['status'] == 'prepared' and 1 <= len(candidate_ids) <= 8
        and len(set(candidate_ids)) == len(candidate_ids)
        and set(candidate_ids) <= {c['id'] for c in pre['cases']}, 'Prepared finite unique candidate IDs required')
    require(not any((run/'cases'/(ident+'.json')).exists() for ident in candidate_ids), 'Screen must be registered before candidate attempts')
    definition = read(TEMPLATE)
    require([{k:c[k] for k in ('name', 'unit', 'required_direction')} for c in definition['checks']]
        == GATE_DEFINITIONS, 'Historical eight screen definitions changed')
    base = next(c for c in read(DEFINITION_VOLUME)['cases'] if c['case_id'] == BASELINE_ID)
    values = gate_values(base)
    require(all(c['baseline'] == values[c['name']] for c in definition['checks']), 'Historical gate baseline differs')
    ledger = policy.load_ledger(ROOT/'runtime/task1-budget.json')
    refs = {str(p):metadata_hash(p) for p in (TEMPLATE, DEFINITION_VOLUME, baseline_summary, run/'preregistration.json')}
    implementation = implementation_refs(); refs.update(implementation['implementation_files_sha256'])
    refs.update(policy.policy_refs(ledger))
    return dict(schema=SCHEMA, status='preregistered_not_executed', created_utc=now(),
        baseline_case_id=BASELINE_ID, baseline_summary_path=str(baseline_summary),
        candidate_case_ids=list(candidate_ids), run_path=str(run), run_registration_sha256=sha(run/'preregistration.json'),
        gate_definition_source=dict(path=str(TEMPLATE), SHA256=sha(TEMPLATE)),
        eight_gates=[dict(d, baseline=values[d['name']]) for d in GATE_DEFINITIONS],
        fixed_baseline_cutoffs_V_m=base['fixed_same_grid_baseline_cutoffs_V_m'],
        primary_ROI=PRIMARY, normalization='skin_contact_only', native_gate_limits=NATIVE_GATES,
        resource_policy_refs=policy.policy_refs(ledger), input_sha256=refs,
        resources=dict(CPU_count=1, max_seconds=120, RSS_bytes=3*GIB, disk_reserve_bytes=2*GIB,
            cumulative_seconds=policy.effective_limit(ledger)),
        no_adoption=True, no_new_PDE=True, **implementation)


def verify_plan(path):
    plan = read(local(path))
    require(plan['schema'] == SCHEMA and plan['status'] == 'preregistered_not_executed'
        and plan['baseline_case_id'] == BASELINE_ID and plan['baseline_summary_path'] == str(BASELINE_SUMMARY.resolve())
        and plan['normalization'] == 'skin_contact_only' and plan['primary_ROI'] == PRIMARY
        and plan['native_gate_limits'] == NATIVE_GATES,
        'Original baseline, fixed ROI, normalization and native numerical gates required')
    require([{k:c[k] for k in ('name', 'unit', 'required_direction')} for c in plan['eight_gates']]
        == GATE_DEFINITIONS, 'Exactly the historical eight screen directions and quantities are required')
    for p, digest in plan['input_sha256'].items():
        require(metadata_hash(p) == digest, 'Preregistered screen metadata changed: '+p)
    require(sha(Path(plan['run_path'])/'preregistration.json') == plan['run_registration_sha256'], 'Prepared run registration changed')
    require(implementation_refs()['implementation_files_sha256'] == plan['implementation_files_sha256'], 'Screen implementation changed')
    return plan


def validate_statistics(row, baseline):
    require(set(row['normalizations']) == set(MODES), 'All five unmodified normalization modes required')
    require(row['fixed_same_grid_baseline_cutoffs_V_m'] == baseline['fixed_same_grid_baseline_cutoffs_V_m'],
        'Candidate cutoffs differ from original baseline; no rescaled/derived cutoff substitution')
    for mode_name, mode in row['normalizations'].items():
        require(number(mode['amplitude_scale']) and mode['amplitude_scale'] > 0, 'Finite positive scale required')
        require(set(mode['regions']) == {'total', PRIMARY, 'supplemental_wholeXY_depth15_20',
            'surface_0_5', 'primary_complement', 'supplemental_complement'}, 'All six fixed ROI/complement masks required')
        require(all(number(v) and v >= 0 for v in mode['normalized_burdens'].values())
            and len(mode['source_output_RMS_by_output_mA']) == 2
            and all(number(v) and v > 0 for v in mode['source_output_RMS_by_output_mA'])
            and abs(sum(mode['source_output_RMS_by_output_mA'])-mode['sum_source_output_RMS_mA'])
                <= tolerance(mode['sum_source_output_RMS_mA']), 'Finite original power/current burden metrics required')
        for region, metrics in mode['regions'].items():
            represented = row['represented_geometry'][region]['represented_volume_m3']
            base_volume = baseline['represented_geometry'][region]['represented_volume_m3']
            require(number(represented) and represented > 0 and abs(represented-base_volume) <= tolerance(base_volume, 'm3'),
                'Same positive represented ROI/non-target weights required')
            for quantity in ('maxTIS', 'fixedTIS', 'RMS'):
                stats = metrics[quantity]
                require(all(number(stats[k]) and stats[k] >= 0 for k in ('mean', 'p10', 'p95', 'min', 'max', 'CV', 'std'))
                    and stats['min'] <= stats['p10'] <= stats['p95'] <= stats['max']
                    and stats['min'] <= stats['mean'] <= stats['max']
                    and number(stats['volume_m3']) and stats['volume_m3'] > 0
                    and abs(stats['volume_m3']-represented) <= tolerance(represented, 'm3')
                    and type(stats['positive_weight_cells']) is int and stats['positive_weight_cells'] > 0,
                    'Complete finite volume-weighted statistics required; no aggregate reconstruction')
                fixed = stats['fixed_baseline_threshold_volume']
                require(set(fixed) == set(baseline['fixed_same_grid_baseline_cutoffs_V_m'][quantity]), 'All frozen cutoff volumes required')
                for key, entry in fixed.items():
                    expected = baseline['fixed_same_grid_baseline_cutoffs_V_m'][quantity][key]
                    require(entry['cutoff_V_m'] == expected and number(entry['volume_m3'])
                        and 0 <= entry['volume_m3'] <= stats['volume_m3']+tolerance(stats['volume_m3'], 'm3')
                        and number(entry['region_volume_fraction'])
                        and abs(entry['region_volume_fraction']-entry['volume_m3']/stats['volume_m3']) <= 1e-10,
                        'High-field volume cutoff/weight binding differs')
    limits = baseline['normalizations']['raw_1Vpp']['normalized_burdens']
    mode = row['normalizations']['skin_contact_only']
    require(set(mode['baseline_derived_numerical_limits']) == set(limits)
        and mode['baseline_derived_numerical_limits'] == limits, 'Normalization baseline caps changed')
    for key in CAP_DEGREES:
        value = mode['normalized_burdens'][key]
        require(number(value) and 0 <= value <= limits[key]+tolerance(limits[key]), 'Normalized skin/contact cap violation: '+key)
    require(mode['includes_source_power_cap'] is False and mode['includes_1Vpp_ceiling'] is False,
        'skin_contact_only must retain its original eight-cap definition')


def source_receipt(row, report_refs):
    path = local(row['summary_path']); run = path.parents[2]
    summary = bind(path, report_refs)
    pre_path, record_path = run/'preregistration.json', run/'cases'/(row['case_id']+'.json')
    pre, record = bind(pre_path, report_refs), bind(record_path, report_refs)
    require(summary['status'] == record['status'] == 'complete' and summary['id'] == record['id'] == row['case_id']
        and record['postprocess_path'] == str(path) and record['postprocess_sha256'] == sha(path), 'Core case completion/summary SHA binding failed')
    require(pre['gates'] == NATIVE_GATES and row['source_commit'] == pre['source_commit'], 'Source commit or native gate definitions differ')
    cases = [c for c in pre['cases'] if c['id'] == row['case_id']]
    require(len(cases) == 1, 'One registered native case required')
    case = cases[0]; config_path = Path(case['config_file']); bind(config_path, report_refs)
    digest = sha(config_path)
    require(digest == case['config_sha256'] == record['config_sha256'] == row['configuration_sha256']
        == summary['mesh_metadata']['config_sha256'], 'Case config SHA binding failed')
    for key, limit in NATIVE_GATES.items():
        value = summary['validation'][key]
        require(number(value) and 0 <= value <= limit and record['validation'][key] == value
            and summary['validation_gate_status'][key]['status'] == 'passed'
            and summary['validation_gate_status'][key]['value'] == value
            and summary['validation_gate_status'][key]['limit'] == limit, 'Native equation gate failed or forged: '+key)
    terminal = read(local(run/'summary.json'))
    require(terminal['status'] == 'complete' and terminal['registration_sha256'] == sha(pre_path)
        and terminal['source_commit'] == pre['source_commit'], 'Core batch terminal receipt differs')
    terminal_cases = [c for c in terminal['cases'] if c['id'] == row['case_id']]
    require(len(terminal_cases) == 1 and terminal_cases[0] == record, 'Core batch case receipt differs from case file')
    manifest_path = run/'frozen-source-manifest.json'
    manifest = bind(manifest_path, report_refs)
    require(manifest['source_commit'] == pre['source_commit'], 'Frozen source commit mismatch')
    for original, snapshot in manifest['files'].items():
        frozen = Path(snapshot['path'])
        if not frozen.is_absolute(): frozen = ROOT/frozen
        require(pre['source_and_input_sha256'].get(original) == snapshot['sha256']
            and metadata_hash(frozen) == snapshot['sha256'], 'Frozen implementation hash mismatch')
    require(row['mesh'] == summary['mesh_metadata'], 'Report mesh differs from native source')
    require(row['comparison_signature'] == comparison_signature(summary, config_path), 'Claimed comparison signature differs from actual model/config')
    return dict(summary=dict(path=str(path), SHA256=sha(path)), registration=dict(path=str(pre_path), SHA256=sha(pre_path)),
        case_record=dict(path=str(record_path), SHA256=sha(record_path)), config_SHA256=digest,
        source_commit=pre['source_commit'], frozen_source_manifest=dict(path=str(manifest_path), SHA256=sha(manifest_path)),
        native_self_gates=dict(values={k:summary['validation'][k] for k in NATIVE_GATES}, limits=NATIVE_GATES,
            passed=True, scope='Existing five discrete equation gates only; not mesh or experiment validation'))


def build_screen(plan, report_path):
    report = read(local(report_path))
    require(report['schema'] == 'task1-volume-selectivity-v1' and report['status'] == 'calculated_unadopted'
        and report['inputs_unchanged'] is True and report['new_PDE_solves'] == 0, 'Completed input-preserving native-volume audit required')
    prereg = report['preregistration']; report_plan = local(prereg['path'])
    require(prereg['verified_before_and_after'] is True and sha(report_plan) == prereg['SHA256']
        and report['inputs_sha256'].get(str(report_plan)) == prereg['SHA256'], 'Volume report preregistration SHA verification missing')
    volume_plan = read(report_plan)
    require(volume_plan['status'] == 'preregistered_not_executed' and volume_plan['new_PDE_conditions'] == 0,
        'Actual volume plan binding required')
    refs = report['inputs_sha256']
    require(all(refs.get(p) == digest for p, digest in volume_plan['input_sha256'].items()),
        'Volume report does not preserve its preregistered input SHA bindings')
    require([str(Path(c['summary']).resolve()) for c in volume_plan['cases']]
        == [r['summary_path'] for r in report['cases']], 'Volume report case order differs from actual preregistration')
    by_id = {r['case_id']:r for r in report['cases']}
    require(len(by_id) == len(report['cases']), 'Duplicate volume case IDs')
    ids = plan['candidate_case_ids']
    require(1 <= len(ids) <= 8 and len(set(ids)) == len(ids) and BASELINE_ID not in ids
        and set([BASELINE_ID, *ids]) <= set(by_id), 'Exact baseline and registered candidates required')
    baseline = by_id[BASELINE_ID]
    require(baseline['summary_path'] == plan['baseline_summary_path']
        and baseline['fixed_same_grid_baseline_cutoffs_V_m'] == plan['fixed_baseline_cutoffs_V_m'], 'Baseline identity/cutoffs changed')
    require([dict(d, baseline=gate_values(baseline)[d['name']]) for d in GATE_DEFINITIONS] == plan['eight_gates'], 'Historical eight baseline gate values changed')
    base_receipt = source_receipt(baseline, refs); validate_statistics(baseline, baseline)
    rows = []
    for ident in ids:
        row = by_id[ident]
        require(Path(row['summary_path']).parents[2] == Path(plan['run_path'])
            and row['baseline_summary'] == baseline['summary_path']
            and row['comparison_signature'] == baseline['comparison_signature'], 'Candidate run/baseline/comparison signature mismatch')
        receipt = source_receipt(row, refs); validate_statistics(row, baseline)
        checks = screen_checks(row, baseline)
        passed = all(c['passed'] for c in checks)
        rows.append(dict(case_id=ident, run_id=row['run_id'], checks=checks, all_screen_checks_passed=passed,
            failed_checks=[c['name'] for c in checks if not c['passed']],
            decision='Eligible only for separately preregistered mesh/contact diagnostics' if passed else 'Reject candidate nomination under unchanged eight-gate screen',
            native_source_receipt=receipt, all_five_normalizations=copy.deepcopy(row['normalizations']),
            circuit=row['circuit'], mesh=row['mesh'], physical_model_version=row['physical_model_version'],
            raw_probe_artifact_reference=row['raw_probe_artifact_reference'], candidate_adopted=False))
    return dict(schema='task1-candidate-screen-v1', status='screen_complete_not_adopted', created_utc=now(),
        input_volume_report=dict(path=str(report_path), SHA256=sha(report_path)),
        source_hash_scope='JSON/configuration/frozen implementation only; native fields/potentials/NPZ not read or independently reproduced',
        normalization='skin_contact_only', baseline_case_id=BASELINE_ID, baseline_native_receipt=base_receipt,
        fixed_baseline_cutoffs_V_m=plan['fixed_baseline_cutoffs_V_m'], cases=rows,
        candidate_adopted=False, full_convergence_validated=False, experimentally_validated=False,
        holds=['Native five gates and eight comparison screens do not establish mesh/SC/XY/bulk/edge/contact convergence',
            'PBS interface is not verified actual skin contact; thresholds are numerical comparisons, not physiology or safety',
            '2074 sampled directions remain a lower bound; unloaded probes and C1 remain separate evidence'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preregistration', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); output = args.output.resolve()
    require(output.is_relative_to(ROOT/'docs') and output.parent.is_dir(), 'Existing docs directory and unique new output required')
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB); fcntl.lockf(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not output.exists() and not output.with_suffix('.attempt.json').exists(), 'Never overwrite/retry attempted screen evidence')
        ledger_path = ROOT/'runtime/task1-budget.json'; ledger = policy.load_ledger(ledger_path)
        require(policy.remaining_seconds(ledger) >= 120, 'Screen requires finite120s remaining authorized time')
        require(shutil.disk_usage(output.parent).free >= 2*GIB+32*1024**2, 'Preserve2GiB disk reserve and bounded JSON output')
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        started = time.monotonic(); status, failure = 'failed_preserved', None
        new_json(output.with_suffix('.attempt.json'), dict(status='running', pid=os.getpid(), started_utc=now()))
        previous = {s:signal.getsignal(s) for s in (signal.SIGALRM, signal.SIGINT, signal.SIGTERM)}
        def interrupt(signum, frame): raise TimeoutError('Finite screen deadline/signal '+str(signum))
        for sig in previous: signal.signal(sig, interrupt)
        signal.setitimer(signal.ITIMER_REAL, 120)
        try:
            plan = verify_plan(args.preregistration); digest = sha(args.preregistration)
            require(plan['resource_policy_refs'] == policy.policy_refs(ledger), 'Screen authorized policy binding changed')
            result = build_screen(plan, args.report.resolve())
            require(sha(args.preregistration) == digest, 'Screen plan changed during calculation')
            verify_plan(args.preregistration)
            require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 < 3*GIB, 'Existing3GiB RSS cap exceeded')
            result.update(implementation_refs(), preregistration=dict(path=str(args.preregistration.resolve()), SHA256=digest),
                resources=dict(wall_seconds=time.monotonic()-started, max_seconds=120, CPU_count=1,
                    global_limit_seconds=policy.effective_limit(ledger), peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
            new_json(output, result); status = result['status']
        except BaseException as error:
            failure = type(error).__name__+': '+str(error)
            new_json(output.with_suffix('.failure.json'), dict(status=status, error=failure, evidence_preserved=True)); raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-started; ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=output.stem, stage='candidate_eight_gate_screen', seconds=elapsed,
                status=status, error=failure, finished_utc=now()))
            temporary = ledger_path.with_suffix('.partial'); temporary.write_text(json.dumps(ledger, indent=2)+'\n'); temporary.replace(ledger_path)
            for sig, handler in previous.items(): signal.signal(sig, handler)
        print(json.dumps(dict(status=status, cases=len(result['cases']), output=str(output))))


if __name__ == '__main__': main()
