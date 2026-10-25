"""Tiny manufactured cached-scalar contract; no real field or cache access."""
import unittest
from unittest import mock
import numpy as np
import cached_metrics as c
import screen_metrics as m
def fixture():
 grid=np.asarray([[0,0,.05,0,1e-9],[0,0,2.,1,1e-9],[0,0,7.,2,1e-9],[0,0,17.5,3,1e-9]])
 total=grid[:,4].copy();target=np.asarray([0.,0.,0.,1e-9]);surface=np.asarray([1e-9,1e-9,0.,0.]);sub=np.asarray([0.,0.,1e-9,0.])
 weights=dict(total=total,target=target,surface_0_5=surface,subsurface_5_10=sub,remaining=np.zeros(4),off_target=total-target)
 a=np.tile([3.+0j,0j,0j],(4,1));b=np.tile([2.+0j,0j,0j],(4,1));winner=int(np.argmax(abs(m.directions(np)[:,0])))
 values=dict(carrier_RMS=np.full(4,np.sqrt(6.5)),carrier0_RMS=np.full(4,3/np.sqrt(2)),carrier1_RMS=np.full(4,2/np.sqrt(2)),AM_x=np.full(4,4.),AM_y=np.zeros(4),AM_z=np.zeros(4),AM_max2074=np.full(4,4.),AM_direction_index=np.full(4,winner,np.int32),Jtotal_vector_RMS=np.full(4,np.sqrt(6.5)))
 return grid,weights,values,a,b
class CachedBulkMetrics(unittest.TestCase):
 def test_reaggregation_preserves_cached_AM_without_full_angular_call(self):
  grid,w,arrays,a,b=fixture()
  with mock.patch.object(m,'evaluate',side_effect=AssertionError('Bulk angular rescan forbidden')):
   result=c.summarize(np,grid,w,arrays,dict(source_Vpp_each=1.),a,b)
  self.assertEqual(result['summary']['regions']['target']['statistics']['maxTIS']['mean'],4.)
  self.assertFalse(result['summary']['directional_search']['bulk_spatial_angular_scan_repeated'])
  np.testing.assert_array_equal(result['arrays']['AM_max2074'],arrays['AM_max2074'])
 def test_modified_selected_direction_value_or_RMS_cannot_alias_old_bulk(self):
  for key in('AM_max2074','carrier_RMS'):
   grid,w,arrays,a,b=fixture();arrays[key]=arrays[key].copy();arrays[key][-1]+=1.
   with self.assertRaises(ValueError):c.summarize(np,grid,w,arrays,dict(source_Vpp_each=1.),a,b)
if __name__=='__main__':unittest.main()
