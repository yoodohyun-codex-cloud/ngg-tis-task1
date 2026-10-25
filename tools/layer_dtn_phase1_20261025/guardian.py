"""Finite graph/eigen benchmark with one hard-killable child; no CEM solve."""
import sys,os,json,time,signal,threading,subprocess,hashlib,shutil
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');SRC=Path('/dev/shm/task1-layer-dtn-20261025/source');OUT=Path('/dev/shm/task1-layer-dtn-20261025-run');PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py');LEDGER=ROOT/'runtime/task1-budget.json';CAP=1500
sys.path[:0]=[str(ROOT/'tools'),str(SRC)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget

def req(x,m):
 if not x:raise ValueError(m)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new(p,j):
 with Path(p).open('x')as f:json.dump(j,f,ensure_ascii=False,allow_nan=False,indent=2)
def size(p):
 try:return p.stat().st_size if p.is_file()else sum(q.stat().st_size for q in p.rglob('*')if q.is_file())
 except FileNotFoundError:return 0
with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
 req(not OUT.exists(),'Unique new graph/eigen run; preserve old attempts');OUT.mkdir();(OUT/'logs').mkdir();(OUT/'source').mkdir();(OUT/'source-publication').mkdir();(OUT/'result-publication').mkdir()
 limits=ep.resolve_limits();configured=ep.configure_process(limits);ledger=budget.load_ledger();budget.require_time_budget(ledger,CAP);req(ledger.get('cumulative_time_unlimited')is True,'Actual unlimited-time authorization required')
 pid=os.getpid();ticks=b.ticks(pid);start=time.monotonic();owned={pid:ticks};stop=threading.Event();state=dict(phase='preparing',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);counter=0;git_wall=0.
 sources={str(p):sha(p)for p in SRC.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')};reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),source_sha256=sources,outer_deadline_seconds=CAP,numerical_child_deadline_seconds=600,resource_limits=limits,execution_policy_refs=ep.execution_policy_refs(),configured=configured,new_CEM_RHS=0)
 reg['helper_sha256']={str(ROOT/'tools'/name):sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')};progress_lock=threading.RLock()
 new(OUT/'registration.json',reg);receipt=dict(schema='task1-layer-dtn-phase1-parent-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,new_CEM_RHS=0,local_cache_remote_verified=False)
 def checkpoint(phase,**extra):
  with progress_lock:
   global counter
   counter+=1;j=dict(schema='task1-live-layer-dtn-phase1-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,run=str(OUT),elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(4)+'.json'),j)
   for target in(OUT/'current.json',ROOT/'runtime/task1-live-native-controller.json'):
    tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,j);os.replace(tmp,target)
   state['phase']=phase
 def guard():
  live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);rss=sum(b.rss(p)for p,t in live.items()if b.live(p,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp))
  req(rss+tmp<=limits['total_memory_bytes'],'Actual aggregate RSS+ALLownedtmpfs cap');req(time.monotonic()-start<CAP,'Finite1500s total benchmark watchdog');req(not(OUT/'STOP').exists(),'Explicit STOP marker')
  for p,h in{**sources,**reg['execution_policy_refs'],**reg['helper_sha256']}.items():req(sha(p)==h,'Frozen source/policy changed '+p)
  req(sha(PUB)==reg['publisher_sha256'],'Frozen publisher changed')
 def interrupt(s,f):raise InterruptedError(state.get('error','Finite watchdog or external signal'))
 def monitor():
  last=0.
  while not stop.wait(.25):
   try:
    guard()
    if time.monotonic()-last>5:checkpoint(state['phase'],observed_peak_RSS=state['peak_RSS'],observed_peak_owned_tmpfs=state['peak_owned_tmpfs']);last=time.monotonic()
   except BaseException as e:state['error']=str(e);os.kill(pid,signal.SIGTERM);return
 handlers={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGINT,signal.SIGTERM)}
 for s in handlers:signal.signal(s,interrupt)
 signal.setitimer(signal.ITIMER_REAL,CAP);thread=threading.Thread(target=monitor,daemon=True);thread.start()
 def command(argv,label,seconds,is_git=False):
  global git_wall
  guard();checkpoint(label);log=OUT/'logs'/(str(counter)+'-'+label+'.log');before=time.monotonic()
  with log.open('xb')as stream:
   child=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);owned[child.pid]=b.ticks(child.pid);checkpoint(label,child_pid=child.pid,child_start_ticks=owned[child.pid],child_timeout_seconds=seconds,log=str(log))
   try:code=child.wait(timeout=min(seconds,CAP-time.monotonic()+start))
   finally:
    if child.poll()is None:child.kill();child.wait(timeout=5)
    if is_git:git_wall+=time.monotonic()-before
  req(code==0,'Finite child failed: '+label+'; log='+str(log))
 def publication_plan(files,parent,message,destination,comment=None):
  return dict(schema='task1-supported-Git-transport-plan-v1',repository='yoodohyun-codex-cloud/ngg-tis-task1',branch='codex/task1-cloud-restart-20261020',expected_parent=parent,message=message,files={target:dict(local_path=str(p),SHA256=sha(p),bytes=p.stat().st_size)for target,p in files.items()},required_result_receipt=str(destination),required_receipt_status='published_readback_verified',new_PDE_required=False,comment_body=comment)
 try:
  with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
   import layer_dtn_backend as model
   refs=model.required_inputs();refs.update(reg['execution_policy_refs']);refs.update(reg['helper_sha256']);spec=model.make_spec();new(OUT/'spec.json',spec)
   new(OUT/'preregistration.json',dict(schema='task1-layer-dtn-phase1-preregistration-v1',source_sha256=sources,input_sha256=refs,spec_sha256=sha(OUT/'spec.json'),new_CEM_RHS=0,physical_evaluation_cells=793860,physical_cell_limit=800000,graph_nodes=7860,matrix_entries=61779600,limits=limits,hard_child_seconds=600,cache_max_additional_bytes_reserved=600000000,child_address_space_upper_bound_bytes=4200000000,local_cache_not_remote_verified=True))
   for p in SRC.iterdir():
    if p.is_file():shutil.copyfile(p,OUT/'source'/p.name)
  prior=read('/dev/shm/task1-u19-basis-audit-20261025-run/result-publication.json');req(prior['status']=='published_readback_verified','Completed priorbasisQApublication required')
  files={'tools/layer_dtn_phase1_20261025/'+p.name:p for p in SRC.iterdir()if p.is_file()}
  for path in reg['helper_sha256']:files['tools/layer_dtn_phase1_20261025/frozen-global-helpers/'+Path(path).name]=Path(path)
  for n in('registration.json','preregistration.json','spec.json'):files['data-native/cloud-layer-dtn-phase1-20261025/'+n]=OUT/n
  files['docs/TASK1_LAYER_DTN_PHASE1_20261025/feasibility.json']=Path('/dev/shm/task1-resume-20261025/audit/layer-DtN-feasibility.json')
  plan=publication_plan(files,prior['commit'],'Preregister bounded same-XY graph eigensystem and analytic-depth benchmark; no CEM solve',OUT/'source-publication/result-publication.json');new(OUT/'source-plan.json',plan)
  command([sys.executable,'-B',str(PUB),'--plan',str(OUT/'source-plan.json'),'--output','/dev/shm/task1-git-layer-dtn-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',330,True)
  sp=read(OUT/'source-publication/result-publication.json');req(sp['status']=='published_readback_verified','Actualsource/configpublication required beforeeigen')
  with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
   guard();tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));as_limit=int(min(4200000000,limits['total_memory_bytes']-tmp-b.rss(pid)-700000000));req(as_limit>=2500000000,'Insufficient approved memory for conservative eigen input/Q/workspace pluscache; preserve allolddata')
   new(OUT/'numeric-child-resource-admission.json',dict(approved_RSS_plus_tmpfs_bytes=limits['total_memory_bytes'],observed_tmpfs_before_bytes=tmp,parent_RSS_before_bytes=b.rss(pid),reserved_cache_and_monitor_bytes=700000000,RLIMIT_AS_bytes=as_limit,scope='Conservative address-space ceiling in addition to250ms actual aggregateRSS+tmpfs monitoring; not an allocation guarantee'))
   command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(SRC/'phase1_worker.py'),'--output',str(OUT),'--as-limit',str(as_limit)],'graph-eigen-and-MMS-child',600)
  wr=read(OUT/'worker-receipt.json');req(wr['status']=='phase1_graph_eigen_MMS_calculated','Actualvalidatedphase1workerreceipt required');summary=read(OUT/'summary.json')
  new(OUT/'next-decision.json',dict(status='phase1_completed_CEM_reference_requires_separate_root_review_and_registration',actual_source_commit=sp['commit'],analytic_passed=summary['analytic']['passed'],new_CEM_RHS=0,candidate_adopted=False,old_5percent_flags_retained=True,next_scientific_condition='Use measured backendcost/error/memory and localcacheSHA to review one separately registered2RHS continuous-z CEM reference at identicalXY/material/topology; no automaticaccuracy/adoption',Windows_storage_verified=False,cache_remote_verified=False))
  checkpoint('eigen_benchmark_complete_result_publication_pending',eigen_wall_seconds=summary['eigen']['eigen_wall_seconds'])
  snapshot=dict(status='numeric_phase_completed_before_publication',resources={k:v for k,v in state.items()if k.startswith('peak_')},new_CEM_RHS=0,worker_receipt_sha256=sha(OUT/'worker-receipt.json'));new(OUT/'parent-numeric-checkpoint.json',snapshot)
  files={}
  for n in('summary.json','arrays.npz','tests.log','worker-receipt.json','threadpool-runtime.json','numeric-child-resource-admission.json','parent-numeric-checkpoint.json','next-decision.json'):
   files['data-native/cloud-layer-dtn-phase1-20261025/'+n]=OUT/n
  files['data-native/cloud-layer-dtn-phase1-20261025/local-eigen-cache-manifest.json']=OUT/'eigen-cache/manifest.json'
  resultplan=publication_plan(files,sp['commit'],'Preserve measured graph eigen and analytic-depth benchmark with explicit local-cache durability limits',OUT/'result-publication/result-publication.json',comment='동일XY그래프7860노드의고유분해·해석깊이벤치마크 완료. 실제CEM/전기장/PDE RHS는0이며 기존5%실패는유지합니다. 전체고유잔차/정규화와64열표본직교검사·해석해검사를분리하고실제CPU/RAM/시간을기록했습니다. Q캐시는로컬tmpfs파생캐시이며원격영속저장검증이아님을명시합니다. 다음실제CEM기준해는별도등록/검증후결정합니다.\n자료: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/tree/codex/task1-cloud-restart-20261020/data-native/cloud-layer-dtn-phase1-20261025\nCPU4/총RSS+ownedtmpfs8e9/800000물리평가셀/단일소유자/600초수치child watchdog/누적시간무제한 유지,Windows저장미검증.')
  new(OUT/'result-plan.json',resultplan);command([sys.executable,'-B',str(PUB),'--plan',str(OUT/'result-plan.json'),'--output','/dev/shm/task1-git-layer-dtn-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',330,True)
  rp=read(OUT/'result-publication/result-publication.json');req(rp['status']=='published_readback_verified','Actualfullreadbackrequired')
  receipt.update(status='phase1_graph_eigen_MMS_published_verified',source_commit=sp['commit'],result_commit=rp['commit'],new_CEM_RHS=0,worker_elapsed_seconds=wr['elapsed_seconds'],eigen_wall_seconds=wr['actual_eigen_wall_seconds']);checkpoint('finite_phase1_complete_next_CEM_registration_required',result_commit=rp['commit'],next_decision=str(OUT/'next-decision.json'))
 except BaseException as e:
  failed_phase=state['phase'];receipt.update(error_type=type(e).__name__,error=str(e),failed_phase=failed_phase);checkpoint('failed_preserved',error=str(e),failed_phase=failed_phase)
  # Preserve and publish failed scientific evidence without retrying the solve.
  try:
   source_result=OUT/'source-publication/result-publication.json'
   if source_result.is_file()and read(source_result)['status']=='published_readback_verified':
    failure=dict(status='failed_preserved_not_a_validated_eigenbasis',error_type=type(e).__name__,error=str(e),failed_phase=failed_phase,new_CEM_RHS=0,resources={k:v for k,v in state.items()if k.startswith('peak_')},partial_cache_files=[dict(name=p.name,bytes=p.stat().st_size,verified_complete=False)for p in(OUT/'eigen-cache').glob('*')if p.is_file()],originals_deleted=False)
    new(OUT/'failure-evidence.json',failure);files={'data-native/cloud-layer-dtn-phase1-20261025/failure-evidence.json':OUT/'failure-evidence.json'}
    for name in('worker-receipt.json','tests.log','numeric-child-resource-admission.json'):
     if(OUT/name).is_file():files['data-native/cloud-layer-dtn-phase1-20261025/failed-'+name]=OUT/name
    for p in(OUT/'logs').iterdir():
     if p.is_file()and p.stat().st_size<4*1024**2:files['data-native/cloud-layer-dtn-phase1-20261025/failure-logs/'+p.name]=p
    plan=publication_plan(files,read(source_result)['commit'],'Preserve failed finite graph eigen benchmark evidence without repeating computation',OUT/'result-publication/result-publication.json',comment='층방향기준해전처리 유한벤치마크 실패증거를보존했습니다. 실패단계: '+failed_phase+'; '+str(e)[:1000]+'. 새로운CEM계산/후보채택/5%실패해제는없습니다. 원본·부분파일은삭제하지않았고 재실행은진단후새등록으로만진행합니다.')
    new(OUT/'failure-plan.json',plan);command([sys.executable,'-B',str(PUB),'--plan',str(OUT/'failure-plan.json'),'--output','/dev/shm/task1-git-layer-dtn-failure-20261025','--queue-registration',str(OUT/'registration.json')],'failure-evidence-publication',330,True)
    receipt['failure_evidence_commit']=read(OUT/'result-publication/result-publication.json')['commit']
  except BaseException as publication_error:receipt['failure_publication_error']=str(publication_error)
  checkpoint('failed_preserved',error=str(e),failed_phase=failed_phase,failure_evidence_commit=receipt.get('failure_evidence_commit'));raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
  for p,t in b.owned_descendants(pid,ticks,dict(owned)).items():
   if p!=pid and b.live(p,t):
    try:os.kill(p,signal.SIGKILL)
    except ProcessLookupError:pass
  elapsed=time.monotonic()-start;ledger=budget.load_ledger();debit=max(0.,elapsed-git_wall);ledger['spent_seconds']+=debit;ledger['runs'].append(dict(run_id=OUT.name,stage='layer_DtN_phase1_numerical_and_supervision',seconds=debit,status=receipt['status'],Git_children_debited_separately=True,new_CEM_RHS=0));temp=LEDGER.with_name('task1-budget-layer-dtn-'+str(pid)+'.tmp');new(temp,ledger);os.replace(temp,LEDGER)
  receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')},remaining_approved_seconds=budget.remaining_seconds(ledger),Windows_saved_verified=False);new(OUT/'receipt.json',receipt)
  for s,h in handlers.items():signal.signal(s,h)
  print(json.dumps(receipt,ensure_ascii=False))
