"""Display three SHA-bound SC4 contact-uncertainty scalar archives only.

No data reads at import. The external caller owns both execution locks, CPU1,
120s wall/3GiB RSS, 2GiB disk reserve and the validated cumulative ledger.
No PDE, E/phi decoding, normalization fitting, scoring or gate recomputation.
"""
from __future__ import annotations
import argparse
import gzip
import html
import json
import math
from pathlib import Path
import time
import subprocess
import numpy as np
import task1_rounded_fullface_maps as contours

base=contours.base
ROOT=base.ROOT
require=base.require
MODES=base.MODES
METRICS=base.METRICS
FACTORS=(1.,.5,2.)
NATIVE_IDS=('rounded-fullface225-sc4-xy80','rounded-fullface225-contact0p5-sc4-xy80','rounded-fullface225-contact2-sc4-xy80')
SELECTED='rounded-opt-e7b3bf639935'
LABELS=('Nominal SC4 contact Z','SC4 contact Z × 0.5','SC4 contact Z × 2')
MAX_OUTPUT_BYTES=32*1024**2
shared_color_limits=base.shared_color_limits
native_slices=base.native_slices


def implementation_receipt():
    receipt=contours.implementation_receipt()
    commit=receipt['implementation_git_commit'];refs=dict(receipt['implementation_files_SHA256'])
    for path in (Path(__file__).resolve(),ROOT/'tests/test_task1_rounded_contact_maps.py'):
        require(path.read_bytes()==subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT),
            'Commit new map helper/tests before guarded rendering: '+str(path))
        refs[str(path)]=base.sha(path)
    return dict(implementation_git_commit=commit,implementation_files_SHA256=refs,
        implementation_file_SHA256=refs[str(Path(__file__).resolve())])


def validate_summary(summary):
    require(summary.get('schema')=='task1-rounded-contact-sensitivity-v1' and
        summary.get('status')=='calculated_unadopted' and summary.get('inputs_unchanged')is True and
        summary.get('candidate_adopted')is False and summary.get('new_PDE')==0 and
        summary.get('nominal_SC4_result_reused_without_recalculation')is True and
        summary.get('nominal_SC4_native_array_decode')is False and
        summary.get('relative_change_acceptance_threshold')is None,
        'Terminal unchanged paired contact diagnostic required; no acceptance threshold invented')
    rows=summary.get('conditions',[])
    require(len(rows)==2 and tuple(r.get('native_contact_case_id')for r in rows)==NATIVE_IDS[1:] and
        tuple(r.get('complex_specific_contact_impedance_factor')for r in rows)==FACTORS[1:] and
        all(r.get('status')=='calculated_unadopted'for r in rows),
        'Exactly registered contact Z factors0.5/2 in order required')
    return rows


def validate_grid_contract(meta):
    expected=dict(cells=361728,h_xy_mm=.625,radius_mm=25.,total_depth_mm=25.1,channels=2,sc_cells=4,
        bulk_layer_counts=[14,14,40],frequencies_Hz=[3000,3030,9000,9090])
    require(all(meta.get(k)==v for k,v in expected.items()) and
        meta.get('tissue_boundaries_mm')==[0,.1,5.1,10.1,25.1],
        'Identical D50/XY.625/SC4/bulk14,14,40 native grid required')


def validate_conditions(conditions,selected_command):
    require(len(conditions)==3 and tuple(c.get('source_case_id')for c in conditions)==NATIVE_IDS,
        'Nominal SC4 plus two contact-scaled SC4 conditions required')
    nominal=conditions[0];expected_coeff=selected_command.get('raw_coefficient_vectors')
    require(selected_command.get('condition_id')==SELECTED and expected_coeff==nominal.get('coefficient_vectors') and
        selected_command.get('raw_source_Vpp_intervals_V')==nominal.get('source_waveform',{}).get('source_Vpp_intervals_V'),
        'Exact selected SC2 e7 command must bind nominal SC4')
    require(isinstance(expected_coeff,dict)and set(expected_coeff)=={str(f)for f in(3000,3030,9000,9090)} and
        all(set(v)=={'real','imaginary'}and all(isinstance(v[k],list)and len(v[k])==2 and
            all(type(x)in(int,float)and math.isfinite(x)for x in v[k])for k in('real','imaginary'))for v in expected_coeff.values())and
        all(x==0 for f in('9000','9090')for k in('real','imaginary')for x in expected_coeff[f][k]),
        'Explicit finite two-output coefficients at four native frequencies and zero harmonics required')
    scales=None
    for index,c in enumerate(conditions):
        schema='task1-rounded-sc4-sensitivity-condition-v1'if index==0 else'task1-rounded-contact-sensitivity-condition-v1'
        require(c.get('schema')==schema and c.get('status')=='calculated_unadopted'and
            c.get('candidate_adopted')is False and c.get('source_geometry_unchanged')is True and
            c.get('same_source_coefficients_and_whole_Vpp')is True and c.get('selected_SC2_condition_id')==SELECTED and
            c.get('coefficient_vectors')==expected_coeff and c.get('active_frequencies_Hz')==[3000,3030]and
            c.get('harmonics_active')is False and c.get('source_waveform')==nominal.get('source_waveform'),
            'Terminal same selected command/whole-wave Vpp/geometry required')
        circuit=c.get('source_circuit',{})
        require(circuit.get('n_pads')==4 and circuit.get('n_outputs')==2 and circuit.get('n_return_nodes')==1 and
            circuit.get('source_resistance_ohm')==50 and circuit.get('return_topology')=='all_return_pads_ideal_common_GND'and
            circuit.get('pad_to_node')=={'0':'out0','1':'out1','2':'GND','3':'GND'},
            'Four physical pads/two outputs/common GND50ohm required')
        modes=c.get('fixed_SC2_amplitude_modes',{})
        require(set(modes)=={'raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin'},
            'Five explicitly frozen historical SC2 amplitudes required')
        for mode,n in modes.items():
            require(type(n.get('amplitude_scale'))in(int,float)and math.isfinite(n['amplitude_scale'])and n['amplitude_scale']>0 and
                n.get('historical_SC2_mode_id')==mode and n.get('normalization_scope')=='frozen_SC2_amplitude_no_SC4_rematch'and
                n.get('SC4_skin_caps_rematched')is False and n.get('matches_SC2_current_on_SC4')is False and
                n.get('matches_SC2_power_on_SC4')is False,
                'Frozen SC2 amplitudes cannot silently become SC4/contact rematches')
        require(all(n['amplitude_scale']==nominal['fixed_SC2_amplitude_modes'][m]['amplitude_scale'] and
            n.get('actual_source_Vpp_intervals_V')==nominal['fixed_SC2_amplitude_modes'][m].get('actual_source_Vpp_intervals_V')for m,n in modes.items()),
            'All five historical amplitudes/source intervals must remain unchanged')
        current={m:modes[m]['amplitude_scale']for m in MODES}
        require(current['raw_1Vpp']==1 and current['skin_contact_only']==selected_command.get('SC2_skin8_amplitude_scale'),
            'Use saved raw1 and exact historical SC2skin8 amplitude only')
        if scales is None:scales=current
        require(current==scales,'Three primary maps must share identical frozen SC2 amplitudes')
        if index:
            contract=c.get('contact_configuration_contract',{})
            require(c.get('complex_specific_contact_impedance_factor')==FACTORS[index]and
                contract.get('complex_specific_contact_impedance_factor')==FACTORS[index]and
                contract.get('additional_Rs_subtraction')is False and contract.get('contact_area_rescaling')is False and
                contract.get('SC_cells')==4,'Contact scale must not add Rs subtraction or contact-area rescaling')
    return [dict(scales)for _ in conditions]


def validate_config_contrast(before,after,factor):
    require(before.keys()==after.keys()and before.get('validation.sc_cells')==after.get('validation.sc_cells')=='4'and
        before.get('mask.sha256')==after.get('mask.sha256'),'Same SC4 schema/physical mask required')
    zkeys={f'z.{f}.{part}'for f in(3000,3030,9000,9090)for part in('re','im')}
    require(all(before[k]==after[k]for k in before if k not in zkeys|{'mask.path'}),
        'Only complex specific contact Z and identical mask path alias may change')
    require(all(k in before and math.isfinite(float(before[k]))and math.isfinite(float(after[k]))and
        math.isclose(float(after[k]),float(before[k])*factor,rel_tol=1e-12,abs_tol=1e-15)for k in zkeys),
        'Every real/imaginary specific contact impedance must receive declared factor')


def load_model(summary_path):
    """Decode only three scalar NPZs and one same-grid CSV after metadata binding."""
    pins={};summary_path=Path(summary_path).resolve();summary=base.bound_json(summary_path,pins);entries=validate_summary(summary)
    declared=dict(summary['input_sha256'])
    def read_ref(ref):return base.bound_json(ref['path'],pins,ref['SHA256'])
    nominal_summary=read_ref(summary['nominal_SC4_result']['summary']);nominal=read_ref(summary['nominal_SC4_result']['condition'])
    require(nominal_summary.get('schema')=='task1-rounded-sc4-sensitivity-v1'and
        nominal_summary.get('status')=='calculated_unadopted'and nominal_summary.get('inputs_unchanged')is True,
        'Terminal unchanged nominal SC4 result required')
    for path,digest in nominal_summary['input_sha256'].items():
        require(path not in declared or declared[path]==digest,'Conflicting source SHA across nominal/contact reports')
        declared[path]=digest
    nominal_entries=[e for e in nominal_summary['conditions']if e['id']==nominal['id']]
    require(len(nominal_entries)==1 and nominal_entries[0]['artifacts']['condition.json']==summary['nominal_SC4_result']['condition'],
        'Nominal summary must bind this exact nominal condition')
    artifacts=[nominal_entries[0]['artifacts']]+[e['artifacts']for e in entries]
    conditions=[nominal]+[read_ref(a['condition.json'])for a in artifacts[1:]]
    scales=validate_conditions(conditions,summary['selected_SC2_command'])
    def bound(path):
        path=str(Path(path).resolve());require(path in declared,'Missing source artifact binding: '+path)
        return base.bound_json(path,pins,declared[path])
    def file_pin(path,digest):
        path=str(Path(path).resolve());require(declared.get(path)==digest and base.sha(path)==digest,'Config/mask/grid SHA differs: '+path)
        pins[path]=digest
    cases=[];metadata=None;grid_path=None;grid_sha=None;configs=[];mask_sha=None
    for index,(c,artifact,scale,label)in enumerate(zip(conditions,artifacts,scales,LABELS)):
        run=ROOT/'data-native'/c['source_run_id'];sp=run/'postprocess'/c['source_case_id']/'summary.json';post=bound(sp)
        record=bound(run/'cases'/(c['source_case_id']+'.json'));pre=bound(run/'preregistration.json')
        native_case=next(case for case in pre['cases']if case['id']==c['source_case_id'])
        require(post.get('status')=='complete'and post.get('source_inputs_unchanged')is True and post.get('id')==c['source_case_id']and
            record.get('status')=='complete'and record['postprocess_sha256']==pins[str(sp)]and
            Path(record['postprocess_path']).resolve()==sp and record['config_sha256']==native_case['config_sha256']==c['configuration_sha256'],
            'Terminal native case/post/config receipts required')
        for key in('config','mask'):file_pin(native_case[key+'_file'],native_case[key+'_sha256'])
        props=dict(line.split('=',1)for line in Path(native_case['config_file']).read_text().splitlines()if'='in line and not line.lstrip().startswith('#'))
        configs.append(props)
        if mask_sha is None:mask_sha=native_case['mask_sha256']
        require(native_case['mask_sha256']==mask_sha,'Contact-only diagnostic must preserve exact physical mask bytes')
        validate_config_contrast(configs[0],props,FACTORS[index])
        contact_shapes=contours.validate_contact_shapes({**native_case,'id':contours.IDS[1]})
        centres=contours.pad_centres_from_properties(Path(native_case['config_file']).read_text())
        require(np.allclose(centres,[p['centroid_mm']for p in contact_shapes],rtol=0,atol=1e-12),'Operative config centres differ from physical outline')
        refs=post['input_sha256'];meta_refs=[p for p in refs if Path(p).name=='mesh-metadata.json'];grid_refs=[p for p in refs if Path(p).name in('grid.csv','grid.csv.gz')]
        require(len(meta_refs)==len(grid_refs)==1,'Unique native metadata/grid references required');meta=bound(meta_refs[0]);validate_grid_contract(meta)
        require(meta==post['mesh_metadata']and meta['config_sha256']==c['configuration_sha256'],'Native mesh/config receipt differs')
        gp=grid_refs[0];gd=refs[gp];file_pin(gp,gd)
        if metadata is None:metadata=meta;grid_path=gp;grid_sha=gd
        require(gd==grid_sha and meta['z_faces_mm']==metadata['z_faces_mm'],'Exact same SC4 grid required across contact conditions')
        vp=artifact['volume.npz'];arrays=base.load_scalars(vp['path'],vp['SHA256'],meta['cells']);pins[str(Path(vp['path']).resolve())]=vp['SHA256']
        if cases:
            require(all(np.array_equal(arrays[k],cases[0]['arrays'][k])for k in('region_total_m3','region_target_m3','region_surface_0_5_m3')),
                'Identical native fractional ROI weights required')
            require(contact_shapes==cases[0]['top_contact_shapes'],'Three columns must display same actual physical contact contours')
        cases.append(dict(id=c['id'],label=label,contact_Z_factor=FACTORS[index],arrays=arrays,scales=scale,
            source_condition=artifact['condition.json'],scalar_archive=vp,source_commit=c['source_commit'],configuration_sha256=c['configuration_sha256'],
            operative_config_path=native_case['config_file'],mask_path=native_case['mask_file'],mask_SHA256=mask_sha,native_grid_SHA256=gd,
            native_registration=dict(path=str(run/'preregistration.json'),SHA256=pins[str(run/'preregistration.json')]),
            top_contact_shapes=contact_shapes,projected_top_contact_pad_centres_mm=centres.tolist(),
            fixed_SC2_amplitude_metadata={m:{k:v for k,v in n.items()if k in('amplitude_scale','historical_SC2_mode_id','normalization_scope','actual_source_Vpp_intervals_V','actual_burdens','actual_power_metrics_W')}for m,n in c['fixed_SC2_amplitude_modes'].items()},
            supplemental_rematched_not_plotted=True,saved_primary_screen=c['primary_fixed_SC2_skin8_screen'],probe_artifact_producer_receipt_not_decoded=artifact['probes.json']))
    with(gzip.open(grid_path,'rt')if str(grid_path).endswith('.gz')else open(grid_path))as stream:grid=np.loadtxt(stream,delimiter=',',skiprows=1)
    require(len(grid)==metadata['cells']and np.isfinite(grid).all()and np.all(np.sum(grid[:,:2]**2,axis=1)<625),'Finite D50 native grid required')
    base.verify_pins(pins)
    return dict(cases=cases,grid=grid,metadata=metadata,input_sha256=pins,source_contact_summary=str(summary_path),
        original_SC2_caps=summary['selected_SC2_command']['SC2_original_eight_caps'],saved_contact_holds=summary['holds'])


def render_model(model,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle,Rectangle,Polygon
    output=Path(output).resolve();require(not output.exists()and(ROOT/'docs')in output.parents,'Unique new docs output required');output.mkdir(parents=True)
    result=dict(schema='task1-rounded-contact-native-maps-v1',status='rendering',display_only=True,no_new_PDE=True,no_E_phi_decode=True,
        external_guard_contract=dict(CPU_count=1,max_seconds=120,RSS_bytes=3*1024**3,disk_reserve_bytes=2*1024**3,max_added_bytes=MAX_OUTPUT_BYTES),
        no_scoring_or_gate_recalculation=True,candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,
        coordinate_system='x/y horizontal mm; +z depth from skin surface0',primary_ROI='r<=5mm,depth15..20mm; frozen fractional weights',
        displayed_modes='raw1Vpp and frozen historical SC2skin8 amplitude; neither means equal contact burden on SC4 contact variants',
        supplemental_SC4_rematches_plotted=False,metrics={'maxTIS':'fundamentals2074 sampled-direction maximum; lower bound to continuous maximum',
            'fixedTIS':'fundamentals along(1/sqrt2,1/sqrt2,0)','RMS':'all active carrier vector RMS; not modulation; square harmonics zero'},
        actual_XY_depth_definition='Nearest saved native slice to17.5mm, reported exactly; distinct from centre20mm differential probe',
        top_contacts='Actual fixed576-full-face polygon; no smoothing/hull/bbox substitution. Deep XY symbols are projected top centroids only.',
        contact_model_scope='Complex specific contact Z×0.5/1/2 uncertainty; no extra Rs subtraction/area scaling; PBS is not validated skin',
        source_contact_summary=model['source_contact_summary'],original_SC2_caps=model['original_SC2_caps'],input_sha256=model['input_sha256'],
        cases=[{k:v for k,v in c.items()if k!='arrays'}for c in model['cases']],color_limits={},artifacts={},**implementation_receipt())
    def save(fig,name):
        path=output/name;fig.savefig(path,dpi=120);plt.close(fig)
        require(sum(p.stat().st_size for p in output.iterdir()if p.is_file())<=MAX_OUTPUT_BYTES,'Fixed32MiB display bundle cap exceeded')
        result['artifacts'][name]=dict(path=str(path),SHA256=base.sha(path))
    try:
        fig,axes=plt.subplots(1,3,figsize=(13,4.5));fig.subplots_adjust(left=.05,right=.98,bottom=.14,top=.8,wspace=.25)
        for ax,case in zip(axes,model['cases']):
            ax.add_patch(Circle((0,0),25,fill=False,color='black'));ax.add_patch(Circle((0,0),5,fill=False,color='gray',linestyle='--'))
            for p in case['top_contact_shapes']:
                ax.add_patch(Polygon(p['polygon_mm'],closed=True,facecolor=('tomato','royalblue','silver','silver')[p['pad']],edgecolor='black',linewidth=.6))
                x,y=p['centroid_mm'];ax.plot(x,y,'k+',markersize=4);ax.annotate(f"pad{p['pad']}: "+('out'+str(p['source_output'])if p['source_output']is not None else'GND'),(x,y),fontsize=6)
            ax.set(xlim=(-26,26),ylim=(-26,26),xlabel='x(mm)',ylabel='y(mm)',title=case['label']+'\nactual contact at z=0');ax.set_aspect('equal')
        fig.suptitle('Identical physical4pads / two outputs / commonGND50Ω\n225mm² each; actual stepped70mm outline, not17.5mm bounding box or smooth circle')
        save(fig,'top-XY-physical-contact-outlines.png')
        for mode in MODES:
            for metric in METRICS:
                for deep in(False,True):
                    tag='deep_ROI_display_clipped'if deep else'global_native_range';lo,hi=shared_color_limits(model['cases'],metric,mode,deep_roi=deep)
                    result['color_limits'][f'{tag}/{mode}/{metric}']=dict(vmin=lo,vmax=hi,units='V/m',shared_cases=3,shared_planes=['XY','XZ'],
                        scope='PrimaryROI positive-weight samples; higher pixels clipped only for display'if deep else'All native cells')
                    fig,axes=plt.subplots(2,3,figsize=(14,8));fig.subplots_adjust(left=.055,right=.89,bottom=.08,top=.85,wspace=.25,hspace=.32)
                    for col,case in enumerate(model['cases']):
                        sl=native_slices(model['grid'],model['metadata'],case['arrays'][metric]*case['scales'][mode]);result['native_slices']=dict(XY_actual_z_mm=sl['xy_actual_depth_mm'],XZ_actual_y_mm=sl['xz_actual_y_mm'])
                        for row,plane in enumerate(('xy','xz')):
                            ax=axes[row,col];im=ax.pcolormesh(sl['x_edges_mm'],sl['y_edges_mm']if plane=='xy'else sl['z_edges_mm'],sl[plane],shading='flat',vmin=lo,vmax=hi,cmap='viridis',rasterized=True)
                            ax.set(xlabel='x(mm)',ylabel='y(mm)'if plane=='xy'else'+z depth(mm)')
                            if plane=='xy':
                                ax.add_patch(Circle((0,0),5,fill=False,color='white',linestyle='--'));ax.set_aspect('equal')
                                for p,(x,y)in enumerate(case['projected_top_contact_pad_centres_mm']):ax.plot(x,y,'+'if p<2 else'x',color='tomato'if p<2 else'white',markersize=4)
                                ax.set_title(case['label']+f"\nz={sl['xy_actual_depth_mm']:.6g}mm; frozenA={case['scales'][mode]:.7g}",fontsize=8)
                            else:
                                for z in(.1,5.1,10.1):ax.axhline(z,color='white',linestyle=':',linewidth=.6)
                                ax.axhspan(5.1,10.1,facecolor='none',hatch='///',edgecolor=(1,1,1,.25),linewidth=0);ax.text(-24,7.6,'fat5.1–10.1mm',color='white',fontsize=6)
                                ax.axhline(0,color='white',linewidth=.7);ax.axhline(5,color='orange',linestyle='--',linewidth=.6)
                                half=math.sqrt(max(0,25-sl['xz_actual_y_mm']**2));ax.add_patch(Rectangle((-half,15),2*half,5,fill=False,color='white',linestyle='--'))
                                ax.invert_yaxis();ax.set_title(f"native y={sl['xz_actual_y_mm']:.6g}mm; r5/depth15–20 ROI dashed",fontsize=8)
                    fig.colorbar(im,cax=fig.add_axes((.915,.13,.015,.64)),label=metric+' (V/m); common3columns/XY+XZ')
                    fig.suptitle(f'{metric} / {mode} / {tag}\n+z depth from skin0; SC0–.1/dermis.1–5.1/fat5.1–10.1/muscle10.1–25.1mm. Native XY plane ≠20mm probe.')
                    save(fig,f'{tag}--{mode}--{metric}.png')
        base.verify_pins(model['input_sha256']);result.update(status='rendered_unadopted',inputs_unchanged=True,heatmap_PNG_count=12,top_contact_PNG_count=1)
        cards=''.join('<figure><figcaption>'+html.escape(n)+'</figcaption><a href="'+html.escape(n)+'"><img loading="lazy" src="'+html.escape(n)+'" alt="'+html.escape(n)+'"></a></figure>'for n in result['artifacts'])
        text='<!doctype html><html lang="en"><meta charset="utf-8"><title>SC4 contact uncertainty native maps</title><style>body{font:16px system-ui;max-width:1500px;margin:2rem auto;padding:1rem}img{width:100%}figure{margin:2rem 0}</style><h1>SC4 contact-Z uncertainty: same selected e7 command</h1><p>Three columns: nominal/0.5×/2× complex specific contact impedance. All use identical geometry/mask/grid and historical SC2 command/amplitudes: raw1Vpp and frozen SC2skin8. These labels do not assert equal current, power or skin/contact burdens in each variant. Supplemental SC4/contact-rematched modes are not mixed into these maps. Four physical pads/two outputs/commonGND50Ω remain fixed. PBS impedance transfer is uncertain; no extra Rs subtraction or area rescaling.</p><p>12heatmaps: three distinct V/m metrics×two frozen amplitudes×global/deepROI display ranges. Each range is common across all3columns and XY/XZ. Deep clipping changes display only. Native XY near17.5mm is labeled with its actual cell depth and is distinct from the20mm differential probe. +z points inward from skin0; r5/depth15–20ROI and fat5.1–10.1mm are marked. Top polygons are actual full-face outlines; deep XY markers are projections, not electrodes at depth. No E/phi decoding, new score/gate, convergence, adoption, loaded-instrument, physiology or safety claim.</p>'+cards+'<p><a href="summary.json">source/config/scalar/grid SHA, saved screens and exact color limits</a></p></html>'
        path=output/'index.html';path.write_text(text);result['artifacts']['index.html']=dict(path=str(path),SHA256=base.sha(path))
        require(sum(p.stat().st_size for p in output.iterdir()if p.is_file())<=MAX_OUTPUT_BYTES,'Fixed32MiB bundle cap exceeded')
    except BaseException as error:
        result.update(status='error',failure={'type':type(error).__name__,'message':str(error)});(output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');raise
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--summary',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    require(not Path(args.output).exists(),'Preserve existing outputs');started=time.monotonic();implementation_receipt()
    result=render_model(load_model(args.summary),args.output);print(json.dumps(dict(status=result['status'],wall_seconds=time.monotonic()-started,output=str(Path(args.output).resolve()))))

if __name__=='__main__':main()
