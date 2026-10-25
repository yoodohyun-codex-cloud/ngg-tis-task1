"""Pure analytic/ABI regressions; no fixture opens a research native file."""
import math
import unittest
import numpy as np
import sc4_post as p


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


class SCColumnAveraging(unittest.TestCase):
    def test_complex_affine_sc_volume_average_and_bulk_identity(self):
        coarse=np.asarray([[0,0,.025,0,.05],[0,0,.075,0,.05],[0,0,1,1,1]],float)
        fine=np.asarray([[0,0,.0125,0,.025],[0,0,.0375,0,.025],[0,0,.0625,0,.025],[0,0,.0875,0,.025],[0,0,1,1,1]],float)
        a=np.column_stack([fine[:,2]*(1+2j)]*3);b=np.column_stack([coarse[:,2]*(1+2j)]*3)
        result=p.compare_native_fields(a,fine,b,coarse)
        self.assertLess(result['SC_full_thickness_volume_averaged_complex']['relative_component_L2'],1e-14)
        self.assertEqual(result['bulk_same_native_centres']['relative_component_L2'],0)


if __name__=='__main__':unittest.main()
