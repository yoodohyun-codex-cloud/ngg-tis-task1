"""Finite two-batch evidence-driven contact validation, one numerical owner at a time."""
import hashlib,json,os,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');BASE=Path('/dev/shm/task1-contact-continuation-20261025');SRC=BASE/'pipeline-source';OUT=Path('/dev/shm/task1-contact-edge-pipeline-20261025-run');CAP=7200
sys.path.insert(0,str(ROOT/'tools'))
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget
PREVIOUS=BASE/'fv-recovery-transfer-stage/merged-manifest.json'
PREVIOUS_SHA='e0a94051b02f9273f04baddfdd3691a94267b7e811c13cff6c0af01c9a9ecae2'

def req(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new(p,value):
 raw=json.dumps(value,allow_nan=False,ensure_ascii=False,indent=2).encode()
 with Path(p).open('xb')as f:f.write(raw)
def size(p):
 try:return p.stat().st_size if p.is_file()else sum(q.stat().st_size for q in p.rglob('*')if q.is_file())
 except FileNotFoundError:return 0

def main():
 with b.dual_lock(ROOT/'.task1-contact-pipeline.lock'):
  req(not OUT.exists(),'Preserve any existing pipeline; no blind restart');OUT.mkdir();(OUT/'logs').mkdir();limits=ep.resolve_limits();settings=ep.configure_process(limits);req(budget.load_ledger().get('cumulative_time_unlimited')is True,'Unlimited cumulative authorization required');req(sha(PREVIOUS)==PREVIOUS_SHA,'Fixed preceding FV transfer manifest')
  pid=os.getpid();ticks=b.ticks(pid);start=time.monotonic();owned={pid:ticks};stop=threading.Event();mutex=threading.RLock();counter=0;state=dict(phase='starting',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);child_debits=0.
  directories=[SRC,BASE/'href-owner-source',BASE/'href-fine-owner-source',Path('/dev/shm/task1-contact-edge-surrogate-20261025/source'),Path('/dev/shm/task1-contact-edge-surrogate-fine-20261025/source')]
  pins={str(p):sha(p)for directory in directories for p in directory.iterdir()if p.is_file()};pins.update(ep.execution_policy_refs());new(OUT/'registration.json',dict(schema='task1-contact-bounded-pipeline-v1',pid=pid,proc_start_ticks=ticks,source_and_policy_SHA256=pins,limits=limits,configured=settings,finite_total_seconds=CAP,maximum_numerical_batches=2,maximum_partial_slab_RHS=10,maximum_analytic_contract_RHS=2,new_actual4pad_CEM_RHS=0,next_selection='After first actual result, choose a five-case resolution follow-up only if last panel/harmonic flags fail or last panel Jmax grows more than5percent. No voltage/material/threshold fitting.',previous_manifest_SHA256=PREVIOUS_SHA,originals_preserved=True,Windows_saved_verified=False))
  def checkpoint(phase,**extra):
   nonlocal counter
   with mutex:
    counter+=1;value=dict(extra);value.update(schema='task1-contact-bounded-pipeline-live-v1',pid=pid,proc_start_ticks=ticks,updated_utc=b.now(),phase=phase,elapsed_seconds=time.monotonic()-start);new(OUT/('checkpoint-%05d.json'%counter),value)
    for target in [OUT/'current.json',ROOT/'runtime/task1-contact-pipeline-live-20261025.json']:
     tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,value);os.replace(tmp,target)
    state['phase']=phase
  def guard():
   live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);rss=sum(b.rss(p)for p,t in live.items()if b.live(p,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp));req(rss+tmp<=limits['total_memory_bytes'],'Aggregate pipeline processes RSS plus ALL task1 tmpfs cap');req(time.monotonic()-start<CAP,'Finite7200secondpipelinewatchdog');req(not(OUT/'STOP').exists(),'Explicit pipeline STOP')
   for p,h in pins.items():req(sha(p)==h,'Frozen pipeline/source/policy changed: '+p)
  def interrupt(sig,frame):raise InterruptedError(state.get('error','Finite pipeline watchdog/external interrupt'))
  def monitor():
   last=0.
   while not stop.wait(.25):
    try:
     guard()
     if time.monotonic()-last>5:checkpoint(state['phase'],observed_peak_accounted_bytes=state['peak_accounted']);last=time.monotonic()
    except BaseException as error:state['error']=str(error);os.kill(pid,signal.SIGTERM);return
  handlers={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
  for s in handlers:signal.signal(s,interrupt)
  signal.setitimer(signal.ITIMER_REAL,CAP);thread=threading.Thread(target=monitor,daemon=True);thread.start();receipt=dict(schema='task1-contact-bounded-pipeline-receipt-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,Windows_saved_verified=False,new_actual4pad_CEM_RHS=0)
  def command(argv,label,seconds,extra_env=None):
   nonlocal child_debits
   guard();checkpoint(label);before=len(budget.load_ledger()['runs']);before_wall=time.monotonic();log=OUT/'logs'/(label+'.log');env=dict(os.environ,**(extra_env or{}))
   with log.open('xb')as stream:
    child=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,env=env);owned[child.pid]=b.ticks(child.pid);checkpoint(label,child_pid=child.pid,child_start_ticks=owned[child.pid],finite_child_seconds=seconds)
    try:code=child.wait(timeout=min(seconds,CAP-(time.monotonic()-start)))
    finally:
     if child.poll()is None:child.kill();child.wait(timeout=5)
     if '--package-id'in argv:
      package=argv[argv.index('--package-id')+1];run_arg=argv[argv.index('--run')+1];token=package+'-'+hashlib.sha256(run_arg.encode()).hexdigest()[:12];allowed={'task1-auto-transfer-'+token+'-m','task1-auto-transfer-'+token+'-t'}
     else:
      slug='contact-edge-surrogate'+('-fine'if label=='surrogate-selected-refinement'else'');allowed={'task1-'+slug+'-20261025-run','task1-git-'+slug+'-source-20261025','task1-git-'+slug+'-result-20261025'}
     recorded=sum(row.get('seconds',0.)for row in budget.load_ledger()['runs'][before:]if row.get('run_id')in allowed);child_debits+=min(time.monotonic()-before_wall,recorded)
   req(code==0,'Finite pipeline child failed; preserve '+label+' log and resume from recorded artifacts')
  def transfer(run,previous,previous_sha,tag):
   command([sys.executable,'-B',str(SRC/'finalize_transfer.py'),'--run',str(run),'--previous',str(previous),'--expected-previous-sha256',previous_sha,'--package-id',tag],tag+'-transfer',1050)
   identity=read(run/'auto-transfer/completed-transfer-identity.json');req(identity['Windows_backup_complete']is False,'Transport must not claim Windows receipt');manifest=run/'auto-transfer'/(tag+'-transfer-manifest.json');req(sha(manifest)==identity['manifest_SHA256'],'Actual merged transfer checksum');return manifest,identity
  try:
   # Both numerical owners use the same global three dual locks; launched sequentially.
   command([sys.executable,'-B',str(BASE/'href-owner-source/guardian.py')],'surrogate-coefficients',1650)
   coarse=Path('/dev/shm/task1-contact-edge-surrogate-20261025-run');summary=read(coarse/'summary.json');owner=read(coarse/'receipt.json');req('published'in owner['status']and'failed'not in owner['status'],'Actual coefficient benchmark published before next choice')
   axes=summary['edge_maximum_diagnostics']['axes'];rows=axes['panel_at_H4096']['rows'];old=rows[-2]['RMS_max_panel_A_m2'];current=rows[-1]['RMS_max_panel_A_m2'];growth=(current-old)/old;flags=summary['adjacent_diagnostics'];last_failure=any(not row['passed']for item in [flags[1],flags[3]]for row in item['rows']);selected=bool(last_failure or growth>.05)
   decision=dict(schema='task1-contact-next-finite-decision-v1',source_commit=owner['source_commit'],result_commit=owner['result_commit'],prior_summary_SHA256=sha(coarse/'summary.json'),last_panel_Jmax_relative_increase=growth,last_panel_or_harmonic_flags_failed=last_failure,predeclared_Jmax_growth_trigger=.05,selected_refinement=selected,next_unique_panel_harmonic_pairs=[[256,16384],[512,16384],[1024,4096],[1024,8192],[1024,16384]]if selected else[],reason='Resolve panel/harmonic truncation and native edge sensitivity; no fitted correction or actual4pad adoption',old_actual_failed_gates_preserved=True,Windows_saved_verified=False)
   new(coarse/'continuation-decision.json',decision);checkpoint('first_result_selected_next_condition',**decision)
   previous,identity=transfer(coarse,PREVIOUS,PREVIOUS_SHA,'contact-edge-surrogate-20261025');receipt.update(first_result_commit=owner['result_commit'],first_transfer_commit=identity['transfer_commit'],selected_refinement=selected)
   if selected:
    command([sys.executable,'-B',str(BASE/'href-fine-owner-source/guardian.py')],'surrogate-selected-refinement',1650,dict(TASK1_EXPECTED_TOPIC_PARENT=identity['transfer_commit'],TASK1_CONTACT_PRIOR_RUN=str(coarse)))
    fine=Path('/dev/shm/task1-contact-edge-surrogate-fine-20261025-run');fine_owner=read(fine/'receipt.json');fine_summary=read(fine/'summary.json');new(fine/'continuation-decision.json',dict(schema='task1-contact-next-review-checkpoint-v1',source_commit=fine_owner['source_commit'],result_commit=fine_owner['result_commit'],all_diagnostic_delta_flags_pass=fine_summary['all_diagnostic_flags_pass'],edge_continuum_Jmax_converged=False,selected_followup_question='Review finite edge-window integrals, mode/panel error and coefficient sensitivity before modifying actual4pad contact operators; all original actual-model failures retained',scope='This finite two-batch queue is not completion or validation of the research',Windows_saved_verified=False));previous,identity=transfer(fine,previous,identity['manifest_SHA256'],'contact-edge-surrogate-fine-20261025');receipt.update(second_result_commit=fine_owner['result_commit'],second_transfer_commit=identity['transfer_commit'])
   receipt['status']='finite_contact_pipeline_results_and_transfers_published_next_review_checkpoint';checkpoint(receipt['status'],**receipt)
  except BaseException as error:
   receipt.update(error_type=type(error).__name__,error=str(error),failed_phase=state['phase']);checkpoint('failed_preserved',**receipt);raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   for p,t in b.owned_descendants(pid,ticks,dict(owned)).items():
    if p!=pid and b.live(p,t):
     try:os.kill(p,signal.SIGKILL)
     except ProcessLookupError:pass
   elapsed=time.monotonic()-start;debit=max(0.,elapsed-child_debits)
   try:
    with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
     ledger=budget.load_ledger();ledger['spent_seconds']+=debit;ledger['runs'].append(dict(run_id=OUT.name,stage='finite_contact_pipeline_supervision_only',seconds=debit,status=receipt['status'],children_debited_separately=True));tmp=ROOT/'runtime'/('task1-budget-contact-pipeline-'+str(pid)+'.tmp');new(tmp,ledger);os.replace(tmp,ROOT/'runtime/task1-budget.json');receipt['ledger_debit_status']='recorded_under_queue_dual_lock'
   except BlockingIOError:
    new(OUT/'deferred-ledger-debit.json',dict(run_id=OUT.name,seconds=debit,reason='Another queue owner holds the dual lock; no concurrent ledger overwrite',requires_reconciliation_before_next_debit=True));receipt['ledger_debit_status']='deferred_preserved_other_queue_owner'
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')});new(OUT/'receipt.json',receipt)
   for s,h in handlers.items():signal.signal(s,h)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
