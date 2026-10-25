"""Exact R3 pre-S log-registration failure; metadata/code only, inert import."""
import hashlib,json
from pathlib import Path
from recovery_R2_history import direct_source_proof
SOURCE=Path('/dev/shm/task1-native-GUI-lite-r4-owner-20261025/source')
OLD_RUN=Path('/dev/shm/task1-native-GUI-lite-r3-20261025-run')
ARCHIVE=SOURCE/'previous-R3-preS-failure-archive.json'
ARCHIVE_SHA='8c55f4f5c24015166c246f8ea3c87ae9bdb7124cd354130862474a5b6bd1aea7'
S_COMMIT='f045c441e18189f89a48eb501420aa875ab6ef10'
S_SHA='43dff4fa9653b9c54254658ca08879b7f2e05d150bda18123855432d4df22d8a'

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and 0<p.stat().st_size<8*1024**2,'Canonical bounded actual source/metadata archive')
 return json.loads(p.read_bytes())
def validate_record(a):
 require(a.get('schema')=='task1-native-GUI-lite-R3-preS-registration-failure-archive-v1'and a.get('status')=='actual_preS_failure_missing_log_registration_preserved'and a.get('original_run')==str(OLD_RUN),'Only actual pre-S R3 registry failure')
 require(a.get('original_owner_status')=='failed_preserved'and a.get('actual_failed_phase')=='preparing'and a.get('terminal_UTC')=='2026-10-25T16:59:08.741778+00:00','Exact failed R3 phase/time')
 for key in('source_publication_available','result_publication_available','actual_MFG_run','actual_native_byte_reads','actual_GUI_built'):require(a.get(key)is False,'No fabricated R3 publication/test/native/GUI '+key)
 require(a.get('source_reuse_commit')==S_COMMIT and a.get('source_reuse_publication_SHA256')==S_SHA,'Reuse is actual older R2 S only, never a fabricated R3 S')
 require(a.get('missing_registered_log_bytes')==664 and a.get('actual_log_bytes_match_prior_R2_archive')is True and a.get('original_registered_source_count')==46 and a.get('source_record_count')==len(a.get('source_records',[]))==47,'All46 registered sources plus the actual omitted664-byte log')
 require(a.get('reused_actual_published_S_records')==27 and a.get('unpublished_UTF8_records')==20 and len(a.get('original_metadata_files',[]))==8,'Complete differential source archive and actual failure/control aliases')
 require(a.get('no_original_files_modified')is True and a.get('no_original_spec_or_large_nested_archive_duplicated')is True,'Original evidence preserved without duplicating nonexistent/large spec')
 return True

def verify_history(admission,registered_sources):
 decision=admission.get('previous_R3_preS_failure',{})
 require(decision.get('run')==str(OLD_RUN)and decision.get('archive_SHA256')==ARCHIVE_SHA and decision.get('source_publication_available')is False and decision.get('result_publication_available')is False,'Root explicitly acknowledges actual R3 pre-S outcome')
 require(digest(ARCHIVE)==ARCHIVE_SHA and registered_sources.get(str(ARCHIVE))==ARCHIVE_SHA,'Registered immutable differential R3 archive')
 a=read(ARCHIVE);validate_record(a);refs={str(ARCHIVE):ARCHIVE_SHA}
 pub_path=Path(a['source_reuse_publication_path']);require(digest(pub_path)==S_SHA,'Exact actual older S receipt before source reuse');pub=read(pub_path);refs[str(pub_path)]=S_SHA
 for row in a['original_metadata_files']:
  p=Path(row['original_path']);copy=SOURCE/row['archive_source_name'];require(copy.parent==SOURCE,'Flat original metadata alias')
  require(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size==row['bytes']and digest(p)==row['SHA256'],'Actual R3 failure/control metadata unchanged')
  require(copy.read_bytes()==p.read_bytes()and registered_sources.get(str(copy))==row['SHA256'],'Every actual R3 failure/control alias including plaintext logs is registered')
  refs[str(p)]=row['SHA256'];refs[str(copy)]=row['SHA256']
 oldreg=read(OLD_RUN/'registration.json');seen=set()
 for row in a['source_records']:
  p=Path(row['original_path']);require(str(p)not in seen,'Unique original source identity');seen.add(str(p))
  require(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size==row['bytes']and digest(p)==row['SHA256'],'Every original R3 source remains byte unchanged')
  if row['present_in_original_registration']:require(oldreg['source_sha256'].get(str(p))==row['SHA256'],'Original source registration identity')
  else:require(str(p)==a['missing_registered_log_original_path']and str(p)not in oldreg['source_sha256']and row['bytes']==664 and row['SHA256']==a['missing_registered_log_SHA256'],'Only the actual correctly hashed omitted log is unregistered')
  if row['storage']=='actual_published_S_alias':
   require(row.get('source_commit')==S_COMMIT,'Only actual immutable older S reuse');direct_source_proof(pub,row)
  elif row['storage']=='unpublished_UTF8':
   raw=row['UTF8'].encode('utf-8');require(raw==p.read_bytes()and len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['SHA256'],'Unique unpublished source is recoverable byte exactly')
  else:raise ValueError('No hash-only source backup claim')
  refs[str(p)]=row['SHA256']
 require(set(oldreg['source_sha256']).issubset(seen),'Complete original registered source coverage')
 absent=[str(OLD_RUN/name)for name in a['actual_absent_outputs']];require(all(not Path(p).exists()for p in absent),'An originally absent R3 output appeared; root review required')
 owner=read(OLD_RUN/'receipt.json');require(owner['status']=='failed_preserved'and owner['failed_phase']=='preparing'and owner['GUI_generated']is False,'Actual R3 failed before source/tests/native')
 return dict(schema='task1-GUI-lite-R4-prior-R3-failure-proof-v1',status='actual_R3_preS_log_registration_failure_preserved',archive_SHA256=ARCHIVE_SHA,old_R3_S_available=False,old_R3_R_available=False,old_R3_MFG_native_GUI_performed=False,reused_older_actual_S_commit=S_COMMIT,unique_unpublished_source_UTF8_preserved=20,reused_exact_durable_source_records=27,original_source_records_preserved=47,no_original_files_modified=True),refs,absent
