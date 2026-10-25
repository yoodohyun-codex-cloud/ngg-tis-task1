"""Small independent analytic depth/field contracts; not a real phantom solve."""
import unittest
import numpy as np
import fine_fields as f
class ManufacturedDepthFields(unittest.TestCase):
 def test_homogeneous_Fourier_profile_analytic_normal_derivative(self):
  gamma=.2+.1j;k=20.;T=sum(f.THICKNESS);Q=np.asarray([[1.,1.],[1.,-1.]])/np.sqrt(2.);zs=np.asarray([.00005,.002,.007,.017]);layers=np.asarray([0,1,2,3]);h=.0005
  profile=f.profiles(np,Q,np.asarray([0.,k*k]),[gamma]*4,zs,h,lambda:None,None);coeff=np.asarray([0.,1.],complex)
  phi,E,J=f.fields(np,Q,profile,coeff,np.asarray([[0,0],[1,0]]),layers,h,lambda:None,None)
  expectedV=np.cosh(k*(T-zs))/np.cosh(k*T);expectedEz=k*np.sinh(k*(T-zs))/np.cosh(k*T)
  np.testing.assert_allclose(phi.reshape(4,2),expectedV[:,None]*Q[:,1],rtol=1e-12,atol=1e-13)
  np.testing.assert_allclose(E.reshape(4,2,3)[:,:,2],expectedEz[:,None]*Q[:,1],rtol=1e-12,atol=1e-12)
 def test_constant_mode_has_zero_carrier_field(self):
  Q=np.ones((1,1));zs=np.asarray([.00005,.002,.007,.017]);profile=f.profiles(np,Q,np.asarray([0.]),[.2+.1j]*4,zs,.0005,lambda:None,None)
  phi,E,J=f.fields(np,Q,profile,np.asarray([1.],complex),np.asarray([[0,0]]),np.arange(4),.0005,lambda:None,None)
  np.testing.assert_allclose(phi,1.,rtol=0,atol=1e-14);np.testing.assert_allclose(E,0.,rtol=0,atol=1e-14);np.testing.assert_allclose(J,0.,rtol=0,atol=1e-14)
if __name__=='__main__':unittest.main()
