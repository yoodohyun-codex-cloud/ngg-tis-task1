"""Single finite source-published browser validation; no science recomputation."""
import hashlib,json,os,re,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
OWNER=Path('/dev/shm/task1-results-gui-browser-r3-20261025/source')
SRC=OWNER
ADMISSION=SRC/'root-admission.json'
OUT=Path('/dev/shm/task1-results-gui-browser-r3-20261025-run')
PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
LEDGER=ROOT/'runtime/task1-budget.json'
CAP=600;BROWSER_CAP=180;PUB_CAP=330;MAX_FILE=80*1024**2
RESOURCE_FORECAST=dict(new_PDE_RHS=0,new_angular_evaluations=0,Q_loaded=False,CPU_cap_unchanged=4,aggregate_RSS_plus_all_task_tmpfs_cap_bytes=8000000000,aggregate_guard_unchanged=True,child_virtual_address_cap='not applied to Chromium virtual reservations; aggregate RSS+ALLtasktmpfs cap unchanged',prior_R2_peak_descendant_RSS_bytes=1188888576,prior_R2_peak_owned_tmpfs_bytes=6842725723,prior_R2_peak_accounted_bytes=8031614299,prior_R2_observed_excess_bytes=31614299,comparison_new_full_payload_clones=0,comparison_new_full_payload_JSON_strings=0,allocation_change='Recursive exact parsed-JSON semantic equality replaces canonical deep clones and duplicate JSON.stringify allocations; existing fresh JSON fetches and whole-D/source identity SHA gates preserved',RAM_reduction_measured=False,forecast_scope='Allocation-structure forecast only; no unmeasured byte savings claimed. Actual250ms RSS+ALLtask1tmpfs<=8e9 is decisive and may still terminate R3.')
REMOTE='data-native/results-gui-browser-r3-20261025/'
sys.path[:0]=[str(ROOT/'tools'),str(SRC)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget

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
def main():
 head=os.environ.get('TASK1_GUI_BROWSER_EXPECTED_PARENT','')
 req(re.fullmatch('[0-9a-f]{40}',head)is not None,'Set TASK1_GUI_BROWSER_EXPECTED_PARENT to the actual public40hex branch parent')
 req(ADMISSION.is_file()and not ADMISSION.is_symlink(),'Positive root selection bound to completed consolidated R and immutable GUI inputs required')
 with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
  req(not OUT.exists(),'Unique run required; preserve all earlier attempts');OUT.mkdir()
  for name in('logs','source-publication','result-publication','source'):(OUT/name).mkdir()
  limits=ep.resolve_limits();req(0<limits['cpu_limit']<=4 and 0<limits['total_memory_bytes']<=8000000000,'Current CPU4/aggregate8e9 policy, no budget increase');configured=ep.configure_process(limits);ledger=budget.load_ledger()
  req(ledger.get('cumulative_time_unlimited')is True,'Actual unlimited-time authorization required');budget.require_time_budget(ledger,CAP)
  pid=os.getpid();ticks=b.ticks(pid);start=time.monotonic();owned={pid:ticks};stop=threading.Event();mutex=threading.RLock()
  state=dict(phase='preparing',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);counter=0;git_wall=0.
  sources={str(p):sha(p)for directory in(SRC,)for p in directory.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')}
  helpers={str(ROOT/'tools'/name):sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,
   controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),
   source_sha256=sources,helper_sha256=helpers,outer_deadline_seconds=CAP,browser_child_deadline_seconds=BROWSER_CAP,
   resource_limits=limits,execution_policy_refs=ep.execution_policy_refs(),configured=configured,
   maximum_new_driven_RHS=0,new_PDE_RHS=0,expected_canonical_native_geometries=15,expected_unloaded_probes=600,expected_new_angular_metrics=0,browser_validation_only=True,new_native_FVM_RHS=0,new_eigen_solves=0)
  new(OUT/'registration.json',reg)
  receipt=dict(schema='task1-results-gui-browser-owner-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,
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
    counter+=1;item=dict(schema='task1-results-gui-browser-live-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,
     elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),item)
    for target in(OUT/'current.json',ROOT/'runtime/task1-results-gui-browser-r3-live-20261025.json'):
     tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,item);os.replace(tmp,target)
    state['phase']=phase
  def guard():
   with mutex:
    live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);fast_now=dict(fast);large_now=dict(large)
   rss=sum(b.rss(p)for p,t in live.items()if b.live(p,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
   with mutex:state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp))
   req(rss+tmp<=limits['total_memory_bytes'],'Actual aggregate descendantRSS plus ALL task1-ownedtmpfs cap')
   req(time.monotonic()-start<CAP,'Finite600s owner watchdog');req(not(OUT/'STOP').exists(),'Explicit STOP marker')
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
    import browser_inputs as model
    admission=read(ADMISSION);new(OUT/'root-admission.json',admission);spec=model.make_spec(admission);refs=model.required_inputs(admission);refs[str(ADMISSION)]=sha(ADMISSION);refs[str(OUT/'root-admission.json')]=sha(OUT/'root-admission.json')
    refs.update(reg['execution_policy_refs']);refs.update(helpers);new(OUT/'spec.json',spec)
    frozen={}
    for namespace,directory in(('model',SRC),):
     target=OUT/'source'/namespace;target.mkdir()
     for path in directory.iterdir():
      if path.is_file()and path.suffix in('.py','.json','.md'):
       copy=target/path.name
       with copy.open('xb')as stream:stream.write(path.read_bytes())
       req(sha(copy)==sources[str(path)],'Frozen source copy identity');frozen[str(copy)]=sha(copy)
    req(spec['root_admission']==admission,'Exact positive published-consolidated-R-bound root decision')
    new(OUT/'preregistration.json',dict(schema='task1-results-gui-browser-preregistration-v1',
     question='Validate actual standalone consolidated GUI in installed Chromium: JS errors, baseline/multipad/top5/native versus LOCAL separation, four normalization controls, persisted physical axes/colour/bar ranges, real mask contour data, six hundred unloaded probe rows, settings export/import and payload provenance immutability. Browser QA is not field convergence or hardware/physiology validation. Do not modify the admitted HTML.',
     source_sha256=sources,frozen_source_sha256=frozen,input_sha256=refs,spec_SHA256=sha(OUT/'spec.json'),limits=limits,
     hard_child_seconds=BROWSER_CAP,maximum_new_driven_RHS=0,new_PDE_RHS=0,
     expected_canonical_native_geometries=15,expected_unloaded_probes_per_geometry=40,expected_unloaded_probes=600,expected_new_angular_evaluations=0,root_admission_SHA256=sha(OUT/'root-admission.json'),root_decision=admission,
     resource_forecast=RESOURCE_FORECAST,
     old_failed_flags_preserved=True,criteria_relaxed=False,candidate_adopted=False))
    bind({**refs,**frozen,**{str(OUT/name):sha(OUT/name)for name in('spec.json','preregistration.json')}})
   files={}
   for path in(OUT/'source').rglob('*'):
    if path.is_file():files['tools/results_gui_browser_r3_20261025/'+path.relative_to(OUT/'source').as_posix()]=path
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and len(rel.parts)==1 and path.name in('registration.json','preregistration.json','spec.json','root-admission.json'):files[REMOTE+rel.as_posix()]=path
   spath=OUT/'source-plan.json';new(spath,plan(files,head,'Preregister bounded actual Chromium QA of the preserved consolidated GUI',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(spath),'--output','/dev/shm/task1-git-results-gui-browser-r3-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',PUB_CAP,True)
   published=read(OUT/'source-publication/result-publication.json');req(published['status']=='published_readback_verified','Immutable source/input publication before browser launch')
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    guard();command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(OUT/'source/model/worker.py'),'--output',str(OUT),'--source',str(OUT/'source/model'),
     '--registration-sha',sha(OUT/'registration.json'),'--preregistration-sha',sha(OUT/'preregistration.json'),'--publication-sha',sha(OUT/'source-publication/result-publication.json'),'--publication-plan-sha',sha(spath)],'actual-browser-child',BROWSER_CAP)
   worker=read(OUT/'worker-receipt.json');req(worker['status']=='consolidated_gui_actual_browser_passed','Actual browser must pass; no HTML fix or fabricated browser approval')
   summary=read(OUT/'browser-receipt.json');req(summary['status']=='passed'and summary['browser_validation_performed']is True,'Actual browser result receipt required')
   # Full source and large-input SHA verification occurs again after the actual browser.
   with mutex:all_pins={**fast,**{path:value[0]for path,value in large.items()}}
   for path,expected in all_pins.items():guard();req(sha(path)==expected,'Complete after-compute input SHA mismatch '+path)
   new(OUT/'browser-checkpoint.json',dict(status='actual_browser_complete_publication_pending',resources={k:v for k,v in state.items()if k.startswith('peak_')},source_commit=published['commit'],worker_receipt_SHA256=sha(OUT/'worker-receipt.json'),actual_new_RHS=0,actual_new_angular_evaluations=0,candidate_adopted=False))
   files={}
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and(rel.parts[0]=='logs'or(len(rel.parts)==1 and(path.suffix in('.jpg',)or path.name in('browser-receipt.json','browser-failure.json','browser-scratch.json','worker-receipt.json','browser-checkpoint.json','input-SHA-verification.json','display-settings-export.json','invalid-display-settings-fixture.json')or path.name.startswith('checkpoint-')))):files[REMOTE+rel.as_posix()]=path
   files[REMOTE+'source-publication-receipt.json']=OUT/'source-publication/result-publication.json'
   rp=OUT/'result-plan.json';new(rp,plan(files,published['commit'],'Publish actual desktop and mobile browser QA of the preserved consolidated GUI',OUT/'result-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(rp),'--output','/dev/shm/task1-git-results-gui-browser-r3-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',PUB_CAP,True)
   result=read(OUT/'result-publication/result-publication.json');req(result['status']=='published_readback_verified','Full result immutable readback required')
   receipt.update(status='actual_browser_passed_published',source_commit=published['commit'],result_commit=result['commit'],worker_elapsed_seconds=worker['elapsed_seconds'],browser_validation_performed=True,scientific_validation_performed=False)
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
   ledger['runs'].append(dict(run_id=OUT.name,stage='actual_browser_validation_and_supervision',seconds=debit,status=receipt['status'],Git_children_debited_separately=True))
   temp=LEDGER.with_name('task1-budget-results-gui-browser-r3-'+str(pid)+'.tmp');new(temp,ledger);os.replace(temp,LEDGER)
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')},remaining_approved_seconds=budget.remaining_seconds(ledger));new(OUT/'receipt.json',receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
