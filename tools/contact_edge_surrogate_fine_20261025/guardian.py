"""One finite boundary-Galerkin owner; immutable source, publication, watchdog and failures."""
import sys,os,json,time,signal,threading,subprocess,hashlib,shutil
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');BASE=Path('/dev/shm/task1-contact-continuation-20261025');SRC=Path('/dev/shm/task1-contact-edge-surrogate-fine-20261025/source');OWNER=BASE/'href-fine-owner-source';OUT=Path('/dev/shm/task1-contact-edge-surrogate-fine-20261025-run');PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py');LEDGER=ROOT/'runtime/task1-budget.json';CAP=1600
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

ADMISSION_INPUTS={'/dev/shm/task1-contact-continuation-20261025/fv-recovery-transfer-stage/FV_VALIDATION.json': '704347ecb19dff4addc4acd2dd3701e643d6801975763b53f7a21effa09563d3', '/dev/shm/task1-contact-edge-fv-recovery-20261025-run/summary.json': '0fc23dd7b47601c8f24b471147ee5e542d19e0423f2fbb1753bb77ac6252b1c0', '/dev/shm/task1-contact-edge-fv-recovery-20261025-run/receipt.json': 'b087608794e75e6d291f03b771ae4ddd74ae4b9469cf3b84cd1bd2bedbd1411c', '/dev/shm/task1-contact-edge-fv-recovery-20261025-run/result-publication/result-publication.json': '704744731b306b31c45834fbc0b244725248a751b25a7d69eee3f6f5e9073cee'}
def validated_FV_admission():
 for path,digest in ADMISSION_INPUTS.items():req(sha(path)==digest,'Pinned actual FV admission changed')
 a=read('/dev/shm/task1-contact-continuation-20261025/fv-recovery-transfer-stage/FV_VALIDATION.json');summary=read('/dev/shm/task1-contact-edge-fv-recovery-20261025-run/summary.json');proof=read('/dev/shm/task1-contact-edge-fv-recovery-20261025-run/result-publication/result-publication.json')
 req(a['all_internal_gates_passed'] and summary['all_internal_gates_passed'] and a['reused_prior_phi']==1 and a['new_FV_solves']==11,'Actual recovered FV numerical validation required')
 req(all(row['reference_flags_passed']for row in a['fine_half_cell_methods']),'Actual finest FV reference flags required')
 req(proof['status']=='published_readback_verified' and proof['commit']=='33ffc6a52e4f396517d988bc99dd4989dacdc2b7','Actual FV result publication required')
 refs=dict(ADMISSION_INPUTS);pipeline=Path('/dev/shm/task1-contact-edge-pipeline-20261025-run/registration.json');req(pipeline.is_file(),'Actual bounded pipeline registration required');refs[str(pipeline)]=sha(pipeline)
 prior=Path(os.environ['TASK1_CONTACT_PRIOR_RUN']);decision=read(prior/'continuation-decision.json');previous_owner=read(prior/'receipt.json');previous_pub=read(prior/'result-publication/result-publication.json');req(decision['selected_refinement'] is True and previous_pub['status']=='published_readback_verified' and previous_owner['result_commit']==previous_pub['commit'],'Actual preceding result and predeclared refinement choice required')
 for name in ['summary.json','receipt.json','continuation-decision.json','result-publication/result-publication.json']:refs[str(prior/name)]=sha(prior/name)
 return refs

def main():
 with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
  req(not OUT.exists(),'Unique run required; preserve old attempts');OUT.mkdir();(OUT/'logs').mkdir();(OUT/'source-publication').mkdir();(OUT/'result-publication').mkdir();(OUT/'source').mkdir()
  limits=ep.resolve_limits();configured=ep.configure_process(limits);ledger=budget.load_ledger();req(ledger.get('cumulative_time_unlimited')is True,'Unlimited authorization required');budget.require_time_budget(ledger,CAP)
  pid=os.getpid();ticks=b.ticks(pid);start=time.monotonic();owned={pid:ticks};stop=threading.Event();state=dict(phase='preparing',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);counter=0;git_wall=0.;mutex=threading.RLock()
  sources={str(p):sha(p)for directory in [SRC,OWNER,BASE/'pipeline-source']for p in directory.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')};helpers={str(ROOT/'tools'/n):sha(ROOT/'tools'/n)for n in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),source_sha256=sources,helper_sha256=helpers,outer_deadline_seconds=CAP,numerical_child_deadline_seconds=600,resource_limits=limits,execution_policy_refs=ep.execution_policy_refs(),configured=configured,new_full_phantom_CEM=0)
  new(OUT/'registration.json',reg);frozen_inputs={str(OUT/'registration.json'):sha(OUT/'registration.json')};receipt=dict(schema='task1-contact-edge-Galerkin-owner-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,new_full_phantom_CEM=0,Windows_saved_verified=False)
  def checkpoint(phase,**extra):
   nonlocal counter
   with mutex:
    counter+=1;j=dict(schema='task1-contact-edge-Galerkin-live-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),j)
    for target in [OUT/'current.json',ROOT/'runtime/task1-contact-edge-live-20261025.json']:
     tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,j);os.replace(tmp,target)
    state['phase']=phase
  def guard():
   live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);rss=sum(b.rss(p)for p,t in live.items()if b.live(p,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp))
   req(rss+tmp<=limits['total_memory_bytes'],'Actual aggregate RSS+ALL task1-ownedtmpfs cap');req(time.monotonic()-start<CAP,'Finite1600s owner watchdog');req(not(OUT/'STOP').exists(),'Explicit STOP marker')
   for p,h in{**sources,**helpers,**reg['execution_policy_refs'],**frozen_inputs}.items():req(sha(p)==h,'Frozen source/input/policy changed '+p)
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
   nonlocal git_wall
   guard();checkpoint(label);log=OUT/'logs'/(str(counter)+'-'+label+'.log');before=time.monotonic();ledger_rows_before=len(budget.load_ledger()['runs'])
   with log.open('xb')as stream:
    child=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);owned[child.pid]=b.ticks(child.pid);checkpoint(label,child_pid=child.pid,child_start_ticks=owned[child.pid],child_timeout_seconds=seconds)
    try:code=child.wait(timeout=min(seconds,CAP-time.monotonic()+start))
    finally:
     if child.poll()is None:child.kill();child.wait(timeout=5)
     if is_git:
      child_run=Path(argv[argv.index('--output')+1]).name
      recorded=sum(row.get('seconds',0.)for row in budget.load_ledger()['runs'][ledger_rows_before:]if row.get('run_id')==child_run)
      git_wall+=min(time.monotonic()-before,recorded)
   req(code==0,'Finite child failed '+label+'; preserved log '+str(log))
  def plan(files,parent,message,destination,comment=None):
   return dict(schema='task1-supported-Git-transport-plan-v1',repository='yoodohyun-codex-cloud/ngg-tis-task1',branch='codex/task1-cloud-restart-20261020',expected_parent=parent,message=message,files={target:dict(local_path=str(p),SHA256=sha(p),bytes=p.stat().st_size)for target,p in files.items()},required_result_receipt=str(destination),required_receipt_status='published_readback_verified',new_PDE_required=False,comment_body=comment)
  try:
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    import contact_edge_surrogate as model
    spec=model.make_spec();refs=model.required_inputs()if hasattr(model,'required_inputs')else{};refs.update(validated_FV_admission());refs.update(reg['execution_policy_refs']);refs.update(helpers);new(OUT/'spec.json',spec)
    new(OUT/'preregistration.json',dict(schema='task1-contact-edge-Galerkin-preregistration-v1',question='Do original2000HzSC/contact coefficients alter the separate equipotential-slab boundary sensitivity and panel/harmonic diagnostics, with unchanged physics definitions/gates and no actual4pad adoption?',source_sha256=sources,input_sha256=refs,spec_SHA256=sha(OUT/'spec.json'),limits=limits,hard_child_seconds=600,new_full_phantom_CEM=0,new_TIS=0,prior_failed_model_commit='d2456af62d0686e06555d9e6664ee5d3504d8c64',old_failed_flags_preserved=True,criteria_relaxed=False))
    frozen_inputs.update(refs);frozen_inputs.update({str(OUT/n):sha(OUT/n)for n in('spec.json','preregistration.json')})
    for directory in [SRC,OWNER,BASE/'pipeline-source']:
     for p in directory.iterdir():
      if p.is_file():shutil.copyfile(p,OUT/'source'/p.name)
   head=os.environ['TASK1_EXPECTED_TOPIC_PARENT']
   files={}
   for directory in [SRC,OWNER,BASE/'pipeline-source']:
    for p in directory.iterdir():
     if p.is_file():files['tools/contact_edge_surrogate_fine_20261025/'+p.name]=p
   for n in ('registration.json','preregistration.json','spec.json'):files['data-native/contact-edge-surrogate-fine-20261025/'+n]=OUT/n
   files['data-native/contact-edge-surrogate-fine-20261025/pipeline-registration.json']=Path('/dev/shm/task1-contact-edge-pipeline-20261025-run/registration.json')
   spath=OUT/'source-plan.json';new(spath,plan(files,head,'Preregister mixed-boundary contact Galerkin and a single finite execution owner',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(spath),'--output','/dev/shm/task1-git-contact-edge-surrogate-fine-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',330,True)
   sp=read(OUT/'source-publication/result-publication.json');req(sp['status']=='published_readback_verified','Immutable source publication precedes new calculation')
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    guard();tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));as_limit=int(min(2500000000,limits['total_memory_bytes']-tmp-b.rss(pid)-600000000));req(as_limit>=1000000000,'Insufficient approved RSS+tmpfs headroom; preserve originals')
    new(OUT/'numeric-admission.json',dict(aggregate_cap_bytes=limits['total_memory_bytes'],observed_owned_tmpfs_bytes=tmp,parent_RSS_bytes=b.rss(pid),child_RLIMIT_AS_bytes=as_limit,extra_reserve_bytes=600000000))
    command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(OWNER/'worker.py'),'--output',str(OUT),'--source',str(SRC),'--as-limit',str(as_limit)],'synthetic_equipotential-boundary-numeric-child',600)
   wr=read(OUT/'worker-receipt.json');req(wr['status']=='synthetic_equipotential_contact_boundary_diagnostic_computed','Actual synthetic_equipotential result required');summary=read(OUT/'summary.json')
   new(OUT/'numeric-checkpoint.json',dict(status='synthetic_equipotential_calculation_complete_publication_pending',resources={k:v for k,v in state.items()if k.startswith('peak_')},source_commit=sp['commit'],worker_receipt_SHA256=sha(OUT/'worker-receipt.json'),old_phantom_failures_retained=True))
   files={}
   for p in OUT.rglob('*'):
    rel=p.relative_to(OUT)
    if p.is_file()and ((len(rel.parts)==1 and (p.name in('summary.json','arrays.npz','tests.log','worker-receipt.json','threadpool-runtime.json','numeric-admission.json','numeric-checkpoint.json','benchmark-spec.json','resume-index.json')or p.name.startswith(('case-','resume-index-'))))or rel.parts[0]in('cases','progress')):files['data-native/contact-edge-surrogate-fine-20261025/'+rel.as_posix()]=p
   files['data-native/contact-edge-surrogate-fine-20261025/source-publication-receipt.json']=OUT/'source-publication/result-publication.json'
   rp=OUT/'result-plan.json';new(rp,plan(files,sp['commit'],'Preserve mixed-boundary synthetic_equipotential fields, E/J errors and contact quadrature diagnostics',OUT/'result-publication/result-publication.json',comment='검증된FV진단을근거로 기존2000HzCEM의SCgamma/zA를그대로옮긴별도슬래브조건을실제계산했습니다. 실제4패드모델이나사람확정물성/TIS검증이아닙니다. 접촉 경계를 정렬한 주기SC슬래브의 Fourier–Galerkin 기준 문제를 실제 계산했습니다. 전체접촉1D해석해 검사와 부분접촉5조건의 패널/Fourier절단 비교, 전기장·전류·signed복소전력 및 원시배열을 보존합니다. 합성물성/이상전압/접지된바닥의2D진단이며 실제고정4패드팬텀/공통귀환회로/TIS/사람물성검증과 구분합니다. 기존XY102의13/14실패·후보미채택을 유지합니다. 결과를 검토해 다음접촉경계검증을 이어가고 원본전송manifest를 추가합니다. 실제Windows저장/OneDrive동기화는미검증입니다. 자료: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/tree/codex/task1-cloud-restart-20261020/data-native/contact-edge-surrogate-fine-20261025'))
   command([sys.executable,'-B',str(PUB),'--plan',str(rp),'--output','/dev/shm/task1-git-contact-edge-surrogate-fine-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',330,True)
   r=read(OUT/'result-publication/result-publication.json');req(r['status']=='published_readback_verified','Full result readback required');receipt.update(status='synthetic_equipotential_boundary_computed_published_review_next_condition',source_commit=sp['commit'],result_commit=r['commit'],worker_elapsed_seconds=wr['elapsed_seconds']);checkpoint('published_reviewing_next_scientific_condition',result_commit=r['commit'])
  except BaseException as e:
   failed=state['phase'];receipt.update(error_type=type(e).__name__,error=str(e),failed_phase=failed);checkpoint('failed_preserved',failed_phase=failed,error=str(e))
   # No solve retry here: root must diagnose preserved partials before selecting another finite condition.
   raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   for p,t in b.owned_descendants(pid,ticks,dict(owned)).items():
    if p!=pid and b.live(p,t):
     try:os.kill(p,signal.SIGKILL)
     except ProcessLookupError:pass
   elapsed=time.monotonic()-start;ledger=budget.load_ledger();debit=max(0.,elapsed-git_wall);ledger['spent_seconds']+=debit;ledger['runs'].append(dict(run_id=OUT.name,stage='contact_edge_Galerkin_numerical_and_supervision',seconds=debit,status=receipt['status'],Git_children_debited_separately=True));temp=LEDGER.with_name('task1-budget-contact-edge-'+str(pid)+'.tmp');new(temp,ledger);os.replace(temp,LEDGER)
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')},remaining_approved_seconds=budget.remaining_seconds(ledger));new(OUT/'receipt.json',receipt)
   for s,h in handlers.items():signal.signal(s,h)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
