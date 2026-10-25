"""Pure memory-phase contracts; no actual fields/cache/PDE are used."""
import unittest,weakref
import mixed_screen as m

class MixedMemoryContracts(unittest.TestCase):
 def test_Q_lifetime_ends_before_any_metric_stage(self):
  refs=[];events=[]
  class Q:pass
  def raw():
   q=Q();refs.append(weakref.ref(q));events.append('raw4');return {'actual_new_driven_RHS':4,'raws':['a','b','c','d']}
  def collect():events.append('gc')
  def metrics(data):
   self.assertIsNone(refs[0]());events.append('metrics2');self.assertEqual(data['actual_new_driven_RHS'],4);return 2
  self.assertEqual(m.separated_stages(raw,metrics,collect),2);self.assertEqual(events,['raw4','gc','metrics2'])
 def test_raw_array_leak_is_a_blocker_not_a_metric_memory_retry(self):
  class Array:pass
  called=[]
  with self.assertRaises(ValueError):m.separated_stages(lambda:{'Q':Array()},lambda _:called.append(True),lambda:None)
  self.assertEqual(called,[])
 def test_candidate_ids_keep_output_group_distinct_from_ground_return_group(self):
  self.assertEqual(m.IDS[2:],('M_Speriph_Rsquare','M_Ssquare_Rperiph'))
  self.assertEqual(len(set(m.IDS)),4)

if __name__=='__main__':unittest.main()
