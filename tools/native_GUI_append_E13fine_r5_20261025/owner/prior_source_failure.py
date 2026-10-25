"""Fixed append-R4 source failure/readback evidence; inert stdlib-only import.

collect() is deferred to the sole Root owner. It reads only fixed bounded
metadata/source/log files and returns hashes/aliases/absences, never data arrays.
"""
import hashlib,json,re
from pathlib import Path
ROOT=Path('/workspace/ngg-tis-task1/runtime')
OLD=ROOT/'native-GUI-append-E13fine-r4-20261025-run'
TRANSPORT=Path('/dev/shm/task1-git-native-GUI-append-E13fine-r4-source-20261025')
RECOVERY=ROOT/'append-r4-source-readback-recovery-20261025-run'
DIAGNOSTIC=ROOT/'append-r4-source-clone-no-filter-check-20261025-run'
COMMIT='f49035410f1a41f90452238ed968b8fcca1110d6'
PARENT='c6c72a5257b313df34fed42b43d559c8aab11a95'
OWNER_SHA='79cf7908fdf349084feb7e29eca141074fcc0c36db662a3920f4a2299de4002c'
PLAN_SHA='a6fa45fe7e08f29086f294ff49a554e0d5bbe3c0c0a5a05a163eed49b96de890'
RECOVERY_SOURCE_SHA='bbef461b28839471bc2cc27db090df0c7e36fe71f7a67f334ddcf8003840eb0c'
DIAGNOSTIC_SOURCE_SHA='06d6715450f37038a22715e3c4937f8011dd3f1f29fff19cb3ee22c9350064dd'
PUBLICATION_SHA='3409d6d25ba23e741babb22144d43ed8302d60e3a669ddebc294596ee667edd7'
# Every item is actual immutable code/metadata/log, not a guessed publication.
FILES={
 'owner':(OLD/'receipt.json',OWNER_SHA,1463),
 'registration':(OLD/'registration.json','16ba4c16de352467df252f2c4b8dc5366ea70012b17a0e4b068b5657e5c66796',8932),
 'preregistration':(OLD/'preregistration.json','6f13ef4e060205350484485e8ba6908242d53797e231acfd4bc571280d971b0a',106172),
 'plan':(OLD/'source-plan.json',PLAN_SHA,21884),
 'owner_log':(OLD/'logs/1-source-publication.log','e0cfcf2de8f263b53bdcf56b5998bd3ab0b2ff0754745fea879f338f0750ab11',1828),
 'publication':(OLD/'source-publication/result-publication.json',PUBLICATION_SHA,23851),
 'publisher_registration':(TRANSPORT/'registration.json','0ede097c9d9dc15e40b350a775de6243dce9371fda9da82e1e08a52534f2c290',4839),
 'state':(TRANSPORT/'transport-state.json','9cf6874a3f2cd4bae9c1a205f2f8458afba9e8b1b0a7fc4b02cfb873f00b3da4',23421),
 'attempt':(TRANSPORT/'attempt-1.json','0945b2f58c539870206deb1c833368459edcb9670c1287b2b377381f526693af',1032),
 'batch':(TRANSPORT/'batch-prefetch-1.json','68d9346a72b9800dc528665f1acf09df7f8b301606a9ee10c8e7eee014ff5851',220),
 'failed_command':(TRANSPORT/'logs/failed-1-141.json','f1a37134084a0f4b2f53a1c1eef9bbeb5066402e5818cc91987f6cf384004ea6',676),
 'recovery':(RECOVERY/'receipt.json','1608b21a029880e0dc45c86ad917b7aa73c4b971adc02330aca3d1f95ae89cac',906),
 'recovery_plan':(RECOVERY/'preregistration.json','a4e2f8aca7ce49aaf605e2898a3eb6acef14fb7331d5b224cd0964f9e5ffad3b',14270),
 'recovery_source':(ROOT/'append-r4-source-readback-recovery-20261025.py',RECOVERY_SOURCE_SHA,10966),
 'recovery_batch':(RECOVERY/'batch-prefetch.json','047554aabb63ea6bcef7eec99055173a4c046f27de59ca849150b0c63a164764',2109),
 'diagnostic':(DIAGNOSTIC/'receipt.json','98698d55f5d8bc2237d183c3a8a45d490898c02991b4998daff109e5c16644b3',886),
 'diagnostic_plan':(DIAGNOSTIC/'preregistration.json','739c78811651e3c84a143c1bcbb0b7eda21e165a4b3dbb42ac7072477c0b97d5',14478),
 'diagnostic_source':(ROOT/'append-r4-source-clone-no-filter-check-20261025.py',DIAGNOSTIC_SOURCE_SHA,11174),
 'diagnostic_batch':(DIAGNOSTIC/'batch-prefetch.json','bdd607e5c7ba72b4dd3f34b08232bae8a0d604765d309040b74351466cfd23ab',248),
}
ABSENT=('worker-receipt.json','synthetic-test-receipt.json','payload.json','index.html','summary.json','gui-build-receipt.json','numeric-admission.json','result-publication/result-publication.json')

def require(ok,message):
 if not ok:raise ValueError(message)
def _zero(record,keys):
 for k in keys:require(type(record.get(k))is int and record[k]==0,'No new native/branch work '+k)
def _hex(value,n):return type(value)is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',value)is not None

def validate_records(r):
 """Pure semantic cross-check; collect independently authenticates all bytes."""
 owner=r['owner'];attempt=r['attempt'];state=r['state'];batch=r['batch'];pub=r['publication'];plan=r['plan'];recovery=r['recovery'];diagnostic=r['diagnostic']
 require(owner.get('status')=='failed_preserved'and owner.get('failed_phase')=='source-publication'and owner.get('GUI_generated')is False and owner.get('candidate_adopted')is False,'Original source-publication failure must remain failed')
 _zero(owner,('new_PDE_RHS','new_Q_loads','new_angular_evaluations'))
 require(not any(k in owner for k in('source_commit','result_commit')),'Late recovered source is not original owner success')
 require(attempt.get('schema')=='task1-Git-only-attempt-v1'and attempt.get('status')=='failed_preserved'and attempt.get('recorded_commit')==COMMIT and attempt.get('push_attempted')is True and attempt.get('push_confirmed')is True,'Actual confirmed-pushed failed publisher attempt')
 require(state.get('commit')==COMMIT and state.get('parent')==PARENT and state.get('push_confirmed')is True,'Fixed original publisher state')
 require(batch.get('returncode')==1 and type(batch.get('returncode'))is int and batch.get('unsupported_fallback')is False and batch.get('unique_blob_count')==61,'Original batch failure is not unsupported-only fallback')
 require(r['failed_command'].get('returncode')==1 and 'bad revision'in r['failed_command'].get('stderr',''),'Actual bad-revision diagnostic retained')
 require(plan.get('expected_parent')==PARENT and type(plan.get('files'))is dict and len(plan['files'])==61,'Exact original source plan61 files')
 require(pub.get('status')=='published_readback_verified'and pub.get('commit')==COMMIT and pub.get('expected_parent')==PARENT and pub.get('transport')=='supported_Git_HTTPS_readback_only_recovery'and pub.get('verification_source_SHA256')==RECOVERY_SOURCE_SHA and pub.get('original_publisher_attempt_preserved')is True and pub.get('no_new_commit_or_push')is True,'Late standard source readback is separate from failed original publisher')
 require(type(pub.get('files'))is dict and set(pub['files'])==set(plan['files'])and len(pub['files'])==61,'All and only61 original source files read back')
 for target,p in pub['files'].items():
  expected=plan['files'][target]
  require(p.get('readback_passed')is True and _hex(p.get('SHA256'),64)and _hex(p.get('Git_blob_SHA'),40)and type(p.get('bytes'))is int and p['bytes']==expected['bytes']and p['SHA256']==expected['SHA256'],'Every exact source target has full SHA/bytes/readback proof '+target)
 require(recovery.get('schema')=='task1-append-R4-source-readback-recovery-v1'and recovery.get('status')=='append_R4_source_readback_recovered'and recovery.get('files_verified')==61 and recovery.get('result_publication_receipt_SHA256')==PUBLICATION_SHA and not any(k in recovery for k in('error','error_type','monitor_error')),'Actual successful complete readback recovery, no failed/pending substitute')
 require(diagnostic.get('status')=='failed_preserved'and diagnostic.get('error_type')=='AssertionError'and 'Explicit-no-filter batch request failed'in diagnostic.get('error','')and 'files_verified'not in diagnostic,'Clone-no-filter diagnostic remains failed')
 for name,record,source_sha in(('recovery',recovery,RECOVERY_SOURCE_SHA),('diagnostic',diagnostic,DIAGNOSTIC_SOURCE_SHA)):
  require(record.get('source_commit')==PARENT and record.get('result_commit')==COMMIT and record.get('original_GUI_owner_status')=='failed_preserved'and record.get('original_GUI_owner_receipt_SHA256')==OWNER_SHA and record.get('GUI_generated')is False and record.get('old_owner_rewritten')is False and record.get('original_GUI_worker_failure_retained')is True and type(record.get('finished_utc'))is str and record['finished_utc'],'Exact separate terminal readback/diagnostic identity')
  _zero(record,('new_PDE','new_native_array_decodes','branch_mutations'))
  prereg=r[name+'_plan'];require(prereg.get('fixed_commit')==COMMIT and prereg.get('expected_parent')==PARENT and prereg.get('plan_SHA256')==PLAN_SHA and prereg.get('original_failed_owner')==owner and prereg.get('original_failed_publisher')==attempt and prereg.get('verifier_source_SHA256')==source_sha,'Separate preregistration binds actual failed original/code/commit')
 require(r['recovery_batch'].get('returncode')==0 and r['recovery_batch'].get('explicit_no_filter')is True and r['recovery_batch'].get('blobs')==61,'Successful fresh-init explicit-no-filter batch')
 require(r['diagnostic_batch'].get('returncode')==1 and r['diagnostic_batch'].get('explicit_no_filter')is True and 'bad revision'in r['diagnostic_batch'].get('stderr',''),'Failed cloned-verifier diagnostic is distinct from successful fresh init')
 return dict(schema='task1-append-R4-prior-source-failure-evidence-v1',original_owner_status='failed_preserved',original_failed_phase='source-publication',original_MFG_performed=False,original_native_work_performed=False,original_GUI_generated=False,original_publication_attempt_failed=True,push_confirmed=True,late_source_readback_available=True,late_source_commit=COMMIT,late_source_parent=PARENT,late_source_files_verified=61,late_source_receipt_SHA256=PUBLICATION_SHA,readback_recovery_status=recovery['status'],clone_no_filter_diagnostic_status='failed_preserved',old_owner_rewritten=False,new_PDE=0,new_native_array_decodes=0,branch_mutations=0)

def collect():
 """Fixed deferred metadata/source/log I/O only; no scan/import/solve/network."""
 records={};raws={};pins={};aliases=[];total=0
 for name,(path,expected,count)in FILES.items():
  require(path.is_absolute()and path==path.resolve()and path.is_file()and not path.is_symlink()and path.suffix in('.json','.py','.log')and 0<count<=512*1024 and path.stat().st_size==count,'Fixed bounded original source/metadata/log '+name)
  raw=path.read_bytes();total+=len(raw);require(total<=2*1024**2 and len(raw)==count and hashlib.sha256(raw).hexdigest()==expected,'Exact original failure evidence SHA/bytes '+name)
  pins[str(path)]=expected;aliases.append(dict(path=str(path),SHA256=expected,bytes=count));raws[name]=raw
  if path.suffix=='.json':records[name]=json.loads(raw)
 for name in('recovery','diagnostic'):
  require(records[name+'_plan']['verifier_source_UTF8'].encode('utf-8')==raws[name+'_source'],'Exact actual executed source is embedded in its preregistration')
 evidence=validate_records(records);absences=[str(OLD/name)for name in ABSENT]
 require(all(not Path(path).exists()for path in absences),'Original R4 MFG/native/GUI/result outputs must remain absent')
 return dict(input_sha256=pins,aliases=aliases,absences=absences,evidence=evidence)
