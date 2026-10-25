"""Finite source-published GUI build: pure MFG before native display extraction."""
import ast,ctypes,gc,hashlib,json,os,re,shutil,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
OWNER=Path('/workspace/ngg-tis-task1/runtime/E13-fine-drive-stream-owner-20261025/source')
SRC=Path('/workspace/ngg-tis-task1/runtime/E13-fine-drive-stream-20261025/source')
ADMISSION=OWNER/'root-admission.json'
OUT=Path('/dev/shm/task1-E13-fine-drive-stream-20261025-run')
PUB=Path('/workspace/ngg-tis-task1/runtime/git-verified-batchfetch-r3-20261025/source/git_publish_verified.py')
PUB_DELTA=Path('/workspace/ngg-tis-task1/runtime/git-verified-batchfetch-r3-20261025/source-delta.json')
PUB_CONTRACT=Path('/workspace/ngg-tis-task1/runtime/git-verified-batchfetch-r3-20261025/BATCHFETCH_CONTRACT.md')
PUB_DELTA_SHA='28b079ceee329413e6b1c9eab645e94cbd83cc80b8ca6ca05aca3af8f4bdd24f'
PUB_CONTRACT_SHA='47a19bfc3ce7be66a1bf66156b33e631a8c329786bacd09d4586b5034402594a'
LEDGER=ROOT/'runtime/task1-budget.json'
CAP=4200;NUMERIC_CAP=3000;PUB_CAP=330;MAX_FILE=80*1024**2
FIXED_CHILD_AS=1200000000
ORIGINAL_MODEL_CHILD_RSS=220000000
PREDICTED_CHILD_RSS=220000000
EXPECTED_OUTPUT_BYTES=35000000
EXPECTED_NEW_TMPFS_OUTPUT_BYTES=35000000
REMOTE='data-native/E13-fine-drive-stream-20261025/'
sys.path[:0]=[str(ROOT/'tools'),str(OWNER),str(SRC)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget
import resource_scope
from resource_checkpoint import resource_checkpoint
from temporary_accounting import counted_bytes as size
from owner_contracts import validate_summary,validate_MFG,validate_owner_admission,source_paths,test_methods,physical_forecast,publication_forecast

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
def task_temp_usage():
 parts={base:sum(size(p)for p in Path(base).glob('task1-*'))for base in('/dev/shm','/tmp')}
 return parts,parts['/dev/shm']+parts['/tmp']
def reclaim_parent_metadata(stage,pid,before_RSS):
 collected=gc.collect();after_GC=b.rss(pid);trim=dict(attempted=False,supported=False,result=None,error_type=None)
 try:
  function=getattr(ctypes.CDLL(None),'malloc_trim');function.argtypes=[ctypes.c_size_t];function.restype=ctypes.c_int
  trim.update(attempted=True,supported=True,result=int(function(0)))
 except(AttributeError,OSError)as error:trim['error_type']=type(error).__name__
 return dict(schema='task1-E13-fine-drive-stream-parent-metadata-release-v1',stage=stage,own_RSS_before_bytes=before_RSS,own_RSS_after_GC_bytes=after_GC,own_RSS_after_optional_trim_bytes=b.rss(pid),collected_objects=collected,own_heap_malloc_trim=trim,worker_reads_immutable_full_spec=True,full_metadata_pins_and_native_stat_guards_retained=True,metadata_preparation_count=1,scientific_objects_or_files_deleted=False,child_forecast_bytes=PREDICTED_CHILD_RSS,output_forecast_bytes=EXPECTED_OUTPUT_BYTES,new_TMPFS_output_forecast_bytes=EXPECTED_NEW_TMPFS_OUTPUT_BYTES,new_output_storage='owned_task_tmpfs',output_forecast_is_not_a_storage_quota=True,physical_cap_bytes=8000000000,forecast_is_revised_provisional_not_measured=True,original_model_informational_forecast_bytes=ORIGINAL_MODEL_CHILD_RSS,physical_or_scientific_cap_relaxed=False)
def source_inventory():
 paths={'model':source_paths(SRC),'owner':source_paths(OWNER)}
 req(all(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size<8*1024**2 for group in paths.values()for p in group),'All canonical bounded GUI source files')
 req((SRC/'drive_screen.py').is_file()and(SRC/'drive_inputs.py').is_file(),'Complete frozen streamed allocation model/input source')
 req(sha(OWNER/'resource_scope.py')=='6c09a7cd06fed12a2e9950cc921242ef12c2a4ae999e9645ae7953d732d7873e','Audited global research resource scope')
 all_sources={str(p):sha(p)for group in paths.values()for p in group};model_sources={str(p):sha(p)for p in paths['model']}
 return paths,all_sources,model_sources
def test_inventory():
 groups={}
 for namespace,root in(('model',SRC),('owner',OWNER)):
  methods={p.stem:test_methods(p)for p in sorted(root.glob('test_*.py'))};counts={name:len(rows)for name,rows in methods.items()}
  groups[namespace+'_counts']=counts;groups[namespace+'_methods']=methods;groups[namespace+'_total']=sum(counts.values())
 req(groups['model_total']>0 and groups['owner_total']>0,'Positive dynamic source-AST model and owner tests before native I/O')
 return dict(groups,total=groups['model_total']+groups['owner_total'],tests_before_any_native_byte_reads=True,no_external_test_result_assumed=True)
def main():
 head=os.environ.get('TASK1_E13_FINE_DRIVE_STREAM_EXPECTED_PARENT','')
 req(re.fullmatch('[0-9a-f]{40}',head)is not None,'Set TASK1_E13_FINE_DRIVE_STREAM_EXPECTED_PARENT to the actual public40hex branch parent')
 req(ADMISSION.is_file()and not ADMISSION.is_symlink(),'New actual-result-bound positive GUI-only admission and safe boundary required')
 with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
  req(not OUT.exists(),'Unique run required; preserve all earlier attempts');OUT.mkdir()
  for name in('logs','source-publication','result-publication','source'):(OUT/name).mkdir()
  limits=ep.resolve_limits();req(limits['cpu_limit']==4 and limits['total_memory_bytes']==8000000000 and limits['max_cells']==800000,'Unchanged CPU4/8e9 whole-taskRAM/800k policy');configured=ep.configure_process(limits);ledger=budget.load_ledger()
  req(ledger.get('cumulative_time_unlimited')is True,'Actual unlimited-time authorization required');budget.require_time_budget(ledger,CAP);del ledger
  pid=os.getpid();ticks=b.ticks(pid);start=time.monotonic();owned={pid:ticks};stop=threading.Event();mutex=threading.RLock();accounting_mutex=threading.RLock();accounting_state={}
  state=dict(phase='preparing',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);research_known={};counter=0;git_wall=0.
  req(sha(PUB)=='de256302c9cdec25def821541711fb4ba8945c4e47275843e820f53b5ac60805','Exact independently reviewed batchfetch publisher, CAP300 unchanged')
  req(sha(PUB_DELTA)==PUB_DELTA_SHA and sha(PUB_CONTRACT)==PUB_CONTRACT_SHA,'Exact independently reviewed publisher delta/contract evidence')
  packs,sources,model_sources=source_inventory()
  helpers={str(ROOT/'tools'/name):sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  admission=read(ADMISSION);prospective=test_inventory();model_count=prospective['model_total'];validate_owner_admission(admission,sources,model_sources,model_count,prospective['owner_total'])
  reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,
   controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),
   source_sha256=sources,helper_sha256=helpers,outer_deadline_seconds=CAP,numerical_child_deadline_seconds=NUMERIC_CAP,
   resource_limits=limits,task_temp_accounting_roots=['/dev/shm/task1-*','/tmp/task1-*'],temporary_accounting_scope='All owned task roots in BOTH tmpfs and auxiliary /tmp; no files moved/deleted to avoid accounting',execution_policy_refs=ep.execution_policy_refs(),configured=configured,
   new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,expected_directional_metric_evaluations=3,expected_new_metric_evaluations=2,source_fields_only=True,scenario='baseline_agreement_then_two_cached_E13fine_allocation_ratios')
  new(OUT/'registration.json',reg)
  receipt=dict(schema='task1-E13-fine-drive-stream-owner-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,
   new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,actual_directional_metric_evaluations=None,actual_new_metric_evaluations=None,GUI_generated=False,Windows_saved_verified=False,candidate_adopted=False)
  fast={};large={};native_stats={}
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
    counter+=1;item=dict(schema='task1-E13-fine-drive-stream-live-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,
     elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),item)
    for target in(OUT/'current.json',ROOT/'runtime/task1-E13-fine-drive-stream-live-20261025.json'):
     tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,item);os.replace(tmp,target)
    state['phase']=phase
  def observe_resources():
   with mutex:owned_now=dict(owned);known_now=dict(research_known)
   live=b.owned_descendants(pid,ticks,owned_now)
   observation=resource_scope.observe(live,b.ticks,known_now);rss=observation['research_RSS_bytes'];temp_parts,tmp=task_temp_usage()
   auxiliary=dict(total_bytes=tmp,by_namespace_bytes=temp_parts,namespaces=['/dev/shm/task1-*','/tmp/task1-*'])
   with mutex:
    owned.update(live);research_known.update(observation['members']);state['latest_process_audit']=observation
    state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp),peak_task_shm_bytes=max(state.get('peak_task_shm_bytes',0),temp_parts['/dev/shm']),peak_task_tmp_aux_bytes=max(state.get('peak_task_tmp_aux_bytes',0),temp_parts['/tmp']))
   return observation,auxiliary
  def account_resources(force=False):
   # One serialized global scan at a time. Safe completion starts the .25s
   # reuse window; forced boundaries rescan after all long hash/stat work.
   with accounting_mutex:
    resource_checkpoint(accounting_state,time.monotonic,start,CAP,observe_resources,limits['total_memory_bytes'],force)
    return accounting_state['processes'],accounting_state['auxiliary']
  def guard():
   account_resources()
   with mutex:fast_now=dict(fast);large_now=dict(large);current_native=dict(native_stats)
   req(time.monotonic()-start<CAP,'Finite4200s cached allocation owner watchdog');req(not(OUT/'STOP').exists(),'Explicit STOP marker')
   for path,expected in fast_now.items():req(sha(path)==expected,'Frozen small source/input/policy changed '+path)
   for path,(_,ident)in large_now.items():req(identity(path)==ident,'Large immutable metadata stat identity changed '+path)
   for path,ident in current_native.items():req(identity(path)==ident,'Native/document descriptor stat changed; byte reads remain post-MFG only '+path)
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
    account_resources(True) # Mandatory fresh accounting immediately before child/PUB start.
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
   account_resources(True) # Mandatory completed-child/stage boundary accounting.
   if not allow_failure:req(code==0,'Finite child failed '+label+'; preserve log '+str(log))
   return code
  def plan(files,parent,message,destination,comment=None):
   for path in files.values():req(path.is_file()and path==path.resolve()and not path.is_symlink()and path.stat().st_size<MAX_FILE,'Preserve file and report publication bound '+str(path))
   return dict(schema='task1-supported-Git-transport-plan-v1',repository='yoodohyun-codex-cloud/ngg-tis-task1',branch='codex/task1-cloud-restart-20261020',expected_parent=parent,message=message,
    files={target:dict(local_path=str(path),SHA256=sha(path),bytes=path.stat().st_size)for target,path in files.items()},required_result_receipt=str(destination),required_receipt_status='published_readback_verified',new_PDE_required=False,comment_body=comment)
  try:
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    import drive_screen as model
    new(OUT/'root-admission.json',admission)
    spec=model.make_spec(admission);refs=dict(spec['metadata_input_sha256'])
    req(spec['metadata_input_sha256']==refs and spec['source_sha256']==model_sources,'Only authenticated metadata/canonical model pins before MFG')
    req(spec['ratio_multipliers']==[.8,1.25]and spec['baseline_multiplier']==1.,'One unchanged baseline QA before two fixed relative allocations')
    req(spec['cells']==793848<=limits['max_cells']==800000 and spec['physical_pads']==4 and spec['independent_outputs']==2 and spec['frequencies_Hz']==[2000,2010],'Exact original fine97 physical model below800k')
    req(spec['per_condition_seconds']==900 and spec['total_numeric_seconds']==3000 and spec['chunk_rows']==128 and spec['direction_block']==2074 and spec.get('lazy_weights_required')is True,'Actual bounded stream/memory plan and finite conditions match source')
    descriptors=spec['native_input_descriptors']
    req(type(descriptors)is list and len(descriptors)>0 and len({d['path']for d in descriptors})==len(descriptors),'Only explicit saved-native inputs, no old failure or field copies')
    for path in refs:req(Path(path).suffix.lower()in('.json','.md','.txt','.log','.py'),'No native data files in pre-MFG metadata pin set')
    for descriptor in descriptors:
     path=descriptor['path'];req(type(descriptor.get('bytes'))is int and descriptor['bytes']>=0 and re.fullmatch('[0-9a-f]{64}',descriptor['SHA256']),'Declared native descriptor full identity')
     stat=identity(path);req(stat[2]==descriptor['bytes'],'Declared native byte size before source admission, no content read');native_stats[path]=stat
    tests=prospective;new(OUT/'test-source-inventory.json',tests);new(OUT/'spec.json',spec);frozen={}
    for namespace,paths in packs.items():
     directory=OUT/'source'/namespace;directory.mkdir()
     for path in paths:
      target=directory/path.name
      with target.open('xb')as stream:stream.write(path.read_bytes())
      req(sha(target)==sources[str(path)],'Exact canonical-to-published GUI snapshot');frozen[str(target)]=sha(target)
    for p in(PUB,PUB_DELTA,PUB_CONTRACT):req(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size<1024**2,'Bounded approved publisher source/proof');refs[str(p)]=sha(p)
    refs.update({str(ADMISSION):sha(ADMISSION),str(OUT/'root-admission.json'):sha(OUT/'root-admission.json')})
    new(OUT/'native-descriptor-stat-registration.json',dict(schema='task1-E13-fine-drive-stream-pre-MFG-native-stats-v1',files={p:list(v)for p,v in native_stats.items()},native_bytes_opened=False))
    new(OUT/'preregistration.json',dict(schema='task1-E13-fine-drive-stream-preregistration-v1',question='Mandatory saved E13fine baseline1.0 agreement QA, then relative multipliers0.8 and1.25, zero new PDE/Q/eigen/field reconstruction; keep original comparisons and holds. No duplicate baseline map archive.',source_sha256=sources,model_source_sha256=model_sources,frozen_source_sha256=frozen,metadata_input_sha256=refs,native_input_descriptors=descriptors,native_descriptor_stats_SHA256=sha(OUT/'native-descriptor-stat-registration.json'),helper_sha256=helpers,execution_policy_refs=reg['execution_policy_refs'],limits=limits,spec_SHA256=sha(OUT/'spec.json'),root_admission_SHA256=sha(OUT/'root-admission.json'),root_decision=admission,expected_synthetic_tests=tests['total'],expected_model_tests=model_count,expected_owner_tests=tests['owner_total'],test_inventory_SHA256=sha(OUT/'test-source-inventory.json'),tests_before_any_native_byte_reads=True,baseline_multiplier=1.,ratio_multipliers=[.8,1.25],expected_conditions=3,expected_baseline_verification_conditions=1,baseline_QA_scope='3_saved_float_maps_plus_winner_diagnostics_and_all8_summary_ROI_electrical',unsaved_float_maps_pointwise_unavailable=5,expected_new_metric_evaluations=2,maximum_new_PDE_RHS=0,maximum_new_Q_loads=0,maximum_new_eigen_solves=0,duplicate_baseline_arrays=0,hard_child_seconds=NUMERIC_CAP,per_condition_seconds=900,child_lease_audit_policy=dict(completion_reuse_strictly_less_than_seconds=.25,quick_deadline_STOP_parent_PID_startticks_every_request=True,full_audit_forced_at_MFG_native_and_each_condition_boundaries=True,failures_and_backward_clock_poison=True,entry_exit_full_source_and_native_SHA_uncached=True),resource_accounting_policy=dict(completed_safe_observation_reuse_seconds=.25,serialized_scans=True,failed_scan_cache_reuse=False,forced_fresh_before_NUM_PUB_child_and_stage_boundaries=True),resource_forecast=dict(fixed_child_RLIMIT_AS_bytes=FIXED_CHILD_AS,predicted_child_RSS_bytes=PREDICTED_CHILD_RSS,expected_output_bytes=EXPECTED_OUTPUT_BYTES,new_owned_tmpfs_output_forecast_bytes=EXPECTED_NEW_TMPFS_OUTPUT_BYTES,actual_output_storage='owned_task_tmpfs',publisher_RSS_forecast_bytes=160000000,publication_output_copy_multiplier=3,forecasts_not_measured=True,actual_total_research_RSS_plus_all_task_tmpfs_cap_bytes=8000000000),candidate_adopted=False))
    bind({**sources,**frozen,**refs,**helpers,**reg['execution_policy_refs'],**{str(OUT/name):sha(OUT/name)for name in('spec.json','test-source-inventory.json','preregistration.json','native-descriptor-stat-registration.json')}})
   files={}
   for path in(OUT/'source').rglob('*'):
    if path.is_file():files['tools/E13_fine_drive_stream_20261025/'+path.relative_to(OUT/'source').as_posix()]=path
   for name in('registration.json','preregistration.json','test-source-inventory.json','spec.json','root-admission.json','native-descriptor-stat-registration.json'):files[REMOTE+name]=OUT/name
   for name,path in(('git_publish_verified.py',PUB),('source-delta.json',PUB_DELTA),('BATCHFETCH_CONTRACT.md',PUB_CONTRACT)):files['tools/verified_Git_batchfetch_r3_20261025/'+name]=path
   # The complete worker spec, preregistration and all hashes are immutable on
   # disk. No later parent phase needs these large metadata object graphs.
   before_release_RSS=b.rss(pid)
   del spec,refs,frozen,packs,admission,reg,configured,prospective,descriptors
   descriptor=path=paths=directory=target=d=None
   release=reclaim_parent_metadata('before_source_publication',pid,before_release_RSS)
   new(OUT/'parent-prepublication-metadata-release.json',release);bind({str(OUT/'parent-prepublication-metadata-release.json'):sha(OUT/'parent-prepublication-metadata-release.json')})
   files[REMOTE+'parent-prepublication-metadata-release.json']=OUT/'parent-prepublication-metadata-release.json'
   spath=OUT/'source-plan.json';new(spath,plan(files,head,'Preregister cached E13fine baseline QA and relative allocations0.8/1.25; source-bound MFG before native stream',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(spath),'--output','/dev/shm/task1-git-E13-fine-drive-stream-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',PUB_CAP,True)
   published=read(OUT/'source-publication/result-publication.json');req(published['status']=='published_readback_verified','Actual immutable source/input readback before bounded manufactured tests and stored-native array reads')
   source_commit=published['commit'];del published,files;published={'commit':source_commit};before_release_RSS=b.rss(pid);release=None
   new(OUT/'parent-postpublication-metadata-release.json',reclaim_parent_metadata('before_fresh_numeric_admission',pid,before_release_RSS));bind({str(OUT/'parent-postpublication-metadata-release.json'):sha(OUT/'parent-postpublication-metadata-release.json')})
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    checkpoint('numeric-admission',source_commit=published['commit'],manufactured_tests_started=False,native_bytes_started=False)
    guard();observation,auxiliary=account_resources(True)
    temp_parts=auxiliary['by_namespace_bytes'];tmp=auxiliary['total_bytes']
    num_forecast=physical_forecast(tmp,observation['research_RSS_bytes'],PREDICTED_CHILD_RSS,EXPECTED_NEW_TMPFS_OUTPUT_BYTES)
    pub_forecast=publication_forecast(tmp,observation['research_RSS_bytes'],EXPECTED_OUTPUT_BYTES)
    new(OUT/'numeric-admission.json',dict(admitted=num_forecast<=8000000000 and pub_forecast<=8000000000,physical_forecast_bytes=num_forecast,publication_peak_forecast_bytes=pub_forecast,publication_forecast_fit=pub_forecast<=8000000000,forecast_base_phase='pre_NUM_before_baseline_and_new_ratio_maps',publication_forecast_uses_same_pre_NUM_base=True,publication_after_NUM_uses_fresh_actual_guard_without_readding_forecast=True,task_temp_accounting_roots=['/dev/shm/task1-*','/tmp/task1-*'],task_shm_bytes=temp_parts['/dev/shm'],task_tmp_aux_bytes=temp_parts['/tmp'],task_temp_accounted_bytes=tmp,all_research_RSS_bytes=observation['research_RSS_bytes'],research_scope=observation['scope'],forecast_child_RSS_bytes=PREDICTED_CHILD_RSS,forecast_new_output_bytes=EXPECTED_OUTPUT_BYTES,forecast_new_owned_tmpfs_output_bytes=EXPECTED_NEW_TMPFS_OUTPUT_BYTES,output_storage='owned_task_tmpfs',physical_cap_bytes=8000000000,child_RLIMIT_AS_bytes=FIXED_CHILD_AS,forecast_not_measured=True,storage_capacity_guard_enabled=False))
    req(num_forecast<=8000000000 and pub_forecast<=8000000000 and limits['cpu_limit']==4 and limits['max_cells']==800000,'Both provisional finite NUM and complete PUB paths must fit unchanged actual8GB cap; no reduced scope/retry')
    bind({str(OUT/'numeric-admission.json'):sha(OUT/'numeric-admission.json')})
    code=command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(OUT/'source/owner/worker.py'),'--output',str(OUT),'--source',str(SRC),'--as-limit',str(FIXED_CHILD_AS),
     '--registration-sha',sha(OUT/'registration.json'),'--preregistration-sha',sha(OUT/'preregistration.json'),'--publication-sha',sha(OUT/'source-publication/result-publication.json'),'--publication-plan-sha',sha(spath)],'E13-fine-drive-stream-child',NUMERIC_CAP,allow_failure=True)
   summary=read(OUT/'summary.json')if(OUT/'summary.json').is_file()else None;passed=False
   if code==0 and summary is not None:
    mfg=read(OUT/'synthetic-test-receipt.json');req(mfg['source_publication_commit']==published['commit']and mfg['owner_source_sha256']==sources,'Actual source-bound MFG result before parent marks GUI build complete')
    expected_events=[module+'.'+method for namespace in('model','owner')for module,methods in tests[namespace+'_methods'].items()for method in methods]
    mfg_accounting=validate_MFG(mfg,model_sources,model_count,tests['owner_total'],expected_events);accounting=validate_summary(summary);accounting['manufactured_tests']=mfg_accounting;passed=True
   else:accounting=dict(passed=False,worker_exit_code=code,summary_present=summary is not None,partial_results_preserved=True,actual_hardware_wiring_changed=False)
   with mutex:all_pins={**fast,**{path:value[0]for path,value in large.items()}}
   for path,expected in all_pins.items():guard();req(sha(path)==expected,'Complete source/input/policy SHA after native scalar/probe postprocessing')
   new(OUT/'research-process-accounting.json',state.get('latest_process_audit',{}))
   with accounting_mutex:accounting_audit=dict(accounting_state)
   new(OUT/'resource-checkpoint-audit.json',accounting_audit)
   new(OUT/'execution-stage.json',dict(status='E13_fine_drive_stream_computed'if passed else'E13_fine_drive_stream_failed_or_partial_preserved',worker_exit_code=code,accounting=accounting,actual_new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,actual_directional_metric_evaluations=summary.get('actual_directional_metric_evaluations')if passed else None,actual_new_metric_evaluations=summary.get('actual_new_metric_evaluations')if passed else None,actual_hardware_wiring_changed=False,source_commit=published['commit']))
   files={}
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and(rel.parts[0]in('logs','conditions','candidates','proofs','maps')or(len(rel.parts)==1 and path.name not in('current.json','source-plan.json','result-plan.json'))):files[REMOTE+rel.as_posix()]=path
   files[REMOTE+'source-publication-receipt.json']=OUT/'source-publication/result-publication.json'
   missing=[name for name in('synthetic-test-receipt.json','worker-receipt.json','summary.json','drive-stream-result.json','baseline-agreement-proof.json')if not(OUT/name).is_file()]
   new(OUT/'missing-output-inventory.json',dict(status='actual_outputs_and_absences_preserved',missing=missing,no_browser_result_inferred=True))
   files[REMOTE+'missing-output-inventory.json']=OUT/'missing-output-inventory.json'
   rp=OUT/'result-plan.json';new(rp,plan(files,published['commit'],'Preserve streamed saved-native E13fine allocation QA/two ratios or exact partial failure, unadopted',OUT/'result-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(rp),'--output','/dev/shm/task1-git-E13-fine-drive-stream-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',PUB_CAP,True)
   result=read(OUT/'result-publication/result-publication.json');req(result['status']=='published_readback_verified','Full result/error publication readback')
   receipt.update(status='E13_fine_drive_stream_computed_published_unadopted'if passed else'E13_fine_drive_stream_failed_or_partial_published',source_commit=published['commit'],result_commit=result['commit'],postprocess_accounting=accounting,actual_directional_metric_evaluations=summary.get('actual_directional_metric_evaluations')if passed else None,actual_new_metric_evaluations=summary.get('actual_new_metric_evaluations')if passed else None,GUI_generated=False,browser_validation_performed=False)
   checkpoint('E13_fine_drive_stream_review_next_finite_step',result_commit=result['commit'],calculation_passed=passed)
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
   ledger['runs'].append(dict(run_id=OUT.name,stage='E13_fine_drive_stream_manufactured_tests_and_cached_metrics',seconds=debit,status=receipt['status'],Git_children_debited_separately=True))
   temp=LEDGER.with_name('task1-budget-E13-fine-drive-stream-'+str(pid)+'.tmp');new(temp,ledger);os.replace(temp,LEDGER)
   cache_locked=accounting_mutex.acquire(timeout=2)
   if cache_locked:
    try:cache_summary={k:v for k,v in accounting_state.items()if k not in('processes','auxiliary')}
    finally:accounting_mutex.release()
   else:cache_summary=dict(status='cache_summary_unavailable_scan_in_progress',fresh_resource_observation_inferred=False,cleanup_audit_acquire_timeout_seconds=2)
   final_state=dict(state)
   receipt.update(resource_checkpoint_summary=cache_summary,finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in final_state.items()if k.startswith('peak_')},remaining_approved_seconds=budget.remaining_seconds(ledger));new(OUT/'receipt.json',receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
