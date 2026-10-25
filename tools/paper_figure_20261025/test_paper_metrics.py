"""Analytic complex-envelope contracts; no native data, filesystem or solver."""
import math
import unittest
import numpy as np
import paper_metrics as m


class ScalarComplexEnvelopeTests(unittest.TestCase):
    def test_quadrature_uses_imaginary_peak_amplitude(self):
        self.assertEqual(m.directional_modulation(1,1j),2.)
        self.assertAlmostEqual(m.envelope(1,1j,1/120),0.,places=13)
        self.assertAlmostEqual(m.envelope(1,1j,3/120),2.,places=13)
        self.assertEqual(2*min(abs((1+0j).real),abs((1j).real)),0.)

    def test_unequal_amplitudes_and_phase_do_not_change_full_beat_range(self):
        a,b=2*np.exp(.2j),.5*np.exp(-1.3j)
        align=(np.angle(a)-np.angle(b))%(2*math.pi)
        opposed=(align+math.pi)%(2*math.pi)
        self.assertAlmostEqual(m.directional_modulation(a,b),1.)
        self.assertAlmostEqual(m.envelope(a,b,align/(2*math.pi*30)),2.5,places=12)
        self.assertAlmostEqual(m.envelope(a,b,opposed/(2*math.pi*30)),1.5,places=12)

    def test_one_carrier_zero_modulation_nonzero_rms(self):
        self.assertEqual(m.directional_modulation(3-4j,0),0.)
        self.assertAlmostEqual(m.distinct_tone_rms(3-4j,0),5/math.sqrt(2))
        t=np.arange(128)/100000
        np.testing.assert_allclose(m.envelope(3-4j,0,t),5,rtol=1e-15,atol=1e-15)

    def test_same_frequency_cancels_coherently(self):
        self.assertEqual(m.same_frequency_rms(1,-1),0.)
        self.assertEqual(m.distinct_tone_rms(1,-1),1.)
        t=np.arange(128)/100000
        np.testing.assert_array_equal(m.signal(1,-1,t,f1=3000,f2=3000),np.zeros(128))
        np.testing.assert_array_equal(m.envelope(1,-1,t,f1=3000,f2=3000),np.zeros(128))

    def test_peak_plus_jwt_sign_and_broadcast(self):
        self.assertEqual(m.signal(2-3j,0,0),2.)
        self.assertAlmostEqual(m.signal(2-3j,0,1/12000),3.,places=14)
        np.testing.assert_array_equal(m.directional_modulation(np.array([1,2j,0]),1),[2,2,0])
        t=np.array([0.,1/12000])[:,None]
        a=np.array([1,1j])[None,:]
        self.assertEqual(m.signal(a,0,t).shape,(2,2))

    def test_invalid_numeric_inputs_fail(self):
        for a,b in ((float('nan'),1),(1,complex('inf'))):
            with self.assertRaises(ValueError):m.directional_modulation(a,b)
        with self.assertRaises(ValueError):m.envelope(1,1,float('inf'))
        with self.assertRaises(ValueError):m.signal(1,1,0,f1=0)

    def test_validation_separates_dense_diagnostic_and_analytic_gate(self):
        proof=m.mathematical_validation()
        self.assertEqual(proof['status'],'passed')
        self.assertFalse(proof['dense_grid_extrema_gated'])
        self.assertTrue(proof['exact_phase_augmented_extrema_gate'])
        self.assertEqual(len(proof['cases']),7)
        self.assertEqual(proof['quadrature_counterexample']['correct_complex_scalar_modulation'],2.)
        self.assertFalse(proof['native_data_read'])
        for case in proof['cases']:
            self.assertTrue(case['passed'])
            self.assertTrue(case['scalar_carrier_RMS']['passed'])
            self.assertEqual(case['dense_grid_only']['status'],'diagnostic_not_gated_sampled_extrema_may_be_missed')


if __name__=='__main__':unittest.main()
