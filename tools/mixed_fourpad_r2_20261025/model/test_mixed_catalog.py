"""Synthetic whole-physicalpad composition contracts; no actual masks or data."""
import unittest
import mixed_catalog as m
class WholePadComposition(unittest.TestCase):
 def fixture(self):return {'B0':[(p,p,0)for p in range(4)],'P23':[(p,p,1)for p in range(4)]}
 def test_signal_peripheral_return_square_is_wholepad_selection(self):
  self.assertEqual(m.merge_rows(self.fixture(),['P23','P23','B0','B0']),[(0,0,1),(1,1,1),(2,2,0),(3,3,0)])
 def test_signal_square_return_peripheral_inverse(self):
  self.assertEqual(m.merge_rows(self.fixture(),['B0','B0','P23','P23']),[(0,0,0),(1,1,0),(2,2,1),(3,3,1)])
 def test_controls_reuse_all_original_physicalpads(self):
  for donor in('B0','P23'):self.assertEqual(m.merge_rows(self.fixture(),[donor]*4),self.fixture()[donor])
 def test_overlap_cannot_be_repaired_or_relabelled(self):
  donors=self.fixture();donors['P23'][0]=(0,2,0)
  with self.assertRaises(ValueError):m.merge_rows(donors,['P23','P23','B0','B0'])
 def test_missing_physicalpad_cannot_trigger_fresh_shape_generation(self):
  donors=self.fixture();donors['P23']=donors['P23'][1:]
  with self.assertRaises(ValueError):m.merge_rows(donors,['P23','P23','B0','B0'])
if __name__=='__main__':unittest.main()
