import unittest
import numpy as np
import whole_layer_interfaces as w


class InterfaceHelpers(unittest.TestCase):
    def test_complex_layered_and_affine_exact_references(self):
        result=w.analytic_validation()
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['layered_slab']),6)
        self.assertFalse(result['full_convergence_validated'])

    def test_quadratic_extrapolation_and_derivative_in_metres(self):
        nodes=np.asarray([.001,.002,.003]);at=.004
        values=(2+3j)+(4-2j)*nodes+(3+.5j)*nodes**2
        exact=(2+3j)+(4-2j)*at+(3+.5j)*at**2
        derivative=(4-2j)+2*(3+.5j)*at
        self.assertAlmostEqual(abs(w.lagrange_weights(nodes,at)@values-exact),0,places=12)
        self.assertAlmostEqual(abs(w.lagrange_weights(nodes,at,1)@values-derivative),0,places=9)

    def test_duplicate_or_nonfinite_fit_nodes_rejected(self):
        for nodes in(([0.,0.]),([0.,float('nan')])):
            with self.assertRaises(ValueError):w.lagrange_weights(nodes,0.)

    def test_zero_face_comparison_uses_explicit_floor(self):
        result=w._comparison(np.zeros(2),np.zeros(2),np.asarray([[0.,0.],[1.,0.]]),.1,'V')
        self.assertEqual(result['normalized_L2'],0)
        self.assertEqual(result['denominator'],w.DENOMINATOR_FLOOR)
        self.assertEqual(result['status'],'diagnostic_not_gated')


if __name__=='__main__':unittest.main()
