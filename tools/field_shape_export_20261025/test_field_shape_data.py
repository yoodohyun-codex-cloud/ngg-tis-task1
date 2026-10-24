"""Small analytic tests; never touch a native cache or research run."""
import base64
import math
import unittest
import numpy as np
import field_shape_data as m


class ComplexFieldContracts(unittest.TestCase):
    def test_same_frequency_outputs_cancel_before_rms(self):
        native = np.asarray([[[3+4j, 1-2j, 0]], [[3+4j, 1-2j, 0]]])
        canceled = m.combine_outputs(native,[1,-1])
        np.testing.assert_array_equal(canceled,np.zeros((1,3)))
        self.assertEqual(float(m.rms_from_components([canceled])[0]),0.)
        self.assertGreater(float(m.rms_from_components([native[0],native[1]])[0]),0.)

    def test_peak_plus_jwt_sign_and_inactive_tone(self):
        field = np.array([[2-3j, -4+5j, 7+0j]])
        np.testing.assert_allclose(m.instantaneous({3000:field},0),field.real,rtol=0,atol=0)
        np.testing.assert_allclose(m.instantaneous({3000:field},1/12000),-field.imag,rtol=0,atol=2e-15)
        pure_sine = -1j*np.array([[2.,3.,4.]])
        np.testing.assert_array_equal(m.instantaneous({3000:pure_sine},0),np.zeros((1,3)))
        np.testing.assert_allclose(m.instantaneous({3000:pure_sine},1/12000),[[2,3,4]],rtol=0,atol=1e-15)

    def test_full_period_waveform_rms_matches_tone_energy(self):
        components={3000:np.array([[1+2j,3-4j,5+6j]]),3030:np.array([[2-1j,1+3j,-2-4j]])}
        times=np.arange(4096)/(4096*30)
        numerical=np.sqrt(np.mean([np.sum(m.instantaneous(components,float(t))**2,axis=1)for t in times],axis=0))
        np.testing.assert_allclose(numerical,m.rms_from_components(list(components.values())),rtol=2e-14,atol=1e-13)

    def test_packed_vectors_keep_xyz_real_imag_and_exterior(self):
        value=np.array([[1+2j,3+4j,5+6j],[-7-8j,-9-10j,-11-12j]])
        indices=np.array([[1,-1],[0,1]])
        encoded=m.encode_display(value,indices)
        a=np.frombuffer(base64.b64decode(encoded['data_base64']),dtype='<f4').reshape(encoded['shape'])
        self.assertEqual(encoded['shape'],[2,2,3,2])
        np.testing.assert_array_equal(a[0,0],np.array([[-7,-8],[-9,-10],[-11,-12]]))
        self.assertTrue(np.isnan(a[0,1]).all())
        np.testing.assert_array_equal(a[1,0],np.array([[1,2],[3,4],[5,6]]))
        self.assertTrue(encoded['precision']['passed'])
        with self.assertRaises(ValueError):m.encode_display(value,np.array([[2]]))

    def test_display_extremes_not_silently_clipped(self):
        value=np.array([[1e5+3e4j,1e-9+0j,-2e5j]])
        d=m.encode_display(value,np.array([[0]]))
        a=np.frombuffer(base64.b64decode(d['data_base64']),dtype='<f4').reshape(1,1,3,2)
        self.assertEqual(float(a[0,0,0,0]),100000.)
        self.assertEqual(float(a[0,0,2,1]),-200000.)
        with self.assertRaises(ValueError):m.encode_display(np.array([[complex('inf'),0,0]]),np.array([[0]]))


if __name__=='__main__': unittest.main()
