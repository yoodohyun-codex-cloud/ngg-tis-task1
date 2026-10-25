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

def common_bulk_depth_identity(np,old_faces,new_faces):
 old=np.asarray(old_faces,float);new=np.asarray(new_faces,float)
 require(old.shape==(102,)and new.shape==(98,),'Original101 and common97 depth faces')
 a=(old[:-1]+old[1:])/2.;b=(new[:-1]+new[1:])/2.
 error=float(np.max(abs(a[8:]-b[4:])))
 require(error<=1e-12,'All93 unchanged bulk planes must share physical depths; never copy by unchecked index')
 require(np.allclose(old[[0,8,27,45,101]],[0,.0001,.0051,.0101,.0251],rtol=0,atol=1e-12)and np.allclose(new[[0,4,23,41,97]],[0,.0001,.0051,.0101,.0251],rtol=0,atol=1e-12),'Same four fixed physical layers')
 return dict(passed=True,maximum_bulk_depth_difference_m=error,unchanged_bulk_planes=93,old_SC_samples=8,new_SC_samples=4,physical_SC_thickness_m=.0001)

def geometry(np,xy_m,ij,faces_m,h,guard,deadline):
 """Original128² boundary fractions, freshly evaluated at this physical grid."""
 from frozen_volume import native_region_weights
 check(guard,deadline);xy=np.asarray(xy_m,float);ij=np.asarray(ij);faces=np.asarray(faces_m,float)
 n=len(xy);counts=[4,19,18,56];zs=(faces[:-1]+faces[1:])/2.;layerids=np.repeat(np.arange(4),counts)
 require(n in(7860,8184)and xy.shape==ij.shape==(n,2)and faces.shape==(98,)and n*97<=800000,'Actual bounded fine/coarse common97 geometry')
 require(np.allclose(faces[[0,4,23,41,97]],[0,.0001,.0051,.0101,.0251],rtol=0,atol=1e-12)and np.all(np.diff(faces)>0),'Unchanged physical depths and strictly positive cells')
 require(np.allclose(xy,(-.025+(ij+.5)*h),rtol=0,atol=1e-14),'Actual graph ij and physical centres agree')
 grid=np.column_stack((np.tile(xy[:,0]*1000,97),np.tile(xy[:,1]*1000,97),np.repeat(zs*1000,n),np.repeat(layerids,n),np.repeat(h*h*np.diff(faces),n)))
 weights,receipt=native_region_weights({key:grid[:,i]for i,key in enumerate(('x_mm','y_mm','z_mm','layer','volume_m3'))},dict(h_xy_mm=h*1000,radius_mm=25.,z_faces_mm=faces*1000,layer_counts=counts,geometry_volume_tolerance_relative=.002,target_volume_tolerance_relative=.001),deadline_monotonic=deadline)
 check(guard,deadline);return dict(grid=grid,weights=weights,ROI_receipt=receipt,zs_m=zs,layerids=layerids,faces_m=faces)
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

