"""Finite P23/B0 adjacent-XY sensitivity, entirely deferred to sole root owner.

Exactly3 new real CEM RHS after1 mandatory authenticated fine B0 restoration.
No fallback fourth solve, new eigen calculation or source-time data/numerics.
Q is confined to raw-frame calls returning JSON metadata; metrics run after GC.
"""
import ast,csv,gc,hashlib,io,json,time
from pathlib import Path
import fine_inputs
import fine_fields
import fine_solver
import physical_overlap
SOURCE=Path('/dev/shm/task1-P23-fineXY-20261025/source')
RUN=Path('/dev/shm/task1-P23-fineXY-20261025-run')
NAMES=('B0','P23');FREQUENCIES=(2000,2010);COUNTS=(4,19,18,56)
def require(ok,message):
 if not ok:raise ValueError(message)
def check(guard,deadline):
 guard()
 if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite fine-XY stage deadline')
def pair(value):return fine_solver.pair(value)
def cv(value):return complex(value['real'],value['imaginary'])
def sha(path):return fine_inputs.digest(path)
def new(path,value):
 raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,indent=2)+'\n').encode()
 with Path(path).open('xb')as stream:stream.write(raw)
def archive(np,path,**arrays):
 with Path(path).open('xb')as stream:np.savez_compressed(stream,**arrays)
 require(0<Path(path).stat().st_size<80*1024**2,'Per-file raw/scalar publication bound80MiB')
 return dict(path=str(path),SHA256=sha(path),bytes=Path(path).stat().st_size)
def verified_bytes(descriptor,pins):
 path=Path(descriptor['path']);require(path.is_file()and not path.is_symlink()and path==path.resolve()and path.stat().st_size==descriptor['bytes']and pins.get(str(path))==descriptor['SHA256']and sha(path)==descriptor['SHA256'],'Exact authenticated immutable input bytes '+str(path))
 return path
def load(np,descriptor,keys,pins,guard,deadline):
 check(guard,deadline);path=verified_bytes(descriptor,pins)
 with np.load(path,allow_pickle=False)as saved:
  require(set(keys).issubset(saved.files),'Required original raw ABI missing; never fabricate/resolve '+str(path));result={key:np.array(saved[key],copy=True)for key in keys}
 require(all(np.isfinite(v).all()for v in result.values()),'All required raw values finite')
 return result
def required_inputs(admission=None):return fine_inputs.required_inputs(admission)
def make_spec(admission=None):
 context=fine_inputs.make_spec(admission)
 return dict(schema='task1-P23-B0-fineXY-screen-spec-v1',root_admission=context['root_admission'],inputs=context,new_eigen_solves=0,maximum_new_driven_RHS=3,mandatory_reused_fine_B0_2000_RHS=1,automatic_fourth_RHS_fallback=False,common_depth_layer_counts=list(COUNTS),full_angular_metric_evaluations=2,SC4_only_angular_metric_evaluations=2,coarse93_bulk_angular_evaluations=0,duplicate_full_coarse_scalar_archives=False,fine_evaluation_cells=793848,coarse_common_evaluation_cells=762420,field_estimator_version='native-lateral-half-face-v1+analytic-z-DtN-v1',raw_stage_returns_only_metadata=True,Q_resident_during_metrics=False,output_forecast_bytes=350000000,raw_RSS_forecast_bytes=800000000,unmeasured_forecasts_not_resource_cap_increases=True,CPU_limit=4,total_RSS_plus_all_task_tmpfs_bytes=8000000000,candidate_adopted=False)
def source_test_count():
 count=0
 for path in SOURCE.glob('test_*.py'):
  tree=ast.parse(path.read_text(),filename=str(path));count+=sum(1 for cls in tree.body if isinstance(cls,ast.ClassDef)for method in cls.body if isinstance(method,ast.FunctionDef)and method.name.startswith('test_'))
 return count
def validate_test_receipt(receipt,model_sources,model_test_count):
 require(receipt.get('status')=='passed'and receipt.get('model_source_sha256')==model_sources,'Actual root-run synthetic/MMS tests bind the complete published canonical model sources')
 require(type(model_test_count)is int and model_test_count>0 and type(receipt.get('model_source_test_count'))is int and receipt['model_source_test_count']==model_test_count,'Prospectively counted actual model test definitions')
 require(type(receipt.get('tests_run'))is int and receipt['tests_run']>=model_test_count and receipt.get('expected_total_tests')==receipt['tests_run'],'Actual root-run count equals preregistered total tests before new RHS')
 return dict(passed=True,tests_run=receipt['tests_run'],model_source_test_count=model_test_count)
def _graph(np,context,which,guard,deadline):
 data=load(np,context['graph_arrays'][which],['eigenvalues_per_m2','XY_m','ij'],context['input_sha256'],guard,deadline);n=8184 if which=='fine'else 7860
 e,xy,ij=data['eigenvalues_per_m2'],data['XY_m'],data['ij'];require(e.shape==(n,)and xy.shape==ij.shape==(n,2),'Actual graph/eigen node ABI')
 graph=context['graph_summaries'][which]['graph'];require(hashlib.sha256(xy.astype('<f8',copy=False).tobytes()).hexdigest()==graph['XY_float64_le_SHA256']and hashlib.sha256(ij.astype('<i4',copy=False).tobytes()).hexdigest()==graph['ij_int32_le_SHA256'],'Actual graph coordinate/index order SHA')
 return e,xy,ij
def _cache(np,context,which,guard,deadline):
 manifest=context['cache_manifests'][which];n=manifest['shape'][0];Q=np.empty((n,n),dtype='<f8',order='F');at=0;proof=[]
 for row,remote in zip(manifest['chunks'],context['remote_Q_chunk_proofs'][which]):
  check(guard,deadline);require(row['column_start']==at and row['SHA256']==remote['SHA256']and row['bytes']==remote['bytes']and remote['readback_passed']is True,'Every original Q chunk bound to actual retained remote publication')
  p=Path(row['path']);require(p.is_file()and not p.is_symlink()and p==p.resolve()and context['input_sha256'].get(str(p))==row['SHA256'],'Actual original Q chunk path')
  raw=p.read_bytes();end=row['column_stop'];require(len(raw)==row['bytes']==n*(end-at)*8<=32*1024**2 and hashlib.sha256(raw).hexdigest()==row['SHA256'],'Actual Q chunk full SHA/byte count before decode')
  Q[:,at:end]=np.frombuffer(raw,dtype='<f8').reshape((n,end-at),order='F');proof.append(dict(path=str(p),SHA256=row['SHA256'],bytes=row['bytes'],before_passed=True,remote_publication_commit=remote['publication_commit']));at=end;del raw
 require(at==n and Q.flags.f_contiguous and np.isfinite(Q).all(),'Complete finite real Fortran Q, never cast whole matrix to complex')
 return Q,proof
def _cache_after(proof,guard,deadline):
 for row in proof:check(guard,deadline);require(sha(row['path'])==row['SHA256'],'Full Q chunk SHA after raw frame');row['after_passed']=True
def _contacts(np,raw,ij,h):
 lookup={(int(i),int(j)):k for k,(i,j)in enumerate(ij)};pads=[];cells=[];areas=[]
 for row in csv.DictReader(io.StringIO(raw.decode())):
  p=int(row['pad']);key=(int(row['i']),int(row['j']));area=float(row['area_m2']);require(p in(0,1,2,3)and key in lookup and 0<area<=h*h*(1+1e-10),'Actual physical contact patch and surface node')
  pads.append(p);cells.append(lookup[key]);areas.append(area)
 p=np.asarray(pads,np.int32);c=np.asarray(cells,np.int32);a=np.asarray(areas,float);require(len(set(zip(p.tolist(),c.tolist())))==len(c),'Unique physical pad/node contact rows')
 require(np.max(np.bincount(c,weights=a,minlength=len(ij)))<=h*h*(1+1e-10),'No overcovered fine face')
 for pad in range(4):require(abs(float(a[p==pad].sum())-.000225)/.000225<=1e-10,'Preserve each225mm2 physical pad without scaling')
 return p,c,a
def _metadata_frame(value):
 json.dumps(value,allow_nan=False);return value
def _geometry_frame(np,spec,out,guard,deadline):
 context=spec['inputs'];faces=context['eval_face_receipts']['fine']['z_faces_m'];old=context['eval_face_receipts']['coarse']['z_faces_m'];proof=fine_fields.common_bulk_depth_identity(np,old,faces);result={}
 for which,h in(('fine',.05/102),('coarse',.0005)):
  eigen,xy,ij=_graph(np,context,which,guard,deadline);geom=fine_fields.geometry(np,xy,ij,faces,h,guard,deadline)
  desc=archive(np,out/(which+'-common97-grid-ROI.npz'),grid=geom['grid'],ij=ij,z_faces_m=geom['faces_m'],**{k+'_volume_weight_m3':v for k,v in geom['weights'].items()});new(out/(which+'-ROI-receipt.json'),geom['ROI_receipt']);result[which]=desc;del eigen,xy,ij,geom
 new(out/'common97-bulk-depth-identity.json',proof);return _metadata_frame(result)
def _raw_arrays(solution,pads,cells,areas):
 return dict(modal_surface_coeff=solution['coeff'],phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],contact_current_peak_A=solution['contact_current'],contact_normal_J_peak_A_m2=solution['contact_J'],contact_drop_peak_V=solution['contact_drop'],contact_pad=pads,contact_xy_index=cells,contact_area_m2=areas,layer_complex_power_W=solution['layer_power'])
def _fine_raw_frame(np,spec,out,guard,deadline):
 context=spec['inputs'];eigen,xy,ij=_graph(np,context,'fine',guard,deadline);Q,cacheproof=_cache(np,context,'fine',guard,deadline);h=.05/102;faces=np.asarray(context['eval_face_receipts']['fine']['z_faces_m']);zs=(faces[:-1]+faces[1:])/2.;layers=np.repeat(np.arange(4),COUNTS)
 prepared=out/'prepared';prepared.mkdir();p23path=verified_bytes(context['P23_mask'],context['input_sha256']);overlap=physical_overlap.remesh_full_cell_union(p23path.read_bytes(),102,ij);require(overlap['proof']['graph_coverage_verified_against_supplied_nodes']is True,'Actual P23 overlap maps to authenticated fine ij')
 rows=['pad,i,j,area_m2']+[str(r['pad'])+','+str(r['i'])+','+str(r['j'])+','+format(r['area_m2'],'.17e')for r in overlap['patches']];rawP23=('\n'.join(rows)+'\n').encode();mask=prepared/'P23-exact-physical-union-XY102.csv'
 with mask.open('xb')as stream:stream.write(rawP23)
 new(prepared/'P23-physical-overlap-proof.json',dict(original_mask=context['P23_mask'],fine_graph_arrays=context['graph_arrays']['fine'],mask_SHA256=sha(mask),**overlap['proof']));rawB0=verified_bytes(context['fine_B0_mask'],context['input_sha256']).read_bytes();contacts={'B0':_contacts(np,rawB0,ij,h),'P23':_contacts(np,rawP23,ij,h)};del overlap,rawP23,rawB0
 result={name:{}for name in NAMES};new_count=0;restore_passed=False
 for frequency,output in((2000,0),(2010,1)):
  gamma=[cv(v)for v in context['gamma_by_frequency'][str(frequency)]];profile=fine_fields.profiles(np,Q,eigen,gamma,zs,h,guard,deadline);za=cv(context['z_by_frequency'][str(frequency)])
  for name in NAMES:
   pads,cells,areas=contacts[name];cached=None;old=None
   if name=='B0'and frequency==2000:
    old=load(np,context['fine_B0_raw'],['phi_surface','metal','modal_surface_coeff','contact_pad','contact_xy_index','contact_area_m2'],context['input_sha256'],guard,deadline)
    require(np.array_equal(old['contact_pad'],pads)and np.array_equal(old['contact_xy_index'],cells)and np.array_equal(old['contact_area_m2'],areas),'Mandatory old fine B0 mask/contact order/areas match; failure blocks before any new RHS')
    require(old['phi_surface'].shape==(2,len(ij))and old['metal'].shape==(2,2)and old['modal_surface_coeff'].shape==(2,len(ij)),'Mandatory cached fine B0 surface/metal/modal ABI')
    cached=dict(phi_surface=old['phi_surface'][0].copy(),metal=old['metal'][0].copy())
   else:require(restore_passed,'No new fine RHS until mandatory B0 restore passed all fresh gates')
   solution=fine_solver.solve(np,Q,profile,pads,cells,areas,za,output,h,guard,deadline,cached=cached);proof=solution['proof'];proof.update(candidate=name,frequency_Hz=frequency,grid='XY102',original_solve_provenance=context['fine_B0_raw']if cached is not None else None)
   if cached is not None:
    delta=float(np.linalg.norm(solution['coeff']-old['modal_surface_coeff'][0]));den=max(float(np.linalg.norm(old['modal_surface_coeff'][0])),1e-12);proof['restored_modal_relative_error']=delta/den;proof['modal_restore_limit']=2e-7;proof['passed']=bool(proof['passed']and delta/den<=2e-7);new(out/'fine-B0-2000-mandatory-restore-proof.json',proof);restore_passed=proof['passed'];del old,cached
   new(out/'rhs'/(name+'-XY102-'+str(frequency)+'-proof.json'),proof);require(proof['passed'],'Fine source physical/residual/KCL/power/passivity/restore failure, no fallback solve')
   new_count+=proof['actual_new_RHS'];require(new_count<=3,'Exactly three prospective new RHS maximum, never a fourth fallback')
   phi,E,interface=fine_fields.fields(np,Q,profile,solution['coeff'],ij,layers,h,guard,deadline);desc=archive(np,out/'rhs'/(name+'-XY102-'+str(frequency)+'-raw.npz'),phi_peak_V=phi,E_peak_V_m=E,interface_downward_J_peak_A_m2=interface,**_raw_arrays(solution,pads,cells,areas));result[name][str(frequency)]=dict(raw=desc,proof=proof)
   new(out/('checkpoint-fine-'+name+'-'+str(frequency)+'.json'),dict(status='fine_raw_saved',candidate=name,frequency_Hz=frequency,actual_new_driven_RHS_so_far=new_count,mandatory_reuse_passed=restore_passed,raw=desc));del phi,E,interface,solution
  del profile
 require(new_count==3 and restore_passed,'Exactly3new fine RHS plus1 mandatory restored response');_cache_after(cacheproof,guard,deadline);new(out/'fine-Q-before-after-proof.json',cacheproof)
 return _metadata_frame(result)
def _coarse_raw_frame(np,spec,out,guard,deadline):
 context=spec['inputs'];eigen,xy,ij=_graph(np,context,'coarse',guard,deadline);Q,cacheproof=_cache(np,context,'coarse',guard,deadline);h=.0005;faces=np.asarray(context['eval_face_receipts']['fine']['z_faces_m']);zs=(faces[:4]+faces[1:5])/2.;layers=np.zeros(4,np.int32);result={name:{}for name in NAMES}
 for frequency,output in((2000,0),(2010,1)):
  profile=fine_fields.profiles(np,Q,eigen,[cv(v)for v in context['gamma_by_frequency'][str(frequency)]],zs,h,guard,deadline);za=cv(context['z_by_frequency'][str(frequency)])
  for name in NAMES:
   original=context['coarse_raw'][name][str(frequency)];old=load(np,original,['phi_surface_peak_V','metal_peak_V','modal_surface_coeff','contact_pad','contact_xy_index','contact_area_m2'],context['input_sha256'],guard,deadline);pads,cells,areas=old['contact_pad'],old['contact_xy_index'],old['contact_area_m2'];require(pads.shape==cells.shape==areas.shape and set(pads.tolist())=={0,1,2,3}and np.all(areas==h*h),'Actual original full-face coarse contact ABI')
   solution=fine_solver.solve(np,Q,profile,pads,cells,areas,za,output,h,guard,deadline,cached=dict(phi_surface=old['phi_surface_peak_V'],metal=old['metal_peak_V']));proof=solution['proof'];error=float(np.linalg.norm(solution['coeff']-old['modal_surface_coeff']))/max(float(np.linalg.norm(old['modal_surface_coeff'])),1e-12);proof.update(candidate=name,frequency_Hz=frequency,grid='XY100-common97-SC4-supplement',original_raw=original,modal_restore_relative_error=error);require(proof['passed']and proof['actual_new_RHS']==0 and error<=2e-7,'Cached coarse SC4 resynthesis must pass unchanged circuit/coefficients, never run a new solve')
   phi,E,interface=fine_fields.fields(np,Q,profile,solution['coeff'],ij,layers,h,guard,deadline);desc=archive(np,out/'rhs'/(name+'-XY100-common97-SC4-'+str(frequency)+'.npz'),phi_SC4_peak_V=phi,E_SC4_peak_V_m=E,**_raw_arrays(solution,pads,cells,areas));result[name][str(frequency)]=dict(raw=desc,proof=proof);new(out/'rhs'/(name+'-XY100-common97-SC4-'+str(frequency)+'-proof.json'),proof);del old,solution,phi,E,interface
  del profile
 _cache_after(cacheproof,guard,deadline);new(out/'coarse-Q-before-after-proof.json',cacheproof);return _metadata_frame(result)
def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(callable(guard)and spec==make_spec(spec['root_admission']),'Exact root-admitted reviewed fine-refinement sources/inputs');out=Path(output_dir or RUN);require(out==RUN and out.is_dir()and out==out.resolve()and not out.is_symlink(),'Unique root-created canonical output');require(not(out/'raw-manifest.json').exists(),'Preserve every previous attempt and partial field');check(guard,deadline_monotonic)
 testpath=out/'synthetic-test-receipt.json';require(testpath.is_file()and not testpath.is_symlink()and testpath.stat().st_size<2*1024**2,'Actual successful tiny MMS/projection/overlay test receipt required before3newRHS');testproof=validate_test_receipt(json.loads(testpath.read_bytes()),spec['inputs']['source_sha256'],source_test_count());new(out/'before-new-RHS-test-verification.json',testproof)
 import numpy as np
 (out/'rhs').mkdir();manifest=dict(geometry=_geometry_frame(np,spec,out,guard,deadline_monotonic));gc.collect();manifest['fine']=_fine_raw_frame(np,spec,out,guard,deadline_monotonic);gc.collect();new(out/'fine-raw-Q-release-boundary.json',dict(raw_frame_returned_only_JSON=True,Q_passed_to_metrics=False,actual_new_driven_RHS=3,mandatory_B0_restored=1));manifest['coarse_SC4']=_coarse_raw_frame(np,spec,out,guard,deadline_monotonic);gc.collect();new(out/'all-Q-release-boundary.json',dict(raw_frames_returned_only_JSON=True,Q_passed_to_metrics=False,new_coarse_RHS=0,new_eigen_solves=0,actual_new_driven_RHS=3));manifest['Q_frames_returned']=True;manifest['GC_before_postprocessing']=True;new(out/'raw-manifest.json',manifest)
 import fine_post
 result=fine_post.build(np,spec,manifest,guard,deadline_monotonic,out);require(result['summary']['actual_new_driven_RHS']==3 and result['summary']['candidate_adopted']is False,'Actual fine sensitivity count, no convergence/adoption substitution');return result
