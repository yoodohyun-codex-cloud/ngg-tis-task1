"""Finite source-published GUI build: pure MFG before native display extraction."""
import ast,ctypes,gc,hashlib,json,os,re,shutil,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
OWNER=Path('/workspace/ngg-tis-task1/runtime/native-GUI-lite-r5-owner-20261025/source')
SRC=Path('/dev/shm/task1-native-GUI-lite-20261025/source')
ADMISSION=OWNER/'root-admission.json'
OUT=Path('/workspace/ngg-tis-task1/runtime/native-GUI-lite-r5-20261025-run')
PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
LEDGER=ROOT/'runtime/task1-budget.json'
CAP=2400;NUMERIC_CAP=1200;PUB_CAP=330;MAX_FILE=80*1024**2
FIXED_CHILD_AS=1200000000
ORIGINAL_MODEL_CHILD_RSS=340000000
PREDICTED_CHILD_RSS=300000000
EXPECTED_OUTPUT_BYTES=12000000
EXPECTED_NEW_TMPFS_OUTPUT_BYTES=0
REMOTE='data-native/native-GUI-lite-r5-20261025/'
sys.path[:0]=[str(ROOT/'tools'),str(OWNER),str(SRC)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget
import resource_scope
from recovery_history import verify_history
from recovery_R2_history import verify_history as verify_R2_history
from recovery_R3_history import verify_history as verify_R3_history
from recovery_R4_history import verify_history as verify_R4_history
from temporary_accounting import counted_bytes as size
from owner_contracts import validate_summary,validate_MFG,validate_admission,source_paths,test_methods,FROZEN_MODEL_SHA

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
 return dict(schema='task1-GUI-lite-parent-metadata-release-v1',stage=stage,own_RSS_before_bytes=before_RSS,own_RSS_after_GC_bytes=after_GC,own_RSS_after_optional_trim_bytes=b.rss(pid),collected_objects=collected,own_heap_malloc_trim=trim,worker_reads_immutable_full_spec=True,full_metadata_pins_and_native_stat_guards_retained=True,metadata_preparation_count=1,scientific_objects_or_files_deleted=False,child_forecast_bytes=PREDICTED_CHILD_RSS,output_forecast_bytes=EXPECTED_OUTPUT_BYTES,new_TMPFS_output_forecast_bytes=EXPECTED_NEW_TMPFS_OUTPUT_BYTES,new_output_storage='existing_workspace_disk',physical_cap_bytes=8000000000,forecast_is_revised_provisional_not_measured=True,original_model_informational_forecast_bytes=ORIGINAL_MODEL_CHILD_RSS,physical_or_scientific_cap_relaxed=False)
def source_inventory():
 paths={'model':source_paths(SRC),'owner':source_paths(OWNER)}
 req(all(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size<8*1024**2 for group in paths.values()for p in group),'All canonical bounded GUI source files')
 for name,expected in FROZEN_MODEL_SHA.items():req(sha(SRC/name)==expected,'Frozen original GUI model/test unchanged '+name)
 req(sha(OWNER/'resource_scope.py')=='6c09a7cd06fed12a2e9950cc921242ef12c2a4ae999e9645ae7953d732d7873e','Audited global research resource scope')
 all_sources={str(p):sha(p)for group in paths.values()for p in group};model_sources={str(p):sha(p)for p in paths['model']}
 return paths,all_sources,model_sources
def test_inventory():
 groups={}
 for namespace,root in(('model',SRC),('owner',OWNER)):
  methods={p.stem:test_methods(p)for p in sorted(root.glob('test_*.py'))};counts={name:len(rows)for name,rows in methods.items()}
  groups[namespace+'_counts']=counts;groups[namespace+'_methods']=methods;groups[namespace+'_total']=sum(counts.values())
 req(groups['model_total']==16 and groups['owner_total']>0,'Exactly frozen16 model and positive dynamic owner tests before native I/O')
 return dict(groups,total=groups['model_total']+groups['owner_total'],tests_before_any_native_byte_reads=True,no_external_test_result_assumed=True)
def main():
 head=os.environ.get('TASK1_NATIVE_GUI_LITE_R5_EXPECTED_PARENT','')
 req(re.fullmatch('[0-9a-f]{40}',head)is not None,'Set TASK1_NATIVE_GUI_LITE_R5_EXPECTED_PARENT to the actual public40hex branch parent')
 req(ADMISSION.is_file()and not ADMISSION.is_symlink(),'New actual-result-bound positive GUI-only admission and safe boundary required')
 with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
  req(not OUT.exists(),'Unique run required; preserve all earlier attempts');OUT.mkdir()
  for name in('logs','source-publication','result-publication','source'):(OUT/name).mkdir()
  limits=ep.resolve_limits();req(limits['cpu_limit']==4 and limits['total_memory_bytes']==8000000000 and limits['max_cells']==800000,'Unchanged CPU4/8e9 whole-taskRAM/800k policy');configured=ep.configure_process(limits);ledger=budget.load_ledger()
  req(ledger.get('cumulative_time_unlimited')is True,'Actual unlimited-time authorization required');budget.require_time_budget(ledger,CAP);del ledger
  pid=os.getpid();ticks=b.ticks(pid);start=time.monotonic();owned={pid:ticks};stop=threading.Event();mutex=threading.RLock()
  state=dict(phase='preparing',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);research_known={};counter=0;git_wall=0.
  req(sha(PUB)=='e29f03472c430598d9b7599eee28416b3453653b977a00c3d1999fa363f75f45','Exact standard verified r3 publisher')
  packs,sources,model_sources=source_inventory()
  helpers={str(ROOT/'tools'/name):sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  admission=read(ADMISSION);prospective=test_inventory();req(prospective['model_total']==16,'Exactly frozen16 model tests');validate_admission(admission,sources,model_sources,prospective['owner_total'])
  reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,
   controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),
   source_sha256=sources,helper_sha256=helpers,outer_deadline_seconds=CAP,numerical_child_deadline_seconds=NUMERIC_CAP,
   resource_limits=limits,task_temp_accounting_roots=['/dev/shm/task1-*','/tmp/task1-*'],temporary_accounting_scope='All owned task roots in BOTH tmpfs and auxiliary /tmp; no files moved/deleted to avoid accounting',execution_policy_refs=ep.execution_policy_refs(),configured=configured,
   new_PDE_RHS=0,new_Q_loads=0,new_angular_evaluations=0,new_eigen_solves=0,source_fields_only=True,scenario='native_display_plane_and_actual_probe_GUI_derivative_only')
  new(OUT/'registration.json',reg)
  receipt=dict(schema='task1-native-GUI-lite-owner-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,
   new_PDE_RHS=0,new_Q_loads=0,new_angular_evaluations=0,GUI_generated=False,Windows_saved_verified=False,candidate_adopted=False)
  fast={};large={};native_stats={};original_absences=[]
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
    counter+=1;item=dict(schema='task1-native-GUI-lite-live-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,
     elapsed_seconds=time.monotonic()-start,**extra);new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),item)
    for target in(OUT/'current.json',ROOT/'runtime/task1-native-GUI-lite-r5-live-20261025.json'):
     tmp=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(tmp,item);os.replace(tmp,target)
    state['phase']=phase
  def guard():
   with mutex:
    live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);fast_now=dict(fast);large_now=dict(large);known_now=dict(research_known)
   observation=resource_scope.observe(live,b.ticks,known_now);rss=observation['research_RSS_bytes'];temp_parts,tmp=task_temp_usage()
   with mutex:research_known.update(observation['members']);state['latest_process_audit']=observation
   with mutex:state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp),peak_task_shm_bytes=max(state.get('peak_task_shm_bytes',0),temp_parts['/dev/shm']),peak_task_tmp_aux_bytes=max(state.get('peak_task_tmp_aux_bytes',0),temp_parts['/tmp']))
   req(rss+tmp<=limits['total_memory_bytes'],'Actual ALL research-family RSS plus task1 roots under BOTH /dev/shm and /tmp cap')
   req(time.monotonic()-start<CAP,'Finite2400s stored-native postprocess owner watchdog');req(not(OUT/'STOP').exists(),'Explicit STOP marker')
   for path,expected in fast_now.items():req(sha(path)==expected,'Frozen small source/input/policy changed '+path)
   for path,(_,ident)in large_now.items():req(identity(path)==ident,'Large immutable metadata stat identity changed '+path)
   with mutex:current_native=dict(native_stats)
   for path,ident in current_native.items():req(identity(path)==ident,'Native descriptor stat changed; byte reads remain post-MFG only '+path)
   for path in original_absences:req(not Path(path).exists(),'Originally absent old pre-S output appeared; preserve/inspect history '+path)
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
   for path in files.values():req(path.is_file()and path==path.resolve()and not path.is_symlink()and path.stat().st_size<MAX_FILE,'Preserve file and report publication bound '+str(path))
   return dict(schema='task1-supported-Git-transport-plan-v1',repository='yoodohyun-codex-cloud/ngg-tis-task1',branch='codex/task1-cloud-restart-20261020',expected_parent=parent,message=message,
    files={target:dict(local_path=str(path),SHA256=sha(path),bytes=path.stat().st_size)for target,path in files.items()},required_result_receipt=str(destination),required_receipt_status='published_readback_verified',new_PDE_required=False,comment_body=comment)
  try:
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    history,history_refs,history_absences=verify_history(admission,sources);original_absences.extend(history_absences);new(OUT/'previous-preS-failure-proof.json',history)
    R2history,R2refs,R2absences=verify_R2_history(admission,sources);original_absences.extend(R2absences);new(OUT/'previous-R2-postS-failure-proof.json',R2history)
    R3history,R3refs,R3absences=verify_R3_history(admission,sources);original_absences.extend(R3absences);new(OUT/'previous-R3-preS-failure-proof.json',R3history)
    R4history,R4refs,R4absences=verify_R4_history(admission,sources);original_absences.extend(R4absences);new(OUT/'previous-R4-numeric-failure-proof.json',R4history)
    import gui_build as model
    new(OUT/'root-admission.json',admission)
    spec=model.make_spec(admission);refs=dict(spec['metadata_input_sha256'])
    req(spec['inputs']['metadata_input_sha256']==refs,'Only authenticated metadata pins before manufactured tests');refs.update(history_refs);refs.update(R2refs);refs.update(R3refs);refs.update(R4refs);refs[str(OUT/'previous-preS-failure-proof.json')]=sha(OUT/'previous-preS-failure-proof.json');refs[str(OUT/'previous-R2-postS-failure-proof.json')]=sha(OUT/'previous-R2-postS-failure-proof.json');refs[str(OUT/'previous-R3-preS-failure-proof.json')]=sha(OUT/'previous-R3-preS-failure-proof.json');refs[str(OUT/'previous-R4-numeric-failure-proof.json')]=sha(OUT/'previous-R4-numeric-failure-proof.json')
    profiles=read(OWNER/'actual-parent-metadata-profiles.json')
    for profile in profiles['actual_metadata_only_profiles']:
     original=Path(profile['original_path']);copy=OWNER/profile['archive_source_name'];req(original.stat().st_size==profile['bytes']and sha(original)==profile['SHA256']and copy.read_bytes()==original.read_bytes()and sources[str(copy)]==profile['SHA256'],'Actual root metadata-only profile originals/aliases unchanged');refs[str(original)]=profile['SHA256']
    req(len(spec['inputs']['cases'])==7,'Three new and four legacy mandatory cases')
    for path in refs:req(Path(path).suffix.lower()in('.json','.md','.txt','.log','.py'),'No native data files in pre-MFG metadata pin set')
    for descriptor in spec['inputs']['native_input_descriptors']:
     path=descriptor['path'];req(type(descriptor.get('bytes'))is int and descriptor['bytes']>=0 and re.fullmatch('[0-9a-f]{64}',descriptor['SHA256']),'Declared native descriptor full identity')
     stat=identity(path);req(stat[2]==descriptor['bytes'],'Declared native byte size before source admission, no content read')
     native_stats[path]=stat
    tests=prospective;new(OUT/'test-source-inventory.json',tests);new(OUT/'spec.json',spec);frozen={}
    for namespace,paths in packs.items():
     directory=OUT/'source'/namespace;directory.mkdir()
     for path in paths:
      target=directory/path.name
      with target.open('xb')as stream:stream.write(path.read_bytes())
      req(sha(target)==sources[str(path)],'Exact canonical-to-published GUI snapshot');frozen[str(target)]=sha(target)
    refs.update({str(ADMISSION):sha(ADMISSION),str(OUT/'root-admission.json'):sha(OUT/'root-admission.json')})
    new(OUT/'native-descriptor-stat-registration.json',dict(schema='task1-native-GUI-lite-pre-MFG-native-stats-v1',files={p:list(v)for p,v in native_stats.items()},native_bytes_opened=False))
    new(OUT/'preregistration.json',dict(schema='task1-native-GUI-lite-preregistration-v1',question='Build compact actual native display only after frozen16 model and dynamic owner tests pass. FineB0/P23 andcoarseE13 are separate fromlegacyB0/MP8/12/16;actual120probes strict60/extrap60, no crossgridrank. Reuse original storedAM/RMS,oneactual2000HzE fordisplayarrows,andoriginalstatistics. NeverloadQ/phi/newPDE/eigen/angular/ROIstatistics. Sourcepublication/readback,globalwhole-tasklimits,andactualsafe-boundarypositiveadmissionprecedeallwork. BrowserQAseparate.',source_sha256=sources,model_source_sha256=model_sources,frozen_source_sha256=frozen,metadata_input_sha256=refs,native_input_descriptors=spec['inputs']['native_input_descriptors'],native_descriptor_stats_SHA256=sha(OUT/'native-descriptor-stat-registration.json'),helper_sha256=helpers,execution_policy_refs=reg['execution_policy_refs'],limits=limits,spec_SHA256=sha(OUT/'spec.json'),root_admission_SHA256=sha(OUT/'root-admission.json'),root_decision=admission,previous_preS_failure_proof_SHA256=sha(OUT/'previous-preS-failure-proof.json'),previous_R2_postS_failure_proof_SHA256=sha(OUT/'previous-R2-postS-failure-proof.json'),previous_R3_preS_failure_proof_SHA256=sha(OUT/'previous-R3-preS-failure-proof.json'),previous_R4_numeric_failure_proof_SHA256=sha(OUT/'previous-R4-numeric-failure-proof.json'),parent_metadata_lifetime_fix=dict(prepare_once=True,metadata_pins_copied_from_same_authenticated_spec=True,full_input_SHA_binding_and_worker_exact_spec_reconstruction_retained=True,release_parent_roots_after_serialization=True,GC_then_optional_own_malloc_trim=True,no_native_phase_before_MFG=True),expected_synthetic_tests=tests['total'],expected_model_tests=16,expected_owner_tests=tests['owner_total'],test_inventory_SHA256=sha(OUT/'test-source-inventory.json'),tests_before_any_native_byte_reads=True,expected_cases=7,expected_new_probes=120,maximum_new_PDE_RHS=0,maximum_new_Q_loads=0,maximum_new_eigen_solves=0,maximum_new_angular_evaluations=0,maximum_new_stat_reductions=0,hard_child_seconds=NUMERIC_CAP,resource_forecast=dict(fixed_child_RLIMIT_AS_bytes=FIXED_CHILD_AS,predicted_child_RSS_bytes=PREDICTED_CHILD_RSS,original_model_informational_forecast_bytes=ORIGINAL_MODEL_CHILD_RSS,revised_owner_provisional_forecast=True,allocation_rationale_SHA256=sha(OWNER/'OWNER_RSS_ESTIMATE.json'),expected_output_bytes=EXPECTED_OUTPUT_BYTES,new_TMPFS_output_forecast_bytes=EXPECTED_NEW_TMPFS_OUTPUT_BYTES,new_output_storage='existing_workspace_disk',publisher_output_storage='mandatory_dev_shm_counted_actual_before_each_stage',forecast_not_measured=True,actual_total_research_RSS_plus_all_task_tmpfs_cap_bytes=8000000000),functional_display_bounds=dict(payload_JSON_bytes=4900000,index_HTML_bytes=5000000,storage_quota=False),browser_validation_performed=False,old_GUI_pointers_modified=False,candidate_adopted=False))
    bind({**sources,**frozen,**refs,**helpers,**reg['execution_policy_refs'],**{str(OUT/name):sha(OUT/name)for name in('spec.json','test-source-inventory.json','preregistration.json','native-descriptor-stat-registration.json')}})
   files={}
   for path in(OUT/'source').rglob('*'):
    if path.is_file():files['tools/native_GUI_lite_r5_20261025/'+path.relative_to(OUT/'source').as_posix()]=path
   for name in('registration.json','preregistration.json','test-source-inventory.json','spec.json','root-admission.json','native-descriptor-stat-registration.json','previous-preS-failure-proof.json','previous-R2-postS-failure-proof.json','previous-R3-preS-failure-proof.json','previous-R4-numeric-failure-proof.json'):files[REMOTE+name]=OUT/name
   # The complete worker spec, preregistration and all hashes are immutable on
   # disk. No later parent phase needs these large metadata object graphs.
   before_release_RSS=b.rss(pid)
   del spec,refs,frozen,packs,admission,history,history_refs,history_absences,R2history,R2refs,R2absences,R3history,R3refs,R3absences,R4history,R4refs,R4absences,reg,configured,prospective,profiles
   descriptor=path=paths=directory=target=profile=original=copy=None
   release=reclaim_parent_metadata('before_source_publication',pid,before_release_RSS)
   new(OUT/'parent-prepublication-metadata-release.json',release);bind({str(OUT/'parent-prepublication-metadata-release.json'):sha(OUT/'parent-prepublication-metadata-release.json')})
   files[REMOTE+'parent-prepublication-metadata-release.json']=OUT/'parent-prepublication-metadata-release.json'
   spath=OUT/'source-plan.json';new(spath,plan(files,head,'Preregister compact seven-case native GUI build after16-source-fixture gates; browser separate',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(spath),'--output','/dev/shm/task1-git-native-GUI-lite-r5-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',PUB_CAP,True)
   published=read(OUT/'source-publication/result-publication.json');req(published['status']=='published_readback_verified','Actual immutable source/input readback before bounded manufactured tests and stored-native array reads')
   source_commit=published['commit'];del published,files;published={'commit':source_commit};before_release_RSS=b.rss(pid);release=None
   new(OUT/'parent-postpublication-metadata-release.json',reclaim_parent_metadata('before_fresh_numeric_admission',pid,before_release_RSS));bind({str(OUT/'parent-postpublication-metadata-release.json'):sha(OUT/'parent-postpublication-metadata-release.json')})
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    checkpoint('numeric-admission',source_commit=published['commit'],manufactured_tests_started=False,native_bytes_started=False)
    guard();temp_parts,tmp=task_temp_usage()
    with mutex:authenticated_now=dict(owned);known_now=dict(research_known)
    observation=resource_scope.observe(authenticated_now,b.ticks,known_now)
    with mutex:research_known.update(observation['members']);state['latest_process_audit']=observation
    physical_forecast=tmp+observation['research_RSS_bytes']+PREDICTED_CHILD_RSS+EXPECTED_NEW_TMPFS_OUTPUT_BYTES
    new(OUT/'numeric-admission.json',dict(admitted=physical_forecast<=limits['total_memory_bytes'],forecast_excess_bytes=max(0,physical_forecast-limits['total_memory_bytes']),parent_metadata_release_SHA256=sha(OUT/'parent-postpublication-metadata-release.json'),task_temp_accounting_roots=['/dev/shm/task1-*','/tmp/task1-*'],task_shm_bytes=temp_parts['/dev/shm'],task_tmp_aux_bytes=temp_parts['/tmp'],task_temp_accounted_bytes=tmp,kind='manufactured_gates_then_finite_stored_native_postprocess',all_owned_tmpfs_bytes=tmp,all_research_RSS_bytes=observation['research_RSS_bytes'],research_scope=observation['scope'],forecast_child_RSS_bytes=PREDICTED_CHILD_RSS,original_model_informational_forecast_bytes=ORIGINAL_MODEL_CHILD_RSS,revised_provisional_forecast_not_measured=True,allocation_rationale_SHA256=sha(OWNER/'OWNER_RSS_ESTIMATE.json'),forecast_new_output_bytes=EXPECTED_OUTPUT_BYTES,forecast_new_TMPFS_output_bytes=EXPECTED_NEW_TMPFS_OUTPUT_BYTES,new_output_storage='existing_workspace_disk',publisher_dev_shm_cache_counted_in_actual_temp=True,storage_capacity_guard_enabled=False,physical_forecast_bytes=physical_forecast,physical_cap_bytes=limits['total_memory_bytes'],child_RLIMIT_AS_bytes=FIXED_CHILD_AS,actual_hardware_wiring_changed=False))
    req(physical_forecast<=limits['total_memory_bytes']==8000000000 and limits['cpu_limit']==4 and limits['max_cells']==800000,'Unchanged actual researchRSS+alltmpfs budget before manufactured tests and native postprocessing; exact numeric-admission diagnostic preserved')
    bind({str(OUT/'numeric-admission.json'):sha(OUT/'numeric-admission.json')})
    code=command(['setpriv','--pdeathsig','KILL',sys.executable,'-B',str(OUT/'source/owner/worker.py'),'--output',str(OUT),'--source',str(SRC),'--as-limit',str(FIXED_CHILD_AS),
     '--registration-sha',sha(OUT/'registration.json'),'--preregistration-sha',sha(OUT/'preregistration.json'),'--publication-sha',sha(OUT/'source-publication/result-publication.json'),'--publication-plan-sha',sha(spath)],'native-GUI-lite-build-child',NUMERIC_CAP,allow_failure=True)
   summary=read(OUT/'summary.json')if(OUT/'summary.json').is_file()else None;passed=False
   if code==0 and summary is not None:
    mfg=read(OUT/'synthetic-test-receipt.json');req(mfg['source_publication_commit']==published['commit']and mfg['owner_source_sha256']==sources,'Actual source-bound MFG result before parent marks GUI build complete')
    expected_events=[module+'.'+method for namespace in('model','owner')for module,methods in tests[namespace+'_methods'].items()for method in methods]
    mfg_accounting=validate_MFG(mfg,model_sources,tests['owner_total'],expected_events);accounting=validate_summary(summary);accounting['manufactured_tests']=mfg_accounting;passed=True
   else:accounting=dict(passed=False,worker_exit_code=code,summary_present=summary is not None,partial_results_preserved=True,actual_hardware_wiring_changed=False)
   with mutex:all_pins={**fast,**{path:value[0]for path,value in large.items()}}
   for path,expected in all_pins.items():guard();req(sha(path)==expected,'Complete source/input/policy SHA after native scalar/probe postprocessing')
   new(OUT/'research-process-accounting.json',state.get('latest_process_audit',{}))
   new(OUT/'execution-stage.json',dict(status='native_GUI_lite_built'if passed else'native_GUI_lite_failed_or_partial_preserved',worker_exit_code=code,accounting=accounting,actual_new_PDE_RHS=0,new_Q_loads=0,new_angular_evaluations=0,actual_hardware_wiring_changed=False,source_commit=published['commit']))
   files={}
   for path in OUT.rglob('*'):
    rel=path.relative_to(OUT)
    if path.is_file()and(rel.parts[0]in('logs','cases','candidates','proofs','case-proofs')or(len(rel.parts)==1 and path.name not in('current.json','source-plan.json','result-plan.json'))):files[REMOTE+rel.as_posix()]=path
   files[REMOTE+'source-publication-receipt.json']=OUT/'source-publication/result-publication.json'
   missing=[name for name in('synthetic-test-receipt.json','worker-receipt.json','payload.json','index.html','summary.json','gui-build-receipt.json')if not(OUT/name).is_file()]
   new(OUT/'missing-output-inventory.json',dict(status='actual_outputs_and_absences_preserved',missing=missing,no_browser_result_inferred=True))
   files[REMOTE+'missing-output-inventory.json']=OUT/'missing-output-inventory.json'
   rp=OUT/'result-plan.json';new(rp,plan(files,published['commit'],'Preserve seven-case compact native GUI derivative or exact fixture/build failure; browser remains unverified',OUT/'result-publication/result-publication.json',
    comment='기존실제nativeAM/RMS와2000Hz복소E의표시용단면및기존R2의120개무부하프로브결과를연결한작은GUI입니다. 새PDE/Q/고유분해/각도스캔/ROI통계/프로브파형재계산은없습니다. FineB0/P23·coarseE13은legacyB0/MP8/12/16과별도격자구역에표시하고,oldTop5는legacy로만보존하며crossgridrank를계산하지않습니다. 실제source-bound16개모델과추가owner fixture통과후원데이터를읽으며,원Float64통계와128개원excerpt는보존하고GUI에는사전등록한64개실제샘플과sparsearrow부분집합만표시합니다. P23접촉실패/E13미채택/SC·가장자리·접촉불확실성을유지하며,표시Float16오차와clipping을원수치와구분합니다. 이게시의성공은브라우저·수렴·실험·안전·활성화·채택검증이아닙니다. 실제상태:'+('built_browser_unverified'if passed else'failed_or_partial_preserved')))
   command([sys.executable,'-B',str(PUB),'--plan',str(rp),'--output','/dev/shm/task1-git-native-GUI-lite-r5-result-20261025','--queue-registration',str(OUT/'registration.json')],'result-publication',PUB_CAP,True)
   result=read(OUT/'result-publication/result-publication.json');req(result['status']=='published_readback_verified','Full result/error publication readback')
   receipt.update(status='native_GUI_lite_built_published_browser_unverified'if passed else'native_GUI_lite_failed_or_partial_published',source_commit=published['commit'],result_commit=result['commit'],postprocess_accounting=accounting,GUI_generated=passed,browser_validation_performed=False)
   checkpoint('native_GUI_lite_build_review_browser_separate',result_commit=result['commit'],calculation_passed=passed)
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
   ledger['runs'].append(dict(run_id=OUT.name,stage='native_GUI_lite_manufactured_tests_and_build',seconds=debit,status=receipt['status'],Git_children_debited_separately=True))
   temp=LEDGER.with_name('task1-budget-native-GUI-lite-r5-'+str(pid)+'.tmp');new(temp,ledger);os.replace(temp,LEDGER)
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={k:v for k,v in state.items()if k.startswith('peak_')},remaining_approved_seconds=budget.remaining_seconds(ledger));new(OUT/'receipt.json',receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
