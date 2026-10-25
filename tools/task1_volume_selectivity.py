#!/usr/bin/env python3
"""Source-bound cached native-cell volume audit; no PDE or field reconstruction.

The original central ROI remains primary. Whole model XY at depth15--20mm is
a separately named supplement, never a replacement ROI or adoption criterion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import gzip
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time
import zipfile

try:
    from task1_resource_policy import effective_limit
except ModuleNotFoundError as error:
    if error.name != 'task1_resource_policy':
        raise
    from tools.task1_resource_policy import effective_limit

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import numpy as np
import task1_results_view as view
import task1_candidate_ranking as ranking

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
MAX_CASES = 12
METRICS = ('maxTIS', 'fixedTIS', 'RMS')
PRIMARY = 'primary_r5_depth15_20'
SLAB = 'supplemental_wholeXY_depth15_20'
BURDENS = {**{key: degree for key, (degree, _) in view.CAPS.items()},
    'bulk_skin_J_vector_RMS_max_A_m2': 1,
    'bulk_skin_J_vector_RMS_p95_A_m2': 1,
    'skin_SC_plus_dermis_power_W': 2}
LAYER_NAMES = ('stratum_corneum', 'dermis', 'fat', 'muscle')


def weighted_statistics(values, weights):
    """Frozen inverse weighted ECDF (side=left), augmented with P90/std/CV."""
    v, w = np.asarray(values, float), np.asarray(weights, float)
    if (v.ndim != 1 or v.shape != w.shape or not np.isfinite(v).all()
            or not np.isfinite(w).all() or np.any(w < 0) or not np.any(w > 0)):
        raise ValueError('Finite equal-shaped scalar values and positive represented volume required')
    use = w > 0
    v, w = v[use], w[use]
    order = np.argsort(v, kind='stable')
    cumulative = np.cumsum(w[order])
    mean = float(v@w/w.sum())
    std = float(np.sqrt(((v-mean)**2)@w/w.sum()))
    result = dict(min=float(v.min()), max=float(v.max()), mean=mean,
        volume_m3=float(w.sum()), positive_weight_cells=int(use.sum()), std=std,
        CV=std/mean if mean else None,
        maximum_scope='native cell-constant represented samples; not continuum maximum')
    for key, fraction in (('p10', .1), ('p50', .5), ('p90', .9), ('p95', .95), ('p99', .99)):
        index = min(int(np.searchsorted(cumulative, fraction*cumulative[-1], side='left')), len(v)-1)
        result[key] = float(v[order[index]])
    result['p10_over_mean'] = result['p10']/mean if mean else None
    return result


def region_weights(arrays, grid, meta):
    total, target, surface = (np.asarray(arrays['region_'+name+'_m3'], float)
        for name in ('total', 'target', 'surface_0_5'))
    n = len(total)
    if (n == 0 or n > 800_000 or n != meta['cells'] or any(a.shape != (n,) for a in arrays.values())
            or len(grid) != n or not all(np.isfinite(a).all() for a in arrays.values())):
        raise ValueError('Finite complete native scalar arrays with common bounded cell count required')
    if any(np.any(a < 0) for a in arrays.values()):
        raise ValueError('Native scalar magnitudes and weights must be nonnegative')
    faces = np.asarray(meta['z_faces_mm'], float)
    z = np.asarray(grid['z_mm'], float)
    boundaries = np.asarray(meta['tissue_boundaries_mm'], float)
    x, y = np.asarray(grid['x_mm'], float), np.asarray(grid['y_mm'], float)
    if (boundaries.shape != (5,) or not np.allclose(boundaries,
            [0., .1, 5.1, 10.1, 25.1], rtol=0, atol=1e-12)
            or not np.isfinite(x).all() or not np.isfinite(y).all()
            or not np.isfinite(z).all() or np.any(x*x+y*y >= 625.)
            or np.any(z < boundaries[0]) or np.any(z >= boundaries[-1])
            or not np.array_equal(grid['layer'], np.searchsorted(boundaries[1:-1], z, side='right'))):
        raise ValueError('Native centers/layers must match fixed D50 tissue depth boundaries')
    centers = (faces[1:]+faces[:-1])/2
    levels = np.unique(z)
    if (faces.ndim != 1 or not np.isfinite(faces).all() or np.any(np.diff(faces) <= 0)
            or len(levels) != len(centers) or not np.allclose(levels, centers, rtol=0, atol=1e-9)):
        raise ValueError('Native grid depth centers must match actual ordered z faces')
    iz = np.searchsorted(levels, z)
    dz = np.diff(faces)[iz]
    exact_total = float(meta['h_xy_mm'])**2*dz*1e-9
    if not np.allclose(total, exact_total, rtol=1e-13, atol=1e-25):
        raise ValueError('Saved total weights must equal full-precision native h^2 dz')
    if not np.allclose(np.asarray(grid['volume_m3']), total, rtol=2e-10, atol=1e-25):
        raise ValueError('Printed CSV volumes disagree with saved native total weights')
    if (np.any(total <= 0) or np.any(target > total*(1+1e-13))
            or np.any(surface > total*(1+1e-13))
            or not np.allclose(arrays['region_off_target_m3'], total-target, rtol=1e-13, atol=1e-25)):
        raise ValueError('Invalid saved fractional ROI or complement weights')
    overlap = np.maximum(0., np.minimum(faces[iz+1], 20.)-np.maximum(faces[iz], 15.))
    slab = total*overlap/dz
    return {'total': total, PRIMARY: target, SLAB: slab, 'surface_0_5': surface,
        'primary_complement': np.maximum(0., total-target),
        'supplemental_complement': np.maximum(0., total-slab)}


def burdens(item, condition):
    metrics, skin = condition['metrics'], item['full_skin'].get(condition['id'])
    if skin is None:
        raise ValueError('Source-bound completed bulk-skin current/loss audit required')
    result = {key: float(metrics[key]) for key in view.CAPS}
    result.update(bulk_skin_J_vector_RMS_max_A_m2=float(skin['J_vector_RMS_max_A_m2']),
        bulk_skin_J_vector_RMS_p95_A_m2=float(skin['J_vector_RMS_p95_A_m2']),
        skin_SC_plus_dermis_power_W=float(skin['skin_SC_plus_dermis_power_W']))
    currents = list(map(float, metrics['source_current_RMS_by_output_mA']))
    if (len(currents) != item['circuit']['n_outputs'] or len(currents) != 2
            or not all(math.isfinite(x) and x >= 0 for x in [*result.values(), *currents])
            or sum(currents) <= 0 or result['source_power_W'] <= 0):
        raise ValueError('Finite nonnegative nine burdens and positive two-output RMS sum/power required')
    return result, currents


def normalization_modes(candidate, baseline, current_sum, baseline_current_sum):
    caps = {}
    for key, degree in BURDENS.items():
        value, limit = candidate[key], baseline[key]
        caps[key] = (limit/value)**(1/degree) if value else math.inf
    skin_caps = {key: value for key, value in caps.items() if key != 'source_power_W'}
    skin_scale = min(skin_caps.values())
    if not math.isfinite(skin_scale) or skin_scale <= 0:
        raise ValueError('Positive finite skin/contact normalization requires nonzero burdens')
    scales = {'raw_1Vpp': 1.,
        'equal_total_source_output_RMS_sum': baseline_current_sum/current_sum,
        'equal_total_power': caps['source_power_W'],
        'skin_contact_only': skin_scale,
        'legacy_composite_full_skin': min(1., *caps.values())}
    return {name: dict(amplitude_scale=float(scale), source_Vpp_per_output=float(scale),
        baseline_derived_numerical_limits=baseline,
        normalized_burdens={key: candidate[key]*scale**degree for key, degree in BURDENS.items()},
        sum_source_output_RMS_mA=current_sum*scale,
        active_skin_contact_caps=[key for key, value in skin_caps.items()
            if math.isclose(scale, value, rel_tol=1e-12, abs_tol=1e-15)],
        includes_source_power_cap=name == 'legacy_composite_full_skin',
        includes_1Vpp_ceiling=name == 'legacy_composite_full_skin',
        may_require_more_than_1Vpp=scale > 1.,
        interpretation='numerical normalization only; baseline limits are not human safety limits')
        for name, scale in scales.items()}


def hotspot(values, weights, grid):
    use = weights > 0
    maximum = np.max(values[use])
    indices = np.flatnonzero(use & (values == maximum))
    index = int(indices[0])
    layer = int(grid['layer'][index])
    if layer not in range(4):
        raise ValueError('Unknown native tissue layer')
    return dict(native_cell_index=index,
        center_xyz_mm=[float(grid[name][index]) for name in ('x_mm', 'y_mm', 'z_mm')],
        layer_index=layer, layer=LAYER_NAMES[layer], tied_native_cell_count=len(indices),
        position_scope='center of a cell with positive fractional region overlap; may lie outside ROI boundary')


def summarize_regions(arrays, regions, grid, scale, cutoffs):
    result = {}
    for region, weights in regions.items():
        result[region] = {}
        for metric in METRICS:
            # Scaling precedes classification; aggregate high-volume numbers cannot be scaled.
            values = arrays[metric]*scale
            stats = weighted_statistics(values, weights)
            stats['hotspot'] = hotspot(values, weights, grid)
            stats['fixed_baseline_threshold_volume'] = {name: dict(cutoff_V_m=cutoff,
                volume_m3=float(weights[values >= cutoff].sum()),
                region_volume_fraction=float(weights[values >= cutoff].sum()/weights.sum()),
                comparison='scaled native scalar >= frozen raw same-grid baseline cutoff',
                quantity='high_field_RMS' if metric == 'RMS' else 'high_fundamental_TIS_modulation',
                interpretation='electrical numerical comparison; not biological activation or safety')
                for name, cutoff in cutoffs[metric].items()}
            result[region][metric] = stats
    return result


def load_native(item):
    c = ranking.condition(item)
    archive_name = c['native_volume_archive']
    if Path(archive_name).name != archive_name or archive_name != 'volume.npz':
        raise ValueError('Require explicit primary native volume.npz artifact')
    archive = item['path'].parent/archive_name
    expected = item['summary']['artifacts']['files'][archive_name]['SHA256']
    paths = item['summary']['input_sha256']
    def source_path(basenames):
        found = [Path(path) for path in paths if Path(path).name in basenames]
        if len(found) != 1:
            raise ValueError('One registered native source required: '+str(basenames))
        path = found[0]
        if view.sha(path) != paths[str(path)]:
            raise ValueError('Native grid/metadata input hash mismatch')
        return path
    grid_path = source_path({'grid.csv', 'grid.csv.gz'})
    meta_path = source_path({'mesh-metadata.json'})
    refs = ranking.input_refs(item)
    refs.update({str(grid_path): view.sha(grid_path), str(meta_path): view.sha(meta_path)})
    probe_path = item['path'].parent/item['summary']['artifacts']['probes_json']
    refs[str(probe_path)] = item['summary']['artifacts']['files'][probe_path.name]['SHA256']
    if view.sha(archive) != expected:
        raise ValueError('Cached scalar archive SHA mismatch')
    refs[str(archive)] = expected
    meta = view.read(meta_path)
    if meta != item['summary']['mesh_metadata']:
        raise ValueError('Native metadata differs from saved postprocess metadata')
    with zipfile.ZipFile(archive) as z:
        if sum(entry.file_size for entry in z.infolist()) > GIB:
            raise ValueError('Scalar archive exceeds finite memory allocation')
    with np.load(archive, allow_pickle=False) as z:
        arrays = {name: z[name] for name in z.files}
    needed = {*METRICS, 'maxTIS_direction_index', *('region_'+name+'_m3' for name in
        ('total', 'target', 'surface_0_5', 'subsurface_5_10', 'remaining', 'off_target'))}
    if set(arrays) != needed:
        raise ValueError('Require known complete native scalar archive schema')
    opener = gzip.open if grid_path.suffix == '.gz' else open
    with opener(grid_path, 'rt') as stream:
        grid = np.genfromtxt(stream, delimiter=',', names=True)
    grid = np.atleast_1d(grid)
    if grid.dtype.names != ('x_mm', 'y_mm', 'z_mm', 'layer', 'volume_m3'):
        raise ValueError('Native grid columns changed')
    if not all(np.isfinite(grid[name]).all() for name in grid.dtype.names):
        raise ValueError('Nonfinite native coordinates')
    regions = region_weights(arrays, grid, meta)
    reproduced = {}
    for metric in METRICS:
        stats = weighted_statistics(arrays[metric], regions[PRIMARY])
        saved = c['volume_metrics']['regions']['target']['statistics'][metric]
        verify_primary_statistics(stats, saved, metric)
        reproduced[metric] = dict(mean=stats['mean'], p10=stats['p10'], passed=True)
    return dict(item=item, condition=c, arrays=arrays, grid=grid, regions=regions,
        refs=refs, reproduced=reproduced)


def verify_primary_statistics(stats, saved, metric):
    for key in ('mean', 'p10', 'p50', 'p95', 'min', 'max', 'volume_m3'):
        absolute = 1e-25 if key == 'volume_m3' else 1e-12
        if not math.isclose(stats[key], saved[key], rel_tol=1e-10, abs_tol=absolute):
            raise ValueError(f'Original primary ROI cached statistic mismatch: {metric}/{key}')


def analytic_volumes(meta):
    radius, depth = float(meta['radius_mm']), float(meta['total_depth_mm'])
    if radius != 25. or not math.isclose(depth, 25.1, abs_tol=1e-12):
        raise ValueError('Fixed D50/layer-depth25.1mm phantom required')
    total = math.pi*radius**2*depth*1e-9
    primary, slab = math.pi*5**2*5*1e-9, math.pi*radius**2*5*1e-9
    return {'total': total, PRIMARY: primary, SLAB: slab, 'surface_0_5': slab,
        'primary_complement': total-primary, 'supplemental_complement': total-slab}


def build_report(baseline_paths, summary_paths, *, loader=None, native_loader=None,
                 deadline=None, per_case_seconds=180., arm_case=None):
    loader, native_loader = loader or view.load_case, native_loader or load_native
    baseline_paths = list(dict.fromkeys(Path(p).resolve() for p in baseline_paths))
    summary_paths = [Path(p).resolve() for p in summary_paths]
    if (not baseline_paths or not summary_paths or len(baseline_paths) > MAX_CASES
            or len(summary_paths) > MAX_CASES or len(set(summary_paths)) != len(summary_paths)):
        raise ValueError('Require 1..12 unique summaries and explicit 1..12 same-grid baselines')
    cache, refs, baselines = {}, {}, {}
    def load(path):
        if path not in cache:
            started = time.monotonic()
            if arm_case is not None:
                arm_case(started)
            if deadline is not None and started >= deadline:
                raise TimeoutError('Finite batch deadline exceeded')
            item = loader(path)
            data = native_loader(item)
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 >= 3*GIB:
                raise MemoryError('Cached data exceeded existing3GiB RSS budget')
            if time.monotonic()-started > per_case_seconds:
                raise TimeoutError('Per-case180s cached audit deadline exceeded')
            cache[path] = data
            refs.update(data['refs'])
        return cache[path]
    for path in baseline_paths:
        data = load(path)
        item = data['item']
        if not ranking.baseline_identity(item):
            raise ValueError('Original 4-pad baseline required')
        if item['signature'] in baselines:
            raise ValueError('Ambiguous baselines for same comparison signature')
        baselines[item['signature']] = data
    cases = []
    for path in summary_paths:
        started = time.monotonic()
        if arm_case is not None:
            arm_case(started)
        data = load(path)
        item, c = data['item'], data['condition']
        if item['signature'] not in baselines:
            raise ValueError('Explicit matching grid/material/contact/ROI baseline missing')
        base = baselines[item['signature']]
        candidate_burden, currents = burdens(item, c)
        baseline_burden, baseline_currents = burdens(base['item'], base['condition'])
        modes = normalization_modes(candidate_burden, baseline_burden, sum(currents), sum(baseline_currents))
        cutoffs = {metric: {region+'_'+stat: weighted_statistics(base['arrays'][metric],
            base['regions'][region])[stat] for region in (PRIMARY, SLAB) for stat in ('mean', 'p10')}
            for metric in METRICS}
        analytic = analytic_volumes(item['summary']['mesh_metadata'])
        for mode in modes.values():
            mode['source_output_RMS_by_output_mA'] = [x*mode['amplitude_scale'] for x in currents]
            mode['regions'] = summarize_regions(data['arrays'], data['regions'], data['grid'],
                mode['amplitude_scale'], cutoffs)
            if (time.monotonic()-started > per_case_seconds
                    or (deadline is not None and time.monotonic() >= deadline)):
                raise TimeoutError('Finite per-case/batch scalar audit deadline exceeded')
        cases.append(dict(case_id=item['summary']['id'], design_id=item['case'].get('design_id'),
            run_id=item['run'].name, summary_path=str(item['path']),
            comparison_signature=item['signature'], baseline_summary=str(base['item']['path']),
            condition_id=c['id'], circuit=item['circuit'], source_commit=item['registration']['source_commit'],
            configuration_sha256=item['summary']['mesh_metadata']['config_sha256'],
            physical_model_version=item['physical_model_version'],
            mesh=item['summary']['mesh_metadata'], primary_ROI_reproduction=data['reproduced'],
            fixed_same_grid_baseline_cutoffs_V_m=cutoffs,
            represented_geometry={region: dict(represented_volume_m3=float(weights.sum()),
                analytic_ideal_volume_m3=analytic[region],
                represented_minus_analytic_percent=100*(float(weights.sum())/analytic[region]-1))
                for region, weights in data['regions'].items()}, normalizations=modes,
            raw_probe_artifact_reference=dict(path=str(item['path'].parent/item['summary']['artifacts']['probes_json']),
                SHA256=item['summary']['artifacts']['files'][item['summary']['artifacts']['probes_json']]['SHA256'],
                scope='raw unloaded probe predictions only; no newly reconstructed or loaded Vpp'),
            C1_comparison='separate existing report, unchanged; no new equivalence claim',
            adopted=False, calculation_status='cached_native_scalar_audit_complete',
            numerical_validation_status='primary_statistics_reproduced_only; mesh/convergence gates unchanged',
            experimental_validation_status='not_established'))
    for path, expected in refs.items():
        if view.sha(path) != expected:
            raise ValueError('Input changed during cached scalar audit: '+path)
    return dict(schema='task1-volume-selectivity-v1', status='calculated_unadopted',
        feedback_id='6297472037', created_utc=datetime.now(timezone.utc).isoformat(),
        new_PDE_solves=0, selected_for_adoption=[], source_sha256=view.sha(__file__),
        inputs_sha256=refs, inputs_unchanged=True,
        scope=dict(primary_ROI='central r<=5mm, depth15..20mm unchanged',
            supplemental_ROI='whole native modeled XY cross-section, depth15..20mm; separately reported',
            coordinates='x,y horizontal; z positive depth from top, all positions mm',
            weights='saved fractional primary ROI and h^2 dz native full-cell volume; exact face-clipped slab',
            whole_XY_geometry='center-in-disk FVM square cells; staircase wall, not exact cylinder clipping; no volume renormalization',
            quantiles='stable inverse volume-weighted ECDF, searchsorted side=left; native cell steps/ties retained; no interpolation',
            metrics=dict(maxTIS='fundamentals only, maximum over2074 sampled directions; lower bound to continuous direction maximum',
                fixedTIS='fundamentals only along (1/sqrt(2),1/sqrt(2),0)',
                RMS='total vector electric-field RMS including all4 stored square_3h spectral lines; not modulation'),
            omitted='X/Y/Z directional scalar fields not cached; sine/triangle RMS not available in this archive',
            current_sum='sum of each physical output RMS including all harmonics/passive-frequency currents; bookkeeping, not common-GND return current',
            skin_contact_only='eight skin/contact burden caps, no source-power cap and no1Vpp ceiling; may exceed1Vpp numerically',
            legacy_composite_full_skin='same eight caps plus source-power cap and1Vpp ceiling',
            equal_current_and_power='no1Vpp ceiling; only named denominator is equalized',
            limits='frozen raw same-grid baseline numerical burdens and scalar cutoffs; not human safety/activation limits'),
        cases=cases)


def committed_implementation():
    """Reject edited/uncommitted implementation before consuming research data."""
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True,
        capture_output=True, text=True, timeout=5).stdout.strip()
    committed = subprocess.run(['git', 'show', commit+':tools/task1_volume_selectivity.py'],
        cwd=ROOT, check=True, capture_output=True, timeout=5).stdout
    if Path(__file__).read_bytes() != committed:
        raise ValueError('Implementation bytes must match committed HEAD before audit')
    return dict(implementation_git_commit=commit, implementation_file=str(Path(__file__).resolve()),
        implementation_file_SHA256=view.sha(__file__))


def verify_preregistration(path, baseline_paths, summary_paths, *, expected_plan_sha=None,
                           consumed_refs=None):
    """Verify ordered plan and consumed hashes, without reading unused E/phi files."""
    path = Path(path).resolve()
    plan_sha = view.sha(path)
    if expected_plan_sha is not None and plan_sha != expected_plan_sha:
        raise ValueError('Preregistration changed during audit')
    plan = view.read(path)
    if (plan.get('schema') != 'task1-volume-selectivity-audit-preregistration-v1'
            or plan.get('status') != 'preregistered_not_executed'
            or plan.get('feedback_id') != 'T1-F010-S1-GH6297472037'
            or plan.get('source_comment_id') != 6297472037
            or plan.get('new_PDE_conditions') != 0):
        raise ValueError('Expected preregistered cached audit schema and stable feedback source')
    cases = plan['cases']
    declared = [Path(case['summary']).resolve() for case in cases]
    actual = [Path(p).resolve() for p in summary_paths]
    baselines = ([Path(p).resolve() for p in plan['baseline_summary_paths']]
        if 'baseline_summary_paths' in plan else
        [Path(case['summary']).resolve() for case in cases if case['case_id'] == plan['baseline_case_id']])
    if (not cases or len(cases) > MAX_CASES or len(cases) != plan['initial_case_count']
            or len(set(declared)) != len(declared) or declared != actual
            or baselines != [Path(p).resolve() for p in baseline_paths] or not baselines
            or len(set(baselines)) != len(baselines) or any(p not in declared for p in baselines)):
        raise ValueError('Summary order/case count/baseline does not match preregistration exactly')
    refs = {str(Path(p).resolve()): digest for p, digest in plan['input_sha256'].items()}
    if not refs:
        raise ValueError('Preregistered input SHA references required')
    native_declared_not_read = []
    for case in cases:
        for field, digest_field in (('summary', 'summary_sha256'), ('volume_npz', 'volume_npz_sha256')):
            if refs.get(str(Path(case[field]).resolve())) != case[digest_field]:
                raise ValueError('Case artifact does not match preregistered input SHA')
        for field in ('registration', 'case_receipt'):
            if str(Path(case[field]).resolve()) not in refs:
                raise ValueError('Case registration/receipt missing from preregistered hashes')
        summary = view.read(case['summary'])
        for native_path, digest in case['native_expected_input_sha256'].items():
            if summary['input_sha256'].get(native_path) != digest:
                raise ValueError('Declared native provenance differs from preregistered source summary')
            resolved = str(Path(native_path).resolve())
            if (Path(native_path).name in ('grid.csv', 'grid.csv.gz', 'mesh-metadata.json')
                    or resolved in (consumed_refs or {})):
                if resolved in refs and refs[resolved] != digest:
                    raise ValueError('Inconsistent preregistered native input digest')
                refs[resolved] = digest
            else:
                native_declared_not_read.append(resolved)
    for input_path, digest in refs.items():
        if view.sha(input_path) != digest:
            raise ValueError('Preregistered input hash mismatch: '+input_path)
    for input_path, digest in (consumed_refs or {}).items():
        if input_path in refs and refs[input_path] != digest:
            raise ValueError('Consumed input differs from preregistered digest')
    return dict(plan=plan, SHA256=plan_sha, input_sha256=refs,
        native_hash_scope='all plan input_sha256 plus consumed native grid/metadata; unused field/potential bytes not read',
        declared_native_inputs_not_byte_rehashed=sorted(set(native_declared_not_read)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, action='append', required=True)
    parser.add_argument('--baseline-summary', type=Path, action='append', required=True)
    parser.add_argument('--preregistration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Never overwrite volume audit evidence')
    implementation = committed_implementation()
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger_path = ROOT/'runtime/task1-budget.json'
        ledger = view.read(ledger_path)
        global_limit = effective_limit(ledger)
        if ledger['spent_seconds'] >= global_limit:
            raise ValueError('Validated cumulative budget exhausted; no allocation left')
        seconds = min(600., global_limit-ledger['spent_seconds'])
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        output.parent.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(output.parent).free < 2*GIB:
            raise ValueError('Preserve existing2GiB disk reserve')
        start, status, failure_reason = time.monotonic(), 'failed', None
        def timeout(signum, frame):
            raise TimeoutError(f'Finite600s/remaining{global_limit}s cached volume-audit deadline exceeded')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        try:
            prereg = verify_preregistration(args.preregistration, args.baseline_summary, args.summary)
            def arm_case(case_started):
                signal.setitimer(signal.ITIMER_REAL, max(.001, min(180., start+seconds-case_started)))
            result = build_report(args.baseline_summary, args.summary, deadline=start+seconds, arm_case=arm_case)
            final_prereg = verify_preregistration(args.preregistration, args.baseline_summary, args.summary,
                expected_plan_sha=prereg['SHA256'], consumed_refs=result['inputs_sha256'])
            if committed_implementation() != implementation:
                raise ValueError('Committed implementation changed during audit')
            result.update(implementation)
            result['feedback_id'] = prereg['plan']['feedback_id']
            result['source_comment_id'] = prereg['plan']['source_comment_id']
            result['source_comment_url'] = prereg['plan']['source_comment_url']
            result['preregistration'] = dict(path=str(args.preregistration.resolve()), SHA256=prereg['SHA256'],
                verified_before_and_after=True, native_hash_scope=final_prereg['native_hash_scope'],
                declared_native_inputs_not_byte_rehashed=final_prereg['declared_native_inputs_not_byte_rehashed'])
            result['inputs_sha256'].update(final_prereg['input_sha256'])
            result['inputs_sha256'][str(args.preregistration.resolve())] = prereg['SHA256']
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            if peak >= 3*GIB:
                raise MemoryError('Exceeded existing3GiB RSS budget')
            result['resources'] = dict(wall_seconds=time.monotonic()-start, max_batch_seconds=seconds,
                max_case_seconds=180, CPU_count=1, simultaneous_jobs=1, peak_process_RSS_bytes=peak,
                disk_reserve_bytes=2*GIB, global_limit_seconds=global_limit)
            payload = json.dumps(result, indent=2, allow_nan=False)+'\n'
            if shutil.disk_usage(output.parent).free < 2*GIB+len(payload.encode()):
                raise ValueError('Output would violate2GiB reserve')
            with output.open('x') as stream:
                stream.write(payload)
            status = result['status']
            print(json.dumps(dict(status=status, output=str(output), cases=len(result['cases']), new_PDE_solves=0)))
        except BaseException as exc:
            failure_reason = type(exc).__name__+': '+str(exc)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-start
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id='cached-volume-selectivity', stage='volume_selectivity',
                seconds=elapsed, status=status, failure_reason=failure_reason,
                finished_utc=datetime.now(timezone.utc).isoformat()))
            temporary = ledger_path.with_name('task1-budget.json.partial')
            temporary.write_text(json.dumps(ledger, indent=2)+'\n')
            temporary.replace(ledger_path)


if __name__ == '__main__':
    main()
