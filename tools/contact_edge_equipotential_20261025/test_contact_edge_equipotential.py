"""Pure synthetic contracts; root alone decides actual execution and admission."""
import math,unittest
import contact_edge_equipotential as model


class ScalarContracts(unittest.TestCase):
 def test_full_contact_signed_power_and_current_units(self):
  gamma=1+.25j;zA=1e-4-2e-5j;L=.002;t=.0001;V=1+0j
  answer=model.full_contact_analytic(gamma,zA,L,t,V)
  self.assertAlmostEqual(abs(answer['I']-L*V/(zA+t/gamma)),0.,places=12)
  self.assertLess(abs(answer['Ssource']-answer['Scontact']-answer['Sbulk']),1e-10)
  self.assertGreater(answer['Sbulk'].real,0.)
  self.assertLess(answer['Sbulk'].imag,0.)

 def test_high_k_depth_kernel_is_finite_and_has_correct_boundary_values(self):
  t=.0001;k=1e9
  at_top=model.stable_kernel(k,0.,t);at_bottom=model.stable_kernel(k,t,t)
  self.assertTrue(all(math.isfinite(value)for value in at_top+at_bottom))
  self.assertAlmostEqual(at_top[0],1/k,places=16)
  self.assertAlmostEqual(at_top[1],1.,places=12)
  self.assertEqual(at_bottom[0],0.)
  self.assertEqual(model.stable_kernel(0.,t/2,t),(t/2,1.))

 def test_two_refinement_axes_share_only_one_finest_case(self):
  spec=model.make_spec();pairs=[tuple(row)for row in spec['plan']['unique_cases']]
  self.assertEqual(len(pairs),5)
  self.assertEqual(len(set(pairs)),5)
  self.assertEqual(spec['plan']['panel_axis']['fixed_positive_harmonics'],2048)
  self.assertEqual(spec['plan']['harmonic_axis']['fixed_panels'],128)
  self.assertEqual(spec['diagnostic_delta_limits'],model.DELTA_LIMITS)


class SmallGalerkinContracts(unittest.TestCase):
 def test_full_period_contact_has_only_the_analytic_constant_mode(self):
  import numpy as np
  proof=model.analytic_validation(np)
  self.assertTrue(proof['passed'])
  self.assertEqual(proof['new_actual_phantom_PDE'],0)

 def test_complex_flux_negative_mode_is_not_the_conjugate_positive_mode(self):
  import numpy as np
  lengths=np.asarray([.0002,.0003]);centres=np.asarray([-.0003,.0001]);q=np.asarray([1+2j,3-1j])
  q0,plus,minus=model._coefficients(np,q,lengths,centres,3,.002,lambda:None,None)
  self.assertFalse(np.allclose(minus,np.conj(plus),rtol=1e-12,atol=1e-12))
  self.assertAlmostEqual(abs(q0-lengths@q/.002),0.,places=12)
  self.assertTrue(np.isfinite(plus).all()and np.isfinite(minus).all())


if __name__=='__main__':unittest.main()
