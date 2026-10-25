"""Byte-preserved pure provenance contracts from the frozen aspect helper.
No file access, arrays, source imports or work on import.
"""
import copy,hashlib,re
from pathlib import Path
MAX_METADATA=8*1024**2
RECOVERY_SOURCE=Path('/dev/shm/task1-E13-fineXY-publication-resume-20261025.py')
def require(ok,message):
 if not ok:raise ValueError(message)
def fullhex(value,n):return isinstance(value,str)and re.fullmatch('[0-9a-f]{'+str(n)+'}',value)is not None

def validate_outcome(kind,primary,missing):
 require(type(primary)is dict and type(missing)is list,'Actual parsed primary and missing list')
 if kind in('computed_complete','computed_complete_publication_recovered'):
  require(not missing and primary.get('status')=='two_E13_matched97_metric_cases_and_physical_overlap_computed_unadopted','Actual complete E13fine summary only')
  counts=dict(actual_new_driven_RHS=2,actual_new_coarse_driven_RHS=0,actual_new_metric_evaluations=2,actual_full_angular_evaluations=1,actual_SC4_only_angular_evaluations=1,actual_repeated_original_bulk_angular_evaluations=0,actual_immutable_fine_B0_aliases=1,actual_control_RHS_repeated=0,actual_control_angular_metrics_repeated=0,new_eigen_solves=0)
  for key,value in counts.items():require(type(primary.get(key))is int and primary[key]==value,'Actual complete fine accounting '+key)
  require(primary.get('candidate_adopted')is False and primary.get('Q_resident_during_postprocessing')is False,'No field-Q leak or adoption assumed')
 else:
  allowed=('failed_preserved','E13_fineXY_failed_or_partial_preserved','E13_fineXY_failed_or_partial_published','failed_partial_E13_fineXY_preserved_no_automatic_resolve')
  require(kind=='failed_preserved'and primary.get('status')in allowed and missing and all(type(x)is str and x.strip()for x in missing)and primary.get('candidate_adopted')is not True,'Known actual failed outcome and explicit missing fields, no fabricated datasets')
 fields=('holds','prospective_adjacent_grid_diagnostics','same_grid_fine_design_comparisons','physical_overlap_comparison','diagnostics_not_run','error_type','error','observed_carrier_proofs','unknown_work_policy')
 return dict(outcome=kind,primary_status=primary['status'],missing_fields=copy.deepcopy(missing),copied_actual_evidence={key:copy.deepcopy(primary[key])if key in primary else None for key in fields},fields_present={key:key in primary for key in fields},grid_or_adjacent_PASS_required=False,failed_numbers_invented=False,fine_values_used_to_correct_model=False)

def validate_publication_recovery(record,prereg,original_owner,*,source_commit,result_commit,original_owner_SHA256,supervisor_SHA256):
 require(record.get('schema')=='task1-E13-fineXY-publication-recovery-owner-v1'and record.get('status')=='E13_fineXY_publication_recovery_published'and record.get('source_commit')==source_commit and record.get('result_commit')==result_commit,'Actual completed separate publication recovery, not numerical-owner success')
 require(record.get('numerical_original_owner_status')=='failed_preserved'and record.get('numerical_original_owner_receipt_SHA256')==original_owner_SHA256 and record.get('old_numerical_owner_rewritten')is False and record.get('recovery_only_not_new_numerical_success')is True and record.get('full_original_result_readback')is True,'Original numerical-owner failure remains unchanged; full late readback is separate')
 require(original_owner.get('status')=='failed_preserved'and original_owner.get('failed_phase')=='result-publication','Only an original publication-only timeout can use this complete-recovered path')
 require(type(record.get('publisher_attempt'))is int and record['publisher_attempt']==2 and type(record.get('publisher_exit_code'))is int and record['publisher_exit_code']==0,'Exactly actual successful publisher attempt2')
 for key in('new_PDE','new_PDE_RHS','new_Q_loads','new_angular_evaluations','new_eigen_solves'):require(type(record.get(key))is int and record[key]==0,'Publication recovery performs no scientific work '+key)
 require(type(record.get('pid'))is int and record['pid']>0 and type(record.get('proc_start_ticks'))is int and record['proc_start_ticks']>0 and type(record.get('finished_utc'))is str and record['finished_utc'],'Actual historical recovery owner identity and terminal time')
 require(not any(key in record for key in('error_type','error','failed_phase'))and record.get('publisher_cleanup_pending')is not True,'Failed/pending recovery does not admit new PDE')
 require(prereg.get('schema')=='task1-E13-fineXY-publication-recovery-preregistration-v1'and prereg.get('operation')=='verify_only_exact_existing_publisher_attempt2'and prereg.get('expected_result_commit')==result_commit and prereg.get('actual_original_source_commit')==source_commit and prereg.get('original_failure')==original_owner,'Actual source-bound exact-plan recovery preregistration')
 source=prereg.get('supervisor_source',{});require(source.get('path')==str(RECOVERY_SOURCE)and source.get('SHA256')==supervisor_SHA256 and fullhex(supervisor_SHA256,64)and type(source.get('UTF8'))is str and hashlib.sha256(source['UTF8'].encode()).hexdigest()==supervisor_SHA256 and source.get('bytes')==len(source['UTF8'].encode()),'Exact root-reviewed recovery supervisor UTF8/source SHA')
 require(prereg.get('new_PDE')==0 and prereg.get('new_native_array_decodes')==0 and prereg.get('new_numerical_worker')is False and prereg.get('old_numerical_owner_rewritten')is False and prereg.get('source_alias_is_original_S_not_new_source_commit')is True,'Recovery is transport-only and aliases original scientific S')
 return True

def validate_recovery_alias(d,original_path,alias_path):
 require(type(d)is dict and d.get('original_path')==str(original_path)and d.get('alias_path')==str(alias_path)and d.get('alias_only')is True,'Exact original and read-only recovery alias paths; immutable resumer ABI')
 require(fullhex(d.get('SHA256'),64)and type(d.get('bytes'))is int and 0<d['bytes']<MAX_METADATA,'Bounded full recovery alias SHA/bytes')
 return d
