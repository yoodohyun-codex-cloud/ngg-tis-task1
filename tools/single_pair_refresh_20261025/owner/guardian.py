"""One finite source-published centred-y0 single-pair comparison owner."""
import ast,hashlib,json,os,re,shutil,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
OWNER=Path('/dev/shm/task1-single-pair-refresh-owner-20261025/source')
SRC=Path('/dev/shm/task1-single-pair-refresh-20261025/source')
ADMISSION=SRC/'root-admission.json'
OUT=Path('/dev/shm/task1-single-pair-refresh-20261025-run')
PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
LEDGER=ROOT/'runtime/task1-budget.json'
CAP=2400;NUMERIC_CAP=1200;PUB_CAP=330;MAX_FILE=80*1024**2
VIRTUAL_RESERVE=250000000
FIXED_CHILD_AS=1600000000
PREDICTED_CHILD_RSS=800000000
EXPECTED_OUTPUT_BYTES=200000000
HISTORY={
 '/dev/shm/task1-mixed-fourpad-r2-20261025-run/worker-receipt.json':'e7705c28b761d2f39f70b6ecaa7d896601022abf44b28626f65ddf782bf8427c',
 '/dev/shm/task1-mixed-fourpad-r2-20261025-run/receipt.json':'25ffea2d157638f2d63db2d9048317bcc5bf81d8c63ecb2ff72f3f0fda4302a4'}
RESOURCE_FORECAST=dict(prior_measured_raw_VmPeak_bytes=1162010624,prior_measured_raw_owned_RSS_bytes=713867264,prior_measured_descendant_RSS_bytes=741543936,
 expected_new_raw_and_scalar_output_bytes=EXPECTED_OUTPUT_BYTES,predicted_child_RSS_bytes=PREDICTED_CHILD_RSS,fixed_child_RLIMIT_AS_bytes=FIXED_CHILD_AS,publication_and_miscellaneous_virtual_reserve_bytes=VIRTUAL_RESERVE,historical_receipt_SHA256=HISTORY,
 aggregate_RSS_plus_all_task_tmpfs_cap_bytes=8000000000,aggregate_guard_unchanged=True,CPU_cap_unchanged=4,
 interpretation='Fixed finite1.6GB virtual-address cap is not a RAM allocation or Javaheap. Admit only measured alltmpfs+parentRSS+predicted800MBchildRSS+200MBnewoutput<=8e9; actual250msaggregateRSS+alltmpfsguard unchanged. Uncommitted virtual mappings may exceed physicalRSS headroom. No resource-budget expansion.')
REMOTE='data-native/single-pair-refresh-20261025/'
sys.path[:0]=[str(ROOT/'tools'),str(SRC)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget
from owner_contracts import validate_single_pair_summary

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
 head=os.environ.get('TASK1_SINGLE_PAIR_EXPECTED_PARENT','')
 req(re.fullmatch('[0-9a-f]{40}',head)is not None,'Set TASK1_SINGLE_PAIR_EXPECTED_PARENT to the actual public40hex branch parent')
 req(ADMISSION.is_file()and not ADMISSION.is_symlink(),'Positive root selection bound to completed recovery and immutable donor provenance required')
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
   source_sha256=sources,helper_sha256=helpers,historical_evidence_sha256=HISTORY,outer_deadline_seconds=CAP,numerical_child_deadline_seconds=NUMERIC_CAP,
   resource_limits=limits,execution_policy_refs=ep.execution_policy_refs(),configured=configured,
   maximum_new_driven_RHS=2,conditions=2,connected_sources=1,physical_pads_per_condition=2,new_angular_metrics=0,new_native_FVM_RHS=0,new_eigen_solves=0)
  new(OUT/'registration.json',reg)
  receipt=dict(schema='task1-single-pair-refresh-owner-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,
   maximum_new_driven_RHS=2,GUI_generated=False,GUI_status='Model provides JSON/raw comparisons only; no GUI renderer is invoked',Windows_saved_verified=False,candidate_adopted=False)
  fast={};large={}
  def bind(refs,full=True):
   for path,expected in refs.items():
    ident=identity(path)
    if full:req(sha(path)==expected,'Immutable input SHA mismatch '+path)
    with mutex:
     if ident[2]<=1024**2:fast[path]=expected
     else:large[path]=(expected,ident)
  bind({**sources,**helpers,**HISTORY,**reg['execution_policy_refs'],str(PUB):reg['publisher_sha256'],str(OUT/'registration.json'):sha(OUT/'registration.json')})
  def checkpoint(phase,**extra):
   nonlocal counter
   with mutex:
    counter+=1;item=dict(schema='task1-single-pair-refresh-live-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,
     elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),item)
    for target in(OUT/'current.json',ROOT/'runtime/task1-single-pair-refresh-live-20261025.json'):
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
    import single_pair_refresh as model
    admission=read(ADMISSION);new(OUT/'root-admission.json',admission);spec=model.make_spec(admission);refs=model.required_inputs(admission);refs.update(HISTORY);req(spec['grid']['cells']<=limits['max_cells']==800000,'Unchanged physical-evaluation-cell cap');req(spec['admission']['selected_TIS_reference']['candidate_id']=='P23p5-peripheral-polyomino225','Root-selected actual provisional P23 comparison only');refs[str(ADMISSION)]=sha(ADMISSION);refs[str(OUT/'root-admission.json')]=sha(OUT/'root-admission.json');tests=test_inventory();new(OUT/'test-source-inventory.json',tests)
    refs[str(OUT/'test-source-inventory.json')]=sha(OUT/'test-source-inventory.json')
    evidence=OUT/'historical-evidence';evidence.mkdir()
    for oldpath,expected in HISTORY.items():
     target=evidence/Path(oldpath).name
     with target.open('xb')as stream:stream.write(Path(oldpath).read_bytes())
     req(sha(target)==expected,'Historical resource evidence exact SHA');refs[str(target)]=expected
    refs.update(reg['execution_policy_refs']);refs.update(helpers);new(OUT/'spec.json',spec)
    frozen={}
    for namespace,directory in(('model',SRC),('owner',OWNER)):
     target=OUT/'source'/namespace;target.mkdir()
     for path in directory.iterdir():
      if path.is_file()and path.suffix in('.py','.json','.md'):
       copy=target/path.name
       with copy.open('xb')as stream:stream.write(path.read_bytes())
       req(sha(copy)==sources[str(path)],'Frozen source copy identity');frozen[str(copy)]=sha(copy)
    req(spec['admission']==admission,'Exact positive single-pair root decision')
    new(OUT/'preregistration.json',dict(schema='task1-memory-separated-single-pair-refresh-preregistration-v1',
     question='Calculate two centred-y0 physical two-pad single-source2000Hz models and separately match centre20mm vectorRMS or targetvolumeRMS to actual provisional P23TIS. Exactly2newRHS, no TISangular/eigen work. Keep original1Vpp and all individual skin/contact/power burdens; equalRMS is not equal modulation or activation.',
     source_sha256=sources,frozen_source_sha256=frozen,input_sha256=refs,spec_SHA256=sha(OUT/'spec.json'),limits=limits,
     hard_child_seconds=NUMERIC_CAP,expected_synthetic_tests=tests['total'],test_inventory_SHA256=sha(OUT/'test-source-inventory.json'),maximum_new_driven_RHS=2,
     expected_completed_conditions=2,connected_sources_per_condition=1,physical_pads_per_condition=2,expected_new_angular_evaluations=0,root_admission_SHA256=sha(OUT/'root-admission.json'),root_decision=admission,
     resource_forecast=RESOURCE_FORECAST,
     old_failed_flags_preserved=True,criteria_relaxed=False,candidate_adopted=False))
    bind({**refs,**frozen,**{str(OUT/name):sha(OUT/name)for name in('spec.json','preregistration.json')}})
   files={}
   for path in(OUT/'source').rglob('*'):
    if path.is_file():files['tools/single_pair_refresh_20261025/'+path.relative_to(OUT/'source').as_posix()]=path
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and(rel.parts[0]in('masks','historical-evidence')or(len(rel.parts)==1 and path.name in('registration.json','preregistration.json','spec.json','test-source-inventory.json','root-admission.json'))):files[REMOTE+rel.as_posix()]=path
   spath=OUT/'source-plan.json';new(spath,plan(files,head,'Preregister centred-y0 single-pair comparisons to actual provisional P23TIS',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(spath),'--output','/dev/shm/task1-git-single-pair-refresh-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',PUB_CAP,True)
   published=read(OUT/'source-publication/result-publication.json');req(published['status']=='published_readback_verified','Immutable source/input publication before numerical work')
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    guard();tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));parent_rss=b.rss(pid);physical_forecast=tmp+parent_rss+PREDICTED_CHILD_RSS+EXPECTED_OUTPUT_BYTES
    req(physical_forecast<=limits['total_memory_bytes'],'Physical RSS+alltmpfs+newoutput forecast exceeds unchanged8e9 cap; preserve originals, no child launch')
    as_limit=FIXED_CHILD_AS
    new(OUT/'numeric-admission.json',dict(aggregate_cap_bytes=limits['total_memory_bytes'],observed_owned_tmpfs_bytes=tmp,parent_RSS_bytes=parent_rss,predicted_child_peak_RSS_bytes=PREDICTED_CHILD_RSS,predicted_new_output_bytes=EXPECTED_OUTPUT_BYTES,physical_forecast_bytes=physical_forecast,child_RLIMIT_AS_bytes=as_limit,minimum_RLIMIT_AS_bytes=1000000000,virtual_cap_is_not_RAM_allocation=True,virtual_mapping_explanation='Finite1.6GBAS includesuncommittedmappings; only actualRSS+allownedtmpfs is8e9 physicalbudget. Independent250msaggregatewatchdog remains active.',resource_forecast=RESOURCE_FORECAST))
    bind({str(OUT/'numeric-admission.json'):sha(OUT/'numeric-admission.json')})
    command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(OUT/'source/owner/worker.py'),'--output',str(OUT),'--source',str(OUT/'source/model'),'--as-limit',str(as_limit),
     '--registration-sha',sha(OUT/'registration.json'),'--preregistration-sha',sha(OUT/'preregistration.json'),'--publication-sha',sha(OUT/'source-publication/result-publication.json'),'--publication-plan-sha',sha(spath)],'cached-single-pair-refresh-child',NUMERIC_CAP)
   worker=read(OUT/'worker-receipt.json');req(worker['status']=='single_pair_comparison_computed','Actual complete two-condition single-pair comparison worker required')
   summary=read(OUT/'summary.json');validate_single_pair_summary(summary)
   # Full source and large-input SHA verification occurs again after computation.
   with mutex:all_pins={**fast,**{path:value[0]for path,value in large.items()}}
   for path,expected in all_pins.items():guard();req(sha(path)==expected,'Complete after-compute input SHA mismatch '+path)
   new(OUT/'numeric-checkpoint.json',dict(status='single_pair_comparison_complete_publication_pending',resources={k:v for k,v in state.items()if k.startswith('peak_')},source_commit=published['commit'],worker_receipt_SHA256=sha(OUT/'worker-receipt.json'),actual_new_RHS=2,connected_sources_per_condition=1,physical_pads_per_condition=2,GUI_generated=False,candidate_adopted=False))
   files={}
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and(rel.parts[0]in('logs','cases','candidates','arrays','proofs')or(len(rel.parts)==1 and(path.suffix=='.npz'or(path.suffix=='.json'and path.name not in('current.json','source-plan.json','result-plan.json'))or path.name=='tests.log'))):files[REMOTE+rel.as_posix()]=path
   files[REMOTE+'source-publication-receipt.json']=OUT/'source-publication/result-publication.json'
   rp=OUT/'result-plan.json';new(rp,plan(files,published['commit'],'Preserve two centred-y0 single-source models and separate RMS matches to provisional P23TIS',OUT/'result-publication/result-publication.json',
    comment='지름50mm·층0.1/5/5/15mm를 유지하고 y=0의 두 전극쌍(중심 ±12.5mm, ±15mm; 각각15×15mm)을 독립출력1개/2000Hz/50Ω/귀환1개로 새로 계산했습니다. 두 조건의 새 RHS는 총2개이며, 기존 P23 TIS의 중심20mm 벡터RMS와 목표ROI 부피RMS를 각각 맞추는 전압·전류·피부/접촉 부담·전력을 구분합니다. 원래1Vpp 결과와 8개 기존 기준 부담도 보존합니다. 단일주파수 RMS는 TIS 변조나 생리적 활성화와 같다고 주장하지 않습니다. 기존 실패와 수렴·물성·접촉 불확실성을 유지합니다. 이 단계는 JSON/원시필드 산출이며 GUI·Windows 저장은 미검증입니다.'))
   command([sys.executable,'-B',str(PUB),'--plan',str(rp),'--output','/dev/shm/task1-git-single-pair-refresh-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',PUB_CAP,True)
   result=read(OUT/'result-publication/result-publication.json');req(result['status']=='published_readback_verified','Full result immutable readback required')
   receipt.update(status='single_pair_comparison_computed_published',source_commit=published['commit'],result_commit=result['commit'],worker_elapsed_seconds=worker['elapsed_seconds'],single_pair_accounting=validate_single_pair_summary(summary))
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
   ledger['runs'].append(dict(run_id=OUT.name,stage='single_pair_comparison_and_supervision',seconds=debit,status=receipt['status'],Git_children_debited_separately=True))
   temp=LEDGER.with_name('task1-budget-single-pair-refresh-'+str(pid)+'.tmp');new(temp,ledger);os.replace(temp,LEDGER)
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')},remaining_approved_seconds=budget.remaining_seconds(ledger));new(OUT/'receipt.json',receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
