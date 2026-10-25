"""Pure analytic/ABI regressions; no fixture opens a research native file."""
import math
import unittest
import numpy as np
import human_post as p


class NativePostContracts(unittest.TestCase):
    def test_square3h_real_time_unit_Vpp_normalization(self):
        c=p.coefficients();phase=math.pi/4
        voltage=.5*(c[3000][0]*np.exp(1j*phase)+c[9000][0]*np.exp(3j*phase)).real
        self.assertAlmostEqual(voltage,.5)
        self.assertEqual(c[3000][1],0);self.assertEqual(c[3030][0],0)

    def test_weighted_ecdf_ties_keep_native_coordinate_identity(self):
        grid=np.asarray([[0,0,1,0,1],[1,0,1,0,2],[2,0,1,0,1]],float)
        stats=p.weighted_statistics([4,1,4],[1,2,1],grid)
        self.assertEqual(stats['median'],1);self.assertEqual(stats['p90'],4)
        self.assertEqual(stats['mean'],2.5);self.assertEqual(stats['maximum_location']['tied_cell_count'],2)
        self.assertEqual(stats['maximum_location']['native_cell_index'],0)

    def test_nonfinite_statistics_and_empty_volume_fail(self):
        grid=np.asarray([[0,0,1,0,1]],float)
        with self.assertRaises(ValueError):p.weighted_statistics([float('nan')],[1],grid)
        with self.assertRaises(ValueError):p.weighted_statistics([1],[0],grid)

    def test_half_face_reconstruction_is_not_plain_one_sided_gradient(self):
        grid=np.asarray([[0,0,.5,0,1e-9],[1,0,.5,0,1e-9]],float)
        geometry=dict(lookup=np.asarray([[[0,1]]]),h=.001,iz=np.asarray([0,0]),dz=np.asarray([.001]))
        contacts=np.asarray([],dtype=[('pad',int),('x_mm',float),('y_mm',float),('area_m2',float)])
        field=p.reconstruct_native_field(np.asarray([1.,.5],complex),grid,geometry,np.asarray([1.+.5j]*4),contacts,np.zeros(2),0j)
        self.assertTrue(np.allclose(field[:,0],250))
        self.assertTrue(np.allclose(field[:,1:],0))
        # Each boundary cell has only one internal face. This fixture tests the
        # stored finite-volume half-face ABI, not the continuum slab field500.


class PerCarrierMaterialLookup(unittest.TestCase):
    def test_per_frequency_conduction_and_displacement_are_distinct(self):
        config={n+'.'+kind+'.'+str(f):str((i+1)*(f/3000 if kind=='sigma'else 100))for i,n in enumerate(p.LAYERS)for kind in('sigma','epsilon_r')for f in p.FREQUENCIES}
        a=p._gamma(config,3000);b=p._gamma(config,9000)
        self.assertTrue(np.allclose(a.real,[1,2,3,4]))
        self.assertTrue(np.allclose(b.real,[3,6,9,12]))
        self.assertTrue(np.allclose(b.imag,3*a.imag))
        self.assertTrue(np.array_equal(p._sigma(config,9000),b.real))


if __name__=='__main__':unittest.main()
