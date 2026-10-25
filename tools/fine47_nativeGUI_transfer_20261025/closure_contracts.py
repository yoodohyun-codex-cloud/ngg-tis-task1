"""Pure metadata/status contracts; no import-time I/O, fields or publication."""
import re
REPO='yoodohyun-codex-cloud/ngg-tis-task1'
def require(ok,message):
 if not ok:raise ValueError(message)
def full_hex(value,length):return isinstance(value,str)and re.fullmatch('[0-9a-f]{'+str(length)+'}',value)is not None
def count(value,expected):return type(value)is int and value==expected
def validate_scope(label,source,result,owner,tests=None):
 for pub in(source,result):
  require(pub.get('status')=='published_readback_verified'and full_hex(pub.get('commit'),40)and isinstance(pub.get('files'),dict)and pub['files'],'Actual successful transport proof is required; it does not change scientific status')
  for target,item in pub['files'].items():require(item.get('readback_passed')is True and full_hex(item.get('SHA256'),64)and type(item.get('bytes'))is int and item['bytes']>=0,'Every transport object has a full fixed identity')
 require(owner.get('source_commit')==source['commit']and owner.get('result_commit')==result['commit'],'Original owner S/R commit linkage')
 require(owner.get('candidate_adopted')is False,'Transfer does not adopt candidates')
 if label=='first_failed':
  require(owner.get('status')=='synthetic_tests_failed_published_field_not_admitted'and owner.get('field_admission_granted')is False and count(owner.get('native_RHS'),0),'Only this explicitly preserved FAILED synthetic scope is accepted')
  require(tests is not None and tests.get('status')=='failed'and count(tests.get('tests_run'),52)and count(tests.get('model_tests_run'),47)and count(tests.get('owner_tests_run'),5)and count(tests.get('tests_failed'),1)and count(tests.get('native_RHS'),0)and tests.get('native_IO_attempts')==[]and tests.get('field_admission_granted')is False,'Original actual failed52 receipt must remain failed and unadmitted')
  require(all(count(tests.get(k),0)for k in('native_field_reads','native_eigen_solves','native_full_field_exports'))and tests.get('native_Q_loaded')is False and tests.get('native_eigen_performed')is False and tests.get('forbidden_field_calls')==['synthetic_angular_metric_fixture_calls'],'Only the explicit old null-deadline boundary failure, without native work, is allowed')
  return dict(semantic_status='FAILED_actual_52_tests_preserved',owner_status=owner['status'],actual_tests_run=52,actual_failed_tests=1,native_RHS=0,field_admission_granted=False)
 if label=='native_gui':
  require(owner.get('status')=='native_GUI_exact_payload_rendered_published_browser_unverified'and count(owner.get('new_PDE_RHS'),0)and count(owner.get('new_angular_evaluations'),0)and owner.get('native_arrays_loaded')is False and owner.get('browser_validation_performed')is False,'Actual render-only GUI result; browser pass is separate')
  return dict(semantic_status='native_GUI_rendered_browser_unverified',owner_status=owner['status'],new_PDE_RHS=0,browser_validation_performed=False)
 require(label=='mfg_r2','Exactly the three authorized closure scopes')
 require(owner.get('status')=='synthetic_tests_passed_published_field_not_admitted'and owner.get('field_admission_granted')is False and count(owner.get('native_RHS'),0),'Root-selected completed R2 PASS owner required before transfer')
 require(tests is not None and tests.get('status')=='passed'and count(tests.get('model_source_test_count'),47)and count(tests.get('model_tests_run'),47)and count(tests.get('owner_tests_run'),6)and count(tests.get('tests_run'),53)and count(tests.get('expected_total_tests'),53),'Actual R2 47+6=53 completed tests, never planned counts')
 require(all(count(tests.get(k),0)for k in('tests_failed','tests_errors','tests_skipped','native_RHS','native_field_reads','native_eigen_solves','native_full_field_exports'))and tests.get('native_Q_loaded')is False and tests.get('native_eigen_performed')is False and tests.get('field_admission_granted')is False,'R2 tests have no native work or skipped/failed test')
 require(tests.get('forbidden_field_calls')==[]and tests.get('native_IO_attempts')==[]and tests.get('manufactured_work_counts',{}).get('negative_expired_deadline_rejection_before_data')==1,'Actual corrected negative fixture and native scope proofs')
 require(tests.get('source_publication_commit')==source['commit']and tests.get('source_sha256')==tests.get('model_source_sha256')and isinstance(tests.get('model_source_sha256'),dict)and tests['model_source_sha256'],'Actual complete canonical model source identity')
 return dict(semantic_status='PASSED_synthetic_53_only_field_not_admitted',owner_status=owner['status'],actual_tests_run=53,model_tests_run=47,owner_tests_run=6,native_RHS=0,field_admission_granted=False)
def require_metadata_covered(publication,identities):
 covered={(row['SHA256'],row['bytes'])for row in publication['files'].values()if row.get('readback_passed')is True}
 require(all((row['SHA256'],row['bytes'])in covered for row in identities.values()),'Every original JSON/receipt/preregistration byte identity must actually be represented in M')
