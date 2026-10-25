"""Caller-owned source tests only; import does not execute any analytic checks."""
import unittest
import sc8_interfaces as w


class GenericXYInterfaceTests(unittest.TestCase):
    def test_analytic_slab_and_affine_cover_both_xy_spacings(self):
        result=w.analytic_validation()
        self.assertTrue(result['passed'])
        self.assertEqual([(v['h_xy_mm'],v['sc_cells'],v['maximum_fit_points_per_side'])
                          for v in result['scenarios']],
                         [(h,c,p)for h in(.5,.625)for c,p in((2,2),(4,2),(4,3),(8,2),(8,3))])
        self.assertEqual([v['h_xy_mm']for v in result['affine_checks']],[.5,.625])
        self.assertFalse(result['full_convergence_validated'])
        self.assertFalse(result['native_data_read'])

    def test_sc2_orders_remain_two_two_and_two_three(self):
        for h in(.5,.625):
            with self.subTest(h_xy_mm=h):
                s=w.synthetic_layered_slab(2,h_xy_mm=h)
                common=w.common_two_point_diagnostics(s['phi'],s['grid'],s['meta'],s['gamma'])
                original=w.interface_diagnostics(s['phi'],s['grid'],s['meta'],s['gamma'])
                self.assertEqual(common['status'],'diagnostic_not_gated')
                self.assertTrue(all(i['upper_fit_points']==i['lower_fit_points']==2
                                    for i in common['interfaces']))
                self.assertEqual((original['interfaces'][0]['upper_fit_points'],
                                  original['interfaces'][0]['lower_fit_points']),(2,3))

    def test_default_native_mask_uses_actual_xy_spacing(self):
        for h,expected in((.5,24.),(.625,23.75)):
            with self.subTest(h_xy_mm=h):
                s=w.synthetic_layered_slab(2,h_xy_mm=h)
                result=w.common_two_point_diagnostics(s['phi'],s['grid'],s['meta'],s['gamma'])
                self.assertEqual(result['interior_radius_mm'],expected)
                self.assertEqual(result['native_interior_radius_mm'],expected)
                self.assertFalse(result['interior_radius_is_fixed_physical'])
                self.assertEqual(result['region_face_columns']['interior'],
                                 result['region_face_columns']['native_interior'])

    def test_fixed_physical_mask_preserves_native_regions_and_stencil_counts(self):
        s=w.synthetic_layered_slab(2,h_xy_mm=.5)
        for function in(w.common_two_point_diagnostics,w.interface_diagnostics):
            with self.subTest(function=function.__name__):
                result=function(s['phi'],s['grid'],s['meta'],s['gamma'],interior_radius_mm=.5)
                self.assertTrue(result['interior_radius_is_fixed_physical'])
                self.assertEqual(result['interior_radius_mm'],.5)
                self.assertEqual(result['native_interior_radius_mm'],24.)
                self.assertEqual(result['region_face_columns']['interior'],4)
                self.assertEqual(result['region_face_columns']['staircase_periphery'],12)
                self.assertEqual(result['region_face_columns']['native_interior'],16)
                self.assertEqual(result['region_face_columns']['fixed_physical_interior'],4)
                for region,count in result['region_face_columns'].items():
                    for axis in('x','y'):
                        self.assertEqual(sum(result['tangent_stencil_counts_by_region'][region][axis].values()),count)
                    for interface in result['interfaces']:
                        self.assertEqual(interface['regions'][region]['face_columns'],count)

    def test_registered_physical_cutoff_is_retained_at_both_spacings(self):
        for h in(.5,.625):
            s=w.synthetic_layered_slab(2,h_xy_mm=h)
            result=w.common_two_point_diagnostics(s['phi'],s['grid'],s['meta'],s['gamma'],
                                                  interior_radius_mm=23.75)
            self.assertEqual(result['interior_radius_mm'],23.75)
            self.assertEqual(result['native_interior_radius_mm'],25.-2*h)
            self.assertTrue(result['interior_radius_is_fixed_physical'])

    def test_invalid_physical_radius_is_rejected(self):
        s=w.synthetic_layered_slab(2,h_xy_mm=.5)
        for radius in(-1.,26.,float('nan')):
            with self.subTest(interior_radius_mm=radius),self.assertRaises(ValueError):
                w.common_two_point_diagnostics(s['phi'],s['grid'],s['meta'],s['gamma'],
                                               interior_radius_mm=radius)


if __name__=='__main__':unittest.main()
