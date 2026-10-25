"""Synthetic-only source fixtures; author has not imported or run them."""
import unittest
import numpy as np
import light_probe as p


def grid(depths=None):
    depths=depths if depths is not None else [.05,1.,4.9,6.,9.,10.,12.,15.,20.,23.]
    xy=[(x,y)for y in[-10.,-7.5,-5.,-2.5,0.,2.5,5.,7.5,10.]for x in[-10.,-7.5,-5.,-2.5,0.,2.5,5.,7.5,10.]]
    return np.asarray([[x,y,z,int(np.searchsorted(p.INTERFACES_MM,z,side='right')-1),1e-9]for z in depths for x,y in xy],float)


class LightPhysicalProbeTests(unittest.TestCase):
    def test_affine_complex_potential_streaming_is_exact_at_all_40_probes(self):
        g=grid();g[:,:2]+=.25  # Force nontrivial bilinear XY stencils at every requested tip.
        prepared=p.prepare(np,g,allow_same_layer_extrapolation=True)
        a=.03+.02j;b=-.04+.01j;c=.02-.03j;phi=a*g[:,0]+b*g[:,1]+c*g[:,2]+.6+.3j
        sampled=p.sample_carrier(np,prepared,phi,2000)
        expected=np.asarray([5*a if row['differential_axis']=='x'else 5*b for row in prepared['probes']])
        np.testing.assert_allclose(sampled['differential_phasors_V_peak'],expected,rtol=1e-13,atol=1e-14)
        self.assertTrue(sampled['available'].all());self.assertEqual(len(prepared['probes']),40)
        self.assertNotIn('grid',prepared)
        self.assertNotIn('lookup',prepared)
        self.assertTrue(all(len(tip['indices'])<=8 for row in prepared['probes']for tip in(row['positive'],row['negative'])))

    def test_default_missing_same_layer_bracket_is_not_cross_layer_fill(self):
        prepared=p.prepare(np,grid())
        missing=[row for row in prepared['probes']if not row['available']]
        self.assertEqual(len(missing),10)
        self.assertTrue(all(row['centre_xyz_mm'][2]==5. for row in missing))
        self.assertTrue(all(row['negative']['metadata']['Z']['cross_layer_interpolation']is False for row in missing))
        self.assertTrue(all(row['negative']['metadata']['Z']['method']=='unavailable_same_layer_bracket_missing'for row in missing))

    def test_explicit_one_spacing_extrapolation_retains_negative_weights(self):
        prepared=p.prepare(np,grid(),allow_same_layer_extrapolation=True)
        row=prepared['probes'][0];info=row['positive']['metadata']['Z']
        self.assertIn('one_sided_linear_extrapolation_explicit',info['method'])
        self.assertLess(info['signed_weights'][0],0.)
        self.assertLessEqual(info['extrapolation_distance_over_sample_spacing'],1.)
        self.assertGreater(info['distance_to_nearest_physical_layer_boundary_mm'],0.)
        self.assertEqual(info['physical_layer_bounds_mm'],[.1,5.1])

    def test_extrapolation_beyond_one_spacing_is_unavailable(self):
        g=grid([.05,4.7,4.8,6.,9.,10.,12.,15.,20.,23.]);prepared=p.prepare(np,g,allow_same_layer_extrapolation=True)
        missing=[row for row in prepared['probes']if not row['available']]
        self.assertEqual(len(missing),10)
        self.assertTrue(all('beyond_one_spacing'in row['positive']['metadata']['Z']['method']for row in missing))

    def test_physical_layer_interface_requires_explicit_other_reconstruction(self):
        layout=p._layout(np,grid())
        with self.assertRaisesRegex(ValueError,'strictly inside'):p._z_stencil(np,layout,5.1,True)
        with self.assertRaisesRegex(ValueError,'XY interpolation'):p._axis_stencil(np,np.asarray([-1.,0.,1.]),2.)

    def test_native_zmajor_order_is_authenticated_not_index_guessed(self):
        g=grid();g[81:162,:2]=g[81:162,:2][::-1]
        with self.assertRaisesRegex(ValueError,'identical ordered XY'):p.prepare(np,g)

    def test_two_tone_real_waveform_dft_rms_and_demodulation_are_distinct(self):
        delta=np.asarray([.4+.3j,.2-.1j]);metrics,small=p.waveform_metrics(np,delta,[2000,2010])
        self.assertAlmostEqual(metrics['carrier_RMS_exact_V'],np.sqrt(np.sum(abs(delta)**2)/2.),places=13)
        self.assertAlmostEqual(metrics['envelope_AM_exact_V_peak'],2*min(abs(delta)),places=13)
        self.assertLess(metrics['physical_voltage_10Hz_DFT_peak_V'],1e-12)
        self.assertGreater(metrics['envelope_10Hz_DFT_peak_V'],.01)
        actual=np.asarray([complex(v['real'],v['imaginary'])for v in metrics['spectrum_coherent_DFT_phasors_V_peak']])
        np.testing.assert_allclose(actual,delta,rtol=1e-12,atol=1e-12)
        self.assertEqual(len(small['carrier_excerpt_V'])+len(small['envelope_V']),256)
        self.assertLessEqual(metrics['Vpp_sampling_diagnostic']['relative_delta'],2e-4)
        self.assertIn('N65536_Vpp',metrics['Vpp_sampling_diagnostic'])

    def test_single_carrier_has_zero_two_tone_am_without_activation_claim(self):
        metrics,_=p.waveform_metrics(np,[.3+.4j],[2000])
        self.assertEqual(metrics['envelope_AM_exact_V_peak'],0.)
        self.assertFalse(metrics['single_carrier_has_two_tone_AM'])
        self.assertAlmostEqual(metrics['carrier_RMS_exact_V'],.5/np.sqrt(2.),places=13)
        self.assertLess(metrics['envelope_AM_sampled_V_peak'],1e-12)

    def test_no_noncoherent_or_more_than_two_carrier_formula_extension(self):
        with self.assertRaisesRegex(ValueError,'Coherent'):p.waveform_metrics(np,[1.,1.],[2000,2010.5])
        with self.assertRaisesRegex(ValueError,'One or two'):p.waveform_metrics(np,[1.,1.,1.],[2000,2010,2020])

    def test_expired_deadline_rejects_before_any_data_access(self):
        with self.assertRaises(TimeoutError):p.prepare(None,None,deadline_monotonic=0.)
        with self.assertRaises(TimeoutError):p.waveform_metrics(None,None,None,deadline_monotonic=0.)
