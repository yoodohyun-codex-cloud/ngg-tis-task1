"""Pure manifest/index contracts; no filesystem reads, arrays or PDE."""
import copy,json,unittest
from pathlib import Path
from publish_caches import validate_manifest,sanitized_index


PATH=Path('/dev/shm/task1-fixture/eigen-cache/manifest.json')
def fixture():
 return dict(schema='task1-local-recomputable-eigen-cache-v1',shape=[2,2],dtype='<f8',order='F',local_readback_passed=True,
  durability='PRIVATE LOCAL DESCRIPTION',chunks=[dict(path=str(PATH.parent/'Q-cols-00000-00002.f64le'),bytes=32,SHA256='a'*64,
   row_start=0,row_stop=2,column_start=0,column_stop=2,dtype='<f8',order='F',local_readback_passed=True,private_annotation='DO NOT PUBLISH')])


class ManifestContracts(unittest.TestCase):
 def test_portable_index_drops_all_private_fields(self):
  obj=fixture();rows=validate_manifest(obj,'xy100',PATH,expected_n=2);index=sanitized_index(obj,'xy100',rows);raw=json.dumps(index)
  self.assertNotIn('/dev/',raw);self.assertNotIn('PRIVATE',raw);self.assertNotIn('DO NOT PUBLISH',raw);self.assertNotIn('durability',index)
  self.assertEqual(index['chunks'][0]['basename'],'Q-cols-00000-00002.f64le')
  self.assertEqual(index['shape'],[2,2])

 def test_bad_chunk_directory_gap_length_and_digest_are_rejected(self):
  bad=[]
  for key,value in(('path','/workspace/other/Q-cols-00000-00002.f64le'),('column_start',1),('bytes',31),('SHA256','bad')):
   obj=copy.deepcopy(fixture());obj['chunks'][0][key]=value;bad.append(obj)
  obj=fixture();obj['shape']=[3,3];bad.append(obj)
  obj=fixture();obj['chunks'][0]['local_readback_passed']=False;bad.append(obj)
  for obj in bad:
   with self.subTest(obj=obj),self.assertRaises(ValueError):validate_manifest(obj,'xy100',PATH,expected_n=2)


if __name__=='__main__':unittest.main()
