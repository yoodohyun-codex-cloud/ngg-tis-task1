"""Display two SHA-bound saved scalar volumes; no PDE, E/phi or scoring.

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
import task1_rounded_fullface_registration as geometry
import task1_perimeter_inward_maps as inward

ROOT=base.ROOT
IDS=('baseline-square15-xy80','rounded-fullface225-xy80')
LABELS=('Original four-square baseline','Same centres/areas; fixed rounded full-face contour')
require=base.require
shared_color_limits=base.shared_color_limits
native_slices=base.native_slices


def implementation_receipt():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    paths=(Path(__file__).resolve(),ROOT/'tests/test_task1_rounded_fullface_maps.py',
        Path(previous.__file__).resolve(),Path(base.__file__).resolve(),Path(geometry.__file__).resolve(),
        Path(geometry.parent.__file__).resolve(),Path(inward.__file__).resolve())
    refs={}
    for path in paths:
        require(path.read_bytes()==subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT),
            'Commit consumed map sources/helpers/tests before rendering: '+str(path))
        refs[str(path)]=base.sha(path)
    return dict(implementation_files_SHA256=refs,implementation_file_SHA256=refs[str(Path(__file__).resolve())],implementation_git_commit=commit)


def validate_audit(summary):
    require(summary.get('schema')=='task1-volume-selectivity-v1' and summary.get('status')=='calculated_unadopted' and
        summary.get('inputs_unchanged') is True and summary.get('selected_for_adoption')==[],
        'Terminal unchanged unadopted saved volume audit required')
    rows=summary.get('cases',[])
    require(len(rows)==2 and tuple(r.get('case_id') for r in rows)==IDS and
        all(r.get('adopted') is False and r.get('calculation_status')=='cached_native_scalar_audit_complete' for r in rows),
        'Exactly original-square and same-centre/area rounded full-face comparison required')
    return rows


validate_modes=previous.validate_modes
validate_grid_contract=previous.validate_grid_contract


def validate_screen(screen,volume_path,volume_sha):
    require(screen.get('schema')=='task1-candidate-screen-v1'and screen.get('status')=='screen_complete_not_adopted'and
        screen.get('candidate_adopted')is False and screen.get('input_volume_report')==dict(path=str(Path(volume_path).resolve()),SHA256=volume_sha)and
        tuple(r.get('case_id')for r in screen.get('cases',[]))==(IDS[1],)and screen['cases'][0].get('candidate_adopted')is False,
        'Completed unadopted rounded screen must bind this exact saved volume report')
    checks=screen['cases'][0].get('checks',[]);targets={'primary_maxTIS_mean','primary_maxTIS_p10'}
    require(len(checks)==8 and len({c.get('name')for c in checks})==8 and
        {c.get('name')for c in checks if c.get('passed')is False}==targets and
        all(c.get('passed')is True for c in checks if c.get('name')not in targets),
        'Saved eight checks must retain two target failures and six off-target passes; no screen recalculation')


pad_centres_from_properties=inward.pad_centres_from_properties


def validate_contact_shapes(case):
    if case.get('id')==IDS[0]:
        result=inward.validate_contact_shapes(case)
        for pad in result:pad['perimeter_mm']=60.
        return result
    require(case.get('id')==IDS[1],'Only the registered same-centre rounded full-face source is displayed')
    design=case.get('design',{});pads=design.get('pads',[])
    require(len(pads)==4 and all(case.get(k)==v and design.get(k)==v for k,v in geometry.COMMON.items()),
        'Rounded fixed-face/D4/cutoff/perimeter/unchanged-centre/area metadata must remain source-bound')
    expected=geometry.rounded_faces();result=[]
    for p,(pad,centre)in enumerate(zip(pads,geometry.CENTRES)):
        require(pad.get('pad')==p and pad.get('role')==('signal'if p<2 else'common_gnd_return')and
            pad.get('source_output')==(p if p<2 else None)and pad.get('rotation_deg')==0 and pad.get('center_mm')==list(centre)and
            pad.get('centroid_mm')==list(centre)and pad.get('shape')=='masked_face_union'and
            pad.get('geometry_primitive')=='fixed_union_of_native_full_face_rectangles'and
            pad.get('native_face_h_mm')==.625 and pad.get('native_face_count')==576 and
            pad.get('native_face_indices')==[list(ij)for ij in expected[p]]and
            all(pad.get(k)==225 for k in('area_mm2','analytic_area_mm2','polygon_area_mm2'))and
            pad.get('physical_outline_frozen')is True and pad.get('smooth_circle_claimed')is False and pad.get('convex_hull_used')is False and
            pad.get('local_D4_symmetric')is True,'Exact576 faces, all16 radial ties, D4 symmetry, pad identity and physical area required')
        cells={tuple(ij)for ij in pad['native_face_indices']};polygon=geometry.parent.boundary_loop(cells)
        require(pad.get('polygon_mm')==polygon and pad.get('boundary_loops_mm')==[polygon],
            'Draw the actual fixed native-face boundary, never a smooth circle, hull or bounding box')
        coords=np.asarray(polygon,float);bbox=[float(coords[:,0].min()),float(coords[:,1].min()),float(coords[:,0].max()),float(coords[:,1].max())]
        perimeter=math.fsum(math.hypot(x-u,y-v)for(x,y),(u,v)in zip(polygon,polygon[1:]+polygon[:1]))
        area=abs(float(np.sum(coords[:,0]*np.roll(coords[:,1],-1)-np.roll(coords[:,0],-1)*coords[:,1])))/2
        require(np.isfinite(coords).all()and np.all(np.sum(coords**2,axis=1)<625)and area==225 and perimeter==70 and
            pad.get('physical_outline_perimeter_mm')==70 and pad.get('bounding_box_mm')==bbox and pad.get('bounding_box_center_mm')==list(centre)and
            pad.get('width_mm')==pad.get('height_mm')==17.5,'Actual225mm2 stepped70mm contour and same-centre17.5mm bbox descriptors required')
        role=pad.get('dimension_fields_role');require(isinstance(role,str)and role.strip(),'Honest bbox dimension role required')
        result.append(dict(pad=p,shape='masked_face_union',role=pad['role'],source_output=pad['source_output'],area_mm2=225.,
            centroid_mm=list(centre),bounding_box_center_mm=list(centre),polygon_mm=polygon,boundary_loops_mm=[polygon],dimension_fields_role=role,perimeter_mm=70.))
    return result


def validate_same_centres(baseline,rounded):
    require(len(baseline)==len(rounded)==4 and all(a['pad']==b['pad']==p and a['role']==b['role']and
        a['source_output']==b['source_output']and a['centroid_mm']==b['centroid_mm']==list(geometry.CENTRES[p])and
        a['area_mm2']==b['area_mm2']==225 and a['perimeter_mm']==60 and b['perimeter_mm']==70 for p,(a,b)in enumerate(zip(baseline,rounded))),
        'Same four physical centres,225mm2 areas and wiring with square60mm versus stepped70mm contour required')


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
        centres=pad_centres_from_properties(Path(case['config_file']).read_text());contact_shapes=validate_contact_shapes(case)
        require(np.allclose(centres,[p['centroid_mm']for p in contact_shapes],rtol=0,atol=1e-12),'Operative config contact centroids differ from SHA-bound physical design')
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
            projected_top_contact_pad_centres_mm=centres.tolist(),top_contact_shapes=contact_shapes,physical_design_registration_path=str(run/'preregistration.json'),
            physical_design_registration_SHA256=pins[str(run/'preregistration.json')],operative_config_path=case['config_file'],mask_path=case['mask_file'],mask_SHA256=case['mask_sha256'],
            source_commit=row['source_commit'],configuration_sha256=case['config_sha256'],scalar_archive=str(vp),
            native_grid_SHA256=gd,source_Vpp_per_output={m:row['normalizations'][m]['source_Vpp_per_output'] for m in base.MODES},
            saved_active_skin_contact_caps=row['normalizations']['skin_contact_only']['active_skin_contact_caps']))
    with (gzip.open(grid_path,'rt') if str(grid_path).endswith('.gz') else open(grid_path)) as stream:
        grid=np.loadtxt(stream,delimiter=',',skiprows=1)
    require(len(grid)==canonical_meta['cells'] and np.isfinite(grid).all() and np.all(np.sum(grid[:,:2]**2,axis=1)<625),'Finite D50 grid required')
    validate_same_centres(cases[0]['top_contact_shapes'],cases[1]['top_contact_shapes'])
    base.verify_pins(pins)
    return dict(cases=cases,grid=grid,metadata=canonical_meta,input_sha256=pins,
        canonical_limits=rows[0]['normalizations']['skin_contact_only']['baseline_derived_numerical_limits'],
        source_volume_audit=str(Path(volume_audit).resolve()),source_screen=str(screen_path.resolve()),saved_screen=screen)


def render_contacts(model,output,plt,Circle,Polygon):
    """Separate z=0 contact panel; no scalar or E/phi evaluation."""
    fig,axes=plt.subplots(1,2,figsize=(10,4.6),layout='constrained')
    for ax,case in zip(axes,model['cases']):
        ax.add_patch(Circle((0,0),25,fill=False,color='black',linewidth=1))
        ax.add_patch(Circle((0,0),5,fill=False,color='gray',linestyle='--',linewidth=.7))
        for pad in case['top_contact_shapes']:
            p=pad['pad'];color=('tomato','royalblue','silver','silver')[p]
            ax.add_patch(Polygon(pad['polygon_mm'],closed=True,facecolor=color,edgecolor='black',linewidth=.7,alpha=.8))
            x,y=pad['centroid_mm'];ax.plot(x,y,'k+',markersize=5)
            label=f'pad{p}: out{p}'if p<2 else f'pad{p}: GND'
            ax.annotate(label,(x,y),xytext=(3,3),textcoords='offset points',fontsize=6)
        ax.set(xlim=(-26,26),ylim=(-26,26),xlabel='x (mm)',ylabel='y (mm)',title=case['label']+'\nactual TOP contact at skin z=0')
        ax.set_aspect('equal');ax.grid(alpha=.15)
    fig.suptitle('Same physical centres and225mm²/pad; two outputs / one common GND\nSquare contour60mm vs fixed D4 stepped contour70mm; not a smooth circle or perimeter reduction.')
    path=Path(output)/'top-XY-physical-contact-outlines.png';fig.savefig(path,dpi=140);plt.close(fig);return path


def render_model(model,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle,Rectangle,Polygon
    output=Path(output).resolve();require(not output.exists() and (ROOT/'docs') in output.parents,'Unique new docs output required')
    output.mkdir(parents=True)
    result=dict(schema='task1-rounded-fullface-native-maps-v1',status='rendering',display_only=True,
        no_new_PDE=True,no_E_phi_decode=True,no_scoring_or_gate_recalculation=True,candidate_adopted=False,
        full_convergence_validated=False,experimentally_validated=False,coordinate_system='x/y horizontal mm; +z depth from skin surface z=0',
        primary_ROI='r<=5mm, depth15..20mm; frozen fractional cell weights unchanged',
        metric_definitions={'maxTIS':'fundamental2carrier maximum over2074 sampled directions; directional lower bound',
            'fixedTIS':'fundamental2carrier modulation in fixed(1/sqrt2,1/sqrt2,0) direction',
            'RMS':'all-carrier total vector field RMS, including square3h harmonics; distinct from modulation'},
        source_voltage_definition='Saved1Vpp whole square waveform per output, open/high-Z before50ohm; skin8 uses only saved common amplitude scale',
        skin8_definition='Eight original-square skin/contact numerical caps; no source-power or1Vpp ceiling; not human safety limits',
        interpretation='Display only. Same-centre/area rounded full-face condition passes six off-target screens but fails both target screens, so no adoption. The70mm stepped contour exceeds square60mm; not a smooth circle, perimeter reduction or isolated edge-effect proof. All convergence/contact/direction holds remain.',
        source_volume_audit=model['source_volume_audit'],source_screen=model['source_screen'],saved_screen=model['saved_screen'],
        input_sha256=model['input_sha256'],canonical_limits=model['canonical_limits'],
        projected_pad_centres_definition='Markers show operative top-contact XY centres projected onto deepXY slice; they do not depict contacts at depth or reproduce mask polygons',
        **implementation_receipt(),
        cases=[{k:v for k,v in c.items() if k!='arrays'} for c in model['cases']],color_limits={},artifacts={})
    try:
        contact_path=render_contacts(model,output,plt,Circle,Polygon)
        result['artifacts'][contact_path.name]=dict(path=str(contact_path),SHA256=base.sha(contact_path))
        result['top_contact_geometry']=dict(skin_surface_z_mm=0,actual_physical_outline=True,deep_XY_contacts_are_projections_only=True,
            centroid_markers='Actual identical contact area centroids; bbox spans are metadata only and not contact outlines',
            total_area_mm2_each_case=900,source_return_pad_ids_preserved=True,common_GND_nodes=1,independent_outputs=2)
        for mode in base.MODES:
            for metric in base.METRICS:
                for deep in (False,True):
                    name='deep_ROI_display_clipped' if deep else 'global_native_range'
                    lo,hi=shared_color_limits(model['cases'],metric,mode,deep_roi=deep)
                    result['color_limits'][f'{name}/{mode}/{metric}']=dict(vmin=lo,vmax=hi,units='V/m',shared_cases=2,
                        scope='Primary-ROI positive-weight native cells; higher values display-clipped' if deep else 'All represented native cells',shared_planes=['XY','XZ'])
                    fig,axes=plt.subplots(2,2,figsize=(10,8),layout='constrained')
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
                                ax.axhspan(5.1,10.1,facecolor='none',hatch='///',edgecolor=(1.,1.,1.,.22),linewidth=0)
                                ax.text(-24,7.6,'fat5.1–10.1mm',color='white',fontsize=6)
                                ax.axhline(0,color='white',linewidth=.8);ax.axhline(5,color='orange',linestyle='--',linewidth=.6)
                                half=math.sqrt(max(0,625-slices['xz_actual_y_mm']**2))
                                ax.add_patch(Rectangle((-half,15),2*half,5,fill=False,color='white',linestyle=':',linewidth=.7))
                                roi_half=math.sqrt(max(0,25-slices['xz_actual_y_mm']**2))
                                ax.add_patch(Rectangle((-roi_half,15),2*roi_half,5,fill=False,color='white',linestyle='--',linewidth=1))
                                ax.invert_yaxis();ax.set_title(f"native y={slices['xz_actual_y_mm']:.4g}mm; primaryROI dashed",fontsize=8)
                    fig.colorbar(image,ax=axes.ravel().tolist(),label=metric+' (V/m); shared two cases / both planes',shrink=.8)
                    fig.suptitle(f'{metric} / {mode} / {name}\n+z from skin0; SC0–0.1 / dermis0.1–5.1 / fat5.1–10.1 / muscle10.1–25.1mm; orange z=5mm')
                    path=output/f'{name}--{mode}--{metric}.png';fig.savefig(path,dpi=140);plt.close(fig)
                    result['artifacts'][path.name]=dict(path=str(path),SHA256=base.sha(path))
        base.verify_pins(model['input_sha256']);result.update(status='rendered_unadopted',inputs_unchanged=True,heatmap_PNG_count=12,top_contact_PNG_count=1)
        cards=[]
        for name,artifact in result['artifacts'].items():
            cards.append('<figure><figcaption>'+html.escape(name)+'</figcaption><a href="'+html.escape(name)+'"><img loading="lazy" src="'+html.escape(name)+'" alt="'+html.escape(name)+'"></a></figure>')
        content='<!doctype html><html lang="en"><meta charset="utf-8"><title>Rounded full-face shape: saved native maps</title><style>body{font:16px system-ui;max-width:1400px;margin:2rem auto;padding:1rem}img{width:100%}figure{margin:2rem 0}figcaption{font-weight:bold}</style><h1>Rounded full-face shape: saved native maps</h1><p>Original square versus fixed rounded full-face union: four identical centres and225mm²/pad, two outputs, commonGND and50Ω. The new contact comprises576full native faces with D4 symmetry and all16cutoff ties; its exact stepped contour is70mm, exceeding the square60mm. It is not a smooth circle or a perimeter reduction. The saved eight-screen result retains six off-target passes and both target failures: no candidate adoption or full convergence. The top panel draws actual SHA-bound physical contact outlines at skin z=0, with no smoothing, hulls or bounding-box substitutes. DeepXY markers project top contact centres; they are not electrodes at depth.</p><p>Twelve heatmaps: raw1Vpp and saved skin8 common-cap scale, maxTIS/fixedTIS/all-carrierRMS, global and explicitly clipped primary-ROI ranges. Both columns and XY/XZ planes share each panel color range. +z increases from skin0; primaryROI radius5mm/depth15–20mm. Fat5.1–10.1mm is hatched; high fields at layer interfaces do not establish deep focus. Display clipping changes no source result. Numerical cutoffs are not physiological thresholds.</p>'+''.join(cards)+'</html>'
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
    implementation_receipt()
    result=render_model(load_model(args.volume_audit,args.screen),args.output)
    print(json.dumps(dict(status=result['status'],wall_seconds=time.monotonic()-started,output=str(Path(args.output).resolve()))))

if __name__=='__main__':main()
