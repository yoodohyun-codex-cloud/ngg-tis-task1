"""Finite source-published manufactured gates followed by one ellipse screen."""
import ast,hashlib,json,os,re,shutil,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
OWNER=Path('/dev/shm/task1-centroid-ellipse-owner-20261025/source')
SRC=Path('/dev/shm/task1-centroid-ellipse-20261025/source')
ADMISSION=SRC/'root-admission.json'
OUT=Path('/dev/shm/task1-centroid-ellipse-20261025-run')
PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
LEDGER=ROOT/'runtime/task1-budget.json'
CAP=2400;NUMERIC_CAP=1200;PUB_CAP=330;MAX_FILE=80*1024**2
FIXED_CHILD_AS=1600000000
PREDICTED_CHILD_RSS=750000000
EXPECTED_OUTPUT_BYTES=150000000
REMOTE='data-native/centroid-ellipse-20261025/'
sys.path[:0]=[str(ROOT/'tools'),str(OWNER),str(SRC)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget
import resource_scope
from owner_contracts import validate_summary,validate_MFG

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
 paths={'model':[p for p in sorted(SRC.iterdir())if p.is_file()and p.suffix in('.py','.json','.md')],
  'owner':[p for p in sorted(OWNER.iterdir())if p.is_file()and p.suffix in('.py','.json','.md')]}
 req(all(p.is_file()and not p.is_symlink()for group in paths.values()for p in group),'All canonical byte-pinned source files')
 return paths,{str(p):sha(p)for group in paths.values()for p in group}
def test_inventory():
 groups={}
 for namespace,root in(('model',SRC),('owner',OWNER)):
  rows={}
  for path in sorted(root.glob('test_*.py')):
   tree=ast.parse(path.read_text(),filename=str(path));rows[path.name]=sum(1 for cls in tree.body if isinstance(cls,ast.ClassDef)for item in cls.body if isinstance(item,ast.FunctionDef)and item.name.startswith('test_'))
  groups[namespace+'_counts']=rows;groups[namespace+'_total']=sum(rows.values())
 req(groups['model_total']>0 and groups['owner_total']>0,'Prospective dynamic model and owner test inventory')
 return dict(groups,total=groups['model_total']+groups['owner_total'],tests_before_any_new_RHS=True,no_external_test_result_assumed=True)
def forecast_evidence():
 evidence_path=OWNER/'resource-forecast-evidence.json';e=read(evidence_path);descriptor=e['publication_receipt'];pubpath=Path(descriptor['path'])
 req(pubpath.is_file()and not pubpath.is_symlink()and pubpath==pubpath.resolve()and pubpath.stat().st_size==descriptor['bytes']and sha(pubpath)==descriptor['SHA256'],'Actual prior public resource receipt exact SHA/bytes')
 pub=read(pubpath);req(pub['status']=='published_readback_verified'and pub['commit']==e['original_public_result_commit']=='f36791a49e85148ca31c444ac8a8e20b87d9698f','Prior actual same-coarseQ two-carrier worker publication')
 worker=e['worker_receipt'];path=Path(worker['path']);proof=pub['files'][worker['publication_target']]
 req(path.is_file()and not path.is_symlink()and path==path.resolve()and path.stat().st_size==worker['bytes']and sha(path)==worker['SHA256']and proof['readback_passed']is True and proof['SHA256']==worker['SHA256']and proof['bytes']==worker['bytes'],'Published actual prior child RSS record')
 row=read(path);req(row['status']=='hypothetical_floating_P23_computed'and row['peak_worker_RSS_bytes']==e['actual_prior_worker_peak_RSS_bytes']==703627264,'Measured prior child RSS, not a new ellipse measurement')
 for target,old in e['published_prior_raw_scalar_file_proofs'].items():
  actual=pub['files'][target];req(actual==old and actual['readback_passed']is True,'Actual prior raw/scalar sizes from full public readback')
 req(e['candidate_child_RSS_forecast_bytes']==PREDICTED_CHILD_RSS and e['candidate_new_output_forecast_bytes']==EXPECTED_OUTPUT_BYTES,'Frozen evidence-derived forecasts agree with controller')
 return e,{str(evidence_path):sha(evidence_path),str(pubpath):descriptor['SHA256'],str(path):worker['SHA256']}
def main():
 head=os.environ.get('TASK1_CENTROID_ELLIPSE_EXPECTED_PARENT','')
 req(re.fullmatch('[0-9a-f]{40}',head)is not None,'Set TASK1_CENTROID_ELLIPSE_EXPECTED_PARENT to the actual public40hex branch parent')
 req(ADMISSION.is_file()and not ADMISSION.is_symlink(),'New positive actual-fine-publication-bound ellipse admission required')
 with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
  req(not OUT.exists(),'Unique run required; preserve all earlier attempts');OUT.mkdir()
  for name in('logs','source-publication','result-publication','source'):(OUT/name).mkdir()
  limits=ep.resolve_limits();configured=ep.configure_process(limits);ledger=budget.load_ledger()
  req(ledger.get('cumulative_time_unlimited')is True,'Actual unlimited-time authorization required');budget.require_time_budget(ledger,CAP)
  pid=os.getpid();ticks=b.ticks(pid);start=time.monotonic();owned={pid:ticks};stop=threading.Event();mutex=threading.RLock()
  state=dict(phase='preparing',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);research_known={};counter=0;git_wall=0.
  packs,sources=source_inventory()
  helpers={str(ROOT/'tools'/name):sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,
   controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),
   source_sha256=sources,helper_sha256=helpers,outer_deadline_seconds=CAP,numerical_child_deadline_seconds=NUMERIC_CAP,
   resource_limits=limits,execution_policy_refs=ep.execution_policy_refs(),configured=configured,
   maximum_new_driven_RHS=2,full_angular_metric_evaluations=1,immutable_control_aliases=2,control_field_or_angular_repeat=0,new_eigen_solves=0,scenario='one_centroid_area_matched_tangent_ellipse_common_return')
  new(OUT/'registration.json',reg)
  receipt=dict(schema='task1-centroid-ellipse-owner-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,
   maximum_new_driven_RHS=2,controls_recomputed=False,GUI_generated=False,Windows_saved_verified=False,candidate_adopted=False)
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
    counter+=1;item=dict(schema='task1-centroid-ellipse-live-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,
     elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),item)
    for target in(OUT/'current.json',ROOT/'runtime/task1-centroid-ellipse-live-20261025.json'):
     tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,item);os.replace(tmp,target)
    state['phase']=phase
  def guard():
   with mutex:
    live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);fast_now=dict(fast);large_now=dict(large);known_now=dict(research_known)
   observation=resource_scope.observe(live,b.ticks,known_now);rss=observation['research_RSS_bytes'];tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
   with mutex:research_known.update(observation['members']);state['latest_process_audit']=observation
   with mutex:state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp))
   req(rss+tmp<=limits['total_memory_bytes'],'Actual ALL research-owned-family RSS plus ALL task1-ownedtmpfs cap')
   req(time.monotonic()-start<CAP,'Finite2400s conditional ellipse owner watchdog');req(not(OUT/'STOP').exists(),'Explicit STOP marker')
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
    except subprocess.TimeoutExpired:
     if not allow_failure:raise
     try:os.killpg(child.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     child.wait(timeout=5);code=124;new(OUT/(label+'-timeout.json'),dict(status='finite_child_timeout_partial_preserved',child_pid=child.pid,seconds=seconds,no_automatic_recalculation=True))
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
    import ellipse_screen as model
    admission=read(ADMISSION);new(OUT/'root-admission.json',admission)
    spec=model.make_spec(admission);refs=model.required_inputs(admission);history,history_refs=forecast_evidence();refs.update(history_refs);refs[str(ADMISSION)]=sha(ADMISSION);refs[str(OUT/'root-admission.json')]=sha(OUT/'root-admission.json')
    req(spec['inputs']['catalog']['grid']['cells']<=limits['max_cells']==800000 and spec['expected_new_driven_RHS']==2 and spec['expected_new_angular_metric_evaluations']==1 and spec['expected_immutable_control_aliases']==2,'Exact physical evaluation and two new RHS/one metric/two immutable alias caps')
    tests=test_inventory();new(OUT/'test-source-inventory.json',tests);new(OUT/'spec.json',spec);frozen={}
    for namespace,paths in packs.items():
     directory=OUT/'source'/namespace;directory.mkdir()
     for path in paths:
      target=directory/path.name
      with target.open('xb')as stream:stream.write(path.read_bytes())
      req(sha(target)==sources[str(path)],'Exact canonical-to-published snapshot');frozen[str(target)]=sha(target)
    small=OUT/'source-inputs';small.mkdir()
    context=spec['inputs']
    for oldpath in(context['P23_mask']['path'],context['P23_mask_receipt']['path'],context['controls']['B0']['mask']['path'],context['material']['path'],context['contact']['path']):
     target=small/Path(oldpath).name
     with target.open('xb')as stream:stream.write(Path(oldpath).read_bytes())
     req(sha(target)==refs[oldpath],'Exact approved mask/material/contact snapshot');refs[str(target)]=sha(target)
    new(OUT/'preregistration.json',dict(schema='task1-centroid-ellipse-preregistration-v1',question='One equal225mm2 tangential ellipse at each authenticated P23 centroid, fixedD50/layers/top4pads/2outputs/commonGND/50ohm,2000-output0+2010-output1. Exact source-bound manufactured tests after source readback must pass before2newRHS; cached B0/P23 are full aliases with zero field/angular repeats. Analytic body/quadrant/area/centroid/complete-positive-contact gates precede PDE; no repair/fallback. Old fractional-contact/edge/13-of14 failures held; one layout is not convergence/adoption.',source_sha256=sources,frozen_source_sha256=frozen,input_sha256=refs,helper_sha256=helpers,execution_policy_refs=reg['execution_policy_refs'],limits=limits,spec_SHA256=sha(OUT/'spec.json'),root_admission_SHA256=sha(OUT/'root-admission.json'),root_decision=admission,expected_synthetic_tests=tests['total'],expected_model_tests=tests['model_total'],expected_owner_tests=tests['owner_total'],test_inventory_SHA256=sha(OUT/'test-source-inventory.json'),tests_before_any_new_RHS=True,maximum_new_driven_RHS=2,expected_full_angular_evaluations=1,expected_immutable_control_aliases=2,control_field_or_angular_repeat=0,hard_child_seconds=NUMERIC_CAP,resource_forecast=dict(fixed_child_RLIMIT_AS_bytes=FIXED_CHILD_AS,virtual_AS_justification='Same retained7860realQ coarse model; finite1.6GB virtual limit is not RAM allocation. Evidence-derived provisional750Mchild+150Moutput forecast and actual8e9researchRSS+alltmpfs guard remain unchanged.',predicted_child_RSS_bytes=PREDICTED_CHILD_RSS,expected_output_bytes=EXPECTED_OUTPUT_BYTES,provisional_forecast_not_ellipse_measurement=True,evidence=history,actual_total_research_RSS_plus_all_task_tmpfs_cap_bytes=8000000000),actual_hardware_wiring_changed=False,candidate_adopted=False))
    bind({**sources,**frozen,**refs,**helpers,**reg['execution_policy_refs'],**{str(OUT/name):sha(OUT/name)for name in('spec.json','test-source-inventory.json','preregistration.json')}})
   files={}
   for path in(OUT/'source').rglob('*'):
    if path.is_file():files['tools/centroid_ellipse_20261025/'+path.relative_to(OUT/'source').as_posix()]=path
   for name in('registration.json','preregistration.json','test-source-inventory.json','spec.json','root-admission.json'):files[REMOTE+name]=OUT/name
   for path in(OUT/'source-inputs').iterdir():files[REMOTE+'source-inputs/'+path.name]=path
   spath=OUT/'source-plan.json';new(spath,plan(files,head,'Preregister source-bound manufactured gates and conditional centroid ellipse two-carrier screen',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(spath),'--output','/dev/shm/task1-git-centroid-ellipse-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',PUB_CAP,True)
   published=read(OUT/'source-publication/result-publication.json');req(published['status']=='published_readback_verified','Actual immutable source/input readback before all manufactured tests and at most2 ellipse PDE RHS')
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    guard();tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
    with mutex:authenticated_now=dict(owned);known_now=dict(research_known)
    observation=resource_scope.observe(authenticated_now,b.ticks,known_now)
    with mutex:research_known.update(observation['members']);state['latest_process_audit']=observation
    physical_forecast=tmp+observation['research_RSS_bytes']+PREDICTED_CHILD_RSS+EXPECTED_OUTPUT_BYTES
    req(physical_forecast<=limits['total_memory_bytes']==8000000000 and limits['cpu_limit']==4 and limits['max_cells']==800000,'Unchanged actual researchRSS+alltmpfs budget before ellipse manufactured tests and field work')
    new(OUT/'numeric-admission.json',dict(kind='manufactured_gates_then_one_conditional_ellipse_two_RHS',all_owned_tmpfs_bytes=tmp,all_research_RSS_bytes=observation['research_RSS_bytes'],research_scope=observation['scope'],forecast_child_RSS_bytes=PREDICTED_CHILD_RSS,forecast_new_output_bytes=EXPECTED_OUTPUT_BYTES,physical_forecast_bytes=physical_forecast,physical_cap_bytes=limits['total_memory_bytes'],child_RLIMIT_AS_bytes=FIXED_CHILD_AS,actual_hardware_wiring_changed=False))
    bind({str(OUT/'numeric-admission.json'):sha(OUT/'numeric-admission.json')})
    code=command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(OUT/'source/owner/worker.py'),'--output',str(OUT),'--source',str(SRC),'--as-limit',str(FIXED_CHILD_AS),
     '--registration-sha',sha(OUT/'registration.json'),'--preregistration-sha',sha(OUT/'preregistration.json'),'--publication-sha',sha(OUT/'source-publication/result-publication.json'),'--publication-plan-sha',sha(spath)],'centroid-ellipse-two-RHS-child',NUMERIC_CAP,allow_failure=True)
   summary=read(OUT/'summary.json')if(OUT/'summary.json').is_file()else None;passed=False
   if code==0 and summary is not None:accounting=validate_summary(summary);passed=True
   else:accounting=dict(passed=False,worker_exit_code=code,summary_present=summary is not None,partial_results_preserved=True,actual_hardware_wiring_changed=False)
   with mutex:all_pins={**fast,**{path:value[0]for path,value in large.items()}}
   for path,expected in all_pins.items():guard();req(sha(path)==expected,'Complete source/input/policy SHA after conditional ellipse work')
   new(OUT/'research-process-accounting.json',state.get('latest_process_audit',{}))
   new(OUT/'execution-stage.json',dict(status='centroid_ellipse_computed'if passed else'centroid_ellipse_failed_or_partial_preserved',worker_exit_code=code,accounting=accounting,maximum_new_RHS=2,actual_hardware_wiring_changed=False,source_commit=published['commit']))
   files={}
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and(rel.parts[0]in('logs','rhs','candidates','prepared','source-inputs')or(len(rel.parts)==1 and path.name not in('current.json','source-plan.json','result-plan.json'))):files[REMOTE+rel.as_posix()]=path
   files[REMOTE+'source-publication-receipt.json']=OUT/'source-publication/result-publication.json'
   rp=OUT/'result-plan.json';new(rp,plan(files,published['commit'],'Preserve finite centroid-ellipse geometry/MFG gates and two-carrier results or failures',OUT/'result-publication/result-publication.json',
    comment='고정 지름50mm/층0.1·5·5·15mm/윗면4패드/2출력/공통귀환/출력별50Ω을 유지한 단일 타원배치 가설입니다. 실제 공개 P23 패드 중심과225mm2 면적을 유지하고 장축13mm를 접선 방향으로 놓으며, 실제 fineXY 결과 공개·검토 후 새 승인으로만 진행합니다. 소스 공개·재읽기 후 제조기하/MMS 테스트가 모두 통과해야2000/2010Hz 새 RHS2개를 계산합니다. 기존B0/P23는 전체 결과 별칭이며 재계산·각도재평가하지 않습니다. 면적·중심·팬텀·완전양수 접촉 인증 실패시 보정·대체 없이 중단합니다. 부분접촉/가장자리/기존13/14 실패를 유지하며 수렴·실험·안전·활성화·채택을 주장하지 않습니다. 실제상태:'+('computed_unadopted'if passed else'failed_or_partial_preserved')))
   command([sys.executable,'-B',str(PUB),'--plan',str(rp),'--output','/dev/shm/task1-git-centroid-ellipse-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',PUB_CAP,True)
   result=read(OUT/'result-publication/result-publication.json');req(result['status']=='published_readback_verified','Full result/error publication readback')
   receipt.update(status='centroid_ellipse_two_RHS_computed_published'if passed else'centroid_ellipse_failed_or_partial_published',source_commit=published['commit'],result_commit=result['commit'],field_accounting=accounting)
   checkpoint('centroid_ellipse_result_review_next_finite_batch',result_commit=result['commit'],calculation_passed=passed)
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
   ledger['runs'].append(dict(run_id=OUT.name,stage='centroid_ellipse_two_RHS_and_supervision',seconds=debit,status=receipt['status'],Git_children_debited_separately=True))
   temp=LEDGER.with_name('task1-budget-centroid-ellipse-'+str(pid)+'.tmp');new(temp,ledger);os.replace(temp,LEDGER)
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')},remaining_approved_seconds=budget.remaining_seconds(ledger));new(OUT/'receipt.json',receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
