"""Generic coarse/fine profiles and hybrid fields; root calls injected numerics.

No IO or scientific import on import. Continuous-z Ez is analytic J/gamma;
lateral components use the frozen native half-face estimator, still unvalidated.
"""
import math,time
import frozen_layer_dtn_backend as kernel
import provisional_field
THICKNESS=(.0001,.005,.005,.015)
def require(ok,message):
 if not ok:raise ValueError(message)
def check(guard,deadline):
 guard()
 if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite profile/field deadline')
def transform(np,Q,values,transpose=False):
 matrix=Q.T if transpose else Q
 return matrix@values.real+1j*(matrix@values.imag)

def profiles(np,Q,eigen,gamma,zs,h,guard,deadline):
 n=Q.shape[0]
 Y=np.empty(n,np.complex128);unitV=np.empty((n,5),np.complex128);unitJ=np.empty_like(unitV);factorV=np.empty((n,len(zs)),np.complex128);factorJ=np.empty_like(factorV);faces=[0.]
 for t in THICKNESS:faces.append(faces[-1]+t)
 for k,value in enumerate(eigen):
  if k%256==0:check(guard,deadline)
  wave=math.sqrt(float(value));Y[k]=kernel.modal_admittance(wave,gamma,THICKNESS);unitV[k],unitJ[k]=kernel.stable_profile(wave,gamma,THICKNESS,faces);factorV[k],factorJ[k]=kernel.stable_profile(wave,gamma,THICKNESS,zs)
 require(Y[0]==0j and all(np.isfinite(a).all()for a in(Y,unitV,unitJ,factorV,factorJ)),'Finite analytic modal profiles and insulated constant mode')
 diagonal=np.zeros(n,np.complex128)
 for first in range(0,n,128):
  check(guard,deadline);last=min(n,first+128);squared=Q[:,first:last]**2;diagonal+=h*h*(squared@Y[first:last].real+1j*(squared@Y[first:last].imag))
 return dict(Y=Y,unitV=unitV,unitJ=unitJ,V=factorV,J=factorJ,diagonal=diagonal,gamma=np.asarray(gamma,np.complex128))

def fields(np,Q,profile,coeff,ij,layerids,h,guard,deadline):
 n=len(ij)
 phi=np.empty((len(layerids),n),np.complex128);E=np.empty((len(layerids),n,3),np.complex128);gamma=profile['gamma'][layerids]
 for first in range(0,len(layerids),8):
  check(guard,deadline);last=min(len(layerids),first+8);v=transform(np,Q,coeff[:,None]*profile['V'][:,first:last]).T;j=transform(np,Q,coeff[:,None]*profile['J'][:,first:last]).T
  phi[first:last]=v;E[first:last,:,:2]=provisional_field.lateral_field(np,v,ij,h,guard);E[first:last,:,2]=j/gamma[first:last,None]
 interface=transform(np,Q,coeff[:,None]*profile['unitJ'][:,1:4]).T
 require(np.isfinite(phi).all()and np.isfinite(E).all()and np.isfinite(interface).all(),'All streamed provisional phi/E/interfaceJ finite')
 return phi.reshape(-1),E.reshape((-1,3)),interface

