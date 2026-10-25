"""Cached provisional design rankings, physical high-volume diagnostics and probes.

Import performs no I/O, numerical imports or array work. The sole finite owner
calls make_spec/build after the first design batch has actually completed. No
PDE is solved and no original raw/scalar output is modified or deleted.
"""
from __future__ import annotations
import hashlib,json,math,time
from pathlib import Path

DEFAULT_RUN=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
REGIONS=('target','surface_0_5','surface_without_SC','off_target','total')

def require(ok,message):
 if not ok:raise ValueError(message)
def sha_file(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def read_metadata(path,expected=None):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size<=8_000_000,'Bounded original metadata required')
 raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest();require(expected is None or digest==expected,'Original metadata SHA mismatch: '+str(p));return json.loads(raw),digest
def encoded(obj):return (json.dumps(obj,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def new_json(path,obj):
 raw=encoded(obj)
 with Path(path).open('xb')as f:f.write(raw)
def check(guard,deadline):
 guard();require(deadline is None or time.monotonic()<deadline,'Finite cached design analysis deadline')

def _inventory(run,publication_path=None,declared_sha256=None):
 run=Path(run);require(run.is_absolute()and run==run.resolve()and run.is_dir()and not run.is_symlink(),'Canonical completed input run')
 declared=dict(declared_sha256 or{});pubpath=Path(publication_path)if publication_path is not None else run/'result-publication/result-publication.json';pub=None;pins={};proofs={}
 if pubpath.is_file():
  pub,pubsha=read_metadata(pubpath);require(pub.get('status')=='published_readback_verified'and len(pub.get('commit',''))==40,'Completed direct result readback publication required');pins[str(pubpath)]=pubsha
 def original(path,digest=None):
  p=Path(path);require(p.is_relative_to(run)and p==p.resolve()and not p.is_symlink(),'Original file must be inside completed design run')
  relative=p.relative_to(run).as_posix()
  if pub is not None:
   matches=[(target,item)for target,item in pub['files'].items()if target.endswith('/'+relative)]
   require(len(matches)==1,'Exactly one original direct publication proof: '+relative);target,item=matches[0]
   require(item.get('readback_passed')is True and len(item['SHA256'])==64 and type(item['bytes'])is int,'Per-file full SHA readback required');expected=item['SHA256'];proofs[str(p)]=dict(fixed_commit=pub['commit'],repo_relative_path=target,SHA256=expected,bytes=item['bytes'])
  else:
   expected=declared.get(str(p));require(isinstance(expected,str)and len(expected)==64,'Explicit sole-owner local SHA required before publication: '+relative)
  require(digest is None or expected==digest,'Original summary/archive declared SHA disagrees with proof');pins[str(p)]=expected;return expected
 summarypath=run/'summary.json';summary_sha=original(summarypath);summary,_=read_metadata(summarypath,summary_sha)
 require(summary['status']=='provisional_eight_layout_screen_computed_unadopted'and summary['completed_candidates']==8 and summary['candidate_adopted']is False,'Actually completed unadopted eight-layout batch required')
 original(run/'common-grid-and-ROI.npz');original(run/'ROI-receipt.json')
 candidates=summary['candidates'];require(len(candidates)==8 and len({r['candidate_id']for r in candidates})==8,'Eight distinct completed candidate IDs')
 for row in candidates:
  scalar=row['scalar_arrays'];original(scalar['path'],scalar['SHA256']);cid=row['candidate_id']
  for f in(2000,2010):
   raw=summary['raw_artifacts'][cid+'-'+str(f)];original(raw['path'],raw['SHA256'])
 return dict(run=str(run),summary=summary,input_sha256=pins,proofs=proofs,publication_status='direct_publication_readback_verified'if pub is not None else'root_local_SHA_verified_publication_pending',result_commit=pub['commit']if pub is not None else None,publication_path=str(pubpath)if pub is not None else None)

def required_inputs(run=DEFAULT_RUN,publication_path=None,declared_sha256=None):
 """Metadata-only deferred inventory; no NPZ opens or field calculations."""
 return _inventory(run,publication_path,declared_sha256)['input_sha256']

def make_spec(run=DEFAULT_RUN,publication_path=None,declared_sha256=None):
 original=_inventory(run,publication_path,declared_sha256);rows=original['summary']['candidates'];baseline=next(row for row in rows if row['geometry']['baseline']);m=baseline['metrics']['regions'];mean=m['target']['statistics']['maxTIS']['mean'];p10=m['target']['statistics']['maxTIS']['p10']
 return dict(schema='task1-cached-design-search-analysis-spec-v1',input_run=original['run'],input_sha256=original['input_sha256'],publication_path=original['publication_path'],publication_status=original['publication_status'],result_commit=original['result_commit'],baseline_id=baseline['candidate_id'],candidate_ids=[row['candidate_id']for row in rows],
  ranking=dict(primary_comparison='joint_eight_surface_contact_burden_caps',score='min(targetAMmean_scaled/B0_targetAMmean,targetAMP10_scaled/B0_targetAMP10)',baseline_target_AM_mean_V_m=mean,baseline_target_AM_P10_V_m=p10,tiebreakers=['larger minimum ratio','larger target mean ratio','larger target P10 ratio','candidate_id ascending'],scope='Provisional robust electrical-proxy ranking only; show absolute values, distribution and off-target burden. No adoption, global optimum or physiological equivalence.'),
  diagnostic_cutoffs=[dict(cutoff_id='B0-target-AM-mean',value_V_m=mean,source='B0 fixed1Vpp targetROI volume-weighted mean of2074-direction AM'),dict(cutoff_id='B0-offtarget-AM-P95',value_V_m=m['off_target']['statistics']['maxTIS']['p95'],source='B0 fixed1Vpp off-target volume-weighted P95 of2074-direction AM')],
  cutoff_policy='Two numerical diagnostic cutoffs frozen from completed B0 metadata before candidate scalar classification, common across all candidates and normalization modes. Never a physiological activation or safety threshold.',
  normalization_modes=list(MODES),high_volume_regions=list(REGIONS),probe=dict(depths_mm=[5,10,15,20],centres_xy_mm=[[0,0],[5,0],[-5,0],[0,5],[0,-5]],axes=['x','y'],tip_spacing_mm=5,loading='unloaded differential potential only; hardware input-loading PDE not run'),
  views=dict(fixed_physical_planes='XZ nearest y=0 node, YZ nearest x=0 node, XY nearest z=20mm; actual plane coordinate reported',default_ranges_shared_across_candidates_and_normalizations=True,manual_axes_color_required=True),
  new_PDE_RHS=0,new_candidate_adoption=False,Windows_saved_verified=False)

def ratio_metrics(mean,p10,std,baseline_mean,baseline_p10):
 """Pure robust score, preserving the two ratios and absolute numerator values."""
 require(all(math.isfinite(float(v))and v>=0 for v in(mean,p10,std,baseline_mean,baseline_p10)),'Finite nonnegative absolute electrical proxies')
 mr=mean/baseline_mean if baseline_mean>0 else None;pr=p10/baseline_p10 if baseline_p10>0 else None
 return dict(target_AM_mean_V_m=float(mean),target_AM_P10_V_m=float(p10),target_AM_std_V_m=float(std),target_AM_CV=std/mean if mean>0 else None,target_P10_mean=p10/mean if mean>0 else None,mean_ratio_to_B0=mr,P10_ratio_to_B0=pr,robust_minimum_ratio=min(mr,pr)if mr is not None and pr is not None else None)

def high_volume(np,values,weights,grid,cutoff):
 """Cell-constant physical volume classification at a numerical comparison value."""
 values=np.asarray(values,float);weights=np.asarray(weights,float);require(values.shape==weights.shape==(len(grid),)and np.isfinite(values).all()and np.isfinite(weights).all()and np.all(weights>=0)and math.isfinite(cutoff)and cutoff>=0,'Finite matched scalar values, physical m3 weights and cutoff')
 use=(weights>0)&(values>=cutoff);volume=float(np.sum(weights[use]));total=float(np.sum(weights));positions=grid[use,:3]
 return dict(cutoff_V_m=float(cutoff),operator='>=',high_volume_m3=volume,high_volume_mm3=volume*1e9,represented_ROI_volume_m3=total,fraction_of_represented_ROI=volume/total if total>0 else None,positive_weight_cells=int(np.count_nonzero(use)),cell_centre_bounds_xyz_mm=dict(min=np.min(positions,axis=0).tolist(),max=np.max(positions,axis=0).tolist())if len(positions)else None,bounds_scope='Bounds of representative native cell centres only, not a continuous isosurface or connected component',physiological_threshold=False)

def _load(np,path,digest,guard,deadline,keys):
 check(guard,deadline);p=Path(path);require(p.is_file()and not p.is_symlink()and p==p.resolve()and p.stat().st_size<=80*1024**2 and sha_file(p)==digest,'Exact bounded original raw/scalar NPZ SHA before decode')
 with np.load(p,allow_pickle=False)as saved:
  require(set(keys).issubset(saved.files),'Actual archive lacks requested fields; no field fabricated');data={key:np.array(saved[key],copy=True)for key in keys}
 require(all(np.isfinite(value).all()for value in data.values()),'All decoded original numerical arrays finite');return data

def _null_list(np,values):
 return [[float(v)if math.isfinite(float(v))else None for v in row]for row in np.asarray(values)]

def _views(np,grid,scalars,E0,E1,electrodes,scales,guard,deadline):
 check(guard,deadline);x=np.unique(grid[:,0]);y=np.unique(grid[:,1]);z=np.unique(grid[:,2]);ix=np.searchsorted(x,grid[:,0]);iy=np.searchsorted(y,grid[:,1]);iz=np.searchsorted(z,grid[:,2]);lookup=np.full((len(z),len(y),len(x)),-1,np.int32);lookup[iz,iy,ix]=np.arange(len(grid));xp=int(np.argmin(abs(x)));yp=int(np.argmin(abs(y)));zp=int(np.argmin(abs(z-20)))
 definitions={'XZ':(lookup[:,yp,:],x,z,dict(axis='y',actual_coordinate_mm=float(y[yp])),(0,2)), 'YZ':(lookup[:,:,xp],y,z,dict(axis='x',actual_coordinate_mm=float(x[xp])),(1,2)), 'XY':(lookup[zp,:,:],x,y,dict(axis='z',actual_coordinate_mm=float(z[zp])),(0,1))};slices={}
 for name,(indices,horizontal,vertical,plane,components)in definitions.items():
  check(guard,deadline);valid=indices>=0;am=np.full(indices.shape,np.nan);rms=np.full_like(am,np.nan);am[valid]=scalars['AM_max2074'][indices[valid]];rms[valid]=scalars['carrier_RMS'][indices[valid]];arrows=[]
  for carrier,field in((2000,E0),(2010,E1)):
   for j in range(0,len(vertical),max(1,len(vertical)//12)):
    for i in range(0,len(horizontal),max(1,len(horizontal)//12)):
     cell=int(indices[j,i])
     if cell<0:continue
     arrows.append(dict(x_mm=float(horizontal[i]),y_mm=float(vertical[j]),u=float(field[cell,components[0]].real),v=float(field[cell,components[1]].real),carrier_Hz=carrier,phase_t_s=0.,units='V/m complex-peak real part at t0'))
  slices[name]=dict(x_mm=horizontal.tolist(),y_mm=vertical.tolist(),values=_null_list(np,am),quantity='sampled-direction TIS modulation',unit='V/m',alternate_values={'carrier_RMS':_null_list(np,rms)},plane=plane,depth_axis='positive downward'if name!='XY'else'horizontal y',arrows=arrows,arrow_scope='Separate raw reconstructed carrier E real part at t=0; these arrows are not a TIS vector',display_interpolation='None; nearest actual physical plane and native cell values',clipping_applied_to_raw=False)
 return dict(electrodes=electrodes,slices=slices,amplitude_scales=scales,field_version='native-lateral-half-face-v1+analytic-z-DtN-v1')

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(callable(guard),'Sole finite owner guard');check(guard,deadline_monotonic)
 current=make_spec(spec['input_run'],spec['publication_path'],spec['input_sha256']);require(spec==current,'Exact frozen analysis inputs/cutoffs; no posterior criterion changes')
 original=_inventory(spec['input_run'],spec['publication_path'],spec['input_sha256']);run=Path(spec['input_run']);out=Path(output_dir);require(out.is_absolute()and out==out.resolve()and out.is_dir()and not out.is_symlink()and out.parent==Path('/dev/shm'),'Unique root-created output directory required')
 import numpy as np
 import probe_prediction
 common=_load(np,run/'common-grid-and-ROI.npz',spec['input_sha256'][str(run/'common-grid-and-ROI.npz')],guard,deadline_monotonic,['grid','total_volume_weight_m3','target_volume_weight_m3','surface_0_5_volume_weight_m3','off_target_volume_weight_m3']);grid=common.pop('grid');require(grid.ndim==2 and grid.shape[1]==5 and len(grid)<=800000,'Actual bounded shared grid')
 layer=grid[:,3].astype(int);weights=dict(total=common['total_volume_weight_m3'],target=common['target_volume_weight_m3'],surface_0_5=common['surface_0_5_volume_weight_m3'],off_target=common['off_target_volume_weight_m3']);weights['surface_without_SC']=weights['surface_0_5']*(layer!=0)
 # This immutable write occurs before any candidate scalar classification.
 new_json(out/'diagnostic-cutoffs.json',dict(cutoffs=spec['diagnostic_cutoffs'],policy=spec['cutoff_policy'],baseline_id=spec['baseline_id']))
 candidates=[];view_candidates={};shared_max=0.;cdir=out/'candidates';cdir.mkdir(exist_ok=True)
 bmean=spec['ranking']['baseline_target_AM_mean_V_m'];bp10=spec['ranking']['baseline_target_AM_P10_V_m']
 for record in original['summary']['candidates']:
  check(guard,deadline_monotonic);cid=record['candidate_id'];scalar=record['scalar_arrays'];scalars=_load(np,scalar['path'],scalar['SHA256'],guard,deadline_monotonic,['AM_max2074','carrier_RMS']);require(all(value.shape==(len(grid),)for value in scalars.values()),'Same shared native scalar ordering')
  phi=[];E=[]
  for f in(2000,2010):
   artifact=original['summary']['raw_artifacts'][cid+'-'+str(f)];a=_load(np,artifact['path'],artifact['SHA256'],guard,deadline_monotonic,['phi_peak_V','E_peak_V_m']);require(a['phi_peak_V'].shape==(len(grid),)and a['E_peak_V_m'].shape==(len(grid),3),'Exact original carrier potential/vector shapes');phi.append(a['phi_peak_V']);E.append(a['E_peak_V_m'])
  metrics={};classification={};scales={}
  for mode in MODES:
   normalized=record['normalizations']['comparisons'][mode];require(normalized['status']=='calculated_global_amplitude_rescaling','Complete separate normalization row required');scale=float(normalized['amplitude_scale']);scales[mode]=scale;target=normalized['absolute_ROI_fields_V_m']['target']['maxTIS'];off=normalized['absolute_ROI_fields_V_m']['off_target']['maxTIS'];surface=normalized['absolute_ROI_fields_V_m']['surface_0_5']['maxTIS'];m=ratio_metrics(target['mean'],target['p10'],target['std'],bmean,bp10)
   m.update(amplitude_scale=scale,source_Vpp_each=normalized['electrical']['source_Vpp_each'],target_AM_max_V_m=target['max'],off_target_AM_P95_V_m=off['p95'],off_target_AM_P99_V_m=off['p99'],off_target_AM_max_V_m=off['max'],surface_AM_P95_V_m=surface['p95'],surface_AM_max_V_m=surface['max'],electrical=normalized['electrical'],limiting_constraints=normalized.get('limiting_constraints',[]));metrics[mode]=m
   scaled=scalars['AM_max2074']*scale;classification[mode]={cut['cutoff_id']:{region:high_volume(np,scaled,w,grid,cut['value_V_m'])for region,w in weights.items()}for cut in spec['diagnostic_cutoffs']};shared_max=max(shared_max,float(np.max(scaled)),float(np.max(scalars['carrier_RMS']))*scale)
  probe=probe_prediction.build(np,grid,phi[0],phi[1],guard,deadline_monotonic);probe_path=cdir/(cid+'-probe.json');new_json(probe_path,probe['summary'])
  with(cdir/(cid+'-probe-arrays.npz')).open('xb')as f:np.savez_compressed(f,**probe['arrays'])
  fixed=record['metrics']['regions'];row=dict(candidate_id=cid,electrodes=record['geometry']['pads'],metrics=metrics,score_burden_matched=metrics['joint_eight_surface_contact_burden_caps']['robust_minimum_ratio'],high_modulation_volumes=classification,
   global_hotspot_fixed1Vpp=fixed['total']['statistics']['maxTIS'],off_target_distribution_fixed1Vpp=fixed['off_target']['statistics']['maxTIS'],surface_distribution_fixed1Vpp=fixed['surface_0_5']['statistics']['maxTIS'],probe_prediction=probe['summary'],source_run_id=run.name,source_result_commit=spec['result_commit'],source_raw_SHA256={str(f):original['summary']['raw_artifacts'][cid+'-'+str(f)]['SHA256']for f in(2000,2010)},holds=original['summary']['holds'],candidate_adopted=False)
  candidates.append(row);view_candidates[cid]=_views(np,grid,scalars,E[0],E[1],row['electrodes'],scales,guard,deadline_monotonic);new_json(cdir/(cid+'-analysis.json'),row);new_json(out/('checkpoint-'+cid+'.json'),dict(status='candidate_cached_analysis_complete',candidate_id=cid,new_PDE_RHS=0,completed_candidates=len(candidates)));del phi,E,scalars,probe
 def sortkey(row):
  m=row['metrics']['joint_eight_surface_contact_burden_caps'];score=row['score_burden_matched'];return (-(score if score is not None else -math.inf),-(m['mean_ratio_to_B0']if m['mean_ratio_to_B0']is not None else -math.inf),-(m['P10_ratio_to_B0']if m['P10_ratio_to_B0']is not None else -math.inf),row['candidate_id'])
 ranked=sorted(candidates,key=sortkey)
 for rank,row in enumerate(ranked,1):row['provisional_rank']=rank if row['score_burden_matched']is not None else None
 top=[r['candidate_id']for r in ranked if r['score_burden_matched']is not None][:5];display=list(top)
 if spec['baseline_id']not in display:display.append(spec['baseline_id'])
 catalog=original['summary']['spec']['catalog']
 summary=dict(schema='task1-cached-design-search-analysis-result-v1',status='cached_provisional_rank_volume_probe_analysis_complete',spec=spec,baseline_id=spec['baseline_id'],candidates=candidates,provisional_top5=top,display_candidates_with_baseline=display,ranking_scope='Robust joint-burden matched electrical proxy, not selected or validated best electrodes. All eight originals and separate comparisons retained.',diagnostic_cutoffs=spec['diagnostic_cutoffs'],high_volume_cutoff_policy=spec['cutoff_policy'],new_PDE_RHS=0,source_run_id=run.name,source_result_commit=spec['result_commit'],publication_status=spec['publication_status'],
  roi_definitions=dict(original_geometry_and_weight_receipt=original['summary']['ROI_receipt'],target_definition=catalog['common_ROI'],classification_weights='Original native_region_weights m3 arrays; target128x128 boundary-square fractions and exactzoverlap, no cell-count weighting or volume renormalization'),
  power_topology=dict(original_source_convention=original['summary']['spec']['source_convention'],physical_pad_count=catalog['physical_pads'],independent_output_count=catalog['independent_outputs'],source_resistance_ohm=catalog['source_resistance_ohm'],return_topology=catalog['return_topology'],inactive_output=catalog['inactive_output']),holds=original['summary']['holds'],candidate_adopted=False,Windows_saved_verified=False)
 views=dict(schema='task1-design-search-views-v1',baseline_id=spec['baseline_id'],fixed_ranges=dict(xy_mm=[-25,25],depth_mm=[0,25.1],field_V_m=[0,shared_max]),candidates=view_candidates,raw_fields_clipped=False)
 new_json(out/'views.json',views);check(guard,deadline_monotonic);return dict(summary=summary,arrays={},views=views)
