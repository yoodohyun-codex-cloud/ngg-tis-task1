"""Pure synthetic test SOURCE; eventual execution belongs to the finite owner."""
import json
import math
import unittest
import numpy as np
import physical_projector as p


def full_square_centres(n):
    h=50./n
    return np.asarray([[-25.+(i+.5)*h,-25.+(j+.5)*h]for i in range(n)for j in range(n)])


class PhysicalProjectorTests(unittest.TestCase):
    def test_nested_rectangle_area_conservation_and_input_order_indices(self):
        coarse=np.asarray([[-24.5,-24.5]])
        fine=np.asarray([[-24.25,-24.25],[-24.75,-24.75],[-24.25,-24.75],[-24.75,-24.25]])
        links=p.build_overlap(coarse,1.,fine,.5)
        self.assertEqual(len(links['area_m2']),4)
        self.assertEqual(set(links['fine_index'].tolist()),{0,1,2,3})
        np.testing.assert_allclose(links['area_m2'],.25e-6,rtol=0,atol=1e-18)
        np.testing.assert_allclose(links['coarse_coverage_area_m2'],[1e-6],rtol=0,atol=1e-18)
        np.testing.assert_allclose(links['fine_coverage_area_m2'],.25e-6,rtol=0,atol=1e-18)
        self.assertAlmostEqual(links['summary']['common_area_m2'],1e-6,places=16)
        self.assertEqual(links['summary']['coarse']['cells_with_unmatched_area'],0)
        self.assertEqual(links['summary']['fine']['cells_with_unmatched_area'],0)
        json.dumps(links['summary'],allow_nan=False)

    def test_non_nested_full_squares_conserve_same_physical_domain(self):
        # Only 25 and 36 cells; neither grid's interior lines nest in the other.
        links=p.build_overlap(full_square_centres(5),10.,full_square_centres(6),50./6.)
        self.assertAlmostEqual(links['summary']['common_area_m2'],.0025,places=14)
        np.testing.assert_allclose(links['coarse_coverage_area_m2'],100.e-6,rtol=0,atol=1e-17)
        np.testing.assert_allclose(links['fine_coverage_area_m2'],(50./6.)**2*1e-6,rtol=0,atol=1e-17)
        self.assertEqual(links['summary']['coarse']['cells_with_unmatched_area'],0)
        self.assertEqual(links['summary']['fine']['cells_with_unmatched_area'],0)

    def test_partial_coverage_records_unmatched_area_without_renormalizing_domain(self):
        coarse=np.asarray([[-24.5,-24.5]])
        fine=np.asarray([[-24.75,-24.75],[-24.75,-24.25]])
        links=p.build_overlap(coarse,1.,fine,.5)
        self.assertAlmostEqual(links['summary']['common_area_m2'],.5e-6,places=16)
        self.assertAlmostEqual(links['summary']['coarse']['unmatched_area_m2'],.5e-6,places=16)
        self.assertEqual(links['summary']['coarse']['partially_covered_cells'],1)
        self.assertEqual(links['summary']['fine']['cells_with_unmatched_area'],0)

    def test_touching_boundaries_have_zero_overlap_and_both_domains_unmatched(self):
        coarse=np.asarray([[-24.5,-24.5]])
        fine=np.asarray([[-23.75,-24.75]])  # touches coarse x=-24 face only
        links=p.build_overlap(coarse,1.,fine,.5)
        self.assertEqual(len(links['area_m2']),0)
        self.assertEqual(links['rectangle_mm'].shape,(0,4))
        self.assertEqual(links['summary']['coarse']['cells_without_overlap'],1)
        self.assertEqual(links['summary']['fine']['cells_without_overlap'],1)
        result=p.compare_piecewise(np.asarray([1.]),np.asarray([1.]),links)
        self.assertEqual(result['status'],'not_run_no_common_weighted_area')

    def test_canonical_coordinates_are_validated_and_duplicate_cells_rejected(self):
        valid=np.asarray([[-24.5,-24.5]])
        for invalid,h in((np.asarray([[-24.6,-24.5]]),1.),
                          (np.asarray([[-24.5,-24.5],[-24.5,-24.5]]),1.),
                          (valid,.7)):
            with self.subTest(spacing=h),self.assertRaises(ValueError):
                p.build_overlap(invalid,h,valid,1.)

    def test_constant_complex_field_has_zero_both_comparison_errors(self):
        coarse=np.asarray([[-24.5,-24.5]])
        fine=np.asarray([[-24.75,-24.75],[-24.75,-24.25],[-24.25,-24.75],[-24.25,-24.25]])
        links=p.build_overlap(coarse,1.,fine,.5)
        result=p.compare_piecewise(np.asarray([3.+2j]),np.full(4,3.+2j),links)
        self.assertAlmostEqual(result['coarse_spatial_complex_RMS'],math.sqrt(13.))
        self.assertAlmostEqual(result['pairwise_primary']['absolute_L2'],0.)
        self.assertAlmostEqual(result['projected_coarse_average_secondary']['absolute_L2'],0.)
        self.assertFalse(result['automatic_gate_applied'])
        json.dumps(result,allow_nan=False)

    def test_coarse_projection_can_hide_fine_variation_pairwise_remains_primary(self):
        coarse=np.asarray([[-24.5,-24.5]])
        fine=np.asarray([[-24.75,-24.75],[-24.75,-24.25],[-24.25,-24.75],[-24.25,-24.25]])
        links=p.build_overlap(coarse,1.,fine,.5)
        result=p.compare_piecewise(np.asarray([0j]),np.asarray([1.,-1.,1.,-1.]),links)
        self.assertAlmostEqual(result['pairwise_primary']['absolute_L2'],1.)
        self.assertAlmostEqual(result['projected_coarse_average_secondary']['absolute_L2'],0.)
        self.assertAlmostEqual(result['within_coarse_fine_variation_squared'],1.)
        self.assertTrue(result['denominator_floor_used'])

    def test_dimensionless_link_densities_preserve_explicit_weighted_area(self):
        coarse=np.asarray([[-24.5,-24.5]])
        fine=np.asarray([[-24.75,-24.75],[-24.75,-24.25],[-24.25,-24.75],[-24.25,-24.25]])
        links=p.build_overlap(coarse,1.,fine,.5)
        result=p.compare_piecewise(np.asarray([1.]),np.asarray([1.,2.,3.,4.]),links,
                                   weights=np.asarray([1.,0.,0.,0.]))
        self.assertAlmostEqual(result['weighted_area_m2'],.25e-6,places=16)
        self.assertAlmostEqual(result['pairwise_primary']['absolute_L2'],0.)
        self.assertEqual(result['contributing_links'],1)

    def test_full_circle_quadrants_halves_and_axis_symmetry_in_square_metres(self):
        r=5.;full=math.pi*r*r*1e-6
        self.assertAlmostEqual(p.analyticdisk_rect_area([-r,r,-r,r],r),full,places=15)
        self.assertAlmostEqual(p.analyticdisk_rect_area([0.,r,0.,r],r),full/4.,places=15)
        self.assertAlmostEqual(p.analyticdisk_rect_area([-r,r,0.,r],r),full/2.,places=15)
        a=p.analyticdisk_rect_area([1.,4.,2.,5.],r)
        self.assertAlmostEqual(a,p.analyticdisk_rect_area([-4.,-1.,2.,5.],r),places=15)
        self.assertAlmostEqual(a,p.analyticdisk_rect_area([2.,5.,1.,4.],r),places=15)
        self.assertAlmostEqual(p.analyticdisk_rect_area([-1.,1.,-1.,1.],r),4.e-6,places=15)
        self.assertEqual(p.analyticdisk_rect_area([6.,7.,6.,7.],r),0.)

    def test_disk_rectangle_vectorized_partition_adds_to_full_disk_area(self):
        rectangles=np.asarray([[-5.,0.,-5.,0.],[-5.,0.,0.,5.],[0.,5.,-5.,0.],[0.,5.,0.,5.]])
        areas=p.analyticdisk_rect_area(rectangles,5.)
        self.assertEqual(areas.shape,(4,))
        self.assertAlmostEqual(float(np.sum(areas)),math.pi*25.e-6,places=15)
        np.testing.assert_allclose(areas,math.pi*25.e-6/4.,rtol=0,atol=1e-15)


if __name__=='__main__':unittest.main()
