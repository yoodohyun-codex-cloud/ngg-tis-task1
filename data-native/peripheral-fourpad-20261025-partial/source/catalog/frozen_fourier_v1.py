"""Guard-called manufactured modal benchmark; never a real phantom/CEM solve.

No IO or array/data evaluation occurs on import. All lengths in metres inside
math functions; complex peak phasors use +j*omega*t and Jz=-gamma*dV/dz.
"""
from __future__ import annotations
import bisect,cmath,hashlib,json,math,time
from pathlib import Path

EPS0=8.8541878128e-12
COARSE=Path('/workspace/task1-experiment-2000-2010-20261025-run')
FINE=Path('/workspace/task1-xy100-2000-20261025-run-r2')
COARSE_CASE='baseline-square15-human-sine2000-2010-xy80'
MATERIAL_SHA='cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469'
COARSE_CONFIG_SHA='61830d8b2abf39a2458666df2b26a0bfb1e585873f3e3002f4e29ba1ab76af13'
LAYERS=('sc','dermis','fat','muscle')
THICKNESS=(.0001,.005,.005,.015)
MODES=(1,2,4,8,16)
QA_LIMIT=.05
ABS_TOL=1e-10
REL_TOL=1e-10


def require(ok,message):
 if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def finite(z):return math.isfinite(complex(z).real)and math.isfinite(complex(z).imag)
def pair(z):return dict(real=float(complex(z).real),imaginary=float(complex(z).imag))
def _close(a,b):return abs(a-b)<=ABS_TOL+REL_TOL*abs(b)
def _properties(raw):return {k.strip():v.strip()for line in raw.decode().splitlines()if '='in line and not line.lstrip().startswith(('#','!'))for k,v in[line.split('=',1)]}


def required_inputs():
 """Only owner-invoked small actual metadata/config/receipt reads; no arrays."""
 paths=[COARSE/'configs'/(COARSE_CASE+'.properties'),COARSE/'material-input.json',COARSE/'postprocess/summary.json',COARSE/'postprocess/artifact-sha256.json',FINE/'postprocess/summary.json',FINE/'postprocess/artifact-sha256.json']
 out={}
 for path in paths:
  require(path.is_file()and not path.is_symlink()and path.stat().st_size<8*1024**2,'Actual completed metadata required: '+str(path));raw=path.read_bytes();out[str(path)]=digest(raw)
 require(out[str(paths[0])]==COARSE_CONFIG_SHA and out[str(paths[1])]==MATERIAL_SHA,'Exact previously verified 2000 Hz inputs')
 for run in(COARSE,FINE):
  artifacts=json.loads((run/'postprocess/artifact-sha256.json').read_bytes())
  require(out[str(run/'postprocess/summary.json')]==artifacts['summary.json']['SHA256'],'Actual completed summary identity')
 return out


def make_spec(material_receipt_bytes,config_bytes,optional_sc4=False):
 require(digest(material_receipt_bytes)==MATERIAL_SHA and digest(config_bytes)==COARSE_CONFIG_SHA,'Reuse exact verified inputs; no material reevaluation')
 cfg=_properties(config_bytes);rows=[]
 for n in LAYERS:
  sigma=float(cfg[n+'.sigma.2000']);epsilon=float(cfg[n+'.epsilon_r.2000']);gamma=complex(sigma,2*math.pi*2000*EPS0*epsilon)
  require(sigma>0 and epsilon>0 and finite(gamma),'Finite positive actual scalar admittivity')
  rows.append(dict(layer=n,sigma_S_m=sigma,epsilon_r=epsilon,gamma_S_m=pair(gamma)))
 grids=[dict(id='A',h_mm=.625,sc_cells=2,bulk_counts=[14,14,40]),dict(id='B',h_mm=.5,sc_cells=2,bulk_counts=[14,14,40]),dict(id='C',h_mm=.5,sc_cells=2,bulk_counts=[18,18,56])]
 if optional_sc4:grids.append(dict(id='D',h_mm=.5,sc_cells=4,bulk_counts=[18,18,56]))
 return dict(schema='task1-manufactured-fourier-spec-v1',frequency_Hz=2000,period_m=.05,thickness_m=list(THICKNESS),material_rows=rows,material_receipt_sha256=MATERIAL_SHA,config_sha256=COARSE_CONFIG_SHA,modes=list(MODES),grids=grids,
  boundary='top Dirichlet cos(k*x) Vpeak; bottom Jz0; x periodic; y independent',independent_normal_current_QA_limit=QA_LIMIT,analytic_absolute_tolerance=ABS_TOL,analytic_relative_tolerance=REL_TOL,
  scope='Manufactured planar operator/diagnostic test only; not cylinder, CEM, electrodes,50ohm hardware, real phantom, TIS, candidate, activation or safety validation')


def transfer_state(state,k,gamma,d):
 """Downward signed-distance transfer; upward uses negative d."""
 v,j=map(complex,state);gamma=complex(gamma);require(k>=0 and math.isfinite(k)and finite(gamma)and abs(gamma)>0 and math.isfinite(d),'Finite modal state and material')
 if k==0:out=(v-d*j/gamma,j)
 else:
  c=math.cosh(k*d);s=math.sinh(k*d);out=(c*v-s*j/(gamma*k),-gamma*k*s*v+c*j)
 require(all(finite(z)for z in out),'Finite transfer result');return out


def exact_profile(k,gamma,thicknesses,zs):
 require(len(gamma)==len(thicknesses)>0 and all(t>0 for t in thicknesses),'Positive layers')
 faces=[0.]
 for d in thicknesses:faces.append(faces[-1]+d)
 states=[None]*(len(gamma)+1);states[-1]=(1.+0j,0j)
 for i in range(len(gamma)-1,-1,-1):states[i]=transfer_state(states[i+1],k,gamma[i],-thicknesses[i])
 normalizer=states[0][0];require(finite(normalizer)and abs(normalizer)>1e-200,'Nonzero top normalization')
 states=[(v/normalizer,j/normalizer)for v,j in states];values=[];currents=[]
 for z in zs:
  require(-1e-15<=z<=faces[-1]+1e-15,'Requested depth inside manufactured domain')
  i=min(max(bisect.bisect_right(faces,z)-1,0),len(gamma)-1)
  v,j=transfer_state(states[i+1],k,gamma[i],z-faces[i+1]);values.append(v);currents.append(j)
 return values,currents,states


def admittance_profile(k,gamma,thicknesses):
 require(k>0,'Positive k for independent admittance recurrence');y=0j;upper=[]
 for g,d in reversed(list(zip(gamma,thicknesses))):
  t=math.tanh(k*d);den=1+y*t/(g*k);require(finite(den)and abs(den)>1e-200,'Finite nonzero admittance denominator');y=(y+g*k*t)/den;upper.append(y)
 return y


def make_grid(h_mm,sc_cells,bulk_counts):
 counts=[sc_cells]+list(bulk_counts);require(len(counts)==4 and all(isinstance(n,int)and n>=2 for n in counts),'Four layers with >=2 cells')
 faces=[0.];layers=[]
 for material,(d,n)in enumerate(zip(THICKNESS,counts)):
  top=faces[-1]
  for j in range(n):faces.append(top+d*(j+1)/n);layers.append(material)
 zs=[(a+b)/2 for a,b in zip(faces[:-1],faces[1:])]
 require(h_mm>0 and abs(round(50/h_mm)*h_mm-50)<1e-10,'Periodic x grid tiles50mm');return faces,layers,zs


def fvm_system(kfd,gamma,faces,layerids):
 n=len(layerids);require(n>1 and len(faces)==n+1,'Complete vertical mesh');dz=[b-a for a,b in zip(faces[:-1],faces[1:])];g=[gamma[i]for i in layerids]
 require(all(d>0 for d in dz),'Positive dz');face=[1/(dz[i]/(2*g[i])+dz[i+1]/(2*g[i+1]))for i in range(n-1)]
 lower=[0j]+[-v for v in face];upper=[-v for v in face]+[0j];diag=[g[i]*dz[i]*kfd*kfd for i in range(n)]
 for i,v in enumerate(face):diag[i]+=v;diag[i+1]+=v
 top=2*g[0]/dz[0];diag[0]+=top;rhs=[top]+[0j]*(n-1)
 return lower,diag,upper,rhs


def solve_fvm(kfd,gamma,faces,layerids):
 lower,diag,upper,rhs=fvm_system(kfd,gamma,faces,layerids);d=diag[:];b=rhs[:]
 for i in range(1,len(d)):
  require(finite(d[i-1])and abs(d[i-1])>1e-200,'Finite Thomas pivot');q=lower[i]/d[i-1];d[i]-=q*upper[i-1];b[i]-=q*b[i-1]
 require(abs(d[-1])>1e-200,'Nonzero final Thomas pivot');out=[0j]*len(d);out[-1]=b[-1]/d[-1]
 for i in range(len(d)-2,-1,-1):out[i]=(b[i]-upper[i]*out[i+1])/d[i]
 require(all(finite(v)for v in out),'Finite complex FVM solution');return out


def _derivative(zs,values,at):
 scale=max(abs(z-at)for z in zs);require(len(zs)in(2,3)and scale>0,'Two or three one-sided nodes');u=[(z-at)/scale for z in zs];weights=[];vweights=[]
 for j in range(len(u)):
  den=math.prod(u[j]-u[l]for l in range(len(u))if l!=j)
  vweights.append(math.prod(-u[l]for l in range(len(u))if l!=j)/den)
  weights.append(sum(math.prod(-u[l]for l in range(len(u))if l not in(j,a))for a in range(len(u))if a!=j)/den/scale)
 return sum(w*v for w,v in zip(weights,values)),sum(w*v for w,v in zip(vweights,values))


def fit_interfaces(values,zs,layers,gamma,thicknesses,interface_states,points,cos_rms):
 rows=[];physical=0.
 for boundary in range(1,len(gamma)):
  physical+=thicknesses[boundary-1];up=[i for i,l in enumerate(layers)if l==boundary-1][-points:];lo=[i for i,l in enumerate(layers)if l==boundary][:points]
  du,vu=_derivative([zs[i]for i in up],[values[i]for i in up],physical);dl,vl=_derivative([zs[i]for i in lo],[values[i]for i in lo],physical)
  ju=-gamma[boundary-1]*du;jl=-gamma[boundary]*dl;truth_v,truth_j=interface_states[boundary]
  numerator=abs(ju-jl)*cos_rms;den=max(abs(ju)*cos_rms,abs(jl)*cos_rms,1e-12);true_den=max(abs(truth_j)*cos_rms,1e-12)
  rows.append(dict(interface_depth_mm=physical*1000,upper_points=len(up),lower_points=len(lo),upper_J=pair(ju),lower_J=pair(jl),exact_J=pair(truth_j),exact_V=pair(truth_v),
   jump_spatial_RMS_A_m2=numerator,denominator_A_m2=den,denominator_floor_A_m2=1e-12,denominator_floor_used=den==1e-12,normalized_L2=numerator/den,numerical_5pct_passed=numerator/den<=QA_LIMIT,
   upper_error_spatial_RMS_A_m2=abs(ju-truth_j)*cos_rms,lower_error_spatial_RMS_A_m2=abs(jl-truth_j)*cos_rms,upper_error_relative=abs(ju-truth_j)*cos_rms/true_den,lower_error_relative=abs(jl-truth_j)*cos_rms/true_den,
   upper_potential_error_V=abs(vu-truth_v),lower_potential_error_V=abs(vl-truth_v),exact_J_denominator_floor_used=true_den==1e-12))
 return rows


def _profile_error(actual,reference,dz,zs):
 volume=sum(dz);rms=math.sqrt(sum(w*abs(a-b)**2 for a,b,w in zip(actual,reference,dz))/volume);den=math.sqrt(sum(w*abs(b)**2 for b,w in zip(reference,dz))/volume);i=max(range(len(dz)),key=lambda j:abs(actual[j]-reference[j]))
 return dict(absolute_volume_weighted_RMS_V=rms,reference_volume_weighted_RMS_V=den,relative_L2=rms/max(den,1e-12),maximum_absolute_error_V=abs(actual[i]-reference[i]),maximum_error_depth_mm=zs[i]*1000,denominator_floor_V=1e-12)


def fvm_diagnostics(values,kfd,gamma,faces,layers,truth):
 lo,di,up,rhs=fvm_system(kfd,gamma,faces,layers);res=[]
 for i,v in enumerate(values):res.append(di[i]*v+(lo[i]*values[i-1]if i else 0)+(up[i]*values[i+1]if i+1<len(values)else 0)-rhs[i])
 residual=max(abs(v)for v in res)/max(max(abs(v)for v in rhs),1e-30)
 dz=[b-a for a,b in zip(faces[:-1],faces[1:])];top=2*gamma[layers[0]]/dz[0];jtop=top*(1-values[0]);source=.5*jtop.conjugate();loss=.5*top.conjugate()*abs(1-values[0])**2;interface=[]
 for i in range(len(values)-1):
  g=1/(dz[i]/(2*gamma[layers[i]])+dz[i+1]/(2*gamma[layers[i+1]]));flux=g*(values[i]-values[i+1]);loss+=.5*g.conjugate()*abs(values[i]-values[i+1])**2
  if layers[i]!=layers[i+1]:
   actual=truth[layers[i+1]][1];interface.append(dict(depth_mm=faces[i+1]*1000,shared_FVM_J=pair(flux),exact_J=pair(actual),absolute_error_A_m2=abs(flux-actual),relative_error=abs(flux-actual)/max(abs(actual),1e-12)))
 for v,w,l in zip(values,dz,layers):loss+=.5*gamma[l].conjugate()*w*kfd*kfd*abs(v)**2
 return dict(relative_algebraic_residual=residual,shared_interface_flux_errors=interface,source_complex_power_amplitude_per_area=pair(source),discrete_complex_energy_sum=pair(loss),complex_energy_relative_error=abs(source-loss)/max(abs(source),1e-12),
  scope='Amplitude-level peak/2 temporal complex energy identity; multiply by mean(cos²) for spatial average. Shared flux continuity is algebraic, not independent accuracy.')


def analytic_contracts(guard=lambda:None):
 guard();gamma=[.003+.02j,.2+.04j,.04+.005j,.3+.07j];zs=[.00002,.00007,.002,.008,.014,.025]
 v,j,states=exact_profile(0,gamma,THICKNESS,zs);require(all(_close(a,1)for a in v)and all(_close(a,0)for a in j),'Insulated zero mode')
 current=1/sum(d/g for d,g in zip(THICKNESS,gamma));state=(1.+0j,current)
 for g,d in zip(gamma,THICKNESS):state=transfer_state(state,0,g,d)
 require(_close(state[0],0)and _close(state[1],current),'Nonzero-current layered zero-mode slab')
 rows=[];k=2*math.pi/.05;length=sum(THICKNESS);constant=.2+.03j
 v,j,states=exact_profile(k,[constant]*4,THICKNESS,zs)
 for z,a,b in zip(zs,v,j):require(_close(a,math.cosh(k*(length-z))/math.cosh(k*length))and _close(b,constant*k*math.sinh(k*(length-z))/math.cosh(k*length)),'Homogeneous continuum closed form')
 smallv,smallj,_=exact_profile(1e-7,gamma,THICKNESS,zs);require(all(_close(a,1)for a in smallv)and all(_close(a,0)for a in smallj),'Small-k zero-mode continuity')
 for g,d in zip(gamma,THICKNESS):
  s=(.7+.2j,.3-.1j);back=transfer_state(transfer_state(s,k,g,d),k,g,-d);require(all(_close(a,b)for a,b in zip(back,s)),'Transfer inverse sign check')
 # Independent discrete homogeneous recurrence, uniform mesh and half-cell BCs.
 n=16;dz=length/n;faces=[i*dz for i in range(n+1)];layers=[0]*n;kfd=2*math.sin(k*.0005/2)/.0005;theta=math.acosh(1+(kfd*dz)**2/2);values=solve_fvm(kfd,[constant],faces,layers)
 exact=[math.cosh(theta*(n-.5-i))/(math.cosh(theta*n)*math.cosh(theta/2))for i in range(n)]
 require(all(_close(a,b)for a,b in zip(values,exact)),'Homogeneous discrete recurrence')
 zero=solve_fvm(0,[constant],faces,layers);require(all(_close(a,1)for a in zero),'FVM zero mode and insulated bottom')
 _,_,truth=exact_profile(kfd,[constant],[length],[]);diag=fvm_diagnostics(values,kfd,[constant],faces,layers,truth)
 require(diag['relative_algebraic_residual']<=REL_TOL and diag['complex_energy_relative_error']<=REL_TOL,'Discrete residual and complex energy identity')
 # Independent top admittance versus exact bottom-up transfer.
 _,_,states=exact_profile(k,gamma,THICKNESS,[]);y=admittance_profile(k,gamma,THICKNESS);require(_close(y,states[0][1]),'Independent admittance recurrence')
 guard();return dict(passed=True,status='passed',absolute_tolerance=ABS_TOL,relative_tolerance=REL_TOL,checks=['zero mode insulated','nonzero-current layered zero-mode slab','homogeneous continuum','small-k limit','transfer inverse','homogeneous discrete recurrence','FVM zero mode','complex energy identity','independent admittance recurrence'],new_real_phantom_PDE=0,native_arrays_read=False)


def build(spec,guard,deadline_monotonic=None):
 require(callable(guard),'Explicit sole-owner guard');guard();require(spec['schema']=='task1-manufactured-fourier-spec-v1'and spec['material_receipt_sha256']==MATERIAL_SHA and spec['config_sha256']==COARSE_CONFIG_SHA,'Pinned manufactured specification')
 require(spec['modes']==list(MODES)and spec['thickness_m']==list(THICKNESS)and spec['period_m']==.05 and spec['independent_normal_current_QA_limit']==QA_LIMIT,'No post-result threshold/domain changes')
 gamma=[complex(r['gamma_S_m']['real'],r['gamma_S_m']['imaginary'])for r in spec['material_rows']];require(len(gamma)==4 and all(finite(g)and g.real>0 and g.imag>0 for g in gamma),'Four verified complex gamma values')
 for i,row in enumerate(spec['material_rows']):require(row['layer']==LAYERS[i]and _close(gamma[i],complex(row['sigma_S_m'],2*math.pi*2000*EPS0*row['epsilon_r'])),'Declared actual sigma/epsilon and gamma arithmetic agree')
 expected_grids=[dict(id='A',h_mm=.625,sc_cells=2,bulk_counts=[14,14,40]),dict(id='B',h_mm=.5,sc_cells=2,bulk_counts=[14,14,40]),dict(id='C',h_mm=.5,sc_cells=2,bulk_counts=[18,18,56])]
 require(spec['grids']==expected_grids or spec['grids']==expected_grids+[dict(id='D',h_mm=.5,sc_cells=4,bulk_counts=[18,18,56])],'Only predeclared manufactured grid tuples')
 contracts=analytic_contracts(guard);rows=[];arrays={}
 for grid in spec['grids']:
  for mode in MODES:
   guard();require(deadline_monotonic is None or time.monotonic()<deadline_monotonic,'Manufactured finite stage deadline')
   faces,layers,zs=make_grid(grid['h_mm'],grid['sc_cells'],grid['bulk_counts']);dz=[b-a for a,b in zip(faces[:-1],faces[1:])];h=grid['h_mm']*.001;k=2*math.pi*mode/.05;kfd=2*math.sin(k*h/2)/h;nx=round(.05/h)
   require(mode<nx/2,'Mode below periodic Nyquist');x=[-.025+(i+.5)*h for i in range(nx)];cos_rms=math.sqrt(sum(math.cos(k*xx)**2 for xx in x)/nx)
   v,j,state=exact_profile(k,gamma,THICKNESS,zs);vfd,jfd,statefd=exact_profile(kfd,gamma,THICKNESS,zs);fv=solve_fvm(kfd,gamma,faces,layers);key=grid['id']+'_m'+str(mode)
   fits={}
   for name,values,truth in(('exact_continuum_k',v,state),('exact_continuum_kfd',vfd,statefd),('FVM_reference_kfd',fv,statefd),('FVM_reference_physical_k',fv,state)):
    fits[name]=dict(common_two_point=fit_interfaces(values,zs,layers,gamma,THICKNESS,truth,2,cos_rms),up_to_three_point=fit_interfaces(values,zs,layers,gamma,THICKNESS,truth,3,cos_rms))
   rows.append(dict(case_id=key,mode=mode,mesh=dict(grid),k_per_m=k,kfd_per_m=kfd,periodic_x_cells=nx,vertical_cells=len(zs),spatial_mean_cos_squared=cos_rms*cos_rms,
    lateral_symbol_only_profile_error=_profile_error(vfd,v,dz,zs),vertical_FVM_vs_kfd_error=_profile_error(fv,vfd,dz,zs),combined_FVM_vs_physical_k_error=_profile_error(fv,v,dz,zs),
    FVM_checks=fvm_diagnostics(fv,kfd,gamma,faces,layers,statefd),independent_fit_diagnostics=fits,exact_interface_states=[dict(depth_mm=sum(THICKNESS[:i])*1000,V=pair(a),J=pair(b))for i,(a,b)in enumerate(state)]))
   arrays[key+'_z_mm']=[z*1000 for z in zs];arrays[key+'_layer']=layers
   for name,values in(('exact_k',v),('exact_kfd',vfd),('FVM_kfd',fv)):
    arrays[key+'_'+name+'_real_V']=[float(a.real)for a in values];arrays[key+'_'+name+'_imaginary_V']=[float(a.imag)for a in values]
 guard();summary=dict(schema='task1-manufactured-fourier-benchmark-v1',status='calculated_manufactured_diagnostic_only',spec=spec,analytic_contracts=contracts,rows=rows,
  metric_scope='Exact sampled fit bias, lateral modified-wavenumber error, vertical FVM error, combined error, and shared-flux/energy algebra are distinct.',
  independent_QA=dict(limit=QA_LIMIT,denominator='max(spatial RMS upper,spatial RMS lower,1e-12 A/m²)',absolute_side_errors_retained=True,failed_flags_retained=True,criteria_changed=False),
  real_model_holds=dict(full_SC_XY_bulk_edge_contact_convergence=False,material_anatomic_or_experimental_calibration=False,candidate_adopted=False,real_PDE_interface_failures_not_cleared=True),
  scope='Manufactured periodic planar top-Dirichlet operator test only. No real cylinder, CEM, electrodes,50ohm circuit, phantom/hardware experiment,TIS,activation or safety validation.',new_real_phantom_PDE=0,native_field_arrays_read=False)
 return dict(summary=summary,arrays=arrays)
