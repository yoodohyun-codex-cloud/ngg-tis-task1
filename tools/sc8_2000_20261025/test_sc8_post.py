"""Pure contracts for physical-domain comparisons; no research fixture opens."""
import unittest
import numpy as np
import sc8_post as post
import sc8_math as geometry
import sc8_interfaces as interfaces


class FixedDomainContracts(unittest.TestCase):
 def test_conditional_selection_requires_scalar_pass_and_unresolved_common_two(self):
  def fixture(scalar_pass,native,fixed):
   return dict(adjacent_SC_checks=dict(all_passed=scalar_pass),independent_interface_diagnostics=dict(fine=dict(
    native_grid_masks=dict(common_QA=dict(status=native)),fixed_coarse_physical_masks=dict(common_QA=dict(status=fixed)))))
  good='all_numerical_flags_pass';hold='numerical_flags_failed'
  self.assertTrue(post.conditional_selection_matches(fixture(True,hold,good)))
  self.assertTrue(post.conditional_selection_matches(fixture(True,good,hold)))
  self.assertFalse(post.conditional_selection_matches(fixture(False,hold,hold)))
  self.assertFalse(post.conditional_selection_matches(fixture(True,good,good)))

 def test_contact_voltage_has_its_predeclared_five_percent_gate(self):
  e={k:1. for k in('contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V','source_power_W','contact_power_W','source_resistor_power_W','SC_power_W','skin_power_W')}
  e['layers_power_W']={n:1. for n in post.LAYERS}
  old={'statistics':{'target':{'E_carrier_RMS_V_m':{'mean':1.,'p10':1.}}},'electrical':e}
  changed=dict(e,contact_voltage_RMS_max_V=1.06)
  new=dict(old,electrical=changed)
  result=post.adjacent_checks(old,new)
  row=next(r for r in result['rows']if r['metric']=='contact_voltage_RMS_max_V')
  self.assertFalse(result['all_passed'])
  self.assertFalse(row['passed'])
  self.assertEqual(row['limit'],.05)

 def test_five_percent_is_unchanged_and_does_not_abort_on_failure(self):
  proof={'interfaces':[{'interface_depth_mm':.1,'regions':{'all':{'total_normal_current':{'normalized_L2':.16775}}}}]}
  r=post.numerical_qa(proof)
  self.assertEqual(r['status'],'numerical_flags_failed')
  self.assertEqual(r['rows'][0]['limit'],.05)
  self.assertEqual(proof['interfaces'][0]['regions']['all']['total_normal_current']['normalized_L2'],.16775)

 def test_physical_scope_comparison_does_not_use_fine_native_periphery(self):
  def proof(value):return {'interfaces':[{'interface_depth_mm':.1,'regions':{k:{'total_normal_current':{'normalized_L2':value}}for k in('all','interior','staircase_periphery')}}]}
  old={k:proof(.2)for k in('common_two_point','nearest_up_to_three_point')}
  fixed={k:proof(.1)for k in('common_two_point','nearest_up_to_three_point')}
  result=post.independent_comparison(old,fixed)
  self.assertEqual(len(result['rows']),6)
  self.assertTrue(all(r['comparison_interior_radius_mm']==23.75 for r in result['rows']))
  self.assertTrue(all(r['absolute_change']==-.1 for r in result['rows']))

 def test_all_thirteen_adjacency_limits_are_exact(self):
  e={k:1. for k in('contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V','source_power_W','contact_power_W','source_resistor_power_W','SC_power_W','skin_power_W')}
  e['layers_power_W']={n:1. for n in post.LAYERS}
  old={'statistics':{'target':{'E_carrier_RMS_V_m':{'mean':1.,'p10':1.}}},'electrical':e}
  result=post.adjacent_checks(old,old)
  self.assertEqual(len(result['rows']),13)
  self.assertEqual({r['metric']:r['limit']*100 for r in result['rows']},post.ADJACENCY_PERCENT)
  self.assertFalse(result['full_convergence_validated'])

 def test_unchanged_native_twenty_four_mm_mask_can_be_compared_explicitly(self):
  def proof():return {'interior_radius_mm':24.,'h_xy_mm':.5,'sc_cells':4,'interfaces':[{'interface_depth_mm':.1,'regions':{k:{'total_normal_current':{'normalized_L2':.1}}for k in('all','interior','staircase_periphery')}}]}
  proofs={k:proof()for k in('common_two_point','nearest_up_to_three_point')}
  fine={k:dict(v,sc_cells=8)for k,v in proofs.items()}
  result=post.independent_comparison(proofs,fine,24.)
  self.assertTrue(all(r['comparison_interior_radius_mm']==24. for r in result['rows']))
  self.assertFalse(result['full_convergence_validated'])
  with self.assertRaises(ValueError):post.independent_comparison(proofs,fine,23.75)

 def test_both_methods_keep_their_order_on_sc4_and_sc8(self):
  proofs=[]
  for count in(4,8):
   slab=interfaces.synthetic_layered_slab(count,h_xy_mm=.5)
   args=(slab['phi'],slab['grid'],slab['meta'],slab['gamma'])
   proofs.append(dict(common_two_point=interfaces.common_two_point_diagnostics(*args,interior_radius_mm=.5),
    nearest_up_to_three_point=interfaces.interface_diagnostics(*args,interior_radius_mm=.5)))
  result=post.independent_comparison(proofs[0],proofs[1],.5)
  common=[r for r in result['rows']if r['order']=='common_two_point']
  nearest=[r for r in result['rows']if r['order']=='nearest_up_to_three_point']
  self.assertEqual(len(common),9)
  self.assertEqual(len(nearest),9)
  self.assertTrue(all(r['same_fit_order']for r in result['rows']))
  self.assertTrue(all(r['coarse_fit_points']==r['fine_fit_points']=={'upper':2,'lower':2}for r in common))
  self.assertTrue(all(r['coarse_fit_points']==r['fine_fit_points']=={'upper':3,'lower':3}for r in nearest))
  self.assertFalse(result['full_convergence_validated'])

 def test_generic_half_face_flux_h_is_read_from_geometry(self):
  grid=np.asarray([[0,0,.025,0,1e-9],[.5,0,.025,0,1e-9]],float)
  g=dict(lookup=np.asarray([[[0,1]]]),h=.0005,h_mm=.5,iz=np.asarray([0,0]),dz=np.asarray([.00005]))
  contacts=np.asarray([],dtype=[('pad',int),('x_mm',float),('y_mm',float),('area_m2',float)])
  field=geometry.reconstruct_native_field(np.asarray([1.,.5],complex),grid,g,np.asarray([1.+.5j]*4),contacts,np.zeros(2),0j)
  self.assertTrue(np.allclose(field[:,0],500))


if __name__=='__main__':unittest.main()
