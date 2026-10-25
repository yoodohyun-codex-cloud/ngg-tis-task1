"""Caller-owned pure analytic tests; this module performs no work on import."""
import unittest
import human_sc4_interfaces as w


class CommonOrderInterfaceTests(unittest.TestCase):
    def test_analytic_reference_covers_sc2_sc4_common_and_quadratic(self):
        result=w.analytic_validation()
        self.assertTrue(result['passed'])
        self.assertEqual([(v['sc_cells'],v['maximum_fit_points_per_side'])for v in result['scenarios']],[(2,2),(4,2),(4,3)])
        self.assertFalse(result['full_convergence_validated'])

    def test_common_mode_has_exactly_two_points_on_every_side(self):
        for cells in(2,4):
            with self.subTest(sc_cells=cells):
                s=w.synthetic_layered_slab(cells)
                result=w.common_two_point_diagnostics(s['phi'],s['grid'],s['meta'],s['gamma'])
                self.assertEqual(result['status'],'diagnostic_not_gated')
                self.assertEqual(result['maximum_fit_points_per_side'],2)
                self.assertTrue(all(i['upper_fit_points']==i['lower_fit_points']==2 for i in result['interfaces']))
                self.assertTrue(all(i['upper_degree']==i['lower_degree']==1 for i in result['interfaces']))

    def test_sc4_quadratic_is_separate_from_common_linear(self):
        s=w.synthetic_layered_slab(4)
        common=w.common_two_point_diagnostics(s['phi'],s['grid'],s['meta'],s['gamma'])
        quadratic=w.interface_diagnostics(s['phi'],s['grid'],s['meta'],s['gamma'])
        self.assertEqual(common['interfaces'][0]['upper_degree'],1)
        self.assertEqual(quadratic['interfaces'][0]['upper_degree'],2)
        self.assertIn('different orders',quadratic['comparison_scope'])


if __name__=='__main__':unittest.main()
