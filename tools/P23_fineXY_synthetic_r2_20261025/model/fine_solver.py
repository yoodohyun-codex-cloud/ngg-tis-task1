"""Generic unchanged two-output grounded-return CEM solve; injected numerics.

No IO/scientific import or solver work at import. Peak+jwt, physical topArea/z,
other ideal output0V through50ohm, pads2/3commonGND, exact modal layer powers.
"""
import time
GMRES=dict(rtol=1e-12,atol=0.,restart=80,max_outer_iterations=40)
LIMITS=dict(relative_algebraic_residual=2e-7,relative_loaded_current_residual=2e-7,relative_all_pad_KCL=2e-6,relative_output_pad_current=2e-6,relative_complex_power_error=2e-7)
def require(ok,message):
 if not ok:raise ValueError(message)
def pair(v):return dict(real=float(v.real),imaginary=float(v.imag))
def check(guard,deadline):
 guard()
 if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite raw CEM frame deadline')
def transform(np,Q,values,transpose=False):
 matrix=Q.T if transpose else Q
 return matrix@values.real+1j*(matrix@values.imag)
def screen_errors(errors):
 rows={key:dict(value=float(errors[key]),limit=limit,passed=bool(errors[key]<=limit))for key,limit in LIMITS.items()}
 return dict(passed=all(v['passed']for v in rows.values()),metrics=rows)
def solve(np,Q,profile,pads,cells,areas,za,output,h,guard,deadline,cached=None):
 from scipy.sparse.linalg import LinearOperator,gmres
 n=Q.shape[0];R=50.;g=areas/za;metalg=np.asarray([g[pads==p].sum()for p in range(2)]);gsum=np.bincount(cells,weights=g.real,minlength=n)+1j*np.bincount(cells,weights=g.imag,minlength=n);diagonal=np.r_[profile['diagonal']+gsum,metalg+1/R];require(np.all(abs(diagonal)>1e-30),'Nonzero diagonal CEM preconditioner')
 def tissue(phi):return h*h*transform(np,Q,profile['Y']*transform(np,Q,phi,True))
 def split(x):
  phi=x[:n];metal=x[n:];vp=np.zeros(len(pads),np.complex128)
  for p in range(2):vp[pads==p]=metal[p]
  q=g*(phi[cells]-vp);qsum=np.zeros(n,np.complex128);np.add.at(qsum,cells,q);qpad=np.asarray([q[pads==p].sum()for p in range(4)]);return phi,metal,vp,q,qsum,qpad
 calls=0
 def action(x):
  nonlocal calls
  calls+=1;check(guard,deadline);phi,metal,vp,q,qsum,qpad=split(x);return np.r_[tissue(phi)+qsum,metal/R-qpad[:2]]
 rhs=np.zeros(n+2,np.complex128);rhs[n+output]=.5/R;history=[];start=time.monotonic()
 if cached is None:
  A=LinearOperator((n+2,n+2),matvec=action,dtype=np.complex128);M=LinearOperator((n+2,n+2),matvec=lambda x:x/diagonal,dtype=np.complex128)
  def callback(v):history.append(float(v));check(guard,deadline)
  x,info=gmres(A,rhs,M=M,rtol=GMRES['rtol'],atol=GMRES['atol'],restart=GMRES['restart'],maxiter=GMRES['max_outer_iterations'],callback=callback,callback_type='pr_norm')
 else:x=np.r_[cached['phi_surface'],cached['metal']];info=0
 phi,metal,vp,q,qsum,qpad=split(x);ideal=np.zeros(2,np.complex128);ideal[output]=.5;Isource=(ideal-metal)/R;tissue_current=tissue(phi);coeff=transform(np,Q,phi,True)
 Slayer=.5*h*h*np.sum(abs(coeff[:,None])**2*(profile['unitV'][:,:-1]*profile['unitJ'][:,:-1].conj()-profile['unitV'][:,1:]*profile['unitJ'][:,1:].conj()),axis=0)
 Ssource=.5*np.sum(ideal*Isource.conj());Scontact=.5*np.sum((vp-phi[cells])*(-q).conj());Presistor=.5*R*float(np.sum(abs(Isource)**2));Ssum=Slayer.sum()+Scontact+Presistor;scale=max(float(np.linalg.norm(tissue_current)),float(np.linalg.norm(qsum)),float(np.linalg.norm(Isource)),1e-12)
 errors=dict(relative_algebraic_residual=float(np.linalg.norm(np.r_[tissue_current+qsum,metal/R-qpad[:2]]-rhs)/np.linalg.norm(rhs)),relative_loaded_current_residual=float(np.linalg.norm(np.r_[tissue_current+qsum,Isource+qpad[:2]])/scale),relative_all_pad_KCL=float(abs(qpad.sum())/max(float(np.sum(abs(qpad))),1e-12)),relative_output_pad_current=float(np.max(abs(Isource+qpad[:2])/np.maximum(np.maximum(abs(Isource),abs(qpad[:2])),1e-12))),relative_complex_power_error=float(abs(Ssource-Ssum)/max(abs(Ssource),abs(Ssum),1e-12)))
 gates=screen_errors(errors);powers=[complex(v)for v in Slayer]+[complex(Scontact),complex(Presistor)];allowance=1e-14+1e-12*max(abs(v)for v in powers);passive=all(v.real>=-allowance for v in powers)
 proof=dict(driven_output=output,source_peak_V=.5,source_high_impedance_Vpp=1.,reused_published_baseline_surface=cached is not None,actual_new_RHS=int(cached is None),gmres_info=int(info),iterations=len(history),history=history,wall_seconds=time.monotonic()-start,matvec_count=calls,physical_gates=gates,passivity_passed=bool(passive),passed=bool(info==0 and gates['passed']and passive),source_complex_power_W=pair(Ssource),layer_complex_power_W=[pair(v)for v in Slayer],contact_complex_power_W=pair(Scontact),source_resistor_power_W=Presistor,source_current_peak_A=[pair(v)for v in Isource],two_basis_reciprocity='not_run_one_driven_RHS_at_each_frequency; prior baseline two-basis reciprocity preserved')
 return dict(phi_surface=phi,metal=metal,source_current=Isource,coeff=coeff,contact_current=-q,contact_J=-q/areas,contact_drop=vp-phi[cells],layer_power=Slayer,source_power=Ssource,contact_power=Scontact,resistor_power=Presistor,proof=proof)

