"""Conditional common-return ellipse candidate; source preparation only.

No IO/scientific import/numerics on import. Root alone may run after the actual
fine-grid outcome is published/reviewed and a new positive decision is supplied.
Two immutable controls are metadata/raw/scalar aliases, never solved or scanned.
"""
import ast,copy,csv,gc,hashlib,io,json,math,time
from fractions import Fraction as F
from pathlib import Path
import ellipse_inputs
import fine_solver
import coarse_fields
SOURCE=Path('/dev/shm/task1-centroid-ellipse-20261025/source')
RUN=Path('/dev/shm/task1-centroid-ellipse-20261025-run')
NEW_ID=ellipse_inputs.NEW_ID
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
REGIONS=('total','target','surface_0_5','subsurface_5_10','remaining','off_target')
def require(ok,message):
 if not ok:raise ValueError(message)
def check(guard,deadline):
 guard()
 if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite conditional ellipse stage deadline')
def sha(path):return ellipse_inputs.digest(path)
def new(path,value):
 raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,indent=2)+'\n').encode()
 with Path(path).open('xb')as stream:stream.write(raw)
def archive(np,path,**arrays):
 with Path(path).open('xb')as stream:np.savez_compressed(stream,**arrays)
 require(0<Path(path).stat().st_size<80*1024**2,'Per-file approved publication bound80MiB')
 return dict(path=str(path),SHA256=sha(path),bytes=Path(path).stat().st_size)
def cv(value):return complex(value['real'],value['imaginary'])
def verify(descriptor,pins):
 p=Path(descriptor['path']);require(p.is_file()and not p.is_symlink()and p==p.resolve()and pins.get(str(p))==descriptor['SHA256']and p.stat().st_size==descriptor['bytes']and sha(p)==descriptor['SHA256'],'Exact original authenticated input '+str(p));return p
def load(np,descriptor,keys,pins,guard,deadline):
 check(guard,deadline);p=verify(descriptor,pins)
 with np.load(p,allow_pickle=False)as saved:
  require(set(keys).issubset(saved.files),'Required actual archive unavailable; do not fabricate/recompute controls');values={key:np.array(saved[key],copy=True)for key in keys}
 require(all(np.isfinite(v).all()for v in values.values()),'Complete finite original arrays');return values
def required_inputs(admission=None):return ellipse_inputs.required_inputs(admission)
def make_spec(admission=None):
 context=ellipse_inputs.make_spec(admission);require(context['field_version']=='native-lateral-half-face-v1+analytic-z-DtN-v1','Same authenticated coarse field estimator as immutable controls');b=context['controls']['B0']['record']['metrics']['regions'];cutoffs=[dict(cutoff_id='original-B0-target-AM-mean',value_V_m=b['target']['statistics']['maxTIS']['mean']),dict(cutoff_id='original-B0-offtarget-AM-P95',value_V_m=b['off_target']['statistics']['maxTIS']['p95'])]
 return dict(schema='task1-centroid-tangent-ellipse-screen-spec-v1',root_admission=context['root_admission'],inputs=context,candidate_id=NEW_ID,expected_new_driven_RHS=2,expected_new_angular_metric_evaluations=1,expected_immutable_control_aliases=2,expected_complete_conditions=3,new_eigen_solves=0,body=dict(diameter_mm=50.,layer_thickness_mm=[.1,5.,5.,15.]),field_version='native-lateral-half-face-v1+analytic-z-DtN-v1',diagnostic_cutoffs=cutoffs,cutoff_policy='Original B0-relative numerical diagnostics fixed before this candidate PDE, not physiological thresholds',geometry=dict(shape='analytic_ellipse',semimajor_mm=13.,semiminor_mm_formula='225/(pi*13)',orientation='Major axis tangential to each actual P23 centroid radial vector; minor axis radial',area_mm2_each=225.,centroid='Actual authenticated P23 physical-mask centroid; no fit or adjustment',preflight='Analytic maximum radius<25mm and complete strict-quadrant containment; otherwise block, no resize/reposition/body fallback'),partial_contact_known_failures_preserved=True,CPU_limit=4,total_RSS_plus_all_task_tmpfs_bytes=8000000000,output_forecast_bytes=150000000,raw_RSS_forecast_bytes=750000000,forecasts_unmeasured=True,source_only_unadmitted_until_root_decision=True,candidate_adopted=False)
def source_test_count():
 count=0
 for p in SOURCE.glob('test_*.py'):
  tree=ast.parse(p.read_text(),filename=str(p));count+=sum(1 for cls in tree.body if isinstance(cls,ast.ClassDef)for m in cls.body if isinstance(m,ast.FunctionDef)and m.name.startswith('test_'))
 return count
def validate_test_receipt(value,sources,count):
 require(value.get('status')=='passed'and value.get('model_source_sha256')==sources and value.get('model_source_test_count')==count and type(count)is int and count>0,'Actual successful prospective ellipse geometry/MMS tests bind canonical model sources')
 require(type(value.get('tests_run'))is int and value['tests_run']>=count and value.get('expected_total_tests')==value['tests_run'],'Actual successful count matches preregistered total before2RHS')
 return dict(passed=True,model_tests=count,actual_tests=value['tests_run'])
def _centroids(raw,metadata):
 """Root-only exact centroid of the published full .5mm-square union."""
 reader=csv.DictReader(io.StringIO(raw.decode()));require(reader.fieldnames==['pad','i','j','area_m2'],'Original actual P23 mask schema')
 cells={p:[]for p in range(4)};occupied=set()
 for row in reader:
  p,i,j=(int(row[k])for k in('pad','i','j'));require(p in cells and 0<=i<100 and 0<=j<100 and float(row['area_m2'])==.0005**2 and(i,j)not in occupied,'Original disjoint full faces, not a new mask/area repair');occupied.add((i,j));cells[p].append((i,j))
 centres=[];rows=[];by_pad={int(r['pad']):r for r in metadata}
 for p in range(4):
  require(len(cells[p])==900,'Original physical P23 pad225mm2 must remain unchanged')
  x=sum((F(-25)+F(2*i+1,4)for i,j in cells[p]),F(0))/900;y=sum((F(-25)+F(2*j+1,4)for i,j in cells[p]),F(0))/900;reported=by_pad[p]['centroid_mm'];delta=max(abs(float(x)-float(reported[0])),abs(float(y)-float(reported[1])));require(delta<=1e-10,'Actual CSV physical centroid disagrees with published receipt; no position fallback')
  centres.append((x,y));rows.append(dict(pad=p,exact_centroid_mm=[dict(numerator=v.numerator,denominator=v.denominator)for v in(x,y)],published_centroid_mm=reported,maximum_difference_mm=delta,limit_mm=1e-10,physical_area_mm2=225.,node_center_equals_full_square_centroid=True))
 return centres,dict(schema='task1-P23-actual-physical-centroid-check-v1',passed=True,rows=rows,new_position_fit=False)
def _graph(np,context,guard,deadline):
 data=load(np,context['graph_arrays'],['eigenvalues_per_m2','XY_m','ij'],context['input_sha256'],guard,deadline);e,xy,ij=data['eigenvalues_per_m2'],data['XY_m'],data['ij'];require(e.shape==(7860,)and xy.shape==ij.shape==(7860,2),'Same coarse original graph/eigen ABI')
 graph=context['graph_summary']['graph'];require(hashlib.sha256(xy.astype('<f8',copy=False).tobytes()).hexdigest()==graph['XY_float64_le_SHA256']and hashlib.sha256(ij.astype('<i4',copy=False).tobytes()).hexdigest()==graph['ij_int32_le_SHA256'],'Original actual XY/ij order');return e,xy,ij
def _cache(np,context,guard,deadline):
 m=context['Q_manifest'];require(m['shape']==[7860,7860]and m['dtype']=='<f8'and m['order']=='F','Original real Fortran Q only');Q=np.empty((7860,7860),dtype='<f8',order='F');at=0;proof=[]
 for row,remote in zip(m['chunks'],context['remote_Q_chunk_proofs']):
  check(guard,deadline);require(row['column_start']==at and row['SHA256']==remote['SHA256']and row['bytes']==remote['bytes']and remote['readback_passed']is True,'Actual retained-Q publication binding for every chunk');p=Path(row['path']);require(p.is_file()and not p.is_symlink()and p==p.resolve()and context['input_sha256'].get(str(p))==row['SHA256'],'Actual original local Q path')
  raw=p.read_bytes();end=row['column_stop'];require(len(raw)==row['bytes']==7860*(end-at)*8<=32*1024**2 and hashlib.sha256(raw).hexdigest()==row['SHA256'],'Full local Q SHA/bytes before decode');Q[:,at:end]=np.frombuffer(raw,dtype='<f8').reshape((7860,end-at),order='F');proof.append(dict(path=str(p),SHA256=row['SHA256'],before_passed=True,remote_commit=remote['publication_commit']));at=end;del raw
 require(at==7860 and np.isfinite(Q).all(),'Complete original real Q, no eigen fallback or complex matrix copy');return Q,proof
def _metadata_only(value):
 if value is None or type(value)in(str,bool,int):return True
 if type(value)is float:return math.isfinite(value)
 if isinstance(value,dict):return all(type(k)is str and _metadata_only(v)for k,v in value.items())
 if isinstance(value,(tuple,list)):return all(_metadata_only(v)for v in value)
 return False
def separated_stages(raw,post,collector=gc.collect):
 result=raw();require(_metadata_only(result),'Raw frame leaked Q/fields/profiles or non-JSON geometry objects');collector();return post(result)
def _raw_frame(np,spec,out,guard,deadline):
 import ellipse_contact
 context=spec['inputs'];p23=verify(context['P23_mask'],context['input_sha256']);centres,centroid_proof=_centroids(p23.read_bytes(),context['centres_metadata']);new(out/'actual-P23-centroid-proof.json',centroid_proof)
 preflight=ellipse_contact.preflight(centres,guard);new(out/'ellipse-analytic-preflight.json',preflight);require(preflight.get('passed')is True,'Analytic shape/body/quadrant preflight failed; no geometry repair/fallback')
 eigen,xy,ij=_graph(np,context,guard,deadline);patches=ellipse_contact.contact_patches(centres,ij,h_mm=.5,guard=guard,deadline=deadline);receipt=patches['receipt'];new(out/'ellipse-contact-quadrature-receipt.json',receipt);require(receipt.get('passed')is True,'Bounded contact-area error certificate unavailable; no rescale/forced-cell fallback')
 lookup={(int(i),int(j)):k for k,(i,j)in enumerate(ij)};rows=patches['patches'];pads=np.asarray([r['pad']for r in rows],np.int32);cells=np.asarray([lookup[int(r['i']),int(r['j'])]for r in rows],np.int32);areas=np.asarray([r['area_m2']for r in rows],float);require(set(pads.tolist())=={0,1,2,3}and np.all(areas>0)and np.all(areas<=.0005**2*(1+1e-10)),'Positive actual fractional contacts and fixed4pad mapping');require(len(set(zip(pads.tolist(),cells.tolist())))==len(cells),'Unique physical contact tuples')
 for p in range(4):require(abs(float(areas[pads==p].sum())-.000225)/.000225<=1e-10,'Actual unscaled ellipse area sum225mm2 within fixed numerical gate')
 with(out/'ellipse-fractional-contact-mask.csv').open('x')as stream:stream.write('pad,i,j,area_m2\n'+'\n'.join(str(r['pad'])+','+str(r['i'])+','+str(r['j'])+','+format(r['area_m2'],'.17e')for r in rows)+'\n')
 require(np.max(np.bincount(cells,weights=areas,minlength=7860))<=.0005**2*(1+1e-10),'No contact overlap beyond actual cell face')
 geometry=load(np,context['common_grid_ROI'],['grid','z_faces_m'],context['input_sha256'],guard,deadline);grid=geometry['grid'];faces=geometry['z_faces_m'];require(grid.shape==(793860,5)and faces.shape==(102,)and np.allclose(faces[[0,8,27,45,101]],[0,.0001,.0051,.0101,.0251],rtol=0,atol=1e-12),'Original fixed101-plane physical depth grid');require(np.array_equal(grid[:,:2],np.tile(xy*1000,(101,1))),'Exact original graph/field ordering');zs=grid[::7860,2]/1000;layers=grid[::7860,3].astype(np.int32);del grid,geometry
 Q,cacheproof=_cache(np,context,guard,deadline);result={};directory=out/'rhs';directory.mkdir()
 for frequency,output in((2000,0),(2010,1)):
  gamma=[cv(v)for v in context['catalog']['gamma_by_frequency'][str(frequency)]];profile=coarse_fields.profiles(np,Q,eigen,gamma,zs,.0005,guard,deadline);za=cv(context['catalog']['z_by_frequency'][str(frequency)]);solution=fine_solver.solve(np,Q,profile,pads,cells,areas,za,output,.0005,guard,deadline);proof=solution['proof'];proof.update(candidate_id=NEW_ID,frequency_Hz=frequency,physical_pad_count=4,independent_outputs=2,source_allocation_amplitudes=[1.,1.],source_pair_return_topology='Two output nodes, physicalpads2/3hardcommonGND; inactiveidealoutput0Vthrough50ohm',geometry_receipt_SHA256=sha(out/'ellipse-contact-quadrature-receipt.json'))
  new(directory/(NEW_ID+'-'+str(frequency)+'-solve-proof.json'),proof);require(proof['passed']and proof['actual_new_RHS']==1,'New ellipse CEM physical gate failure; no relaxed limits')
  phi,E,J=coarse_fields.fields(np,Q,profile,solution['coeff'],ij,layers,.0005,guard,deadline);raw=archive(np,directory/(NEW_ID+'-'+str(frequency)+'-raw.npz'),phi_peak_V=phi,E_peak_V_m=E,interface_downward_J_peak_A_m2=J,modal_surface_coeff=solution['coeff'],phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],contact_current_peak_A=solution['contact_current'],contact_normal_J_peak_A_m2=solution['contact_J'],contact_drop_peak_V=solution['contact_drop'],contact_pad=pads,contact_xy_index=cells,contact_area_m2=areas,layer_complex_power_W=solution['layer_power']);result[str(frequency)]=dict(raw=raw,proof=proof);new(out/('checkpoint-new-ellipse-'+str(frequency)+'.json'),dict(status='ellipse_raw_saved',actual_new_RHS_so_far=len(result),angular_metrics=0,raw=raw));del phi,E,J,solution,profile
 for row in cacheproof:check(guard,deadline);require(sha(row['path'])==row['SHA256'],'Full Q SHA after exactly2new ellipse RHS');row['after_passed']=True
 new(out/'Q-before-after-proof.json',cacheproof);return dict(raw_by_frequency=result,new_RHS=2,geometry_receipt=receipt,centroid_proof=centroid_proof,cache_reuse=dict(new_eigen_solves=0,all_chunks_before_after=True))
def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(callable(guard)and spec==make_spec(spec['root_admission']),'Exact future-root-admitted ellipse scope/source/fine-outcome binding');out=Path(output_dir or RUN);require(out==RUN and out.is_dir()and out==out.resolve()and not out.is_symlink()and not(out/'raw-manifest.json').exists(),'Unique root-created candidate output, no overwrite');check(guard,deadline_monotonic)
 receipt=out/'synthetic-test-receipt.json';require(receipt.is_file()and not receipt.is_symlink()and receipt.stat().st_size<2*1024**2,'Actual passed bounded ellipse geometry/MMS tests required first');testproof=validate_test_receipt(json.loads(receipt.read_bytes()),spec['inputs']['source_sha256'],source_test_count());new(out/'before-new-RHS-test-proof.json',testproof)
 import numpy as np
 import ellipse_post
 def post(raw):
  new(out/'Q-release-boundary.json',dict(raw_frame_returned_only_JSON=True,Q_passed_to_metrics=False,actual_new_RHS=2));new(out/'raw-manifest.json',raw);return ellipse_post.build(np,spec,raw,guard,deadline_monotonic,out)
 return separated_stages(lambda:_raw_frame(np,spec,out,guard,deadline_monotonic),post)
