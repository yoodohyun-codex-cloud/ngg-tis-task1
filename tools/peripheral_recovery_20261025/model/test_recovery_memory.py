"""Pure stage-lifetime tests; no NumPy/original arrays/PDE are invoked."""
import unittest,weakref
import recovery as m

class MemorySeparationContracts(unittest.TestCase):
 def test_raw_frame_object_is_released_before_angular_stage(self):
  events=[];references=[]
  class Cache:pass
  def raw():
   q=Cache();references.append(weakref.ref(q));events.append('raw');return {'path':'/saved/new-raw.npz','SHA256':'a'*64,'new_RHS':2}
  def collect():events.append('collect')
  def metrics(artifacts):
   self.assertIsNone(references[0]());events.append('metrics');self.assertEqual(artifacts['new_RHS'],2);return 'complete'
  self.assertEqual(m.separated_stages(raw,metrics,collect),'complete');self.assertEqual(events,['raw','collect','metrics'])
 def test_numeric_cache_object_leak_prevents_metric_execution(self):
  class Cache:pass
  called=[]
  with self.assertRaises(ValueError):m.separated_stages(lambda:{'Q':Cache()},lambda _:called.append('invalid'),lambda:None)
  self.assertEqual(called,[])
 def test_metadata_boundary_retains_json_proofs_but_not_complex_arrays(self):
  self.assertTrue(m.metadata_only({'proofs':[{'passed':True,'loss_W':.01}],'path':'/saved/raw','count':2}))
  self.assertFalse(m.metadata_only({'field':1+2j}))

if __name__=='__main__':unittest.main()
