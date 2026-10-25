"""Display three SHA-bound saved scalar volumes; no PDE, E/phi or scoring.

The external caller owns dual execution locks, CPU1,120s wall/RSS3GiB,
2GiB free reserve and cumulative resource ledger. Import has no data reads.
"""
from __future__ import annotations
import argparse
import gzip
import html
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np
import task1_frequency_volume_maps as base
import task1_one_return_rotation_maps as previous

ROOT=base.ROOT
IDS=('baseline-square15-xy80','asym-cross281p25-return168p75-xy80','asym-return-tangent4p375-xy80')
LABELS=('Original four-square baseline','Unrotated asymmetric parent','Same parent; two GND returns shifted tangentially')
require=base.require
shared_color_limits=base.shared_color_limits
native_slices=base.native_slices


def validate_audit(summary):
    require(summary.get('schema')=='task1-volume-selectivity-v1' and summary.get('status')=='calculated_unadopted' and
        summary.get('inputs_unchanged') is True and summary.get('selected_for_adoption')==[],
        'Terminal unchanged unadopted saved volume audit required')
    rows=summary.get('cases',[])
    require(len(rows)==3 and tuple(r.get('case_id') for r in rows)==IDS and
        all(r.get('adopted') is False and r.get('calculation_status')=='cached_native_scalar_audit_complete' for r in rows),
        'Exactly original baseline, unrotated asymmetric parent and tangential returns required')
    return rows


validate_modes=previous.validate_modes
validate_grid_contract=previous.validate_grid_contract


def validate_screen(screen,volume_path,volume_sha):
    screened=tuple(r.get('case_id')for r in screen.get('cases',[]))
    require(screen.get('schema')=='task1-candidate-screen-v1'and screen.get('status')=='screen_complete_not_adopted'and
        screen.get('candidate_adopted')is False and screen.get('input_volume_report')==dict(path=str(Path(volume_path).resolve()),SHA256=volume_sha)and
        screened in((IDS[2],),IDS[1:])and all(r.get('candidate_adopted')is False for r in screen['cases']),
        'Completed unadopted screen must bind the exact saved volume and new tangent; cached parent screen may also be present')


def pad_centres_from_properties(text):
    config={k.strip():v.strip()for line in text.splitlines()if line.strip()and not line.lstrip().startswith('#')for k,v in[line.split('=',1)]}
    xy=np.asarray([[float(config[f'pad.{p}.x_mm']),float(config[f'pad.{p}.y_mm'])]for p in range(4)])
    require(xy.shape==(4,2)and np.isfinite(xy).all()and np.all(np.sum(xy*xy,axis=1)<625),'Finite operative four-pad XY centres insideD50 required')
    return xy


def validate_pad_translation(parent,new):
    parent=np.asarray(parent,float);new=np.asarray(new,float)
    require(parent.shape==new.shape==(4,2)and np.isfinite(parent).all()and np.isfinite(new).all()and
        np.array_equal(parent[:2],new[:2])and np.array_equal(parent[2:],[[10.,-10.],[-10.,10.]])and
        np.array_equal(new[2:],[[14.375,-5.625],[-14.375,5.625]]),
        'Only the registered two integer-cell GND return translations with sources unchanged are displayed')


def load_model(volume_audit,screen_path=None):
    """Read saved summaries, configs/masks, scalar NPZ and one native grid only."""
    pins={};summary=base.bound_json(volume_audit,pins);rows=validate_audit(summary);scales=validate_modes(rows)
    screen_path=Path(screen_path)if screen_path is not None else Path(volume_audit).resolve().parent/'screen.json'
    screen=base.bound_json(screen_path,pins);validate_screen(screen,volume_audit,pins[str(Path(volume_audit).resolve())])
    declared=summary['inputs_sha256'];cases=[];canonical_meta=None;grid_path=None;grid_sha=None
    def bound(path,expected=None):
        path=Path(path).resolve();digest=declared.get(str(path))
        require(digest is not None and (expected is None or digest==expected),'Audit lacks exact artifact binding: '+str(path))
        return base.bound_json(path,pins,digest)
    def binary_pin(path,expected):
        path=Path(path).resolve();require(declared.get(str(path))==expected and base.sha(path)==expected,'Saved config/grid/scalar SHA differs')
        pins[str(path)]=expected
    for row,scale,label in zip(rows,scales,LABELS):
        sp=Path(row['summary_path']).resolve();post=bound(sp);run=sp.parents[2]
        require(post.get('status')=='complete' and post.get('id')==row['case_id'] and post.get('source_inputs_unchanged') is True,
            'Completed unchanged native postprocessor summary required')
        record=bound(run/'cases'/(row['case_id']+'.json'));pre=bound(run/'preregistration.json')
        case=next(c for c in pre['cases'] if c['id']==row['case_id'])
        require(record['status']=='complete' and Path(record['postprocess_path']).resolve()==sp and
            record['postprocess_sha256']==pins[str(sp)] and record['config_sha256']==case['config_sha256']==row['configuration_sha256'],
            'Terminal case/source/config receipt differs')
        for key in ('config','mask'):binary_pin(case[key+'_file'],case[key+'_sha256'])
        centres=pad_centres_from_properties(Path(case['config_file']).read_text())
        circuit=row['circuit'];require(circuit['n_pads']==4 and circuit['n_outputs']==2 and circuit['n_return_nodes']==1 and
            circuit['return_topology']=='all_return_pads_ideal_common_GND' and circuit['source_resistance_ohm']==50 and
            circuit['pad_to_node']=={'0':'out0','1':'out1','2':'GND','3':'GND'},'Four physical pads/two common-GND50ohm outputs required')
        square=[c for c in post['conditions'] if c['waveform']=='square_3h']
        require(len(square)==1 and square[0]['id']==row['condition_id'] and square[0]['native_volume_archive']=='volume.npz' and
            square[0]['actual_fundamental_Hz']==[3000,3030] and square[0]['source_Vpp_per_output']==1,
            'Genuine saved square3h scalar archive required; no waveform alias')
        refs=post['input_sha256']
        def one(names):
            found=[(p,d) for p,d in refs.items() if Path(p).name in names]
            require(len(found)==1,'Unique native source reference required');return found[0]
        mp,md=one({'mesh-metadata.json'});gp,gd=one({'grid.csv','grid.csv.gz'})
        meta=bound(mp,md);validate_grid_contract(meta)
        require(meta==post['mesh_metadata']==row['mesh'] and meta['config_sha256']==case['config_sha256'],'Stored mesh/config identities differ')
        if canonical_meta is None:canonical_meta=meta;grid_path=gp;grid_sha=gd
        require(gd==grid_sha and meta['z_faces_mm']==canonical_meta['z_faces_mm'],'Case native grid/coordinates differ')
        binary_pin(gp,gd)
        vp=sp.parent/'volume.npz';vd=post['artifacts']['files']['volume.npz']['SHA256'];binary_pin(vp,vd)
        arrays=base.load_scalars(vp,vd,meta['cells'])
        if cases:
            for key in ('region_total_m3','region_target_m3','region_surface_0_5_m3'):
                require(np.array_equal(arrays[key],cases[0]['arrays'][key]),'Frozen native ROI/volume weights differ')
        cases.append(dict(id=row['case_id'],label=label,arrays=arrays,scales=scale,source_summary=str(sp),
            projected_top_contact_pad_centres_mm=centres.tolist(),operative_config_path=case['config_file'],mask_path=case['mask_file'],mask_SHA256=case['mask_sha256'],
            source_commit=row['source_commit'],configuration_sha256=case['config_sha256'],scalar_archive=str(vp),
            native_grid_SHA256=gd,source_Vpp_per_output={m:row['normalizations'][m]['source_Vpp_per_output'] for m in base.MODES},
            saved_active_skin_contact_caps=row['normalizations']['skin_contact_only']['active_skin_contact_caps']))
    with (gzip.open(grid_path,'rt') if str(grid_path).endswith('.gz') else open(grid_path)) as stream:
        grid=np.loadtxt(stream,delimiter=',',skiprows=1)
    require(len(grid)==canonical_meta['cells'] and np.isfinite(grid).all() and np.all(np.sum(grid[:,:2]**2,axis=1)<625),'Finite D50 grid required')
    validate_pad_translation(cases[1]['projected_top_contact_pad_centres_mm'],cases[2]['projected_top_contact_pad_centres_mm'])
    base.verify_pins(pins)
    return dict(cases=cases,grid=grid,metadata=canonical_meta,input_sha256=pins,
        canonical_limits=rows[0]['normalizations']['skin_contact_only']['baseline_derived_numerical_limits'],
        source_volume_audit=str(Path(volume_audit).resolve()),source_screen=str(screen_path.resolve()),saved_screen=screen)


def render_model(model,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle,Rectangle
    output=Path(output).resolve();require(not output.exists() and (ROOT/'docs') in output.parents,'Unique new docs output required')
    output.mkdir(parents=True)
    result=dict(schema='task1-tangential-return-native-maps-v1',status='rendering',display_only=True,
        no_new_PDE=True,no_E_phi_decode=True,no_scoring_or_gate_recalculation=True,candidate_adopted=False,
        full_convergence_validated=False,experimentally_validated=False,coordinate_system='x/y horizontal mm; +z depth from skin surface z=0',
        primary_ROI='r<=5mm, depth15..20mm; frozen fractional cell weights unchanged',
        metric_definitions={'maxTIS':'fundamental2carrier maximum over2074 sampled directions; directional lower bound',
            'fixedTIS':'fundamental2carrier modulation in fixed(1/sqrt2,1/sqrt2,0) direction',
            'RMS':'all-carrier total vector field RMS, including square3h harmonics; distinct from modulation'},
        source_voltage_definition='Saved1Vpp whole square waveform per output, open/high-Z before50ohm; skin8 uses only saved common amplitude scale',
        skin8_definition='Eight original-square skin/contact numerical caps; no source-power or1Vpp ceiling; not human safety limits',
        interpretation='Display only. Tangential return translation remains unadopted; saved screen evidence is copied without recomputation. All prior convergence/contact holds remain.',
        source_volume_audit=model['source_volume_audit'],source_screen=model['source_screen'],saved_screen=model['saved_screen'],
        input_sha256=model['input_sha256'],canonical_limits=model['canonical_limits'],
        projected_pad_centres_definition='Markers show operative top-contact XY centres projected onto deepXY slice; they do not depict contacts at depth or reproduce mask polygons',
        implementation_files_SHA256={str(p):base.sha(p)for p in(Path(__file__).resolve(),Path(previous.__file__).resolve(),Path(base.__file__).resolve(),ROOT/'tests/test_task1_tangential_return_maps.py')},
        implementation_file_SHA256=base.sha(__file__),implementation_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        cases=[{k:v for k,v in c.items() if k!='arrays'} for c in model['cases']],color_limits={},artifacts={})
    try:
        for mode in base.MODES:
            for metric in base.METRICS:
                for deep in (False,True):
                    name='deep_ROI_display_clipped' if deep else 'global_native_range'
                    lo,hi=shared_color_limits(model['cases'],metric,mode,deep_roi=deep)
                    result['color_limits'][f'{name}/{mode}/{metric}']=dict(vmin=lo,vmax=hi,units='V/m',shared_cases=3,
                        scope='Primary-ROI positive-weight native cells; higher values display-clipped' if deep else 'All represented native cells',shared_planes=['XY','XZ'])
                    fig,axes=plt.subplots(2,3,figsize=(13,8),layout='constrained')
                    for col,case in enumerate(model['cases']):
                        slices=native_slices(model['grid'],model['metadata'],case['arrays'][metric]*case['scales'][mode])
                        result['native_slices']=dict(XY_actual_z_mm=slices['xy_actual_depth_mm'],XZ_actual_y_mm=slices['xz_actual_y_mm'])
                        for row,plane in enumerate(('xy','xz')):
                            ax=axes[row,col];yy=slices['y_edges_mm'] if plane=='xy' else slices['z_edges_mm']
                            image=ax.pcolormesh(slices['x_edges_mm'],yy,slices[plane],shading='flat',vmin=lo,vmax=hi,cmap='viridis',rasterized=True)
                            ax.set(xlabel='x (mm)',ylabel='y (mm)' if plane=='xy' else '+z depth (mm)')
                            if plane=='xy':
                                ax.add_patch(Circle((0,0),5,fill=False,color='white',linestyle='--',linewidth=.8));ax.set_aspect('equal')
                                for p,(px,py)in enumerate(case['projected_top_contact_pad_centres_mm']):
                                    ax.plot(px,py,marker='+'if p<2 else'x',color='tomato'if p<2 else'white',markersize=5)
                                    ax.annotate(str(p),(px,py),xytext=(3,3),textcoords='offset points',fontsize=7,color='white')
                                ax.set_title(case['label']+f"\nnative z={slices['xy_actual_depth_mm']:.4g}mm; scale={case['scales'][mode]:.6g}",fontsize=8)
                            else:
                                for z in (.1,5.1,10.1):ax.axhline(z,color='white',linestyle=':',linewidth=.6)
                                ax.axhline(0,color='white',linewidth=.8);ax.axhline(5,color='orange',linestyle='--',linewidth=.6)
                                half=math.sqrt(max(0,625-slices['xz_actual_y_mm']**2))
                                ax.add_patch(Rectangle((-half,15),2*half,5,fill=False,color='white',linestyle=':',linewidth=.7))
                                roi_half=math.sqrt(max(0,25-slices['xz_actual_y_mm']**2))
                                ax.add_patch(Rectangle((-roi_half,15),2*roi_half,5,fill=False,color='white',linestyle='--',linewidth=1))
                                ax.invert_yaxis();ax.set_title(f"native y={slices['xz_actual_y_mm']:.4g}mm; primaryROI dashed",fontsize=8)
                    fig.colorbar(image,ax=axes.ravel().tolist(),label=metric+' (V/m); shared three cases / both planes',shrink=.8)
                    fig.suptitle(f'{metric} / {mode} / {name}\n+z from skin0; SC0–0.1 / dermis0.1–5.1 / fat5.1–10.1 / muscle10.1–25.1mm; orange z=5mm')
                    path=output/f'{name}--{mode}--{metric}.png';fig.savefig(path,dpi=140);plt.close(fig)
                    result['artifacts'][path.name]=dict(path=str(path),SHA256=base.sha(path))
        base.verify_pins(model['input_sha256']);result.update(status='rendered_unadopted',inputs_unchanged=True)
        cards=[]
        for name,artifact in result['artifacts'].items():
            cards.append('<figure><figcaption>'+html.escape(name)+'</figcaption><a href="'+html.escape(name)+'"><img loading="lazy" src="'+html.escape(name)+'" alt="'+html.escape(name)+'"></a></figure>')
        content='<!doctype html><html lang="en"><meta charset="utf-8"><title>Tangential returns: saved native maps</title><style>body{font:16px system-ui;max-width:1400px;margin:2rem auto;padding:1rem}img{width:100%}figure{margin:2rem 0}figcaption{font-weight:bold}</style><h1>Tangential returns: saved native maps</h1><p>Original square / unrotated asymmetric parent / same parent with two common-GND returns shifted tangentially by(±4.375,±4.375)mm. Source pads, areas, rotations, outputs, commonGND and50Ω are preserved. Saved scalar display only; no new solve or scoring; no candidate adopted. XY markers are projected TOP contact centres, not contacts at depth or mask outlines.</p><p>Raw1Vpp and saved skin8 common-cap scale; global and explicitly clipped primary-ROI shared ranges. +z increases from skin0; primaryROI radius5mm/depth15–20mm. All3columns and both slices share each panel color range. Clipping changes display only.</p>'+''.join(cards)+'</html>'
        (output/'index.html').write_text(content)
        result['artifacts']['index.html']=dict(path=str(output/'index.html'),SHA256=base.sha(output/'index.html'))
    except BaseException as error:
        result.update(status='error',failure={'type':type(error).__name__,'message':str(error)})
        (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');raise
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--volume-audit',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--screen');args=parser.parse_args();require(not Path(args.output).exists(),'Preserve existing outputs');started=time.monotonic()
    result=render_model(load_model(args.volume_audit,args.screen),args.output)
    print(json.dumps(dict(status=result['status'],wall_seconds=time.monotonic()-started,output=str(Path(args.output).resolve()))))

if __name__=='__main__':main()
