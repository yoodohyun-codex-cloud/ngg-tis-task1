"""Read-only native RMS comparison and standalone views; no work on import.

Root supplies an authenticated admission, exclusive output and finite guard.
No Q, PDE, new TIS angular metric, field translation or original-file write.
"""
import gc,json,math,time
from pathlib import Path
import pair_gui_inputs as inputs
import frozen_pixel_outline as outline
SOURCE=inputs.SOURCE
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
MODES=('fixed_1Vpp','same_centre20mm_vector_RMS','same_target_volume_RMS')
DEPTHS=(5.,10.,15.,17.5,20.)
LINEAR=('source_Vpp_each','sum_output_current_RMS_A_bookkeeping','skin_vector_J_RMS_max_A_m2','skin_vector_J_RMS_P95_A_m2','contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V')
POWERS=('source_power_W','source_resistor_power_W','SC_power_W','skin_power_W','contact_power_W')
def require(ok,message):inputs.require(ok,message)
def check(guard,deadline):
 guard()
 if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite cached single-pair GUI deadline')
def native(value):
 if value is None or type(value)in(str,bool,int):return value
 if type(value)is float:
  require(math.isfinite(value),'Finite output JSON scalar');return value
 if isinstance(value,dict):return{str(k):native(v)for k,v in value.items()}
 if isinstance(value,(list,tuple)):return[native(v)for v in value]
 if hasattr(value,'item'):
  result=value.item();require(type(result)in(bool,int,float),'Scientific scalar must become an ordinary finite scalar');return native(result)
 raise TypeError('No complex or array object is silently serialized')
def encoded(value):return(json.dumps(native(value),ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def new_json(path,value):
 raw=encoded(value)
 with Path(path).open('xb')as stream:stream.write(raw)
def required_inputs(admission=None):return inputs.required_inputs(admission)
def make_spec(admission=None):
 spec=inputs.make_spec(admission);spec.update(comparison_modes=list(MODES),XY_requested_depths_mm=list(DEPTHS),field_definition='Temporal vector carrier RMS sqrt(sum_frequency sum_component abs(Epeak)^2/2); not TIS AM',arrows_definition='Separate chosen carrier real(Epeak) at t=0; no envelope or AM vector',histogram_definition='40 common raw fixed1Vpp bins, physical fractional volume weights; explicit below/above range volume; no physiological cutoff',new_PDE_RHS=0,new_angular_evaluations=0,Q_loaded=False);return spec
def scale_stats(stats,amplitude):
 require(math.isfinite(amplitude)and amplitude>0,'Positive linear response amplitude')
 return{k:(v*amplitude if k in('mean','std','rms','min','max','p10','p95')else v)for k,v in stats.items()}
def relative_burdens(electrical,reference):
 return{k:float(electrical[k])/float(reference[k])if k in electrical and k in reference and reference[k]>0 else None for k in LINEAR+POWERS}
def regression(value,expected,label):
 require(math.isfinite(float(value))and math.isfinite(float(expected)),'Finite regression '+label)
 error=abs(float(value)-float(expected));limit=1e-10+2e-7*abs(float(expected));require(error<=limit,'Saved native metric regression failed '+label)
 return dict(passed=True,actual=float(value),expected=float(expected),absolute_error=error,absolute_limit=limit,scope='Cached-field consistency only; not mesh or experiment validation')
def _load(np,descriptor,keys,pins,guard,deadline):
 check(guard,deadline);path=Path(descriptor['path']);require(pins.get(str(path))==descriptor['SHA256']and path.is_file()and not path.is_symlink()and path==path.resolve()and path.stat().st_size==descriptor['bytes']and inputs.sha(path)==descriptor['SHA256'],'Actual full pinned archive SHA before decode')
 with np.load(path,allow_pickle=False)as archive:
  require(set(keys).issubset(archive.files),'Required saved native field missing; no substitute');data={key:np.array(archive[key],copy=True)for key in keys}
 require(all(np.isfinite(value).all()for value in data.values()),'Finite native arrays only');return data
def _stats(np,values,weights):
 use=weights>0;v=values[use];w=weights[use];require(len(v)>0 and np.isfinite(v).all()and np.isfinite(w).all()and np.all(w>0),'Positive finite physical ROI volume')
 volume=float(w.sum());mean=float(np.dot(v,w)/volume);order=np.argsort(v,kind='stable');cum=np.cumsum(w[order]);quantile=lambda f:float(v[order[min(int(np.searchsorted(cum,f*volume,side='left')),len(order)-1)]])
 return dict(volume_m3=volume,mean=mean,std=float(np.sqrt(np.dot(w,(v-mean)**2)/volume)),rms=float(np.sqrt(np.dot(w,v*v)/volume)),min=float(v.min()),max=float(v.max()),p10=quantile(.1),p95=quantile(.95))
def _axes(np,grid):
 x=np.unique(grid[:,0]);y=np.unique(grid[:,1]);z=np.unique(grid[:,2]);require(len(x)==len(y)==100 and len(z)==101 and len(grid)==793860,'Original XY100/101-level/793860 native grid')
 xy=grid[:7860,:2];require(np.array_equal(grid[:,:2],np.tile(xy,(101,1)))and np.array_equal(grid[:,2],np.repeat(z,7860)),'Saved exporter and actual common grid share original depth-major native order')
 width=[]
 for iz,depth in enumerate(z):
  volumes=grid[iz*7860:(iz+1)*7860,4];require(np.all(volumes==volumes[0]),'Uniform lateral full-cell physical volume at each actual depth');width.append(float(volumes[0])/.0005**2*1000)
 faces=np.concatenate(([0.],np.cumsum(width)));require(np.allclose(z,(faces[:-1]+faces[1:])/2,rtol=0.,atol=1e-10)and np.allclose(faces[[0,8,27,45,101]],[0.,.1,5.1,10.1,25.1],rtol=0.,atol=1e-10),'Actual full-cell volume-derived depth faces and physical layer boundaries')
 ix=np.searchsorted(x,grid[:,0]);iy=np.searchsorted(y,grid[:,1]);iz=np.searchsorted(z,grid[:,2]);lookup=np.full((len(z),100,100),-1,np.int32);lookup[iz,iy,ix]=np.arange(len(grid));require(np.count_nonzero(lookup>=0)==len(grid),'Unique exact coordinate lookup')
 require(np.all(np.diff(x)>0)and np.all(np.diff(y)>0)and np.all(np.diff(z)>0),'Strictly monotone physical axes')
 return dict(x=x,y=y,z=z,z_faces=faces,xy_faces=np.arange(101)*.5-25.,lookup=lookup,x0=int(np.argmin(abs(x))),y0=int(np.argmin(abs(y))))
def _slice(np,values,indices):
 result=np.full(indices.shape,np.nan,float);use=indices>=0;result[use]=values[indices[use]];return[float(v)if math.isfinite(float(v))else None for v in result.ravel()]
def _views(np,rms,arrows,axes):
 lookup=axes['lookup'];result={};definitions=[('XZ',lookup[:,axes['y0'],:],axes['x'],axes['z'],dict(axis='y',requested_mm=0.,actual_mm=float(axes['y'][axes['y0']])),(0,2)),('YZ',lookup[:,:,axes['x0']],axes['y'],axes['z'],dict(axis='x',requested_mm=0.,actual_mm=float(axes['x'][axes['x0']])),(1,2))]
 for depth in DEPTHS:
  iz=int(np.argmin(abs(axes['z']-depth)));definitions.append(('XY_'+str(depth),lookup[iz],axes['x'],axes['y'],dict(axis='depth',requested_mm=depth,actual_mm=float(axes['z'][iz])),(0,1)))
 for name,index,horizontal,vertical,plane,components in definitions:
  vectors={}
  for frequency,field in arrows.items():
   rows=[]
   for j in range(0,index.shape[0],6):
    for i in range(0,index.shape[1],6):
     cell=int(index[j,i])
     if cell>=0:rows.append([float(horizontal[i]),float(vertical[j]),float(field[cell,components[0]].real),float(field[cell,components[1]].real)])
   vectors[frequency]=rows
  result[name]=dict(x_mm=horizontal.tolist(),y_mm=vertical.tolist(),x_edges_mm=axes['xy_faces'].tolist(),y_edges_mm=(axes['xy_faces']if name.startswith('XY_')else axes['z_faces']).tolist(),values=_slice(np,rms,index),plane=plane,depth_axis_positive_down=not name.startswith('XY_'),vector_carrier_peak_real_by_frequency=vectors,display_interpolation='None; nearest actual native plane, actual coordinate and volume-derived depth faces disclosed',raw_clipping=False)
 return result
def _mask(np,grid,pads,cells,areas,count):
 require(pads.shape==cells.shape==areas.shape and np.all(areas>0)and np.all(cells>=0)and np.all(cells<7860)and set(pads.tolist())==set(range(count)),'Actual physical contact mapping')
 require(np.all(abs(areas-.0005**2)<=1e-10*.0005**2)and len(set(cells.tolist()))==len(cells),'Disjoint authenticated full .5mm contact faces')
 xy=grid[:7860,:2];result=[]
 for p in range(count):
  use=pads==p;ij=[]
  for cell in cells[use]:
   xx,yy=(float(v)for v in xy[int(cell)]);i=round((xx+25)/.5-.5);j=round((yy+25)/.5-.5);require(0<=i<100 and 0<=j<100 and abs(xx-(-25+(i+.5)*.5))<1e-10 and abs(yy-(-25+(j+.5)*.5))<1e-10,'Exact contact-cell coordinate/index identity');ij.append((i,j))
  loops,signed=outline.integer_contours(ij);area=float(areas[use].sum());require(abs(area-225e-6)<=1e-10*225e-6,'Actual 225mm2 pad area')
  result.append(dict(physical_pad_id=p,node=('out'+str(p)if count==4 and p<2 else'source0'if count==2 and p==0 else'GND'),area_mm2=area*1e6,center_mm=np.average(xy[cells[use]],axis=0,weights=areas[use]).tolist(),mask_contours_mm=[[[-25+i*.5,-25+j*.5]for i,j in loop]for loop in loops],mask_fill_rule='evenodd',mask_full_cell_count=len(ij),signed_contour_area_mm2=[v*.5*.5/2 for v in signed]))
 return result
def _metrics_and_views(np,spec,entry,grid,weights,axes,hist_edges,guard,deadline):
 cid=entry['candidate_id'];is_tis=entry.get('is_TIS',False);reference=spec['TIS']['reference_metrics'];record=entry['record'];pins={**spec['input_sha256'],**spec['source_sha256']};squared=np.zeros(len(grid));j_squared=np.zeros(len(grid));fields={};contact=None;contact_j2=None;drop2=None;current2=None;metal2=None;point2=0.;proofs=[];layers=grid[:,3].astype(int);gamma_by_frequency=spec['single_pair_result']['spec']['gamma_by_frequency'];stencil=spec['centre_interpolation']['stencil']
 for frequency,descriptor in entry['raw_by_frequency'].items():
  keys=['E_peak_V_m','contact_xy_index','contact_area_m2','contact_normal_J_peak_A_m2','contact_drop_peak_V','source_current_peak_A']+(['contact_pad','metal_peak_V']if is_tis else['contact_physical_pad_id','connected_source_metal_peak_V'])
  raw=_load(np,descriptor,keys,pins,guard,deadline);E=raw['E_peak_V_m'];require(E.shape==(len(grid),3),'Actual full complex-vector carrier field')
  gamma=np.asarray([complex(v['real'],v['imaginary'])for v in gamma_by_frequency[frequency]])
  energy=np.sum(abs(E)**2,axis=1)/2.;squared+=energy;j_squared+=abs(gamma[layers])**2*energy
  centre=np.asarray([sum(row['weight']*E[row['native_cell_index'],component]for row in stencil)for component in range(3)]);point2+=float(np.sum(abs(centre)**2)/2.)
  fields[frequency]=E
  pads=raw['contact_pad']if is_tis else raw['contact_physical_pad_id'];cells=raw['contact_xy_index'];areas=raw['contact_area_m2'];mapping=(pads,cells,areas)
  if contact is None:contact=mapping;contact_j2=np.zeros(len(areas));drop2=np.zeros(len(areas));current2=np.zeros(2 if is_tis else 1);metal2=np.zeros_like(current2)
  else:require(all(np.array_equal(a,b)for a,b in zip(contact,mapping)),'Both TIS carriers must have exactly identical physical contact rows')
  contact_j2+=abs(raw['contact_normal_J_peak_A_m2'])**2/2.;drop2+=abs(raw['contact_drop_peak_V'])**2/2.;I=raw['source_current_peak_A'];metal=raw['metal_peak_V']if is_tis else raw['connected_source_metal_peak_V'];require(I.shape==metal.shape==current2.shape,'Actual connected-output current/metal identity');current2+=abs(I)**2/2.;metal2+=abs(metal)**2/2.
  ideal=np.zeros(len(I),complex);ideal[0 if frequency=='2000'else 1]=.5;require(float(np.max(abs(metal+50*I-ideal)))<=1e-9+2e-7*.5,'Preserve exact high-Z source/loaded metal/50ohm circuit')
 rms=np.sqrt(squared);jrms=np.sqrt(j_squared);regions={name:_stats(np,rms,w)for name,w in weights.items()};expected=record['metrics']['regions']if is_tis else record['regions'];electrical=record['metrics']['electrical']if is_tis else record['electrical']
 for name in REGIONS:
  saved=expected[name]['statistics']['RMS']if is_tis else expected[name]
  for key in('mean','std','max','p10','p95'):proofs.append(regression(regions[name][key],saved[key],cid+'/'+name+'/'+key))
 point=math.sqrt(point2);proofs.extend([regression(point,reference['centre_vector_RMS_V_m']if is_tis else record['centre_vector_RMS_V_m'],cid+'/physical_centre_vector_RMS'),regression(regions['target']['rms'],reference['target_volume_RMS_V_m']if is_tis else record['target_volume_RMS_V_m'],cid+'/ROI_second_moment_RMS')])
 if not is_tis:
  scalar=_load(np,entry['scalar'],['RMS_V_m','Jtotal_vector_RMS_A_m2'],pins,guard,deadline);require(all(v.shape==(len(grid),)for v in scalar.values()),'Actual saved scalar dimension');require(np.allclose(rms,scalar['RMS_V_m'],rtol=2e-7,atol=1e-10)and np.allclose(jrms,scalar['Jtotal_vector_RMS_A_m2'],rtol=2e-7,atol=1e-12),'Full saved scalar arrays reproduce actual complex raw fields');del scalar
 cstats=_stats(np,np.sqrt(contact_j2),contact[2]);skin=_stats(np,jrms,weights['total']*(layers<=1));computed=dict(contact_normal_J_RMS_max_A_m2=cstats['max'],contact_normal_J_RMS_P95_A_m2=cstats['p95'],contact_voltage_RMS_max_V=float(np.sqrt(drop2.max())),skin_vector_J_RMS_max_A_m2=skin['max'],skin_vector_J_RMS_P95_A_m2=skin['p95'],sum_output_current_RMS_A_bookkeeping=float(np.sqrt(current2).sum()))
 for key,value in computed.items():proofs.append(regression(value,electrical[key],cid+'/'+key))
 masks=_mask(np,grid,*contact,4 if is_tis else 2);slices=_views(np,rms,fields,axes);hist={}
 for name,w in weights.items():
  volume,_=np.histogram(rms,bins=hist_edges,weights=w);hist[name]=dict(bin_edges_V_m=hist_edges.tolist(),physical_volume_m3=volume.tolist(),below_range_volume_m3=float(w[rms<hist_edges[0]].sum()),above_range_volume_m3=float(w[rms>hist_edges[-1]].sum()),unit='m3',cutoff_interpretation='Numerical carrier RMS distribution, not a physiological threshold')
 contactmap=np.full((100,100),np.nan)
 for cell,value in zip(contact[1],np.sqrt(contact_j2)):
  xx,yy=grid[int(cell),:2];i=round((float(xx)+25)/.5-.5);j=round((float(yy)+25)/.5-.5);contactmap[j,i]=value
 contact_values=[float(v)if math.isfinite(float(v))else None for v in contactmap.ravel()]
 output=dict(candidate_id=cid,is_TIS=is_tis,physical_pads=4 if is_tis else 2,independent_outputs=2 if is_tis else 1,contact_area_mm2=900. if is_tis else 450.,frequencies_Hz=[2000,2010]if is_tis else[2000],regions_fixed_1Vpp=regions,centre_vector_RMS_V_m=point,target_volume_RMS_V_m=regions['target']['rms'],electrical_fixed_1Vpp=electrical,loaded_metal_RMS_by_output_V=np.sqrt(metal2).tolist(),output_current_RMS_A=np.sqrt(current2).tolist(),regression_proofs=proofs,histograms_fixed_1Vpp=hist,source_raw_by_frequency=entry['raw_by_frequency'],TIS_AM_saved_regions=record['metrics']['regions']if is_tis else None,single_carrier_10Hz_envelope_AM_V_m=None if is_tis else 0.,candidate_adopted=False)
 del fields,rms,jrms,squared,j_squared;gc.collect();check(guard,deadline)
 return output,dict(candidate_id=cid,electrodes=masks,RMS_slices=slices,contact_normal_J_RMS_top=dict(x_mm=axes['x'].tolist(),y_mm=axes['y'].tolist(),values=contact_values,unit='A/m2',raw_clipping=False))
def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(callable(guard)and spec==make_spec(spec['root_admission']),'Exact published single-pair GUI specification and root guard');check(guard,deadline_monotonic);out=Path(output_dir);require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink()and out.parent==Path('/dev/shm'),'New root-owned canonical output');require(not(out/'summary.json').exists(),'Never overwrite an old GUI/result')
 import numpy as np
 pins={**spec['input_sha256'],**spec['source_sha256']};common=_load(np,spec['common_grid'],['grid']+[name+'_volume_weight_m3'for name in REGIONS],pins,guard,deadline_monotonic);grid=common['grid'];require(grid.shape==(793860,5),'Actual shared common-grid ABI');weights={name:common[name+'_volume_weight_m3']for name in REGIONS};require(all(w.shape==(len(grid),)and np.all(w>=0)for w in weights.values())and np.allclose(weights['total'],grid[:,4],rtol=1e-12,atol=1e-25)and np.allclose(weights['target']+weights['off_target'],weights['total'],rtol=1e-12,atol=1e-25),'Original finite physical fractional-volume ROI weights');axes=_axes(np,grid)
 records=[dict(candidate_id=inputs.TIS_ID,is_TIS=True,record=spec['TIS']['record'],raw_by_frequency=spec['TIS']['raw_by_frequency'])]+[dict(candidate_id=row['candidate_id'],record=row['record'],raw_by_frequency={'2000':row['files']['-2000-raw.npz']},scalar=row['files']['-RMS-J-scalars.npz'])for row in spec['pairs']]
 maximum=max([spec['TIS']['record']['metrics']['regions']['total']['statistics']['RMS']['max']]+[row['record']['regions']['total']['max']for row in spec['pairs']]);hist_edges=np.linspace(0.,maximum*(1+1e-7),41);rows=[];views={};scales={inputs.TIS_ID:{mode:1. for mode in MODES}}
 for row in spec['pairs']:scales[row['candidate_id']]={'fixed_1Vpp':1.,**{mode:float(row['record']['separate_RMS_matches_to_selected_TIS'][mode]['amplitude_scale'])for mode in MODES[1:]}}
 source_electrical=spec['TIS']['record']['metrics']['electrical'];displaymax=0.;jmax=0.
 for entry in records:
  row,view=_metrics_and_views(np,spec,entry,grid,weights,axes,hist_edges,guard,deadline_monotonic);cid=row['candidate_id'];row['modes']={}
  for mode in MODES:
   a=scales[cid][mode];electrical=row['electrical_fixed_1Vpp']if entry.get('is_TIS')or mode=='fixed_1Vpp'else entry['record']['separate_RMS_matches_to_selected_TIS'][mode]['electrical'];row['modes'][mode]=dict(amplitude_scale=a,required_source_high_impedance_Vpp=float(electrical['source_Vpp_each']),centre_vector_RMS_V_m=row['centre_vector_RMS_V_m']*a,target_volume_RMS_V_m=row['target_volume_RMS_V_m']*a,regions={name:scale_stats(stats,a)for name,stats in row['regions_fixed_1Vpp'].items()},electrical=electrical,burden_ratios_to_fixed_1Vpp_P23=relative_burdens(electrical,source_electrical),loaded_metal_RMS_by_output_V=[v*a for v in row['loaded_metal_RMS_by_output_V']]);displaymax=max(displaymax,row['regions_fixed_1Vpp']['total']['max']*a);jmax=max(jmax,electrical['contact_normal_J_RMS_max_A_m2'])
  row['saved_single_pair_comparison']=entry['record']if not entry.get('is_TIS')else None;rows.append(row);views[cid]=view;new_json(out/('checkpoint-%02d.json'%len(rows)),dict(status='cached_complex_field_RMS_views_complete',candidate_id=cid,completed_geometries=len(rows),new_PDE_RHS=0,new_angular_evaluations=0))
 summary=dict(schema='task1-single-pair-comparison-gui-v1',status='cached_three_geometry_single_pair_GUI_prepared_unadopted',spec=spec,baseline_id=inputs.TIS_ID,candidates=rows,comparison_modes=list(MODES),new_PDE_RHS=0,new_angular_evaluations=0,Q_loaded=False,originals_overwritten=False,browser_validation_performed=False,candidate_adopted=False,ROI_receipt=spec['ROI_receipt'],grid_binding=dict(common_grid_SHA256=spec['common_grid']['SHA256'],original_fractional_masks_authenticated=True,original_weights_changed=False,raw_exporters_share_original_flat_order=True,raw_archives_do_not_embed_separate_grids=True),AM_scope=dict(TIS='Existing stored2074-direction sampled AM statistics preserved in selected source record; no angular reevaluation here',single_carrier_10Hz_envelope_AM_V_m=0.,equal_RMS_does_not_imply_equal_vector_waveform_modulation_activation_or_safety=True),holds=spec['single_pair_result']['holds'])
 viewdata=dict(schema='task1-single-pair-comparison-native-views-v1',candidates=views,raw_fixed_1Vpp_values=True,shared_ranges=dict(x_mm=[-25.,25.],y_mm=[-25.,25.],depth_mm=[0.,25.1],RMS_V_m=[0.,displaymax],contact_J_A_m2=[0.,jmax]),coordinate_system='x/y top-plane axes; depth z=0 at physical top, positive down; mm',XY_requested_depths_mm=list(DEPTHS),arrows_definition=spec['arrows_definition']);new_json(out/'views.json',viewdata);new_json(out/'summary.json',summary)
 import pair_gui_render
 html=pair_gui_render.build(summary,viewdata);raw=html.encode('utf-8');require(0<len(raw)<80*1024**2,'Standalone GUI per-file output bound')
 with(out/'index.html').open('xb')as stream:stream.write(raw)
 new_json(out/'gui-receipt.json',dict(status='standalone_GUI_rendered_browser_unverified',index_SHA256=inputs.sha(out/'index.html'),index_bytes=len(raw),native_geometries=3,new_PDE_RHS=0,new_angular_evaluations=0,source_input_SHA256=pins,candidate_adopted=False));check(guard,deadline_monotonic);return dict(summary=summary,views=viewdata,arrays={})
