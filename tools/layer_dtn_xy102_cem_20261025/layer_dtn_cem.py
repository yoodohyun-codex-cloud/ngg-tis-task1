"""One new continuous-z CEM reference condition/two RHS; owner execution only.

No arrays, cache bytes, research imports or IO are evaluated merely on import.
The owner sets four-thread limits before build's lazy NumPy/SciPy imports and
runs this function in one externally killable600s numerical child.
"""
from __future__ import annotations
import csv,hashlib,io,json,math,time
from pathlib import Path
from fractions import Fraction
import frozen_layer_dtn_backend as kernel

SOURCE=Path('/dev/shm/task1-layer-dtn-xy102-cem-20261025/source')
RUN=Path('/dev/shm/task1-layer-dtn-xy102-cem-20261025-run')
COARSE_CEM=Path('/dev/shm/task1-layer-dtn-cem-20261025-run')
COARSE_CEM_COMMIT='e4c09902bf529b4111c006dd4b4fb6681ca81252'
PHASE1=Path('/dev/shm/task1-layer-dtn-xy102-20261025-run')
REFERENCE=kernel.REFERENCE
PHASE1_COMMIT='ea11fdd9198a7e0c82d91d87f594a5063087486a'
PHASE1_SUMMARY_SHA='33e6585e3ff2c797a8fb3cb42040d252dfe5da1aa848aa3817feb2747b538cd4'
PHASE1_ARRAYS_SHA='f69596f7b38a9063489963588fcbf3861e4a2e78c13179cff8e422c034b73525'
CACHE_MANIFEST_SHA='26da99d7edfcb24a418ab56e1091bab5cb156eccd998653631d5852108c683aa'
PAD_RECTANGLES_MM={'0':[-17.5,-2.5,-17.5,-2.5],'1':[2.5,17.5,2.5,17.5],'2':[2.5,17.5,-17.5,-2.5],'3':[-17.5,-2.5,2.5,17.5]}
KERNEL_SHA='7ff50b6b30198abe4d2cfc5f4ac4fa2afa0873f040ca23175f0e881fb22e1d08'
GMRES=dict(rtol=1e-12,atol=0.,restart=80,max_outer_iterations=40,callback_type='pr_norm',
 preconditioner='diagonal h2 sum_j Qij squared Yj plus physical contact conductance; two metal diagonal sums plus1/50')
LIMITS=dict(relative_algebraic_residual=2e-7,relative_loaded_current_residual=2e-7,
 relative_all_pad_KCL=2e-6,relative_output_pad_current=2e-6,relative_complex_power_error=2e-7,
 relative_transfer_reciprocity=2e-7,passivity_absolute_floor_W=1e-14,passivity_relative_allowance=1e-12,
 current_absolute_floor_A=1e-12,power_absolute_floor_W=1e-12)
PLAN=dict(new_CEM_conditions=1,new_CEM_RHS=2,frequency_Hz=2000,source_resistance_ohm=50.,ideal_voltage_peak_V=.5,
 pad_count=4,independent_outputs=2,return_topology='pads2,3 common0V; inactive ideal output0V through its50ohm, never open circuit',
 nx=102,h_m=.05/102,layers_m=[.0001,.005,.005,.015],evaluation_layer_counts=[4,19,18,56],XY_nodes=8184,evaluation_cells=793848,max_physical_evaluation_cells=800000,
 numerical_child_timeout_seconds=600,CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,
 field_ABI='potential and analytic downward normal current only; no old half-face E ABI or TIS metric',
 physical_top_contact='g_patch=patchArea/z_specific; analytic SC includes its whole0.1mm; no extra SC half-cell',
 reconstruction_depth_block=8,diagonal_column_block=128,candidate_adopted=False)

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pair(value):return kernel.pair(value)
def _read(path,limit=8*1024**2):
 path=Path(path);require(path.is_file()and not path.is_symlink()and path.stat().st_size<limit,'Bounded regular metadata input: '+str(path));return path.read_bytes()
def _hash_file(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def check(guard,deadline):kernel.check(guard,deadline)
def _new_json(path,value):
 with Path(path).open('x',encoding='utf-8')as stream:json.dump(value,stream,allow_nan=False,indent=2)
def validate_admission(raw):
 obj=json.loads(raw)
 require(obj['schema']=='task1-layer-dtn-xy102-cem-root-admission-v1'and obj['status']=='admitted_fine_reference_condition'and obj['root_review_positive']is True and obj['phase1_result_commit']==PHASE1_COMMIT and obj['new_CEM_conditions']==1 and obj['new_CEM_RHS']==2 and obj['candidate_adopted']is False,'Explicit positive sole-root one-condition reference admission')
 require(obj['phase1_summary_sha256']==PHASE1_SUMMARY_SHA and obj['phase1_cache_manifest_sha256']==CACHE_MANIFEST_SHA and obj['coarse_reference_commit']==COARSE_CEM_COMMIT,'Actual published fine backend and coarse continuous-z reference decision identities')
 return obj

def _phase1_metadata():
 summaryraw=_read(PHASE1/'summary.json');manifestraw=_read(PHASE1/'eigen-cache/manifest.json');pub=json.loads(_read(PHASE1/'result-publication/result-publication.json'))
 require(sha(summaryraw)==PHASE1_SUMMARY_SHA and sha(manifestraw)==CACHE_MANIFEST_SHA,'Exact actual phase1 summary/cache manifest')
 require(pub['status']=='published_readback_verified'and pub['commit']==PHASE1_COMMIT,'Positive first phase actual full publication')
 for name,digest in(('summary.json',PHASE1_SUMMARY_SHA),('arrays.npz',PHASE1_ARRAYS_SHA),('local-eigen-cache-manifest.json',CACHE_MANIFEST_SHA)):
  row=pub['files']['data-native/cloud-layer-dtn-xy102-20261025/'+name];require(row['SHA256']==digest and row['readback_passed']is True,'Actual phase1 remote full-SHA proof: '+name)
 summary=json.loads(summaryraw);manifest=json.loads(manifestraw)
 require(summary['status']=='calculated_graph_eigen_analytic_MMS_only'and summary['analytic']['passed']is True and summary['eigen']['cache']==manifest and manifest['shape']==[8184,8184]and manifest['dtype']=='<f8'and manifest['order']=='F','Successful exact shared graph/analytic backend and real cache ABI')
 return summary,manifest

def required_inputs():
 """Deferred owner-only metadata, raw/cache SHA references; no array decoding."""
 refs=kernel.required_inputs();summary,manifest=_phase1_metadata()
 for name in('summary.json','arrays.npz','worker-receipt.json','receipt.json','result-publication/result-publication.json','eigen-cache/manifest.json'):
  p=PHASE1/name;refs[str(p)]=sha(_read(p))
 for chunk in manifest['chunks']:refs[chunk['path']]=chunk['SHA256']
 require(sha(_read(SOURCE/'frozen_layer_dtn_backend.py'))==KERNEL_SHA==sha(_read(PHASE1/'source/layer_dtn_backend.py')),'Exact unchanged phase1 kernel copy')
 refs[str(SOURCE/'frozen_layer_dtn_backend.py')]=KERNEL_SHA
 ar=_read(SOURCE/'root-admission.json');validate_admission(ar);require(_read(RUN/'root-admission.json')==ar,'Exact source-to-runtime root admission copy')
 refs[str(SOURCE/'root-admission.json')]=sha(ar);refs[str(RUN/'root-admission.json')]=sha(ar)
 for name in('fine-mask.csv','fine-mask-receipt.json','evaluation-z-faces.json'):
  path=RUN/name;refs[str(path)]=sha(_read(path))
 require_input_receipts()
 return refs

def rectangle_intersection(x0,x1,y0,y1,rx0,rx1,ry0,ry1):
 """Exact rational pixel/axis-aligned-rectangle area in square metres."""
 return max(Fraction(0),min(x1,rx1)-max(x0,rx0))*max(Fraction(0),min(y1,ry1)-max(y0,ry0))

def fractional_mask_inputs():
 """Owner-only pure exact geometry builder; never old indices or area rescale."""
 nx=PLAN['nx'];h=Fraction(1,20*nx);radius=Fraction(1,40);halfwidth=Fraction(3,400)
 xy,ij,edges,degree=kernel._graph_records(nx);lookup={tuple(v):p for p,v in enumerate(ij)}
 require(len(xy)==PLAN['XY_nodes'],'Actual verified fine graph column count')
 centers=[(Fraction(-1,100),Fraction(-1,100)),(Fraction(1,100),Fraction(1,100)),(Fraction(1,100),Fraction(-1,100)),(Fraction(-1,100),Fraction(1,100))]
 for a,(cx,cy)in enumerate(centers):
  for dx,dy in centers[a+1:]:
   require(rectangle_intersection(cx-halfwidth,cx+halfwidth,cy-halfwidth,cy+halfwidth,dx-halfwidth,dx+halfwidth,dy-halfwidth,dy+halfwidth)==0,'Exact rational disjoint physical pad polygons')
 lines=['pad,i,j,area_m2'];covered={};pads=[];totalrows=0
 for pad,(cx,cy)in enumerate(centers):
  rx0,rx1,ry0,ry1=cx-halfwidth,cx+halfwidth,cy-halfwidth,cy+halfwidth;total=Fraction(0);float_total=0.;count=0
  require(all(x*x+y*y<radius*radius for x in(rx0,rx1)for y in(ry0,ry1)),'Entire unchanged225mm2 rectangle inside cylinder; no circle trimming')
  for j in range(nx):
   y0=-radius+j*h;y1=-radius+(j+1)*h
   for i in range(nx):
    x0=-radius+i*h;x1=-radius+(i+1)*h;area=rectangle_intersection(x0,x1,y0,y1,rx0,rx1,ry0,ry1)
    if not area:continue
    require((i,j)in lookup,'Every fine contact patch maps to actual same-graph surface column')
    covered[i,j]=covered.get((i,j),Fraction(0))+area;require(covered[i,j]<=h*h,'No overlapping contact-face areas, exact rational proof')
    total+=area;float_total+=float(area);count+=1;totalrows+=1;lines.append('%d,%d,%d,%s'%(pad,i,j,format(float(area),'.17g')))
  analytic=(2*halfwidth)**2;require(total==analytic,'Exact rational225mm2 partition, no renormalization')
  relative=abs(float_total-float(analytic))/float(analytic);require(relative<=1e-10,'Frozen contact-area relative gate1e-10 in exported float patches')
  pads.append(dict(pad=pad,center_mm=[float(cx*1000),float(cy*1000)],width_mm=15.,height_mm=15.,rotation_deg=0.,
   analytic_area_m2=float(analytic),represented_area_m2=float_total,area_relative_error=relative,area_relative_limit=1e-10,
   exact_represented_area_numerator=total.numerator,exact_represented_area_denominator=total.denominator,patch_count=count,exact_rational_partition_passed=True))
 raw=('\n'.join(lines)+'\n').encode()
 receipt=dict(schema='task1-xy102-exact-fractional-contact-mask-v1',nx=nx,h_m=PLAN['h_m'],circle_diameter_mm=50.,physical_top_contact=True,
  method='Exact rational axis-aligned rectangle/pixel intersection; convert each exact area once tofloat64; NO area rescale, old index reuse or circle trimming',
  mask_sha256=sha(raw),mask_bytes=len(raw),rows=totalrows,pads=pads,pad_count=4,independent_outputs=2,
  return_topology=PLAN['return_topology'],no_overlapping_faces=True,circle_trimmed=False,physical_pad_geometry_changed=False,lateral_graph_changed=True,
  canonical_row_order='pad0,1,2,3; then ascending j; then ascending i',source_pad_positions_mm=[[-10,-10],[10,10]],ground_pad_positions_mm=[[10,-10],[-10,10]],
  maximum_exported_area_relative_error=max(r['area_relative_error']for r in pads),contact_area_gate_passed=True)
 faces,layers,zs=kernel.f.make_grid(PLAN['h_m']*1000,4,[19,18,56])
 zreceipt=dict(schema='task1-xy102-continuous-z-evaluation-v1',units='m',physical_layer_thickness_m=PLAN['layers_m'],layer_counts=[4,19,18,56],z_faces_m=faces,
  XY_columns=len(xy),evaluation_cells=len(xy)*len(zs),maximum_physical_evaluation_cells=800000,
  interpretation='SC4 is evaluation quadrature of unchanged continuous0.1mm SC, not vertical FVM/coarsening; XY102 differs from old XY100 nodes')
 require(zreceipt['evaluation_cells']==PLAN['evaluation_cells']<=800000,'Unchanged physical evaluation-cell cap')
 return raw,receipt,zreceipt

def _json_bytes(value):return(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode()

def prepare_inputs():
 """Sole owner BEFORE source publication: exclusive immutable fine inputs."""
 require(RUN.is_dir()and not RUN.is_symlink(),'Canonical unique owner-created fine run directory')
 _phase1_metadata();ar=_read(SOURCE/'root-admission.json');validate_admission(ar);require(_read(RUN/'root-admission.json')==ar,'Pinned positive admission runtime copy')
 mask,receipt,zreceipt=fractional_mask_inputs()
 outputs={'fine-mask.csv':mask,'fine-mask-receipt.json':_json_bytes(receipt),'evaluation-z-faces.json':_json_bytes(zreceipt)}
 refs={}
 for name,raw in outputs.items():
  p=RUN/name
  if p.exists():require(_read(p)==raw,'Immutable derived input already exists with different bytes: '+name)
  else:
   with p.open('xb')as stream:stream.write(raw)
  require(_read(p)==raw,'Full derived-input readback');refs[str(p)]=sha(raw)
 return dict(schema='task1-xy102-CEM-prepared-inputs-v1',files=refs,mask_receipt=receipt,evaluation_receipt=zreceipt)

def require_input_receipts():
 mask=_read(RUN/'fine-mask.csv');receipt=json.loads(_read(RUN/'fine-mask-receipt.json'));zreceipt=json.loads(_read(RUN/'evaluation-z-faces.json'))
 require(receipt['schema']=='task1-xy102-exact-fractional-contact-mask-v1'and receipt['mask_sha256']==sha(mask)and receipt['contact_area_gate_passed']is True and receipt['circle_trimmed']is False and receipt['no_overlapping_faces']is True,'Published fine physical fractional-mask receipt')
 exactmask,exactreceipt,exactz=fractional_mask_inputs();require(mask==exactmask and receipt==exactreceipt and zreceipt==exactz,'Re-derived exact fine geometry and97plane evaluation inputs')
 return receipt,zreceipt

def make_spec(admission_bytes=None):
 admissionraw=_read(SOURCE/'root-admission.json')if admission_bytes is None else admission_bytes;validate_admission(admissionraw)
 base=kernel.make_spec();summary,manifest=_phase1_metadata();cfg=kernel.properties(_read(kernel.CONFIG));maskreceipt,zreceipt=require_input_receipts()
 require(base['registered_geometry']['XY_columns']==8184 and base['registered_geometry']['evaluation_cells']==793848,'Actual verified fine benchmark counts within800k')
 return dict(schema='task1-layer-dtn-xy102-cem-reference-spec-v1',plan=json.loads(json.dumps(PLAN)),gmres=dict(GMRES),gates=dict(LIMITS),admission_sha256=sha(admissionraw),phase1_commit=PHASE1_COMMIT,
  phase1_summary_sha256=PHASE1_SUMMARY_SHA,phase1_arrays_sha256=PHASE1_ARRAYS_SHA,cache_manifest_sha256=CACHE_MANIFEST_SHA,
  phase1_summary_path=str(PHASE1/'summary.json'),phase1_cache_directory=str(PHASE1/'eigen-cache'),phase1_kernel_sha256=KERNEL_SHA,
  coarse_reference_commit=COARSE_CEM_COMMIT,coarse_reference_run=str(COARSE_CEM),coarse_reference_summary_path=str(COARSE_CEM/'reference-summary.json'),coarse_reference_arrays_path=str(COARSE_CEM/'reference-arrays.npz'),
  material_rows=base['material_rows'],material_receipt_sha256=base['material_receipt_sha256'],contact_receipt_sha256=kernel.CONTACT_SHA,
  actual_U19_provenance_config_sha256=kernel.CONFIG_SHA,pad_rectangles_mm=json.loads(json.dumps(PAD_RECTANGLES_MM)),
  mask_path=str(RUN/'fine-mask.csv'),mask_sha256=maskreceipt['mask_sha256'],mask_receipt_path=str(RUN/'fine-mask-receipt.json'),mask_receipt_sha256=sha(_read(RUN/'fine-mask-receipt.json')),
  contact_specific_impedance_ohm_m2=pair(complex(float(cfg['z.2000.re']),float(cfg['z.2000.im']))),
  z_faces_path=str(RUN/'evaluation-z-faces.json'),z_faces_sha256=sha(_read(RUN/'evaluation-z-faces.json')),phi_ref_evaluation_grid_receipt_sha256=sha(_read(RUN/'evaluation-z-faces.json')),
  phi_ref_cell_order='fine97depthplanes/z outer; fine j then i XY inside circle; xy_mm defines fineQ order; cell_index=z_index*8184+xy_index; NOT old native indices',
  phasor_convention='peak complex exp(+j*omega*t); source1Vpp high-impedance convention=.5Vpeak before50ohm',
  power_convention='S=.5 V conj(I); tissue S=.5 integral conj(gamma)|E|^2, positive real dissipation and capacitive reactive imaginary negative',
  comparison_scope='NEW XY102 graph/physical fractional mask CEM, same physical polygons/material/contact/circuit; any coarse comparison requires separately registered physical projection/quadrature, never node-index subtraction',
  old_independent_QA_limit=.05,old_failed_QA_preserved=True,experimental_validation=False)

def contact_conductance(area,z_specific):
 require(area>0 and kernel.f.finite(z_specific)and z_specific.real>0,'Finite positive physical contact area/passive impedance')
 return area/z_specific

def contact_equations(tissue,phi,metal,pads,cells,areas,z_specific,R=50.):
 """Small pure reference equations for signed source/return contract tests."""
 surface=list(tissue);qpad=[0j]*4
 for p,i,area in zip(pads,cells,areas):
  q=contact_conductance(area,z_specific)*(phi[i]-(metal[p]if p<2 else 0j));surface[i]+=q;qpad[p]+=q
 return surface,[metal[p]/R-qpad[p]for p in range(2)],qpad

def screen_errors(errors):
 names=('relative_algebraic_residual','relative_loaded_current_residual','relative_all_pad_KCL','relative_output_pad_current','relative_complex_power_error')
 rows=[dict(metric=k,value=float(errors[k]),limit=LIMITS[k],passed=math.isfinite(float(errors[k]))and float(errors[k])<=LIMITS[k])for k in names]
 return dict(passed=all(r['passed']for r in rows),rows=rows)

def _load_cache(np,manifest,guard,deadline):
 n=PLAN['XY_nodes'];Q=np.empty((n,n),dtype='<f8',order='F');at=0;proof=[]
 for row in manifest['chunks']:
  check(guard,deadline);p=Path(row['path']);require(p.parent==PHASE1/'eigen-cache'and p.is_file()and not p.is_symlink()and row['row_start']==0 and row['row_stop']==n and row['column_start']==at and 0<row['column_stop']-at and row['dtype']=='<f8'and row['order']=='F','Exact ordered disjoint local realQ chunk ABI')
  raw=p.read_bytes();end=row['column_stop'];require(len(raw)==row['bytes']==n*(end-at)*8<=32*1024**2 and sha(raw)==row['SHA256'],'Full cached Q chunk SHA/bytes before decode')
  Q[:,at:end]=np.frombuffer(raw,dtype='<f8').reshape((n,end-at),order='F');proof.append(dict(path=str(p),SHA256=row['SHA256'],bytes=len(raw),before_passed=True));at=end;del raw
 require(at==n and Q.flags.f_contiguous and np.isfinite(Q).all(),'Complete finite realF Q without fullcomplexcast')
 return Q,proof

def _contacts(np,xy,ij,spec):
 raw=_read(spec['mask_path']);require(sha(raw)==spec['mask_sha256'],'Exact published NEW fine fractional contact mask')
 lookup={(int(i),int(j)):p for p,(i,j)in enumerate(ij)};pads=[];cells=[];areas=[]
 for row in csv.DictReader(io.StringIO(raw.decode())):
  p=int(row['pad']);i=int(row['i']);j=int(row['j']);area=float(row['area_m2']);require(p in(0,1,2,3)and(i,j)in lookup and 0<area<=PLAN['h_m']**2*(1+1e-10),'Valid NEW fractional patch for unchanged physical pad polygons');pads.append(p);cells.append(lookup[i,j]);areas.append(area)
 pads=np.asarray(pads,dtype=np.int32);cells=np.asarray(cells,dtype=np.int32);areas=np.asarray(areas,float)
 coverage=np.bincount(cells,weights=areas,minlength=len(xy));require(np.max(coverage)<=PLAN['h_m']**2*(1+1e-10),'No overlapping top patch areas')
 for p in range(4):require(abs(float(areas[pads==p].sum())-.000225)/.000225<=1e-10,'Preserved225mm2 physicalpad area at frozenrelative1e-10 gate')
 return pads,cells,areas

def _real_complex_transform(np,Q,values,transpose=False):
 """Never multiply real full Q by a complex argument (implicit densecast)."""
 matrix=Q.T if transpose else Q
 return matrix@values.real+1j*(matrix@values.imag)

def build(spec,guard,deadline_monotonic=None):
 """Root-only one new physical-top reference condition, exactly two new RHS."""
 check(guard,deadline_monotonic)
 require(spec==make_spec(),'Immutable phase2 method/material/contact/admission specification')
 admission=_read(RUN/'root-admission.json');require(sha(admission)==spec['admission_sha256'],'Pinned positive runtime root admission');validate_admission(admission)
 require(RUN.is_dir()and not RUN.is_symlink(),'Unique owner-created canonical runtime')
 import numpy as np
 import scipy
 from scipy.sparse.linalg import LinearOperator,gmres
 wall=time.monotonic();cpu=time.process_time();phase1,manifest=_phase1_metadata();Q,cacheproof=_load_cache(np,manifest,guard,deadline_monotonic)
 arraysraw=_read(PHASE1/'arrays.npz');require(sha(arraysraw)==PHASE1_ARRAYS_SHA,'Exact published phase1 spectral/graph metadata arrays')
 with np.load(io.BytesIO(arraysraw),allow_pickle=False)as source:
  eigen=np.asarray(source['eigenvalues_per_m2'],float);xy=np.asarray(source['XY_m'],float);ij=np.asarray(source['ij'],np.int32)
 n=PLAN['XY_nodes'];require(Q.shape==(n,n)and eigen.shape==(n,)and xy.shape==(n,2)and ij.shape==(n,2),'Exact sameXY/eigen ABI')
 require(sha(xy.astype('<f8',copy=False).tobytes())==phase1['graph']['XY_float64_le_SHA256']and sha(ij.astype('<i4',copy=False).tobytes())==phase1['graph']['ij_int32_le_SHA256'],'Exact original XY/index order')
 gamma=[complex(r['gamma_S_m']['real'],r['gamma_S_m']['imaginary'])for r in spec['material_rows']];th=PLAN['layers_m'];h2=PLAN['h_m']**2
 Y=np.asarray([kernel.modal_admittance(math.sqrt(float(v)),gamma,th)for v in eigen],np.complex128);require(Y[0]==0j and np.isfinite(Y).all(),'Passive finite top DtN with insulated constant mode')
 pads,cells,areas=_contacts(np,xy,ij,spec);za=complex(spec['contact_specific_impedance_ohm_m2']['real'],spec['contact_specific_impedance_ohm_m2']['imaginary']);g=areas/za;R=PLAN['source_resistance_ohm']
 gsum=np.bincount(cells,weights=g.real,minlength=n)+1j*np.bincount(cells,weights=g.imag,minlength=n)
 metalg=np.asarray([g[pads==p].sum()for p in range(2)])
 diag=np.zeros(n,np.complex128)
 for start in range(0,n,PLAN['diagonal_column_block']):
  check(guard,deadline_monotonic);stop=min(n,start+PLAN['diagonal_column_block']);squared=Q[:,start:stop]**2;diag+=h2*(squared@Y[start:stop].real+1j*(squared@Y[start:stop].imag))
 diag=np.concatenate((diag+gsum,metalg+1/R));require(np.isfinite(diag).all()and np.all(abs(diag)>1e-30),'Finite nonzero diagonal preconditioner')
 matvec_count=0
 def tissue(phi):return h2*_real_complex_transform(np,Q,Y*_real_complex_transform(np,Q,phi,True))
 def split(x):
  phi=x[:n];metal=x[n:];vp=np.zeros(len(pads),np.complex128)
  for p in range(2):vp[pads==p]=metal[p]
  q=g*(phi[cells]-vp);qsum=np.zeros(n,np.complex128);np.add.at(qsum,cells,q)
  qpad=np.asarray([q[pads==p].sum()for p in range(4)]);return phi,metal,vp,q,qsum,qpad
 def action(x):
  nonlocal matvec_count
  matvec_count+=1;check(guard,deadline_monotonic);phi,metal,vp,q,qsum,qpad=split(x);return np.concatenate((tissue(phi)+qsum,metal/R-qpad[:2]))
 A=LinearOperator((n+2,n+2),matvec=action,dtype=np.complex128);M=LinearOperator((n+2,n+2),matvec=lambda x:x/diag,dtype=np.complex128)
 solutions=[];proofs=[];contacts_current=[];contact_drops=[];metals=[];sources=[];modal=[];layerpowers=[]
 layerfaces=[0.]
 for thickness in th:layerfaces.append(layerfaces[-1]+thickness)
 # Unit physical-top modal states are independent of the two source RHS.
 unitV=np.empty((n,5),np.complex128);unitJ=np.empty((n,5),np.complex128)
 for k,value in enumerate(eigen):
  if k%256==0:check(guard,deadline_monotonic)
  vv,jj=kernel.stable_profile(math.sqrt(float(value)),gamma,th,layerfaces);unitV[k]=vv;unitJ[k]=jj
 for basis in range(2):
  check(guard,deadline_monotonic);b=np.zeros(n+2,np.complex128);b[n+basis]=.5/R;history=[];start=time.monotonic()
  def callback(value):history.append(float(value));check(guard,deadline_monotonic)
  x,info=gmres(A,b,M=M,rtol=GMRES['rtol'],atol=GMRES['atol'],restart=GMRES['restart'],maxiter=GMRES['max_outer_iterations'],callback=callback,callback_type=GMRES['callback_type'])
  check(guard,deadline_monotonic);phi,metal,vp,q,qsum,qpad=split(x);t=tissue(phi);ideal=np.zeros(2,np.complex128);ideal[basis]=.5;Isource=(ideal-metal)/R
  raw_residual=np.concatenate((t+qsum,metal/R-qpad[:2]))-b
  physical_residual=np.concatenate((t+qsum,Isource+qpad[:2]));current_scale=max(float(np.linalg.norm(t)),float(np.linalg.norm(qsum)),float(np.linalg.norm(Isource)),LIMITS['current_absolute_floor_A'])
  coeff=_real_complex_transform(np,Q,phi,True);Slayer=.5*h2*np.sum(abs(coeff[:,None])**2*(unitV[:,:-1]*unitJ[:,:-1].conj()-unitV[:,1:]*unitJ[:,1:].conj()),axis=0)
  Ssource=.5*np.sum(ideal*Isource.conj());Scontact=.5*np.sum((vp-phi[cells])*(-q).conj());Presistor=.5*R*float(np.sum(abs(Isource)**2));Ssum=Slayer.sum()+Scontact+Presistor
  perpad_den=np.maximum(np.maximum(abs(Isource),abs(qpad[:2])),LIMITS['current_absolute_floor_A'])
  errors=dict(relative_algebraic_residual=float(np.linalg.norm(raw_residual)/np.linalg.norm(b)),relative_loaded_current_residual=float(np.linalg.norm(physical_residual)/current_scale),
   relative_all_pad_KCL=float(abs(qpad.sum())/max(float(np.sum(abs(qpad))),LIMITS['current_absolute_floor_A'])),relative_output_pad_current=float(np.max(abs(Isource+qpad[:2])/perpad_den)),
   relative_complex_power_error=float(abs(Ssource-Ssum)/max(abs(Ssource),abs(Ssum),LIMITS['power_absolute_floor_W'])))
  gates=screen_errors(errors);powers=[complex(v)for v in Slayer]+[complex(Scontact),complex(Presistor)];power_allowance=LIMITS['passivity_absolute_floor_W']+LIMITS['passivity_relative_allowance']*max(abs(v)for v in powers);passive=all(v.real>=-power_allowance for v in powers)
  proof=dict(basis=basis,gmres_info=int(info),inner_iterations=len(history),preconditioned_callback_history=history,wall_seconds=time.monotonic()-start,
   physical_gates=gates,loaded_current_scale_A=current_scale,current_absolute_floor_A=LIMITS['current_absolute_floor_A'],source_RHS_norm_A=float(np.linalg.norm(b)),
   passivity_passed=passive,negative_real_power_allowance_W=power_allowance,layer_complex_power_W=[pair(v)for v in Slayer],source_complex_power_W=pair(Ssource),contact_complex_power_W=pair(Scontact),source_resistor_power_W=Presistor,
   source_current_A=[pair(v)for v in Isource],all_pad_outward_tissue_to_metal_current_A=[pair(v)for v in qpad],passed=int(info)==0 and gates['passed']and passive,
   interpretation='Fresh unpreconditioned residual against both0.01A source RHS and loaded tissue-current scale; independent current/power gates. No old5percent interface flag cleared.')
  _new_json(RUN/('rhs%d-solve-proof.json'%basis),proof)
  with(RUN/('rhs%d-surface-partial.npz'%basis)).open('xb')as stream:np.savez_compressed(stream,phi_surface=phi,metal=metal,source_current=Isource)
  require(proof['passed'],'Reference GMRES/physical current/KCL/power/passivity gate failed; exact proof and surface iterate preserved')
  solutions.append(phi);proofs.append(proof);contacts_current.append(-q);contact_drops.append(vp-phi[cells]);metals.append(metal);sources.append(Isource);modal.append(coeff);layerpowers.append(Slayer)
 sourcearr=np.asarray(sources);reciprocity=float(abs(sourcearr[0,1]-sourcearr[1,0])/max(abs(sourcearr[0,1]),abs(sourcearr[1,0]),LIMITS['current_absolute_floor_A']))
 _new_json(RUN/'reciprocity-proof.json',dict(relative_transfer_reciprocity=reciprocity,limit=LIMITS['relative_transfer_reciprocity'],passed=reciprocity<=LIMITS['relative_transfer_reciprocity']))
 require(reciprocity<=LIMITS['relative_transfer_reciprocity'],'Two-output reciprocal transfer gate; old fields preserved')
 facebytes=_read(spec['z_faces_path']);require(sha(facebytes)==spec['z_faces_sha256'],'Exact published continuous-z97plane physical-depth evaluation faces');faceobj=json.loads(facebytes);zfaces=np.asarray(faceobj['z_faces_m'],float);zs=(zfaces[:-1]+zfaces[1:])/2
 layerids=np.repeat(np.arange(4),[4,19,18,56]);require(len(zs)==97 and n*len(zs)==PLAN['evaluation_cells']<=PLAN['max_physical_evaluation_cells'],'Unchanged evaluation-grid physical cell cap')
 factors=np.empty((n,len(zs)),np.complex128)
 for k,value in enumerate(eigen):
  if k%256==0:check(guard,deadline_monotonic)
  factors[k]=kernel.stable_profile(math.sqrt(float(value)),gamma,th,zs)[0]
 phi_ref=np.empty((2,n*len(zs)),np.complex128);Jn=np.empty((2,3,n),np.complex128)
 for basis,coeff in enumerate(modal):
  for first in range(0,len(zs),PLAN['reconstruction_depth_block']):
   check(guard,deadline_monotonic);last=min(len(zs),first+PLAN['reconstruction_depth_block']);c=coeff[:,None]*factors[:,first:last];values=_real_complex_transform(np,Q,c)
   phi_ref[basis,first*n:last*n]=values.T.reshape(-1)
  Jn[basis]=_real_complex_transform(np,Q,coeff[:,None]*unitJ[:,1:4]).T
 require(np.isfinite(phi_ref).all()and np.isfinite(Jn).all(),'Finite potential/interface reference arrays')
 for record in cacheproof:
  check(guard,deadline_monotonic);require(_hash_file(record['path'])==record['SHA256'],'Exact cached basis SHA again after solve/reconstruction');record['after_passed']=True
 check(guard,deadline_monotonic)
 summary=dict(schema='task1-layer-dtn-xy102-cem-reference-result-v1',status='calculated_reference_physical_gates_passed_unadopted',spec=spec,
  actual_new_CEM_conditions=1,actual_new_CEM_RHS=2,actual_new_native_FVM_RHS=0,condition_frequency_Hz=2000,physical_gates_passed=True,linear_solve_proofs=proofs,
  reciprocity=dict(relative_error=reciprocity,limit=LIMITS['relative_transfer_reciprocity'],passed=True),matvec_count=matvec_count,
  cache_reuse=dict(manifest_sha256=CACHE_MANIFEST_SHA,complete_before_after_SHA_verified=True,records=cacheproof,local_cache_remote_durability_unverified=True,no_new_eigen_run=True),
  numerical_method=dict(scipy_version=scipy.__version__,numpy_version=np.__version__,complex_symmetric_not_Hermitian=True,solver='matrix-free scipy GMRES',diagonal_preconditioner=True,no_complex_dense_Q_or_K=True),
  reference_array_ABI=dict(phi_ref='complex128 peak V shape[basis=2,cell=793848] FINE97plane z-major/j/i order; not coarse indices',interface_J='complex128 peak downward A/m2 shape[basis=2,interface=3,xy=8184],xy_mm explicitly defines order',
   interface_depths_mm=[.1,5.1,10.1],contact_current='metal to tissue peak A; contact J=current/actual_patch_area',source_current='ideal source to output through50ohm peak A axes[basis,output]',
   layer_complex_power='S=VI*/2; conj(gamma) energy, negative capacitive reactive part; no silent absolute value or clipping',phi_ref_evaluation_grid_receipt_sha256=spec['phi_ref_evaluation_grid_receipt_sha256'],phi_ref_cell_order=spec['phi_ref_cell_order']),
  wall_seconds=time.monotonic()-wall,cpu_process_seconds=time.process_time()-cpu,
  holds=dict(old_5percent_independent_interface_failures_preserved=True,continuousz_conditional_on_fixed_XY=True,full_SC_XY_bulk_edge_contact_convergence=False,material_contact_hardware_experiment_validated=False,candidate_adopted=False,TIS_from_one_carrier=False,
   old_native_E_ABI_not_exported=True,analytic_Ez_not_yet_exported=True,Windows_saved_verified=False))
 arrays=dict(phi_ref=phi_ref,modal_surface_coeff=np.asarray(modal),phi_surface=np.asarray(solutions),metal=np.asarray(metals),source_current=sourcearr,source_ideal_voltage=.5*np.eye(2,dtype=np.complex128),
  interface_J=Jn,layer_complex_power=np.asarray(layerpowers),contact_current=np.asarray(contacts_current),contact_normal_J=np.asarray(contacts_current)/areas[None,:],contact_drop=np.asarray(contact_drops),
  contact_pad=pads,contact_xy_index=cells,contact_xy_mm=np.round(xy[cells]*1000,12),contact_area_m2=areas,xy_mm=np.round(xy*1000,12),z_eval_mm=zs*1000,layer_eval=layerids)
 return dict(summary=summary,arrays=arrays)
