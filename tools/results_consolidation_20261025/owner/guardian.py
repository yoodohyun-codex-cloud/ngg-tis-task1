"""One finite source-published cached native-results consolidation and GUI."""
import ast,hashlib,json,os,re,shutil,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
OWNER=Path('/dev/shm/task1-results-consolidation-owner-20261025/source')
SRC=Path('/dev/shm/task1-results-consolidation-20261025/source')
ADMISSION=SRC/'root-admission.json'
OUT=Path('/dev/shm/task1-results-consolidation-20261025-run')
PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
LEDGER=ROOT/'runtime/task1-budget.json'
CAP=2400;NUMERIC_CAP=1200;PUB_CAP=330;MAX_FILE=80*1024**2
VIRTUAL_RESERVE=150000000
RESOURCE_FORECAST=dict(new_PDE_RHS=0,new_angular_evaluations=0,Q_loaded=False,extra_virtual_address_reserve_bytes=VIRTUAL_RESERVE,
 maximum_child_RLIMIT_AS_bytes=2000000000,minimum_child_RLIMIT_AS_bytes=800000000,
 aggregate_RSS_plus_all_task_tmpfs_cap_bytes=8000000000,aggregate_guard_unchanged=True,CPU_cap_unchanged=4,
 interpretation='Finite cached postprocessing with no Q; reserve does not change the aggregate8GB budget or watchdog')
REMOTE='data-native/results-consolidation-20261025/'
sys.path[:0]=[str(ROOT/'tools'),str(SRC)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget
from owner_contracts import validate_consolidation_summary

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
def test_inventory():
 rows={}
 for namespace,directory in(('model',SRC),('owner',OWNER)):
  for path in sorted(directory.glob('test_*.py')):
   tree=ast.parse(path.read_text(),filename=str(path))
   rows[namespace+'/'+path.name]=sum(1 for cls in tree.body if isinstance(cls,ast.ClassDef)for item in cls.body if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef))and item.name.startswith('test_'))
 req(sum(rows.values())>0,'Prospectively count actual synthetic test methods from source AST')
 return dict(method='AST class test-method definitions, before execution',counts=rows,total=sum(rows.values()))
def main():
 head=os.environ.get('TASK1_CONSOLIDATION_EXPECTED_PARENT','')
 req(re.fullmatch('[0-9a-f]{40}',head)is not None,'Set TASK1_CONSOLIDATION_EXPECTED_PARENT to the actual public40hex branch parent')
 req(ADMISSION.is_file()and not ADMISSION.is_symlink(),'Positive root selection bound to completed mixed R2 and immutable cached native datasets required')
 with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
  req(not OUT.exists(),'Unique run required; preserve all earlier attempts');OUT.mkdir()
  for name in('logs','source-publication','result-publication','source'):(OUT/name).mkdir()
  limits=ep.resolve_limits();configured=ep.configure_process(limits);ledger=budget.load_ledger()
  req(ledger.get('cumulative_time_unlimited')is True,'Actual unlimited-time authorization required');budget.require_time_budget(ledger,CAP)
  pid=os.getpid();ticks=b.ticks(pid);start=time.monotonic();owned={pid:ticks};stop=threading.Event();mutex=threading.RLock()
  state=dict(phase='preparing',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);counter=0;git_wall=0.
  sources={str(p):sha(p)for directory in(SRC,OWNER)for p in directory.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')}
  helpers={str(ROOT/'tools'/name):sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,
   controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),
   source_sha256=sources,helper_sha256=helpers,outer_deadline_seconds=CAP,numerical_child_deadline_seconds=NUMERIC_CAP,
   resource_limits=limits,execution_policy_refs=ep.execution_policy_refs(),configured=configured,
   maximum_new_driven_RHS=0,new_PDE_RHS=0,expected_canonical_native_geometries=15,expected_unloaded_probes=600,expected_new_angular_metrics=0,new_native_FVM_RHS=0,new_eigen_solves=0)
  new(OUT/'registration.json',reg)
  receipt=dict(schema='task1-results-consolidation-owner-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,
   maximum_new_driven_RHS=0,new_PDE_RHS=0,Windows_saved_verified=False,candidate_adopted=False)
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
    counter+=1;item=dict(schema='task1-results-consolidation-live-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,
     elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),item)
    for target in(OUT/'current.json',ROOT/'runtime/task1-results-consolidation-live-20261025.json'):
     tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,item);os.replace(tmp,target)
    state['phase']=phase
  def guard():
   with mutex:
    live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);fast_now=dict(fast);large_now=dict(large)
   rss=sum(b.rss(p)for p,t in live.items()if b.live(p,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
   with mutex:state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp))
   req(rss+tmp<=limits['total_memory_bytes'],'Actual aggregate descendantRSS plus ALL task1-ownedtmpfs cap')
   req(time.monotonic()-start<CAP,'Finite2400s owner watchdog');req(not(OUT/'STOP').exists(),'Explicit STOP marker')
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
  def command(argv,label,seconds,is_git=False):
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
   req(code==0,'Finite child failed '+label+'; preserve log '+str(log))
  def plan(files,parent,message,destination,comment=None):
   for path in files.values():req(path.is_file()and not path.is_symlink()and path.stat().st_size<MAX_FILE,'Preserve file and report publication bound '+str(path))
   return dict(schema='task1-supported-Git-transport-plan-v1',repository='yoodohyun-codex-cloud/ngg-tis-task1',branch='codex/task1-cloud-restart-20261020',expected_parent=parent,message=message,
    files={target:dict(local_path=str(path),SHA256=sha(path),bytes=path.stat().st_size)for target,path in files.items()},required_result_receipt=str(destination),required_receipt_status='published_readback_verified',new_PDE_required=False,comment_body=comment)
  try:
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    import consolidation as model
    admission=read(ADMISSION);new(OUT/'root-admission.json',admission);spec=model.make_spec(admission);refs=model.required_inputs(admission);refs[str(ADMISSION)]=sha(ADMISSION);refs[str(OUT/'root-admission.json')]=sha(OUT/'root-admission.json');tests=test_inventory();new(OUT/'test-source-inventory.json',tests)
    refs[str(OUT/'test-source-inventory.json')]=sha(OUT/'test-source-inventory.json')
    refs.update(reg['execution_policy_refs']);refs.update(helpers);new(OUT/'spec.json',spec)
    frozen={}
    for namespace,directory in(('model',SRC),('owner',OWNER)):
     target=OUT/'source'/namespace;target.mkdir()
     for path in directory.iterdir():
      if path.is_file()and path.suffix in('.py','.json','.md'):
       copy=target/path.name
       with copy.open('xb')as stream:stream.write(path.read_bytes())
       req(sha(copy)==sources[str(path)],'Frozen source copy identity');frozen[str(copy)]=sha(copy)
    req(spec['root_admission']==admission,'Exact positive completed-mixed-R2-bound root decision')
    new(OUT/'preregistration.json',dict(schema='task1-cached-results-consolidation-preregistration-v1',
     question='Consolidate fifteen distinct authenticated native geometries, preserving scalar variants and exact aliases. Rank cached metrics and classify stored scalar fields, predict forty unloaded physical5mm differential probes per geometry, render the standalone GUI. No new PDE, angular metrics, Q loading or original field duplication. Local reported results remain unranked until authenticated raw artifacts are supplied.',
     source_sha256=sources,frozen_source_sha256=frozen,input_sha256=refs,spec_SHA256=sha(OUT/'spec.json'),limits=limits,
     hard_child_seconds=NUMERIC_CAP,expected_synthetic_tests=tests['total'],test_inventory_SHA256=sha(OUT/'test-source-inventory.json'),maximum_new_driven_RHS=0,new_PDE_RHS=0,
     expected_canonical_native_geometries=15,expected_unloaded_probes_per_geometry=40,expected_unloaded_probes=600,expected_new_angular_evaluations=0,root_admission_SHA256=sha(OUT/'root-admission.json'),root_decision=admission,
     resource_forecast=RESOURCE_FORECAST,
     old_failed_flags_preserved=True,criteria_relaxed=False,candidate_adopted=False))
    bind({**refs,**frozen,**{str(OUT/name):sha(OUT/name)for name in('spec.json','preregistration.json')}})
   files={}
   for path in(OUT/'source').rglob('*'):
    if path.is_file():files['tools/results_consolidation_20261025/'+path.relative_to(OUT/'source').as_posix()]=path
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and len(rel.parts)==1 and path.name in('registration.json','preregistration.json','spec.json','test-source-inventory.json','root-admission.json'):files[REMOTE+rel.as_posix()]=path
   spath=OUT/'source-plan.json';new(spath,plan(files,head,'Preregister cached consolidation of fifteen native geometries, unloaded probes and standalone GUI',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(spath),'--output','/dev/shm/task1-git-results-consolidation-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',PUB_CAP,True)
   published=read(OUT/'source-publication/result-publication.json');req(published['status']=='published_readback_verified','Immutable source/input publication before numerical work')
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    guard();tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));as_limit=int(min(2000000000,limits['total_memory_bytes']-tmp-b.rss(pid)-VIRTUAL_RESERVE))
    req(as_limit>=800000000,'Insufficient actual approved RSS+alltmpfs headroom; preserve originals')
    new(OUT/'numeric-admission.json',dict(aggregate_cap_bytes=limits['total_memory_bytes'],observed_owned_tmpfs_bytes=tmp,parent_RSS_bytes=b.rss(pid),child_RLIMIT_AS_bytes=as_limit,extra_reserve_bytes=VIRTUAL_RESERVE,resource_forecast=RESOURCE_FORECAST))
    command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(OUT/'source/owner/worker.py'),'--output',str(OUT),'--source',str(OUT/'source/model'),'--as-limit',str(as_limit),
     '--registration-sha',sha(OUT/'registration.json'),'--preregistration-sha',sha(OUT/'preregistration.json'),'--publication-sha',sha(OUT/'source-publication/result-publication.json'),'--publication-plan-sha',sha(spath)],'cached-results-consolidation-child',NUMERIC_CAP)
   worker=read(OUT/'worker-receipt.json');req(worker['status']=='results_consolidation_cached_analysis_computed','Actual complete cached-consolidation worker required')
   summary=read(OUT/'summary.json');validate_consolidation_summary(summary)
   # Full source and large-input SHA verification occurs again after computation.
   with mutex:all_pins={**fast,**{path:value[0]for path,value in large.items()}}
   for path,expected in all_pins.items():guard();req(sha(path)==expected,'Complete after-compute input SHA mismatch '+path)
   new(OUT/'numeric-checkpoint.json',dict(status='cached_results_consolidation_complete_publication_pending',resources={k:v for k,v in state.items()if k.startswith('peak_')},source_commit=published['commit'],worker_receipt_SHA256=sha(OUT/'worker-receipt.json'),actual_new_RHS=0,actual_new_angular_evaluations=0,canonical_native_geometries=15,unloaded_probes=600,candidate_adopted=False))
   files={}
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and(rel.parts[0]in('views','probes','conditions','cases','candidates','arrays','proofs','progress','logs')or(len(rel.parts)==1 and(path.suffix in('.npz','.html')or path.name in('summary.json','views.json','tests.log','worker-receipt.json','threadpool-runtime.json','numeric-admission.json','numeric-checkpoint.json','ROI-receipt.json','common-grid-identity-proof.json','control-identity-variant-proof.json','diagnostic-cutoffs.json','gui-render-receipt.json','input-SHA-verification.json','test-source-inventory.json')or path.name.startswith('checkpoint-')))):files[REMOTE+rel.as_posix()]=path
   files[REMOTE+'source-publication-receipt.json']=OUT/'source-publication/result-publication.json'
   rp=OUT/'result-plan.json';new(rp,plan(files,published['commit'],'Publish fifteen native-geometry comparisons, six hundred unloaded probes and standalone GUI',OUT/'result-publication/result-publication.json',
    comment='실제 원자료와 공개 SHA가 연결된 서로 다른 native 전극 배치15개를 같은 ROI·단위·색상·축에서 통합 비교했습니다. 기존 저장 스칼라와 복소 전위·벡터를 후처리했고 새 PDE·각도 탐색은0회입니다. 각 배치의 깊이5·10·15·20mm 십자 위치에서 X/Y 방향 팁 간격5mm 무부하 차동 예측40개씩 총600개와 standalone GUI를 보존합니다. B0와8·12·16패드 비교를 함께 유지하고 패드 수와 독립출력2개를 구분합니다. 전압·전류합 bookkeeping·전력·joint8부담 비교는 서로 별도입니다. LOCAL14/16은 사용자 보고와 인증된 native 결과를 구분하고 임의로 순위에 넣지 않습니다. 기존 실패·접촉 불확실성·표층 hotspot·수렴 보류를 유지하며 채택·실험·인체안전을 주장하지 않습니다. 실제 장비 부하·Windows 저장·OneDrive동기화는 검증하지 않았습니다.'))
   command([sys.executable,'-B',str(PUB),'--plan',str(rp),'--output','/dev/shm/task1-git-results-consolidation-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',PUB_CAP,True)
   result=read(OUT/'result-publication/result-publication.json');req(result['status']=='published_readback_verified','Full result immutable readback required')
   receipt.update(status='results_consolidation_computed_published',source_commit=published['commit'],result_commit=result['commit'],worker_elapsed_seconds=worker['elapsed_seconds'],consolidation_accounting=validate_consolidation_summary(summary))
   checkpoint('published_reviewing_next_finite_design_batch',result_commit=result['commit'])
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
   ledger['runs'].append(dict(run_id=OUT.name,stage='cached_results_consolidation_and_supervision',seconds=debit,status=receipt['status'],Git_children_debited_separately=True))
   temp=LEDGER.with_name('task1-budget-results-consolidation-'+str(pid)+'.tmp');new(temp,ledger);os.replace(temp,LEDGER)
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')},remaining_approved_seconds=budget.remaining_seconds(ledger));new(OUT/'receipt.json',receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
