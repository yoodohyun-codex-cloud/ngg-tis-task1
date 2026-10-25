"""Authenticate exact metadata members of a fully read-back immutable archive.

No extraction, I/O or research execution on import. Raw native files must retain
individual direct publication proof; this helper is for archived metadata only.
"""
import hashlib,io,tarfile
from pathlib import PurePosixPath,Path
MAX_ARCHIVE=64*1024**2
MAX_MEMBER=8*1024**2

def require(ok,message):
 if not ok:raise ValueError(message)
def archive_member_bytes(raw,proof,member,expected_sha256):
 require(proof.get('readback_passed')is True,'Archive full immutable readback proof required')
 require(isinstance(raw,bytes)and len(raw)==proof['bytes']and len(raw)<=MAX_ARCHIVE and hashlib.sha256(raw).hexdigest()==proof['SHA256'],'Whole archive SHA/bytes must match published proof')
 name=PurePosixPath(member)
 require(not name.is_absolute()and '..'not in name.parts and str(name)==member,'Exact canonical relative archive member')
 require(not name.parts or name.parts[0]!='bases','Native raw data requires direct individual publication proof')
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')as archive:
  matches=[m for m in archive.getmembers()if m.name==member]
  require(len(matches)==1 and matches[0].isfile()and 0<=matches[0].size<=MAX_MEMBER,'One bounded regular metadata member required')
  stream=archive.extractfile(matches[0]);require(stream is not None,'Regular archive stream required')
  with stream:data=stream.read(MAX_MEMBER+1)
  require(len(data)==matches[0].size and hashlib.sha256(data).hexdigest()==expected_sha256,'Exact member SHA must equal locally pinned comparator bytes')
  return data

def verified_archive_member(path,proof,member,expected_sha256):
 path=Path(path)
 require(path.is_file()and not path.is_symlink()and path.stat().st_size==proof['bytes']and path.stat().st_size<=MAX_ARCHIVE,'Canonical bounded local publication archive')
 return archive_member_bytes(path.read_bytes(),proof,member,expected_sha256)
