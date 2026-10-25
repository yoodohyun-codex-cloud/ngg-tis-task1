#!/usr/bin/env python3
"""Render saved scalar native cells; no E/phi, solver, normalization or scoring.

The caller owns serialized execution and budget accounting. Only terminal,
SHA-bound results on the identical original square grid are accepted.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import math
import subprocess
from pathlib import Path
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
METRICS = ('maxTIS', 'fixedTIS', 'RMS')
MODES = ('raw_1Vpp', 'skin_contact_only')
COHORT = 'cached_original_square_3000_3030_caps'
PAIRS = ((1000, 1030), (2000, 2030), (3000, 3030), (5000, 5030), (9000, 9030))
SCHEMAS = {'task1-frequency-resynthesis-audit-v1', 'task1-lower-carrier-recovery-result-v1',
           'task1-mid-high-carrier-result-v1'}
CAPS = {'surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2', 'contact_voltage_RMS_max_V',
        'SC_power_W', 'contact_power_W', 'bulk_skin_J_vector_RMS_max_A_m2',
        'bulk_skin_J_vector_RMS_p95_A_m2', 'skin_SC_plus_dermis_power_W'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def verify_pins(pins):
    for path, digest in pins.items():
        require(Path(path).is_file() and sha(path) == digest, 'Input SHA changed: '+str(path))


def bound_json(path, pins, expected=None):
    path = Path(path).resolve()
    require(path.suffix == '.json' and path.stat().st_size <= 24*1024**2, 'Bounded JSON required')
    digest = sha(path)
    require(expected is None or digest == expected, 'JSON artifact SHA mismatch: '+str(path))
    value = json.loads(path.read_text())
    require(sha(path) == digest, 'JSON changed while reading')
    pins[str(path)] = digest
    return value


def load_scalars(path, expected_sha, cells):
    """Read only the three saved scalars and frozen fractional region weights."""
    path = Path(path)
    require(0 < cells <= 800000 and path.stat().st_size <= 96*1024**2, 'Bounded native scalar archive required')
    require(sha(path) == expected_sha, 'Scalar NPZ SHA mismatch')
    wanted = METRICS + ('region_total_m3', 'region_target_m3', 'region_surface_0_5_m3')
    out = {}
    with np.load(path, allow_pickle=False) as archive:
        for name in wanted:
            a = archive[name]
            require(a.shape == (cells,) and a.dtype.kind == 'f' and np.all(np.isfinite(a)) and np.all(a >= 0),
                    'Invalid native scalar/region array: '+name)
            out[name] = a.copy()
    require(np.all(out['region_total_m3'] > 0) and
            np.all(out['region_target_m3'] <= out['region_total_m3']) and
            np.all(out['region_surface_0_5_m3'] <= out['region_total_m3']), 'Invalid fractional native weights')
    require(sha(path) == expected_sha, 'Scalar NPZ changed while reading')
    return out


def native_slices(grid, meta, values, xy_depth_mm=17.5):
    """Return unchanged native cell slices with exact cell faces and actual coordinates."""
    grid = np.asarray(grid, dtype=float)
    values = np.asarray(values, dtype=float)
    require(grid.ndim == 2 and grid.shape[1] >= 3 and len(grid) == len(values) == meta['cells'] and
            np.all(np.isfinite(grid)) and values.shape == (len(grid),) and np.all(np.isfinite(values)),
            'Finite cell-aligned grid and scalar required')
    x, y, z = (np.unique(grid[:, k]) for k in range(3))
    h = float(meta['h_xy_mm']); zfaces = np.asarray(meta['z_faces_mm'], dtype=float)
    require(h > 0 and len(zfaces) == len(z)+1 and np.all(np.diff(zfaces) > 0) and
            np.allclose(z, (zfaces[:-1]+zfaces[1:])/2, rtol=0, atol=1e-8) and
            np.allclose(np.diff(x), h, rtol=0, atol=1e-8) and
            np.allclose(np.diff(y), h, rtol=0, atol=1e-8), 'Native cell faces do not match grid')
    ix, iy, iz = (np.searchsorted(a, grid[:, k]) for k, a in enumerate((x, y, z)))
    require(len(np.unique((iz*len(y)+iy)*len(x)+ix)) == len(grid), 'Duplicate native grid cell')
    counts = np.bincount(iz, minlength=len(z))
    require(np.all(counts == counts[0]), 'Identical represented XY cells required at every depth')
    xy_index = int(np.argmin(np.abs(z-float(xy_depth_mm))))
    y_index = int(np.argmin(np.abs(y)))
    xy = np.full((len(y), len(x)), np.nan)
    xz = np.full((len(z), len(x)), np.nan)
    on_xy, on_xz = iz == xy_index, iy == y_index
    xy[iy[on_xy], ix[on_xy]] = values[on_xy]
    xz[iz[on_xz], ix[on_xz]] = values[on_xz]
    return dict(xy=xy, xz=xz, x_edges_mm=np.r_[x-h/2, x[-1]+h/2],
                y_edges_mm=np.r_[y-h/2, y[-1]+h/2], z_edges_mm=zfaces,
                xy_actual_depth_mm=float(z[xy_index]), xz_actual_y_mm=float(y[y_index]))


def shared_color_limits(cases, metric, mode, deep_roi=False):
    require(metric in METRICS and mode in MODES and cases, 'Known metric/mode and cases required')
    maximum = 0.
    for case in cases:
        scale = float(case['scales'][mode]); values = np.asarray(case['arrays'][metric])
        require(math.isfinite(scale) and scale > 0 and values.size and np.all(np.isfinite(values)) and
                np.all(values >= 0), 'Finite positive saved scale and nonnegative scalar required')
        if deep_roi:
            mask=np.asarray(case['arrays']['region_target_m3']) > 0
            require(mask.shape == values.shape and np.any(mask), 'Nonempty frozen primary ROI required for display range')
            values=values[mask]
        maximum = max(maximum, float(np.max(values))*scale)
    return (0., maximum if maximum > 0 else 1.)


def load_model(baseline_summary, frequency_summaries):
    """Verify terminal JSON/NPZ/grid bindings; consume no field or potential data."""
    pins = {}
    baseline_path = Path(baseline_summary).resolve()
    baseline = bound_json(baseline_path, pins)
    require(baseline.get('status') == 'complete' and baseline.get('id') == 'baseline-square15-xy80',
            'Completed original square baseline required')
    run = baseline_path.parent.parent.parent
    record = bound_json(run/'cases'/f"{baseline['id']}.json", pins)
    require(record['status'] == 'complete' and Path(record['postprocess_path']).resolve() == baseline_path and
            record['postprocess_sha256'] == pins[str(baseline_path)], 'Baseline case is not terminal/source-bound')
    originals = [c for c in baseline['conditions'] if c['waveform'] == 'square_3h']
    require(len(originals) == 1 and originals[0]['native_volume_archive'] == 'volume.npz',
            'Only genuinely stored original square arrays may be used')
    original = originals[0]
    grid_refs = [(p, d) for p, d in baseline['input_sha256'].items() if Path(p).name in ('grid.csv', 'grid.csv.gz')]
    meta_refs = [(p, d) for p, d in baseline['input_sha256'].items() if Path(p).name == 'mesh-metadata.json']
    require(len(grid_refs) == len(meta_refs) == 1, 'Unique source grid and metadata required')
    grid_path, grid_sha = grid_refs[0]
    meta_path, meta_sha = meta_refs[0]
    meta = bound_json(meta_path, pins, meta_sha)
    require(meta['radius_mm'] == 25 and math.isclose(meta['total_depth_mm'], 25.1) and
            np.allclose(meta['tissue_boundaries_mm'], [0, .1, 5.1, 10.1, 25.1], rtol=0, atol=1e-12),
            'D50 and frozen .1/5/5/15mm layers required')
    require(sha(grid_path) == grid_sha, 'Grid SHA mismatch')
    pins[str(Path(grid_path).resolve())] = grid_sha
    opener = gzip.open if str(grid_path).endswith('.gz') else open
    with opener(grid_path, 'rt') as stream:
        grid = np.loadtxt(stream, delimiter=',', skiprows=1)
    require(len(grid) == meta['cells'] and np.all(np.isfinite(grid)) and
            np.all(np.sum(grid[:, :2]**2, axis=1) < 625), 'Invalid D50 native grid')
    path = baseline_path.parent/'volume.npz'
    digest = baseline['artifacts']['files']['volume.npz']['SHA256']
    arrays = load_scalars(path, digest, meta['cells']); pins[str(path)] = digest
    cases = [dict(id=original['id'], label='Square 3k/3.03k + 3rd harmonics', waveform='square_3h',
        actual_fundamental_Hz=[3000,3030], beat_frequency_Hz=30, arrays=arrays,
        scales={'raw_1Vpp':1., 'skin_contact_only':1.}, source_summary=str(baseline_path),
        source_condition_id=original['id'], scalar_archive=str(path),
        configuration_sha256=record['config_sha256'], native_grid_SHA256=grid_sha)]
    found = {}; canonical_limits = None
    for summary_path in frequency_summaries:
        summary = bound_json(summary_path, pins)
        require(summary.get('schema') in SCHEMAS and summary.get('status') == 'calculated_unadopted' and
                summary.get('inputs_unchanged') is True and summary.get('candidate_adopted') is False,
                'Terminal, unchanged, unadopted frequency summary required')
        inputs = summary['input_sha256']
        require(inputs.get(str(baseline_path)) == pins[str(baseline_path)] and
                inputs.get(str(Path(grid_path).resolve())) == grid_sha, 'Frequency summary lacks original baseline/grid binding')
        declared_grids = [d for p,d in inputs.items() if Path(p).name in ('grid.csv', 'grid.csv.gz')]
        require(declared_grids and all(d == grid_sha for d in declared_grids), 'Frequency grids differ from cached baseline')
        for reference in summary['conditions']:
            pair = tuple(reference['actual_fundamental_Hz'])
            if pair not in PAIRS:
                continue  # Old9k/9090 beat90 is deliberately not in the common beat30 comparison.
            require(pair not in found and reference['status'] == 'calculated_unadopted', 'Duplicate or incomplete frequency condition')
            artifacts = reference['artifacts']; cref = artifacts['condition.json']; vref = artifacts['volume.npz']
            condition = bound_json(cref['path'], pins, cref['SHA256'])
            require(condition['status'] == 'calculated_unadopted' and condition['id'] == reference['id'] and
                    condition['waveform'] == 'sine' and condition['actual_fundamental_Hz'] == list(pair) and
                    condition['beat_frequency_Hz'] == 30 and reference['beat_frequency_Hz'] == 30 and
                    condition['candidate_adopted'] is False, 'Saved pure-sine identity or actual beat differs')
            cohort = condition['cohorts'][COHORT]; mode = cohort['normalizations']['skin_contact_only']
            require(cohort['reference_id'] == original['id'] and cohort['reference_waveform'] == 'square_3h' and
                    cohort['reference_actual_fundamental_Hz'] == [3000,3030] and
                    mode['includes_source_power_cap'] is False and mode['includes_1Vpp_ceiling'] is False,
                    'Canonical eight skin/contact caps must remain distinct from source-power/voltage caps')
            limits = mode['baseline_derived_numerical_limits']
            require(CAPS <= set(limits) and all(math.isfinite(limits[k]) and limits[k] > 0 for k in CAPS), 'Eight saved cap limits required')
            if canonical_limits is None:
                canonical_limits = limits
            require(limits == canonical_limits, 'Original square numerical cap references differ')
            scale = float(mode['amplitude_scale'])
            require(math.isfinite(scale) and scale > 0 and np.allclose(mode['source_Vpp_by_output'], [scale,scale],
                    rtol=1e-12, atol=1e-14), 'Saved equal-output sine amplitude scale required')
            archive = Path(vref['path']).resolve()
            require(archive.parent == Path(cref['path']).resolve().parent and archive.name == 'volume.npz',
                    'Condition and scalar archive must belong together')
            a = load_scalars(archive, vref['SHA256'], meta['cells']); pins[str(archive)] = vref['SHA256']
            for name in ('region_total_m3','region_target_m3','region_surface_0_5_m3'):
                require(np.array_equal(a[name], arrays[name]), 'Frozen ROI/native volume weights differ')
            found[pair] = dict(id=condition['id'], label=f'Sine {pair[0]/1000:g}k/{pair[1]/1000:g}k; beat30Hz',
                waveform='sine', actual_fundamental_Hz=list(pair), beat_frequency_Hz=30, arrays=a,
                scales={'raw_1Vpp':1., 'skin_contact_only':scale}, source_summary=str(Path(summary_path).resolve()),
                source_condition_id=condition['id'], scalar_archive=str(archive), canonical_cap_reference_id=cohort['reference_id'],
                source_provenance={key:value for key,value in condition['source_provenance'].items()
                    if key in ('run_id','case_id','native_case_id','source_commit','source_summary','configuration_sha256','circuit')},
                native_grid_SHA256=grid_sha)
    require(set(found) == set(PAIRS), 'Exactly the five actual beat30 sine pairs are required')
    cases.extend(found[pair] for pair in PAIRS)
    verify_pins(pins)
    return dict(cases=cases, grid=grid, metadata=meta, input_sha256=pins, canonical_limits=canonical_limits)


def render_model(model, output, deep_color_range=False):
    """Write6 panels with one global color range per stored metric/mode/slice."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    output = Path(output).resolve()
    require(not output.exists() and (ROOT/'docs') in output.parents, 'Unique new docs output directory required')
    output.mkdir(parents=True)
    metadata = dict(schema='task1-frequency-native-volume-maps-v1', status='rendering',
        no_new_PDE=True, no_E_phi_decode=True, no_scoring_or_gate_recalculation=True,
        candidate_adopted=False, coordinate_system='x/y horizontal mm; +z depth from skin surface z=0',
        primary_ROI='r<=5mm, depth15..20mm; original frozen partial-cell weights preserved',
        metric_definitions={'maxTIS':'fundamental2carrier maximum over2074 sampled directions; lower bound on continuous direction maximum',
            'fixedTIS':'fundamental2carrier modulation at fixed (1/sqrt2,1/sqrt2,0)',
            'RMS':'total vector field RMS from exactly the stored condition; square includes third harmonics, sine two carriers'},
        modes={'raw_1Vpp':'Stored scalar arrays; nominal source1Vpp/output',
            'skin_contact_only':'Only saved amplitude scale against original square eight skin/contact numerical caps; no source power cap or1Vpp ceiling'},
        input_sha256=model['input_sha256'], canonical_square_numerical_limits=model['canonical_limits'],
        implementation_file_SHA256=sha(__file__),
        implementation_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        display_only=True, full_convergence_validated=False, experimentally_validated=False,
        color_limits={}, artifacts={}, cases=[])
    try:
        for case in model['cases']:
            metadata['cases'].append({k:v for k,v in case.items() if k != 'arrays'})
        for mode, metric, deep in ((mode,metric,deep) for mode in MODES for metric in METRICS
                                   for deep in ((False,True) if deep_color_range else (False,))):
                range_name='deep_ROI_display_clipped' if deep else 'global_native_range'
                low, high = shared_color_limits(model['cases'], metric, mode, deep_roi=deep)
                metadata['color_limits'][range_name+'/'+mode+'/'+metric] = dict(vmin=low, vmax=high,
                    units='V/m', scope=('All native cells with positive frozen primary ROI weight, all6 conditions; above-range values clipped for display'
                        if deep else 'All represented native cells of all6 conditions; shared across XY and XZ'))
                fig, axes = plt.subplots(2, len(model['cases']), figsize=(23,8), layout='constrained')
                for column, case in enumerate(model['cases']):
                    slices = native_slices(model['grid'],model['metadata'],case['arrays'][metric]*case['scales'][mode])
                    for row, plane in enumerate(('xy','xz')):
                        ax=axes[row,column]
                        yy=slices['y_edges_mm'] if plane=='xy' else slices['z_edges_mm']
                        mesh=ax.pcolormesh(slices['x_edges_mm'],yy,slices[plane],shading='flat',vmin=low,vmax=high,cmap='viridis',rasterized=True)
                        ax.set(xlabel='x (mm)', ylabel='y (mm)' if plane=='xy' else '+z depth (mm)')
                        if plane=='xy':
                            ax.add_patch(Circle((0,0),5,fill=False,color='white',linestyle='--',linewidth=.8))
                            ax.set_aspect('equal'); ax.set_title(case['label']+'\n'+f"native z={slices['xy_actual_depth_mm']:.4g}mm; scale={case['scales'][mode]:.5g}",fontsize=8)
                        else:
                            for boundary in (.1,5.1,10.1): ax.axhline(boundary,color='white',linestyle=':',linewidth=.6)
                            ax.axhline(5,color='orange',linestyle='--',linewidth=.6)
                            radial_half_width=math.sqrt(max(0,25-slices['xz_actual_y_mm']**2))
                            ax.add_patch(Rectangle((-radial_half_width,15),2*radial_half_width,5,fill=False,color='white',linestyle='--',linewidth=.8))
                            ax.invert_yaxis(); ax.set_title(f"native y={slices['xz_actual_y_mm']:.4g}mm; ROI radial cross-section",fontsize=8)
                fig.colorbar(mesh,ax=axes.ravel().tolist(),label=metric+' (V/m); '+range_name,shrink=.8)
                fig.suptitle(f'{metric} / {mode} / {range_name}; stored scalars only; no interpolation; +z from skin surface; layers SC0–0.1 / dermis0.1–5.1 / fat5.1–10.1 / muscle10.1–25.1mm; orange z=5mm surface-region edge')
                path=output/f'{range_name}--{mode}--{metric}.png'; fig.savefig(path,dpi=140); plt.close(fig)
                metadata['artifacts'][path.name]={'SHA256':sha(path),'path':str(path)}
        verify_pins(model['input_sha256'])
        metadata['status']='rendered_unadopted'; metadata['inputs_unchanged']=True
    except BaseException as error:
        metadata['status']='error';metadata['failure']={'type':type(error).__name__,'message':str(error)}
        (output/'summary.json').write_text(json.dumps(metadata,indent=2,allow_nan=False)+'\n')
        raise
    (output/'summary.json').write_text(json.dumps(metadata,indent=2,allow_nan=False)+'\n')
    return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-summary',required=True)
    parser.add_argument('--frequency-summary',action='append',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--deep-color-range',action='store_true',help='Also render a separately labeled common primary-ROI display range, clipping higher values; no new metrics')
    args=parser.parse_args()
    started=time.monotonic()
    require(not Path(args.output).exists(), 'Output exists; preserve all originals')
    model=load_model(args.baseline_summary,args.frequency_summary)
    result=render_model(model,args.output,deep_color_range=args.deep_color_range)
    print(json.dumps({'status':result['status'],'output':str(Path(args.output).resolve()),'wall_seconds':time.monotonic()-started}))


if __name__=='__main__':
    main()
