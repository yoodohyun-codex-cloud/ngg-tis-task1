"""Pure synthetic contracts; root alone decides actual execution and admission."""
import math,unittest
import contact_edge_surrogate as model


class ScalarContracts(unittest.TestCase):
 def test_full_contact_signed_power_and_current_units(self):
  gamma=model.complex_value(model.EXPECTED_GAMMA);zA=model.complex_value(model.EXPECTED_CONTACT);L=.002;t=.0001;V=1+0j
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
  self.assertEqual(spec['plan']['panel_axis']['fixed_positive_harmonics'],16384)
  self.assertEqual(spec['plan']['harmonic_axis']['fixed_panels'],1024)
  self.assertEqual(spec['diagnostic_delta_limits'],model.DELTA_LIMITS)
  self.assertEqual(spec['coefficient_transfer']['frequency_Hz'],2000)
  self.assertEqual(spec['plan']['transferred_gamma_S_m'],model.EXPECTED_GAMMA)
  self.assertEqual(spec['plan']['transferred_contact_ohm_m2'],model.EXPECTED_CONTACT)


class FourierCoefficientContract(unittest.TestCase):
 def test_complex_flux_negative_mode_is_not_the_conjugate_positive_mode(self):
  import numpy as np
  lengths=np.asarray([.0002,.0003]);centres=np.asarray([-.0003,.0001]);q=np.asarray([1+2j,3-1j])
  q0,plus,minus=model._coefficients(np,q,lengths,centres,3,.002,lambda:None,None)
  self.assertFalse(np.allclose(minus,np.conj(plus),rtol=1e-12,atol=1e-12))
  self.assertAlmostEqual(abs(q0-lengths@q/.002),0.,places=12)
  self.assertTrue(np.isfinite(plus).all()and np.isfinite(minus).all())


class SerializationContracts(unittest.TestCase):
 def test_numpy_scalars_normalize_without_precision_or_array_export(self):
  import json,numpy as np
  value={'flag':np.bool_(True),'count':np.int64(7),'value':np.float64(.125),'nested':(np.bool_(False),)}
  result=json.loads(model.encoded(value))
  self.assertIs(result['flag'],True);self.assertEqual(result['count'],7)
  self.assertEqual(result['value'],.125);self.assertIs(result['nested'][0],False)
  with self.assertRaises(TypeError):model.python_scalars(np.asarray([1,2]))

 def test_nonfinite_or_unsupported_metadata_never_opens_output(self):
  from unittest.mock import patch
  from pathlib import Path
  import numpy as np
  for value in(float('nan'),float('inf'),np.float64(float('nan')),np.asarray([1,2]),1+2j):
   with self.subTest(value_type=type(value).__name__),patch.object(Path,'open',side_effect=AssertionError('Invalid metadata must fail before open')):
    with self.assertRaises((ValueError,TypeError)):model.new_json(Path('/dev/shm/unused-HREF-invalid.json'),{'value':value})


if __name__=='__main__':unittest.main()
