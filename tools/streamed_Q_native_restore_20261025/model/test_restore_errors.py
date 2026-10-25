"""Prospective tiny fixtures; scientific imports occur only when root runs tests."""
import math,unittest
from unittest.mock import patch
import restore_errors as errors

def fixture(np,n=5):
 grid=np.zeros((n,5),dtype=np.float64);grid[:,0]=np.arange(n);grid[:,2]=np.arange(n)+.25;grid[:,3]=np.arange(n)%4;grid[:,4]=(np.arange(n)+1)*1e-9
 old=np.zeros((n,3),dtype=np.complex128);old[:,0]=1+2j
 fractions=dict(total=1.,target=.25,surface_0_5=.2,subsurface_5_10=.2,remaining=.6,off_target=.75)
 weights={k:grid[:,4]*fractions[k]for k in errors.REGIONS}
 return grid,old,weights
class RestoreErrorFixtures(unittest.TestCase):
 def test_identical_fields_pass_both_gates_and_preserve_inputs(self):
  import numpy as np
  grid,old,w=fixture(np);before=old.copy();result=errors.compare_fields(np,old.copy(),old,grid,w,lambda:None)
  self.assertTrue(result['summary']['passed']);self.assertTrue(np.array_equal(result['norm_delta_V_m'],np.zeros(5)));self.assertTrue(np.array_equal(old,before))
  self.assertEqual(set(result['summary']['regions']),set(errors.REGIONS));self.assertEqual(result['summary']['maximum_component_absolute_delta_V_m']['exact_float_tied_cells'],5)
 def test_component_failure_is_independent_of_large_vector_reference(self):
  import numpy as np
  grid,old,w=fixture(np,2);old[:]=0;old[:,1]=1000.;new=old.copy();new[0,0]=1e-7
  s=errors.compare_fields(np,new,old,grid,w,lambda:None)['summary']
  self.assertFalse(s['component_passed']);self.assertTrue(s['vector_passed']);self.assertEqual(s['component_failures'],1);self.assertEqual(s['maximum_component_absolute_delta_V_m']['component'],'x')
 def test_vector_failure_can_occur_when_all_components_pass(self):
  import numpy as np
  grid,old,w=fixture(np,2);old[:]=0;new=old.copy();new[1,:]=7e-9
  s=errors.compare_fields(np,new,old,grid,w,lambda:None)['summary']
  self.assertTrue(s['component_passed']);self.assertFalse(s['vector_passed']);self.assertEqual(s['vector_failure_cells'],1);self.assertEqual(s['maximum_vector_tolerance_ratio']['native_cell_index'],1)
 def test_fractional_volume_L2_matches_independent_small_formula(self):
  import numpy as np
  grid,old,w=fixture(np,2);old[:]=0;old[:,0]=[1.,2.];new=old.copy();new[:,2]=[1e-9,2e-9]
  s=errors.compare_fields(np,new,old,grid,w,lambda:None)['summary'];r=s['regions']['target'];v=w['target']
  expected=math.sqrt(float(v[0])*1e-18+float(v[1])*4e-18);reference=math.sqrt(float(v[0])+float(v[1])*4.)
  self.assertAlmostEqual(r['absolute_vector_L2_V_m_sqrt_m3'],expected,delta=expected*1e-13);self.assertAlmostEqual(r['relative_vector_L2'],expected/reference,delta=1e-22)
 def test_streaming_ROIs_are_outer_loop_and_ties_use_first_native_cell(self):
  import numpy as np
  grid,old,w=fixture(np);calls=[]
  def provider(name,a,b):calls.append((name,a,b));return w[name][a:b]
  with patch.object(errors,'CHUNK_CELLS',2):s=errors.compare_fields(np,old.copy(),old,grid,{'regions':errors.REGIONS,'chunk':provider},lambda:None)['summary']
  self.assertEqual([x[0]for x in calls],[name for name in errors.REGIONS for _ in range(3)])
  self.assertEqual(s['maximum_component_absolute_delta_V_m']['native_cell_index'],0);self.assertEqual(s['maximum_component_absolute_delta_V_m']['exact_float_tied_cells'],5)
 def test_zero_reference_floor_and_missing_ROIs_are_explicit(self):
  import numpy as np
  grid,old,w=fixture(np,2);old[:]=0;new=old.copy();new[:,0]=1e-9
  result=errors.compare_fields(np,new,old,grid,None,lambda:None);s=result['summary'];g=s['global_volume_L2']
  self.assertTrue(s['pointwise_passed']);self.assertFalse(s['passed']);self.assertFalse(s['ROI_weights_available']);self.assertTrue(g['relative_floor_dominates']);self.assertAlmostEqual(g['relative_vector_L2'],.1)
 def test_invalid_weights_grid_or_nonfinite_fields_reject_without_partial_PASS(self):
  import numpy as np
  grid,old,w=fixture(np,2)
  for mutation in('weights','grid','field'):
   g=grid.copy();new=old.copy();weights={k:v.copy()for k,v in w.items()}
   if mutation=='weights':weights['target'][0]=2*g[0,4]
   elif mutation=='grid':g[0,3]=.5
   else:new[0,0]=complex(float('nan'),0.)
   with self.assertRaises(ValueError):errors.compare_fields(np,new,old,g,weights,lambda:None)
 def test_two_carrier_bounds_match_small_analytic_values_without_AM_scan(self):
  import numpy as np
  grid,old,w=fixture(np,2);d0=np.array([3.,0.],dtype=np.float64);d1=np.array([4.,2.],dtype=np.float64)
  s=errors.combine_carrier_bounds(np,d0,d1,grid,w,lambda:None);g=s['global_bounds']
  self.assertEqual(g['AM']['maximum_upper_bound_V_m']['value'],8.);self.assertAlmostEqual(g['RMS']['maximum_upper_bound_V_m']['value'],5/math.sqrt(2.));self.assertFalse(s['angular_search_performed']);self.assertFalse(s['actual_AM_error_measured']);self.assertFalse(s['acceptance_gate_applied'])
 def test_conditional_bounds_reject_negative_errors(self):
  import numpy as np
  grid,old,w=fixture(np,2)
  with self.assertRaises(ValueError):errors.combine_carrier_bounds(np,np.array([-1.,0.]),np.zeros(2),grid,w,lambda:None)
 def test_expired_deadline_rejects_before_any_array_inspection(self):
  with self.assertRaises(TimeoutError):errors.compare_fields(None,None,None,None,None,lambda:None,0.)
  with self.assertRaises(TimeoutError):errors.combine_carrier_bounds(None,None,None,None,None,lambda:None,0.)
if __name__=='__main__':unittest.main()
