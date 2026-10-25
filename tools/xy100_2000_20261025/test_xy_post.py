"""Pure contracts for physical-domain comparisons; no research fixture opens."""
import unittest
import numpy as np
import xy_post as post
import xy_math as geometry


class FixedDomainContracts(unittest.TestCase):
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

 def test_generic_half_face_flux_h_is_read_from_geometry(self):
  grid=np.asarray([[0,0,.025,0,1e-9],[.5,0,.025,0,1e-9]],float)
  g=dict(lookup=np.asarray([[[0,1]]]),h=.0005,h_mm=.5,iz=np.asarray([0,0]),dz=np.asarray([.00005]))
  contacts=np.asarray([],dtype=[('pad',int),('x_mm',float),('y_mm',float),('area_m2',float)])
  field=geometry.reconstruct_native_field(np.asarray([1.,.5],complex),grid,g,np.asarray([1.+.5j]*4),contacts,np.zeros(2),0j)
  self.assertTrue(np.allclose(field[:,0],500))


if __name__=='__main__':unittest.main()
