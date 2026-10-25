"""Pure accounting gates for stored-native postprocessing and manufactured proof."""
def require(ok,message):
 if not ok:raise ValueError(message)
def fixture_elements(shape,limit=65536):
 dims=(shape,)if type(shape)is int else tuple(shape);require(all(type(n)is int and n>=0 for n in dims),'Manufactured array shape uses nonnegative Python integers')
 total=1
 for n in dims:total*=n;require(total<=limit,'Bounded manufactured arrays before allocation; native graph/field/Q shapes forbidden')
 return total
def validate_summary(s,expected_geometries):
 require(type(expected_geometries)is int and expected_geometries in(2,3),'Two fine geometries plus optional actual complete ellipse')
 require(s.get('status')=='cached_native_highvolume_and40probe_postbatch_computed_unadopted','Exact stored-native postbatch complete status')
 for key in('actual_new_PDE_RHS','actual_new_Q_loads','actual_new_eigen_solves','actual_new_angular_evaluations'):require(type(s.get(key))is int and s[key]==0,'Zero new scientific solve/field/angular work '+key)
 require(type(s.get('completed_native_geometries'))is int and s['completed_native_geometries']==expected_geometries and len(s.get('candidates',[]))==expected_geometries,'Exact actual requested native geometries')
 rows=s['candidates'];require(len({r['candidate_id']for r in rows})==expected_geometries,'Unique authenticated native geometries only')
 keys=('requested_probes','calculated_probes','unavailable_probes','strict_same_layer_bracket_available_probes','same_layer_extrapolated_probes')
 for r in rows:
  require(all(type(r.get(k))is int and r[k]>=0 for k in keys)and r['requested_probes']==40 and r['calculated_probes']+r['unavailable_probes']==40 and r['strict_same_layer_bracket_available_probes']+r['same_layer_extrapolated_probes']==r['calculated_probes'],'Each forty requests retain calculated/unavailable and strict/extrapolated counts separately')
  for k in('new_PDE_RHS','new_Q_loads','new_eigen_solves','new_angular_evaluations'):require(type(r.get(k))is int and r[k]==0,'No per-case hidden scientific recompute '+k)
  require(r.get('candidate_adopted')is False,'No per-case candidate adoption')
 for k in keys:require(type(s.get(k))is int and s[k]==sum(r[k]for r in rows),'Exact actual retained-row aggregate '+k)
 require(s['requested_probes']==40*expected_geometries and s.get('expected_threshold_subsets_per_geometry')==48,'Forty probes and four separate modes bytwo cutoffs bysix ROI')
 require(s.get('original_statistics_recomputed')is False and s.get('original_results_overwritten')is False and s.get('old600probe_predictions_preserved')is True,'Original results/statistics/predictions preserved')
 for k in('hardware_loading_validated','experimental_validation','full_convergence','physiological_activation_or_safety_claim','candidate_adopted','Windows_saved_verified'):require(s.get(k)is False,'No unsupported validation/storage/adoption claim '+k)
 require(s.get('inherited_holds',{}).get('old_13_of_14_electrical_failures_per_basis_preserved')is True and s['inherited_holds'].get('old_independent_5percent_interface_failures_preserved')is True,'Old failed diagnostics remain held')
 return dict(passed=True,completed_native_geometries=expected_geometries,**{k:s[k]for k in keys},new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,candidate_adopted=False)
def validate_MFG(r,sources,model_count,owner_count):
 require(type(model_count)is int and model_count>0 and type(owner_count)is int and owner_count>0,'Positive prospective source-AST test counts')
 require(r.get('status')=='passed'and r.get('model_source_sha256')==sources and r.get('model_source_test_count')==model_count,'Actual successful prospective tests bound to exact canonical model')
 for key,value in dict(model_tests_run=model_count,owner_tests_run=owner_count,tests_run=model_count+owner_count,expected_total_tests=model_count+owner_count,tests_failed=0,tests_errors=0,tests_skipped=0).items():require(type(r.get(key))is int and r[key]==value,'Exact successful actual test count '+key)
 require(r.get('native_RHS')==0 and r.get('native_Q_loaded')is False and r.get('native_field_reads')==0 and r.get('field_admission_granted')is False and r.get('scientific_API_spy_calls')==[],'Only bounded manufactured arrays/FFT, no actual native/cache/scientific work in tests')
 return dict(passed=True,model_tests=model_count,owner_tests=owner_count,actual_tests=model_count+owner_count)
