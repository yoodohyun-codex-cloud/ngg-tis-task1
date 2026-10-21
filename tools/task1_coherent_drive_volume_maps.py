"""Display saved coherent-drive scalars; never solve, resynthesize or rescore.

The external root guard owns the dual lock,120-second deadline,CPU1,RSS3GiB,
2GiB free-disk reserve and ledger. Importing this file performs no file reads.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np
import task1_frequency_volume_maps as base

ROOT=base.ROOT
RATIOS=(.5,1.)
PHASES=(0,90,180,270)
BASELINE='baseline-square15-xy80'
EXCLUSIVE='sine-3000-3030-beat30'
SOURCE_VPP_DEFINITION='actual full two-tone max-minus-min before50ohm; bounds, not each tone Vpp'
require=base.require
shared_color_limits=base.shared_color_limits


def _id(ratio,phase):
    return f"coherent-r{'0p5' if ratio == .5 else '1'}-p{phase:03d}"


def validate_summary(summary):
    require(summary.get('schema') == 'task1-coherent-drive-scout-v1' and summary.get('status') == 'calculated_unadopted' and
        summary.get('inputs_unchanged') is True and summary.get('new_PDE') == 0 and
        all(summary.get(key) is False for key in ('candidate_adopted','full_convergence_validated','experimentally_validated')) and
        summary.get('actual_fundamental_Hz') == [3000,3030] and summary.get('beat_frequency_Hz') == 30,
        'Terminal unchanged unadopted coherent eight-condition summary required')
    rows=summary.get('conditions',[])
    require(len(rows) == 8 and [row.get('id') for row in rows] == [_id(r,p) for r in RATIOS for p in PHASES] and
        all(row.get('mix_ratio') == r and row.get('phase_deg') == p and row.get('status') == 'calculated_unadopted'
            for row,(r,p) in zip(rows,((r,p) for r in RATIOS for p in PHASES))),
        'Exactly saved ratios0.5/1 and phases0/90/180/270 in declared order required')
    return rows


def validate_condition(condition,reference,baseline_id,configsha,canonical_limits):
    require(condition.get('schema') == 'task1-coherent-drive-condition-v1' and condition.get('status') == 'calculated_unadopted' and
        condition.get('id') == reference['id'] and condition.get('mix_ratio') == reference['mix_ratio'] and
        condition.get('phase_deg') == reference['phase_deg'] and condition.get('source_case_id') == baseline_id and
        condition.get('configuration_sha256') == configsha and condition.get('actual_fundamental_Hz') == [3000,3030] and
        condition.get('active_frequencies_Hz') == [3000,3030] and condition.get('harmonics_active') is False and
        condition.get('new_PDE') == 0 and all(condition.get(key) is False for key in
            ('candidate_adopted','full_convergence_validated','experimentally_validated')),
        'Saved coherent condition/config/actual two-line drive identity differs')
    circuit=condition['source_circuit']
    require(circuit.get('n_pads') == 4 and circuit.get('n_outputs') == 2 and circuit.get('n_return_nodes') == 1 and
        circuit.get('pad_to_node') == {'0':'out0','1':'out1','2':'GND','3':'GND'} and circuit.get('source_resistance_ohm') == 50 and
        circuit.get('return_topology') == 'all_return_pads_ideal_common_GND' and
        circuit.get('uncommanded_frequency_termination','').replace(' ','') == '0Vthrough50ohm' and
        circuit.get('active_frequencies_by_output_Hz') == {'0':[3000,3030],'1':[3000,3030]},
        'Four physical pads/two commonGND50ohm outputs with both tones on both outputs required')
    scales={};intervals={};uppers={}
    for mode in base.MODES:
        row=condition['normalizations'][mode];scale=float(row['amplitude_scale'])
        require(math.isfinite(scale) and scale>0 and row['baseline_derived_numerical_limits'] == canonical_limits and
            base.CAPS <= set(canonical_limits) and all(math.isfinite(canonical_limits[k]) and canonical_limits[k]>0 for k in base.CAPS) and
            row['includes_source_power_cap'] is False and row['includes_1Vpp_ceiling'] is False and
            row['source_Vpp_definition'] == SOURCE_VPP_DEFINITION,
            'Only saved original-square eight skin/contact cap scales and full-source Vpp intervals are allowed')
        interval=np.asarray(row['actual_source_Vpp_intervals_V'],float);upper=np.asarray(row['source_Vpp_upper_by_output_V'],float)
        require(interval.shape == (2,2) and upper.shape == (2,) and np.isfinite(interval).all() and
            np.all(interval[:,0]>0) and np.all(interval[:,1]>=interval[:,0]) and
            np.array_equal(interval[:,1],upper),'Positive saved full-source voltage intervals required')
        scales[mode]=scale;intervals[mode]=interval.tolist();uppers[mode]=upper.tolist()
    require(scales['raw_1Vpp'] == 1 and np.allclose(uppers['raw_1Vpp'],[1.,1.],rtol=0,atol=1e-12) and
        np.allclose(intervals['skin_contact_only'],np.asarray(intervals['raw_1Vpp'])*scales['skin_contact_only'],rtol=1e-12,atol=1e-14),
        'Saved skin-cap source interval must use the saved raw common amplitude scale; no per-tone1Vpp reinterpretation')
    return dict(scales=scales,source_voltage_intervals=intervals,source_Vpp_upper_by_output=uppers,
        source_Vpp_definition=SOURCE_VPP_DEFINITION,source_circuit=copy.deepcopy(circuit))


def panel_cases(model,ratio):
    require(ratio in RATIOS and len(model['cases']) == 10,'One of two fixed ratio panels over ten conditions required')
    controls=model['cases'][:2]
    selected=[case for case in model['cases'][2:] if case.get('mix_ratio') == ratio]
    require([case.get('phase_deg') for case in selected] == list(PHASES),'Four distinct stored phase conditions required per ratio panel')
    return [*controls,*selected]


def _archive(reference,condition_path,canonical_arrays,meta,pins):
    archive=Path(reference['path']).resolve()
    require(archive.name == 'volume.npz' and archive.parent == Path(condition_path).resolve().parent,
        'Saved scalar archive must belong to the condition artifact directory')
    arrays=base.load_scalars(archive,reference['SHA256'],meta['cells']);pins[str(archive)]=reference['SHA256']
    for key in ('region_total_m3','region_target_m3','region_surface_0_5_m3'):
        require(np.array_equal(arrays[key],canonical_arrays[key]),'Frozen original native volume/ROI weights differ')
    return arrays


def _artifact_pins(artifacts,pins):
    require({'condition.json','volume.npz','probes.json','native-volume-metrics.json'} == set(artifacts),
        'Complete saved scalar/condition/probe/metric artifacts required')
    for name,reference in artifacts.items():
        path=Path(reference['path']).resolve()
        require(path.name == name and path.is_file() and path.suffix in ('.json','.npz') and not path.is_symlink() and
            base.sha(path) == reference['SHA256'],'Saved artifact SHA/path differs')
        pins[str(path)]=reference['SHA256']


def load_model(baseline_summary,coherent_summary):
    """Called only by the externally guarded display stage; no E/phi reads."""
    pins={};baseline_path=Path(baseline_summary).resolve();coherent_path=Path(coherent_summary).resolve()
    summary=base.bound_json(coherent_path,pins);references=validate_summary(summary);inputs=summary['input_sha256']
    require(str(baseline_path) in inputs,'Coherent summary must pin original four-square source summary')
    baseline=base.bound_json(baseline_path,pins,inputs[str(baseline_path)])
    require(baseline.get('status') == 'complete' and baseline.get('id') == BASELINE and
        Path(summary['canonical_square_reference']['summary_path']).resolve() == baseline_path,
        'Actual original square control must remain the baseline')
    run=baseline_path.parent.parent.parent;record=base.bound_json(run/'cases'/(BASELINE+'.json'),pins)
    pre=base.bound_json(run/'preregistration.json',pins);native=next(c for c in pre['cases'] if c['id'] == BASELINE)
    require(record['status'] == 'complete' and record['postprocess_path'] == str(baseline_path) and
        record['postprocess_sha256'] == pins[str(baseline_path)] and record['config_sha256'] == native['config_sha256'],
        'Baseline terminal case/config/source receipt differs')
    for key in ('config','mask'):
        path=Path(native[key+'_file']).resolve();require(base.sha(path) == native[key+'_sha256'],'Baseline physical config/mask SHA differs')
        pins[str(path)]=native[key+'_sha256']
    original=next(c for c in baseline['conditions'] if c['waveform'] == 'square_3h')
    require(original['actual_fundamental_Hz'] == [3000,3030] and original['source_Vpp_per_output'] == 1 and
        original['native_volume_archive'] == 'volume.npz','Original genuine4-line square source/array archive required')
    def one(names):
        found=[(p,d) for p,d in baseline['input_sha256'].items() if Path(p).name in names]
        require(len(found) == 1,'Unique actual native grid/mesh source required');return found[0]
    grid_path,grid_sha=one({'grid.csv','grid.csv.gz'});meta_path,meta_sha=one({'mesh-metadata.json'})
    meta=base.bound_json(meta_path,pins,meta_sha)
    require(meta == baseline['mesh_metadata'] and meta['config_sha256'] == native['config_sha256'] and
        meta['radius_mm'] == 25 and math.isclose(meta['total_depth_mm'],25.1) and meta['h_xy_mm'] == .625 and
        meta['sc_cells'] == 2 and meta['bulk_layer_counts'] == [14,14,40] and meta['frequencies_Hz'] == [3000,3030,9000,9090] and
        np.allclose(meta['tissue_boundaries_mm'],[0,.1,5.1,10.1,25.1],rtol=0,atol=1e-12),
        'Same fixedD50 original four-line native mesh/config required')
    require(inputs.get(str(Path(grid_path).resolve())) == grid_sha and base.sha(grid_path) == grid_sha,
        'Coherent native grid SHA differs from original')
    require(all(d == grid_sha for p,d in inputs.items() if Path(p).name in ('grid.csv','grid.csv.gz')),
        'A coherent source uses a different raw native grid')
    pins[str(Path(grid_path).resolve())]=grid_sha
    with (gzip.open(grid_path,'rt') if str(grid_path).endswith('.gz') else open(grid_path)) as stream:
        grid=np.loadtxt(stream,delimiter=',',skiprows=1)
    require(len(grid) == meta['cells'] and np.isfinite(grid).all() and np.all(np.sum(grid[:,:2]**2,axis=1)<625),
        'Finite original cell-aligned D50 grid required')
    archive=baseline_path.parent/'volume.npz';digest=baseline['artifacts']['files']['volume.npz']['SHA256']
    arrays=base.load_scalars(archive,digest,meta['cells']);pins[str(archive)]=digest
    cases=[dict(id=original['id'],label='4-line square baseline',waveform='square_3h',active_frequencies_Hz=[3000,3030,9000,9090],
        arrays=arrays,scales={'raw_1Vpp':1.,'skin_contact_only':1.},source_summary=str(baseline_path),
        source_condition_id=original['id'],configuration_sha256=native['config_sha256'],scalar_archive=str(archive),
        source_voltage_intervals={mode:[[1.,1.],[1.,1.]] for mode in base.MODES},source_Vpp_definition='Original saved1Vpp whole square waveform per output')]
    canonical_limits=summary['canonical_square_reference']['burdens']
    control=summary['cached_exclusive_sine_control'];require(control['id'] == EXCLUSIVE and control.get('new_PDE') == 0 and
        control.get('new_condition') is False and control.get('recomposed') is False,'Actual cached exclusive sine control required')
    exclusive_path=Path(control['summary_path']).resolve();require(str(exclusive_path) in inputs,'Exclusive summary provenance required')
    exsummary=base.bound_json(exclusive_path,pins,inputs[str(exclusive_path)])
    require(exsummary['status'] == 'calculated_unadopted' and exsummary['inputs_unchanged'] is True and
        exsummary['candidate_adopted'] is False and exsummary['input_sha256'].get(str(Path(grid_path).resolve())) == grid_sha and
        exsummary['input_sha256'].get(str(baseline_path)) == pins[str(baseline_path)],
        'Terminal unchanged exclusive control summary required')
    _artifact_pins(control['artifacts'],pins);cref=control['artifacts']['condition.json']
    ex=base.bound_json(cref['path'],pins,cref['SHA256']);mode=ex['cohorts'][base.COHORT]['normalizations']['skin_contact_only']
    require(ex['id'] == EXCLUSIVE and ex['status'] == 'calculated_unadopted' and ex['waveform'] == 'sine' and
        ex['actual_fundamental_Hz'] == [3000,3030] and ex['beat_frequency_Hz'] == 30 and ex['candidate_adopted'] is False and
        ex['source_provenance']['case_id'] == BASELINE and ex['source_provenance']['source_summary'] == str(baseline_path) and
        ex['source_Vpp_by_output'] == [1.,1.] and
        ex['source_provenance']['configuration_sha256'] == native['config_sha256'] and
        mode['baseline_derived_numerical_limits'] == canonical_limits and mode['includes_source_power_cap'] is False and
        mode['includes_1Vpp_ceiling'] is False,'Cached exclusive sine source/config/eight-cap reference differs')
    scale=float(mode['amplitude_scale']);require(math.isfinite(scale) and scale>0 and
        np.allclose(mode['source_Vpp_by_output'],[scale,scale],rtol=1e-12,atol=1e-14),'Saved exclusive source scale differs')
    exarrays=_archive(control['artifacts']['volume.npz'],cref['path'],arrays,meta,pins)
    cases.append(dict(id=ex['id'],label='Exclusive 2-line sine control',waveform='sine',active_frequencies_Hz=[3000,3030],
        arrays=exarrays,scales={'raw_1Vpp':1.,'skin_contact_only':scale},source_summary=str(exclusive_path),
        source_condition_id=ex['id'],configuration_sha256=native['config_sha256'],scalar_archive=control['artifacts']['volume.npz']['path'],
        source_voltage_intervals={'raw_1Vpp':[[1.,1.],[1.,1.]],'skin_contact_only':[[scale,scale],[scale,scale]]},
        source_Vpp_definition='Saved whole pure-sine Vpp per output; one active carrier per output'))
    for reference in references:
        _artifact_pins(reference['artifacts'],pins);cref=reference['artifacts']['condition.json']
        condition=base.bound_json(cref['path'],pins,cref['SHA256'])
        details=validate_condition(condition,reference,BASELINE,native['config_sha256'],canonical_limits)
        a=_archive(reference['artifacts']['volume.npz'],cref['path'],arrays,meta,pins)
        cases.append(dict(id=condition['id'],label=f"Coherent r={condition['mix_ratio']:g}; phase{condition['phase_deg']}deg",
            mix_ratio=condition['mix_ratio'],phase_deg=condition['phase_deg'],waveform='coherent_two_tone_sine',
            active_frequencies_Hz=[3000,3030],arrays=a,source_summary=str(coherent_path),source_condition_id=condition['id'],
            source_condition_json=cref['path'],configuration_sha256=native['config_sha256'],scalar_archive=reference['artifacts']['volume.npz']['path'],
            stored_canonical_screen=copy.deepcopy(condition['canonical_skin_cap_screen']),**details))
    base.verify_pins(pins)
    highlight=next(c for c in cases if c.get('mix_ratio') == 1 and c.get('phase_deg') == 90)
    checks={row['name']:row for row in highlight['stored_canonical_screen']['checks']}
    saved_changes={key:checks[key]['relative_change_percent'] for key in
        ('primary_maxTIS_mean','surface_0_5_maxTIS_p95','primary_complement_maxTIS_p95')}
    require(all(math.isfinite(v) for v in saved_changes.values()),'Finite saved screen percentage labels required')
    return dict(cases=cases,grid=grid,metadata=meta,input_sha256=pins,canonical_limits=canonical_limits,
        source_coherent_summary=str(coherent_path),saved_r1_phase90_changes_percent=saved_changes,
        interpretation='Stored scalar display only; no waveform, source-Vpp, normalization or gate recalculation')


def render_model(model,output):
    """Render24 images: two ratios with shared all-ten-case metric ranges."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle,Rectangle
    output=Path(output).resolve();require(not output.exists() and (ROOT/'docs') in output.parents,'Unique new docs output directory required')
    output.mkdir(parents=True)
    receipt=dict(schema='task1-coherent-drive-volume-maps-v1',status='rendering',display_only=True,new_PDE=0,
        no_E_phi_decode=True,no_waveform_or_Vpp_recalculation=True,no_scoring_or_gate_recalculation=True,
        candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,
        source_coherent_summary=model['source_coherent_summary'],input_sha256=model['input_sha256'],
        saved_r1_phase90_changes_percent=model['saved_r1_phase90_changes_percent'],
        implementation_SHA256=base.sha(__file__),renderer_helper_SHA256=base.sha(base.__file__),
        implementation_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        external_guard_required=dict(seconds=120,CPU=1,RSS_bytes=3*1024**3,free_disk_bytes=2*1024**3,ledger_owner='root external guard'),
        case_count=10,panel_count=2,columns_per_panel=6,png_count_expected=24,
        coordinates='x/y horizontal mm; +z depth from skin surface0; native-cell samples only, no interpolation',
        ROI='Unchanged original r<=5mm, depth15..20mm, fractional native weights',
        metric_definitions={'maxTIS':'Fundamental2carrier maximum over2074 sampled directions; lower bound on continuous-direction maximum',
            'fixedTIS':'Fundamental2carrier modulation in fixed diagonal direction (1/sqrt2,1/sqrt2,0)',
            'RMS':'Stored vector-field RMS; four square spectral lines versus two pure-sine lines; distinct from modulation'},
        drive_definitions='Baseline4line square; exclusive control1sine per output; coherent2tones on BOTH outputs. Whole-source Vpp before50ohm, not per-tone Vpp.',
        normalization='Raw saved whole-source1Vpp intervals or saved common skin8 scale only; no source-power/1Vpp ceiling cap, no human safety inference',
        limitations=['Layer-boundary high fields and clipped deep display do not establish deep focus or a fat-band target.',
            'Multitone hardware phase sync, power sinking/compliance and instrument loading remain unvalidated.'],
        cases=[{k:v for k,v in c.items() if k!='arrays'} for c in model['cases']],color_limits={},artifacts={})
    try:
        for mode in base.MODES:
            for metric in base.METRICS:
                for deep in (False,True):
                    name='deep_ROI_display_clipped' if deep else 'global_native_range'
                    low,high=shared_color_limits(model['cases'],metric,mode,deep_roi=deep)
                    receipt['color_limits'][name+'/'+mode+'/'+metric]=dict(vmin=low,vmax=high,units='V/m',
                        scope='ALL10 distinct cases and BOTH ratio panels/XY+XZ; '+('positive original primary ROI weight cells only; above-range colors clipped' if deep else 'all represented native cells'))
                    for ratio in RATIOS:
                        selected=panel_cases(model,ratio);fig,axes=plt.subplots(2,6,figsize=(23,7.5),layout='constrained')
                        for col,c in enumerate(selected):
                            sl=base.native_slices(model['grid'],model['metadata'],c['arrays'][metric]*c['scales'][mode])
                            for row,plane in enumerate(('xy','xz')):
                                ax=axes[row,col];yy=sl['y_edges_mm'] if plane=='xy' else sl['z_edges_mm']
                                image=ax.pcolormesh(sl['x_edges_mm'],yy,sl[plane],shading='flat',vmin=low,vmax=high,cmap='viridis',rasterized=True)
                                ax.set(xlabel='x (mm)',ylabel='y (mm)' if plane=='xy' else '+z depth (mm)')
                                if plane=='xy':
                                    ax.add_patch(Circle((0,0),5,fill=False,color='white',linestyle='--',linewidth=.8));ax.set_aspect('equal')
                                    vpp=c['source_voltage_intervals'][mode]
                                    ax.set_title(c['label']+f"\nz={sl['xy_actual_depth_mm']:.3g}mm; scale={c['scales'][mode]:.4g}\nwhole Vpp bounds {vpp[0][0]:.4g}..{vpp[0][1]:.4g} / {vpp[1][0]:.4g}..{vpp[1][1]:.4g}",fontsize=7)
                                else:
                                    for boundary in (.1,5.1,10.1):ax.axhline(boundary,color='white',linestyle=':',linewidth=.6)
                                    ax.axhline(5,color='orange',linestyle='--',linewidth=.6)
                                    radial=math.sqrt(max(0,25-sl['xz_actual_y_mm']**2))
                                    ax.add_patch(Rectangle((-radial,15),2*radial,5,fill=False,color='white',linestyle='--',linewidth=.8))
                                    ax.invert_yaxis();ax.set_title(f"native y={sl['xz_actual_y_mm']:.3g}mm; fixed primary ROI",fontsize=7)
                        fig.colorbar(image,ax=axes.ravel().tolist(),label=metric+' (V/m); '+name,shrink=.8)
                        changes=model['saved_r1_phase90_changes_percent']
                        note=f"r1/phase90 saved skin8: target mean{changes['primary_maxTIS_mean']:+.2f}%, SURFACE P95{changes['surface_0_5_maxTIS_p95']:+.2f}%, complement P95{changes['primary_complement_maxTIS_p95']:+.2f}%; no deep-focus claim"
                        fig.suptitle(f'{metric} / {mode} / r={ratio:g} / {name}; shared ALL10; +z from skin; layers0/.1/5.1/10.1/25.1mm.\n'+note,fontsize=10)
                        path=output/f'r{str(ratio).replace(".","p")}--{name}--{mode}--{metric}.png'
                        fig.savefig(path,dpi=120);plt.close(fig)
                        receipt['artifacts'][path.name]=dict(path=str(path),SHA256=base.sha(path))
        base.verify_pins(model['input_sha256']);receipt.update(status='rendered_unadopted',inputs_unchanged=True)
    except BaseException as error:
        receipt.update(status='error',failure=dict(type=type(error).__name__,message=str(error)))
        (output/'summary.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');raise
    (output/'summary.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-summary',required=True);parser.add_argument('--coherent-summary',required=True)
    parser.add_argument('--output',required=True);args=parser.parse_args()
    start=time.monotonic();require(not Path(args.output).exists(),'Preserve prior map evidence; unique output required')
    model=load_model(args.baseline_summary,args.coherent_summary);result=render_model(model,args.output)
    print(json.dumps(dict(status=result['status'],output=str(Path(args.output).resolve()),wall_seconds=time.monotonic()-start)))


if __name__=='__main__':main()
