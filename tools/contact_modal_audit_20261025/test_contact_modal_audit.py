"""Pure modal contracts; no actual stored arrays or PDE are used by these tests."""
import math,unittest
import contact_modal_audit as model

class ModalContracts(unittest.TestCase):
 def test_constant_current_has_uniform_temporal_RMS_field(self):
  import numpy as np
  L=.002;t=.0001;gamma=1+.25j;q=.2+.1j
  value=model.modal_integral(np,q,np.asarray([],complex),np.asarray([],complex),L,t,gamma)
  self.assertAlmostEqual(math.sqrt(value/(2*L*t)),abs(q/gamma)/math.sqrt(2),places=13)

 def test_missing_higher_signed_modes_are_zero_padded(self):
  import numpy as np
  a=dict(q0=0j,plus=np.asarray([1+2j]),minus=np.asarray([2-3j]))
  b=dict(q0=0j,plus=np.asarray([1+2j,3+4j]),minus=np.asarray([2-3j,-2+1j]))
  answer=model.modal_difference(np,a,b,.002,.0001,1+.25j)
  self.assertEqual(complex(answer['arrays']['delta_q_positive_peak_A_m2'][0]),0j)
  self.assertEqual(complex(answer['arrays']['delta_q_negative_peak_A_m2'][0]),0j)
  self.assertEqual(complex(answer['arrays']['delta_q_positive_peak_A_m2'][1]),3+4j)
  self.assertEqual(complex(answer['arrays']['delta_q_negative_peak_A_m2'][1]),-2+1j)
  self.assertGreater(answer['summary']['difference_integral_peak_E_squared_V2'],0.)

 def test_global_phasor_rotation_is_not_fitted_away(self):
  import numpy as np
  a=dict(q0=1+0j,plus=np.asarray([.1+.2j]),minus=np.asarray([.2-.1j]));b=dict(q0=1j,plus=1j*a['plus'],minus=1j*a['minus'])
  result=model.modal_difference(np,a,b,.002,.0001,1+.25j)
  self.assertAlmostEqual(result['summary']['relative_L2'],math.sqrt(2),places=12)

 def test_constant_plus_single_cosine_matches_independent_vector_quadrature(self):
  import numpy as np
  self.assertTrue(model.analytic_contract(np)['passed'])

 def test_signed_coefficients_are_not_assumed_conjugate(self):
  import numpy as np
  p=np.asarray([1+2j]);m=np.asarray([4-3j]);L=.002;t=.0001;gamma=1+.25j;k=2*math.pi/L
  truth=L/abs(gamma)**2*math.tanh(k*t)/k*(abs(p[0])**2+abs(m[0])**2)
  self.assertAlmostEqual(model.modal_integral(np,0j,p,m,L,t,gamma),truth,places=14)

if __name__=='__main__':unittest.main()
