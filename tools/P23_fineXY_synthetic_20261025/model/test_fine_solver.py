"""Independent tiny manufactured CEM matrix; never a phantom/eigen solve."""
import unittest
import numpy as np
import fine_solver as s
def fixture():
 Q=np.asarray([[1,1,1,1],[1,-1,1,-1],[1,1,-1,-1],[1,-1,-1,1]],float)/2
 Y=np.asarray([0,.2+.1j,.3+.1j,.4+.1j]);h=.0005
 V=np.ones((4,5),complex);J=np.zeros((4,5),complex);V[1:,1:]=0;J[:,0]=Y
 profile=dict(Y=Y,diagonal=h*h*np.diag(Q@np.diag(Y)@Q.T),unitV=V,unitJ=J)
 pads=np.arange(4,dtype=np.int32);cells=np.arange(4,dtype=np.int32);areas=np.full(4,h*h);z=5.5e-5-1.2e-4j
 return Q,profile,pads,cells,areas,z,h
class TinyFineCEM(unittest.TestCase):
 def test_against_independent_full_coupled_MNA_and_power(self):
  Q,p,pads,cells,areas,z,h=fixture();T=h*h*(Q@np.diag(p['Y'])@Q.T);g=areas/z
  A=np.zeros((6,6),complex);A[:4,:4]=T+np.diag(g)
  for node in range(2):A[node,4+node]=-g[node];A[4+node,node]=-g[node];A[4+node,4+node]=g[node]+1/50
  b=np.zeros(6,complex);b[4]=.5/50;expected=np.linalg.solve(A,b)
  result=s.solve(np,Q,p,pads,cells,areas,z,0,h,lambda:None,None)
  np.testing.assert_allclose(np.r_[result['phi_surface'],result['metal']],expected,rtol=1e-10,atol=1e-12)
  self.assertTrue(result['proof']['passed']);self.assertEqual(result['proof']['actual_new_RHS'],1)
  self.assertGreater(abs(result['source_current'][1]),0.,'Inactive ideal0V/50ohm output remains connected')
 def test_validated_reuse_is_zero_RHS_with_unchanged_physics(self):
  Q,p,pads,cells,areas,z,h=fixture();first=s.solve(np,Q,p,pads,cells,areas,z,0,h,lambda:None,None)
  reused=s.solve(np,Q,p,pads,cells,areas,z,0,h,lambda:None,None,cached=first)
  self.assertTrue(reused['proof']['passed']);self.assertEqual(reused['proof']['actual_new_RHS'],0)
  np.testing.assert_allclose(reused['layer_power'],first['layer_power'],rtol=1e-12,atol=1e-18)
 def test_bad_cached_metal_cannot_pass_the_fresh_circuit_gate(self):
  Q,p,pads,cells,areas,z,h=fixture();first=s.solve(np,Q,p,pads,cells,areas,z,0,h,lambda:None,None)
  cached=dict(phi_surface=first['phi_surface'],metal=first['metal']+np.asarray([.01,0.]))
  bad=s.solve(np,Q,p,pads,cells,areas,z,0,h,lambda:None,None,cached=cached)
  self.assertFalse(bad['proof']['passed']);self.assertFalse(bad['proof']['physical_gates']['passed'])
if __name__=='__main__':unittest.main()
