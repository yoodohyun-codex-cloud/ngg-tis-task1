"""Pure integer topology tests, no real masks or data are read."""
import unittest
import pixel_outline as m

class PixelBoundaryContracts(unittest.TestCase):
 def test_rectangle_outline_has_exact_area_and_no_internal_edges(self):
  loops,areas=m.integer_contours({(0,0),(1,0),(0,1),(1,1)})
  self.assertEqual(len(loops),1);self.assertEqual(areas,[8]);self.assertEqual(len(loops[0])-1,8)
 def test_hole_remains_a_negative_area_contour(self):
  cells={(i,j)for i in range(3)for j in range(3)if(i,j)!=(1,1)};loops,areas=m.integer_contours(cells)
  self.assertEqual(len(loops),2);self.assertEqual(sorted(areas),[-2,18]);self.assertEqual(sum(areas),16)
 def test_corner_touch_does_not_create_a_fake_filled_bridge(self):
  loops,areas=m.integer_contours({(0,0),(1,1)})
  self.assertEqual(len(loops),2);self.assertEqual(areas,[2,2])
 def test_concavity_keeps_actual_square_boundary(self):
  loops,areas=m.integer_contours({(0,0),(1,0),(0,1)})
  self.assertEqual(len(loops),1);self.assertEqual(sum(areas),6)

if __name__=='__main__':unittest.main()
