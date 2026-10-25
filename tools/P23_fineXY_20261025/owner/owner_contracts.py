"""Pure finite fine-XY accounting and mandatory no-fallback restoration gates."""
def require(ok,message):
 if not ok:raise ValueError(message)
def validate_restore(p):
 require(p.get('passed')is True and p.get('passivity_passed')is True and p.get('physical_gates',{}).get('passed')is True,'Mandatory cachedB0 fresh residual/current/power/passivity gates')
 require(p.get('actual_new_RHS')==0 and p.get('reused_published_baseline_surface')is True,'Cached B0 restore must never become a fallback solve')
 require(0<=p.get('restored_modal_relative_error',-1)<=2e-7 and p.get('modal_restore_limit')==2e-7,'Mandatory restored modal coefficient identity')
 require(len(p['physical_gates'].get('metrics',{}))==5,'All five unchanged native screening gates required')
 return dict(passed=True,reused_fine_B0_2000_RHS=1,new_RHS=0,automatic_fourth_fallback=False)
def validate_summary(s):
 require(s.get('status')=='four_matched97_metric_cases_and_physical_overlap_computed_unadopted','Exact complete adjacent-XY result status')
 expected=dict(actual_new_driven_RHS=3,actual_reused_fine_B0_2000_RHS=1,actual_new_coarse_driven_RHS=0,actual_new_metric_evaluations=4,actual_full_angular_evaluations=2,actual_SC4_only_angular_evaluations=2,actual_repeated_original_bulk_angular_evaluations=0,actual_duplicate_full_coarse_scalar_archives=0,new_eigen_solves=0)
 for key,value in expected.items():require(type(s.get(key))is int and s[key]==value,'Exact prospective work and reuse count '+key)
 require(len(s.get('candidates',[]))==4 and s.get('Q_resident_during_postprocessing')is False and s.get('candidate_adopted')is False,'Four summaries only after raw Q frames end; no adoption')
 require(s.get('coarse_common97_bulk_binding',{}).get('passed')is True and s['coarse_common97_bulk_binding'].get('bulk_raw_duplicated')is False,'Actual original93bulk physical coordinate/volume/face identity required')
 require(s.get('holds',{}).get('old_13_of_14_electrical_failures_per_basis_preserved')is True and s['holds'].get('full_convergence')is False,'Old failed screens held; one adjacent step is not convergence')
 return dict(passed=True,**expected,maximum_new_RHS=3,automatic_fourth_fallback=False,full_convergence=False,candidate_adopted=False)
def validate_MFG(receipt,model_sources,model_count):
 require(receipt.get('status')=='passed'and receipt.get('model_source_sha256')==model_sources and receipt.get('model_source_test_count')==model_count==47,'Only actual published PASS from same frozen47 model tests')
 require(receipt.get('model_tests_run')==47 and receipt.get('tests_run')==receipt.get('expected_total_tests')and type(receipt.get('tests_run'))is int and receipt['tests_run']>=47 and all(receipt.get(k)==0 for k in('tests_failed','tests_errors','tests_skipped')),'Actual complete successful test execution, never first failed MFG receipt')
 require(receipt.get('native_RHS')==0 and receipt.get('native_Q_loaded')is False and receipt.get('field_admission_granted')is False,'Manufactured test proof is not prior field admission')
 return dict(passed=True,model_tests_reused=47,total_manufactured_tests_reused=receipt['tests_run'],tests_repeated=False)
