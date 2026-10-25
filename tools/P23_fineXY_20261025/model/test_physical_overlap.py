"""Synthetic scalar geometry contracts; source author did not run these."""
import unittest
from fractions import Fraction as F
import physical_overlap as overlap
class PhysicalOverlapContracts(unittest.TestCase):
 def test_full_synthetic_B0_union_is_partitioned_on_actual_fine_nodes(self):
  rows=['pad,i,j,area_m2']
  for p,(i0,j0)in enumerate(((15,15),(55,55),(55,15),(15,55))):
   for j in range(j0,j0+30):
    for i in range(i0,i0+30):rows.append('%d,%d,%d,2.5e-7'%(p,i,j))
  radius=F(1,40);h=F(1,2040);nodes=[]
  for j in range(102):
   for i in range(102):
    x=-radius+(F(i)+F(1,2))*h;y=-radius+(F(j)+F(1,2))*h
    if x*x+y*y<radius*radius:nodes.append((i,j))
  result=overlap.remesh_full_cell_union(('\n'.join(rows)+'\n').encode(),fine_nodes=nodes);proof=result['proof']
  self.assertTrue(proof['graph_coverage_verified_against_supplied_nodes']);self.assertFalse(proof['area_rescaled']);self.assertFalse(proof['coarse_indices_copied_to_fine']);self.assertEqual([p['physical_area_mm2']for p in proof['pads']],[225.]*4)
  self.assertEqual(sum((F(p['exact_area_m2']['numerator'],p['exact_area_m2']['denominator'])for p in proof['pads']),F(0)),F(900,1000000));self.assertTrue(any(F(p['exact_area_m2']['numerator'],p['exact_area_m2']['denominator'])<h*h for p in result['patches']))
 def test_exact_rational_overlap_and_boundary_touch(self):
  self.assertEqual(overlap.rectangle_intersection((F(0),F(1),F(0),F(1)),(F(1,2),F(2),F(0),F(1))),F(1,2));self.assertEqual(overlap.rectangle_intersection((F(0),F(1),F(0),F(1)),(F(1),F(2),F(0),F(1))),0)
 def test_fraction_exports_without_JSON_fraction_object(self):self.assertEqual(overlap.fraction_record(F(2,3)),dict(numerator=2,denominator=3))
 def test_nonfullface_or_duplicate_geometry_rejected(self):
  for payload in(b'pad,i,j,area_m2\n0,49,49,1e-7\n',b'pad,i,j,area_m2\n0,49,49,2.5e-7\n1,49,49,2.5e-7\n'):
   with self.assertRaises(ValueError):overlap.remesh_full_cell_union(payload)
 def test_wrong_graph_resolution_never_copies_indices(self):
  with self.assertRaises(ValueError):overlap.remesh_full_cell_union(b'pad,i,j,area_m2\n',100)
if __name__=='__main__':unittest.main()
