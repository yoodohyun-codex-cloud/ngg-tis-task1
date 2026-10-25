"""Unrun pure scalar manufactured ellipse certificates; no files or arrays."""
import copy
import unittest
from unittest.mock import patch
from fractions import Fraction as F
import ellipse_contact as ellipse


class EllipseCertificateContracts(unittest.TestCase):
    def enclosed(self,value,interval):
        self.assertLessEqual(interval.lo,F(value));self.assertGreaterEqual(interval.hi,F(value))

    def test_full_and_axis_aligned_quarter_areas_follow_exact_analytic_area(self):
        shape=ellipse.make_ellipse(0,0,3,6,orientation='axis_x')
        full=ellipse.ellipse_rectangle_area(shape,(-4,4,-4,4))
        quarter=ellipse.ellipse_rectangle_area(shape,(0,4,0,4))
        self.enclosed(6,full['interval']);self.enclosed(F(3,2),quarter['interval'])
        self.assertLess(full['interval'].hi-full['interval'].lo,F(1,10**10))
        self.assertEqual(full['method'],'analytic_conic_primitive_with_outward_interval_certificate')

    def test_translated_rotated_halfplanes_and_quadrant_partition(self):
        shape=ellipse.make_ellipse(F(1),F(1),3,6)
        right=ellipse.ellipse_rectangle_area(shape,(1,5,-3,5))['interval']
        top=ellipse.ellipse_rectangle_area(shape,(-3,5,1,5))['interval']
        self.enclosed(3,right);self.enclosed(3,top)
        quadrants=[ellipse.ellipse_rectangle_area(shape,r)['interval'] for r in
                   ((-3,1,-3,1),(1,5,-3,1),(-3,1,1,5),(1,5,1,5))]
        self.enclosed(6,sum(quadrants,ellipse.Interval(0)))
        self.assertLessEqual(quadrants[0].lo,quadrants[3].hi)
        self.assertLessEqual(quadrants[3].lo,quadrants[0].hi)

    def test_inside_outside_and_boundary_touch_use_geometry_proofs(self):
        shape=ellipse.make_ellipse(0,0,3,6,orientation='axis_x')
        inside=ellipse.ellipse_rectangle_area(shape,(F(-1,10),F(1,10),F(-1,10),F(1,10)))
        outside=ellipse.ellipse_rectangle_area(shape,(4,5,4,5))
        touch=ellipse.ellipse_rectangle_area(shape,(3,4,-1,1))
        self.assertEqual(inside['method'],'whole_square_proved_inside')
        self.enclosed(F(1,25),inside['interval']);self.enclosed(0,outside['interval']);self.enclosed(0,touch['interval'])
        self.assertEqual(outside['interval'].hi,0)

    def test_preflight_preserves_exact_centres_and_blocks_bad_circle_or_quadrants(self):
        centres=[[-F(25,2),-F(25,2)],[F(25,2),F(25,2)],[F(25,2),-F(25,2)],[-F(25,2),F(25,2)]]
        original=copy.deepcopy(centres);receipt=ellipse.preflight(centres)
        self.assertTrue(receipt['passed']);self.assertEqual(centres,original)
        for centre,pad in zip(centres,receipt['pads']):
            self.assertEqual(pad['analytic_centroid_exact'],[dict(numerator=v.numerator,denominator=v.denominator) for v in centre])
            self.assertLess(pad['maximum_radius_upper_bound_mm'],25.)
            self.assertTrue(all(v>0 for v in pad['quadrant_axis_margins_mm']))
        bad=[[-20,-20],[20,20],[20,-20],[-20,20]]
        with self.assertRaises(ValueError):ellipse.preflight(bad)
        bad=copy.deepcopy(centres);bad[0][0]=F(25,2)
        with self.assertRaises(ValueError):ellipse.preflight(bad)

    def test_missing_graph_support_blocks_instead_of_trimming_or_rescaling(self):
        centres=[[-F(25,2),-F(25,2)],[F(25,2),F(25,2)],[F(25,2),-F(25,2)],[-F(25,2),F(25,2)]]
        with self.assertRaisesRegex(ValueError,'actual injected graph'):
            ellipse.contact_patches(centres,[])
        # A tiny unresolved positive interval cannot be omitted on an area
        # budget: that gives no bound on contact-current or voltage peaks.
        rectangle=(F(-15,2),F(-7),F(-15,2),F(-7))
        def manufactured_interval(shape,bounds,*args):
            return dict(interval=ellipse.Interval(0,F(1,10**30)) if tuple(bounds)==rectangle else ellipse.Interval(0),
                        method='manufactured_unresolved_support_guard_fixture')
        with patch.object(ellipse,'ellipse_rectangle_area',side_effect=manufactured_interval):
            with self.assertRaisesRegex(ValueError,'Unresolved potentially positive ellipse contact support'):
                ellipse.contact_patches(centres,[(35,35)])

    def test_exact_interval_sqrt_and_series_remainder_enclose_known_values(self):
        value=ellipse._sqrt_point(F(2))
        self.assertLessEqual(value.lo*value.lo,2);self.assertGreaterEqual(value.hi*value.hi,2)
        zero=ellipse._atan_point(F(0),lambda:None,None)
        self.enclosed(0,zero)
        quarter=ellipse._atan_point(F(1),lambda:None,None)
        pi=ellipse._pi();self.assertLessEqual(quarter.lo,pi.hi/4);self.assertGreaterEqual(quarter.hi,pi.lo/4)


if __name__=='__main__':unittest.main()
