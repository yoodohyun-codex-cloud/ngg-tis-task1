"""Small pure physical quadrature contracts; root owns eventual execution."""
import math
import unittest
import numpy as np
import cem_compare as c
import physical_projector as p


class PhysicalComparisonContracts(unittest.TestCase):
 def test_target_requires_same_physical_planes_and_preserves_complex_difference(self):
  xy=np.asarray([[-12.5,-12.5],[12.5,-12.5],[-12.5,12.5],[12.5,12.5]])
  faces=np.asarray([0.,.0001,.0051,.0101,.015,.020,.0251]);z=(faces[:-1]+faces[1:])/2*1000
  a=dict(xy_mm=xy,z_eval_mm=z,phi_ref=np.ones((2,24),complex));b=dict(xy_mm=xy,z_eval_mm=z,phi_ref=np.full((2,24),1.1+0j))
  links=p.build_overlap(xy,25.,xy,25.)
  result=c.roi_potential_comparison(a,b,faces,faces,links,lambda:None)
  self.assertAlmostEqual(result['represented_volume_m3'],math.pi*.005**2*.005,places=17)
  self.assertAlmostEqual(result['rows'][0]['pairwise_cellconstant_potential_L2_V'],.1)
  self.assertFalse(result['rows'][0]['phase_or_gauge_fitted'])
  bad=faces.copy();bad[5]=.019
  badz=(bad[:-1]+bad[1:])/2*1000
  with self.assertRaises(ValueError):c.roi_potential_comparison(a,dict(b,z_eval_mm=badz),faces,bad,links,lambda:None)

 def test_fixed_physical_pad_and_edge_areas_are_not_point_count_rescaled(self):
  rectangles={'0':[-17.5,-2.5,-17.5,-2.5],'1':[2.5,17.5,2.5,17.5],'2':[2.5,17.5,-17.5,-2.5],'3':[-17.5,-2.5,2.5,17.5]}
  ranges=[(range(15,45),range(15,45)),(range(55,85),range(55,85)),(range(55,85),range(15,45)),(range(15,45),range(55,85))]
  xy=[];pad=[]
  for label,(xs,ys)in enumerate(ranges):
   for j in ys:
    for i in xs:xy.append([-25+(i+.5)*.5,-25+(j+.5)*.5]);pad.append(label)
  xy=np.asarray(xy);n=len(pad);J=np.ones((2,n),complex);z=1+.2j
  data=dict(contact_xy_mm=xy,contact_area_m2=np.full(n,.25e-6),contact_pad=np.asarray(pad),contact_xy_index=np.arange(n),xy_mm=xy,
   source_current=np.zeros((2,2),complex),source_ideal_voltage=.5*np.eye(2),contact_normal_J=J,contact_drop=z*J,layer_complex_power=np.zeros((2,4),complex))
  result=c.contact_metrics(data,.5,rectangles,z)
  for item in result['pad_area_proof']:
   self.assertAlmostEqual(item['actual_area_m2'],225e-6,places=15)
   self.assertAlmostEqual(item['edge_area_m2'],29e-6,places=15)
  self.assertAlmostEqual(result['basis'][0]['edge_J_RMS_P95_A_m2'],1/math.sqrt(2))
  changed=dict(data,contact_area_m2=data['contact_area_m2'].copy());changed['contact_area_m2'][0]*=1.001
  with self.assertRaises(ValueError):c.contact_metrics(changed,.5,rectangles,z)

 def test_available_electrical_screens_do_not_claim_unavailable_E(self):
  self.assertEqual(c.REVIEW_PERCENT['contact_J_RMS_max_A_m2'],5)
  self.assertEqual(c.REVIEW_PERCENT['edge_J_RMS_P95_A_m2'],5)
  self.assertEqual(c.REVIEW_PERCENT['source_power_W'],2)
  self.assertFalse(any('E_carrier' in k or 'TIS' in k for k in c.REVIEW_PERCENT))


if __name__=='__main__':unittest.main()
