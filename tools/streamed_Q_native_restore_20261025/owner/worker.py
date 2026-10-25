"""Small protected tests then native cached circuit/E restore with streamed real Q."""
import argparse,builtins,contextlib,hashlib,io,json,math,os,re,resource,sys,time,unittest
from unittest.mock import patch
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');sys.path.insert(0,str(ROOT/'tools'))
import task1_execution_policy as ep
import task1_bounded_continuation as b
from owner_contracts import validate_summary,validate_cached_gates,validate_MFG,fixture_elements
import resource_scope
REMOTE='data-native/streamed-Q-native-restore-20261025/'
def new(path,value):
 raw=(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode()
 with Path(path).open('xb')as stream:stream.write(raw)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def req(ok,message):
 if not ok:raise ValueError(message)
def read_pinned(path,expected):
 path=Path(path);req(path.is_file()and not path.is_symlink()and path.stat().st_size<2*1024**2,'Canonical bounded controller metadata')
 req(sha(path)==expected,'Expected controller metadata SHA '+str(path));return json.loads(path.read_text())
def identity(path):
 path=Path(path);req(path.is_file()and not path.is_symlink(),'Canonical immutable input '+str(path));s=path.stat()
 return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def tmpfs_bytes():
 total=0
 for root in Path('/dev/shm').glob('task1-*'):
  paths=[root]if root.is_file()else root.rglob('*')
  for p in paths:
   try:
    if p.is_file():total+=p.stat().st_size
   except FileNotFoundError:pass
 return total

def virtual_peak_bytes():
 try:
  for line in Path('/proc/self/status').read_text().splitlines():
   if line.startswith('VmPeak:'):return int(line.split()[1])*1024
 except OSError:pass
 return None
def owns(pid,path):
 wanted=path.stat();kinds=set()
 for fd in Path('/proc',str(pid),'fd').glob('*'):
  try:
   actual=fd.stat()
   if(actual.st_dev,actual.st_ino)!=(wanted.st_dev,wanted.st_ino):continue
   for line in Path('/proc',str(pid),'fdinfo',fd.name).read_text().splitlines():
    if line.startswith('lock:')and(' '+str(pid)+' ')in line:
     if' FLOCK 'in line:kinds.add('FLOCK')
     if' POSIX 'in line:kinds.add('POSIX')
  except OSError:pass
 return kinds=={'FLOCK','POSIX'}
def actual_controller(pid):
 req(Path('/proc',str(pid),'exe').resolve().name.startswith('python'),'Actual parent must be Python')
 argv=[v.decode()for v in Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0')if v]
 req(argv and Path(argv[0]).name.startswith('python'),'Actual Python command required');at=1
 while at<len(argv)and argv[at].startswith('-'):
  if argv[at]=='--':at+=1;break
  req(argv[at]in('-B','-u','-E','-s','-S','-I','-O','-OO','-q','-R'),'Actual script required; no -c/-m spoofing');at+=1
 req(at<len(argv),'Actual controller script argument required')
 return(Path('/proc',str(pid),'cwd').resolve()/argv[at]).resolve()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--source',required=True);parser.add_argument('--as-limit',type=int,required=True)
 for name in('registration-sha','preregistration-sha','publication-sha','publication-plan-sha'):parser.add_argument('--'+name,required=True)
 args=parser.parse_args()
 out=Path(args.output);src=Path(args.source)
 if args.as_limit!=1200000000:raise ValueError('Preregistered finite1.2GB address-space cap required; this is not a RAM allocation')
 resource.setrlimit(resource.RLIMIT_AS,(args.as_limit,args.as_limit));limits=ep.resolve_limits();configured=ep.configure_process(limits)
 sys.path.insert(0,str(src));started=time.monotonic();cpu0=time.process_time();deadline=started+1200
 record=dict(schema='task1-streamed-Q-native-restore-worker-v1',status='failed_preserved',new_PDE_RHS=0,new_Krylov_calls=0,new_angular_evaluations=0,native_Q_read=False,full_Q_materialized=False,expected_native_E_reconstructions=2,GUI_generated=False,new_eigen_solves=0,new_native_FVM_RHS=0,candidate_adopted=False,actual_Windows_saved=False,CPU_cap=limits['cpu_limit'],configured=configured)
 proofs={};lease=None;pins={};stats={}
 def guard():
  if time.monotonic()>=deadline:raise TimeoutError('Finite1200s small tests and streamed-Q cached-native restore deadline')
  if(out/'STOP').exists():raise InterruptedError('Explicit STOP marker')
  req(lease is not None,'Authenticated actual numerical owner required')
  parent=lease['parent_pid'];tick=lease['parent_ticks']
  req(os.getppid()==parent and b.live(parent,tick),'Actual parent PID/startticks changed')
  controller=actual_controller(parent)
  req(controller==Path('/dev/shm/task1-streamed-Q-native-restore-owner-20261025/source/guardian.py')and str(controller)==lease['controller_path']and sha(controller)==lease['controller_sha256'],'Actual frozen parent controller changed')
  for name in('.task1-queue-owner.lock','.task1-loop.lock','.task1-execution.lock'):req(owns(parent,ROOT/name),'Actual parent must own both FLOCK and POSIX '+name)
  for path,expected in lease['metadata_pins'].items():req(sha(path)==expected,'Registered publication/preregistration metadata changed '+path)
  for path,expected in pins.items():
   ident=identity(path);req(ident==stats[path],'Frozen source/input stat changed '+path)
   if ident[2]<=1024**2:req(sha(path)==expected,'Frozen small source/input SHA changed '+path)
 def verify(pins,stage):
  for path,expected in pins.items():
   guard()
   if sha(path)!=expected:raise ValueError('Frozen source/input SHA mismatch '+path)
  proofs[stage]=dict(passed=True,count=len(pins))
 try:
  req(out==Path('/dev/shm/task1-streamed-Q-native-restore-20261025-run')and out==out.resolve(),'Exact registered design output')
  req(src==Path('/dev/shm/task1-streamed-Q-native-restore-20261025/source')and Path(__file__).resolve()==out/'source/owner/worker.py','Canonical scientific source plus identical published frozen snapshot')
  registration=read_pinned(out/'registration.json',args.registration_sha);prereg=read_pinned(out/'preregistration.json',args.preregistration_sha)
  publication=read_pinned(out/'source-publication/result-publication.json',args.publication_sha);plan=read_pinned(out/'source-plan.json',args.publication_plan_sha)
  parent=registration['supervisor_pid'];tick=registration['proc_start_ticks']
  req(type(parent)is int and type(tick)is int and registration['schema']=='task1-finite-native-continuation-registration-v1','Explicit finite actual-parent identity')
  req(publication['status']=='published_readback_verified'and re.fullmatch('[0-9a-f]{40}',publication['commit'])and publication['remote_branch_head_verified']==publication['commit'],'Verified immutable source-publication required')
  req(publication['expected_parent']==plan['expected_parent']and set(publication['files'])==set(plan['files']),'Exact published source/input file set and expected parent')
  for target,item in plan['files'].items():
   proof=publication['files'][target]
   req(proof['readback_passed']is True and proof['SHA256']==item['SHA256']and proof['bytes']==item['bytes']and sha(item['local_path'])==item['SHA256'],'Exact published source/input readback '+target)
  for name in('registration.json','preregistration.json','spec.json','test-source-inventory.json','root-admission.json','operator-MFG-test-receipt.json'):
   proof=publication['files'][REMOTE+name]
   req(proof['readback_passed']is True and proof['SHA256']==sha(out/name),'Actual published controller/input bytes '+name)
  pins={**prereg['source_sha256'],**prereg['frozen_source_sha256'],**prereg['input_sha256'],**prereg['helper_sha256'],**prereg['execution_policy_refs']};stats={path:identity(path)for path in pins}
  req(sha(out/'spec.json')==prereg['spec_SHA256'],'Published spec SHA mismatch')
  req(sha(out/'test-source-inventory.json')==prereg['test_inventory_SHA256'],'Exact preregistered test inventory')
  req(sha(out/'root-admission.json')==prereg['root_admission_SHA256'],'Exact actual20-operator-MFG-result-bound native restore decision')
  req(prereg['resource_forecast']['fixed_child_RLIMIT_AS_bytes']==args.as_limit,'Unchanged preregistered virtual-address limit')
  numerical=json.loads((out/'numeric-admission.json').read_text());req(numerical['child_RLIMIT_AS_bytes']==args.as_limit and numerical['physical_forecast_bytes']<=numerical['physical_cap_bytes']==limits['total_memory_bytes']==8000000000 and limits['cpu_limit']==4 and limits['max_cells']==800000,'Actual unchanged physical budget admission and distinct virtual cap')
  req(registration['source_sha256']==prereg['source_sha256'],'Controller and calculation frozen sources agree')
  lease=dict(parent_pid=parent,parent_ticks=tick,controller_path=registration['controller_path'],controller_sha256=registration['controller_sha256'],
   metadata_pins={str(out/'registration.json'):args.registration_sha,str(out/'preregistration.json'):args.preregistration_sha,str(out/'spec.json'):prereg['spec_SHA256'],str(out/'root-admission.json'):prereg['root_admission_SHA256'],str(out/'test-source-inventory.json'):prereg['test_inventory_SHA256'],str(out/'operator-MFG-test-receipt.json'):prereg['operator_MFG_receipt_SHA256'],str(out/'source-publication/result-publication.json'):args.publication_sha,str(out/'source-plan.json'):args.publication_plan_sha,str(out/'numeric-admission.json'):sha(out/'numeric-admission.json')})
  guard();record['actual_parent_authentication']=dict(parent_pid=parent,parent_start_ticks=tick,three_dual_locks=True,source_publication_commit=publication['commit'],exact_source_input_readback_verified=True)
  verify(pins,'before_tests_and_build')
  import native_restore as model
  spec=json.loads((out/'spec.json').read_text())
  admission=json.loads((out/'root-admission.json').read_text());req(admission==prereg['root_decision']==spec['root_admission'],'Published root decision and finite streamed-Q native restore specification agree')
  req(spec==model.make_spec(admission),'Exact published20-MFG/source/body/material/contact/cached-native proof chain before local tests/application')
  req(prereg['expected_cached_native_responses']==spec['expected_cached_native_responses']==2 and prereg['expected_native_E_reconstructions']==2 and prereg['whole_Q_materialization_allowed']is False and all(prereg[k]==spec[k]==0 for k in('maximum_new_PDE_RHS','maximum_new_Krylov_calls','maximum_new_eigen_solves','maximum_new_angular_evaluations')),'Prospectively published cached2responses/2RAM-onlyE and zero newPDE/Krylov/eigen/angular')
  source_model=spec['inputs']['source_sha256'];model_count=model.source_test_count();req(model_count==prereg['expected_model_tests'],'Frozen dynamic local source test count')
  actual_operator=json.loads((out/'operator-MFG-test-receipt.json').read_text());req(actual_operator==spec['inputs']['MFG_evidence']['receipt']and actual_operator['status']=='passed'and actual_operator['tests_run']==20,'Actual published operator20 PASS reused exactly, not rerun')
  import restore_inputs,restore_errors,streamed_real_q,fine_fields,fine_solver
  import numpy as np
  import numpy.ma,numpy.fft,numpy.testing
  record['dependency_initialization_before_constructor_spies']=dict(modules=['numpy.ma','numpy.fft','numpy.testing'],native_inputs_read=False,native_arrays_loaded=False,Q_loaded=False,reason='Initialize existing NumPy lazy module metadata against original constructors before bounded manufactured-only patches; no installation or scientific data access')
  stream=io.StringIO();spy_calls=[];fixture_allocations=[];real_import=builtins.__import__
  def denied(label):
   def blocked(*args,**kwargs):spy_calls.append(label);raise AssertionError('Manufactured stage cannot access actual native/cache/PDE API '+label)
   return blocked
  def manufactured_import(name,*args,**kwargs):
   if name.split('.')[0]=='scipy':return denied('scientific_import:'+name)()
   return real_import(name,*args,**kwargs)
  def fixture_size(value):
   if isinstance(value,np.ndarray):return fixture_elements(tuple(int(n)for n in value.shape))
   if isinstance(value,(tuple,list)):
    total=sum(fixture_size(item)for item in value);req(total<=65536,'Manufactured literal array fixture exceeds65536elements before allocation');return total
   req(type(value)in(int,float,complex,bool)or isinstance(value,np.generic),'Only bounded numeric manufactured literals/arrays, no arbitrary array provider');return 1
  def bounded_constructor(label,original):
   def bounded(value,*args,**kwargs):
    if label in('array','asarray'):count=fixture_size(value)
    elif label=='arange':
     vals=(value,)+args;req(1<=len(vals)<=3 and all(type(v)in(int,float)and math.isfinite(v)for v in vals),'Bounded manufactured arange scalar arguments')
     start,stop,step=(0,vals[0],1)if len(vals)==1 else(vals[0],vals[1],1)if len(vals)==2 else vals;req(step!=0,'Manufactured arange nonzero step');count=fixture_elements(max(0,math.ceil((stop-start)/step)))
    else:count=fixture_elements(value)
    fixture_allocations.append(dict(constructor=label,elements=count));return original(value,*args,**kwargs)
   return bounded
  test_results={}
  with contextlib.ExitStack()as stack:
   for module,names in((model,('build','frequency_frame','graph','checked_geometry','load','verify','sha','new','RegionWeights')),(restore_inputs,('metadata','digest','source_inventory','required_inputs')),(streamed_real_q,('StreamedRealQ',)),(fine_fields,('profiles','fields')),(fine_solver,('solve',))):
    for name in names:stack.enter_context(patch.object(module,name,side_effect=denied(module.__name__+'.'+name)))
   for name in('load','fromfile','memmap','frombuffer','save','savez','savez_compressed'):stack.enter_context(patch.object(np,name,side_effect=denied('numpy.'+name)))
   for name in('eig','eigh','eigvals','eigvalsh','solve','lstsq','inv','pinv'):stack.enter_context(patch.object(np.linalg,name,side_effect=denied('numpy.linalg.'+name)))
   for name in('array','asarray','arange','empty','zeros','ones','full'):stack.enter_context(patch.object(np,name,side_effect=bounded_constructor(name,getattr(np,name))))
   stack.enter_context(patch('builtins.__import__',side_effect=manufactured_import))
   for namespace,directory,expected in(('model',src,prereg['expected_model_tests']),('owner',out/'source/owner',prereg['expected_owner_tests'])):
    guard();suite=unittest.TestLoader().discover(str(directory),pattern='test_*.py',top_level_dir=str(directory));result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    test_results[namespace]=dict(run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),successful=result.wasSuccessful()and result.testsRun==expected and not result.skipped)
  with(out/'tests.log').open('x')as handle:handle.write(stream.getvalue())
  tests_run=sum(v['run']for v in test_results.values());successful=all(v['successful']for v in test_results.values())and not spy_calls
  mfg=dict(schema='task1-streamed-Q-native-restore-manufactured-test-receipt-v1',status='passed'if successful else'failed',kind='actual_bounded_cached_restore_error_power_and_input_contracts_before_native_operator_application',source_publication_commit=publication['commit'],model_source_sha256=source_model,model_source_test_count=model_count,model_tests_run=test_results['model']['run'],owner_tests_run=test_results['owner']['run'],tests_run=tests_run,expected_total_tests=prereg['expected_synthetic_tests'],tests_failed=sum(v['failures']for v in test_results.values()),tests_errors=sum(v['errors']for v in test_results.values()),tests_skipped=sum(v['skipped']for v in test_results.values()),per_suite=test_results,scientific_API_spy_calls=spy_calls,manufactured_array_fixture_limit_elements=65536,manufactured_array_allocations=fixture_allocations,native_RHS=0,native_Q_loaded=False,native_field_reads=0,field_admission_granted=False,candidate_adopted=False)
  new(out/'synthetic-test-receipt.json',mfg);record['test_count']=tests_run
  validate_MFG(mfg,source_model,model_count,prereg['expected_owner_tests'])
  req(successful,'Actual complete bounded-manufactured/model and owner tests must pass without native I/O/cache/solve/field work')
  test_receipt_path=str(out/'synthetic-test-receipt.json');test_receipt_SHA=sha(test_receipt_path);pins[test_receipt_path]=test_receipt_SHA;stats[test_receipt_path]=identity(test_receipt_path);lease['metadata_pins'][test_receipt_path]=test_receipt_SHA
  guard();resource_known={}
  def resource_probe():
   guard();observed=resource_scope.observe({lease['parent_pid']:lease['parent_ticks'],os.getpid():b.ticks(os.getpid())},b.ticks,resource_known);resource_known.update(observed['members']);tmp=tmpfs_bytes();aggregate=observed['research_RSS_bytes']+tmp
   req(aggregate<=8000000000,'Actual ALLresearchRSS+ALLtasktmpfs guard');return dict(scope='ALL_RSS_plus_ALL_owned_task1_tmpfs',observations_current=True,aggregate_bytes=int(aggregate),RSS_scope_detail=observed['scope'])
  new(out/'resource-entry-snapshot.json',resource_probe())
  record.update(native_Q_read=None,native_Q_application_entered=True)
  result=model.build(spec,guard,deadline_monotonic=deadline,output_dir=out)
  summary=result['summary']
  accounting=validate_summary(summary)
  req(json.loads((out/'native-restore-result.json').read_text())==summary,'Model-owned native restore result matches returned values; never rewrite model result')
  gate_checks=[]
  for response in summary['responses']:
   descriptor=response['cached_gate_receipt'];req(sha(descriptor['path'])==descriptor['SHA256'],'Actual fresh cached gate receipt SHA');gate_checks.append(validate_cached_gates(json.loads(Path(descriptor['path']).read_text())))
   qdesc=response['streamed_Q_receipt'];req(sha(qdesc['path'])==qdesc['SHA256'],'Actual streamed-Q audit receipt SHA');q=json.loads(Path(qdesc['path']).read_text());req(q['closed']is True and q['whole_Q_loaded']is False and q['complex_Q_materialized']is False and q['all_loaded_chunks_before_after_verified']is True and q['audit']['loaded_chunk_visits']>0,'Actual positive boundedQvisits/closedoperator/fullbeforeafterproof; neverfullQ')
  req(not any(p.is_file()and p.suffix.lower()in('.npz','.npy','.f64','.bin')for p in out.rglob('*')),'No new full native phi/E/Q archives')
  verify(pins,'after_build');new(out/'input-SHA-verification.json',proofs)
  new(out/'summary.json',summary)
  try:
   from threadpoolctl import threadpool_info
   new(out/'threadpool-runtime.json',threadpool_info())
  except ImportError:new(out/'threadpool-runtime.json',dict(status='not_available_no_install'))
  record.update(status='streamed_Q_cached_native_restore_computed',summary_SHA256=sha(out/'summary.json'),native_restore_accounting=accounting,cached_gate_checks=gate_checks,manufactured_test_receipt_SHA256=sha(out/'synthetic-test-receipt.json'),native_Q_read=True,full_Q_materialized=False,actual_native_E_reconstructions=2,
   scope='TwoactualcachedfineB0carriers restoredwithstreamedrealQ;0newPDE/Krylov/eigen/angular;2RAM-onlyEreconstructions/comparisons; original5/modal/current/powergatesbeforeE; fielddiagnosticfailuresretained; conditionalAM/RMSboundsnotnewangularsearch/convergence/adoption')
 except BaseException as error:
  record.update(error_type=type(error).__name__,error=str(error));observed=[]
  for path in sorted(out.glob('B0-*.json')):
   if path.is_file():observed.append(dict(path=str(path),bytes=path.stat().st_size,SHA256=sha(path)))
  for path in out.glob('B0-*-streamed-Q-receipt.json'):
   try:
    if json.loads(path.read_text()).get('audit',{}).get('loaded_chunk_visits',0)>0:record['native_Q_read']=True
   except(OSError,ValueError):pass
  new(out/'failure-status.json',dict(status='failed_partial_native_restore_preserved_no_fallback',error_type=type(error).__name__,error=str(error),observed_restore_artifacts=observed,new_PDE_RHS=0,new_Krylov_calls=0,new_eigen_solves=0,new_angular_evaluations=0,native_Q_application_status='See preserved per-frequency operator receipts/checkpoints; do not infer none from missing final audit'));raise
 finally:
  elapsed=time.monotonic()-started;cpu=time.process_time()-cpu0;record.update(elapsed_seconds=elapsed,process_CPU_seconds=cpu,average_process_CPU_cores=cpu/max(elapsed,1e-30),peak_worker_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,actual_worker_VmPeak_bytes=virtual_peak_bytes(),input_verification=proofs)
  new(out/'worker-receipt.json',record)
if __name__=='__main__':main()
