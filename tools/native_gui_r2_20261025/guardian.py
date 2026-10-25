"""One finite renderer-only recovery; root alone executes this new source."""
import hashlib,json,os,re,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
SRC=Path('/dev/shm/task1-native-gui-r2-20261025/source')
OUT=Path('/dev/shm/task1-native-gui-r2-20261025-run')
ADMISSION=SRC/'root-admission.json'
PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
LEDGER=ROOT/'runtime/task1-budget.json'
REMOTE='data-native/native-gui-r2-20261025/'
RESOURCE_SCOPE_SHA='6c09a7cd06fed12a2e9950cc921242ef12c2a4ae999e9645ae7953d732d7873e'
CAP=900;RENDER_CAP=300;PUB_CAP=330;MAX_FILE=80*1024**2
sys.path[:0]=[str(ROOT/'tools'),str(SRC)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget
import resource_scope

def require(ok,message):
 if not ok:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text())
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def new(path,value):
 raw=(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode()
 with Path(path).open('xb')as stream:stream.write(raw)
def identity(path):
 p=Path(path);require(p.is_file()and not p.is_symlink(),'Immutable regular input');s=p.stat();return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def size(path):
 try:return path.stat().st_size if path.is_file()else sum(p.stat().st_size for p in path.rglob('*')if p.is_file())
 except FileNotFoundError:return 0

def main():
 head=os.environ.get('TASK1_NATIVE_GUI_R2_EXPECTED_PARENT','');require(re.fullmatch('[0-9a-f]{40}',head)is not None,'Actual40hex public parent required')
 require(ADMISSION.is_file()and not ADMISSION.is_symlink(),'Root positive render-only admission required')
 with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
  require(not OUT.exists(),'Unique new output; preserve old GUI/failure runs');OUT.mkdir()
  for name in('logs','source-publication','result-publication','source'):(OUT/name).mkdir()
  limits=ep.resolve_limits();require(0<limits['cpu_limit']<=4 and 0<limits['total_memory_bytes']<=8000000000,'UnchangedCPU4/global8e9 budget');configured=ep.configure_process(limits);ledger=budget.load_ledger();budget.require_time_budget(ledger,CAP)
  pid=os.getpid();tick=b.ticks(pid);started=time.monotonic();owned={pid:tick};remembered={};last_scope=[None];mutex=threading.RLock();stop=threading.Event();counter=0;git_wall=0.
  state=dict(phase='preparing',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0,peak_research_processes=[])
  sources={str(p):sha(p)for p in SRC.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')};require(sources[str(SRC/'resource_scope.py')]==RESOURCE_SCOPE_SHA,'Exact frozen ALLresearch observer')
  helpers={str(ROOT/'tools'/name):sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=tick,controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),source_sha256=sources,helper_sha256=helpers,resource_limits=limits,execution_policy_refs=ep.execution_policy_refs(),configured=configured,outer_deadline_seconds=CAP,render_child_deadline_seconds=RENDER_CAP,new_PDE_RHS=0,new_angular_evaluations=0,native_arrays_loaded=False)
  new(OUT/'registration.json',reg);receipt=dict(schema='task1-native-gui-render-owner-v1',status='failed_preserved',pid=pid,proc_start_ticks=tick,started_utc=b.now(),new_PDE_RHS=0,new_angular_evaluations=0,native_arrays_loaded=False,browser_validation_performed=False,candidate_adopted=False)
  fast={};large={}
  def bind(refs):
   for path,expected in refs.items():
    token=identity(path);require(sha(path)==expected,'Exact frozen input SHA '+path)
    with mutex:
     if token[2]<=1024**2:fast[path]=expected
     else:large[path]=(expected,token)
  bind({**sources,**helpers,**reg['execution_policy_refs'],str(PUB):reg['publisher_sha256'],str(OUT/'registration.json'):sha(OUT/'registration.json')})
  def checkpoint(phase,**extra):
   nonlocal counter
   with mutex:
    counter+=1;item=dict(schema='task1-native-gui-render-live-v1',queue_pid=pid,queue_start_ticks=tick,phase=phase,updated_utc=b.now(),elapsed_seconds=time.monotonic()-started,**extra);new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),item)
    for target in(OUT/'current.json',ROOT/'runtime/task1-native-gui-r2-live-20261025.json'):
     tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,item);os.replace(tmp,target)
    state['phase']=phase
  def guard():
   with mutex:family=b.owned_descendants(pid,tick,dict(owned));owned.update(family);known=dict(remembered);fs=dict(fast);ls=dict(large)
   observed=resource_scope.observe(family,b.ticks,remembered=known);rss=observed['research_RSS_bytes'];tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
   with mutex:
    remembered.update(observed['members']);last_scope[0]=observed
    if rss+tmp>state['peak_accounted']:state['peak_research_processes']=[dict(PID=r['pid'],proc_start_ticks=r['start_ticks'],RSS_bytes=r['RSS_bytes'])for r in observed['scanned_processes']if r['research_owned']][:256]
    state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp))
   require(rss+tmp<=limits['total_memory_bytes'],'Actual ALLresearchRSS+ALLtasktmpfs cap');require(time.monotonic()-started<CAP,'Finite900s render owner');require(not(OUT/'STOP').exists(),'STOP marker')
   for path,expected in fs.items():require(sha(path)==expected,'Frozen small input/source changed '+path)
   for path,(_,token)in ls.items():require(identity(path)==token,'Frozen large input identity changed '+path)
  def interrupt(signum,frame):raise InterruptedError(state.get('error','Finite watchdog/external signal'))
  def monitor():
   last=0.
   while not stop.wait(.25):
    try:
     guard()
     if time.monotonic()-last>=5:checkpoint(state['phase'],peak_accounted=state['peak_accounted']);last=time.monotonic()
    except BaseException as error:state['error']=str(error);os.kill(pid,signal.SIGTERM);return
  handlers={sig:signal.getsignal(sig)for sig in(signal.SIGALRM,signal.SIGINT,signal.SIGTERM)}
  for sig in handlers:signal.signal(sig,interrupt)
  signal.setitimer(signal.ITIMER_REAL,CAP);thread=threading.Thread(target=monitor,daemon=True);thread.start()
  def command(argv,label,seconds,is_git=False):
   nonlocal git_wall
   guard();checkpoint(label);before=time.monotonic();rows_before=len(budget.load_ledger()['runs']);log=OUT/'logs'/(str(counter)+'-'+label+'.log')
   with log.open('xb')as stream:
    child=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    with mutex:owned[child.pid]=b.ticks(child.pid)
    checkpoint(label,child_pid=child.pid,child_start_ticks=owned[child.pid],child_timeout_seconds=seconds)
    try:code=child.wait(timeout=max(.01,min(seconds,CAP-(time.monotonic()-started))))
    finally:
     if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
     if is_git:
      child_run=Path(argv[argv.index('--output')+1]).name;recorded=sum(r.get('seconds',0.)for r in budget.load_ledger()['runs'][rows_before:]if r.get('run_id')==child_run);git_wall+=min(time.monotonic()-before,recorded)
   require(code==0,'Finite child failed '+label+'; preserve '+str(log))
  def plan(files,parent,message,destination):
   for path in files.values():require(path.is_file()and not path.is_symlink()and path.stat().st_size<MAX_FILE,'Publication bound, preserve evidence '+str(path))
   return dict(schema='task1-supported-Git-transport-plan-v1',repository='yoodohyun-codex-cloud/ngg-tis-task1',branch='codex/task1-cloud-restart-20261020',expected_parent=parent,message=message,files={name:dict(local_path=str(path),SHA256=sha(path),bytes=path.stat().st_size)for name,path in files.items()},required_result_receipt=str(destination),required_receipt_status='published_readback_verified',new_PDE_required=False)
  try:
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    import native_gui_render as model
    admission=read(ADMISSION);new(OUT/'root-admission.json',admission);spec=model.make_spec(admission);refs=model.required_inputs(admission);refs.update({str(ADMISSION):sha(ADMISSION),str(OUT/'root-admission.json'):sha(OUT/'root-admission.json'),**helpers,**reg['execution_policy_refs']});new(OUT/'spec.json',spec)
    frozen={};target=OUT/'source/model';target.mkdir()
    for path in SRC.iterdir():
     if path.is_file()and path.suffix in('.py','.json','.md'):
      copy=target/path.name
      with copy.open('xb')as stream:stream.write(path.read_bytes())
      require(sha(copy)==sources[str(path)],'Frozen source identity');frozen[str(copy)]=sha(copy)
    new(OUT/'preregistration.json',dict(schema='task1-native-gui-render-preregistration-v1',question='Rename only six applicationJS top references to appTopIds in a new GUI, with EXACT old/new embedded payload bytes and suppliedS/V semantic equality; scientific results/oldindex untouched; browserR5 separate.',source_sha256=sources,frozen_source_sha256=frozen,input_sha256=refs,spec_SHA256=sha(OUT/'spec.json'),root_admission_SHA256=sha(OUT/'root-admission.json'),root_decision=admission,hard_child_seconds=RENDER_CAP,limits=limits,new_PDE_RHS=0,new_angular_evaluations=0,native_arrays_loaded=False,browser_validation_performed=False,candidate_adopted=False))
    bind({**refs,**frozen,str(OUT/'spec.json'):sha(OUT/'spec.json'),str(OUT/'preregistration.json'):sha(OUT/'preregistration.json')})
   files={'tools/native_gui_r2_20261025/'+p.relative_to(OUT/'source/model').as_posix():p for p in(OUT/'source/model').iterdir()if p.is_file()}
   for name in('registration.json','preregistration.json','spec.json','root-admission.json'):files[REMOTE+name]=OUT/name
   sp=OUT/'source-plan.json';new(sp,plan(files,head,'Preregister minimal nativeGUI JS-binding recovery with exact original payload preservation',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(sp),'--output','/dev/shm/task1-git-native-gui-r2-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',PUB_CAP,True)
   source=read(OUT/'source-publication/result-publication.json');require(source['status']=='published_readback_verified','Source/input publication before render')
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    guard();new(OUT/'resource-scope-before-render.json',last_scope[0]);command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(OUT/'source/model/worker.py'),'--output',str(OUT),'--source',str(OUT/'source/model'),'--registration-sha',sha(OUT/'registration.json'),'--preregistration-sha',sha(OUT/'preregistration.json'),'--publication-sha',sha(OUT/'source-publication/result-publication.json'),'--publication-plan-sha',sha(sp)],'exact-payload-render-child',RENDER_CAP)
   worker=read(OUT/'worker-receipt.json');result=read(OUT/'render-receipt.json');require(worker['status']=='native_GUI_exact_payload_rendered'and result['status']=='minimal_JS_binding_rendered_payload_EXACT_browser_unverified','Actual exact-payload render only')
   with mutex:all_pins={**fast,**{path:row[0]for path,row in large.items()}}
   for path,expected in all_pins.items():guard();require(sha(path)==expected,'Full post-render original/source SHA '+path)
   new(OUT/'resource-scope-after-render.json',last_scope[0]);new(OUT/'render-checkpoint.json',dict(status='render_complete_publication_pending',new_index_SHA256=result['new_index_SHA256'],browser_validation_performed=False,new_PDE_RHS=0))
   files={}
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and(rel.parts[0]=='logs'or(len(rel.parts)==1 and(path.suffix=='.html'or path.name in('render-receipt.json','worker-receipt.json','render-checkpoint.json','payload-identity-proof.json','payload-after-write-proof.json','original-summary-views-aliases.json','input-SHA-verification.json')or path.name.startswith(('checkpoint-','resource-scope-'))))):files[REMOTE+rel.as_posix()]=path
   for name in('summary.json','views.json'):files[REMOTE+name]=Path(spec['inputs'][name]['path'])
   for name in('renderer-delta.json','r4-JS-failure-evidence.json','prior-browser-launch-failure-evidence.json','prior-browser-r2-memory-failure-evidence.json','prior-browser-r3-memory-failure-evidence.json'):files[REMOTE+name]=SRC/name
   files[REMOTE+'source-publication-receipt.json']=OUT/'source-publication/result-publication.json';rp=OUT/'result-plan.json';new(rp,plan(files,source['commit'],'Publish minimal nativeGUI binding fix and exact unchanged scientific payload; browser validation pending',OUT/'result-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(rp),'--output','/dev/shm/task1-git-native-gui-r2-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',PUB_CAP,True)
   published=read(OUT/'result-publication/result-publication.json');require(published['status']=='published_readback_verified','NewGUI full immutable readback');receipt.update(status='native_GUI_exact_payload_rendered_published_browser_unverified',source_commit=source['commit'],result_commit=published['commit'],new_index_SHA256=result['new_index_SHA256']);checkpoint('published_waiting_separate_R5_browser_validation',result_commit=published['commit'])
  except BaseException as error:receipt.update(error_type=type(error).__name__,error=str(error),failed_phase=state['phase']);checkpoint('failed_preserved',error=str(error));raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   for child,t in b.owned_descendants(pid,tick,dict(owned)).items():
    if child!=pid and b.live(child,t):
     try:os.kill(child,signal.SIGKILL)
     except ProcessLookupError:pass
   if last_scope[0]is not None:new(OUT/'resource-scope-final.json',last_scope[0])
   elapsed=time.monotonic()-started;debit=max(0.,elapsed-git_wall);ledger=budget.load_ledger();ledger['spent_seconds']+=debit;ledger['runs'].append(dict(run_id=OUT.name,stage='native_GUI_render_only',seconds=debit,status=receipt['status'],Git_children_debited_separately=True));tmp=LEDGER.with_name('task1-budget-native-gui-r2-'+str(pid)+'.tmp');new(tmp,ledger);os.replace(tmp,LEDGER)
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')});new(OUT/'receipt.json',receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
