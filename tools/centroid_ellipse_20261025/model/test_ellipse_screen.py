"""Synthetic physical-centroid and raw-frame contracts, not a candidate run."""
import unittest
import ellipse_screen as model
def square_fixture():
 rows=['pad,i,j,area_m2'];meta=[]
 for pad,(lo_i,lo_j,cx,cy)in enumerate(((15,15,-10.,-10.),(55,55,10.,10.),(55,15,10.,-10.),(15,55,-10.,10.))):
  for j in range(lo_j,lo_j+30):
   for i in range(lo_i,lo_i+30):rows.append(str(pad)+','+str(i)+','+str(j)+',2.5e-7')
  meta.append(dict(pad=pad,centroid_mm=[cx,cy]))
 return ('\n'.join(rows)+'\n').encode(),meta
class EllipseStageContracts(unittest.TestCase):
 def test_exact_full_square_union_centroid_verified_without_repositioning(self):
  raw,meta=square_fixture();centres,proof=model._centroids(raw,meta);self.assertTrue(proof['passed']);self.assertFalse(proof['new_position_fit']);self.assertEqual(centres[0][0],-10);self.assertEqual(centres[1][1],10)
  meta[0]['centroid_mm'][0]=-.5
  with self.assertRaises(ValueError):model._centroids(raw,meta)
 def test_raw_frame_ends_and_collects_before_any_metrics(self):
  events=[]
  def raw():events.append('raw');return dict(paths=['immutable-file'],new_RHS=2)
  def collect():events.append('GC')
  def post(value):events.append('post');return value['new_RHS']
  self.assertEqual(model.separated_stages(raw,post,collect),2);self.assertEqual(events,['raw','GC','post'])
  with self.assertRaises(ValueError):model.separated_stages(lambda:dict(Q=object()),post,collect)
 def test_actual_passed_model_test_proof_precedes_new_RHS(self):
  refs={'canonical-source':'a'*64};proof=dict(status='passed',model_source_sha256=refs,model_source_test_count=4,tests_run=6,expected_total_tests=6)
  self.assertTrue(model.validate_test_receipt(proof,refs,4)['passed'])
  for key,value in(('status','not_run'),('model_source_sha256',{}),('tests_run',True),('expected_total_tests',7)):
   bad=dict(proof);bad[key]=value
   with self.assertRaises(ValueError):model.validate_test_receipt(bad,refs,4)
if __name__=='__main__':unittest.main()
