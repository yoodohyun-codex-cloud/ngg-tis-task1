"""One finite source-published twelve-fixture streamed-Q manufactured owner."""
import ast,hashlib,json,os,re,shutil,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
OWNER=Path('/dev/shm/task1-streamed-Q-MFG-owner-20261025/source')
MODEL=Path('/dev/shm/task1-streamed-Q-20261025/source')
OUT=Path('/dev/shm/task1-streamed-Q-MFG-20261025-run')
PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
LEDGER=ROOT/'runtime/task1-budget.json'
CAP=1200;NUMERIC_CAP=180;PUB_CAP=330;MAX_FILE=80*1024**2
FIXED_CHILD_AS=1000000000
PREDICTED_CHILD_RSS=200000000
EXPECTED_OUTPUT_BYTES=10000000
REMOTE='data-native/streamed-Q-MFG-20261025/'
sys.path[:0]=[str(ROOT/'tools'),str(OWNER)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget
import resource_scope
from owner_contracts import SUITES,MODEL_COUNTS,test_methods,source_paths,validate_test_receipt,validate_admission,SCOPE

def req(ok,message):
 if not ok:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text())
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def new(path,value):
 raw=(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode()
 with Path(path).open('xb')as stream:stream.write(raw)
def identity(path):
 p=Path(path);req(p.is_file()and not p.is_symlink(),'Canonical immutable input '+str(p));s=p.stat()
 return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def size(path):
 try:return path.stat().st_size if path.is_file()else sum(p.stat().st_size for p in path.rglob('*')if p.is_file())
 except FileNotFoundError:return 0
def source_inventory():
 paths={'model':source_paths(MODEL),'owner':source_paths(OWNER)}
 req(paths['model']and all(p.is_file()and not p.is_symlink()and p.stat().st_size<8*1024**2 for group in paths.values()for p in group),'Complete bounded source pack; never call field source/input APIs')
 req(sha(OWNER/'resource_scope.py')=='6c09a7cd06fed12a2e9950cc921242ef12c2a4ae999e9645ae7953d732d7873e','Exact audited resource ownership observer')
 return paths,{str(p):sha(p)for group in paths.values()for p in group},{str(p):sha(p)for p in paths['model']}
def test_inventory():
 principal={name:test_methods(MODEL/(name+'.py'))for name in SUITES};owners={p.stem:test_methods(p)for p in sorted(OWNER.glob('test_*.py'))}
 req(tuple(sorted(p.stem for p in MODEL.glob('test_*.py')))==SUITES and tuple(len(principal[name])for name in SUITES)==MODEL_COUNTS and sum(map(len,principal.values()))==12,'Exactly twelve prospectively discovered model methods in the sole frozen streamed operator suite')
 return dict(method='AST class test-method discovery, before imports/execution or field/input API calls',principal=principal,owner=owners,principal_total=sum(map(len,principal.values())),owner_total=sum(map(len,owners.values())),native_RHS=0,native_Q_eigen_work=0,native_field_angular_work=0)
def main():
 head=os.environ.get('TASK1_STREAMED_Q_MFG_EXPECTED_PARENT','')
 req(re.fullmatch('[0-9a-f]{40}',head)is not None,'Set TASK1_STREAMED_Q_MFG_EXPECTED_PARENT to the actual public40hex branch parent')
 admission_path=OWNER/'root-admission.json';req(admission_path.is_file()and not admission_path.is_symlink()and admission_path==admission_path.resolve()and admission_path.stat().st_size<1024**2,'Canonical bounded positive root MFG admission is required')
 admission=read(admission_path);packs,sources,model_sources=source_inventory();prospective=test_inventory()
 validate_admission(admission,sources,model_sources,prospective['principal_total'],prospective['owner_total']);admission_sha=sha(admission_path)
 req(sha(PUB)=='e29f03472c430598d9b7599eee28416b3453653b977a00c3d1999fa363f75f45','Exact approved standard publisher')
 with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
  req(not OUT.exists(),'Unique run required; preserve all earlier attempts');OUT.mkdir()
  for name in('logs','source-publication','result-publication','failure-publication','source','synthetic'):(OUT/name).mkdir()
  limits=ep.resolve_limits();req(limits['cpu_limit']==4 and limits['total_memory_bytes']==8000000000 and limits['max_cells']==800000,'Exact unchanged root execution limits');configured=ep.configure_process(limits);ledger=budget.load_ledger()
  req(ledger.get('cumulative_time_unlimited')is True,'Actual unlimited-time authorization required');budget.require_time_budget(ledger,CAP)
  pid=os.getpid();ticks=b.ticks(pid);start=time.monotonic();owned={pid:ticks};stop=threading.Event();mutex=threading.RLock()
  state=dict(phase='preparing',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);research_known={};counter=0;git_wall=0.
  req(source_inventory()[1]==sources,'Complete admitted source map unchanged at owner registration')
  helpers={str(ROOT/'tools'/name):sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,
   controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),
   source_sha256=sources,helper_sha256=helpers,outer_deadline_seconds=CAP,numerical_child_deadline_seconds=NUMERIC_CAP,
   resource_limits=limits,execution_policy_refs=ep.execution_policy_refs(),configured=configured,
   native_RHS=0,native_Q_eigen_work=0,native_field_angular_work=0,numerical_kind=SCOPE,root_admission_SHA256=admission_sha)
  new(OUT/'registration.json',reg)
  receipt=dict(schema='task1-streamed-Q-MFG-owner-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,
   native_RHS=0,field_admission_granted=False,actual_hardware_wiring_changed=False,GUI_generated=False,Windows_saved_verified=False,candidate_adopted=False)
  fast={};large={}
  def bind(refs,full=True):
   for path,expected in refs.items():
    ident=identity(path)
    if full:req(sha(path)==expected,'Immutable input SHA mismatch '+path)
    with mutex:
     if ident[2]<=1024**2:fast[path]=expected
     else:large[path]=(expected,ident)
  bind({**sources,**helpers,**reg['execution_policy_refs'],str(PUB):reg['publisher_sha256'],str(OUT/'registration.json'):sha(OUT/'registration.json'),str(admission_path):admission_sha})
  def checkpoint(phase,**extra):
   nonlocal counter
   with mutex:
    counter+=1;item=dict(schema='task1-streamed-Q-MFG-live-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,
     elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),item)
    for target in(OUT/'current.json',ROOT/'runtime/task1-streamed-Q-MFG-live-20261025.json'):
     tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,item);os.replace(tmp,target)
    state['phase']=phase
  def guard():
   with mutex:
    live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);fast_now=dict(fast);large_now=dict(large);known_now=dict(research_known)
   observation=resource_scope.observe(live,b.ticks,known_now);rss=observation['research_RSS_bytes'];tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
   with mutex:
    research_known.update(observation['members']);state['latest_process_audit']=observation;state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp))
   req(rss+tmp<=limits['total_memory_bytes'],'Actual ALL research-owned-family RSS plus ALL task1-ownedtmpfs cap')
   req(time.monotonic()-start<CAP,'Finite1200s synthetic owner watchdog');req(not(OUT/'STOP').exists(),'Explicit STOP marker')
   for path,expected in fast_now.items():req(sha(path)==expected,'Frozen small source/input/policy changed '+path)
   for path,(_,ident)in large_now.items():req(identity(path)==ident,'Large immutable input stat identity changed '+path)
  def interrupt(signum,frame):raise InterruptedError(state.get('error','Finite watchdog or external signal'))
  def monitor():
   last=0.
   while not stop.wait(.25):
    try:
     guard()
     if time.monotonic()-last>=5:checkpoint(state['phase'],observed_peak_RSS=state['peak_RSS'],observed_peak_owned_tmpfs=state['peak_owned_tmpfs']);last=time.monotonic()
    except BaseException as error:state['error']=str(error);os.kill(pid,signal.SIGTERM);return
  handlers={sig:signal.getsignal(sig)for sig in(signal.SIGALRM,signal.SIGINT,signal.SIGTERM)}
  for sig in handlers:signal.signal(sig,interrupt)
  signal.setitimer(signal.ITIMER_REAL,CAP);thread=threading.Thread(target=monitor,daemon=True);thread.start()
  def command(argv,label,seconds,is_git=False,allow_failure=False):
   nonlocal git_wall
   guard();checkpoint(label);log=OUT/'logs'/(str(counter)+'-'+label+'.log');before=time.monotonic();rows_before=len(budget.load_ledger()['runs'])
   with log.open('xb')as stream:
    child=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    with mutex:owned[child.pid]=b.ticks(child.pid)
    checkpoint(label,child_pid=child.pid,child_start_ticks=owned[child.pid],child_timeout_seconds=seconds)
    try:code=child.wait(timeout=max(.01,min(seconds,CAP-(time.monotonic()-start))))
    finally:
     if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
     if is_git:
      child_run=Path(argv[argv.index('--output')+1]).name
      recorded=sum(row.get('seconds',0.)for row in budget.load_ledger()['runs'][rows_before:]if row.get('run_id')==child_run)
      git_wall+=min(time.monotonic()-before,recorded)
   if not allow_failure:req(code==0,'Finite child failed '+label+'; preserve log '+str(log))
   return code
  def plan(files,parent,message,destination,comment=None):
   for path in files.values():req(path.is_file()and not path.is_symlink()and path.stat().st_size<MAX_FILE,'Preserve file and report publication bound '+str(path))
   return dict(schema='task1-supported-Git-transport-plan-v1',repository='yoodohyun-codex-cloud/ngg-tis-task1',branch='codex/task1-cloud-restart-20261020',expected_parent=parent,message=message,
    files={target:dict(local_path=str(path),SHA256=sha(path),bytes=path.stat().st_size)for target,path in files.items()},required_result_receipt=str(destination),required_receipt_status='published_readback_verified',new_PDE_required=False,comment_body=comment)
  def fixture_inventory():
   target=OUT/'synthetic-fixture-inventory.json'
   if target.exists():return
   rows=[];total=0
   for path in sorted((OUT/'synthetic').rglob('*')):
    if path.is_symlink():rows.append(dict(path=str(path.relative_to(OUT)),kind='preserved_negative_symlink_fixture',link_target=os.readlink(path),published_as_regular_file=False));continue
    if path.is_file():
     count=path.stat().st_size;req(count<=4096,'Bounded synthetic file before preservation');total+=count
     rows.append(dict(path=str(path.relative_to(OUT)),kind='synthetic_fixture_only',bytes=count,SHA256=sha(path)))
   req(total<=65536,'Bounded total synthetic fixture preservation');new(target,dict(schema='task1-streamed-Q-MFG-synthetic-fixtures-v1',files=rows,total_regular_bytes=total,native_files_read=0,not_original_native_Q=True))
  try:
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    tests=test_inventory();new(OUT/'test-source-inventory.json',tests);frozen={}
    for namespace,paths in packs.items():
     directory=OUT/'source'/namespace;directory.mkdir()
     for path in paths:
      target=directory/path.name
      with target.open('xb')as stream:stream.write(path.read_bytes())
      req(sha(target)==sources[str(path)],'Exact synthetic source snapshot');frozen[str(target)]=sha(target)
    req(sha(admission_path)==admission_sha and read(admission_path)==admission,'Root admission immutable before source publication')
    with(OUT/'root-admission.json').open('xb')as stream:stream.write(admission_path.read_bytes())
    admission_refs={str(admission_path):admission_sha,str(OUT/'root-admission.json'):admission_sha};refs={**helpers,**reg['execution_policy_refs'],**admission_refs,str(OUT/'test-source-inventory.json'):sha(OUT/'test-source-inventory.json')}
    new(OUT/'preregistration.json',dict(schema='task1-streamed-Q-MFG-preregistration-v1',
     question='Execute twelve frozen streamed real-Q operator manufactured fixtures and separate owner contracts once after actual source readback. Zero native file/Q/eigen/PDE/full-field work; only canonical OUT/synthetic files and bounded 6x6 fixture operators. Root confirms the safe boundary. Fresh cached native B0 five-gate physics restoration remains mandatory before any new PDE.',
     source_sha256=sources,frozen_source_sha256=frozen,model_source_sha256=model_sources,helper_sha256=helpers,execution_policy_refs=reg['execution_policy_refs'],limits=limits,
     expected_principal_tests=tests['principal_total'],expected_owner_tests=tests['owner_total'],test_inventory_SHA256=sha(OUT/'test-source-inventory.json'),
     suites=list(SUITES),test_inventory=tests,admission_input_sha256=admission_refs,root_admission_SHA256=admission_sha,native_RHS=0,native_Q_loaded=False,native_eigen_performed=False,native_field_reads=0,field_admission_granted=False,
     hard_child_seconds=NUMERIC_CAP,physical_forecast_child_RSS_bytes=PREDICTED_CHILD_RSS,physical_forecast_output_bytes=EXPECTED_OUTPUT_BYTES,fixed_child_RLIMIT_AS_bytes=FIXED_CHILD_AS,
     numerical_scope=SCOPE,synthetic_fixture_root=str(OUT/'synthetic'),synthetic_operator_shape=[6,6],maximum_synthetic_allocation_elements=4096,maximum_fixture_file_bytes=4096,maximum_all_fixture_bytes=65536,native_file_reads=0,native_restore_performed=False))
    bind({**sources,**frozen,**refs,str(OUT/'preregistration.json'):sha(OUT/'preregistration.json')})
   files={}
   for path in(OUT/'source').rglob('*'):
    if path.is_file():files['tools/streamed_Q_MFG_20261025/'+path.relative_to(OUT/'source').as_posix()]=path
   for name in('registration.json','preregistration.json','test-source-inventory.json','root-admission.json'):files[REMOTE+name]=OUT/name
   spath=OUT/'source-plan.json';new(spath,plan(files,head,'Preregister twelve tiny streamed-Q operator fixtures; no native restore or PDE admission',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(spath),'--output','/dev/shm/task1-git-streamed-Q-MFG-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',PUB_CAP,True)
   published=read(OUT/'source-publication/result-publication.json');req(published['status']=='published_readback_verified','Actual source readback before importing/running tests')
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    guard();tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
    with mutex:authenticated=dict(owned);known_now=dict(research_known)
    observation=resource_scope.observe(authenticated,b.ticks,known_now)
    with mutex:research_known.update(observation['members']);state['latest_process_audit']=observation
    physical_forecast=tmp+observation['research_RSS_bytes']+PREDICTED_CHILD_RSS+EXPECTED_OUTPUT_BYTES
    req(physical_forecast<=limits['total_memory_bytes']==8000000000 and limits['cpu_limit']==4 and limits['max_cells']==800000,'Unchanged actual whole-task physical budget before small tests')
    new(OUT/'numeric-admission.json',dict(kind=SCOPE,all_owned_tmpfs_bytes=tmp,parent_RSS_bytes=b.rss(pid),all_research_RSS_bytes=observation['research_RSS_bytes'],research_scope=observation['scope'],forecast_child_RSS_bytes=PREDICTED_CHILD_RSS,forecast_new_output_bytes=EXPECTED_OUTPUT_BYTES,physical_forecast_bytes=physical_forecast,physical_cap_bytes=limits['total_memory_bytes'],child_RLIMIT_AS_bytes=FIXED_CHILD_AS,field_admission_granted=False))
    bind({str(OUT/'numeric-admission.json'):sha(OUT/'numeric-admission.json')})
    code=command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(OUT/'source/owner/worker.py'),'--output',str(OUT),
     '--registration-sha',sha(OUT/'registration.json'),'--preregistration-sha',sha(OUT/'preregistration.json'),'--publication-sha',sha(OUT/'source-publication/result-publication.json'),'--publication-plan-sha',sha(spath)],'small-synthetic-test-child',NUMERIC_CAP,allow_failure=True)
   fixture_inventory();missing=[name for name in('synthetic-test-receipt.json','worker-receipt.json','input-SHA-verification.json')if not(OUT/name).is_file()]
   new(OUT/'missing-result-inventory.json',dict(status='actual_absence_preserved',missing=missing,worker_fabricated=False))
   testpath=OUT/'synthetic-test-receipt.json';test_receipt=read(testpath)if testpath.is_file()else None;passed=False
   if code==0 and test_receipt is not None:
    accounting=validate_test_receipt(test_receipt,tests['principal_total'],tests['owner_total'],model_sources);passed=accounting['tests_passed']
   else:accounting=dict(scope_passed=False,tests_passed=False,worker_exit_code=code,test_receipt_present=test_receipt is not None,field_admission_granted=False)
   with mutex:all_pins={**fast,**{path:value[0]for path,value in large.items()}}
   for path,expected in all_pins.items():guard();req(sha(path)==expected,'Complete source/policy SHA after synthetic tests')
   new(OUT/'research-process-accounting.json',state.get('latest_process_audit',{}))
   new(OUT/'execution-stage.json',dict(status='tests_passed'if passed else'tests_failed_or_incomplete_preserved',worker_exit_code=code,accounting=accounting,native_RHS=0,field_admission_granted=False,source_commit=published['commit']))
   files={}
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and not path.is_symlink()and(rel.parts[0]in('logs','synthetic')or(len(rel.parts)==1 and path.name not in('current.json','source-plan.json','result-plan.json'))):files[REMOTE+rel.as_posix()]=path
   files[REMOTE+'source-publication-receipt.json']=OUT/'source-publication/result-publication.json'
   rp=OUT/'result-plan.json';new(rp,plan(files,published['commit'],'Preserve actual tiny streamed-Q manufactured test outcomes; native restore absent',OUT/'result-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(rp),'--output','/dev/shm/task1-git-streamed-Q-MFG-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',PUB_CAP,True)
   result=read(OUT/'result-publication/result-publication.json');req(result['status']=='published_readback_verified','Full result/error publication readback')
   receipt.update(status='synthetic_tests_passed_published_field_not_admitted'if passed else'synthetic_tests_failed_published_field_not_admitted',source_commit=published['commit'],result_commit=result['commit'],test_accounting=accounting)
   checkpoint('synthetic_review_complete_field_admission_pending',result_commit=result['commit'],tests_passed=passed)
  except BaseException as error:
   failed=state['phase'];receipt.update(error_type=type(error).__name__,error=str(error),failed_phase=failed)
   try:
    checkpoint('failed_preserved',failed_phase=failed,error=str(error));fixture_inventory()
    new(OUT/'failure-outcome.json',dict(status='failed_preserved',error_type=type(error).__name__,error=str(error),failed_phase=failed,native_restore_performed=False,field_admission_granted=False))
    spub=OUT/'source-publication/result-publication.json'
    if spub.is_file()and read(spub).get('status')=='published_readback_verified'and not(OUT/'result-publication/result-publication.json').exists():
     files={}
     for path in OUT.rglob('*'):
      rel=path.relative_to(OUT)
      if path.is_file()and not path.is_symlink()and(rel.parts[0]in('logs','synthetic')or(len(rel.parts)==1 and path.name not in('current.json','source-plan.json','result-plan.json','failure-plan.json'))):files[REMOTE+rel.as_posix()]=path
     files[REMOTE+'source-publication-receipt.json']=spub
     missing=[name for name in('synthetic-test-receipt.json','worker-receipt.json','input-SHA-verification.json')if not(OUT/name).is_file()]
     if not(OUT/'missing-result-inventory.json').exists():new(OUT/'missing-result-inventory.json',dict(status='actual_absence_preserved',missing=missing,worker_fabricated=False))
     files[REMOTE+'missing-result-inventory.json']=OUT/'missing-result-inventory.json'
     fp=OUT/'failure-plan.json';new(fp,plan(files,read(spub)['commit'],'Preserve failed or incomplete streamed-Q manufactured attempt and actual absent outputs',OUT/'failure-publication/result-publication.json'))
     # No numerical continuation or lock acquisition here; only the standard
     # separately bounded publisher owns its normal three dual locks.
     command([sys.executable,'-B',str(PUB),'--plan',str(fp),'--output','/dev/shm/task1-git-streamed-Q-MFG-failure-20261025','--queue-registration',str(OUT/'registration.json')],'failure-result-publication',PUB_CAP,True)
     failure_pub=read(OUT/'failure-publication/result-publication.json');req(failure_pub['status']=='published_readback_verified','Actual failure result readback');receipt['failure_result_commit']=failure_pub['commit']
   except BaseException as preservation_error:
    receipt['failure_publication_error']=str(preservation_error)
   raise

  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   for child,tick in b.owned_descendants(pid,ticks,dict(owned)).items():
    if child!=pid and b.live(child,tick):
     try:os.kill(child,signal.SIGKILL)
     except ProcessLookupError:pass
   elapsed=time.monotonic()-start;ledger=budget.load_ledger();debit=max(0.,elapsed-git_wall);ledger['spent_seconds']+=debit
   ledger['runs'].append(dict(run_id=OUT.name,stage='streamed_Q_MFG_tests_and_supervision',seconds=debit,status=receipt['status'],Git_children_debited_separately=True))
   temp=LEDGER.with_name('task1-budget-streamed-Q-MFG-'+str(pid)+'.tmp');new(temp,ledger);os.replace(temp,LEDGER)
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')},remaining_approved_seconds=budget.remaining_seconds(ledger));new(OUT/'receipt.json',receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
