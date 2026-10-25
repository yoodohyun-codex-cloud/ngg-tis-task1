"""Phase1 graph/eigen/analytic-depth benchmark; NO CEM solve and no import IO.

Owner configures CPU/BLAS before importing build's lazy numpy/scipy dependencies.
Heavy build must run in one separately watchdog-controlled numerical child.
All depth profiles use peak phasors exp(+j omega t), downward J=-gamma dV/dz.
"""
from __future__ import annotations
import hashlib,json,math,sys,time
from pathlib import Path
import frozen_fourier_v1 as f

ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-layer-dtn-20261025/source')
REFERENCE=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run')
CASE='baseline-square15-human-sine2000-sc8-vs19uniform-bulk19-18-56-xy100'
CONFIG=REFERENCE/'configs'/(CASE+'.properties')
CACHE=Path('/dev/shm/task1-layer-dtn-20261025-run/eigen-cache')
REFERENCE_COMMIT='cebb04aa2074e848e34ffd7aede4bc0476aa16c6'
CONFIG_SHA='a20334ff9788323b065c89968cd18d764e813beb4017879bdc390f19a4db6445'
CONTACT_SHA='cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b'
MASK_SHA='884d3bc2537bc88d87a82bffcd735a197c48afda02485573ec27b80469b688ca'
TOL=dict(eigenvalue_roundoff_relative=1e-12,eigen_residual_spectral_relative=1e-11,
 unit_norm_absolute=2e-10,selected_orthogonality_absolute=2e-10,transform_relative=2e-10,
 constant_mode_alignment_error=2e-10,analytic_absolute=1e-10,analytic_relative=1e-10,
 passive_admittance_relative=1e-12)
PLAN=dict(phase='graph_full_eigen_and_analytic_manufactured_only',h_m=.0005,radius_m=.025,nx=100,
 physical_layers_m=[.0001,.005,.005,.015],evaluation_SC_cells=8,evaluation_bulk_counts=[19,18,56],
 max_evaluation_cells=800000,expected_XY_columns=7860,expected_evaluation_cells=793860,
 eigensolver='scipy.linalg.eigh',driver='evr',overwrite_a=True,check_finite=False,
 real_dtype='float64',dense_order='F',eigen_residual_block_columns=128,
 orthogonality_selected_columns=64,orthogonality_scope='all columns against 64 deterministic selected columns; NOT exhaustive all-pairs',
 complex_roundtrip_probe_count=3,cache_raw_chunk_max_bytes=32*1024**2,
 local_cache_durability='local recomputable cache only; NOT remote verified scientific raw output',
 outer_numerical_child_watchdog_seconds=600,max_effective_CPU=4,total_RSS_plus_all_owned_tmpfs_limit_bytes=8000000000,
 new_CEM_conditions=0,new_CEM_RHS=0,candidate_adopted=False)

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def properties(raw):return f._properties(raw)
def pair(z):return f.pair(z)
def check(guard,deadline):
 guard();require(deadline is None or time.monotonic()<deadline,'Finite phase1 deadline')
def _metadata(path,limit=8*1024**2):
 p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<limit,'Bounded regular immutable input: '+str(p));return p.read_bytes()

def required_inputs():
 """Owner-invoked small provenance/input reads; never native field decoding."""
 paths=[CONFIG,REFERENCE/'material-input.json',REFERENCE/'contact-receipt.json',REFERENCE/'result-publication.json',
  REFERENCE/'preregistration.json',REFERENCE/'postprocess/summary.json',REFERENCE/'postprocess/artifact-sha256.json',REFERENCE/'z-faces.json',
  ROOT/'tis-java/SelectivityShapeBasis.java',ROOT/'tis-java/TisSweep.java',ROOT/'tools/task1_execution_policy.py',
  ROOT/'tools/task1_resource_policy.py',SOURCE/'frozen_fourier_v1.py']
 refs={str(p):sha(_metadata(p))for p in paths}
 require(refs[str(CONFIG)]==CONFIG_SHA and refs[str(REFERENCE/'material-input.json')]==f.MATERIAL_SHA and refs[str(REFERENCE/'contact-receipt.json')]==CONTACT_SHA,'Unchanged verified material/contact receipts')
 cfg=properties(_metadata(CONFIG));mask=Path(cfg['mask.path']);require(sha(_metadata(mask))==MASK_SHA==cfg['mask.sha256'],'Unchanged actual four-pad mask');refs[str(mask)]=MASK_SHA
 pub=json.loads(_metadata(REFERENCE/'result-publication.json'));require(pub['status']=='published_readback_verified'and pub['commit']==REFERENCE_COMMIT,'Actual fully published U19 prerequisite')
 art=json.loads(_metadata(REFERENCE/'postprocess/artifact-sha256.json'));require(refs[str(REFERENCE/'postprocess/summary.json')]==art['summary.json']['SHA256'],'Pinned actual completed U19 summary')
 old=Path('/dev/shm/task1-estimator-fourier-20261025/source/frozen_fourier_v1.py');require(_metadata(old)==_metadata(SOURCE/'frozen_fourier_v1.py'),'Exact frozen analytic helper');refs[str(old)]=refs[str(SOURCE/'frozen_fourier_v1.py')]
 return refs

def make_spec(material_receipt_bytes=None,config_bytes=None):
 """Pure byte-to-spec builder; defaults read only pinned small actual inputs."""
 mr=_metadata(REFERENCE/'material-input.json')if material_receipt_bytes is None else material_receipt_bytes
 cr=_metadata(CONFIG)if config_bytes is None else config_bytes
 require(sha(mr)==f.MATERIAL_SHA and sha(cr)==CONFIG_SHA,'Exact source-verified surrogate material receipt and immutable actual U19 config')
 cfg=properties(cr);require(cfg['h_mm']=='0.5'and cfg['frequencies']=='2000'and cfg['channels']=='2'and cfg['validation.sc_cells']=='8'and cfg['bulk.counts']=='19,18,56'and cfg['validation.expected_cells']=='793860','Actual published fixed graph/evaluation geometry')
 require(cfg['material.input_sha256']==f.MATERIAL_SHA and cfg['contact.input_sha256']==CONTACT_SHA and cfg['mask.sha256']==MASK_SHA,'Unchanged material/contact/pad input identities')
 rows=[]
 for layer in f.LAYERS:
  s=float(cfg[layer+'.sigma.2000']);e=float(cfg[layer+'.epsilon_r.2000']);g=complex(s,2*math.pi*2000*f.EPS0*e)
  require(s>0 and e>0 and f.finite(g),'Finite actual passive scalar gamma');rows.append(dict(layer=layer,sigma_S_m=s,epsilon_r=e,gamma_S_m=pair(g)))
 return dict(schema='task1-layer-dtn-phase1-spec-v1',plan=json.loads(json.dumps(PLAN)),tolerances=dict(TOL),frequency_Hz=2000,
  material_receipt_sha256=sha(mr),actual_U19_config_sha256=sha(cr),material_rows=rows,
  physical_model='same staircase XY Neumann graph and scalar piecewise-constant gamma; continuous analytic z, insulated bottom',
  graph_source='SelectivityShapeBasis.ValidationMesh/ShapeNet XY edges, original j-then-i order and strict center-inside radius test',
  mask_sha256=MASK_SHA,contact_receipt_sha256=CONTACT_SHA,reference_commit=REFERENCE_COMMIT,
  local_eigen_cache_directory=str(CACHE),independent_normal_current_QA_limit=.05,
  inherited_material_scope='HREF-MIX declared surrogates; no actual anatomical/phantom/skin-contact calibration',
  source_and_hardware_scope='Phase1 does not solve electrodes or outputs. Future two-output50ohm common-return CEM is a separately registered NEW PDE, actual hardware unverified.',
  cell_semantics=dict(physical_evaluation_cells=793860,physical_evaluation_cell_limit=800000,surface_graph_nodes=7860,
   future_surface_CEM_unknowns=7862,dense_real_matrix_entries=61779600,dense_entries_are_not_physical_cells=True),
  resource_estimate=dict(status='unmeasured theoretical allocation plan, not guaranteed peak or runtime',
   dense_input_real_bytes=494236800,returned_real_Q_bytes=494236800,workspace_conservative_allowance_bytes=536870912,
   vector_library_diagnostic_allowance_bytes=268435456,additional_local_Q_cache_bytes=494236800,
   allocation_lifetime='Dense Fortran input and returned Q may coexist through EVR; input released before blocked diagnostics; Q remains RSS while cache adds task tmpfs. Parent accounts RSS plus ALL task tmpfs throughout.',
   caveat='Implicit backend copies/workspaces and real resident peak must be measured; hard parent process watchdog is mandatory during blocking LAPACK. No600s fit promise.'))

def eigenvalue_policy(values,scale,constant_alignment_error):
 """Pure contract: prove one constant mode, then set ONLY that mode to zero."""
 vals=[float(x)for x in values];tol=TOL['eigenvalue_roundoff_relative']*scale
 require(len(vals)>1 and all(math.isfinite(x)for x in vals)and all(a<=b for a,b in zip(vals[:-1],vals[1:])),'Finite ordered eigenvalues')
 require(vals[0]>=-tol and abs(vals[0])<=tol and vals[1]>tol and vals[-1]<=scale+tol,'One roundoff-sized zero, no significant negative/extra null eigenvalue')
 require(constant_alignment_error<=TOL['constant_mode_alignment_error'],'Zero eigenvector must be constant')
 original=vals[0];vals[0]=0.;return vals,dict(raw_zero_eigenvalue_per_m2=original,zero_roundoff_tolerance_per_m2=tol,constant_alignment_error=constant_alignment_error,clipped_only_proven_constant_zero=True)

def modal_admittance(k,gamma,thickness):
 require(k>=0 and math.isfinite(k)and len(gamma)==len(thickness)>0,'Finite nonnegative modal wavenumber/layers')
 if k==0:return 0j
 y=0j
 for g,d in reversed(list(zip(gamma,thickness))):
  require(f.finite(g)and g.real>0 and g.imag>=0 and d>0,'Passive finite homogeneous layer');a=g*k;t=math.tanh(k*d);den=a+y*t
  require(f.finite(den)and abs(den)>1e-250,'Stable nonzero admittance denominator');y=a*(y+a*t)/den
 require(f.finite(y),'Finite input admittance');return y

def stable_profile(k,gamma,thickness,zs):
 """Scaled exponential solution, unit physical-top potential/insulated bottom."""
 require(k>=0,'Nonnegative mode');faces=[0.]
 for d in thickness:faces.append(faces[-1]+d)
 require(all(-1e-15<=z<=faces[-1]+1e-15 for z in zs),'Sample depths inside physical layers')
 if k==0:return [1+0j for _ in zs],[0j for _ in zs]
 below=[0j]*len(gamma);y=0j
 for i in range(len(gamma)-1,-1,-1):
  below[i]=y;a=gamma[i]*k;t=math.tanh(k*thickness[i]);y=a*(y+a*t)/(a+y*t)
 def ratio(i,z):
  g=gamma[i];d=thickness[i];r=below[i]/(g*k);e=math.exp(-2*k*d);den=(1+r)+(1-r)*e
  require(f.finite(den)and abs(den)>1e-250,'Stable profile denominator');at=math.exp(-k*z);tail=math.exp(-2*k*(d-z))
  return at*((1+r)+(1-r)*tail)/den,g*k*at*((1+r)-(1-r)*tail)/den
 top=[1+0j]
 for i,d in enumerate(thickness[:-1]):top.append(top[-1]*ratio(i,d)[0])
 values=[];currents=[]
 for z in zs:
  i=min(next((i for i in range(len(gamma))if z<=faces[i+1]+1e-15),len(gamma)-1),len(gamma)-1);v,j=ratio(i,max(0.,min(thickness[i],z-faces[i])));values.append(top[i]*v);currents.append(top[i]*j)
 require(all(f.finite(z)for z in values+currents),'Finite analytic depth profile');return values,currents

def _graph(np):
 """Exact native j-then-i strict-center cylinder XY ordering and edges."""
 nxy=PLAN['nx'];h=PLAN['h_m'];r=PLAN['radius_m'];xy=[];ij=[];lookup={}
 for j in range(nxy):
  for i in range(nxy):
   x=-r+(i+.5)*h;y=-r+(j+.5)*h
   if x*x+y*y<r*r:lookup[i,j]=len(xy);xy.append((x,y));ij.append((i,j))
 edges=[];degree=[0]*len(xy)
 for p,(i,j)in enumerate(ij):
  for qij in((i+1,j),(i,j+1)):
   if qij in lookup:q=lookup[qij];edges.append((p,q));degree[p]+=1;degree[q]+=1
 visited={0};todo=[0];neighbors=[[]for _ in xy]
 for a,b in edges:neighbors[a].append(b);neighbors[b].append(a)
 while todo:
  for q in neighbors[todo.pop()]:
   if q not in visited:visited.add(q);todo.append(q)
 require(len(visited)==len(xy)==PLAN['expected_XY_columns']and all(1<=d<=4 for d in degree),'Exact connected7860-column graph/degree bounds')
 return np.asarray(xy,dtype='<f8'),np.asarray(ij,dtype='<i4'),np.asarray(edges,dtype='<i4'),np.asarray(degree,dtype='<i4')

def _analytic_checks(eigenvalues,spec,guard,deadline):
 gamma=[complex(r['gamma_S_m']['real'],r['gamma_S_m']['imaginary'])for r in spec['material_rows']];th=spec['plan']['physical_layers_m']
 base=f.analytic_contracts(lambda:check(guard,deadline));faces,layers,zs=f.make_grid(.5,8,[19,18,56]);indices=sorted(set([0,1,len(eigenvalues)//10,len(eigenvalues)//2,len(eigenvalues)-1]));rows=[]
 for idx in indices:
  check(guard,deadline);k=math.sqrt(float(eigenvalues[idx]));y=modal_admittance(k,gamma,th);v,j=stable_profile(k,gamma,th,zs);ev,ej,states=f.exact_profile(k,gamma,th,zs)
  vre=max(abs(a-b)/max(1.,abs(b))for a,b in zip(v,ev));jre=max(abs(a-b)/max(1.,abs(b))for a,b in zip(j,ej));top=states[0][1]
  require(vre<=TOL['analytic_relative']and jre<=TOL['analytic_relative']and abs(y-top)<=TOL['analytic_absolute']+TOL['analytic_relative']*abs(top),'Stable modal profile/admittance versus independent exact bottom-up transfer')
  require(y.real>=-TOL['passive_admittance_relative']*max(1.,abs(y)),'Passive input admittance')
  c=.2+.03j;yh=modal_admittance(k,[c]*4,th);truth=c*k*math.tanh(k*sum(th))if k else 0j
  require(abs(yh-truth)<=TOL['analytic_absolute']+TOL['analytic_relative']*abs(truth),'Homogeneous closed-form layer composition')
  fits={label:f.fit_interfaces(v,zs,layers,gamma,th,states,count,1.)for label,count in(('common_two_point',2),('nearest_three_point',3))}
  rows.append(dict(eigen_index=idx,k_graph_per_m=k,lambda_graph_per_m2=float(eigenvalues[idx]),input_Y_S_m2=pair(y),independent_transfer_Y_S_m2=pair(top),profile_scaled_error_V=vre,current_scaled_error_A_m2=jre,
   sampled_exact_continuous_z_fit_diagnostics=fits,continuity_scope='Analytic interface V/J continuity is by construction; sampled2/2 and3/3 fit flags remain separate and do not clear old native5percent failures.'))
 return dict(frozen_analytic_contracts=base,selected_modal_rows=rows,passed=True,actual_CEM_solved=False,new_CEM_RHS=0)

def save_eigenvector_cache(Q,directory,guard,deadline=None):
 """Exclusive local cache chunks, <=32MiB, exact bytes readback; no overwrite."""
 p=Path(directory);require(p==CACHE and not p.exists(),'Unique canonical new local eigen cache path');p.mkdir(parents=True,exist_ok=False)
 require(sys.byteorder=='little'and Q.dtype.str=='<f8'and Q.flags.f_contiguous,'Little-endian realfloat64 Fortran Q, without dense copy')
 n=Q.shape[0];cols=max(1,PLAN['cache_raw_chunk_max_bytes']//(n*8));chunks=[]
 for start in range(0,n,cols):
  check(guard,deadline);stop=min(n,start+cols);block=Q[:,start:stop];raw=memoryview(block.T).cast('B');require(len(raw)<=PLAN['cache_raw_chunk_max_bytes'],'Declared raw chunk byte bound');path=p/('Q-cols-%05d-%05d.f64le'%(start,stop))
  with path.open('xb')as stream:stream.write(raw)
  expected=hashlib.sha256(raw).hexdigest();h=hashlib.sha256();readbytes=0
  with path.open('rb')as stream:
   for data in iter(lambda:stream.read(1024**2),b''):h.update(data);readbytes+=len(data)
  require(h.hexdigest()==expected and readbytes==len(raw),'Local complete eigen chunkSHA/bytes readback')
  chunks.append(dict(path=str(path),SHA256=expected,bytes=readbytes,row_start=0,row_stop=n,column_start=start,column_stop=stop,dtype='<f8',order='F',local_readback_passed=True,remote_verified=False))
 manifest=dict(schema='task1-local-recomputable-eigen-cache-v1',shape=list(Q.shape),dtype='<f8',order='F',chunks=chunks,local_readback_passed=True,remote_verified=False,durability='Local tmpfs only, recomputable; eigen recomputation wall cost recorded in benchmark. Chunk hashes and metadata may be published without publishing this cache.')
 with(p/'manifest.json').open('x',encoding='utf-8')as stream:json.dump(manifest,stream,allow_nan=False,indent=2)
 check(guard,deadline);return manifest

def build(spec,guard,deadline_monotonic=None):
 """Owner-only full real eigensystem + analytic MMS; ZERO CEM solves.

 Run in one separately killable numerical child. Guard checks cannot interrupt
 a blocking LAPACK call; the owning parent must monitor RSS+ALLtasktmpfs and
 enforce the registered600s hard subprocess deadline throughout this function.
 """
 check(guard,deadline_monotonic);require(spec['schema']=='task1-layer-dtn-phase1-spec-v1'and spec['plan']==PLAN and spec['tolerances']==TOL,'Exact preregistered phase1 algorithm/tolerances')
 require(spec['material_receipt_sha256']==f.MATERIAL_SHA and spec['actual_U19_config_sha256']==CONFIG_SHA and spec['material_rows']==make_spec()['material_rows'] and spec['reference_commit']==REFERENCE_COMMIT and spec['independent_normal_current_QA_limit']==.05,'Unchanged actualinputs and numerical5percentQA')
 require(spec['local_eigen_cache_directory']==str(CACHE),'Unique local cache canonical path')
 import numpy as np
 import scipy
 from scipy import sparse,linalg
 wall=time.monotonic();cpu=time.process_time();xy,ij,edges,degree=_graph(np);n=len(xy);h=PLAN['h_m'];scale=8/h**2
 require(n*sum([8,19,18,56])==PLAN['expected_evaluation_cells']<=PLAN['max_evaluation_cells'],'Unchanged evaluation-cell cap, separately recorded spectral matrix entries')
 a=edges[:,0];b=edges[:,1];rows=np.concatenate((np.arange(n),a,b));columns=np.concatenate((np.arange(n),b,a));data=np.concatenate((degree.astype(float),-np.ones(len(a)),-np.ones(len(b))))/h**2
 L=sparse.coo_matrix((data,(rows,columns)),shape=(n,n)).tocsr();constant=np.ones(n)/math.sqrt(n)
 require(float(np.max(np.abs(L@constant)))<1e-7 and (L-L.T).nnz==0,'Exact graph symmetry/constant row sum')
 check(guard,deadline_monotonic);matrix=L.toarray(order='F');require(matrix.dtype==np.float64 and matrix.flags.f_contiguous,'Real Fortran dense backend input')
 before=time.monotonic();values,Q=linalg.eigh(matrix,driver=PLAN['driver'],overwrite_a=True,check_finite=False);eigen_wall=time.monotonic()-before
 del matrix
 check(guard,deadline_monotonic);require(Q.dtype==np.float64 and Q.flags.f_contiguous and Q.shape==(n,n)and np.isfinite(values).all(),'Real complete eigenbasis ABI')
 alignment=1-abs(float(constant@Q[:,0]));vlist,zeroproof=eigenvalue_policy(values,scale,alignment);values=np.asarray(vlist,dtype='<f8')
 maxres=0.;maxnorm=0.;blockcols=PLAN['eigen_residual_block_columns']
 for first in range(0,n,blockcols):
  check(guard,deadline_monotonic);B=Q[:,first:first+blockcols];R=L@B-B*values[first:first+blockcols];r=np.sqrt(np.sum(R*R,axis=0))/scale
  maxres=max(maxres,float(np.max(r)));maxnorm=max(maxnorm,float(np.max(np.abs(np.sum(B*B,axis=0)-1))))
 require(maxres<=TOL['eigen_residual_spectral_relative']and maxnorm<=TOL['unit_norm_absolute'],'Full blocked eigen residual and all-column normalization gates')
 selected=np.unique(np.linspace(0,n-1,PLAN['orthogonality_selected_columns'],dtype=int));orth=Q.T@Q[:,selected]
 orth[selected,np.arange(len(selected))]-=1;ortherror=float(np.max(np.abs(orth)));del orth
 require(ortherror<=TOL['selected_orthogonality_absolute'],'All eigenvectors against fixed64 selected columns orthogonality gate; not exhaustive all-pairs')
 probes=np.empty((n,3),dtype=float);probes[:,0]=constant;probes[:,1]=np.sin(np.arange(n)*.37);probes[:,2]=np.cos(np.arange(n)*.23)
 transformed=Q.T@probes;returned=Q@transformed;roundtrip=float(np.linalg.norm(returned-probes)/np.linalg.norm(probes));del transformed,returned
 require(roundtrip<=TOL['transform_relative'],'RealQ forward/inverse deterministic probes')
 complexprobe=probes[:,1]+1j*probes[:,2];realcoeff=Q.T@complexprobe.real;imagcoeff=Q.T@complexprobe.imag
 reconreal=Q@realcoeff;reconimag=Q@imagcoeff;complexerror=float(np.linalg.norm((reconreal-complexprobe.real)+1j*(reconimag-complexprobe.imag))/np.linalg.norm(complexprobe))
 require(complexerror<=TOL['transform_relative'],'Complex-vector transform using separate real/imaginary realQ products')
 check(guard,deadline_monotonic);analytic=_analytic_checks(values,spec,guard,deadline_monotonic)
 cache=save_eigenvector_cache(Q,spec['local_eigen_cache_directory'],guard,deadline_monotonic)
 summary=dict(schema='task1-layer-dtn-phase1-result-v1',status='calculated_graph_eigen_analytic_MMS_only',spec=spec,
  graph=dict(nodes=n,undirected_edges=len(edges),connected_components=1,h_m=h,shape=list(Q.shape),degree_min=int(degree.min()),degree_max=int(degree.max()),
   graph_node_order='native j-then-i, strict center-inside circle; same nearest neighbor missing-face insulating graph',
   XY_float64_le_SHA256=sha(xy.tobytes(order='C')),ij_int32_le_SHA256=sha(ij.tobytes(order='C')),edges_int32_le_SHA256=sha(edges.tobytes(order='C'))),
  eigen=dict(backend='scipy.linalg.eigh',scipy_version=scipy.__version__,numpy_version=np.__version__,driver='evr',overwrite_a_requested=True,implicit_workspace_or_copy_not_individually_measured=True,parent_peak_RSS_plus_all_tmpfs_receipt_required=True,
   eigen_wall_seconds=eigen_wall,eigenvalue_min_per_m2=float(values[0]),eigenvalue_positive_min_per_m2=float(values[1]),eigenvalue_max_per_m2=float(values[-1]),zero_mode=zeroproof,
   full_blocked_spectral_scaled_residual_max=maxres,all_column_unit_norm_max_error=maxnorm,selected_orthogonality_max_error=ortherror,selected_orthogonality_column_indices=selected.tolist(),
   orthogonality_scope=PLAN['orthogonality_scope'],full_all_pairs_orthogonality_checked=False,real_roundtrip_relative_error=roundtrip,complex_roundtrip_split_real_imag_relative_error=complexerror,
   no_complex_dense_Q_or_K=True,cache=cache),analytic=analytic,wall_seconds=time.monotonic()-wall,cpu_process_seconds=time.process_time()-cpu,
  new_CEM_conditions=0,new_CEM_RHS=0,new_native_FVM_RHS=0,full_reference_field_solved=False,
  interpretation='Numerical preprocessing and manufactured operator checks only. Exact continuous-z solution remains conditional on the fixed discrete XY graph and numerical eigen tolerance; no actual CEM potential/field was calculated.',
  holds=dict(old_5percent_independent_flags_preserved=True,criteria_relaxed=False,full_SC_XY_bulk_edge_contact_convergence=False,material_or_skin_contact_or_hardware_validated=False,candidate_adopted=False,
   later_CEM_requires_new_PDE_registration=True,later_analytic_Ez_new_field_ABI_required=True,local_eigen_cache_remote_durability_unverified=True))
 check(guard,deadline_monotonic)
 return dict(summary=summary,arrays=dict(eigenvalues_per_m2=values,XY_m=xy,ij=ij,edges=edges,degree=degree))
