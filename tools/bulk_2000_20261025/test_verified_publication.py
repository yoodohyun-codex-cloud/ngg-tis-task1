"""Synthetic in-memory archive contracts only; root chooses actual execution."""
import hashlib,io,tarfile,unittest
from verified_publication import archive_member_bytes

def fixture(data=b'approved metadata',name='postprocess/artifact-sha256.json'):
 output=io.BytesIO()
 with tarfile.open(fileobj=output,mode='w:gz')as archive:
  member=tarfile.TarInfo(name);member.size=len(data);archive.addfile(member,io.BytesIO(data))
 raw=output.getvalue()
 return raw,dict(readback_passed=True,SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
class ArchiveContracts(unittest.TestCase):
 def test_correct_published_member(self):
  raw,proof=fixture();expected=hashlib.sha256(b'approved metadata').hexdigest()
  self.assertEqual(archive_member_bytes(raw,proof,'postprocess/artifact-sha256.json',expected),b'approved metadata')
 def test_altered_member_rejected(self):
  raw,proof=fixture(b'altered')
  with self.assertRaises(ValueError):archive_member_bytes(raw,proof,'postprocess/artifact-sha256.json',hashlib.sha256(b'approved metadata').hexdigest())
 def test_missing_member_rejected(self):
  raw,proof=fixture()
  with self.assertRaises(ValueError):archive_member_bytes(raw,proof,'postprocess/missing.json',hashlib.sha256(b'approved metadata').hexdigest())
if __name__=='__main__':unittest.main()
