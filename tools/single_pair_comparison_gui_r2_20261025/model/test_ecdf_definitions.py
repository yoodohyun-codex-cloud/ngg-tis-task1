"""Deterministic ECDF boundary fixtures, no native input or source-time run."""
import math,unittest
import ecdf_definitions as ecdf
class ECDFBoundaryContracts(unittest.TestCase):
 def test_roundoff_in_normalization_can_cross_an_exact_CDF_step(self):
  cumulative=[.25,.5,.75,1.]
  self.assertEqual(ecdf.inverse_ecdf_index(cumulative,1.,.5),1)
  self.assertEqual(ecdf.inverse_ecdf_index(cumulative,math.nextafter(1.,math.inf),.5),2)
 def test_inverse_is_left_closed_without_epsilon_or_interpolation(self):
  self.assertEqual(ecdf.inverse_ecdf_index([1.,2.,4.],4.,.5),1)
  self.assertEqual(ecdf.inverse_ecdf_index([1.,2.,4.],4.,math.nextafter(.5,math.inf)),2)
 def test_invalid_or_zero_normalization_is_not_repaired(self):
  for denominator in (0.,float('nan'),float('inf')):
   with self.assertRaises(ValueError):ecdf.inverse_ecdf_index([1.],denominator,.5)
 def test_both_actual_numpy_producer_definitions_keep_threshold_evidence(self):
  import numpy as np
  values=np.asarray([0.,1.,2.,3.]);weights=np.asarray([0.,1.,1.,2.])
  full=ecdf.quantile(np,values,weights,.5,ecdf.CANONICAL);positive=ecdf.quantile(np,values,weights,.5,ecdf.POSITIVE_SUM)
  self.assertEqual(full['value'],2.);self.assertEqual(positive['value'],2.);self.assertEqual(full['zero_weight_rows_in_sort'],1);self.assertEqual(positive['zero_weight_rows_in_sort'],0);self.assertIn('threshold',full);self.assertIn('sorted_cumulative_total',positive)
if __name__=='__main__':unittest.main()
