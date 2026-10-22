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
import task1_perimeter_shell_registration as geometry

ROOT=base.ROOT
IDS=('baseline-square15-xy80','perimeter-shell225-notch-xy80','perimeter-shell225-inward0p625-xy80')
TRANSLATIONS=((.625,.625),(-.625,-.625),(-.625,.625),(.625,-.625))
LABELS=('Original four-square baseline','Fixed stepped perimeter shell','Same shell; all four pads moved inward')
require=base.require
shared_color_limits=base.shared_color_limits
native_slices=base.native_slices


def implementation_receipt():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    paths=(Path(__file__).resolve(),ROOT/'tests/test_task1_perimeter_inward_maps.py',
        Path(previous.__file__).resolve(),Path(base.__file__).resolve(),Path(geometry.__file__).resolve())
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
    require(len(rows)==3 and tuple(r.get('case_id') for r in rows)==IDS and
        all(r.get('adopted') is False and r.get('calculation_status')=='cached_native_scalar_audit_complete' for r in rows),
        'Exactly original square baseline, fixed shell control and same shell inward placement required')
    return rows


validate_modes=previous.validate_modes
validate_grid_contract=previous.validate_grid_contract


def validate_screen(screen,volume_path,volume_sha):
    screened=tuple(r.get('case_id')for r in screen.get('cases',[]))
    require(screen.get('schema')=='task1-candidate-screen-v1'and screen.get('status')=='screen_complete_not_adopted'and
        screen.get('candidate_adopted')is False and screen.get('input_volume_report')==dict(path=str(Path(volume_path).resolve()),SHA256=volume_sha)and
        screened in((IDS[2],),IDS[1:])and all(r.get('candidate_adopted')is False for r in screen['cases']),
        'Completed unadopted screen must bind the exact saved volume and new inward placement; cached shell screen may also be present')


def pad_centres_from_properties(text):
    config={k.strip():v.strip()for line in text.splitlines()if line.strip()and not line.lstrip().startswith('#')for k,v in[line.split('=',1)]}
    xy=np.asarray([[float(config[f'pad.{p}.x_mm']),float(config[f'pad.{p}.y_mm'])]for p in range(4)])
    require(xy.shape==(4,2)and np.isfinite(xy).all()and np.all(np.sum(xy*xy,axis=1)<625),'Finite operative four-pad XY centres insideD50 required')
    return xy


def validate_pad_translation(parent,new):
    parent=np.asarray(parent,float);new=np.asarray(new,float)
    require(parent.shape==new.shape==(4,2)and np.isfinite(parent).all()and np.isfinite(new).all()and
        np.allclose(new-parent,TRANSLATIONS,rtol=0,atol=1e-12)and
        np.all(np.sign(parent)==np.sign(new))and np.all(abs(new)<abs(parent)),
        'All four physical pads must move by the registered0.625mm per-coordinate inward translation; no pad exchange')


def validate_contact_shapes(case):
    """Read only SHA-bound physical descriptors; never draw their bounding boxes as contacts."""
    ident=case.get('id');pads=case.get('design',{}).get('pads',[])
    require(ident in IDS and len(pads)==4,'Exact saved physical four-pad contact design required')
    shapes=[]
    for p,pad in enumerate(pads):
        require(pad.get('pad')==p and pad.get('role')==('signal'if p<2 else'common_gnd_return')and
            pad.get('source_output')==(p if p<2 else None)and pad.get('rotation_deg')==0,
            'Physical pad identity, output/return role and zero operative rotation required')
        centroid=np.asarray(pad.get('center_mm'),float)
        require(centroid.shape==(2,)and np.isfinite(centroid).all(),'Finite physical area-centroid coordinates required')
        if ident==IDS[0]:
            require(pad.get('shape')=='rectangle'and pad.get('width_mm')==pad.get('height_mm')==15 and
                pad.get('analytic_area_mm2')==225,'Original225mm2 rectangular contact required')
            x,y=centroid;half=7.5
            polygon=[[x-half,y-half],[x+half,y-half],[x+half,y+half],[x-half,y+half]]
            bboxcentre=centroid.tolist();role='Actual15x15mm rectangle; area centroid and bounding-box centre coincide'
        else:
            require(case.get('geometry_kind')=='fixed_native_face_union'and case.get('physical_geometry_frozen')is True and
                case.get('future_grid_reranking_allowed')is False and pad.get('shape')=='masked_face_union'and
                pad.get('geometry_primitive')=='fixed_union_of_native_full_face_rectangles'and
                pad.get('native_face_h_mm')==.625 and pad.get('native_face_count')==576 and
                all(pad.get(k)==225 for k in('area_mm2','analytic_area_mm2','polygon_area_mm2'))and
                pad.get('physical_outline_frozen')is True and pad.get('smooth_annular_arc_claimed')is False and
                pad.get('convex_hull_used')is False,'Frozen576-full-face nonconvex contact required; no smooth arc or convex hull')
            faces=pad.get('native_face_indices',[])
            require(len(faces)==576 and all(isinstance(q,list)and len(q)==2 and all(type(v)is int and 0<=v<80 for v in q)for q in faces)and
                len({tuple(q)for q in faces})==576,'Exactly576 unique native contact faces required')
            polygon=pad.get('polygon_mm');loops=pad.get('boundary_loops_mm')
            require(isinstance(polygon,list)and loops==[polygon]and polygon==geometry.boundary_loop({tuple(q)for q in faces}),
                'Contact outline must be the actual single nonconvex native-face boundary, not a bounding box')
            coords=np.asarray(polygon,float);bbox=[float(coords[:,0].min()),float(coords[:,1].min()),float(coords[:,0].max()),float(coords[:,1].max())]
            actual_centroid=np.mean([[-25+(i+.5)*.625,-25+(j+.5)*.625]for i,j in faces],axis=0)
            bboxcentre=[(bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2]
            require(np.allclose(centroid,actual_centroid,rtol=0,atol=1e-12)and
                np.allclose(pad.get('centroid_mm',[]),centroid,rtol=0,atol=1e-12)and pad.get('bounding_box_mm')==bbox and
                pad.get('bounding_box_center_mm')==bboxcentre and pad.get('width_mm')==bbox[2]-bbox[0]and pad.get('height_mm')==bbox[3]-bbox[1],
                'Area centroid, bounding-box centre and spans must retain their distinct actual geometric roles')
            role=pad.get('dimension_fields_role')
            require(isinstance(role,str)and bool(role.strip()),'Honest bounding-box descriptor role required')
        coords=np.asarray(polygon,float)
        require(coords.ndim==2 and coords.shape[1]==2 and len(coords)>=4 and np.isfinite(coords).all()and
            np.all(np.sum(coords**2,axis=1)<625),'Finite physical contact vertices strictly inside fixedD50 required')
        area=abs(float(np.sum(coords[:,0]*np.roll(coords[:,1],-1)-np.roll(coords[:,0],-1)*coords[:,1])))/2
        require(math.isclose(area,225.,rel_tol=0,abs_tol=1e-9),'Actual drawn physical contact area must remain225mm2')
        shapes.append(dict(pad=p,shape=pad['shape'],role=pad['role'],source_output=pad['source_output'],area_mm2=area,
            centroid_mm=centroid.tolist(),bounding_box_center_mm=bboxcentre,polygon_mm=polygon,boundary_loops_mm=[polygon],dimension_fields_role=role))
    return shapes


def validate_contact_translation(parent,new):
    require(len(parent)==len(new)==4,'Both fixed outlines need all four physical pads')
    validate_pad_translation([p['centroid_mm']for p in parent],[p['centroid_mm']for p in new])
    for p,(old,current,(dx,dy))in enumerate(zip(parent,new,TRANSLATIONS)):
        expected=[[x+dx,y+dy]for x,y in old['polygon_mm']]
        require(old['pad']==current['pad']==p and old['role']==current['role']and old['source_output']==current['source_output']and
            old['shape']==current['shape']=='masked_face_union'and current['polygon_mm']==expected and
            current['boundary_loops_mm']==[expected]and current['area_mm2']==old['area_mm2']==225.,
            'Every source and return must preserve the exact physical nonconvex outline under rigid inward translation')


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
    validate_pad_translation(cases[1]['projected_top_contact_pad_centres_mm'],cases[2]['projected_top_contact_pad_centres_mm'])
    validate_contact_translation(cases[1]['top_contact_shapes'],cases[2]['top_contact_shapes'])
    base.verify_pins(pins)
    return dict(cases=cases,grid=grid,metadata=canonical_meta,input_sha256=pins,
        canonical_limits=rows[0]['normalizations']['skin_contact_only']['baseline_derived_numerical_limits'],
        source_volume_audit=str(Path(volume_audit).resolve()),source_screen=str(screen_path.resolve()),saved_screen=screen)


def render_contacts(model,output,plt,Circle,Polygon):
    """Separate z=0 contact panel; no scalar or E/phi evaluation."""
    fig,axes=plt.subplots(1,3,figsize=(13,4.6),layout='constrained')
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
    fig.suptitle('Physical contact contours: D50; four225mm² pads; two outputs / one common GND\nStepped face-union loops are fixed physical outlines. + = area centroid; bbox spans are not contact outlines.')
    path=Path(output)/'top-XY-physical-contact-outlines.png';fig.savefig(path,dpi=140);plt.close(fig);return path


def render_model(model,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle,Rectangle,Polygon
    output=Path(output).resolve();require(not output.exists() and (ROOT/'docs') in output.parents,'Unique new docs output required')
    output.mkdir(parents=True)
    result=dict(schema='task1-perimeter-inward-native-maps-v1',status='rendering',display_only=True,
        no_new_PDE=True,no_E_phi_decode=True,no_scoring_or_gate_recalculation=True,candidate_adopted=False,
        full_convergence_validated=False,experimentally_validated=False,coordinate_system='x/y horizontal mm; +z depth from skin surface z=0',
        primary_ROI='r<=5mm, depth15..20mm; frozen fractional cell weights unchanged',
        metric_definitions={'maxTIS':'fundamental2carrier maximum over2074 sampled directions; directional lower bound',
            'fixedTIS':'fundamental2carrier modulation in fixed(1/sqrt2,1/sqrt2,0) direction',
            'RMS':'all-carrier total vector field RMS, including square3h harmonics; distinct from modulation'},
        source_voltage_definition='Saved1Vpp whole square waveform per output, open/high-Z before50ohm; skin8 uses only saved common amplitude scale',
        skin8_definition='Eight original-square skin/contact numerical caps; no source-power or1Vpp ceiling; not human safety limits',
        interpretation='Display only. Rigid inward placement remains unadopted; rim clearance and pad separation change together, without an isolated rim-effect claim; saved screen evidence is copied without recomputation. All prior convergence/contact holds remain.',
        source_volume_audit=model['source_volume_audit'],source_screen=model['source_screen'],saved_screen=model['saved_screen'],
        input_sha256=model['input_sha256'],canonical_limits=model['canonical_limits'],
        projected_pad_centres_definition='Markers show operative top-contact XY centres projected onto deepXY slice; they do not depict contacts at depth or reproduce mask polygons',
        **implementation_receipt(),
        cases=[{k:v for k,v in c.items() if k!='arrays'} for c in model['cases']],color_limits={},artifacts={})
    try:
        contact_path=render_contacts(model,output,plt,Circle,Polygon)
        result['artifacts'][contact_path.name]=dict(path=str(contact_path),SHA256=base.sha(contact_path))
        result['top_contact_geometry']=dict(skin_surface_z_mm=0,actual_physical_outline=True,deep_XY_contacts_are_projections_only=True,
            centroid_markers='Actual contact area centroids; shell bbox centres/spans are metadata only and not contact outlines',
            total_area_mm2_each_case=900,source_return_pad_ids_preserved=True,common_GND_nodes=1,independent_outputs=2)
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
                                ax.axhspan(5.1,10.1,facecolor='none',hatch='///',edgecolor=(1.,1.,1.,.22),linewidth=0)
                                ax.text(-24,7.6,'fat5.1–10.1mm',color='white',fontsize=6)
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
        content='<!doctype html><html lang="en"><meta charset="utf-8"><title>Perimeter inward placement: saved native maps</title><style>body{font:16px system-ui;max-width:1400px;margin:2rem auto;padding:1rem}img{width:100%}figure{margin:2rem 0}figcaption{font-weight:bold}</style><h1>Perimeter inward placement: saved native maps</h1><p>Original square / fixed stepped perimeter shell / the same four physical outlines moved0.625mm per-coordinate toward the origin. All source and return pads move, while each225mm² area, role, rotation, two outputs, commonGND and50Ω remain fixed. The position contrast changes both rim clearance and separation: shell0.02345mm/3.75mm to inward0.85040mm/2.5mm. It does not isolate a rim effect. Saved scalar display only; no new solve or scoring; no candidate adopted. The first panel shows actual TOP physical contacts at skin z=0, from SHA-bound registration design loops; stepped shell outlines are native-face unions, without smoothing, convex hulls or bounding-box substitutes. Plus markers are actual area centroids; shell width/height are bounding-box spans only. Deep XY markers are projected TOP centroids, not contacts at depth or mask outlines.</p><p>Raw1Vpp and saved skin8 common-cap scale; global and explicitly clipped primary-ROI shared ranges. +z increases from skin0; primaryROI radius5mm/depth15–20mm. All3columns and both slices share each panel color range. Clipping changes display only.</p>'+''.join(cards)+'</html>'
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
