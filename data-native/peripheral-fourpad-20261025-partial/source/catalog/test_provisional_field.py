"""Small analytic unit-test SOURCE; no test execution or NumPy import on import."""
import unittest
import provisional_field as f


def np_for_test():
    import numpy as np
    return np


class ProvisionalFieldTests(unittest.TestCase):
    def test_complex_affine_interior_and_outer_half_face_contributions(self):
        np=np_for_test();h=.0005
        ij=np.asarray([(i,j)for j in range(3)for i in range(3)])
        a=.3+.2j;b=-.4+.1j
        phi=.7+a*ij[:,0]*h+b*ij[:,1]*h
        e=f.lateral_field(np,phi,ij,h)
        lookup={tuple(row):i for i,row in enumerate(ij)}
        np.testing.assert_allclose(e[lookup[1,1]],[-a,-b],rtol=1e-10,atol=1e-10)
        np.testing.assert_allclose(e[lookup[0,1]],[-a/2.,-b],rtol=1e-10,atol=1e-10)
        np.testing.assert_allclose(e[lookup[0,0]],[-a/2.,-b/2.],rtol=1e-10,atol=1e-10)

    def test_staircase_missing_neighbor_contributes_zero_not_full_one_sided(self):
        np=np_for_test();h=.0005
        ij=np.asarray([[0,0],[1,0],[0,1]])
        a=1.+2j;b=-3.+.5j;phi=a*ij[:,0]*h+b*ij[:,1]*h
        e=f.lateral_field(np,phi,ij,h)
        np.testing.assert_allclose(e,[[-a/2.,-b/2.],[-a/2.,0.],[0.,-b/2.]],rtol=1e-10,atol=1e-10)

    def test_row_reordering_preserves_physical_neighbor_mapping(self):
        np=np_for_test();h=.0005
        ij=np.asarray([[0,0],[1,0],[0,1],[1,1]])
        phi=(.2+.1j)*ij[:,0]+(.3-.4j)*ij[:,1]
        original=f.lateral_field(np,phi,ij,h);order=np.asarray([3,0,2,1])
        reordered=f.lateral_field(np,phi[order],ij[order],h)
        np.testing.assert_allclose(reordered,original[order],rtol=0,atol=1e-12)

    def test_constant_complex_potential_has_zero_lateral_field(self):
        np=np_for_test();ij=np.asarray([[0,0],[1,0],[0,1]])
        e=f.lateral_field(np,np.full((2,3,3),2.+3j),ij,.0005)
        np.testing.assert_array_equal(e,np.zeros((2,3,3,2),complex))

    def test_assembled_E_uses_downward_J_over_complex_gamma_without_minus(self):
        np=np_for_test();h=.0005;ij=np.asarray([[0,0],[1,0],[0,1]])
        phi=np.zeros((2,2,3),complex)
        j=np.asarray([[[1.+2j]*3,[3.-4j]*3],[[2.-1j]*3,[4.+3j]*3]])
        gamma=np.asarray([.2+.03j,.04+.01j]);storage=np.empty((2,2,3,3),complex)
        e=f.assemble_E(np,phi,j,gamma,ij,h,depth_block=1,out=storage)
        self.assertIs(e,storage)
        np.testing.assert_array_equal(e[...,:2],np.zeros((2,2,3,2),complex))
        np.testing.assert_allclose(e[...,2],j/gamma[:,None],rtol=1e-10,atol=1e-10)
        self.assertEqual(f.provenance()['derived_field_version'],'native-lateral-half-face-v1+analytic-z-DtN-v1')
        self.assertFalse(f.provenance()['old_vertical_field_ABI_reproduced'])
        self.assertFalse(f.provenance()['full_E_accuracy_validated'])


if __name__=='__main__':unittest.main()
