"""Pure terminal metadata contracts; no import-time I/O or research work."""
import re

def require(ok,message):
 if not ok:raise ValueError(message)

def validate_r5(owner):
 require(owner.get('schema')=='task1-results-gui-browser-owner-v1'and owner.get('status')=='failed_preserved','Only the actual preserved failed R5 owner is accepted')
 require(owner.get('new_PDE_RHS')==0 and owner.get('candidate_adopted')is False and owner.get('failed_phase')=='actual-browser-child','R5 is browser-only failure, no candidate adoption')
 require(owner.get('error_type')=='InterruptedError'and owner.get('error')=='Actual ALL research-familyRSS plus ALL task1-ownedtmpfs cap','The actual unchanged 8e9-cap interruption must be preserved')
 resources=owner.get('resources',{})
 require(type(resources.get('peak_accounted'))is int and resources['peak_accounted']>8_000_000_000,'Historical recorded cap exceedance, not a current-resource measurement')
 return dict(semantic_status='FAILED_R5_browser_cap_failure_preserved',owner_status=owner['status'],failure_phase=owner['failed_phase'],historical_peak_accounted_bytes=resources['peak_accounted'],cap_bytes=8_000_000_000,browser_PASS=False,new_PDE_RHS=0,candidate_adopted=False)

def validate_fine(owner,source,result,outcome,stage=None):
 require(owner.get('schema')=='task1-P23-fineXY-owner-v1'and owner.get('candidate_adopted')is False and owner.get('maximum_new_driven_RHS')==3 and owner.get('automatic_fourth_fallback')is False,'Exact finite fineXY scope, three-new-RHS ceiling and no fourth fallback')
 for key,pub in(('source_commit',source),('result_commit',result)):
  if key in owner:require(owner[key]==pub['commit'],'Original fine owner/publication commit linkage '+key)
 require(source.get('status')=='published_readback_verified'and result.get('status')=='published_readback_verified','Actual fine source/result full readback required')
 if outcome=='completed':
  require(owner.get('status')=='P23_fineXY_three_RHS_computed_published','Only actual completed fine result may be labelled completed')
  accounting=owner.get('field_accounting',{})
  expected={'actual_new_driven_RHS':3,'actual_reused_fine_B0_2000_RHS':1,'actual_new_coarse_driven_RHS':0,'actual_new_metric_evaluations':4,'actual_full_angular_evaluations':2,'actual_SC4_only_angular_evaluations':2,'actual_repeated_original_bulk_angular_evaluations':0,'actual_duplicate_full_coarse_scalar_archives':0,'new_eigen_solves':0}
  require(accounting.get('passed')is True and all(type(accounting.get(k))is int and accounting[k]==v for k,v in expected.items()),'Actual complete unchanged finite-work accounting')
  require(accounting.get('automatic_fourth_fallback')is False and accounting.get('full_convergence')is False and accounting.get('candidate_adopted')is False,'Completed calculation is not full convergence/adoption')
  require(stage is not None and stage.get('status')=='adjacent_fineXY_computed'and stage.get('worker_exit_code')==0 and stage.get('accounting')==accounting and stage.get('source_commit')==source['commit'],'Actual completed fine execution-stage/owner identity')
  return dict(semantic_status='fineXY_adjacent_calculation_completed_UNADOPTED_not_full_convergence',owner_status=owner['status'],actual_accounting=accounting,full_convergence=False,candidate_adopted=False)
 require(outcome=='failed'and owner.get('status')in('P23_fineXY_failed_or_partial_published','failed_preserved'),'Explicit actual failed or partial fine result, never planned completion')
 if stage is not None:require(stage.get('status')in('adjacent_fineXY_failed_or_partial_preserved','adjacent_fineXY_computed'),'Preserve actual execution stage; never fabricate a failure counter')
 return dict(semantic_status='fineXY_actual_failed_or_partial_preserved_UNADOPTED',owner_status=owner['status'],recorded_accounting=owner.get('field_accounting'),recorded_stage_status=None if stage is None else stage.get('status'),actual_completed_RHS_not_inferred=True,maximum_new_RHS=3,automatic_fourth_fallback=False,full_convergence=False,candidate_adopted=False)

def require_metadata_covered(publication,identities):
 covered={(row['SHA256'],row['bytes'])for row in publication['files'].values()if row.get('readback_passed')is True}
 require(all((row['SHA256'],row['bytes'])in covered for row in identities.values()),'Every original metadata identity must actually be represented in M')
