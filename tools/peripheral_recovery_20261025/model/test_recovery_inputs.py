"""Synthetic provenance contracts only; no run data or scientific imports."""
import unittest
import recovery_inputs as m

class PublicationContracts(unittest.TestCase):
 def fixture(self):return dict(status='published_readback_verified',commit='a'*40,files={'data-native/example/rhs/known.npz':dict(SHA256='b'*64,bytes=123,readback_passed=True)})
 def test_exact_published_file_requires_complete_readback(self):
  result=m.published_file_proof(self.fixture(),'rhs/known.npz','b'*64)
  self.assertEqual(result['SHA256'],'b'*64);self.assertTrue(result['readback_passed'])
 def test_pending_readback_rejected(self):
  p=self.fixture();next(iter(p['files'].values()))['readback_passed']=False
  with self.assertRaises(ValueError):m.published_file_proof(p,'rhs/known.npz')
 def test_altered_or_ambiguous_identity_rejected(self):
  p=self.fixture()
  with self.assertRaises(ValueError):m.published_file_proof(p,'rhs/known.npz','c'*64)
  p['files']['other/rhs/known.npz']=dict(next(iter(p['files'].values())))
  with self.assertRaises(ValueError):m.published_file_proof(p,'rhs/known.npz')
 def test_missing_original_bytes_are_not_a_publication_proof(self):
  with self.assertRaises(ValueError):m.published_file_proof(self.fixture(),'rhs/not-computed.npz')
 def test_boolean_byte_length_is_rejected(self):
  p=self.fixture();next(iter(p['files'].values()))['bytes']=True
  with self.assertRaises(ValueError):m.published_file_proof(p,'rhs/known.npz')

class StageReplayContracts(unittest.TestCase):
 def test_clean_partial_stage_records_absence_without_reading_arrays(self):
  result=m.unfinished_stage_proof({'files':{}},exists=lambda relative:False)
  self.assertEqual(result['status'],'exact_partial_stage_absence_verified')
  self.assertIn('rhs/'+m.NEW+'-2000-raw.npz',result['relative_paths_absent'])
 def test_published_p12_RHS_cannot_be_replayed(self):
  p={'files':{'data-native/partial/rhs/'+m.NEW+'-2000-raw.npz':{}}}
  with self.assertRaises(ValueError):m.unfinished_stage_proof(p,exists=lambda relative:False)
 def test_local_completed_P23_metrics_cannot_be_replayed(self):
  marker='candidates/'+m.REUSE+'-scalars.npz'
  with self.assertRaises(ValueError):m.unfinished_stage_proof({'files':{}},exists=lambda relative:relative==marker)

if __name__=='__main__':unittest.main()
