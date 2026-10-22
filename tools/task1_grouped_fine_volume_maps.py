#!/usr/bin/env python3
"""Display SHA-bound fine grouped-pad saved scalars; no field/PDE/gate calculations.

Execution serialization, finite resource limits and budget accounting belong to
its calling finite worker. Existing data and outputs are never overwritten.
"""
from __future__ import annotations
import argparse
import gzip
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np
import task1_frequency_volume_maps as base

ROOT=Path(__file__).resolve().parents[1]
BASELINE='baseline-square15-xy80'
BASELINE_RUN='cloud-mesh-c1-20261019T190000Z'
GROUPED_RUN='cloud-grouped-fine-20261021T160000Z'
COUNTS=(4,8,12,16)
GROUPED=tuple(f'grouped-strip225-gap1-p{n:02d}-xy80'for n in COUNTS)
IDS=(BASELINE,*GROUPED)
require=base.require


def validate_circuit(circuit,n):
    require(n in COUNTS,'Supported physical-pad count required')
    m=n//4; nodes=[0]*m+[1]*m+[-1]*(2*m)
    expected={str(p):'GND'if node<0 else f'out{node}'for p,node in enumerate(nodes)}
    require(circuit.get('n_pads')==n and circuit.get('n_outputs')==2 and
        circuit.get('n_return_nodes')==1 and circuit.get('pad_to_node')==expected and
        circuit.get('return_topology')=='all_return_pads_ideal_common_GND'and
        circuit.get('source_resistance_ohm')==50 and circuit.get('source_peak_V')==.5 and
        circuit.get('source_Vpp_each')==1 and circuit.get('carrier_assignment_Hz')==[3000,3030]and
        circuit.get('inactive_source_at_other_frequencies','').replace(' ','')=='0Vthrough50ohm',
        'Physical pads must remain2outputs/common GND/50ohm with passive-frequency termination')
    if 'harmonics_Hz'in circuit:
        require(circuit['harmonics_Hz']==[9000,9090],'Square harmonic identities differ')
    return dict(physical_pads=n,independent_outputs=2,pads_on_out0=m,pads_on_out1=m,
        common_GND_return_pads=2*m,independent_return_nodes=1)


def terminal_report(payload):
    require(payload.get('schema')=='task1-volume-selectivity-v1'and
        payload.get('status')=='calculated_unadopted'and payload.get('inputs_unchanged')is True and
        payload.get('new_PDE_solves')==0 and payload.get('selected_for_adoption')==[],
        'Terminal unchanged unadopted cached-volume report required')
    rows=payload.get('cases',[])
    require([row.get('case_id')for row in rows]==list(IDS),'Exactly original square plus fine4/8/12/16 rows in order required')
    require(all(row.get('adopted')is False and row.get('calculation_status')=='cached_native_scalar_audit_complete'
        for row in rows),'Every saved-volume case must be complete and unadopted')
    return rows


def validate_case(row,post,record,original,n):
    validate_circuit(row['circuit'],n)
    mesh=row['mesh']
    require(mesh.get('h_xy_mm')==.625 and mesh.get('sc_cells')==2 and mesh.get('bulk_layer_counts')==[14,14,40]and
        mesh.get('cells')==351680 and mesh.get('radius_mm')==25 and math.isclose(mesh.get('total_depth_mm',0),25.1)and
        mesh.get('frequencies_Hz')==[3000,3030,9000,9090], 'True fine h.625 SC2 bulk14/14/40 D50 square branch required')
    require(row['run_id']==(BASELINE_RUN if row['case_id']==BASELINE else GROUPED_RUN)and
        row['baseline_summary']==original['summary_path']and
        row['fixed_same_grid_baseline_cutoffs_V_m']==original['fixed_same_grid_baseline_cutoffs_V_m'],
        'Fine grouped rows must retain the exact original square baseline/cutoffs')
    require(post.get('status')=='complete'and post.get('id')==row['case_id']and record.get('status')=='complete'and
        record.get('id')==row['case_id']and Path(record['postprocess_path']).resolve()==Path(row['summary_path']).resolve(),
        'Original source case must be completed and match its saved postprocess path')
    if row['case_id']!=BASELINE:
        require(mesh.get('n_pads')==n and mesh.get('n_outputs')==mesh.get('channels')==2 and
            mesh.get('n_return_nodes')==1 and mesh.get('return_topology')=='common_GND',
            'Grouped native metadata must distinguish physical pads/output/return nodes')
    conditions=[c for c in post['conditions']if c.get('id')==row['condition_id']]
    require(len(conditions)==1,'One exact saved condition required')
    require(record.get('config_sha256')==mesh.get('config_sha256')==row['configuration_sha256'],
        'Saved case, config, volume row and native mesh identities differ')
    require(np.allclose(mesh.get('tissue_boundaries_mm',[]),[0,.1,5.1,10.1,25.1],rtol=0,atol=1e-12),
        'Frozen .1/5/5/15mm tissue boundaries required')
    condition=conditions[0]
    require(condition.get('waveform')=='square_3h'and condition.get('actual_fundamental_Hz')==[3000,3030]and
        condition.get('source_Vpp_per_output')==1 and condition.get('native_volume_archive')=='volume.npz',
        'Only genuinely archived square3h 1Vpp native scalar arrays may be used')
    mode=row['normalizations']['skin_contact_only'];raw=row['normalizations']['raw_1Vpp']
    require(raw['amplitude_scale']==1 and raw['source_Vpp_per_output']==1 and
        mode['includes_source_power_cap']is False and mode['includes_1Vpp_ceiling']is False and
        mode['baseline_derived_numerical_limits']==original['normalizations']['skin_contact_only']['baseline_derived_numerical_limits']and
        base.CAPS<=set(mode['baseline_derived_numerical_limits']), 'Same saved original square eight skin/contact caps required')
    scale=float(mode['amplitude_scale'])
    require(math.isfinite(scale)and scale>0 and math.isclose(mode['source_Vpp_per_output'],scale,rel_tol=1e-12,abs_tol=1e-14),
        'Positive stored common amplitude scale required; normalization is not recalculated')
    return condition,scale


def load_model(audit_path):
    pins={};audit=base.bound_json(audit_path,pins);rows=terminal_report(audit)
    original=rows[0];cases=[];grid=None;canonical_meta=None;canonical_grid_sha=None;canonical_weights=None
    refs=audit['inputs_sha256']
    for row,n in zip(rows,(4,*COUNTS)):
        path=Path(row['summary_path']).resolve()
        require(str(path)in refs,'Volume report must bind source summary SHA')
        post=base.bound_json(path,pins,refs[str(path)])
        run=path.parent.parent.parent
        record_path=run/'cases'/f"{row['case_id']}.json"
        record=base.bound_json(record_path,pins,refs.get(str(record_path)))
        require(record['postprocess_sha256']==pins[str(path)],'Case receipt does not bind postprocess SHA')
        condition,scale=validate_case(row,post,record,original,n)
        native=post['input_sha256']
        def one(name):
            candidates=[(p,d)for p,d in native.items()if Path(p).name in name]
            require(len(candidates)==1,'Unique native grid/metadata input required')
            return candidates[0]
        grid_path,grid_sha=one({'grid.csv','grid.csv.gz'});meta_path,meta_sha=one({'mesh-metadata.json'})
        meta=base.bound_json(meta_path,pins,meta_sha)
        require(meta==row['mesh'],'Saved volume row and actual native mesh metadata differ')
        if canonical_grid_sha is None:
            canonical_grid_sha=grid_sha;canonical_meta=meta
            require(base.sha(grid_path)==grid_sha,'Baseline grid SHA mismatch')
            opener=gzip.open if str(grid_path).endswith('.gz')else open
            with opener(grid_path,'rt')as stream:
                grid=np.loadtxt(stream,delimiter=',',skiprows=1)
            require(len(grid)==meta['cells']and np.all(np.isfinite(grid))and np.all(np.sum(grid[:,:2]**2,axis=1)<625),
                'Finite represented native D50 grid required')
        require(grid_sha==canonical_grid_sha and base.sha(grid_path)==grid_sha,'All five true fine grids must be byte-identical')
        pins[str(Path(grid_path).resolve())]=grid_sha
        require(meta['z_faces_mm']==canonical_meta['z_faces_mm'],'Native thickness faces differ')
        archive=path.parent/'volume.npz';digest=post['artifacts']['files']['volume.npz']['SHA256']
        require(refs.get(str(archive))==digest,'Volume report must bind consumed scalar archive SHA')
        arrays=base.load_scalars(archive,digest,meta['cells']);pins[str(archive)]=digest
        weights={k:arrays[k]for k in ('region_total_m3','region_target_m3','region_surface_0_5_m3')}
        if canonical_weights is None:canonical_weights=weights
        require(all(np.array_equal(weights[k],canonical_weights[k])for k in weights),'Frozen native ROI/volume weights differ')
        cases.append(dict(id=row['case_id'],label='Original4 square pads'if row['case_id']==BASELINE else f'Fine{n} strip pads /2outputs',
            arrays=arrays,scales={'raw_1Vpp':1.,'skin_contact_only':scale},circuit=row['circuit'],
            wiring=validate_circuit(row['circuit'],n),source_commit=row['source_commit'],
            configuration_sha256=row['configuration_sha256'],physical_model_version=row['physical_model_version'],source_summary=str(path),source_condition_id=condition['id'],
            scalar_archive=str(archive),actual_fundamental_Hz=[3000,3030],harmonics_Hz=[9000,9090],native_grid_SHA256=grid_sha))
    base.verify_pins(pins)
    return dict(cases=cases,grid=grid,metadata=canonical_meta,input_sha256=pins,
        canonical_limits=original['normalizations']['skin_contact_only']['baseline_derived_numerical_limits'],
        source_volume_report=str(Path(audit_path).resolve()))


def render_model(model,output,deep_color_range=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle,Rectangle
    output=Path(output).resolve()
    require(not output.exists()and(ROOT/'docs')in output.parents,'Unique new docs output directory required')
    output.mkdir(parents=True)
    receipt=dict(schema='task1-grouped-fine-native-volume-maps-v1',status='rendering',display_only=True,
        source_volume_report=model['source_volume_report'],input_sha256=model['input_sha256'],
        implementation_SHA256=base.sha(__file__),renderer_helper_SHA256=base.sha(base.__file__),
        implementation_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        no_new_PDE=True,no_E_phi_decode=True,no_scoring_or_gate_recalculation=True,candidate_adopted=False,
        full_convergence_validated=False,experimentally_validated=False,case_count=5,
        coordinates='x/y horizontal mm; +z depth from skin surface z=0; layers0/.1/5.1/10.1/25.1mm',
        ROI='Original central r<=5mm, depth15..20mm, frozen partial-cell weights unchanged',
        metric_definitions={'maxTIS':'fundamental2carrier maximum over2074 sampled directions; continuous-direction lower bound',
            'fixedTIS':'fundamental2carrier modulation along (1/sqrt2,1/sqrt2,0)',
            'RMS':'total vector field RMS including all4 square3h spectral lines; not modulation'},
        normalization='raw1Vpp/output or only saved scale from original square eight skin/contact numerical caps; not human safety limits; no power cap/1Vpp ceiling',
        cases=[{k:v for k,v in c.items()if k!='arrays'}for c in model['cases']],color_limits={},artifacts={})
    try:
        for mode in base.MODES:
            for metric in base.METRICS:
                for deep in ((False,True)if deep_color_range else(False,)):
                    kind='deep_ROI_display_clipped'if deep else'global_native_range'
                    low,high=base.shared_color_limits(model['cases'],metric,mode,deep_roi=deep)
                    receipt['color_limits'][kind+'/'+mode+'/'+metric]=dict(vmin=low,vmax=high,units='V/m',
                        scope='All5 fine conditions and both planes; '+('positive frozen ROI-weight cells, above-range colors clipped'if deep else'all represented native cells'))
                    fig,axes=plt.subplots(2,5,figsize=(20,8),layout='constrained')
                    for col,c in enumerate(model['cases']):
                        sl=base.native_slices(model['grid'],model['metadata'],c['arrays'][metric]*c['scales'][mode])
                        for row,plane in enumerate(('xy','xz')):
                            ax=axes[row,col];yy=sl['y_edges_mm']if plane=='xy'else sl['z_edges_mm']
                            image=ax.pcolormesh(sl['x_edges_mm'],yy,sl[plane],shading='flat',vmin=low,vmax=high,cmap='viridis',rasterized=True)
                            ax.set(xlabel='x (mm)',ylabel='y (mm)'if plane=='xy'else'+z depth (mm)')
                            if plane=='xy':
                                ax.add_patch(Circle((0,0),5,fill=False,color='white',linestyle='--',linewidth=.8));ax.set_aspect('equal')
                                ax.set_title(c['label']+f"\nnative z={sl['xy_actual_depth_mm']:.4g}mm; scale={c['scales'][mode]:.5g}",fontsize=8)
                            else:
                                for boundary in(.1,5.1,10.1):ax.axhline(boundary,color='white',linestyle=':',linewidth=.6)
                                ax.axhline(5,color='orange',linestyle='--',linewidth=.6)
                                half=math.sqrt(max(0,25-sl['xz_actual_y_mm']**2))
                                ax.add_patch(Rectangle((-half,15),2*half,5,fill=False,color='white',linestyle='--',linewidth=.8));ax.invert_yaxis()
                                ax.set_title(f"native y={sl['xz_actual_y_mm']:.4g}mm; radial ROI section",fontsize=8)
                    fig.colorbar(image,ax=axes.ravel().tolist(),label=metric+' (V/m); '+kind,shrink=.8)
                    fig.suptitle(f'Fine h.625: original square +4/8/12/16 grouped strips; {metric} / {mode} / {kind}\nNative cells without interpolation; +z from skin surface; SC0–.1 / dermis.1–5.1 / fat5.1–10.1 / muscle10.1–25.1mm')
                    path=output/f'{kind}--{mode}--{metric}.png';fig.savefig(path,dpi=140);plt.close(fig)
                    receipt['artifacts'][path.name]=dict(path=str(path),SHA256=base.sha(path))
        base.verify_pins(model['input_sha256']);receipt.update(status='rendered_unadopted',inputs_unchanged=True)
    except BaseException as error:
        receipt.update(status='error',failure=dict(type=type(error).__name__,message=str(error)))
        (output/'summary.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');raise
    (output/'summary.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--volume-audit',required=True)
    parser.add_argument('--output',required=True);parser.add_argument('--deep-color-range',action='store_true');args=parser.parse_args()
    require(not Path(args.output).exists(),'Never overwrite maps/evidence');started=time.monotonic()
    result=render_model(load_model(args.volume_audit),args.output,args.deep_color_range)
    print(json.dumps(dict(status=result['status'],output=str(Path(args.output).resolve()),wall_seconds=time.monotonic()-started)))


if __name__=='__main__':main()
