"""Synthetic contact-edge FV versus finite independent Fourier-Galerkin data.
Import performs no I/O, arrays, scientific imports or numerical work.
"""
from __future__ import annotations
import hashlib,io,json,math,time
from pathlib import Path
from fractions import Fraction
REFERENCE=Path('/dev/shm/task1-contact-edge-equipotential-20261025-run')
REFERENCE_COMMIT='c25c7d62783aa2ed310961ebc39784092b8b315c'
REFERENCE_CASE='P128-H2048'
FAILED_RUN=Path('/dev/shm/task1-contact-edge-fv-20261025-run')
FIRST_CASE='N40-Z8-aligned-physical_area_robin'
FIRST_NPZ_SHA='76fd031deaa845a93fd7ab5ea8549f89cd56b9c87a4a766af91d47290c111abc'
FIRST_NPZ_BYTES=21259
FAILED_SOURCE_COMMIT='64f0f2fa6bd7c4cbe1c5b62cf58ac1c812117225'
FAILED_SOURCE_SHA='d02813aacdbdccc390666878562e7bb5f9ce9dd4f0f2332f53e3b7c2aa5835cf'
FAILED_SPEC_SHA='b40f51193bb00df8989aada648fcf2ff7c6698dc22dc928fa9d1369b19ec671f'
FAILED_WORKER_SHA='b7af95e4d99176622e9b0586a3faf6e5f1dd6bff6ce627aeb08a4385c7c30816'
FAILURE_PUBLICATION=Path('/dev/shm/task1-contact-continuation-20261025/fv-failure-stage/result-publication.json')
FAILURE_COMMIT='f96126ff2b6e4c5beebc89dfb9fa295eb00ebbfe'
REFERENCE_ARRAYS_SHA='bf2eee9185dd27cf2e61d2b9e0b618e7cbc34482385683cc27af8a0b9da70b88'
METHODS=('physical_area_robin','wholepixel_halfcell_lumping','boundary_fitted')
CASES=tuple((nx,nz,phase)for nx,nz in((40,8),(80,16),(160,32))for phase in('aligned','half_cell'))
GATES=dict(relative_algebraic_residual=1e-10,relative_current_balance=1e-10,relative_complex_power_balance=1e-10,
 reference_current_relative=.02,reference_contact_P95_relative=.05,reference_primary_E_relative_L2=.05)
PLAN=dict(period_width_m=.002,SC_thickness_m=.0001,contact_endpoints_m=[-.0005,.0005],gamma_S_m=dict(real=1.,imaginary=.25),zA_ohm_m2=dict(real=1e-4,imaginary=-2e-5),
 metal_peak_V=1.,bottom_peak_V=0.,methods=list(METHODS),cases=[dict(nx=n,nz=z,phase=p)for n,z,p in CASES],
 synthetic_case_entries=18,expected_unique_FV_solves=12,maximum_registered_cells=5184,new_actual_phantom_PDE=0,new_actual_four_pad_CEM_RHS=0,
 max_cells_per_case=800000,CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,numerical_child_timeout_seconds=600,
 field_definition='Cell E is arithmetic mean of signed conservative opposite-face fields; independent of reference; contactq=I/actualcontactlength',
 reference='Published P128-H2048 finite Galerkin solution; conditional comparator, NOT continuum truth',reference_mode_block=64)

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pair(v):v=complex(v);return dict(real=v.real,imaginary=v.imag)
def cv(v):return complex(v['real'],v['imaginary'])
def python_scalars(value):
 """Lossless JSON scalar normalization, rejecting nonfinite/nonscalar objects."""
 if value is None or type(value)in(bool,str,int):return value
 if type(value)is float:
  require(math.isfinite(value),'Nonfinite metadata rejected before file open');return value
 if isinstance(value,dict):return{key:python_scalars(item)for key,item in value.items()}
 if isinstance(value,(list,tuple)):return[python_scalars(item)for item in value]
 if type(value).__name__=='ndarray':raise TypeError('Metadata arrays require explicit registered export, not implicit JSON conversion')
 if getattr(value,'ndim',None)==0 and callable(getattr(value,'item',None)):
  scalar=value.item()
  if scalar is None or type(scalar)in(bool,str,int,float):return python_scalars(scalar)
  raise TypeError('Unsupported scientific scalar payload: '+type(scalar).__name__)
 raise TypeError('Unsupported scientific metadata type: '+type(value).__name__)
def encoded(value):return(json.dumps(python_scalars(value),allow_nan=False,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def new_json(path,value):
 raw=encoded(value) # Normalize/serialize FIRST; failure never opens an empty JSON.
 with Path(path).open('xb')as stream:stream.write(raw)
def file_sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for b in iter(lambda:stream.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def check(guard,deadline):guard();require(deadline is None or time.monotonic()<deadline,'Finite FV comparison deadline')
def _reference_inputs():
 refs={};pub=json.loads((REFERENCE/'result-publication/result-publication.json').read_bytes())
 require(pub['status']=='published_readback_verified'and pub['commit']==REFERENCE_COMMIT,'Actual full independent-reference publication')
 for name in('summary.json','spec.json','receipt.json','cases/'+REFERENCE_CASE+'.json','result-publication/result-publication.json'):
  p=REFERENCE/name;require(p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2,'Bounded actual reference metadata');refs[str(p)]=sha(p.read_bytes())
 meta_path=REFERENCE/'cases'/(REFERENCE_CASE+'.json');meta_bytes=meta_path.read_bytes();metadata=json.loads(meta_bytes)
 meta_proof=pub['files']['data-native/contact-edge-equipotential-20261025/cases/'+REFERENCE_CASE+'.json']
 require(sha(meta_bytes)==meta_proof['SHA256']and meta_proof['readback_passed']is True,'Numerical reference Eenergy/current/P95 metadata authenticated against full remote publication')
 require(metadata['arrays_SHA256']==REFERENCE_ARRAYS_SHA and metadata['panels']==128 and metadata['positive_harmonics']==2048,'Exact conditional reference arrays/case identity')
 summary_raw=(REFERENCE/'summary.json').read_bytes();summary_proof=pub['files']['data-native/contact-edge-equipotential-20261025/summary.json'];summary=json.loads(summary_raw)
 require(sha(summary_raw)==summary_proof['SHA256']and summary_proof['readback_passed']is True and summary['all_diagnostic_flags_pass']is True and summary['analytic_contract']['passed']is True,'Actual published finite-reference analytic and panel/harmonic review passed; not continuum truth')
 target='data-native/contact-edge-equipotential-20261025/cases/'+REFERENCE_CASE+'.npz';proof=pub['files'][target]
 require(proof['SHA256']==REFERENCE_ARRAYS_SHA and proof['readback_passed']is True,'Fresh remote full reference-array proof')
 refs[str(REFERENCE/'cases'/(REFERENCE_CASE+'.npz'))]=REFERENCE_ARRAYS_SHA
 return refs

def _physics_spec():
 return dict(schema='task1-contact-edge-fv-spec-v1',plan=json.loads(json.dumps(PLAN)),gates=dict(GATES),reference_commit=REFERENCE_COMMIT,reference_arrays_sha256=REFERENCE_ARRAYS_SHA,
 coordinate_system='Periodic x over2mm; depthz0top to0.1mmbottom; unit out-of-plane length. I:A/m,complexpower:W/m.',
 excitation='One synthetic equipotentialpatch1Vpeak=2Vpp, entirebottom0V. No50ohm/fourpad/material/hardware model.',
 operators=dict(physical_area_robin='G=ell/(zA+dz/(2gamma))',wholepixel_halfcell_lumping='G=ell/(zA+f*dz/(2gamma)),f=ell/dx',boundary_fitted='Insert exactcontact endpoints into xedges; fullcontactfaces use physicalareaRobin'),
 reference_projection='Exact analytic Fourier rectangle-average Ex/Ez; primary full physical L2 includes finite-reference Parsevalenergy. Secondary cell-average projection is separately labelled smoothing.',
 contact_comparison='Primary pairwise physical interval intersections versus native BEMpanels; secondary conservative length-averageprojection separate.',
 reference_validity='Finite panel/harmonic diagnostics passed; edgeJmax not continuum-converged. This stage establishes no actualphantom/contact model correction.',
 original_failures_preserved=True,model_correction_applied=False,candidate_adopted=False)

def _recovery_provenance():
 publication=json.loads(FAILURE_PUBLICATION.read_bytes());require(publication['status']=='published_readback_verified'and publication['commit']==FAILURE_COMMIT,'Actual complete failure-evidence publication before reuse')
 proof=publication['files']['data-native/contact-edge-fv-20261025/failure/'+FIRST_CASE+'.npz']
 require(proof['SHA256']==FIRST_NPZ_SHA and proof['bytes']==FIRST_NPZ_BYTES and proof['readback_passed']is True,'Exact durable previously solved first-case NPZ')
 src=FAILED_RUN/'source/contact_edge_fv.py';spec=FAILED_RUN/'spec.json';worker=FAILED_RUN/'worker-receipt.json'
 require(file_sha(src)==FAILED_SOURCE_SHA and file_sha(spec)==FAILED_SPEC_SHA and file_sha(worker)==FAILED_WORKER_SHA,'Unchanged failed worker/source/original specification')
 require(json.loads(spec.read_bytes())==_physics_spec(),'Recovery must use identical physical problem, methods, gates and reference')
 sourcepub=json.loads((FAILED_RUN/'source-publication/result-publication.json').read_bytes());require(sourcepub['status']=='published_readback_verified'and sourcepub['commit']==FAILED_SOURCE_COMMIT,'Original frozen source publication')
 for target,digest in(('tools/contact_edge_fv_20261025/contact_edge_fv.py',FAILED_SOURCE_SHA),('data-native/contact-edge-fv-20261025/spec.json',FAILED_SPEC_SHA)):
  row=sourcepub['files'][target];require(row['SHA256']==digest and row['readback_passed']is True,'Original method/spec authenticated against publication')
 ownfrozen=Path(__file__).parent/'frozen_failed_contact_edge_fv.py';require(file_sha(ownfrozen)==FAILED_SOURCE_SHA,'Byte-exact prior failed source copy')
 return dict(original_run=str(FAILED_RUN),original_source_commit=FAILED_SOURCE_COMMIT,original_source_sha256=FAILED_SOURCE_SHA,original_spec_sha256=FAILED_SPEC_SHA,
  failure_publication_commit=FAILURE_COMMIT,failure_publication_receipt=str(FAILURE_PUBLICATION),first_case_id=FIRST_CASE,first_case_NPZ_sha256=FIRST_NPZ_SHA,first_case_NPZ_bytes=FIRST_NPZ_BYTES,
  prior_solved_first_phi_reused_without_spsolve=True,expected_recovered_prior_unique_solutions=1,expected_new_unique_FV_solves=11,expected_alias_entries=6,
  unchanged_physics=True,old_empty_JSON_logs_and_originals_preserved=True,rederived_array_relative_tolerance=1e-12,rederived_array_absolute_tolerance=1e-12)

def required_inputs():
 refs=_reference_inputs();_recovery_provenance()
 for path in(FAILED_RUN/'spec.json',FAILED_RUN/'worker-receipt.json',FAILED_RUN/'source/contact_edge_fv.py',FAILED_RUN/'source-publication/result-publication.json',FAILURE_PUBLICATION,Path(__file__).parent/'frozen_failed_contact_edge_fv.py'):
  refs[str(path)]=file_sha(path)
 refs[str(FAILED_RUN/'cases'/(FIRST_CASE+'.npz'))]=FIRST_NPZ_SHA
 return refs

def make_spec():
 value=_physics_spec();value['schema']='task1-contact-edge-fv-recovery-spec-v1';value['recovery']=_recovery_provenance();return value

def reuse_or_solve(np,A,rhs,saved_phi,shape,solver):
 if saved_phi is None:return solver(A,rhs),True
 phi=np.asarray(saved_phi,dtype=np.complex128);require(phi.shape==shape and np.isfinite(phi).all(),'Pinned prior phi exact finite coordinate/shape ABI')
 return phi.reshape(-1).copy(),False

def overlap_length(a,b,c,d):return max(0.,min(b,d)-max(a,c))
def contact_conductance(length,dx,dz,gamma,zA,method):
 require(0<length<=dx*(1+1e-10)and dx>0 and dz>0,'Positive actual contact fraction')
 f=length/dx;factor=f if method=='wholepixel_halfcell_lumping'else 1.
 return length/(zA+factor*dz/(2*gamma))
def depth_average_factors(k,zl,zu,t):
 require(k>=0 and 0<=zl<zu<=t*(1+1e-12),'Physical depth average')
 if k==0:return t-(zl+zu)/2,1.
 dz=zu-zl;C=-math.expm1(-k*dz)/(k*dz)/(1+math.exp(-2*k*t))
 return C*(math.exp(-k*zl)-math.exp(-k*(2*t-zu)))/k,C*(math.exp(-k*zl)+math.exp(-k*(2*t-zu)))

def exact_mesh_records(nx,phase,method):
 """Pure exact rational geometry; no floating endpoint ghost contacts."""
 require(nx in(4,40,80,160)and phase in('aligned','half_cell')and method in METHODS,'Registered uniform/aligned mesh geometry')
 L=Fraction(1,500);h=L/nx;shift=Fraction(0)if phase=='aligned'else h/2;edges=[-L/2+shift+i*h for i in range(nx+1)];a=Fraction(-1,2000);b=Fraction(1,2000)
 if method=='boundary_fitted':edges=sorted(set(edges+[a,b]))
 widths=[v-u for u,v in zip(edges[:-1],edges[1:])];contact=[max(Fraction(0),min(v,b)-max(u,a))for u,v in zip(edges[:-1],edges[1:])]
 require(sum(contact,Fraction(0))==b-a and all(w>0 and 0<=ell<=w for w,ell in zip(widths,contact)),'Exact fixed contact support/area partition')
 if phase=='aligned'or method=='boundary_fitted':require(all(ell==0 or ell==w for w,ell in zip(widths,contact)),'Aliasing only exact full/zero contact faces')
 return edges,widths,contact

def _mesh(np,nx,nz,phase,method):
 exact_edges,exact_width,exact_contact=exact_mesh_records(nx,phase,method)
 edges=np.asarray([float(v)for v in exact_edges]);dx=np.diff(edges)
 # A mathematically full face shares the identical computed face width. This
 # follows exact rational equality; no partial contact is snapped/rescaled.
 contact=np.asarray([0. if ell==0 else float(dx[i])if ell==exact_width[i]else float(ell)for i,ell in enumerate(exact_contact)])
 zfaces=np.linspace(0,PLAN['SC_thickness_m'],nz+1);require(np.all(dx>1e-14)and len(dx)*nz<=PLAN['max_cells_per_case'],'Registered finite positive FV mesh')
 require(abs(float(contact.sum())-.001)<=1e-14,'Float export preserves exact1mm physical contact')
 if phase=='aligned'or method=='boundary_fitted':require(np.all((contact==0)|(contact==dx)),'Exact f1 contact matrices required for result aliases')
 receipt=dict(exact_rational_geometry=True,no_positive_ghost_contact=True,partial_areas_snapped_or_rescaled=False,exact_contact_length_m=.001,
  exported_contact_length_m=float(contact.sum()),float_length_error_m=float(contact.sum())-.001,mathematically_full_faces=sum(ell==w for w,ell in zip(exact_width,exact_contact)),mathematically_partial_faces=sum(0<ell<w for w,ell in zip(exact_width,exact_contact)))
 return edges,zfaces,dx,contact,receipt

def _reference_averages(np,ref,edges,zfaces,gamma,guard,deadline):
 L=PLAN['period_width_m'];t=PLAN['SC_thickness_m'];dx=np.diff(edges);xc=(edges[:-1]+edges[1:])/2;nz=len(zfaces)-1;nx=len(dx)
 q0=complex(ref['q_mode0_peak_A_m2']);plus=ref['q_mode_positive_peak_A_m2'];minus=ref['q_mode_negative_peak_A_m2'];require(len(plus)==len(minus)==2048,'Frozen signed Fourier mode ABI')
 ex=np.zeros((nz,nx),np.complex128);ez=np.full((nz,nx),q0/gamma,np.complex128)
 for first in range(0,len(plus),PLAN['reference_mode_block']):
  check(guard,deadline);last=min(len(plus),first+PLAN['reference_mode_block']);k=2*math.pi*np.arange(first+1,last+1)/L
  X=np.exp(1j*k[:,None]*xc[None,:])*np.sinc(k[:,None]*dx[None,:]/(2*math.pi));XN=X.conj();FP=np.empty((nz,len(k)));FZ=np.empty_like(FP)
  for j in range(nz):
   for v,kv in enumerate(k):FP[j,v],FZ[j,v]=depth_average_factors(float(kv),float(zfaces[j]),float(zfaces[j+1]),t)
  pp=FP*plus[None,first:last]/gamma;pm=FP*minus[None,first:last]/gamma
  ex+=(-1j*k[None,:]*pp)@X+(1j*k[None,:]*pm)@XN
  ez+=(FZ*plus[None,first:last]/gamma)@X+(FZ*minus[None,first:last]/gamma)@XN
 return ex,ez

def _contact_errors(np,edges,contact,J,ref):
 panel=ref['panel_edges_m'];q=ref['q_panel_peak_A_m2'];num=0.;den=0.;secondary=0.;projectionden=0.;length=0.;pairs=0
 for i,ell in enumerate(contact):
  if ell<=0:continue
  left=max(float(edges[i]),PLAN['contact_endpoints_m'][0]);right=min(float(edges[i+1]),PLAN['contact_endpoints_m'][1]);avg=0j
  for a in range(len(q)):
   w=overlap_length(left,right,float(panel[a]),float(panel[a+1]))
   if w:
    num+=w*abs(J[i]-q[a])**2;den+=w*abs(q[a])**2;avg+=w*q[a];length+=w;pairs+=1
  avg/=ell;secondary+=ell*abs(J[i]-avg)**2;projectionden+=ell*abs(avg)**2
 return dict(primary_pairwise_relative_L2=math.sqrt(num/max(den,1e-300)),primary_pairwise_absolute_RMS_A_m2=math.sqrt(num/(2*length)),secondary_average_projection_relative_L2=math.sqrt(secondary/max(projectionden,1e-300)),common_contact_length_m=length,pairwise_intersections=pairs,
 interpretation='Primary retains panel/subcell variation; secondary averaging can hide error. No indexwise difference or continuum-edge-maximum claim.')

def _weighted_p95(np,values,length):
 select=length>0;v=values[select];w=length[select];order=np.argsort(v,kind='stable');idx=min(int(np.searchsorted(np.cumsum(w[order]),.95*w.sum(),side='left')),len(v)-1);return float(v[order[idx]])

def _case(np,nx,nz,phase,method,ref,refmeta,guard,deadline,saved_phi=None):
 from scipy import sparse
 from scipy.sparse.linalg import spsolve
 check(guard,deadline);start=time.monotonic();gamma=cv(PLAN['gamma_S_m']);zA=cv(PLAN['zA_ohm_m2']);V=complex(PLAN['metal_peak_V']);edges,zfaces,dx,contact,mesh_receipt=_mesh(np,nx,nz,phase,method);N=len(dx);dz=PLAN['SC_thickness_m']/nz;n=N*nz
 diagonal=np.zeros(n,np.complex128);rhs=np.zeros(n,np.complex128);rr=[];cc=[];dd=[];graph=[]
 def add(p,q,g):
  diagonal[p]+=g;diagonal[q]+=g;rr.extend((p,q));cc.extend((q,p));dd.extend((-g,-g));graph.append((p,q,g))
 for z in range(nz):
  for i in range(N):
   p=z*N+i;j=(i+1)%N;add(p,z*N+j,gamma*dz/((dx[i]+dx[j])/2))
   if z+1<nz:add(p,p+N,gamma*dx[i]/dz)
 topG=np.zeros(N,np.complex128)
 for i,ell in enumerate(contact):
  if ell>0:topG[i]=contact_conductance(float(ell),float(dx[i]),dz,gamma,zA,method);diagonal[i]+=topG[i];rhs[i]+=topG[i]*V
 bottomG=gamma*dx/(dz/2)
 for i,g in enumerate(bottomG):diagonal[(nz-1)*N+i]+=g
 rr.extend(range(n));cc.extend(range(n));dd.extend(diagonal);A=sparse.coo_matrix((dd,(rr,cc)),shape=(n,n)).tocsr();phi,new_solve_performed=reuse_or_solve(np,A,rhs,saved_phi,(nz,N),spsolve);residual=float(np.linalg.norm(A@phi-rhs)/max(float(np.linalg.norm(rhs)),1e-300));phi=phi.reshape((nz,N))
 require(np.isfinite(phi).all(),'Finite FV linear-system solution')
 Ipatch=topG*(V-phi[0]);I=complex(Ipatch.sum());Ibottom=complex(bottomG@phi[-1]);current_error=abs(I-Ibottom)/max(abs(I),abs(Ibottom),1e-300)
 source=.5*V*I.conjugate();contactP=.5*zA*sum(float(abs(Ipatch[i])**2/contact[i])for i in range(N)if contact[i]>0)
 halfP=0j
 for i,ell in enumerate(contact):
  if ell>0:
   area=dx[i]if method=='wholepixel_halfcell_lumping'else ell;halfP+=.5*dz/(2*gamma*area)*abs(Ipatch[i])**2
 flat=phi.reshape(-1);bulk=sum((.5*g.conjugate()*abs(flat[p]-flat[q])**2 for p,q,g in graph),0j);bottomP=.5*np.sum(bottomG.conj()*abs(phi[-1])**2);psum=contactP+halfP+bulk+bottomP;power_error=abs(source-psum)/max(abs(source),abs(psum),1e-300)
 Ex=np.empty_like(phi);Ez=np.empty_like(phi)
 for i in range(N):
  east=-(phi[:,(i+1)%N]-phi[:,i])/((dx[i]+dx[(i+1)%N])/2);west=-(phi[:,i]-phi[:,(i-1)%N])/((dx[i]+dx[(i-1)%N])/2);Ex[:,i]=(east+west)/2
 faceEz=np.empty((nz+1,N),np.complex128);faceEz[0]=Ipatch/dx/gamma;faceEz[1:nz]=-(phi[1:]-phi[:-1])/dz;faceEz[nz]=phi[-1]/(dz/2);Ez[:]=(faceEz[:-1]+faceEz[1:])/2
 Exref,Ezref=_reference_averages(np,ref,edges,zfaces,gamma,guard,deadline);weights=dz*dx[None,:];reference_energy=refmeta['slab_field']['finite_series_integral_peak_E_squared_V2'];numerical_energy=float(np.sum(weights*(abs(Ex)**2+abs(Ez)**2)));cross=2*float(np.real(np.sum(weights*(Ex.conj()*Exref+Ez.conj()*Ezref))));error_energy=numerical_energy-cross+reference_energy
 require(error_energy>=-1e-10*reference_energy,'Physical full-field error energy cannot be materially negative');roundoff=error_energy<0;error_energy=max(0.,error_energy)
 projected_error=float(np.sum(weights*(abs(Ex-Exref)**2+abs(Ez-Ezref)**2)));projected_ref=float(np.sum(weights*(abs(Exref)**2+abs(Ezref)**2)));J=np.zeros(N,np.complex128);positive=contact>0;J[positive]=Ipatch[positive]/contact[positive];jrms=abs(J)/math.sqrt(2);p95=_weighted_p95(np,jrms,contact);Iref=cv(refmeta['contact_current_peak_A_per_m']);Ierror=abs(I-Iref)/abs(Iref);P95error=abs(p95-refmeta['contact_q_native_panel']['RMS_P95_A_m2'])/refmeta['contact_q_native_panel']['RMS_P95_A_m2'];Eerror=math.sqrt(error_energy/reference_energy)
 internal=[dict(metric='relative_algebraic_residual',value=residual,limit=1e-10,passed=residual<=1e-10),dict(metric='relative_current_balance',value=current_error,limit=1e-10,passed=current_error<=1e-10),dict(metric='relative_complex_power_balance',value=power_error,limit=1e-10,passed=power_error<=1e-10)]
 flags=[dict(metric='reference_current_relative',value=Ierror,limit=.02,passed=Ierror<=.02),dict(metric='reference_contact_P95_relative',value=P95error,limit=.05,passed=P95error<=.05),dict(metric='reference_primary_E_relative_L2',value=Eerror,limit=.05,passed=Eerror<=.05)]
 L=PLAN['period_width_m'];t=PLAN['SC_thickness_m'];cid='N%d-Z%d-%s-%s'%(nx,nz,phase,method)
 arrays=dict(x_edges_m=edges,z_faces_m=zfaces,dx_m=dx,contact_length_m=contact,phi_peak_V=phi,Ex_FV_peak_V_m=Ex,Ez_FV_peak_V_m=Ez,Ex_reference_cell_average_peak_V_m=Exref,Ez_reference_cell_average_peak_V_m=Ezref,contact_J_peak_A_m2=J,contact_I_peak_A_per_m=Ipatch)
 metadata=dict(case_id=cid,mesh_receipt=mesh_receipt,nx_nominal=nx,nx_actual=N,nz=nz,cells=n,phase=phase,method=method,unique_solve=True,new_solve_performed=bool(new_solve_performed),recovered_prior_compute=not bool(new_solve_performed),internal_gates=internal,internal_gates_passed=all(r['passed']for r in internal),reference_flags=flags,reference_flags_passed=all(r['passed']for r in flags),
 contact_current_peak_A_per_m=pair(I),bottom_current_peak_A_per_m=pair(Ibottom),contact_J_RMS_P95_A_m2=p95,contact_J_RMS_max_A_m2=float(jrms.max()),contact_maximum_scope='Mesh-dependent piecewise constant patch density, not continuum maximum',
 complex_powers_W_per_m=dict(source=pair(source),contact=pair(contactP),top_half_SC=pair(halfP),graph_bulk=pair(bulk),bottom_half_SC=pair(bottomP)),
 physical_E_comparison=dict(primary_absolute_RMS_L2_V_m=math.sqrt(error_energy/(2*L*t)),primary_derived_J_absolute_RMS_L2_A_m2=abs(gamma)*math.sqrt(error_energy/(2*L*t)),primary_relative_L2=Eerror,numerical_E_RMS_L2_V_m=math.sqrt(numerical_energy/(2*L*t)),reference_E_RMS_L2_V_m=math.sqrt(reference_energy/(2*L*t)),primary_error_energy_peak_V2=error_energy,roundoff_negative_energy_truncated=roundoff,
 secondary_cell_average_projection_relative_L2=math.sqrt(projected_error/max(projected_ref,1e-300)),reference_integral='Exact finite Fourier Parseval energy and analytic rectangle averages, no pointwise or indexwise subtraction',secondary_scope='Averaged projection can conceal unresolved reference-field variation'),
 contact_comparison=_contact_errors(np,edges,contact,J,ref),wall_seconds=time.monotonic()-start,new_actual_phantom_PDE=0,new_actual_four_pad_CEM_RHS=0,candidate_adopted=False)
 return dict(metadata=python_scalars(metadata),arrays=arrays)

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(spec==make_spec()and callable(guard),'Frozen finite FV operator/reference comparison');check(guard,deadline_monotonic);out=Path(output_dir);require(out.is_absolute()and out.parent==Path('/dev/shm')and out.name.startswith('task1-contact-edge-fv-')and out.is_dir()and not out.is_symlink(),'Canonical owner-created output')
 import numpy as np
 required_inputs();reference_path=REFERENCE/'cases'/(REFERENCE_CASE+'.npz');require(file_sha(reference_path)==REFERENCE_ARRAYS_SHA,'Actual finite-reference complete bytesSHA before decode')
 with np.load(reference_path,allow_pickle=False)as data:ref={k:data[k]for k in data.files}
 refmeta=json.loads((REFERENCE/'cases'/(REFERENCE_CASE+'.json')).read_bytes());spec_sha=sha(encoded(spec));method_sha=file_sha(Path(__file__).resolve());casesdir=out/'cases';progress=out/'progress';casesdir.mkdir(exist_ok=True);progress.mkdir(exist_ok=True);completed=[];results=[];aliases={};solves=0
 for nx,nz,phase in CASES:
  for method in METHODS:
   check(guard,deadline_monotonic);require(file_sha(Path(__file__).resolve())==method_sha,'Frozen source identity');cid='N%d-Z%d-%s-%s'%(nx,nz,phase,method);meta_path=casesdir/(cid+'.json');arr_path=casesdir/(cid+'.npz');key=(nx,nz,phase)
   if meta_path.exists():
    meta=json.loads(meta_path.read_bytes());require(meta['spec_sha256']==spec_sha and meta['method_sha256']==method_sha,'Same-spec completed case resume')
    if meta.get('alias_of'):result=dict(metadata=meta,arrays=None)
    else:
     require(meta['arrays_SHA256']==file_sha(arr_path),'Completed same-case full arraySHA');result=dict(metadata=meta,arrays=None)
   elif phase=='aligned'and method!='physical_area_robin':
    base=aliases[key];meta=json.loads(encoded(base));meta.update(case_id=cid,method=method,unique_solve=False,new_solve_performed=False,recovered_prior_compute=False,uses_prior_recovered_solution=bool(base.get('recovered_prior_compute')),alias_of=base['case_id'],alias_reason='Contact edges already lie on uniform faces; exactf1 matrices/physical geometry identical, no new solve',spec_sha256=spec_sha,method_sha256=method_sha);new_json(meta_path,meta);result=dict(metadata=meta,arrays=None)
   else:
    require(not arr_path.exists(),'Partial array preserved; root recovery/new run required')
    if cid==FIRST_CASE:
     previous=FAILED_RUN/'cases'/(FIRST_CASE+'.npz');require(previous.is_file()and not previous.is_symlink()and previous.stat().st_size==FIRST_NPZ_BYTES and file_sha(previous)==FIRST_NPZ_SHA,'Full exact durable first-case raw bytes before decode')
     with np.load(previous,allow_pickle=False)as saved:original={k:saved[k]for k in saved.files}
     result=_case(np,nx,nz,phase,method,ref,refmeta,guard,deadline_monotonic,saved_phi=original['phi_peak_V'])
     require(set(original)==set(result['arrays']),'Identical original/rederived array ABI');checks=[]
     for name,before in original.items():
      after=result['arrays'][name];same=before.shape==after.shape and np.allclose(before,after,rtol=1e-12,atol=1e-12,equal_nan=False)
      if name in('x_edges_m','z_faces_m','dx_m','contact_length_m'):same=same and np.array_equal(before,after)
      require(bool(same),'Prior raw/rederived physical-array mismatch: '+name);checks.append(dict(array=name,passed=True,maximum_absolute_difference=float(np.max(abs(before-after)))if before.size else 0.))
     require(result['metadata']['new_solve_performed']is False and result['metadata']['recovered_prior_compute']is True,'Saved first solution reused; no spsolve')
     with previous.open('rb')as old,arr_path.open('xb')as target:
      for block in iter(lambda:old.read(1024**2),b''):target.write(block)
     require(file_sha(arr_path)==FIRST_NPZ_SHA,'Original first NPZ copied unchanged, not recompressed/recomputed')
     result['metadata'].update(calculation_source_sha256=FAILED_SOURCE_SHA,calculation_source_commit=FAILED_SOURCE_COMMIT,verification_source_sha256=method_sha,recovery_prior_array_checks=checks,original_NPZ_bytes_reused=True,recovered_from_NPZ_SHA256=FIRST_NPZ_SHA,failure_publication_commit=FAILURE_COMMIT)
    else:
     result=_case(np,nx,nz,phase,method,ref,refmeta,guard,deadline_monotonic)
     with arr_path.open('xb')as stream:np.savez_compressed(stream,**result['arrays'])
     solves+=1
    result['metadata'].update(spec_sha256=spec_sha,method_sha256=method_sha,arrays_SHA256=file_sha(arr_path));new_json(meta_path,result['metadata'])
   meta=result['metadata'];results.append(meta)
   if method=='physical_area_robin':aliases[key]=meta
   marker=dict(case_id=cid,metadata_SHA256=file_sha(meta_path),complete=True,unique_solve=meta['unique_solve'],alias_of=meta.get('alias_of'));p=progress/(cid+'.json')
   if p.exists():require(json.loads(p.read_bytes())==marker,'Immutable completed checkpoint')
   else:new_json(p,marker)
   completed.append(marker);index=dict(schema='task1-contact-edge-FV-resume-index-v1',completed=list(completed),remaining_entries=18-len(completed),no_completed_case_recomputed=True,spec_sha256=spec_sha,method_sha256=method_sha)
   snap=out/('resume-index-%02d.json'%len(completed))
   if not snap.exists():new_json(snap,index)
   temp=out/('resume-index-%d.new'%time.time_ns());new_json(temp,index);temp.replace(out/'resume-index.json')
   require(meta['internal_gates_passed'],'Invalid FV solve/internal conservation gate; raw arrays/proof/checkpoint preserved')
 check(guard,deadline_monotonic);require(file_sha(reference_path)==REFERENCE_ARRAYS_SHA,'Reference bytes unchanged after comparison')
 return dict(summary=python_scalars(dict(schema='task1-contact-edge-fv-recovery-result-v1',status='finite_FV_reference_comparison_calculated_unadopted',spec=spec,cases=results,completed_entries=len(results),unique_FV_solutions=sum(r['unique_solve']for r in results),new_solves_this_invocation=solves,recovered_prior_unique_solutions=sum(bool(r.get('recovered_prior_compute'))for r in results),new_unique_solutions_in_recovery_batch=sum(bool(r.get('new_solve_performed'))for r in results),
 all_internal_gates_passed=all(r['internal_gates_passed']for r in results),all_reference_flags_passed=all(r['reference_flags_passed']for r in results),
 reference_scope='Conditional finite P128-H2048 comparator; neither continuum edge Jmax nor actual4pad/contact validation',reference_arrays_SHA256=REFERENCE_ARRAYS_SHA,
 new_actual_phantom_PDE=0,new_actual_four_pad_CEM_RHS=0,synthetic_FV_linear_system_RHS=12,old_failed_actual_screens_preserved=True,model_correction_applied=False,candidate_adopted=False,resume_index_SHA256=file_sha(out/'resume-index.json'))),arrays={})
