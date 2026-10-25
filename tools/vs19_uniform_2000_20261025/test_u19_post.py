"""Pure contracts for physical-domain comparisons; no research fixture opens."""
import unittest
import numpy as np
import u19_post as post
import u19_math as geometry
import u19_interfaces as interfaces


class FixedDomainContracts(unittest.TestCase):
 def test_completed_comparator_is_not_root_admission(self):
  summary=dict(case_id=post.COARSE_CASE,actual_new_RHS=2,actual_new_native_conditions=1,frequency_Hz=2000,scenarios={'SC8':{}})
  self.assertTrue(post.conditional_selection_matches(summary))
  self.assertFalse(post.conditional_selection_matches(dict(summary,case_id='not_the_comparator')))

 def test_positive_MMS_and_root_admission_are_both_required(self):
  spec={'synthetic_spec':True}
  review={'candidate':'U19','true_continuum_error_nonregression':True,'physical_error_improvement_review':True}
  summary={'spec':spec,'analytic_contracts':{'passed':True},'predeclared_native_review':[review]}
  admission=dict(schema='task1-u19-native-root-admission-v1',status='admitted_native_diagnostic',candidate='U19',root_review_positive=True,automatic_native_admission=False,candidate_adopted=False,new_native_conditions=1,maximum_native_RHS=2,decision_basis='Synthetic unit-test decision only',mms_result_commit='a'*40,sc8_result_commit='b'*40)
  self.assertEqual(post.validate_admission(spec,summary,admission,'c'*40),review)
  with self.assertRaises(ValueError):post.validate_admission(spec,summary,dict(admission,root_review_positive=False),'c'*40)
  failed=dict(summary,predeclared_native_review=[dict(review,true_continuum_error_nonregression=False)])
  with self.assertRaises(ValueError):post.validate_admission(spec,failed,admission,'c'*40)


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
  def proof():return {'interior_radius_mm':24.,'h_xy_mm':.5,'sc_cells':8,'interfaces':[{'interface_depth_mm':.1,'regions':{k:{'total_normal_current':{'normalized_L2':.1}}for k in('all','interior','staircase_periphery')}}]}
  proofs={k:proof()for k in('common_two_point','nearest_up_to_three_point')}
  fine={k:dict(v,sc_cells=8)for k,v in proofs.items()}
  result=post.independent_comparison(proofs,fine,24.)
  self.assertTrue(all(r['comparison_interior_radius_mm']==24. for r in result['rows']))
  self.assertFalse(result['full_convergence_validated'])
  with self.assertRaises(ValueError):post.independent_comparison(proofs,fine,23.75)

 def test_both_methods_keep_order_on_distinct_VS18_and_VS19_analytic_slabs(self):
  proofs=[]
  boundaries=np.asarray([0.,.1,5.1,10.1,25.1]);gamma=np.asarray([.002+.01j,.2+.002j,.04+.0002j,.3+.02j])
  current=1./sum((boundaries[i+1]-boundaries[i])/1000/gamma[i]for i in range(4))
  for vs in(18,19):
   counts=[8,vs,3,4]
   faces=np.concatenate([np.linspace(boundaries[i],boundaries[i+1],counts[i]+1)[:-1]for i in range(4)]+[boundaries[-1:]])
   z=(faces[:-1]+faces[1:])/2;layers=np.repeat(np.arange(4),counts);axis=(np.arange(4)-1.5)*.5
   xx,yy=np.meshgrid(axis,axis,indexing='xy');xy=np.column_stack([xx.ravel(),yy.ravel()]);grid=[];potential=[]
   for depth,layer in zip(z,layers):
    integral=sum((boundaries[i+1]-boundaries[i])/1000/gamma[i]for i in range(layer))+(depth-boundaries[layer])/1000/gamma[layer]
    for x,y in xy:
     grid.append([x,y,depth,layer,1.]);potential.append(1-current*integral+(.3+.2j)*x/1000+(-.4+.1j)*y/1000)
   meta=dict(sc_cells=8,bulk_layer_counts=[vs,3,4],z_faces_mm=faces.tolist(),h_xy_mm=.5,radius_mm=2.)
   args=(np.asarray(potential),np.asarray(grid),meta,gamma)
   proofs.append(dict(common_two_point=interfaces.common_two_point_diagnostics(*args,interior_radius_mm=.5),nearest_up_to_three_point=interfaces.interface_diagnostics(*args,interior_radius_mm=.5)))
  result=post.independent_comparison(proofs[0],proofs[1],.5)
  self.assertTrue(all(r['same_fit_order']for r in result['rows']))
  self.assertTrue(all(r['coarse_passed']and r['fine_passed']for r in result['rows']))
  for r in result['rows']:
   points=2 if r['order']=='common_two_point'else 3
   self.assertEqual(r['coarse_fit_points'],{'upper':points,'lower':points})
   self.assertEqual(r['coarse_fit_points'],r['fine_fit_points'])
  self.assertFalse(result['full_convergence_validated'])

 def test_generic_half_face_flux_h_is_read_from_geometry(self):
  grid=np.asarray([[0,0,.025,0,1e-9],[.5,0,.025,0,1e-9]],float)
  g=dict(lookup=np.asarray([[[0,1]]]),h=.0005,h_mm=.5,iz=np.asarray([0,0]),dz=np.asarray([.00005]))
  contacts=np.asarray([],dtype=[('pad',int),('x_mm',float),('y_mm',float),('area_m2',float)])
  field=geometry.reconstruct_native_field(np.asarray([1.,.5],complex),grid,g,np.asarray([1.+.5j]*4),contacts,np.zeros(2),0j)
  self.assertTrue(np.allclose(field[:,0],500))


if __name__=='__main__':unittest.main()
