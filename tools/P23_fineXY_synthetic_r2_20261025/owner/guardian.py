"""One finite source-published47-model manufactured/MMS/overlay test owner."""
import ast,hashlib,json,os,re,shutil,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
OWNER=Path('/dev/shm/task1-P23-fineXY-synthetic-r2-owner-20261025/source')
MODEL=Path('/dev/shm/task1-P23-fineXY-20261025/source')
OUT=Path('/dev/shm/task1-P23-fineXY-synthetic-r2-20261025-run')
PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
LEDGER=ROOT/'runtime/task1-budget.json'
CAP=600;NUMERIC_CAP=180;PUB_CAP=330;MAX_FILE=80*1024**2
FIXED_CHILD_AS=1000000000
PREDICTED_CHILD_RSS=200000000
EXPECTED_OUTPUT_BYTES=10000000
REMOTE='data-native/P23-fineXY-synthetic-r2-20261025/'
sys.path[:0]=[str(ROOT/'tools'),str(OWNER)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget
import resource_scope
from owner_contracts import SUITES,MODEL_COUNTS,test_methods,source_paths,validate_test_receipt

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
def historical_failure_inputs(model_sources):
 path=OWNER/'prior-first-synthetic-failure-evidence.json';evidence=read(path);req(evidence['schema']=='task1-prior-fine47-synthetic-boundary-failure-evidence-v1'and evidence['actual_previous_status']=='failed'and evidence['actual_previous_tests_run']==52,'Actual first-run failed52 evidence, never a valid field-test PASS')
 old=evidence['evidence']['synthetic-test-receipt.json']['record'];req(old['status']=='failed'and old['model_source_sha256']==model_sources and old['native_IO_attempts']==[]and old['forbidden_field_calls']==['synthetic_angular_metric_fixture_calls'],'Frozen47 model remains byte-identical; previous boundary attempt remains failed')
 refs={str(path):sha(path)}
 for item in evidence['evidence'].values():
  original=Path(item['path']);req(original.is_file()and not original.is_symlink()and original==original.resolve()and original.stat().st_size==item['bytes']and sha(original)==item['SHA256'],'Original failed test/source/publication evidence byte identity');refs[str(original)]=item['SHA256']
 return refs
def test_inventory():
 principal={name:test_methods(MODEL/(name+'.py'))for name in SUITES};owners={p.stem:test_methods(p)for p in sorted(OWNER.glob('test_*.py'))}
 req(tuple(sorted(p.stem for p in MODEL.glob('test_*.py')))==SUITES and tuple(len(principal[name])for name in SUITES)==MODEL_COUNTS and sum(map(len,principal.values()))==47,'Exactly47 prospectively discovered frozen model methods across ten actual suites')
 return dict(method='AST class test-method discovery, before imports/execution or field/input API calls',principal=principal,owner=owners,principal_total=sum(map(len,principal.values())),owner_total=sum(map(len,owners.values())),native_RHS=0,native_Q_eigen_work=0,native_field_angular_work=0)
def main():
 head=os.environ.get('TASK1_FINE_SYNTHETIC_EXPECTED_PARENT','')
 req(re.fullmatch('[0-9a-f]{40}',head)is not None,'Set TASK1_FINE_SYNTHETIC_EXPECTED_PARENT to the actual public40hex branch parent')
 with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
  req(not OUT.exists(),'Unique run required; preserve all earlier attempts');OUT.mkdir()
  for name in('logs','source-publication','result-publication','source'):(OUT/name).mkdir()
  limits=ep.resolve_limits();configured=ep.configure_process(limits);ledger=budget.load_ledger()
  req(ledger.get('cumulative_time_unlimited')is True,'Actual unlimited-time authorization required');budget.require_time_budget(ledger,CAP)
  pid=os.getpid();ticks=b.ticks(pid);start=time.monotonic();owned={pid:ticks};stop=threading.Event();mutex=threading.RLock()
  state=dict(phase='preparing',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);research_known={};counter=0;git_wall=0.
  packs,sources,model_sources=source_inventory()
  helpers={str(ROOT/'tools'/name):sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,
   controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),
   source_sha256=sources,helper_sha256=helpers,outer_deadline_seconds=CAP,numerical_child_deadline_seconds=NUMERIC_CAP,
   resource_limits=limits,execution_policy_refs=ep.execution_policy_refs(),configured=configured,
   native_RHS=0,native_Q_eigen_work=0,native_field_angular_work=0,numerical_kind='manufactured_MMS_overlay_projection_and_contracts_only')
  new(OUT/'registration.json',reg)
  receipt=dict(schema='task1-P23-fineXY-synthetic-r2-owner-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,
   native_RHS=0,field_admission_granted=False,actual_hardware_wiring_changed=False,GUI_generated=False,Windows_saved_verified=False,candidate_adopted=False)
  fast={};large={}
  def bind(refs,full=True):
   for path,expected in refs.items():
    ident=identity(path)
    if full:req(sha(path)==expected,'Immutable input SHA mismatch '+path)
    with mutex:
     if ident[2]<=1024**2:fast[path]=expected
     else:large[path]=(expected,ident)
  bind({**sources,**helpers,**reg['execution_policy_refs'],str(PUB):reg['publisher_sha256'],str(OUT/'registration.json'):sha(OUT/'registration.json')})
  def checkpoint(phase,**extra):
   nonlocal counter
   with mutex:
    counter+=1;item=dict(schema='task1-P23-fineXY-synthetic-r2-live-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,
     elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),item)
    for target in(OUT/'current.json',ROOT/'runtime/task1-P23-fineXY-synthetic-r2-live-20261025.json'):
     tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,item);os.replace(tmp,target)
    state['phase']=phase
  def guard():
   with mutex:
    live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);fast_now=dict(fast);large_now=dict(large);known_now=dict(research_known)
   observation=resource_scope.observe(live,b.ticks,known_now);rss=observation['research_RSS_bytes'];tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
   with mutex:
    research_known.update(observation['members']);state['latest_process_audit']=observation;state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp))
   req(rss+tmp<=limits['total_memory_bytes'],'Actual ALL research-owned-family RSS plus ALL task1-ownedtmpfs cap')
   req(time.monotonic()-start<CAP,'Finite600s synthetic owner watchdog');req(not(OUT/'STOP').exists(),'Explicit STOP marker')
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
  try:
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    tests=test_inventory();new(OUT/'test-source-inventory.json',tests);frozen={}
    for namespace,paths in packs.items():
     directory=OUT/'source'/namespace;directory.mkdir()
     for path in paths:
      target=directory/path.name
      with target.open('xb')as stream:stream.write(path.read_bytes())
      req(sha(target)==sources[str(path)],'Exact synthetic source snapshot');frozen[str(target)]=sha(target)
    history_refs=historical_failure_inputs(model_sources);refs={**helpers,**reg['execution_policy_refs'],**history_refs,str(OUT/'test-source-inventory.json'):sha(OUT/'test-source-inventory.json')}
    new(OUT/'preregistration.json',dict(schema='task1-P23-fineXY-synthetic-r2-preregistration-v1',
     question='Execute exactly47 unchanged frozen model synthetic/MMS/overlay/projection methods plus separate owner contracts once after preserving the original failed52 boundary attempt. A single exact expired-deadline null-data negative fixture must reject before any data access; no broader field API exemption. No field model API/controller make_spec/required_inputs, native data/cache/Q/eigen/PDE/fullfield exports. Only tiny bounded manufactured matrices and synthetic geometry fixtures are allowed; field admission remains separate after actual result readback and root review.',
     source_sha256=sources,frozen_source_sha256=frozen,model_source_sha256=model_sources,helper_sha256=helpers,execution_policy_refs=reg['execution_policy_refs'],limits=limits,
     expected_principal_tests=tests['principal_total'],expected_owner_tests=tests['owner_total'],test_inventory_SHA256=sha(OUT/'test-source-inventory.json'),
     suites=list(SUITES),test_inventory=tests,historical_input_sha256=history_refs,prior_failure_evidence_SHA256=sha(OWNER/'prior-first-synthetic-failure-evidence.json'),native_RHS=0,native_Q_loaded=False,native_eigen_performed=False,native_field_reads=0,field_admission_granted=False,
     hard_child_seconds=NUMERIC_CAP,physical_forecast_child_RSS_bytes=PREDICTED_CHILD_RSS,physical_forecast_output_bytes=EXPECTED_OUTPUT_BYTES,fixed_child_RLIMIT_AS_bytes=FIXED_CHILD_AS,
     numerical_scope='Manufactured CEM Qn<=4, analytic depth<=4, synthetic angular fixture<=64cells, projector<=36nodes and generated physical-overlap fixtures; no original dataset/Q/eigen/field read or native phantom RHS'))
    bind({**sources,**frozen,**refs,str(OUT/'preregistration.json'):sha(OUT/'preregistration.json')})
   files={}
   for path in(OUT/'source').rglob('*'):
    if path.is_file():files['tools/P23_fineXY_synthetic_r2_20261025/'+path.relative_to(OUT/'source').as_posix()]=path
   for name in('registration.json','preregistration.json','test-source-inventory.json'):files[REMOTE+name]=OUT/name
   spath=OUT/'source-plan.json';new(spath,plan(files,head,'Preregister47 frozen fine-model synthetic/MMS/overlay tests; no native field admission',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(spath),'--output','/dev/shm/task1-git-P23-fineXY-synthetic-r2-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',PUB_CAP,True)
   published=read(OUT/'source-publication/result-publication.json');req(published['status']=='published_readback_verified','Actual source readback before importing/running tests')
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    guard();tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
    with mutex:authenticated=dict(owned);known_now=dict(research_known)
    observation=resource_scope.observe(authenticated,b.ticks,known_now)
    with mutex:research_known.update(observation['members']);state['latest_process_audit']=observation
    physical_forecast=tmp+observation['research_RSS_bytes']+PREDICTED_CHILD_RSS+EXPECTED_OUTPUT_BYTES
    req(physical_forecast<=limits['total_memory_bytes']==8000000000 and limits['cpu_limit']==4 and limits['max_cells']==800000,'Unchanged actual whole-task physical budget before small tests')
    new(OUT/'numeric-admission.json',dict(kind='synthetic_small_matrix_only',all_owned_tmpfs_bytes=tmp,parent_RSS_bytes=b.rss(pid),all_research_RSS_bytes=observation['research_RSS_bytes'],research_scope=observation['scope'],forecast_child_RSS_bytes=PREDICTED_CHILD_RSS,forecast_new_output_bytes=EXPECTED_OUTPUT_BYTES,physical_forecast_bytes=physical_forecast,physical_cap_bytes=limits['total_memory_bytes'],child_RLIMIT_AS_bytes=FIXED_CHILD_AS,field_admission_granted=False))
    bind({str(OUT/'numeric-admission.json'):sha(OUT/'numeric-admission.json')})
    code=command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(OUT/'source/owner/worker.py'),'--output',str(OUT),
     '--registration-sha',sha(OUT/'registration.json'),'--preregistration-sha',sha(OUT/'preregistration.json'),'--publication-sha',sha(OUT/'source-publication/result-publication.json'),'--publication-plan-sha',sha(spath)],'small-synthetic-test-child',NUMERIC_CAP,allow_failure=True)
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
    if path.is_file()and(rel.parts[0]=='logs'or(len(rel.parts)==1 and path.name not in('current.json','source-plan.json','result-plan.json'))):files[REMOTE+rel.as_posix()]=path
   files[REMOTE+'source-publication-receipt.json']=OUT/'source-publication/result-publication.json'
   rp=OUT/'result-plan.json';new(rp,plan(files,published['commit'],'Preserve actual47-model MMS/overlay/projection test results; field admission remains separate',OUT/'result-publication/result-publication.json',
    comment='고정 D50 P23/B0의 세분 XY 후속 계산 전에 소형 제조해·MMS·물리 겹침·보간·소스 계약 테스트47개와 독립 owner 계약을 유한 배치로 실행하고 실제 결과·오류·로그·공개 소스 SHA를 보존했습니다. 원래 native 데이터·Q·고유계산·팬텀 PDE·전체 전기장 또는 원래 각도 지표를 계산하지 않았습니다. 소형 합성 행렬 계산과 합성 형상 검증은 별도로 기록하며, 실제 native 계산3 RHS와 조건부 B0@2000 재사용은 이 테스트 결과의 공개 readback 및 별도 root 검토 전에는 허가하지 않습니다. 실패는 보존하며 네 번째 RHS 대체·팬텀 확장·후보 채택·수렴·실험·인체안전 주장을 하지 않습니다. 실제 테스트 상태: '+('passed'if passed else'failed_or_incomplete_preserved')))
   command([sys.executable,'-B',str(PUB),'--plan',str(rp),'--output','/dev/shm/task1-git-P23-fineXY-synthetic-r2-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',PUB_CAP,True)
   result=read(OUT/'result-publication/result-publication.json');req(result['status']=='published_readback_verified','Full result/error publication readback')
   receipt.update(status='synthetic_tests_passed_published_field_not_admitted'if passed else'synthetic_tests_failed_published_field_not_admitted',source_commit=published['commit'],result_commit=result['commit'],test_accounting=accounting)
   checkpoint('synthetic_review_complete_field_admission_pending',result_commit=result['commit'],tests_passed=passed)
  except BaseException as error:
   failed=state['phase'];receipt.update(error_type=type(error).__name__,error=str(error),failed_phase=failed)
   checkpoint('failed_preserved',failed_phase=failed,error=str(error));raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   for child,tick in b.owned_descendants(pid,ticks,dict(owned)).items():
    if child!=pid and b.live(child,tick):
     try:os.kill(child,signal.SIGKILL)
     except ProcessLookupError:pass
   elapsed=time.monotonic()-start;ledger=budget.load_ledger();debit=max(0.,elapsed-git_wall);ledger['spent_seconds']+=debit
   ledger['runs'].append(dict(run_id=OUT.name,stage='P23_fineXY_synthetic_tests_and_supervision',seconds=debit,status=receipt['status'],Git_children_debited_separately=True))
   temp=LEDGER.with_name('task1-budget-P23-fineXY-synthetic-r2-'+str(pid)+'.tmp');new(temp,ledger);os.replace(temp,LEDGER)
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')},remaining_approved_seconds=budget.remaining_seconds(ledger));new(OUT/'receipt.json',receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
