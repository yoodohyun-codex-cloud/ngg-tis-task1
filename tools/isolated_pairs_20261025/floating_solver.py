"""Floating voltage-source pairs. Peak phasors, one 50-ohm resistor per pair.
Only a gauge term constrains mean metal voltage; it supplies zero net current.
No import-time IO or numerical work.
"""
def solve(np,tissue,tdiag,pads,cells,areas,za,pairs,voltages,guard,rtol=1e-12,gauge=0.):
 from scipy.sparse.linalg import LinearOperator,gmres
 import time
 n=len(tdiag); m=int(pads.max())+1; R=50.; gauge_g=.02
 B=np.zeros((m,len(pairs)))
 for k,(a,b) in enumerate(pairs): B[a,k]=1;B[b,k]=-1
 assert np.all(np.sum(abs(B),axis=1)==1)
 g=areas/za; gp=np.array([g[pads==p].sum() for p in range(m)])
 gsum=np.zeros(n,complex);np.add.at(gsum,cells,g)
 diag=np.r_[tdiag+gsum,gp+np.diag(B@B.T)/R+gauge_g/m]
 def split(x):
  phi=x[:n]; metal=x[n:]; q=g*(phi[cells]-metal[pads])
  qs=np.zeros(n,complex);np.add.at(qs,cells,q)
  qp=np.zeros(m,complex);np.add.at(qp,pads,q)
  return phi,metal,q,qs,qp
 calls=0
 def action(x):
  nonlocal calls
  calls+=1;guard();phi,metal,q,qs,qp=split(x)
  return np.r_[tissue(phi)+qs,-qp+B@(B.T@metal)/R+gauge_g*metal.mean()]
 rhs=np.r_[np.zeros(n,complex),B@np.asarray(voltages)/R+gauge_g*gauge]
 hist=[];start=time.monotonic()
 def cb(v):hist.append(float(v));guard()
 A=LinearOperator((n+m,n+m),matvec=action,dtype=complex)
 M=LinearOperator(A.shape,matvec=lambda x:x/diag,dtype=complex)
 x,info=gmres(A,rhs,M=M,rtol=rtol,atol=0.,restart=80,maxiter=40,callback=cb,callback_type='pr_norm')
 phi,metal,q,qs,qp=split(x);I=(np.asarray(voltages)-B.T@metal)/R
 Sp=.5*np.sum(np.asarray(voltages)*I.conj());Sc=.5*np.sum((metal[pads]-phi[cells])*(-q).conj())
 Pr=.5*R*float(np.sum(abs(I)**2));St=.5*np.vdot(tissue(phi),phi)
 scale=max(float(np.linalg.norm(I)),float(np.linalg.norm(qp)),1e-12)
 errors=dict(algebraic=float(np.linalg.norm(action(x)-rhs)/max(np.linalg.norm(rhs),1e-12)),
  electrode_KCL=float(np.linalg.norm(-qp-B@I)/scale),
  pair_KCL=float(max(abs(qp[a]+qp[b]) for a,b in pairs)/scale),
  total_KCL=float(abs(qp.sum())/scale),
  source_power=float(abs(Sp-St-Sc-Pr)/max(abs(Sp),abs(St+Sc+Pr),1e-12)),
  gauge=float(abs(metal.mean()-gauge)))
 passed=info==0 and max(errors.values())<2e-7 and min(St.real,Sc.real,Pr)>-1e-14
 proof=dict(passed=bool(passed),gmres_info=int(info),iterations=len(hist),history=hist,matvec_count=calls,wall_seconds=time.monotonic()-start,errors=errors,
  pairs=pairs,source_resistance_ohm_per_pair=R,source_Vpp_open_circuit_each=1.,inactive_source='zero differential volts through 50 ohm; floating common mode',gauge='mean metal voltage only; no physical ground')
 return dict(phi_surface=phi,metal=metal,contact_current=-q,contact_J=-q/areas,contact_drop=metal[pads]-phi[cells],source_current=I,source_power=Sp,contact_power=Sc,resistor_power=Pr,tissue_power=St,proof=proof)

def contracts(np,guard):
 # Independent analytic series two-pad circuit, complex passive load/contact.
 y=1/(300-70j);T=np.array([[y,-y],[-y,y]])
 args=(np,lambda v:T@v,np.diag(T),np.array([0,1]),np.array([0,1]),np.ones(2),20-5j,[(0,1)])
 s=solve(*args,[.5],guard);expected=.5/(50+2*(20-5j)+300-70j)
 assert s['proof']['passed'] and abs(s['source_current'][0]-expected)<1e-13
 shift=solve(*args,[.5],guard,gauge=2.3)
 assert np.max(abs(shift['phi_surface']-s['phi_surface']-2.3))<1e-10
 assert np.max(abs(shift['source_current']-s['source_current']))<1e-12
 # Asymmetric passive four-port network with complex reciprocal admittances.
 T=np.zeros((4,4),complex)
 for a,b,z in [(0,1,120-10j),(0,2,330-20j),(0,3,190-30j),(1,2,250-12j),(1,3,410-50j),(2,3,180-20j)]:
  d=np.zeros(4);d[a]=1;d[b]=-1;T+=np.outer(d,d)/z
 args=(np,lambda v:T@v,np.diag(T),np.arange(4),np.arange(4),np.ones(4),20-5j,[(0,2),(1,3)])
 a=solve(*args,[.5,0],guard);b=solve(*args,[0,.5],guard)
 assert a['proof']['passed'] and b['proof']['passed']
 reciprocity=abs(a['source_current'][1]-b['source_current'][0])/max(abs(a['source_current'][1]),1e-12)
 assert reciprocity<2e-7 and abs(a['source_current'][1])>1e-8
 return dict(passed=True,two_pad_analytic_current_error_A=float(abs(s['source_current'][0]-expected)),gauge_shift_V=2.3,gauge_current_error_A=float(np.max(abs(shift['source_current']-s['source_current']))),reciprocity_relative=float(reciprocity),inactive_induced_current_A=float(abs(a['source_current'][1])),proofs=[s['proof'],a['proof'],b['proof']],scope='Synthetic algebraic circuit validation, not phantom mesh convergence or physiology')

