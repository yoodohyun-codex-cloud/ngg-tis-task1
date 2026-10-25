"""Nonuniform weighted-DtN Fourier MMS; no import IO/arrays/scientific imports.
Separate periodic rectangle/top-Dirichlet validation, never the four-pad model.
"""
from __future__ import annotations
import hashlib,json,math,time
from fractions import Fraction
from pathlib import Path
CONFIG=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run/configs/baseline-square15-human-sine2000-sc8-vs19uniform-bulk19-18-56-xy100.properties')
MATERIAL=CONFIG.parent.parent/'material-input.json'
CONFIG_SHA='a20334ff9788323b065c89968cd18d764e813beb4017879bdc390f19a4db6445'
MATERIAL_SHA='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
EPS0=8.8541878128e-12
PLAN=dict(period_width_m=.05,SC_thickness_m=.0001,grids=[16,32,64],bottoms=['Dirichlet0','Neumann0'],
 moved_faces_m=[-.0175,-.0025,.0025,.0175],spatial_top_forcing='cos(kappa*x)+0.3*sin(2*kappa*y), kappa=2pi/L; exact physical cell averages',
 depth_quadrature_points=5,energy_quadrature_points=8,maximum_physical_samples=800000,
 MMS_conditions=6,one_dimensional_eigensystems=3,new_actual_circle_eigensystems=0,new_actual_phantom_PDE=0,new_actual_four_pad_CEM_RHS=0,
 CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,numerical_child_timeout_seconds=600)
GATES=dict(eigen_relative_residual=1e-10,orthogonality_absolute=1e-10,weighted_null_alignment=1e-10,
 uniform_limit_relative=1e-12,full_contact_relative=1e-10,parseval_relative=1e-10,complex_power_relative=1e-10,
 finest_relative_phi=.02,finest_relative_qtop=.02,finest_relative_Ez=.02,finest_relative_Ex=.05,finest_relative_Ey=.05,minimum_observed_order=1.)
FLOORS=dict(phi=1e-12,qtop=1e-12,Ex=1e-10,Ey=1e-10,Ez=1e-10)
GAUSS5=((-0.9061798459386640,.2369268850561891),(-.5384693101056831,.4786286704993665),(0.,.5688888888888889),(.5384693101056831,.4786286704993665),(.9061798459386640,.2369268850561891))
GAUSS8=((-0.9602898564975363,.1012285362903763),(-.7966664774136267,.2223810344533745),(-.5255324099163290,.3137066458778873),(-.1834346424956498,.3626837833783620),(.1834346424956498,.3626837833783620),(.5255324099163290,.3137066458778873),(.7966664774136267,.2223810344533745),(.9602898564975363,.1012285362903763))

def require(ok,message):
 if not ok:raise ValueError(message)
def pair(z):z=complex(z);return dict(real=z.real,imaginary=z.imag)
def cv(z):return complex(z['real'],z['imaginary'])
def sha(raw):return hashlib.sha256(raw).hexdigest()
def native(value):
 if value is None or type(value)in(bool,str,int):return value
 if type(value)is float:require(math.isfinite(value),'Finite metadata');return value
 if isinstance(value,dict):return{k:native(v)for k,v in value.items()}
 if isinstance(value,(list,tuple)):return[native(v)for v in value]
 if type(value).__name__=='ndarray':raise TypeError('Metadata arrays require explicit export')
 if getattr(value,'ndim',None)==0 and callable(getattr(value,'item',None)):return native(value.item())
 raise TypeError('Unsupported metadata type '+type(value).__name__)
def encoded(v):return(json.dumps(native(v),allow_nan=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def new_json(path,value):
 raw=encoded(value)
 with Path(path).open('xb')as stream:stream.write(raw)
def file_sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for b in iter(lambda:stream.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def check(guard,deadline):guard();require(deadline is None or time.monotonic()<deadline,'Finite weighted MMS deadline')
def required_inputs():
 require(file_sha(CONFIG)==CONFIG_SHA and file_sha(MATERIAL)==MATERIAL_SHA,'Frozen original2000Hz material source only; no contact/hardware import')
 return{str(CONFIG):CONFIG_SHA,str(MATERIAL):MATERIAL_SHA}
def make_spec():
 required_inputs();cfg={k.strip():v.strip()for line in CONFIG.read_text().splitlines()if '='in line and not line.lstrip().startswith(('#','!'))for k,v in[line.split('=',1)]}
 gamma=complex(float(cfg['sc.sigma.2000']),2*math.pi*2000*EPS0*float(cfg['sc.epsilon_r.2000']))
 require(gamma.real>0 and gamma.imag>0,'Positive source-verified SC scalar admittivity')
 return dict(schema='task1-weighted-DtN-Fourier-MMS-spec-v1',plan=json.loads(json.dumps(PLAN)),gates=dict(GATES),absolute_error_floors=dict(FLOORS),
  gamma_SC_S_m=pair(gamma),gamma_config_SHA256=CONFIG_SHA,material_receipt_SHA256=MATERIAL_SHA,material_scope='Original2kHz HREF-MIX declared SC surrogate; no new human/phantom calibration',
  coordinate_system='Periodic50mm by50mm rectangle, SCslab0.1mm, depth0top; not a circle or actual phantom. Peak exp(+jomega*t).',
  top_boundary='Prescribed spatially variable Dirichlet cell-average Fourier forcing; no equipotential pads/metals/50ohm',
  zero_modes='Dirichlet bottom: F0=1-z/t,Y0=gamma/t; Neumann bottom:F0=1,Y0=0. Actual four-pad insulated bottom is unchanged.',
  field_ABI='phi and Ez use analytic modal depth; Ex/Ey are explicitly conservative nonuniform opposite-face gradient averages; J=gammaE derived, not independent verification',
  norm='Area-mass weighted cell-average spatialRMS of PEAK phasor errors; temporalRMS is separately divided bysqrt2; five fixed Gauss depth points for volume metrics, exact physical lateral Fourier cell averages. Not continuous 3D truth.',
  energy='VI*/2 signed complex power; independent8point depth quadrature of (G²+lambdaF²), discrete horizontal eigenvalue retained, no continuum error conflation.',
  rate='Observed pairwise order of absolute weighted RMS errors vs nominalh=L/n. >=1 is a predeclared engineering screening hypothesis, not a theorem for abrupt moved-face TPFA. Failures/inconclusivefloors remain.',
  quadrature='Five physical Gauss depth points fixed acrossallgrids; eight-point energy quadrature independent from analytic modal boundarypower',
  no_fourier_as_discrete_eigenvector_assumption=True,no_fitted_curves_or_criteria_relaxation=True,candidate_adopted=False)

def moved_faces(n):
 require(n in PLAN['grids'],'Registered three grids');L=Fraction(1,20);h=L/n;original=[-L/2+i*h for i in range(n+1)];faces=list(original);used=set()
 for target in(Fraction(-7,400),Fraction(-1,400),Fraction(1,400),Fraction(7,400)):
  j=min(range(1,n),key=lambda i:(abs(original[i]-target),i));require(j not in used,'Distinct nearest faces');used.add(j);faces[j]=target
 require(all(a<b for a,b in zip(faces[:-1],faces[1:]))and faces[-1]-faces[0]==L,'Positive periodic nonuniform intervals')
 return faces

def profile(k,z,t,bottom):
 require(k>=0 and 0<=z<=t*(1+1e-12)and bottom in PLAN['bottoms'],'Valid synthetic modal state')
 if k==0:return(1-z/t,1/t)if bottom=='Dirichlet0'else(1.,0.)
 a=math.exp(-k*z);tail=math.exp(-2*k*(t-z))
 if bottom=='Dirichlet0':den=-math.expm1(-2*k*t);return a*(-math.expm1(-2*k*(t-z)))/den,k*a*(1+tail)/den
 den=1+math.exp(-2*k*t);return a*(1+tail)/den,k*a*(-math.expm1(-2*k*(t-z)))/den

def _axis(np,faces):
 edges=np.asarray([float(v)for v in faces]);dx=np.asarray([float(b-a)for a,b in zip(faces[:-1],faces[1:])]);n=len(dx);K=np.zeros((n,n));diagonal=np.zeros(n)
 for i in range(n):
  j=(i+1)%n;g=1/((dx[i]+dx[j])/2);K[i,i]+=g;K[j,j]+=g;K[i,j]-=g;K[j,i]-=g
 r=np.sqrt(dx);A=K/r[:,None]/r[None,:];return edges,dx,K,A

def _basis(np,n):
 edges,dx,K,A=_axis(np,moved_faces(n));eigen,Q=np.linalg.eigh(A);scale=float(np.linalg.norm(A,ord=np.inf));zero=np.sqrt(dx/dx.sum());alignment=1-abs(float(zero@Q[:,0]));tol=1e-10*scale
 require(eigen[0]>=-tol and abs(eigen[0])<=tol and eigen[1]>tol and alignment<=GATES['weighted_null_alignment'],'One justified weighted constant mode, no significant negative mode')
 raw_zero=float(eigen[0]);eigen[0]=0.;res=float(np.linalg.norm(A@Q-Q*eigen)/max(scale*float(np.linalg.norm(Q)),1e-300));orth=float(np.max(abs(Q.T@Q-np.eye(n))))
 require(res<=GATES['eigen_relative_residual']and orth<=GATES['orthogonality_absolute'],'One-dimensional weighted eigen contracts')
 # Independent uniform reduction to the existing h^-2 periodic stencil.
 L=PLAN['period_width_m'];h=L/n;uniform=[Fraction(-1,40)+i*Fraction(1,20*n)for i in range(n+1)];_,udx,uK,uA=_axis(np,uniform);old=np.zeros((n,n))
 for i in range(n):old[i,i]=2/h**2;old[i,(i-1)%n]=-1/h**2;old[i,(i+1)%n]=-1/h**2
 uniform_error=float(np.max(abs(uA-old))/max(float(np.max(abs(old))),1e-300));require(uniform_error<=GATES['uniform_limit_relative'],'Uniform area-mass operator reduction')
 return dict(edges=edges,dx=dx,K=K,A=A,eigen=eigen,Q=Q),dict(n=n,weighted_eigen_relative_residual=res,orthogonality_max_error=orth,weighted_null_alignment_error=alignment,raw_zero_eigenvalue=raw_zero,only_proven_zero_clipped=True,uniform_stencil_reduction_relative=uniform_error,all_passed=True)

def _coeff(np,basis,phi):
 r=np.sqrt(basis['dx']);return basis['Q'].T@(r[:,None]*phi*r[None,:])@basis['Q']
def _reconstruct(np,basis,coeff):
 r=np.sqrt(basis['dx']);return(basis['Q']@coeff@basis['Q'].T)/r[:,None]/r[None,:]
def _physical_ref(np,basis,z,bottom,gamma):
 edges=basis['edges'];dx=basis['dx'];x=(edges[:-1]+edges[1:])/2;k=2*math.pi/PLAN['period_width_m'];t=PLAN['SC_thickness_m'];c=np.cos(k*x)*np.sinc(k*dx/(2*math.pi));s=np.sin(2*k*x)*np.sinc(2*k*dx/(2*math.pi));sx=np.sin(k*x)*np.sinc(k*dx/(2*math.pi));cy=np.cos(2*k*x)*np.sinc(2*k*dx/(2*math.pi));Fx,Gx=profile(k,z,t,bottom);Fy,Gy=profile(2*k,z,t,bottom)
 return dict(phi=Fx*c[None,:]+.3*Fy*s[:,None],Ex=k*Fx*sx[None,:]+np.zeros((len(x),1)),Ey=-.6*k*Fy*cy[:,None]+np.zeros((1,len(x))),Ez=Gx*c[None,:]+.3*Gy*s[:,None])

def _gradients(np,phi,dx):
 east=-(np.roll(phi,-1,axis=1)-phi)/((dx+np.roll(dx,-1))/2)[None,:];west=-(phi-np.roll(phi,1,axis=1))/((dx+np.roll(dx,1))/2)[None,:]
 south=-(np.roll(phi,-1,axis=0)-phi)/((dx+np.roll(dx,-1))/2)[:,None];north=-(phi-np.roll(phi,1,axis=0))/((dx+np.roll(dx,1))/2)[:,None]
 return(east+west)/2,(south+north)/2

def _error(np,actual,reference,weights,floor):
 den=float(np.sum(weights*abs(reference)**2));num=float(np.sum(weights*abs(actual-reference)**2));volume=float(np.sum(weights));abs_error=math.sqrt(num/volume);ref=math.sqrt(den/volume)
 return dict(absolute_spatial_peak_RMS_L2=abs_error,reference_spatial_peak_RMS_L2=ref,absolute_temporal_RMS_L2=abs_error/math.sqrt(2),reference_temporal_RMS_L2=ref/math.sqrt(2),relative_L2=abs_error/max(ref,floor),absolute_denominator_floor=floor,denominator_floor_used=ref<floor)

def _constant_contract(np,basis,bottom,gamma):
 n=len(basis['dx']);ones=np.ones((n,n));B=_coeff(np,basis,ones);lam=basis['eigen'][:,None]+basis['eigen'][None,:];t=PLAN['SC_thickness_m'];Y=np.empty_like(lam,dtype=np.complex128)
 for index,v in np.ndenumerate(lam):Y[index]=gamma*profile(math.sqrt(float(v)),0.,t,bottom)[1]
 q=_reconstruct(np,basis,Y*B);truth=gamma/t if bottom=='Dirichlet0'else 0j;mass=basis['dx'][:,None]*basis['dx'][None,:];I=complex(np.sum(mass*q));expected=truth*PLAN['period_width_m']**2
 qerror=float(np.max(abs(q-truth)))/max(abs(gamma/t),1e-12);Ierror=abs(I-expected)/max(abs(gamma/t)*PLAN['period_width_m']**2,1e-12)
 require(qerror<=GATES['full_contact_relative']and Ierror<=GATES['full_contact_relative'],'Constant full-contact Dirichlet/nonflux Neumann normalization')
 return dict(bottom=bottom,peak_current_A=pair(I),expected_peak_current_A=pair(expected),q_relative_error=qerror,current_relative_error=Ierror,passed=True,scope='Synthetic prescribed full top, no actual pad/source circuit')

def _case(np,n,bottom,basis,basisproof,spec,guard,deadline):
 check(guard,deadline);start=time.monotonic();gamma=cv(spec['gamma_SC_S_m']);t=PLAN['SC_thickness_m'];dx=basis['dx'];mass=dx[:,None]*dx[None,:];area=float(mass.sum());top=_physical_ref(np,basis,0.,bottom,gamma)['phi'];B=_coeff(np,basis,top);lam=basis['eigen'][:,None]+basis['eigen'][None,:];Y=np.empty((n,n),np.complex128)
 for index,value in np.ndenumerate(lam):Y[index]=gamma*profile(math.sqrt(float(value)),0.,t,bottom)[1]
 # Uniform-area ABI identity uses an arbitrary real orthonormal tensorbasis;
 # it does not assume the nonuniform eigenvectors are uniform Fourier modes.
 h=PLAN['period_width_m']/n;test=np.arange(n*n,dtype=float).reshape((n,n))/(n*n);Q=basis['Q'];buniform=Q.T@(h*test)@Q
 weighted_current=h*(Q@(Y*buniform)@Q.T);old_uniform_current=h*h*(Q@(Y*(Q.T@test@Q))@Q.T)
 uniform_abi=float(np.linalg.norm(weighted_current-old_uniform_current)/max(float(np.linalg.norm(old_uniform_current)),1e-300));require(uniform_abi<=GATES['uniform_limit_relative'],'Uniform h² DtN current ABI reduction')
 qtop=_reconstruct(np,basis,Y*B);top_roundtrip=_reconstruct(np,basis,B);parseval=abs(float(np.sum(mass*abs(top)**2))-float(np.sum(abs(B)**2)))/max(float(np.sum(mass*abs(top)**2)),1e-300)
 require(parseval<=GATES['parseval_relative']and float(np.max(abs(top_roundtrip-top)))<=1e-10,'Weighted tensor coefficient roundtrip and Parseval')
 z=np.asarray([t*(p+1)/2 for p,w in GAUSS5]);zw=np.asarray([t*w/2 for p,w in GAUSS5]);fields={k:[]for k in('phi','Ex','Ey','Ez')};refs={k:[]for k in fields}
 for depth in z:
  check(guard,deadline);F=np.empty((n,n));G=np.empty_like(F)
  for index,value in np.ndenumerate(lam):F[index],G[index]=profile(math.sqrt(float(value)),float(depth),t,bottom)
  phi=_reconstruct(np,basis,B*F);Ez=_reconstruct(np,basis,B*G);Ex,Ey=_gradients(np,phi,dx);reference=_physical_ref(np,basis,float(depth),bottom,gamma)
  for key,val in dict(phi=phi,Ex=Ex,Ey=Ey,Ez=Ez).items():fields[key].append(val);refs[key].append(reference[key])
 fields={k:np.asarray(v)for k,v in fields.items()};refs={k:np.asarray(v)for k,v in refs.items()};volume_weights=zw[:,None,None]*mass[None,:,:];errors={k:_error(np,fields[k],refs[k],volume_weights,FLOORS[k])for k in fields}
 qref=gamma*_physical_ref(np,basis,0.,bottom,gamma)['Ez'];errors['qtop']=_error(np,qtop,qref,mass,FLOORS['qtop'])
 source=.5*complex(np.sum(mass*top*qtop.conj()));modal=.5*complex(np.sum(abs(B)**2*Y.conj()));modalpower=abs(source-modal)/max(abs(source),abs(modal),1e-300)
 energy=np.zeros((n,n))
 for node,weight in GAUSS8:
  check(guard,deadline);depth=t*(node+1)/2
  for index,value in np.ndenumerate(lam):F,G=profile(math.sqrt(float(value)),depth,t,bottom);energy[index]+=t*weight/2*(G*G+float(value)*F*F)
 quadrature=.5*gamma.conjugate()*float(np.sum(abs(B)**2*energy));energy_error=abs(source-quadrature)/max(abs(source),abs(quadrature),1e-300)
 require(modalpower<=GATES['complex_power_relative']and energy_error<=GATES['complex_power_relative'],'Signed discrete boundary/modal/independent depth-energy identity')
 constant=_constant_contract(np,basis,bottom,gamma);Eerror=math.sqrt(sum(errors[k]['absolute_spatial_peak_RMS_L2']**2 for k in('Ex','Ey','Ez')))
 arrays=dict(x_edges_m=basis['edges'],dx_m=dx,mass_m2=mass,z_m=z,z_weights_m=zw,phi_top_peak_V=top,weighted_modal_coeff_peak_V_m=B,qtop_peak_A_m2=qtop,qtop_reference_peak_A_m2=qref)
 for key in fields:arrays[key+'_numerical']=fields[key];arrays[key+'_physical_reference_cell_average']=refs[key]
 metadata=dict(case_id='N%d-%s'%(n,bottom),n=n,bottom=bottom,XY_cells=n*n,physical_depth_samples=len(z),physical_evaluation_samples=n*n*len(z),basis_contracts=basisproof,constant_full_contact_contract=constant,
  weighted_parseval_relative=parseval,uniform_area_DtN_h2_ABI_relative=uniform_abi,source_complex_power_W=pair(source),modal_complex_power_W=pair(modal),independent_depth_quadrature_complex_power_W=pair(quadrature),boundary_to_modal_power_relative=modalpower,boundary_to_quadrature_power_relative=energy_error,
  errors=errors,absolute_vector_E_spatial_peak_RMS_error_V_m=Eerror,absolute_vector_E_temporal_RMS_error_V_m=Eerror/math.sqrt(2),derived_vector_J_spatial_peak_RMS_error_A_m2=abs(gamma)*Eerror,derived_vector_J_temporal_RMS_error_A_m2=abs(gamma)*Eerror/math.sqrt(2),J_error_is_gamma_times_E_not_independent=True,
  interpretation='Physical cell-average Fourier comparison; nonuniform discrete modes are NOT continuum Fourier eigenvectors. Ex/Ey reconstruction error and analytic-modal Ez are separate.',wall_seconds=time.monotonic()-start,new_actual_phantom_PDE=0,new_actual_four_pad_CEM_RHS=0,candidate_adopted=False)
 return dict(metadata=native(metadata),arrays=arrays)

def _reviews(results):
 finest=[];orders=[]
 for bottom in PLAN['bottoms']:
  last=next(r for r in results if r['n']==64 and r['bottom']==bottom)
  for metric in('phi','qtop','Ex','Ey','Ez'):
   key='finest_relative_'+metric;value=last['errors'][metric]['relative_L2'];finest.append(dict(bottom=bottom,metric=metric,value=value,limit=GATES[key],passed=value<=GATES[key]))
   for oldn,newn in((16,32),(32,64)):
    a=next(r for r in results if r['n']==oldn and r['bottom']==bottom)['errors'][metric]['absolute_spatial_peak_RMS_L2'];b=next(r for r in results if r['n']==newn and r['bottom']==bottom)['errors'][metric]['absolute_spatial_peak_RMS_L2'];defined=a>FLOORS[metric]and b>FLOORS[metric];order=math.log(a/b)/math.log(newn/oldn)if defined else None
    orders.append(dict(bottom=bottom,metric=metric,coarse=oldn,fine=newn,coarse_absolute_spatial_peak_RMS_error=a,fine_absolute_spatial_peak_RMS_error=b,observed_order=order,minimum=1.,status='evaluated'if defined else'below_predeclared_error_floor_inconclusive',passed=order>=1. if defined else None,
     scope='Engineering screening hypothesis, not guaranteed order on abrupt TPFA relocation; no curve fit or threshold relaxation'))
 return dict(finest_error_flags=finest,observed_order_flags=orders,all_finest_flags_pass=all(r['passed']for r in finest),all_order_flags_pass=all(r['passed']is True for r in orders),criteria_changed=False)

def build(spec,guard,deadline_monotonic=None,output_dir=None):
 require(spec==make_spec()and callable(guard),'Immutable weighted MMS specification');check(guard,deadline_monotonic);out=Path(output_dir);require(out.is_absolute()and out.parent==Path('/dev/shm')and out.name.startswith('task1-weighted-dtn-mms-')and out.is_dir()and not out.is_symlink(),'Owner-created unique synthetic output')
 import numpy as np
 total=2*sum(n*n*5 for n in PLAN['grids']);require(total<=PLAN['maximum_physical_samples'],'All six registered physical sample counts below800000');method_sha=file_sha(Path(__file__).resolve());spec_sha=sha(encoded(spec));casesdir=out/'cases';progress=out/'progress';casesdir.mkdir(exist_ok=True);progress.mkdir(exist_ok=True);completed=[];results=[];eigensystems=0
 for n in PLAN['grids']:
  basis=None;basisproof=None
  for bottom in PLAN['bottoms']:
   check(guard,deadline_monotonic);require(file_sha(Path(__file__).resolve())==method_sha,'Frozen weighted MMS source');cid='N%d-%s'%(n,bottom);mp=casesdir/(cid+'.json');ap=casesdir/(cid+'.npz')
   if mp.exists():
    meta=json.loads(mp.read_bytes());require(meta['spec_sha256']==spec_sha and meta['method_sha256']==method_sha and meta['arrays_SHA256']==file_sha(ap),'Same-spec completed case resume')
   else:
    require(not ap.exists(),'Preserve partial arrays; root recovery/newrun required')
    if basis is None:basis,basisproof=_basis(np,n);eigensystems+=1
    result=_case(np,n,bottom,basis,basisproof,spec,guard,deadline_monotonic)
    with ap.open('xb')as stream:np.savez_compressed(stream,**result['arrays'])
    meta=result['metadata'];meta.update(spec_sha256=spec_sha,method_sha256=method_sha,arrays_SHA256=file_sha(ap));new_json(mp,meta)
   results.append(meta);record=dict(case_id=cid,metadata_SHA256=file_sha(mp),arrays_SHA256=file_sha(ap),complete=True);marker=progress/(cid+'.json')
   if marker.exists():require(json.loads(marker.read_bytes())==record,'Immutable completed checkpoint')
   else:new_json(marker,record)
   completed.append(record);index=dict(schema='task1-weighted-DtN-MMS-resume-v1',completed=list(completed),remaining_cases=6-len(completed),no_completed_case_recomputed=True,spec_sha256=spec_sha,method_sha256=method_sha)
   snapshot=out/('resume-index-%02d.json'%len(completed))
   if not snapshot.exists():new_json(snapshot,index)
   temp=out/('resume-index-%d.new'%time.time_ns());new_json(temp,index);temp.replace(out/'resume-index.json')
 review=_reviews(results);check(guard,deadline_monotonic)
 return dict(summary=native(dict(schema='task1-weighted-DtN-Fourier-MMS-result-v1',status='six_weighted_MMS_conditions_calculated_unadopted',spec=spec,cases=results,predeclared_review=review,
  completed_MMS_conditions=6,new_1D_eigensystems_this_invocation=eigensystems,all_physical_evaluation_samples=total,new_actual_circle_eigen_runs=0,new_actual_phantom_PDE=0,new_actual_four_pad_CEM_RHS=0,
  original_four_pad_failures_preserved=True,actual_geometry_material_circuit_unchanged=True,actual_four_pad_admission=False,candidate_adopted=False,resume_index_SHA256=file_sha(out/'resume-index.json'))),arrays={})
