"""One finite existing-owner U19 continuation; no detached infinite worker."""
import sys,os,json,time,signal,subprocess,threading,hashlib,shutil
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');sys.path.insert(0,str(ROOT/'tools'))
import task1_bounded_continuation as b,task1_execution_policy as ep
OUT=Path('/dev/shm/task1-u19-continuation-20261025-run');RUN=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run');OWNER=Path('/dev/shm/task1-vs19-uniform-2000-20261025/source/u19_run.py');PUBLISHER=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py');CAP=1200

def req(x,m):
 if not x:raise ValueError(m)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new(p,j):
 with Path(p).open('x')as f:json.dump(j,f,ensure_ascii=False,allow_nan=False,indent=2)
def size(p):return p.stat().st_size if p.is_file()else sum(q.stat().st_size for q in p.rglob('*')if q.is_file())
with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
 req(not OUT.exists(),'Preserve previous queue attempts');OUT.mkdir();(OUT/'logs').mkdir();start=time.monotonic();pid=os.getpid();ticks=b.ticks(pid);owned={pid:ticks};stop=threading.Event();limits=ep.resolve_limits();ep.configure_process(limits);state=dict(phase='registering',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);counter=0
 reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUBLISHER),publisher_sha256=sha(PUBLISHER),owner_path=str(OWNER),owner_sha256=sha(OWNER),run=str(RUN),max_native_conditions=1,maximum_new_native_RHS=2,outer_deadline_seconds=CAP,resource_policy_refs=ep.execution_policy_refs(),source_publication_commit=read(RUN/'source-publication.json')['commit'],cumulative_time_unlimited=True)
 new(OUT/'registration.json',reg);receipt=dict(schema='task1-finite-U19-continuation-receipt-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,stop_reason=None)
 def checkpoint(phase,**extra):
  global counter
  counter+=1;value=dict(schema='task1-active-finite-U19-continuation-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,run=str(RUN),elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(4)+'.json'),value)
  for target in(OUT/'current.json',ROOT/'runtime/task1-live-native-controller.json'):
   temp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(temp,value);os.replace(temp,target)
  state['phase']=phase
 def guard():
  live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);rss=sum(b.rss(p)for p,t in live.items()if b.live(p,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp));req(rss+tmp<=limits['total_memory_bytes'],'AggregateRSS+ALLownedtmpfs8e9');req(time.monotonic()-start<CAP,'Finite1200secondcontinuationdeadline');req(sha(OWNER)==reg['owner_sha256']and sha(PUBLISHER)==reg['publisher_sha256']and sha(__file__)==reg['controller_sha256'],'Frozenowner/publisher/controllerchanged')
 def interrupt(s,f):raise InterruptedError(state.get('error','External signal or finite continuation deadline'))
 def monitor():
  while not stop.wait(1):
   try:guard()
   except BaseException as e:state['error']=str(e);os.kill(pid,signal.SIGTERM);return
 handlers={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGINT,signal.SIGTERM)}
 for s in handlers:signal.signal(s,interrupt)
 signal.setitimer(signal.ITIMER_REAL,CAP);thread=threading.Thread(target=monitor,daemon=True);thread.start()
 def command(argv,label,timeout,allow_transport=False):
  guard();checkpoint(label);log=OUT/'logs'/(str(counter)+'-'+label+'.log')
  with log.open('xb')as stream:
   child=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);owned[child.pid]=b.ticks(child.pid);checkpoint(label,child_pid=child.pid,child_start_ticks=owned[child.pid],log=str(log))
   try:code=child.wait(timeout=min(timeout,CAP-time.monotonic()+start))
   finally:
    if child.poll()is None:child.terminate();child.wait(timeout=5)
  if code and allow_transport and read(RUN/'publish-results-receipt.json')['status']=='requires_supported_Git_transport':return
  req(code==0,'Finite stage failed: '+label+'; log='+str(log))
 def completed(stage):
  p=RUN/(stage+'-receipt.json')
  if not p.is_file():return False
  r=read(p)
  return r.get('new_native_conditions_completed')==1 if stage=='execute'else(r.get('status','').startswith('new_native_postprocessed')if stage=='postprocess'else r.get('local_native_and_post_hashes_verified')is True)
 try:
  req(read(RUN/'source-publication.json')['status']=='published_readback_verified','Actualsourcepublicationrequired');checkpoint('registered')
  if not completed('execute'):
   # Never restart a live or failed previous solve. Root may already have started it.
   heartbeat=read(RUN/'heartbeat.json');hp=heartbeat.get('pid');ht=heartbeat.get('proc_start_ticks')
   if heartbeat.get('stage')=='execute'and b.live(hp,ht):
    req(str(OWNER).encode()in Path('/proc',str(hp),'cmdline').read_bytes().split(b'\0'),'Exact existing native owner');checkpoint('tracking_existing_native_owner',native_owner_pid=hp,native_owner_startticks=ht)
    while b.live(hp,ht):guard();time.sleep(1)
    req(completed('execute'),'Existingownerendedwithoutcompletedreceipt; preserve failure, no repeat')
   else:
    req(not(RUN/'execute-receipt.json').exists()and not(RUN/'native-sha256.json').exists()and not any((RUN/'bases').iterdir()),'Preserve failed/partial native data; no duplicate solve')
    command([sys.executable,'-B',str(OWNER),'--execute','--output',str(RUN)],'execute',225)
  if not completed('postprocess'):command([sys.executable,'-B',str(OWNER),'--postprocess','--output',str(RUN)],'postprocess',165)
  summary=read(RUN/'postprocess/summary.json');adj=summary['adjacent_VS_checks'];comparison=summary['independent_same_physical_region_comparison']['fixed23_75mm'];unresolved=any(v['order']=='common_two_point'and v['interface_depth_mm']<1 and not v['fine_passed']for v in comparison['rows'])
  next_decision=dict(schema='task1-U19-next-scientific-selection-v1',prior_actual_case=summary['case_id'],adjacent_all_passed=adj['all_passed'],independent_common2_flags_unresolved=unresolved,candidate_adopted=False,full_convergence_validated=False,criteria_relaxed=False,selected_next=('Finite cached source-basis and mask/edge localization QA on both actual2RHS; then separately registered2010Hz same-mesh comparison only after source/material/contact validation'if adj['all_passed']else'Investigate failed scalar sensitivities using preserved native fields before any frequency/design expansion'),reason='Distinguish geometry/current transfer from one-sided estimator bias. Preserve actual2/2and3/3/absolute-current differences and allfailed5percentflags; no SC16/cellcap increase or automaticadoption.',next_execution_ready=False,resume_condition='Register and validate the next finite source after reviewing this actual result; no cumulative-time approval blocker',next_command='python -B /dev/shm/task1-u19-continuation-20261025/source/controller.py  # completed immutable queue: do not rerun; use its next-decision.json to register a new finite batch',limits=limits,Windows_storage_verified=False)
  new(OUT/'next-decision.json',next_decision);new(OUT/'actual-summary-receipt.json',dict(summary_sha256=sha(RUN/'postprocess/summary.json'),actual_native_execute=read(RUN/'execute-receipt.json'),actual_postprocess=read(RUN/'postprocess-receipt.json'),adjacent_checks=adj,independent_same_physical_region_comparison=comparison))
  if not(RUN/'result-publication.json').exists():
   if not(RUN/'external-git-publication-plan.json').exists():command([sys.executable,'-B',str(OWNER),'--publish-results','--output',str(RUN)],'prepare-publication',270,True)
   plan=read(RUN/'external-git-publication-plan.json')
   for name in('registration.json','next-decision.json','actual-summary-receipt.json'):
    p=OUT/name;plan['files']['docs/TASK1_U19_NATIVE_2000_20261025/'+name]=dict(local_path=str(p),SHA256=sha(p),bytes=p.stat().st_size)
   p=Path(__file__).resolve();plan['files']['tools/u19_continuation_20261025/controller.py']=dict(local_path=str(p),SHA256=sha(p),bytes=p.stat().st_size)
   for p in PUBLISHER.parent.iterdir():
    if p.is_file()and p.suffix=='.py':plan['files']['tools/git_verified_publication_r3_20261025/'+p.name]=dict(local_path=str(p),SHA256=sha(p),bytes=p.stat().st_size)
   plan['comment_body']='U19 실제793860cell/2000Hz2RHS 계산·후처리 완료. 13개 scalar비교 all_passed='+str(adj['all_passed'])+'; 독립common2의5%실패잔여='+str(unresolved)+'. 동일ROI/물리마스크/2점·3점차수와절대전류차이·분모를 유지하고 source/contact/power/phi/E 원자료를보존했습니다. 전체수렴/후보채택/활성화·안전검증은아닙니다.\n\n자료: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/tree/codex/task1-cloud-restart-20261020/data-native/cloud-vs19-uniform-2000-20261025\n다음선정과실제실행을구분한 next-decision.json도함께보존합니다. G18은사전MMS비악화실패로미실행보존. 누적시간무제한/CPU4/RSS+전체ownedtmpfs8e9bytes/800000cells/단일소유자/유한watchdog 유지. Windows저장미검증.'
   new(OUT/'result-plan.json',plan);transport=Path('/dev/shm/task1-git-u19-native-20261025');command([sys.executable,'-B',str(PUBLISHER),'--plan',str(OUT/'result-plan.json'),'--output',str(transport),'--queue-registration',str(OUT/'registration.json')],'supported-Git-publication',330)
  if not completed('persist'):command([sys.executable,'-B',str(OWNER),'--persist','--output',str(RUN)],'verify-persistence',65)
  req(read(RUN/'result-publication.json')['status']=='published_readback_verified','Actualfullreadbackrequired')
  checkpoint('result_calculated_published_verified',result_commit=read(RUN/'result-publication.json')['commit'],next_decision=str(OUT/'next-decision.json'))
  # Feedback is ancillary to the already completed scientific result, and is not
  # used to pretend a further unregistered PDE started.
  proc=subprocess.Popen(['gh','api','repos/yoodohyun-codex-cloud/ngg-tis-task1/issues/2/comments?since=2026-10-25T04%3A12%3A00Z&per_page=100'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);owned[proc.pid]=b.ticks(proc.pid)
  try:raw,error=proc.communicate(timeout=30)
  finally:
   if proc.poll()is None:proc.kill();proc.wait(timeout=2)
  if proc.returncode==0:
   comments=json.loads(raw);new(OUT/'feedback.json',dict(status='actual_readonly_feedback_received',checked_utc=b.now(),comments=[dict(id=v['id'],url=v['html_url'],author=v['user']['login'],body=v['body'],created_at=v['created_at'])for v in comments]));receipt['feedback_status']='received_review_for_next_registration'
  else:new(OUT/'feedback-failure.json',dict(status='readonly_feedback_failed_result_publication_intact',returncode=proc.returncode,stderr=error.decode(errors='replace')[:3000]));receipt['feedback_status']='readonly_service_failure_preserved'
  receipt.update(status='finite_U19_continuation_complete_next_batch_requires_registration',result_commit=read(RUN/'result-publication.json')['commit'],stop_reason='predeclared finite case complete; nextsource implementation/registration required, not turn end or time budget',next_decision=str(OUT/'next-decision.json'));checkpoint('finite_scope_complete_next_source_registration_required',result_commit=receipt['result_commit'],next_decision=receipt['next_decision'],stop_reason=receipt['stop_reason'])
 except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e),failed_phase=state['phase'],stop_reason='actual numerical/transport/resource/controller error preserved; not cumulative time budget');checkpoint('failed_preserved',failed_phase=state['phase'],error=str(e));raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
  for p,t in b.owned_descendants(pid,ticks,dict(owned)).items():
   if p!=pid and b.live(p,t):
    try:os.kill(p,signal.SIGTERM)
    except ProcessLookupError:pass
  receipt.update(finished_utc=b.now(),elapsed_seconds=time.monotonic()-start,resources={k:v for k,v in state.items()if k.startswith('peak_')},ledger_accounting='Child stages debit actualelapsed; supervisor wall not doublecharged');new(OUT/'receipt.json',receipt)
  for s,h in handlers.items():signal.signal(s,h)
  print(json.dumps(receipt,ensure_ascii=False))
