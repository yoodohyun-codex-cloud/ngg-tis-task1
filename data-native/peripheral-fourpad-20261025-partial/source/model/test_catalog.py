"""Small predeclared topology/orbit contracts; no actualmask generation."""
import unittest
import catalog as c
class RecipeContracts(unittest.TestCase):
 def test_pair_is_never_split_and_missing_singleton_blocks(self):
  with self.assertRaises(c.RecipeBlocker):c.select_ordered_orbits([(c.Fraction(4),((0,1),(1,0)))],1)
 def test_fixed_parity_skip_records_pair_before_later_singleton(self):
  selected,taken,skipped=c.select_ordered_orbits([(c.Fraction(4),((0,1),(1,0))),(c.Fraction(3),((1,1),))],1)
  self.assertEqual(selected,{(1,1)});self.assertEqual(len(skipped),1);self.assertEqual(skipped[0]['radius_squared_exact'],[4,1])
 def test_exact_prefix_stops_without_extra_cells(self):
  selected,taken,skipped=c.select_ordered_orbits([(c.Fraction(4),((0,1),(1,0))),(c.Fraction(3),((1,1),))],2)
  self.assertEqual(selected,{(0,1),(1,0)});self.assertEqual(skipped,[])
 def test_four_neighbor_connectivity_rejects_corner_bridge(self):
  self.assertFalse(c._connected({(0,0),(1,1)}));self.assertTrue(c._connected({(0,0),(1,0),(1,1)}))
  with self.assertRaises(c.RecipeBlocker):c._topology({(0,0),(1,1)})
 def test_topology_reports_hole_without_repair(self):
  ring={(i,j)for i in range(3)for j in range(3)if(i,j)!=(1,1)};report=c._topology(ring)
  self.assertTrue(report['four_neighbor_connected']);self.assertEqual(report['interior_hole_components'],1);self.assertEqual(report['exposed_pixel_edges'],16)
if __name__=='__main__':unittest.main()
