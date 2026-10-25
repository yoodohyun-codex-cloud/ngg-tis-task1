"""Exact R4 successful-S/numeric budget failure metadata; inert import."""
import hashlib,json
from pathlib import Path
SOURCE=Path('/workspace/ngg-tis-task1/runtime/native-GUI-lite-r5-owner-20261025/source')
OLD_RUN=Path('/dev/shm/task1-native-GUI-lite-r4-20261025-run')
ARCHIVE=SOURCE/'previous-R4-numeric-block-archive.json'
ARCHIVE_SHA='e9cee93cbd8260b6704e4f25ca5be40c3032b62b1ce9fc146efae19adeb56d8c'
S_COMMIT='872706b47b498995b6eb9b2ad47e2b986a7a33a8'
S_SHA='aee88b1e85180d9e7788a8cfa0c64959095337db44f5de27eb55665886b7b921'

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and 0<p.stat().st_size<8*1024**2,'Canonical bounded actual source/metadata only')
 return json.loads(p.read_bytes())
def validate_record(a):
 require(a.get('schema')=='task1-native-GUI-lite-R4-source-published-numeric-budget-failure-v1'and a.get('status')=='actual_R4_S_published_numeric_block_before_MFG_native_GUI'and a.get('original_run')==str(OLD_RUN),'Only actual R4 numeric forecast block')
 require(a.get('original_owner_status')=='failed_preserved'and a.get('actual_failed_phase')=='numeric-admission'and a.get('terminal_UTC')=='2026-10-25T17:25:26.113534+00:00','Exact original terminal R4 phase/time')
 require(a.get('source_publication_available')is True and a.get('source_commit')==S_COMMIT and a.get('source_publication_SHA256')==S_SHA,'Actual successful R4 source publication remains distinct from failed computation admission')
 for key in('result_publication_available','actual_MFG_run','actual_native_byte_reads','actual_GUI_built'):require(a.get(key)is False,'No fabricated R4 result/test/native/GUI '+key)
 n=a.get('exact_original_numeric_admission',{});require(n.get('admitted')is False and n.get('physical_forecast_bytes')==8004039390 and n.get('forecast_excess_bytes')==4039390 and n.get('physical_cap_bytes')==8000000000,'Exact recorded old numeric blocker, not reconstructed peaks')
 require(n.get('all_owned_tmpfs_bytes')==7656256734 and n.get('all_research_RSS_bytes')==35782656 and n.get('forecast_child_RSS_bytes')==300000000 and n.get('forecast_new_output_bytes')==12000000,'Original forecast components unchanged')
 require(n['all_owned_tmpfs_bytes']+n['all_research_RSS_bytes']+n['forecast_child_RSS_bytes']+n['forecast_new_output_bytes']==n['physical_forecast_bytes'],'Original numeric sum identity')
 require(a.get('no_original_files_modified')is True and a.get('no_large_source_or_spec_bytes_duplicated')is True and len(a.get('original_registered_source_files',[]))==58,'All actual source code durably referenced without giant duplicate data')
 return True

def verify_history(admission,registered_sources):
 d=admission.get('previous_R4_numeric_failure',{});require(d.get('run')==str(OLD_RUN)and d.get('archive_SHA256')==ARCHIVE_SHA and d.get('source_commit')==S_COMMIT and d.get('source_publication_SHA256')==S_SHA and d.get('result_publication_available')is False,'Root actual R4 S/failure decision')
 require(digest(ARCHIVE)==ARCHIVE_SHA and registered_sources.get(str(ARCHIVE))==ARCHIVE_SHA,'Registered immutable actual R4 failure archive')
 a=read(ARCHIVE);validate_record(a);pubpath=OLD_RUN/'source-publication/result-publication.json';require(digest(pubpath)==S_SHA,'Exact old S receipt');pub=read(pubpath)
 require(pub.get('status')=='published_readback_verified'and pub.get('commit')==S_COMMIT and pub.get('remote_branch_head_verified')==S_COMMIT,'Actual old S full readback')
 refs={str(ARCHIVE):ARCHIVE_SHA,str(pubpath):S_SHA}
 for row in a['original_metadata_files']:
  p=Path(row['original_path']);copy=SOURCE/row['archive_source_name'];require(copy.parent==SOURCE,'Flat immutable metadata alias')
  require(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size==row['bytes']and digest(p)==row['SHA256'],'Original R4 failure/control bytes unchanged')
  require(copy.read_bytes()==p.read_bytes()and registered_sources.get(str(copy))==row['SHA256'],'Actual failure/control aliases all registered')
  refs[str(p)]=row['SHA256'];refs[str(copy)]=row['SHA256']
 for row in a['original_registered_source_files']+a['original_directly_published_metadata_files']:
  proof=pub.get('files',{}).get(row['published_target'],{});require(proof.get('readback_passed')is True and proof.get('SHA256')==row['SHA256']and proof.get('bytes')==row['bytes'],'Exact durable S code/large metadata reference')
  p=Path(row['original_path']);require(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size==row['bytes']and digest(p)==row['SHA256'],'Old source and published metadata remain byte exact');refs[str(p)]=row['SHA256']
 owner=read(OLD_RUN/'receipt.json');require(owner['status']=='failed_preserved'and owner['failed_phase']=='numeric-admission'and owner['GUI_generated']is False,'Actual failed owner before MFG/native')
 absent=[str(OLD_RUN/name)for name in a['actual_absent_outputs']];require(all(not Path(p).exists()for p in absent),'Originally absent old R4 output appeared; root review required')
 return dict(schema='task1-GUI-lite-R5-prior-R4-failure-proof-v1',status='actual_R4_S_and_numeric_block_preserved',archive_SHA256=ARCHIVE_SHA,old_source_commit=S_COMMIT,old_R_available=False,old_MFG_native_GUI_performed=False,old_recorded_forecast_bytes=8004039390,old_recorded_excess_bytes=4039390,old_source_records_preserved=58,no_original_files_modified=True),refs,absent
