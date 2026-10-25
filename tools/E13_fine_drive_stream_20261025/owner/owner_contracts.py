"""Pure finite cached-allocation admission/MFG/resource gates; no native I/O."""
import math

def require(ok,message):
 if not ok:raise ValueError(message)
def fixture_elements(shape):
 if type(shape)is int:shape=(shape,)
 require(type(shape)in(tuple,list)and 0<len(shape)<=4 and all(type(n)is int and n>=0 for n in shape),'Explicit bounded manufactured shape')
 n=math.prod(shape);require(n<=65536,'Native field/Q dimensions forbidden in MFG fixtures');return n
def physical_forecast(task_temp,research_RSS,child=220000000,new_temp=35000000):
 require(all(type(n)is int and n>=0 for n in(task_temp,research_RSS,child,new_temp)),'Separate actual observed bytes and provisional forecasts')
 return task_temp+research_RSS+child+new_temp
def publication_forecast(task_temp,research_RSS,new_output=35000000,publisher_RSS=160000000):
 require(all(type(n)is int and n>=0 for n in(task_temp,research_RSS,new_output,publisher_RSS)),'Separate observed bytes and provisional publication components')
 return task_temp+research_RSS+3*new_output+publisher_RSS
def validate_owner_admission(a,sources,model_sources,model_count,owner_count):
 require(type(a)is dict and a.get('root_authorized')is True and a.get('safe_boundary_confirmed')is True,'Separate positive Root owner decision at actual safe boundary')
 require(a.get('source_sha256')==model_sources and a.get('owner_source_sha256')==sources,'Complete canonical final source maps')
 require(type(model_count)is int and model_count>0 and type(owner_count)is int and owner_count>0 and a.get('expected_model_tests')==model_count and a.get('expected_owner_tests')==owner_count,'Actual dynamic source-AST test inventory')
 require(a.get('child_RSS_forecast_bytes')==220000000 and a.get('new_owned_tmpfs_forecast_bytes')==35000000,'Unmeasured fixed provisional220MB RSS plus35MB owned temporary data; no fit by lowering at runtime')
 require(a.get('CPU_limit')==4 and a.get('physical_cap_bytes')==8000000000 and a.get('max_cells')==800000,'Unchanged CPU4/ALLresearchRSS+both-temp8GB/800k')
 for key in('candidate_adopted','browser_authorized','old_results_overwritten'):require(a.get(key)is False,'No '+key)
 return True
def validate_MFG(r,model_sources,model_count,owner_count,events):
 require(r.get('schema')=='task1-E13-fine-drive-stream-manufactured-tests-v1'and r.get('status')=='passed'and r.get('model_source_sha256')==model_sources,'Actual passed exact-source manufactured receipt')
 counts=dict(model_source_test_count=model_count,model_tests_run=model_count,owner_tests_run=owner_count,tests_run=model_count+owner_count,expected_total_tests=model_count+owner_count,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loads=0,native_field_reads=0,native_eigen_solves=0,new_angular_evaluations=0)
 require(all(type(r.get(k))is int and r[k]==v for k,v in counts.items()),'Exact complete dynamic tests and zero native work before PASS')
 require(r.get('scientific_API_spy_calls')==[]and r.get('native_IO_attempts')==[]and r.get('native_Q_loaded')is False and r.get('field_admission_granted')is False,'Caught native/scientific access cannot count as manufactured success')
 got=r.get('test_events');require(type(got)is list and len(got)==len(events)==model_count+owner_count and len({x.get('test_id')for x in got})==len(got)and {x.get('test_id')for x in got}==set(events)and all(x.get('outcome')=='passed'for x in got),'Actual unique passed test IDs equal separately published inventory')
 return dict(passed=True,actual_model_tests=model_count,actual_owner_tests=owner_count,actual_total_tests=model_count+owner_count,native_field_reads_during_MFG=0)

def source_paths(root):
 from pathlib import Path
 return sorted(p for p in Path(root).iterdir()if p.is_file()and p.suffix in('.py','.md','.json','.log')and p.name not in('root-admission.json','synthetic-test-receipt.json','tests-receipt.json','SOURCE-HASHES.json'))
def test_methods(path):
 import ast
 from pathlib import Path
 tree=ast.parse(Path(path).read_text())
 return[c.name+'.'+f.name for c in tree.body if isinstance(c,ast.ClassDef)for f in c.body if isinstance(f,ast.FunctionDef)and f.name.startswith('test_')]
def validate_summary(s):
 require(s.get('status')=='e13_fine_streamed_allocation_complete_unadopted','Actual completed cached baseline QA/two allocations, no substituted partial status')
 expected=dict(completed_conditions=3,baseline_verification_conditions=1,actual_new_metric_evaluations=2,actual_directional_metric_evaluations=3,duplicate_baseline_arrays=0,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0)
 require(all(type(s.get(k))is int and s[k]==v for k,v in expected.items()),'Exactly baseline verification1 +newratios2; no hidden PDE/Q/eigen/duplicatebaseline')
 require(s.get('baseline_agreement_passed')is True and s.get('baseline_multiplier')==1. and s.get('ratio_multipliers')==[.8,1.25],'Mandatory original baseline agreement before the exact two relative allocations')
 require(s.get('baseline_saved_float_maps')==['AM_max2074','carrier_RMS','Jtotal_vector_RMS']and s.get('unavailable_saved_float_maps')==['AM_x','AM_y','AM_z','carrier0_RMS','carrier1_RMS']and type(s.get('baseline_scalar_summary_count'))is int and s['baseline_scalar_summary_count']==8,'Only three actual saved-map pointwise gates; five unsaved maps unavailable, all eight summaries retained')
 require(s.get('candidate_adopted')is False and s.get('original_results_overwritten')is False,'Original native evidence and unadopted scope preserved')
 require(type(s.get('output_artifacts'))in(list,dict),'Explicit two-map/JSON artifact identities retained')
 return dict(passed=True,**expected,baseline_agreement_passed=True,ratio_multipliers=[.8,1.25],candidate_adopted=False)
