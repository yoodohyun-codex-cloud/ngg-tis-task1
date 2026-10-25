#!/usr/bin/env python3
"""Two finite unequal-output re-syntheses of one frozen eligible native basis.

No PDE, producer mutation, worker or candidate adoption. Research modules are
imported only inside the CLI's shared execution/resource lock after provenance
checks. The existing equal-drive condition is a cached comparator, not a new
calculation. Every new condition has an explicit two-output source-Vpp vector.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import importlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import numpy as np
import task1_results_view as view
import task1_candidate_ranking as ranking
import task1_volume_selectivity as volume
import task1_waveform_check as waveform

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
FREQUENCIES = (3000, 3030, 9000, 9090)
RATIOS = (('ratio-output0-0p5', [.5, 1.]), ('ratio-output0-2', [2., 1.]))
BASELINE_ID = 'baseline-square15-xy80'
BASELINE_RUN = 'cloud-mesh-c1-20261019T190000Z'
SCHEMA = 'task1-drive-ratio-audit-preregistration-v1'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def scaled_coefficients(base, source_Vpp_by_output):
    amplitudes = np.asarray(source_Vpp_by_output, float)
    require(amplitudes.shape == (2,) and np.isfinite(amplitudes).all() and np.all(amplitudes > 0),
        'Two finite positive physical-output Vpp values required')
    require(set(base) == set(FREQUENCIES), 'All four actual carrier/harmonic bases required')
    result = {}
    for frequency in FREQUENCIES:
        coefficient = np.asarray(base[frequency], complex)
        require(coefficient.shape == (2,) and np.isfinite(coefficient).all(), 'Finite two-output peak-basis coefficients required')
        result[frequency] = coefficient*amplitudes
    return result


def normalization_adapter(candidate, baseline, current_sum, baseline_current_sum, source_Vpp_by_output):
    declared = list(map(float, source_Vpp_by_output))
    require(len(declared) == 2 and all(math.isfinite(x) and x > 0 for x in declared), 'Explicit positive output Vpp vector required')
    result = volume.normalization_modes(candidate, baseline, current_sum, baseline_current_sum)
    result['raw_declared_Vpp'] = result.pop('raw_1Vpp')
    # Legacy composite's physical ceiling applies to EACH actual output.  The
    # reused helper assumes raw[1,1]; replace that assumption explicitly.
    composite = result['legacy_composite_full_skin']
    caps = {key:(baseline[key]/candidate[key])**(1/degree) if candidate[key] else math.inf
        for key,degree in volume.BURDENS.items()}
    corrected = min(1./max(declared), *caps.values())
    if corrected != composite['amplitude_scale']:
        composite = volume.normalization_modes(candidate, baseline, current_sum, baseline_current_sum)['raw_1Vpp']
        composite.update(amplitude_scale=corrected, normalized_burdens={key:candidate[key]*corrected**degree
            for key, degree in volume.BURDENS.items()}, sum_source_output_RMS_mA=current_sum*corrected,
            active_skin_contact_caps=[key for key,value in caps.items() if key != 'source_power_W'
                and math.isclose(value,corrected,rel_tol=1e-12,abs_tol=1e-15)],
            includes_source_power_cap=True, includes_1Vpp_ceiling=True)
        result['legacy_composite_full_skin'] = composite
    for name, mode in result.items():
        mode.pop('source_Vpp_per_output', None)
        mode['source_Vpp_by_output'] = [x*mode['amplitude_scale'] for x in declared]
        mode['raw_declared_source_Vpp_by_output'] = declared.copy()
        mode['may_require_more_than_1Vpp'] = max(mode['source_Vpp_by_output']) > 1.
        mode['1Vpp_ceiling_definition'] = 'each actual physical output <=1Vpp' if name == 'legacy_composite_full_skin' else 'no physical-output1Vpp ceiling'
    return result


def scaled_probe_rows(probe, scale):
    require(probe.get('status') == 'complete' and len(probe['measurements']) == 40
        and len({row['id'] for row in probe['measurements']}) == 40
        and math.isfinite(scale) and scale > 0, 'Complete40 unique unloaded probes and positive common amplitude scale required')
    return [dict(id=row['id'], RMS_V=row['RMS_V']*scale,
        Vpp_lower_V=row['Vpp_lower_V']*scale, Vpp_upper_V=row['Vpp_upper_V']*scale,
        fundamental_envelope_variation_V=row['fundamental_fixed_axis_envelope']['variation_range_V']*scale)
        for row in probe['measurements']]


def implementation_paths():
    return [Path(__file__).resolve(), Path(volume.__file__).resolve(), Path(waveform.__file__).resolve(),
        Path(view.__file__).resolve(), Path(ranking.__file__).resolve()]


def implementation_receipt():
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True,
        capture_output=True, text=True, timeout=5).stdout.strip()
    result = {}
    for path in implementation_paths():
        expected = subprocess.run(['git', 'show', commit+':'+path.relative_to(ROOT).as_posix()],
            cwd=ROOT, check=True, capture_output=True, timeout=5).stdout
        require(path.read_bytes() == expected, 'Implementation/helper differs from committed HEAD: '+str(path))
        result[str(path)] = view.sha(path)
    return dict(implementation_git_commit=commit, implementation_files_sha256=result)


def baseline_item(path):
    item = view.load_case(path)
    meta = item['summary']['mesh_metadata']
    require(item['summary']['id'] == BASELINE_ID and item['run'].name == BASELINE_RUN
        and item['circuit']['n_pads'] == 4 and item['circuit']['n_outputs'] == 2
        and meta['h_xy_mm'] == .625 and meta['sc_cells'] == 2 and meta['bulk_layer_counts'] == [14, 14, 40]
        and meta['cells'] == 351680, 'Only the exact eligible frozen four-pad h.625 SC2 baseline is registered')
    ranking.condition(item)
    return item


def make_preregistration(baseline_summary, output_directory):
    """Metadata/hash plan only; native E/phi hashes copied from completed source."""
    item = baseline_item(baseline_summary)
    case, summary, run = item['case'], item['summary'], item['run']
    refs = ranking.input_refs(item)
    refs.update(summary['input_sha256'])
    archive = item['path'].parent/'volume.npz'
    refs[str(archive)] = summary['artifacts']['files']['volume.npz']['SHA256']
    probes = item['path'].parent/summary['artifacts']['probes_json']
    refs[str(probes)] = summary['artifacts']['files'][probes.name]['SHA256']
    refs[str(Path(case['mask_file']))] = case['mask_sha256']
    manifest_path = run/'frozen-source-manifest.json'
    refs[str(manifest_path)] = view.sha(manifest_path)
    frozen_manifest = view.read(manifest_path)['files']
    resolved = {}
    for original, expected in item['registration']['source_and_input_sha256'].items():
        snapshot = frozen_manifest.get(original)
        chosen = ROOT/snapshot['path'] if snapshot else Path(original)
        require(chosen.is_file() and view.sha(chosen) == expected, 'Frozen original source/input missing: '+original)
        refs[str(chosen.resolve())] = expected
        resolved[original] = str(chosen.resolve())
    for path in implementation_paths():
        refs[str(path)] = view.sha(path)
    definition = ROOT/'docs/cloud-progress-20261021/volume-audit-plan.json'
    refs[str(definition)] = view.sha(definition)
    return dict(schema=SCHEMA, status='preregistered_not_executed', created_utc=datetime.now(timezone.utc).isoformat(),
        feedback_id='T1-F010-S1-GH6297472037', new_PDE_conditions=0,
        baseline_summary=str(item['path']), baseline_summary_sha256=view.sha(item['path']),
        output_directory=str(Path(output_directory).resolve()),
        conditions=[dict(id=ident, source_Vpp_by_output=values) for ident, values in RATIOS],
        cached_equal_drive_comparator=dict(source_Vpp_by_output=[1., 1.], new_condition=False),
        native_input_sha256=summary['input_sha256'], input_sha256=refs, frozen_source_resolution=resolved,
        frozen_definition_source=str(definition), frozen_definition_sha256=refs[str(definition)],
        resource_limits=dict(CPU_count=1, per_condition_seconds=180, total_seconds=420,
            overhead_seconds=60, RSS_bytes=3*GIB, disk_reserve_bytes=2*GIB, cumulative_budget_seconds=6600),
        holds=['Native source algebra/conservation and waveform checks are distinct from SC/XY/bulk/contact convergence',
            'No adoption, physiological equivalence, human safety, experimental or COMSOL claim',
            '40 differential probe results are unloaded; instrument loading/calibration remains held'],
        scope='Exactly two explicit unequal-output re-syntheses; no PDE; preserve source electrodes, commonGND and50ohm passive-frequency termination')


def verify_plan(path, baseline_summary, output_directory, expected_sha=None):
    path = Path(path).resolve()
    digest = view.sha(path)
    require(expected_sha is None or digest == expected_sha, 'Preregistration changed during audit')
    plan = view.read(path)
    require(plan['schema'] == SCHEMA and plan['status'] == 'preregistered_not_executed'
        and plan['new_PDE_conditions'] == 0
        and plan['conditions'] == [dict(id=i, source_Vpp_by_output=v) for i, v in RATIOS]
        and plan['baseline_summary'] == str(Path(baseline_summary).resolve())
        and plan['output_directory'] == str(Path(output_directory).resolve()), 'Exact registered source/condition order/output directory required')
    require(plan['input_sha256'].get(plan['baseline_summary']) == plan['baseline_summary_sha256'], 'Baseline summary digest missing')
    for input_path, expected in plan['input_sha256'].items():
        p = Path(input_path)
        require(p.is_absolute() and p == p.resolve() and p.is_relative_to(ROOT) and p.is_file()
            and not p.is_symlink() and view.sha(p) == expected, 'Preregistered input hash mismatch: '+input_path)
    require(view.read(baseline_summary)['input_sha256'] == plan['native_input_sha256'], 'Native source manifest differs')
    return plan, digest


def import_frozen(run, plan):
    folder = run/'frozen-source/tis-java'
    require(folder.is_dir(), 'Exact frozen research folder required; no historical absolute-path fallback')
    names = ('selectivity_postprocess', 'selectivity_volume', 'layered_probe_analysis', 'explore_tis', 'explore_inputs')
    require(not any(name in sys.modules for name in names), 'Research module cache already populated; use a fresh standalone process')
    sys.path.insert(0, str(folder))
    post = importlib.import_module('selectivity_postprocess')
    scalar = importlib.import_module('selectivity_volume')
    probe = importlib.import_module('layered_probe_analysis')
    for name in names:
        module = sys.modules.get(name)
        require(module is not None and Path(module.__file__).resolve().is_relative_to(folder)
            and str(Path(module.__file__).resolve()) in plan['input_sha256'], 'Unpinned research module lookup: '+name)
    return post, scalar, probe


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def derive_condition(basis, case, geometry, volume_meta, base_coefficients, declared, baseline,
                     baseline_cutoffs, weights, post, scalar, probe_module, output, deadline, source_digest):
    coefficients = scaled_coefficients(base_coefficients, declared['source_Vpp_by_output'])
    spectra = post._spectra(basis, coefficients)
    electrical = post._electrical(basis, coefficients, geometry, deadline)
    native_volume = scalar.evaluate_volume(spectra, basis['grid'], volume_meta,
        fundamental_frequencies_Hz=[3000, 3030], region_weights=weights,
        fibonacci_count=2048, chunk_cells=256, deadline_monotonic=deadline)
    require(time.monotonic() < deadline, 'Per-condition volume deadline exceeded')
    regions = volume.region_weights({**{k:native_volume['scalars'][k] for k in volume.METRICS},
        'maxTIS_direction_index':native_volume['scalars']['maxTIS_direction_index'],
        **{'region_'+k+'_m3':v for k, v in native_volume['region_weights_m3'].items()}}, basis['grid'], basis['metadata'])
    arrays = {k:native_volume['scalars'][k] for k in (*volume.METRICS, 'maxTIS_direction_index')}
    arrays.update({'region_'+key+'_m3':value for key,value in native_volume['region_weights_m3'].items()})
    np.savez_compressed(output/'volume.npz', **arrays)
    write_json(output/'native-volume-metrics.json', native_volume['metrics'])
    skin = waveform.bulk_skin_current_density(spectra, basis['grid'], geometry['gamma_S_m'])
    losses = waveform.layer_losses_from_matrices({f:row['loss'] for f,row in basis['f'].items()},
        {f:row['source'] for f,row in basis['f'].items()}, coefficients, electrical)
    fake_item = dict(circuit=baseline['item']['circuit'], full_skin={declared['id']:dict(
        J_vector_RMS_max_A_m2=skin['regions']['skin_SC_plus_dermis']['total']['J_vector_RMS_max_A_m2'],
        J_vector_RMS_p95_A_m2=skin['regions']['skin_SC_plus_dermis']['total']['J_vector_RMS_p95_A_m2'],
        skin_SC_plus_dermis_power_W=losses['metrics']['skin_SC_plus_dermis_power_W'])})
    candidate_burden, currents = volume.burdens(fake_item, dict(id=declared['id'], metrics=electrical))
    baseline_burden, baseline_currents = volume.burdens(baseline['item'], baseline['condition'])
    modes = normalization_adapter(candidate_burden, baseline_burden, sum(currents), sum(baseline_currents), declared['source_Vpp_by_output'])
    provenance = dict(source_run_id=baseline['item']['run'].name, source_condition_id=case['id'],
        source_candidate_id=case['id']+'-'+declared['id'], input_sha256=source_digest,
        code_sha256=view.sha(__file__), result_sha256=post._digest(basis['validation']))
    probes = probe_module.evaluate_layered_probe(basis['grid'],
        {f:row['potential'] for f,row in basis['f'].items()}, {f:row['field'] for f,row in basis['f'].items()},
        geometry, coefficients, provenance=provenance, fundamental_frequencies_Hz=[3000, 3030],
        plus_pitch_mm=5., tip_gap_mm=5., depths_mm=(5., 10., 15., 20.))
    probes['actual_source_Vpp_by_output'] = declared['source_Vpp_by_output']
    probes['drive_ratio_condition_id'] = declared['id']
    for row in probes['measurements']:
        row.pop('time_plot', None)
    write_json(output/'probes.json', probes)
    require(probes['status'] == 'complete' and probes['numerical_checks']['all_passed'], 'New native40-probe phi/E validation incomplete')
    probe_audit = waveform.probe_check(dict(id=declared['id'], probe40=probes))
    field_waveform_audit = waveform.field_check(dict(id=declared['id'], waveform='square_3h',
        actual_fundamental_Hz=[3000,3030],metrics=electrical))
    require(time.monotonic() < deadline, 'Per-condition waveform audit deadline exceeded')
    for mode in modes.values():
        mode['regions'] = volume.summarize_regions(native_volume['scalars'], regions, basis['grid'], mode['amplitude_scale'], baseline_cutoffs)
        mode['source_output_RMS_by_output_mA'] = [value*mode['amplitude_scale'] for value in currents]
        mode['probe40_unloaded'] = scaled_probe_rows(probes, mode['amplitude_scale'])
        mode['probe_scaling_scope'] = 'Exact common amplitude scaling of this new ratio native phasor/time predictions; no instrument loading'
        require(time.monotonic() < deadline, 'Per-condition normalized statistics deadline exceeded')
    result = dict(schema='task1-drive-ratio-condition-v1', status='calculated_unadopted', id=declared['id'],
        source_case_id=case['id'], source_candidate_id=provenance['source_candidate_id'],
        source_Vpp_by_output=declared['source_Vpp_by_output'], waveform='square_3h', frequencies_Hz=list(FREQUENCIES),
        coefficient_vectors={str(f):dict(real=c.real.tolist(), imaginary=c.imag.tolist()) for f,c in coefficients.items()},
        electrical_metrics=electrical, bulk_skin_J=skin, layer_contact_source_losses=losses,
        native_volume_metrics=native_volume['metrics'], normalizations=modes,
        fixed_same_grid_equal_drive_baseline_cutoffs_V_m=baseline_cutoffs,
        probe_waveform_audit=probe_audit, field_waveform_audit=field_waveform_audit,
        probe_artifact='probes.json', native_volume_artifact='volume.npz',
        sampled_direction_scope='2074 directions independently recomputed per native cell for this unequal drive; no continuous-direction or physiological proof',
        basis_source_normalization='Original each basis0.5Vpeak/1Vpp through50ohm remains unchanged; actual output vector recorded separately',
        raw_mode='raw_declared_Vpp', new_PDE=0, adopted=False, numerical_validation_promoted=False,
        experimental_validation=False, instrument_loaded_prediction=False)
    write_json(output/'condition.json', result)
    return dict(id=declared['id'], status=result['status'], source_Vpp_by_output=declared['source_Vpp_by_output'],
        artifacts={name:dict(path=str(output/name), SHA256=view.sha(output/name)) for name in
            ('condition.json', 'probes.json', 'volume.npz', 'native-volume-metrics.json')})


def execute(plan, baseline_summary, output, deadline):
    item = baseline_item(baseline_summary)
    cached = volume.load_native(item)
    c = cached['condition']
    cutoffs = {metric:{region+'_'+stat:volume.weighted_statistics(cached['arrays'][metric],cached['regions'][region])[stat]
        for region in (volume.PRIMARY, volume.SLAB) for stat in ('mean','p10')} for metric in volume.METRICS}
    post, scalar, probe = import_frozen(item['run'], plan)
    basis = post._load_basis(item['run']/'bases'/item['case']['id'], item['case'], min(deadline, time.monotonic()+60))
    require(basis['hashes'] == plan['native_input_sha256'], 'Loaded native basis SHA differs from source')
    geometry, volume_meta = post._geometry(basis, item['case'])
    require(np.array_equal(basis['grid'], cached['grid']), 'Cached baseline scalar grid differs from loaded basis')
    coeff = post._coefficients(2, 'square_3h')
    weights = {name:cached['arrays']['region_'+name+'_m3'] for name in
        ('total','target','surface_0_5','subsurface_5_10','remaining','off_target')}
    source_digest = post._digest(basis['hashes'])
    conditions = []
    for index, declared in enumerate(plan['conditions']):
        condition_deadline = min(deadline, time.monotonic()+180)
        signal.setitimer(signal.ITIMER_REAL, max(.001, condition_deadline-time.monotonic()))
        folder = output/declared['id'];folder.mkdir()
        write_json(output/f'checkpoint-{index+1:02d}-start.json', dict(phase='derived_condition', condition_id=declared['id'],
            started_utc=datetime.now(timezone.utc).isoformat(), source_Vpp_by_output=declared['source_Vpp_by_output']))
        conditions.append(derive_condition(basis,item['case'],geometry,volume_meta,coeff,declared,cached,
            cutoffs,weights,post,scalar,probe,folder,condition_deadline,source_digest))
        write_json(output/f'checkpoint-{index+1:02d}-complete.json', conditions[-1])
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 < 3*GIB, 'Existing3GiB RSS cap exceeded')
    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline-time.monotonic()))
    return dict(schema='task1-drive-ratio-audit-v1', status='calculated_unadopted', conditions=conditions,
        cached_baseline_summary=str(item['path']), cached_equal_drive_source_Vpp_by_output=[1.,1.],
        baseline_new_condition=False, new_PDE=0, new_conditions=2, adopted=False, selected_for_adoption=[],
        execution_scope='Finite native basis re-synthesis; no PDE/source edits/worker or convergence promotion',
        holds=plan['holds'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-summary', type=Path, required=True)
    parser.add_argument('--preregistration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT/'docs/cloud-continuation-20261021') and not output.exists(), 'Unique new continuation output directory required')
    implementation = implementation_receipt()
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path = ROOT/'runtime/task1-budget.json';ledger=view.read(ledger_path)
        require(ledger['limit_seconds']==6600 and 6600-ledger['spent_seconds'] >= 420,
            'Admission requires full finite420s reservation within unchanged6600s budget')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        output.parent.mkdir(parents=True,exist_ok=True)
        require(shutil.disk_usage(output.parent).free >= 2*GIB+256*1024**2, 'Preserve2GiB reserve plus256MiB bounded artifacts')
        output.mkdir();start=time.monotonic();deadline=start+420;status='failed_preserved';error=None
        def expired(signum,frame):raise TimeoutError('Finite180s condition/420s batch deadline expired')
        signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,60)
        write_json(output/'checkpoint-admitted.json',dict(status='running',started_utc=datetime.now(timezone.utc).isoformat(),
            PID=os.getpid(),total_budget_seconds=420,per_condition_seconds=180,new_PDE=0,**implementation))
        try:
            plan,plan_sha=verify_plan(args.preregistration,args.baseline_summary,output)
            result=execute(plan,args.baseline_summary,output,deadline)
            verify_plan(args.preregistration,args.baseline_summary,output,expected_sha=plan_sha)
            require(implementation_receipt()==implementation,'Implementation changed during execution')
            result.update(implementation,preregistration=dict(path=str(args.preregistration.resolve()),SHA256=plan_sha),
                input_sha256=plan['input_sha256'],inputs_unchanged=True,
                resources=dict(wall_seconds=time.monotonic()-start,CPU_count=1,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
            write_json(output/'summary.json',result);status=result['status']
        except BaseException as exc:
            error=type(exc).__name__+': '+str(exc)
            write_json(output/'failure.json',dict(status=status,error=error,finished_utc=datetime.now(timezone.utc).isoformat(),
                partial_artifacts_preserved=True,new_PDE=0,**implementation))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);elapsed=time.monotonic()-start
            ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='drive_ratio_native_recomposition',seconds=elapsed,
                status=status,failure_reason=error,finished_utc=datetime.now(timezone.utc).isoformat()))
            tmp=ledger_path.with_suffix('.json.partial');tmp.write_text(json.dumps(ledger,indent=2)+'\n');tmp.replace(ledger_path)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__ == '__main__':main()
