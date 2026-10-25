"""Exact R2 S-only budget failure preservation; inert and metadata-only."""
import hashlib,json
from pathlib import Path
SOURCE=Path('/workspace/ngg-tis-task1/runtime/native-GUI-lite-r5-owner-20261025/source')
OLD_RUN=Path('/dev/shm/task1-native-GUI-lite-r2-20261025-run')
ARCHIVE=SOURCE/'previous-R2-postS-failure-archive.json'
ARCHIVE_SHA='8230234edaeaac44cb344e7ec287b82dc81a2436260fa47b742fa756d8267b98'
S_COMMIT='f045c441e18189f89a48eb501420aa875ab6ef10'
S_SHA='43dff4fa9653b9c54254658ca08879b7f2e05d150bda18123855432d4df22d8a'

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and 0<p.stat().st_size<8*1024**2,'Canonical bounded source/JSON failure metadata only')
 return json.loads(p.read_bytes())
def validate_record(a):
 require(a.get('schema')=='task1-native-GUI-lite-R2-postS-preMFG-failure-archive-v1'and a.get('status')=='actual_source_published_budget_block_before_MFG_native_GUI'and a.get('original_run')==str(OLD_RUN),'Only actual R2 post-S pre-MFG budget failure')
 require(a.get('original_owner_status')=='failed_preserved'and a.get('actual_failed_phase')=='source-publication'and a.get('terminal_UTC')=='2026-10-25T16:40:32.717762+00:00','Exact original terminal owner phase/time')
 require(a.get('source_publication_available')is True and a.get('source_commit')==S_COMMIT and a.get('source_publication_SHA256')==S_SHA,'Actual R2 source publication is preserved, not a failed-source inference')
 for key in('result_publication_available','actual_MFG_run','actual_native_byte_reads','actual_GUI_built','old_numeric_admission_diagnostic_available','old_blocked_forecast_exact_values_known'):require(a.get(key)is False,'No nonexistent R2 outcome/diagnostic '+key)
 require(a.get('no_original_files_modified')is True and a.get('historical_peak_resources_are_not_coincident_forecast_values')is True,'Original failure preserved without inventing exact old blocked forecast')
 required={'numeric-admission.json','synthetic-test-receipt.json','worker-receipt.json','summary.json','index.html','result-publication/result-publication.json'}
 require(required.issubset(set(a.get('actual_absent_outputs',[]))),'Explicit original absent diagnostics/MFG/nativeGUI/R outputs')
 require(len(a.get('original_registered_source_files',[]))==32 and len(a.get('original_metadata_files',[]))==8,'Complete original source map and unpublished failure/control aliases')
 return True

def direct_source_proof(pub,row):
 require(pub.get('status')=='published_readback_verified'and pub.get('commit')==S_COMMIT and pub.get('remote_branch_head_verified')==S_COMMIT,'Exact complete actual S publication')
 proof=pub.get('files',{}).get(row['published_target'],{})
 require(proof.get('readback_passed')is True and proof.get('SHA256')==row['SHA256']and proof.get('bytes')==row['bytes'],'Exact direct source publication path/SHA/bytes; no basename fallback')
 return True

def verify_history(admission,registered_sources):
 decision=admission.get('previous_R2_postS_failure',{})
 require(decision.get('run')==str(OLD_RUN)and decision.get('archive_SHA256')==ARCHIVE_SHA and decision.get('source_commit')==S_COMMIT and decision.get('source_publication_SHA256')==S_SHA and decision.get('result_publication_available')is False,'Root explicitly binds actual R2 source and failed pre-MFG outcome')
 require(digest(ARCHIVE)==ARCHIVE_SHA and registered_sources.get(str(ARCHIVE))==ARCHIVE_SHA,'Registered byte-exact R2 failure archive')
 a=read(ARCHIVE);validate_record(a);refs={str(ARCHIVE):ARCHIVE_SHA}
 pub_path=OLD_RUN/'source-publication/result-publication.json';require(digest(pub_path)==S_SHA,'Original R2 source readback receipt unchanged');pub=read(pub_path);refs[str(pub_path)]=S_SHA
 for row in a['original_metadata_files']:
  p=Path(row['original_path']);copy=SOURCE/row['archive_source_name'];require(copy.parent==SOURCE,'Flat immutable metadata alias')
  require(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size==row['bytes']and digest(p)==row['SHA256'],'Original R2 failure/control metadata bytes unchanged')
  require(copy.read_bytes()==p.read_bytes()and registered_sources.get(str(copy))==row['SHA256'],'All actual unpublished failure/control bytes included in R3 source')
  refs[str(p)]=row['SHA256'];refs[str(copy)]=row['SHA256']
 for row in a['original_registered_source_files']+a['original_directly_published_metadata_files']:
  direct_source_proof(pub,row);p=Path(row['original_path'])
  require(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size==row['bytes']and digest(p)==row['SHA256'],'All old canonical source and large published metadata remain exact')
  refs[str(p)]=row['SHA256']
 owner=read(OLD_RUN/'receipt.json');require(owner['status']=='failed_preserved'and owner['GUI_generated']is False and owner['failed_phase']=='source-publication'and owner['new_PDE_RHS']==owner['new_Q_loads']==owner['new_angular_evaluations']==0,'Actual R2 failed before manufactured/native phase')
 absent=[str(OLD_RUN/name)for name in a['actual_absent_outputs']];require(all(not Path(p).exists()for p in absent),'Originally absent R2 output appeared; root review required')
 return dict(schema='task1-GUI-lite-R3-prior-R2-failure-proof-v1',status='actual_S_published_preMFG_budget_failure_preserved',archive_SHA256=ARCHIVE_SHA,old_owner_status='failed_preserved',old_source_commit=S_COMMIT,old_source_publication_SHA256=S_SHA,old_result_publication_available=False,old_tests_run=False,old_native_phase_reached=False,old_GUI_generated=False,old_exact_blocked_forecast_not_recorded=True,all_actual_original_and_S_publication_identities_verified=True),refs,absent
