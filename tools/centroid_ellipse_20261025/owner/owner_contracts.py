"""Pure finite ellipse accounting and source-bound manufactured-test gates."""
def require(ok,message):
 if not ok:raise ValueError(message)
def fixture_elements(shape,limit=4096):
 dims=(shape,)if type(shape)is int else tuple(shape)
 require(all(type(n)is int and n>=0 for n in dims),'Manufactured array dimensions are nonnegative Python integers')
 total=1
 for n in dims:
  total*=n;require(total<=limit,'Manufactured arrays are bounded before allocation; native graph/Q shapes forbidden')
 return total
def validate_summary(s):
 require(s.get('status')=='single_centroid_area_matched_ellipse_screen_computed_unadopted','Exact complete conditional ellipse result status')
 expected=dict(completed_conditions=3,actual_new_driven_RHS=2,actual_new_angular_metric_evaluations=1,actual_immutable_control_aliases=2,actual_control_RHS_repeated=0,actual_control_angular_metrics_repeated=0,new_eigen_solves=0)
 for key,value in expected.items():require(type(s.get(key))is int and s[key]==value,'Exact finite work and alias count '+key)
 rows=s.get('candidates',[]);require(len(rows)==3 and s.get('Q_resident_during_metrics')is False and s.get('originals_overwritten')is False and s.get('candidate_adopted')is False,'Three results only after Q frame ends; no overwrite/adoption')
 aliases=[r for r in rows if r.get('control_alias')is True];new=[r for r in rows if r.get('control_alias')is False]
 require(len(aliases)==2 and len(new)==1 and len({r['candidate_id']for r in rows})==3,'Exactly one new geometry and two immutable controls')
 for row in aliases:require(row.get('new_PDE_RHS')==0 and row.get('new_angular_metric_evaluations')==0,'No control solve or angular work')
 proofs=new[0].get('source_physics_proofs',[])
 require(len(proofs)==2 and {p.get('frequency_Hz')for p in proofs}=={2000,2010}and all(p.get('passed')is True and p.get('passivity_passed')is True and p.get('physical_gates',{}).get('passed')is True and p.get('actual_new_RHS')==1 for p in proofs),'Both fresh unchanged source/current/power/passivity gates must pass')
 require(s.get('holds',{}).get('old_13_of_14_XY_contact_failures_preserved')is True and s['holds'].get('fractional_contact_and_edge_peak_uncertainty')is True and s['holds'].get('full_convergence')is False,'Old failures/partial-area uncertainty held; candidate screen is not convergence')
 return dict(passed=True,**expected,full_convergence=False,candidate_adopted=False)
def validate_MFG(r,sources,model_count,owner_count):
 require(type(model_count)is int and model_count>0 and type(owner_count)is int and owner_count>0,'Positive prospective source-AST counts')
 require(r.get('status')=='passed'and r.get('model_source_sha256')==sources and r.get('model_source_test_count')==model_count,'Actual manufactured test PASS bound to exact canonical model sources')
 expected=dict(model_tests_run=model_count,owner_tests_run=owner_count,tests_run=model_count+owner_count,expected_total_tests=model_count+owner_count,tests_failed=0,tests_errors=0,tests_skipped=0)
 for key,value in expected.items():require(type(r.get(key))is int and r[key]==value,'Exact successful prospective test count '+key)
 require(r.get('native_RHS')==0 and r.get('native_Q_loaded')is False and r.get('native_field_reads')==0 and r.get('field_admission_granted')is False and r.get('scientific_API_spy_calls')==[],'Manufactured proof has no actual native field/cache/PDE work or admission')
 return dict(passed=True,model_tests=model_count,owner_tests=owner_count,actual_tests=model_count+owner_count)
