"""Caller-owned pure analytic test SOURCE; no native inputs or execution on import."""
import json
import math
import unittest
import numpy as np
import cem_fit as f


def slab_fixture(sc_cells=2):
    boundaries=np.asarray([0.,.1,5.1,10.1,25.1])
    counts=np.asarray([sc_cells,3,3,4])
    gamma=np.asarray([.002+.01j,.2+.002j,.04+.0002j,.3+.02j])
    faces=np.concatenate([np.linspace(boundaries[l],boundaries[l+1],counts[l]+1)[:-1]
                          for l in range(4)]+[boundaries[-1:]])
    centres=(faces[:-1]+faces[1:])/2.;layers=np.repeat(np.arange(4),counts)
    xy=np.asarray([[-.5,-.5],[-.5,.5],[.5,-.5],[.5,.5]])
    current=1./np.sum(np.diff(boundaries)/1000./gamma)
    pz=[]
    for z,layer in zip(centres,layers):
        resistance=np.sum(np.diff(boundaries)[:layer]/1000./gamma[:layer])+(z-boundaries[layer])/1000./gamma[layer]
        pz.append(1.-current*resistance)
    tangent=(.3+.2j)*xy[:,0]/1000.+(-.4+.1j)*xy[:,1]/1000.
    phi=(np.asarray(pz)[:,None]+tangent[None,:]).reshape(-1)
    grid=np.column_stack((np.tile(xy[:,0],len(centres)),np.tile(xy[:,1],len(centres)),
                          np.repeat(centres,len(xy)),np.repeat(layers,len(xy)),
                          np.repeat(np.diff(faces)*1e-9,len(xy))))
    # Input order is deliberately different from sorted native z/XY order.
    order=np.arange(len(phi))[::-1]
    meta=dict(sc_cells=sc_cells,bulk_layer_counts=[3,3,4],z_faces_mm=faces.tolist(),h_xy_mm=1.,radius_mm=25.)
    return phi[order],grid[order],meta,gamma,current


class CEMFitAnalyticTests(unittest.TestCase):
    def test_affine_layered_complex_slab_normal_current_exact_both_orders(self):
        for cells in(2,4):
            phi,grid,meta,gamma,current=slab_fixture(cells)
            layout=f.prepare_layout(grid,meta)
            for points in(2,3):
                with self.subTest(sc_cells=cells,points=points):
                    result=f.normal_fits(phi,grid,meta,gamma,points,layout=layout)
                    np.testing.assert_allclose(result['upper_J'],current,rtol=1e-10,atol=1e-10)
                    np.testing.assert_allclose(result['lower_J'],current,rtol=1e-10,atol=1e-10)
                    np.testing.assert_allclose(result['upper_phi'],result['lower_phi'],rtol=1e-10,atol=1e-10)
                    self.assertEqual(result['upper_points'][0],min(cells,points))
                    self.assertTrue(all(v==points for v in result['lower_points']))
                    self.assertEqual(result['status'],'diagnostic_not_gated')

    def test_common_two_point_is_exactly_two_on_every_side(self):
        phi,grid,meta,gamma,_=slab_fixture(4)
        result=f.normal_fits(phi,grid,meta,gamma,2)
        self.assertEqual(result['upper_points'],[2,2,2])
        self.assertEqual(result['lower_points'],[2,2,2])
        np.testing.assert_allclose(result['interface_depths_mm'],[.1,5.1,10.1],rtol=0,atol=1e-12)

    def test_layout_reuse_and_guard_preserve_results(self):
        phi,grid,meta,gamma,_=slab_fixture(4);calls=[]
        layout=f.prepare_layout(grid,meta)
        fresh=f.normal_fits(phi,grid,meta,gamma,3)
        reused=f.normal_fits(phi,grid,meta,gamma,3,guard=lambda:calls.append(1),layout=layout)
        np.testing.assert_array_equal(fresh['upper_J'],reused['upper_J'])
        self.assertEqual(len(calls),4)

    def test_fixed_and_native_periphery_scopes_are_distinct(self):
        xy=np.asarray([[0.,0.],[23.5,0.],[23.8,0.],[24.1,0.]])
        masks=f.scopes(xy,.5)
        self.assertEqual(masks['interior'].tolist(),[True,True,False,False])
        self.assertEqual(masks['native_interior'].tolist(),[True,True,True,False])
        np.testing.assert_array_equal(masks['staircase_periphery'],~masks['interior'])
        np.testing.assert_array_equal(masks['native_staircase_periphery'],~masks['native_interior'])
        coarse=f.scopes(xy,.625)
        np.testing.assert_array_equal(coarse['interior'],coarse['native_interior'])

    def test_interface_norm_is_spatial_complex_not_temporal_rms(self):
        xy=np.asarray([[0.,0.],[1.,0.]])
        result=f.interface_norms(np.asarray([1.+1j,1.+1j]),np.asarray([1.+0j,1.+0j]),xy,.1,np.asarray([True,True]))
        self.assertAlmostEqual(result['upper_spatial_complex_RMS'],math.sqrt(2.))
        self.assertAlmostEqual(result['difference_spatial_complex_RMS'],1.)
        self.assertAlmostEqual(result['normalized_L2'],1./math.sqrt(2.))
        self.assertTrue(result['screening_flag_5pct'])
        json.dumps(result,allow_nan=False)

    def test_zero_interface_norm_discloses_floor_and_empty_scope(self):
        xy=np.asarray([[0.,0.],[1.,0.]])
        zero=np.zeros(2,complex)
        result=f.interface_norms(zero,zero,xy,.1,np.asarray([True,True]))
        self.assertTrue(result['denominator_floor_used'])
        self.assertEqual(result['normalized_L2'],0.)
        self.assertFalse(result['screening_flag_5pct'])
        empty=f.interface_norms(zero,zero,xy,.1,np.asarray([False,False]))
        self.assertEqual(empty['status'],'not_run_no_samples')
        self.assertIsNone(empty['screening_flag_5pct'])

    def test_signed_decomposition_retains_negative_cancellation_cross_term(self):
        reference=np.asarray([3.+2j,3.+2j])
        intermediate=reference+(-1.-.5j)
        native=intermediate+(2.+1j)
        result=f.signed_decomposition(native,intermediate,reference,np.asarray([True,True]))
        row=result['faces'][0]
        self.assertAlmostEqual(row['components']['solution_through_estimator']['absolute_RMS'],math.sqrt(5.))
        self.assertAlmostEqual(row['components']['reference_sample_fit_bias']['absolute_RMS'],math.sqrt(1.25))
        self.assertAlmostEqual(row['total']['absolute_RMS'],math.sqrt(1.25))
        self.assertAlmostEqual(row['cross_term_2Re_mean_c1_conj_c2'],-5.)
        self.assertAlmostEqual(row['squared_RMS_identity_closure'],0.,places=12)
        self.assertLessEqual(row['maximum_absolute_vector_identity_closure'],1e-12)
        self.assertEqual(result['status'],'diagnostic_not_gated')
        json.dumps(result,allow_nan=False)

    def test_custom_shared_flux_labels_masks_multiple_faces_and_json_safety(self):
        reference=np.asarray([[1.+1j,2.+0j,3.+0j],[2.+1j,3.+0j,4.+0j]])
        intermediate=reference+1j;native=intermediate+2.
        native[:,1]=1e100  # This excluded column must not enter summary norms.
        labels=('native_fit_minus_native_shared_flux','native_shared_flux_minus_reference')
        result=f.signed_decomposition(native,intermediate,reference,np.asarray([True,False,True]),component_names=labels)
        self.assertEqual(len(result['faces']),2)
        for row in result['faces']:
            self.assertEqual(row['samples'],2)
            self.assertAlmostEqual(row['components'][labels[0]]['absolute_RMS'],2.)
            self.assertAlmostEqual(row['components'][labels[1]]['absolute_RMS'],1.)
            self.assertAlmostEqual(row['cross_term_2Re_mean_c1_conj_c2'],0.)
        json.dumps(result,allow_nan=False)

    def test_signed_decomposition_floor_and_empty_mask_are_explicit(self):
        reference=np.zeros(2,complex);intermediate=reference+1e-13;native=intermediate+2e-13
        result=f.signed_decomposition(native,intermediate,reference,np.asarray([True,True]))
        self.assertTrue(result['faces'][0]['denominator_floor_used'])
        self.assertAlmostEqual(result['faces'][0]['denominator'],1e-12)
        empty=f.signed_decomposition(native,intermediate,reference,np.asarray([False,False]))
        self.assertEqual(empty['status'],'not_run_no_samples')


if __name__=='__main__':unittest.main()
