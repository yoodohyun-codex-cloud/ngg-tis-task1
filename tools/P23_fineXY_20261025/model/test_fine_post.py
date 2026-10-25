"""Unrun scalar projection/accounting test SOURCE; no arrays or dataset reads."""
import math
import unittest
import fine_post as post


def records():
    return [dict(candidate_id=cid+'-'+grid,physical_geometry_id=cid,grid_variant=grid,
                 metric_evaluations=1,candidate_adopted=False,
                 angular_work=dict(full_field_evaluations=1 if grid=='XY102-Z97' else 0,
                                   SC4_only_evaluations=1 if grid=='XY100-Z97' else 0,
                                   repeated_original_bulk_angular_evaluations=0))
            for grid in ('XY102-Z97','XY100-Z97') for cid in (post.B0,post.P23)]


class FinePostContracts(unittest.TestCase):
    def test_physical_volume_pairwise_norm_retains_cancelled_fine_variation(self):
        # Coarse=0, fine=(+1,-1), equal overlap volumes. A coarse-cell average
        # would give zero error; the primary sum of squared differences is 2.
        result=post.projection_summary(2.,0.,2.,2.)
        self.assertEqual(result['pairwise_primary_absolute_L2'],1.)
        self.assertEqual(result['fine_spatial_norm'],1.)
        self.assertTrue(result['denominator_floor_used'])
        self.assertEqual(result['projected_average_secondary']['status'],'not_run')

    def test_complex_vector_components_contribute_before_spatial_reduction(self):
        # Independent component errors: (1+i,2,0) gives squared vector norm 6.
        components=[1.+1j,2.,0.]
        square=sum(abs(v)**2 for v in components)
        result=post.projection_summary(.25,0.,square*.25,square*.25)
        self.assertAlmostEqual(result['pairwise_primary_absolute_L2'],math.sqrt(6.))

    def test_volume_weighting_and_zero_overlap_are_explicit(self):
        # Volume .75 at difference0 and .25 at difference2 => RMS difference1.
        result=post.projection_summary(1.,4.,5.,.75*0.+.25*4.)
        self.assertEqual(result['pairwise_primary_absolute_L2'],1.)
        self.assertEqual(result['pairwise_primary_normalized_L2'],.5)
        self.assertFalse(result['automatic_convergence_gate_applied'])
        self.assertEqual(post.projection_summary(0.,0.,0.,0.)['status'],'not_run_no_common_weighted_volume')
        with self.assertRaises(ValueError):post.projection_summary(1.,1.,1.,-1.)

    def test_grid_variant_does_not_become_new_physical_geometry_or_extra_rhs(self):
        result=post.finite_accounting(records())
        self.assertEqual(result['metric_evaluations'],4)
        self.assertEqual(result['new_fine_driven_RHS'],3)
        self.assertEqual(result['reused_fine_B0_2000_RHS'],1)
        self.assertEqual(result['new_coarse_driven_RHS'],0)
        self.assertEqual(result['original_coarse101_angular_evaluations_repeated'],0)
        self.assertEqual(result['full_angular_evaluations'],2)
        self.assertEqual(result['SC4_only_angular_evaluations'],2)
        self.assertEqual(result['duplicate_full_coarse_scalar_archives'],0)
        bad=records();bad[0]['metric_evaluations']=True
        with self.assertRaises(ValueError):post.finite_accounting(bad)
        bad=records();bad[2]['angular_work']['repeated_original_bulk_angular_evaluations']=1
        with self.assertRaises(ValueError):post.finite_accounting(bad)
        bad=records();bad[0]['physical_geometry_id']='new-smoothed-P23'
        with self.assertRaises(ValueError):post.finite_accounting(bad)

    def test_prospective_error_limits_and_old_failures_never_clear(self):
        result=post.relative_diagnostic(100.,102.,.01,'V/m')
        self.assertEqual(result['relative_difference'],.02)
        self.assertFalse(result['passed'])
        self.assertTrue(post.relative_diagnostic(100.,104.,.05,'A/m2')['passed'])
        self.assertFalse(post.relative_diagnostic(100.,104.,.02,'W')['passed'])
        self.assertEqual(result['relative_limit'],.01)

    def test_fixed_scalar_archive_contract_is_four_arrays(self):
        self.assertEqual(post.SCALARS,('AM_max2074','carrier_RMS','Jtotal_vector_RMS','AM_direction_index'))
        self.assertEqual(len(post.SCALARS),4)

    def test_actual_saved_rhs_proofs_block_a_fourth_fine_solve(self):
        manifest={group:{name:{frequency:dict(proof=dict(actual_new_RHS=(1 if group=='fine' and (name!='B0' or frequency!='2000') else 0)))
                              for frequency in ('2000','2010')} for name in ('B0','P23')}
                  for group in ('fine','coarse_SC4')}
        self.assertEqual(post.raw_accounting(manifest)['actual_new_fine_driven_RHS'],3)
        manifest['fine']['B0']['2000']['proof']['actual_new_RHS']=1
        with self.assertRaises(ValueError):post.raw_accounting(manifest)


if __name__=='__main__':unittest.main()
