"""Common electrical cutoffs across two completed contact cohorts; no PDE.

Metadata-only make_preregistration returns a plan. Execution reads cached scalar
NPZ/grid/metadata/probes through reviewed loaders; unused E/phi are never read.
Each cohort retains its OWN immutable skin-contact amplitude normalization.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
REGIONS = ('total', 'primary_r5_depth15_20', 'supplemental_wholeXY_depth15_20',
           'surface_0_5', 'primary_complement', 'supplemental_complement')
MODES = ('raw_1Vpp', 'skin_contact_only')
CASE_IDS = ('baseline-square15-xy80', 'cross17p5-arm10-xy80',
            'baseline-square15-rs2000-xy80', 'cross17p5-arm10-rs2000-xy80')
REPORTS = tuple(ROOT/'docs/cloud-continuation-20261021'/name for name in
                ('volume-cross.json', 'volume-contact.json'))


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def source_files():
    return [Path(__file__), *[ROOT/'tools'/name for name in
        ('task1_volume_selectivity.py', 'task1_results_view.py', 'task1_candidate_ranking.py')]]


def make_preregistration(report_paths=REPORTS):
    """Read only report/summary JSON and source identities; do not read NPZ bytes."""
    paths = [Path(path).resolve() for path in report_paths]
    require(len(paths) == 2 and len(set(paths)) == 2, 'Exactly two distinct completed volume reports required')
    reports = [read(path) for path in paths]
    cases, pins = [], {str(path): sha(path) for path in paths}
    for report_index, (path, report) in enumerate(zip(paths, reports)):
        require(report.get('schema') == 'task1-volume-selectivity-v1' and
                report.get('status') == 'calculated_unadopted' and report.get('new_PDE_solves') == 0 and
                report.get('inputs_unchanged') is True, 'Complete input-preserving volume reports required')
        for ident in CASE_IDS[report_index*2:report_index*2+2]:
            matches = [row for row in report['cases'] if row['case_id'] == ident]
            require(len(matches) == 1, 'One exact source case required: '+ident)
            row = matches[0]
            summary_path = Path(row['summary_path']).resolve()
            summary = read(summary_path)
            require(summary.get('id') == ident and summary.get('status') == 'complete', 'Completed source summary required')
            digest = sha(summary_path)
            require(report['inputs_sha256'].get(str(summary_path)) == digest,
                    'Report source-summary SHA differs')
            archive = summary_path.parent/'volume.npz'
            archive_sha = summary['artifacts']['files']['volume.npz']['SHA256']
            require(report['inputs_sha256'].get(str(archive)) == archive_sha,
                    'Report/summary NPZ manifest hashes differ')
            require(row['baseline_summary'] == report['cases'][0]['summary_path'],
                    'Each case must retain its own contact-model baseline')
            skin_scale = row['normalizations']['skin_contact_only']['amplitude_scale']
            require(math.isfinite(skin_scale) and skin_scale > 0 and
                    row['normalizations']['raw_1Vpp']['amplitude_scale'] == 1., 'Immutable own-model amplitudes required')
            cases.append(dict(case_id=ident, source_report=str(path), source_report_sha256=pins[str(path)],
                summary_path=str(summary_path), summary_sha256=digest, volume_npz=str(archive),
                volume_npz_manifest_sha256=archive_sha, own_baseline_summary=row['baseline_summary'],
                own_comparison_signature=row['comparison_signature'],
                own_model_amplitude_scales=dict(raw_1Vpp=1., skin_contact_only=skin_scale)))
            pins[str(summary_path)] = digest
    nominal = reports[0]['cases'][0]
    require(nominal['case_id'] == CASE_IDS[0], 'Nominal500 baseline must be first source row')
    cutoffs = nominal['fixed_same_grid_baseline_cutoffs_V_m']['maxTIS']
    expected = {region+'_'+stat for region in REGIONS[1:3] for stat in ('mean', 'p10')}
    require(set(cutoffs) == expected and all(math.isfinite(x) and x > 0 for x in cutoffs.values()),
            'Exactly four nominal500 raw-baseline maxTIS cutoffs required')
    for path in source_files():
        pins[str(path.resolve())] = sha(path)
    return dict(schema='task1-common-cutoff-preregistration-v1', status='preregistered_not_executed',
        created_utc=now(), feedback_id='T1-F010-S2-GH6308380231', source_comment_id=6308380231,
        source_comment_url='https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6308380231',
        source_reports=[dict(path=str(p), sha256=sha(p)) for p in paths],
        cases=cases, common_cutoffs_V_m=dict(cutoffs), common_cutoff_source_case=CASE_IDS[0],
        modes=list(MODES), regions=list(REGIONS), normalization='Each source report own-model skin_contact_only scale is retained verbatim; no cross-model burden normalization',
        comparison='Same physical scalar threshold >= four fixed nominal500 raw cutoff values; electrical, not biological',
        regression=dict(relative=1e-12, absolute_V_m=1e-14, scope='raw primary maxTIS mean/P10 vs completed source volume report'),
        resources=dict(cpu=1, total_seconds=180, per_case_seconds=60, cumulative_limit_seconds=6600,
            RSS_bytes=3*GIB, disk_reserve_bytes=2*GIB, lock='global flock and POSIX lockf'),
        new_PDE_solves=0, candidate_adopted=False, input_sha256=pins,
        unused_native_arrays='No field/potential array read; only cached scalar NPZ and source-bound grid/metadata/probes',
        limitations=['Different contact models intentionally retained; common thresholds do not equalize their physical burdens',
                    'No mesh/experimental validation, activation, safety or adoption claim'])


def own_scales(case, report_row):
    """Never derive an Rs2000 scale from nominal500 burdens."""
    scales = {mode: float(report_row['normalizations'][mode]['amplitude_scale']) for mode in MODES}
    require(scales == case['own_model_amplitude_scales'] and scales['raw_1Vpp'] == 1. and
            all(math.isfinite(x) and x > 0 for x in scales.values()), 'Own-model immutable normalization changed')
    require(report_row['baseline_summary'] == case['own_baseline_summary'], 'Cross-model normalization prohibited')
    return scales


def summarize(values, weights, scale, cutoffs, volume):
    import numpy as np
    require(math.isfinite(scale) and scale > 0, 'Positive finite amplitude required')
    values, weights = np.asarray(values, float)*scale, np.asarray(weights, float)
    stats = volume.weighted_statistics(values, weights)
    return dict(mean=stats['mean'], p10=stats['p10'], p95=stats['p95'], maximum=stats['max'],
        represented_volume_m3=stats['volume_m3'], common_cutoff_volumes={name: dict(cutoff_V_m=float(cutoff),
            volume_m3=float(weights[values >= cutoff].sum()),
            fraction=float(weights[values >= cutoff].sum()/weights.sum()), comparison='>=',
            quantity='sampled-direction fundamental modulation; not activation') for name, cutoff in cutoffs.items()})


def require_same_geometry(reference, data):
    import numpy as np
    grid, regions = data['grid'], data['regions']
    require(tuple(regions) == REGIONS and all(region in regions for region in REGIONS), 'Exactly six ROI weights required')
    if reference is None:
        return dict(grid=grid.copy(), regions={name: weights.copy() for name, weights in regions.items()})
    require(grid.dtype == reference['grid'].dtype and grid.shape == reference['grid'].shape and
            grid.tobytes() == reference['grid'].tobytes(), 'Cross-model source grids are not byte/value identical')
    for name in REGIONS:
        a, b = np.asarray(regions[name]), np.asarray(reference['regions'][name])
        require(a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes(),
                'Cross-model fractional ROI weights differ: '+name)
    return reference


def verify_plan(plan):
    require(plan.get('schema') == 'task1-common-cutoff-preregistration-v1' and
            plan.get('status') == 'preregistered_not_executed' and
            [c['case_id'] for c in plan['cases']] == list(CASE_IDS), 'Exact four-case preregistration required')
    expected = make_preregistration([r['path'] for r in plan['source_reports']])
    for key in ('source_reports', 'cases', 'common_cutoffs_V_m', 'modes', 'regions', 'regression', 'resources', 'input_sha256'):
        require(plan[key] == expected[key], 'Preregistered identity or definition changed: '+key)
    for path, digest in plan['input_sha256'].items():
        require(sha(path) == digest, 'Pinned report/source changed: '+path)


def committed_implementation():
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, timeout=5).strip()
    pins = {}
    for path in source_files():
        content = subprocess.check_output(['git', 'show', commit+':'+str(path.relative_to(ROOT))], cwd=ROOT, timeout=5)
        require(path.read_bytes() == content, 'Implementation must match committed HEAD: '+str(path))
        pins[str(path)] = sha(path)
    return dict(commit=commit, source_sha256=pins)


def build_report(plan, deadline, arm_case, *, volume=None, loader=None):
    if volume is None:
        import task1_volume_selectivity as volume
    loader = loader or volume.view.load_case
    reports = {row['path']: read(row['path']) for row in plan['source_reports']}
    output, refs, reference, model_signatures = [], dict(plan['input_sha256']), None, []
    for case in plan['cases']:
        started = time.monotonic();arm_case(started)
        require(started < deadline, 'Common-cutoff total deadline exceeded')
        item = loader(Path(case['summary_path']))
        data = volume.load_native(item)
        mesh = item['summary']['mesh_metadata']
        require(mesh['h_xy_mm'] == .625 and mesh['sc_cells'] == 2 and
                mesh['bulk_layer_counts'] == [14, 14, 40] and item['circuit']['n_outputs'] == 2,
                'Fixed h0.625/SC2/two-output grid required')
        require(item['summary']['id'] == case['case_id'] and item['signature'] == case['own_comparison_signature'],
                'Loaded case/contact cohort differs')
        reference = require_same_geometry(reference, data)
        row = next(c for c in reports[case['source_report']]['cases'] if c['case_id'] == case['case_id'])
        scales = own_scales(case, row)
        raw = volume.weighted_statistics(data['arrays']['maxTIS'], data['regions'][REGIONS[1]])
        for stat in ('mean', 'p10'):
            saved = row['normalizations']['raw_1Vpp']['regions'][REGIONS[1]]['maxTIS'][stat]
            require(math.isclose(raw[stat], saved, rel_tol=1e-12, abs_tol=1e-14), 'Raw primary regression failed: '+stat)
        modes = {}
        for mode, scale in scales.items():
            regions = {}
            for name in REGIONS:
                require(time.monotonic() < deadline and time.monotonic()-started <= 60, 'Common-cutoff case/total deadline')
                require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 < 3*GIB, 'Common-cutoff RSS gate')
                regions[name] = summarize(data['arrays']['maxTIS'], data['regions'][name], scale,
                    plan['common_cutoffs_V_m'], volume)
                regions[name]['own_model_cutoff_volumes_from_existing_report'] = row['normalizations'][mode]['regions'][name]['maxTIS']['fixed_baseline_threshold_volume']
            modes[mode] = dict(amplitude_scale=scale, own_baseline_summary=case['own_baseline_summary'],
                own_active_caps=row['normalizations'][mode]['active_skin_contact_caps'], regions=regions)
        output.append(dict(case_id=case['case_id'], source_report=case['source_report'],
            summary_path=case['summary_path'], own_comparison_signature=item['signature'],
            own_model_cutoffs_V_m=row['fixed_same_grid_baseline_cutoffs_V_m']['maxTIS'],
            raw_primary_regression=dict(passed=True, relative=1e-12, absolute_V_m=1e-14), normalizations=modes))
        refs.update(data['refs']);model_signatures.append(item['signature'])
        del data
    require(model_signatures[0] == model_signatures[1] and model_signatures[2] == model_signatures[3] and
            model_signatures[0] != model_signatures[2], 'Two separate internally matched contact cohorts required')
    for path, digest in refs.items():
        require(sha(path) == digest, 'Consumed input changed: '+path)
    return dict(schema='task1-common-cutoff-audit-v1', status='calculated_unadopted', created_utc=now(),
        cases=output, common_cutoffs_V_m=plan['common_cutoffs_V_m'], threshold_source=CASE_IDS[0],
        all_grids_and_six_fractional_ROIs_byte_value_equal=True, inputs_sha256=refs, inputs_unchanged=True,
        new_PDE_solves=0, native_E_phi_read=False, cross_model_burden_normalization=False,
        feedback_id=plan['feedback_id'],source_comment_id=plan['source_comment_id'],source_comment_url=plan['source_comment_url'],
        limitations=plan['limitations'], interpretation='Field/normalization effects can be compared with fixed thresholds; own-cutoff versus common-cutoff volumes reveal threshold-shift effects separately. No ranking from ratios alone.',
        selected_for_adoption=[])


def _write(path, value, *, exclusive=False):
    if exclusive:
        with path.open('x') as stream:json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
    else:
        temporary = path.with_name(path.name+'.partial')
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n');temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preregistration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args();output=args.output.resolve();planpath=args.preregistration.resolve()
    runtime=output.with_suffix('.runtime.json');failure=output.with_suffix('.failure.json')
    require(output.is_relative_to(ROOT/'docs') and all(not p.exists() for p in (output,runtime,failure)),
            'Fresh docs output/runtime/failure paths required')
    implementation=committed_implementation()
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledgerpath=ROOT/'runtime/task1-budget.json';ledger=read(ledgerpath)
        require(ledger['limit_seconds']==6600 and math.isfinite(ledger['spent_seconds']) and 0<=ledger['spent_seconds']<6600,
                'Existing6600s budget invalid/exhausted')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});output.parent.mkdir(parents=True,exist_ok=True)
        require(shutil.disk_usage(output.parent).free>=2*GIB,'Preserve2GiB disk reserve')
        start=time.monotonic();seconds=min(180.,6600-ledger['spent_seconds']);status='failed';error_text=None
        owner=dict(pid=os.getpid(),proc_start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]))
        state=dict(schema='task1-common-cutoff-runtime-v1',status='running',owner=owner,started_utc=now(),
            implementation=implementation,preregistration=str(planpath),preregistration_sha256=sha(planpath))
        _write(runtime,state,exclusive=True)
        def timeout(signum,frame):raise TimeoutError('Common-cutoff180total/60case/remainingbudget deadline')
        signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,seconds)
        try:
            plan=read(planpath);verify_plan(plan)
            def arm_case(started):signal.setitimer(signal.ITIMER_REAL,max(.001,min(60.,start+seconds-started)))
            result=build_report(plan,start+seconds,arm_case)
            signal.setitimer(signal.ITIMER_REAL,max(.001,start+seconds-time.monotonic()))
            require(sha(planpath)==state['preregistration_sha256'],'Preregistration changed')
            verify_plan(plan);require(committed_implementation()==implementation,'Implementation changed')
            result.update(implementation=implementation,preregistration=state['preregistration_sha256'],
                resources=dict(seconds=time.monotonic()-start,total_limit_seconds=seconds,per_case_seconds=60,
                    CPU=1,RSS_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,disk_reserve_bytes=2*GIB))
            payload=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
            require(shutil.disk_usage(output.parent).free>=2*GIB+len(payload.encode()),'Output violates disk reserve')
            _write(output,result,exclusive=True);status=result['status']
        except BaseException as error:
            error_text=type(error).__name__+': '+str(error)
            _write(failure,dict(status='failed_preserved',error=error_text,owner=owner,observed_utc=now()),exclusive=True)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);elapsed=time.monotonic()-start
            ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.stem,stage='common_cutoff_audit',
                seconds=elapsed,status=status,failure_reason=error_text,finished_utc=now()));_write(ledgerpath,ledger)
            state.update(status=status,error=error_text,wall_seconds=elapsed,finished_utc=now(),worker_live=False,execution_was_started=True)
            _write(runtime,state)
    print(json.dumps(dict(status=status,output=str(output),new_PDE_solves=0)))


if __name__=='__main__':main()
