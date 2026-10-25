"""Root-owned small contracts only. No test invokes a linear/PDE solve."""
import math,unittest
import grade_kernel as g


class ScalarKernelContracts(unittest.TestCase):
 def test_exact_self_log_integral(self):
  L=.002;h=1e-9;a=-.0005;b=a+h
  actual=g.log_rectangle(a,b,a,b,L)
  width=b-a;expected=width*width*(math.log(width/L)-1.5)
  self.assertLess(abs(actual-expected)/abs(expected),1e-12)

 def test_periodic_seam_and_high_precision_agree(self):
  L=.002;a=-L/2;b=a+1e-9;c=L/2-1e-9;d=L/2
  counts={'Decimal_F_fallback_pairs':0};actual=g.log_rectangle(a,b,c,d,L,-1,counts)
  expected=g._decimal_log_rectangle(a,b,c,d,L,-1,70)
  self.assertEqual(counts['Decimal_F_fallback_pairs'],1)
  self.assertLess(abs(actual-expected)/max(abs(expected),1e-300),1e-13)

 def test_near_unequal_rectangle_uses_same_formula_at_two_precisions(self):
  values=(-.0005,-.0005+1e-10,-.00049,-.00045,.002)
  a=g._decimal_log_rectangle(*values,0,50);b=g._decimal_log_rectangle(*values,0,70)
  self.assertLess(abs(a-b)/max(abs(b),1e-300),1e-13)

 def test_correction_tail_bound_is_positive_and_decreases(self):
  a=g.correction_tail_bound(.002,.0001,32);b=g.correction_tail_bound(.002,.0001,64)
  self.assertGreater(a,b);self.assertGreater(b,0.)


class SmallGeometryAndOperatorContracts(unittest.TestCase):
 def test_nested_mesh_keeps_nodes_and_actual_edges(self):
  import numpy as np
  ell=abs(g.cv(g.EXPECTED_GAMMA)*g.cv(g.EXPECTED_Z));coarse,_=g.graded_edges(np,128,.001,ell);fine,_=g.graded_edges(np,256,.001,ell);finest,_=g.graded_edges(np,512,.001,ell)
  np.testing.assert_array_equal(coarse,fine[::2]);np.testing.assert_array_equal(fine,finest[::2])
  self.assertEqual(coarse[0],-.0005);self.assertEqual(coarse[-1],.0005)
  self.assertTrue(np.all(np.diff(finest)>0));self.assertTrue(np.array_equal(finest,-finest[::-1]))

 def test_full_period_kernel_row_sum_and_wrap_without_any_solve(self):
  import numpy as np
  L=.002;t=.0001;edges=np.linspace(-L/2,L/2,5)
  G,proof=g.assemble_geometry(np,edges,L,t,32,lambda:None,None)
  expected=t*np.diff(edges)
  self.assertLess(float(np.max(abs(G.sum(axis=1)-expected)/expected)),g.CONTRACTS['constant_relative'])
  self.assertTrue(proof['symmetry_passed']);self.assertTrue(proof['PSD_passed']);self.assertFalse(proof['eigenvalues_clipped'])
  self.assertEqual(proof['actual_3D_cells'],0)

 def test_non_equipotential_MMS_is_full_period_only(self):
  import numpy as np
  L=.002;t=.0001;gamma=g.cv(g.EXPECTED_GAMMA);zA=g.cv(g.EXPECTED_Z)
  rhs,mean,variance,total,meta=g._forcing(np,'MMS-mode1',np.linspace(-L/2,L/2,9),L,t,gamma,zA)
  self.assertFalse(meta['equipotential']);self.assertTrue(meta['manufactured_non_equipotential_forcing_only'])
  self.assertTrue(np.isfinite(rhs).all());self.assertTrue(np.all(variance>=0));self.assertGreater(total,0)
  with self.assertRaises(ValueError):g._forcing(np,'MMS-mode1',np.linspace(-.0005,.0005,9),L,t,gamma,zA)


class OperatorAccuracyGateContracts(unittest.TestCase):
 def test_predeclared_gate_rejects_excess_projected_error(self):
  def fixture(error):
   return {(512,32):{'metadata':{'case_id':'verification-P512-Q32','forcing_rows':[{'forcing':{'name':name},'projected_q_nonconstant_relative_L2':error,'true_continuous_q_relative_L2':1e-6,'projection_variance_relative_L2':1e-7}for name in('MMS-mode1','MMS-mode4')]}}}
  self.assertTrue(g.operator_accuracy_review(fixture(.004))['all_passed'])
  self.assertFalse(g.operator_accuracy_review(fixture(.006))['all_passed'])
  self.assertEqual(g.OPERATOR_ACCURACY_GATE['projected_q_nonconstant_relative_L2_limit'],.005)

 def test_MMS_accuracy_denominator_excludes_DC_component(self):
  import numpy as np
  from unittest.mock import patch
  L=.002;t=.0001;edges=np.linspace(-L/2,L/2,9);gamma=g.cv(g.EXPECTED_GAMMA);zA=g.cv(g.EXPECTED_Z)
  original=g._forcing(np,'MMS-mode1',edges,L,t,gamma,zA)[4]
  large=dict(g.MMS_COEFFICIENTS,q0={'real':100.,'imaginary':20.})
  with patch.object(g,'MMS_COEFFICIENTS',large):changed=g._forcing(np,'MMS-mode1',edges,L,t,gamma,zA)[4]
  self.assertEqual(original['exact_nonconstant_q_squared_integral_A2_per_m3'],changed['exact_nonconstant_q_squared_integral_A2_per_m3'])


class SerializationContracts(unittest.TestCase):
 def test_scientific_scalars_are_losslessly_normalized(self):
  import json,numpy as np
  value={'flag':np.bool_(True),'count':np.int64(3),'number':np.float64(.125)}
  actual=json.loads(g.encoded(value));self.assertIs(actual['flag'],True);self.assertEqual(actual['count'],3);self.assertEqual(actual['number'],.125)

 def test_bad_metadata_does_not_open_a_file(self):
  from pathlib import Path
  from unittest.mock import patch
  import numpy as np
  for value in(float('nan'),float('inf'),np.asarray([1,2]),1+2j):
   with self.subTest(type=type(value).__name__),patch.object(Path,'open',side_effect=AssertionError('Do not open for bad metadata')):
    with self.assertRaises((ValueError,TypeError)):g.new_json(Path('/dev/shm/unused-graded-invalid.json'),{'v':value})


if __name__=='__main__':unittest.main()
