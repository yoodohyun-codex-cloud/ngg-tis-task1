"""Synthetic identity/provenance tests; no original files/arrays/PDE are read."""
import unittest
from unittest.mock import patch
import consolidation_inputs as m
class IdentityContracts(unittest.TestCase):
 def row(self,cid,sha,dataset):return dict(candidate_id=cid,scalar={'SHA256':sha},mask={'SHA256':'m'*64},provenance={'dataset_id':dataset})
 def test_exact_ID_scalar_alias_deduplicates_with_provenance(self):
  rows=[self.row('B0','a'*64,'FIRST8'),self.row('B0','a'*64,'MULTIPAD')];canonical,aliases,variants=m.classify_records(rows)
  self.assertEqual(len(canonical),1);self.assertEqual(len(aliases),1);self.assertEqual(aliases[0]['alias_dataset'],'MULTIPAD');self.assertEqual(variants,[])
 def test_same_ID_different_scalar_preserves_conflict(self):
  rows=[self.row('B0','a'*64,'FIRST8'),self.row('B0','b'*64,'OTHER')];canonical,aliases,variants=m.classify_records(rows)
  self.assertEqual(len(canonical),1);self.assertEqual(aliases,[]);self.assertEqual(variants[0]['record'],rows[1])
 def test_same_scalar_different_geometry_rejected(self):
  rows=[self.row('B0','a'*64,'FIRST8'),self.row('B0','a'*64,'OTHER')];rows[1]['mask']['SHA256']='x'*64
  with self.assertRaises(ValueError):m.classify_records(rows)
 def test_same_ID_changed_scalar_and_geometry_is_rejected_not_hidden_as_variant(self):
  rows=[self.row('B0','a'*64,'FIRST8'),self.row('B0','b'*64,'OTHER')];rows[1]['mask']['SHA256']='x'*64
  with self.assertRaises(ValueError):m.classify_records(rows)
 def test_source_pin_is_identical_from_canonical_and_frozen_deployment(self):
  previous=m.__file__
  try:
   with patch.object(m,'digest',return_value='a'*64):
    m.__file__='/canonical/source/consolidation_inputs.py';one=m.source_pins();m.__file__='/frozen/snapshot/consolidation_inputs.py';two=m.source_pins()
   self.assertEqual(one,two);self.assertEqual(set(one),{str(m.SOURCE/'consolidation_inputs.py')})
  finally:m.__file__=previous
class PublicationContracts(unittest.TestCase):
 def fixture(self):return dict(status='published_readback_verified',commit='c'*40,files={'data-native/candidates/a.npz':dict(SHA256='d'*64,bytes=10,readback_passed=True)})
 def test_complete_direct_proof_accepted(self):self.assertEqual(m.published_file_matches(self.fixture(),'candidates/a.npz')['SHA256'],'d'*64)
 def test_pending_or_conflicting_proof_rejected(self):
  p=self.fixture();next(iter(p['files'].values()))['readback_passed']=False
  with self.assertRaises(ValueError):m.published_file_matches(p,'candidates/a.npz')
  with self.assertRaises(ValueError):m.published_file_matches(self.fixture(),'candidates/a.npz','x'*64)
if __name__=='__main__':unittest.main()
