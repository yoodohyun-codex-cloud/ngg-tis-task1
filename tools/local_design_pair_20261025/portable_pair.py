"""Portable path/input adapter for two assigned local designs, not a Windows owner.

Import performs no input reads, geometry work, NumPy imports or calculations.
Only the future validated Windows owner may call the numerical APIs below.
The original Linux eight-layout build/worker is deliberately not exposed.
"""
from __future__ import annotations
import hashlib,importlib,json,math,sys
from fractions import Fraction
from pathlib import Path,PurePosixPath

SOURCE=Path(__file__).resolve().parent
MANIFEST_SHA256='f6429dbf2dc9e6f5cd63214d9ac69185834863c86f9d31d8ae3435b376120d4a'
CATALOG_SHA256='c893edb20cc28a793c66304cc02900bff2cd23b887740bd5e98a9a9622b8da04'
PORTABLE_ROI_SHA256='8591056b828dc6cec031b6218ab1fca0c4157bb5c292bbae2dbdc9a94eeec24e'
H=.0005;NXY=7860;FREQUENCIES=(2000,2010);COUNTS=(8,19,18,56)
IDS=('LOCAL14-c9-diagonal','LOCAL16-c8p5-diagonal')
EPS0=8.8541878128e-12

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def encoded(value):return(json.dumps(value,allow_nan=False,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def _json(path,expected):
 path=Path(path);require(path.is_file()and not path.is_symlink()and path.stat().st_size<2*1024**2,'Bounded portable metadata')
 require(sha(path)==expected,'Pinned portable metadata SHA');return json.loads(path.read_text())
def _relative(root,name):
 posix=PurePosixPath(name)
 require(not posix.is_absolute()and all(part not in('','.','..')for part in posix.parts)and ':'not in name and '\\'not in name,'Safe local-relative artifact path')
 root=Path(root).resolve();path=root.joinpath(*posix.parts)
 require(path.resolve().is_relative_to(root)and not path.is_symlink(),'Artifact remains inside selected local root');return path
def manifest():return _json(SOURCE/'input-manifest.json',MANIFEST_SHA256)
def catalog():
 value=_json(SOURCE/'local-candidates.json',CATALOG_SHA256)
 require(tuple(c['candidate_id']for c in value['candidates'])==IDS and value['maximum_new_driven_RHS']==4,'Exact two conditional assignments only')
 return value
def required_inputs(local_root):
 """Return local paths/expected hashes without opening raw arrays or caches."""
 return {str(_relative(local_root,row['local_relative_path'])):row['SHA256']for row in manifest()['files']}
def _artifact(local_root,logical):
 rows=[row for row in manifest()['files']if row['logical_artifact']==logical]
 require(len(rows)==1,'One explicitly declared logical artifact '+logical);row=rows[0]
 return _relative(local_root,row['local_relative_path']),row
def verify_inputs(local_root,guard):
 """Owner-called full input SHA pass; includes the existing real-Q cache."""
 require(callable(guard),'Validated finite owner guard required')
 for row in manifest()['files']:
  guard();path=_relative(local_root,row['local_relative_path'])
  require(path.is_file()and not path.is_symlink()and path.stat().st_size==row['bytes']and sha(path)==row['SHA256'],'Portable source/input integrity '+row['logical_artifact'])
 return dict(passed=True,scope='Byte identity only; not Windows owner, RAM, lock, numerical or experimental validation')
def _new(path,raw):
 path=Path(path)
 if path.exists():require(path.is_file()and not path.is_symlink()and path.read_bytes()==raw,'Preserve different prepared input '+str(path))
 else:
  with path.open('xb')as stream:stream.write(raw)
def _mask(candidate):
 h=Fraction(1,2000);radius=Fraction(1,40);covered=set();lines=['pad,i,j,area_m2'];pads=[]
 for pad in candidate['pads']:
  p=pad['pad'];w=Fraction(str(pad['width_mm']))/1000;d=Fraction(str(pad['height_mm']))/1000
  x,y=(Fraction(str(v))/1000 for v in pad['center_mm']);bounds=(x-w/2,x+w/2,y-d/2,y+d/2)
  require(p in range(4)and pad['node']==('out'+str(p)if p<2 else'GND')and pad['rotation_deg']==0,'Explicit four-pad/two-output mapping')
  require(w>0 and d>0 and all(a*a+b*b<radius*radius for a in bounds[:2]for b in bounds[2:]),'Untrimmed physical pad inside D50')
  indices=[(v+radius)/h for v in bounds];require(all(v.denominator==1 for v in indices),'Grid-aligned full-face local geometry')
  i0,i1,j0,j1=map(int,indices);require(0<=i0<i1<=100 and 0<=j0<j1<=100,'In-range XY100 contact indices');area=Fraction(0)
  for j in range(j0,j1):
   for i in range(i0,i1):
    xx=-radius+(Fraction(i)+Fraction(1,2))*h;yy=-radius+(Fraction(j)+Fraction(1,2))*h
    require(xx*xx+yy*yy<radius*radius and(i,j)not in covered,'Disjoint full-face graph contacts');covered.add((i,j));area+=h*h
    lines.append('%d,%d,%d,%s'%(p,i,j,format(float(h*h),'.17g')))
  require(area==w*d,'Actual local candidate area; no225mm2 assumption')
  pads.append(dict(pad=p,node=pad['node'],width_mm=pad['width_mm'],height_mm=pad['height_mm'],center_mm=pad['center_mm'],analytic_area_m2=float(area),represented_area_m2=float(area),all_fraction_exactly_one=True))
 return('\n'.join(lines)+'\n').encode(),pads
def prepare_spec(local_root,output_dir):
 """Metadata/geometry preparation only; does not grant execution or a lease.

No Q/graph NPZ is opened. The future Windows owner must call verify_inputs,
validate its Job/lease and freeze/read back these generated bytes first.
"""
 out=Path(output_dir).resolve();require(out.is_dir()and not out.is_symlink(),'Owner-created unique local output directory')
 mp,mr=_artifact(local_root,'material_receipt');cp,cr=_artifact(local_root,'contact_receipt')
 material=_json(mp,mr['SHA256']);contact=_json(cp,cr['SHA256'])
 require(contact['Rs_subtractions']==1 and contact['measurement_area_multiplications']==1 and contact['division_by_two']is False,'Existing once-Rs/area handling unchanged')
 rows={(r['layer'],int(r['frequency_Hz'])):r for r in material['rows']};zr={int(r['frequency_Hz']):r for r in contact['rows']};gamma={};specific={}
 for f in FREQUENCIES:
  gamma[str(f)]=[]
  for layer in('sc','dermis','fat','muscle'):
   r=rows[layer,f];s=float(r['sigma_S_m']);e=float(r['epsilon_r']);require(s>0 and e>0 and math.isfinite(s+e),'Published passive surrogate row')
   gamma[str(f)].append(dict(real=s,imaginary=2*math.pi*f*EPS0*e))
  specific[str(f)]=dict(real=zr[f]['area_real_ohm_m2'],imaginary=zr[f]['area_imag_ohm_m2'])
 cases=[];pins=required_inputs(local_root);(out/'masks').mkdir(exist_ok=True)
 for candidate in catalog()['candidates']:
  raw,pads=_mask(candidate);path=out/'masks'/(candidate['candidate_id']+'.csv');_new(path,raw);pins[str(path)]=hashlib.sha256(raw).hexdigest()
  canonical=dict(geometry_fixed=candidate['geometry_fixed'],pads=candidate['pads'],circuit=candidate['circuit'],frequencies_Hz=list(FREQUENCIES),
   material_SHA256=mr['SHA256'],contact_SHA256=cr['SHA256'],gamma_by_frequency=gamma,z_by_frequency=specific,
   portable_adapter_SHA256=sha(__file__),portable_ROI_SHA256=PORTABLE_ROI_SHA256,input_manifest_SHA256=MANIFEST_SHA256,candidate_catalog_SHA256=CATALOG_SHA256,
   ROI=dict(primary_radius_mm=5,primary_depth_mm=[15,20],depth_origin='physical top z0',depth_axis='+z',surface_depth_mm=[0,5],off_target='whole represented domain minus fractional primary ROI',
    volume_weight_ABI='native centre-inside D50 whole XY cells; exact depth overlap; target lateral128x128 midpoint boundary subcells; m3 weights; no analytic-volume renormalization'),
   field_version='native-lateral-half-face-v1+analytic-z-DtN-v1',metric_version='task1-provisional-coarse-dtn-screen-metrics-v1',
   modulation_definition='peak 2min(abs(u dot E2000),abs(u dot E2010)); max over same2074 real unit directions is sampled lower bound',
   grid=dict(nx=100,h_m=H,nxy=NXY,layer_counts=list(COUNTS),cells=793860),
   scientific_source_SHA256={r['logical_artifact']:r['SHA256']for r in manifest()['files']if r['bundled_source']})
  digest=hashlib.sha256(encoded(canonical)).hexdigest();config=out/(candidate['candidate_id']+'-canonical-config.json');_new(config,encoded(canonical));pins[str(config)]=digest
  cases.append(dict(candidate_id=candidate['candidate_id'],run_id=candidate['run_id'],canonical_config_SHA256=digest,canonical_config_path=str(config),mask_path=str(path),mask_sha256=pins[str(path)],pads=pads,
   assignment_status='assigned_waiting_adapter_and_lease',execution_permitted=False,lease=None,reuse_baseline_2000=False,maximum_new_driven_RHS=2))
 spec=dict(schema='task1-portable-local-pair-prepared-spec-v1',candidates=cases,gamma_by_frequency=gamma,z_by_frequency=specific,input_pins=pins,
  frequencies_Hz=list(FREQUENCIES),grid=dict(nx=100,nxy=NXY,h_m=H,layer_counts=list(COUNTS),cells=793860),maximum_new_driven_RHS=4,
  execution_permitted=False,lease=None,Windows_owner_adapter_validated=False,baseline_physics_reused=False,first8_source_commit=manifest()['first8_source_commit'])
 _new(out/'local-pair-spec.json',encoded(spec));return spec
def scientific_kernel(local_root):
 """Load unchanged portable low-level physics functions, never Linux build().

Caller must already own a validated Windows Job/CAS lease and finite guard.
This source-loading API alone does not authenticate that execution context.
"""
 folder=_relative(local_root,'kernel');require(folder.is_dir(),'Verified local kernel folder required')
 for row in manifest()['files']:
  if row['bundled_source']:
   path=_relative(local_root,row['local_relative_path']);require(sha(path)==row['SHA256'],'Frozen first8 scientific source identity')
 if'design_screen'in sys.modules:require(Path(sys.modules['design_screen'].__file__).resolve()==folder/'design_screen.py','Fresh isolated local process; no model module alias contamination')
 sys.path.insert(0,str(folder));core=importlib.import_module('design_screen')
 roi_path=_relative(local_root,'portable_native_roi.py');require(sha(roi_path)==PORTABLE_ROI_SHA256,'Exact portable native-ROI source')
 if'portable_native_roi'in sys.modules:require(Path(sys.modules['portable_native_roi'].__file__).resolve()==roi_path,'No native-ROI module alias contamination')
 sys.path.insert(0,str(Path(local_root).resolve()));roi=importlib.import_module('portable_native_roi')
 return dict(profile=core._profiles,solve=core._solve,reconstruct=core._fields,mask=core._mask,
  field=importlib.import_module('provisional_field'),metrics=importlib.import_module('screen_metrics'),
  native_region_weights=roi.native_region_weights,
  physical_gates=core.base.LIMITS,GMRES=core.base.GMRES,linux_build_supported=False,
  note='Call solve cached=None for each of the four assigned RHS; original build/make_spec/required_inputs/worker APIs are Linux-only and MUST NOT be called')
def load_graph_and_Q(local_root,np,guard):
 """Owner-called portable lossless cache loader; no eigen or source solve."""
 require(callable(guard),'Validated finite resource/lease guard required');meta=manifest();cache=meta['cache']
 graph,record=_artifact(local_root,'phase1_graph_archive');guard();require(sha(graph)==record['SHA256'],'Original graph NPZ bytes')
 with np.load(graph,allow_pickle=False)as saved:
  eigen=np.array(saved['eigenvalues_per_m2'],copy=True);xy=np.array(saved['XY_m'],copy=True);ij=np.array(saved['ij'],copy=True)
 require(eigen.shape==(NXY,)and xy.shape==ij.shape==(NXY,2),'Exact coarse graph ABI')
 summary,receipt=_artifact(local_root,'phase1_summary');s=_json(summary,receipt['SHA256'])
 require(hashlib.sha256(xy.astype('<f8',copy=False).tobytes()).hexdigest()==s['graph']['XY_float64_le_SHA256']and hashlib.sha256(ij.astype('<i4',copy=False).tobytes()).hexdigest()==s['graph']['ij_int32_le_SHA256'],'Original XY/index row identity')
 Q=np.empty((NXY,NXY),dtype='<f8',order='F');at=0
 for chunk in cache['chunks']:
  guard();path,row=_artifact(local_root,chunk['logical_artifact']);raw=path.read_bytes();end=chunk['column_stop']
  require(chunk['row_start']==0 and chunk['row_stop']==NXY and chunk['column_start']==at and chunk['dtype']=='<f8'and chunk['order']=='F','Disjoint ordered coarse realQ ABI')
  require(len(raw)==chunk['bytes']==NXY*(end-at)*8<=32*1024**2 and hashlib.sha256(raw).hexdigest()==row['SHA256']==chunk['SHA256'],'Full localQ chunk SHA before decode')
  Q[:,at:end]=np.frombuffer(raw,dtype='<f8').reshape((NXY,end-at),order='F');at=end;del raw
 require(at==NXY and Q.flags.f_contiguous and np.isfinite(Q).all(),'Complete finite lossless realQ, never complexQ')
 return dict(Q=Q,eigen=eigen,XY_m=xy,ij=ij,source_solve_RHS=0,new_eigen_solves=0)
def prepare_grid(local_root,np,shared,guard,deadline_monotonic):
 """Owner-called SAME first8 grid and fractional volume ROI, without a solve."""
 guard();api=scientific_kernel(local_root);core=sys.modules['design_screen'];xy=shared['XY_m']
 faces,_,centres=core.base.kernel.f.make_grid(.5,8,[19,18,56]);faces=np.asarray(faces,float);centres=np.asarray(centres,float);layerids=np.repeat(np.arange(4),COUNTS)
 grid=np.column_stack((np.tile(xy[:,0]*1000,len(centres)),np.tile(xy[:,1]*1000,len(centres)),np.repeat(centres*1000,NXY),np.repeat(layerids,NXY),np.repeat(H*H*np.diff(faces),NXY)))
 weights,receipt=api['native_region_weights']({key:grid[:,i]for i,key in enumerate(('x_mm','y_mm','z_mm','layer','volume_m3'))},dict(h_xy_mm=.5,radius_mm=25,z_faces_mm=faces*1000,layer_counts=list(COUNTS),geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001),deadline_monotonic=deadline_monotonic)
 guard();return dict(grid=grid,weights=weights,ROI_receipt=receipt,z_faces_m=faces)
def build_local_case(np,local_root,case,spec,shared,grid,weights,owner,output_dir,deadline_monotonic):
 """One explicit case/two NEW RHS, called only by a validated Windows owner.

owner.assert_active(config_sha) MUST authenticate its real current CAS lease,
Windows Job/process identity, aggregate memory, CPU and finite deadline. This
bundle deliberately supplies no such owner implementation and no CLI. The
exact ROI/grid implementation and its SHA admission are also owner duties.
"""
 require(case in spec['candidates']and case['candidate_id']in IDS and case['maximum_new_driven_RHS']==2 and not case['reuse_baseline_2000'],'One assigned new case, never implicit four-RHS scheduling')
 require(callable(getattr(owner,'assert_active',None)),'Validated platform owner adapter required; a plain Boolean admission is insufficient')
 def guard():
  owner.assert_active(case['canonical_config_SHA256'])
  import time
  require(time.monotonic()<deadline_monotonic,'Finite local-case deadline')
 require(math.isfinite(deadline_monotonic),'Finite explicit local-case deadline required')
 guard();verify_inputs(local_root,guard);kernel=scientific_kernel(local_root);core=sys.modules['design_screen'];Q=shared['Q'];eigen=shared['eigen'];ij=shared['ij']
 require(Q.shape==(NXY,NXY)and eigen.shape==(NXY,)and ij.shape==(NXY,2),'Authenticated shared coarse geometry ABI')
 require(grid.shape==(793860,5)and set(weights)==set(kernel['metrics'].REGIONS),'Exact authenticated first8 grid/ROI ABI required')
 expected=prepare_grid(local_root,np,shared,guard,deadline_monotonic)
 require(np.array_equal(grid,expected['grid'])and all(np.array_equal(weights[key],value)for key,value in expected['weights'].items()),'Actual grid and every fractional ROI weight must match the pinned portable native recipe, not shape alone')
 del expected
 out=Path(output_dir).resolve();require(out.is_dir()and not out.is_symlink(),'Owner-created immutable per-case output')
 faces,_,centres=core.base.kernel.f.make_grid(.5,8,[19,18,56]);layerids=np.repeat(np.arange(4),COUNTS)
 pads,cells,areas=core._mask(np,case,ij);fields=[];proofs=[];losses=np.zeros(4);current2=np.zeros(2);j2=np.zeros(len(areas));drop2=np.zeros(len(areas));sourceP=contactP=resistorP=0.
 for f,output in((2000,0),(2010,1)):
  guard();gamma=[complex(v['real'],v['imaginary'])for v in spec['gamma_by_frequency'][str(f)]];za=complex(spec['z_by_frequency'][str(f)]['real'],spec['z_by_frequency'][str(f)]['imaginary'])
  profile=core._profiles(np,Q,eigen,gamma,np.asarray(centres),guard,deadline_monotonic)
  solution=core._solve(np,Q,profile,pads,cells,areas,za,output,guard,deadline_monotonic,cached=None)
  proof=solution['proof'];proof.update(candidate_id=case['candidate_id'],frequency_Hz=f);_new(out/(str(f)+'-solve-proof.json'),encoded(proof))
  core.archive(np,out/(str(f)+'-surface-state.npz'),phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],modal_surface_coeff=solution['coeff'])
  require(proof['passed']and proof['actual_new_RHS']==1,'Fresh physical gates required; preserve failed surface/proof, no retry')
  phi,E,interface=core._fields(np,Q,profile,solution,ij,layerids,guard,deadline_monotonic)
  core.archive(np,out/(str(f)+'-raw.npz'),phi_peak_V=phi,E_peak_V_m=E,interface_downward_J_peak_A_m2=interface,modal_surface_coeff=solution['coeff'],phi_surface_peak_V=solution['phi_surface'],metal_peak_V=solution['metal'],source_current_peak_A=solution['source_current'],contact_current_peak_A=solution['contact_current'],contact_normal_J_peak_A_m2=solution['contact_J'],contact_drop_peak_V=solution['contact_drop'],contact_pad=pads,contact_xy_index=cells,contact_area_m2=areas,layer_complex_power_W=solution['layer_power'])
  fields.append(E);proofs.append(proof);losses+=solution['layer_power'].real;sourceP+=float(solution['source_power'].real);contactP+=float(solution['contact_power'].real);resistorP+=solution['resistor_power'];current2+=abs(solution['source_current'])**2/2;j2+=abs(solution['contact_J'])**2/2;drop2+=abs(solution['contact_drop'])**2/2
  _new(out/(str(f)+'-checkpoint.json'),encoded(dict(status='one_new_driven_RHS_complete',candidate_id=case['candidate_id'],frequency_Hz=f,actual_new_RHS=1,candidate_adopted=False)))
  del phi,interface,solution,profile
 j=np.sqrt(j2);order=np.argsort(j,kind='stable');at=min(int(np.searchsorted(np.cumsum(areas[order]),.95*float(areas.sum()),side='left')),len(order)-1)
 electrical=dict(source_Vpp_each=1.,source_current_RMS_by_output_A=np.sqrt(current2).tolist(),sum_output_current_RMS_A_bookkeeping=float(np.sqrt(current2).sum()),source_power_W=sourceP,layers_power_W={name:float(losses[i])for i,name in enumerate(('sc','dermis','fat','muscle'))},SC_power_W=float(losses[0]),skin_power_W=float(losses[:2].sum()),contact_power_W=contactP,source_resistor_power_W=resistorP,contact_normal_J_RMS_max_A_m2=float(j.max()),contact_normal_J_RMS_P95_A_m2=float(j[order[at]]),contact_voltage_RMS_max_V=float(np.sqrt(drop2.max())))
 gamma0=np.asarray([complex(v['real'],v['imaginary'])for v in spec['gamma_by_frequency']['2000']]);gamma1=np.asarray([complex(v['real'],v['imaginary'])for v in spec['gamma_by_frequency']['2010']])
 result=kernel['metrics'].evaluate(np,grid,weights,fields[0],fields[1],gamma0,gamma1,electrical,guard,deadline_monotonic)
 record=dict(schema='task1-portable-local-case-result-v1',candidate_id=case['candidate_id'],canonical_config_SHA256=case['canonical_config_SHA256'],metrics=result['summary'],source_physics_proofs=proofs,actual_new_driven_RHS=2,baseline_physics_reused=False,candidate_adopted=False,field_definition=kernel['field'].provenance())
 core.archive(np,out/'scalars.npz',**result['arrays']);_new(out/'case-summary.json',encoded(record));verify_inputs(local_root,guard);guard();return record
def build(*args,**kwargs):
 raise RuntimeError('Execution held: no validated portable Windows owner/Job/CAS lease and same-ROI orchestration yet. Use ADAPTER_CONTRACT.md; do not invoke the frozen Linux eight-case build/worker.')
