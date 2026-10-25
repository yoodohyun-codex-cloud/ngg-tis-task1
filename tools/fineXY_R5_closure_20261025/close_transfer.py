"""Finite metadata closure for actual fineXY outcome and preserved R5 failure.

No helper, process, lock, network or research work runs on import. Root alone
executes after selecting the actual completed or failed fineXY R. No native reads.
"""
import argparse,fcntl,hashlib,json,os,re,signal,subprocess,sys,threading,time
from pathlib import Path
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-fineXY-R5-closure-20261025/source')
OUT=Path('/dev/shm/task1-fineXY-R5-closure-20261025-run')
PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
PUBLISHER_SHA='e29f03472c430598d9b7599eee28416b3453653b977a00c3d1999fa363f75f45'
PREVIOUS=Path('/dev/shm/task1-fine47-nativeGUI-transfer-20261025-run/manifests/fine47-nativeGUI-transfer-manifest.json')
PREVIOUS_SHA='9aee65feb1da8a859ce1b19dc1909739924c943e13475779d5e2f268739e7b41'
PUBLIC='docs/TASK1_CONTACT_EDGE_20261025';PACKAGE='fineXY-R5-closure-20261025'
CAP=1000;PUB_CAP=330;MAX_METADATA=8_000_000
HELPERS={'metadata_plan.py':'491985f5c43e9763b5bdc4b759eaa50a04b8b5dc1b180f1d5e8e78bbdb81e1c2','incremental_transfer.py':'4324dbd4b37c34a6d887b248406b02dd1a65df82266c70c6689c1983052c4d21','frozen_manifest_validation.py':'8be379f9f1b6c5d1cfa65baa24eebce5084282bc3e2753490d811c901ea717c0','resource_scope.py':'6c09a7cd06fed12a2e9950cc921242ef12c2a4ae999e9645ae7953d732d7873e'}
RUNS={'r5_failed':Path('/dev/shm/task1-results-gui-browser-r5-20261025-run'),'fine':Path('/dev/shm/task1-P23-fineXY-20261025-run')}
R5_SOURCE_COMMIT='c773e4eeb1b0e4e46837357cc5e96644a6daaa24'
R5_SOURCE_RECEIPT_SHA='78ae57fc18958b5e411a85e15a6b2b846905ed5cc4afdfc34c71a3e2868199a6'
def require(ok,message):
 if not ok:raise ValueError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def read(path):
 path=Path(path);require(path.is_absolute()and path==path.resolve()and path.is_file()and not path.is_symlink()and path.stat().st_size<=MAX_METADATA,'Canonical bounded original metadata '+str(path));return json.loads(path.read_bytes())
def encoded(value):return(json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+'\n').encode()
def tree_size(path):
 try:return path.stat().st_size if path.is_file()else sum(p.stat().st_size for p in path.rglob('*')if p.is_file())
 except FileNotFoundError:return 0
def new(path,value):
 with Path(path).open('xb')as stream:stream.write(encoded(value))
def same_or_create(path,value):
 if Path(path).exists():require(Path(path).read_bytes()==encoded(value),'Exact preserved plan/output must remain unchanged '+str(path))
 else:new(path,value)
def file_plan(path):return dict(local_path=str(path),SHA256=sha(path),bytes=Path(path).stat().st_size)
def publication_proof(doc,plan=None):
 require(doc.get('status')=='published_readback_verified'and re.fullmatch('[0-9a-f]{40}',doc.get('commit','')),'Actual complete standard publication proof')
 if plan is not None:require(set(doc['files'])==set(plan['files'])and doc['expected_parent']==plan['expected_parent'],'Exact frozen publication plan coverage')
 for target,item in doc['files'].items():
  require(item.get('readback_passed')is True and re.fullmatch('[0-9a-f]{64}',item.get('SHA256',''))and type(item.get('bytes'))is int and item['bytes']>=0,'Full publication file SHA/bytes/readback')
  if plan is not None:require(item['SHA256']==plan['files'][target]['SHA256']and item['bytes']==plan['files'][target]['bytes'],'Actual immutable publication bytes match plan')
def direct_metadata_proof(publication,path,published_target=None):
 rows=[row for target,row in publication['files'].items()if (target==published_target if published_target is not None else target.endswith('/'+Path(path).name))and row['SHA256']==sha(path)and row['bytes']==Path(path).stat().st_size]
 require(rows and all(row.get('readback_passed')is True for row in rows),'Original metadata has direct full publication readback '+str(path))
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for name in('fine-result-commit','fine-result-receipt-sha256','fine-owner-receipt-sha256','r5-owner-receipt-sha256'):parser.add_argument('--'+name,required=True)
 parser.add_argument('--fine-outcome',choices=('completed','failed'),required=True);parser.add_argument('--resume',action='store_true');args=parser.parse_args()
 initial_parent=os.environ.get('TASK1_FINE_R5_CLOSURE_EXPECTED_PARENT','');require(re.fullmatch('[0-9a-f]{40}',initial_parent)is not None,'Set actual current public branch parent in TASK1_FINE_R5_CLOSURE_EXPECTED_PARENT')
 require(re.fullmatch('[0-9a-f]{40}',args.fine_result_commit)is not None and all(re.fullmatch('[0-9a-f]{64}',getattr(args,k))is not None for k in('fine_result_receipt_sha256','fine_owner_receipt_sha256','r5_owner_receipt_sha256')),'Root must select actual terminal fine R and both original owner full SHA values, never placeholders')
 sys.dont_write_bytecode=True;sys.path[:0]=[str(SOURCE),str(ROOT/'tools')]
 import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget,resource_scope
 from metadata_plan import metadata_publication_plan
 from incremental_transfer import merge_files
 from frozen_manifest_validation import validate_manifest
 from closure_contracts import validate_r5,validate_fine,require_metadata_covered
 for name,expected in HELPERS.items():require(sha(SOURCE/name)==expected,'Exact unchanged approved helper '+name)
 require(sha(PUB)==PUBLISHER_SHA,'Exact standard r3 publisher source')
 limits=ep.resolve_limits();require(limits['cpu_limit']<=4 and limits['total_memory_bytes']<=8000000000,'Existing CPU4/whole-research8e9 cap, no expansion');configured=ep.configure_process(limits)
 require(budget.load_ledger().get('cumulative_time_unlimited')is True,'Existing unlimited cumulative-time authorization required');budget.require_time_budget(budget.load_ledger(),CAP)
 source_refs={str(p):sha(p)for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')};policy_refs=ep.execution_policy_refs();source_refs.update({str(PUB):sha(PUB),**policy_refs})
 request=dict(schema='task1-terminal-fine-and-failed-R5-closure-request-v1',expected_initial_parent=initial_parent,fine_result_commit=args.fine_result_commit,fine_result_publication_SHA256=args.fine_result_receipt_sha256,fine_owner_SHA256=args.fine_owner_receipt_sha256,r5_owner_SHA256=args.r5_owner_receipt_sha256,fine_outcome=args.fine_outcome,previous_manifest_SHA256=PREVIOUS_SHA,source_SHA256=source_refs,metadata_only=True,new_PDE_RHS=0,new_fields=0,new_physical_lease=False)
 if OUT.exists():require(args.resume and OUT==OUT.resolve()and not OUT.is_symlink(),'Use exact --resume for preserved output; never overwrite another attempt')
 else:require(not args.resume,'No old closure output to resume');OUT.mkdir()
 output_mutex=(OUT/'.metadata-output-supervisor.lock').open('a');fcntl.flock(output_mutex.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 same_or_create(OUT/'request.json',request)
 for folder in('attempts','originals','R5-R','M','T','manifests','logs','resume-verification'):(OUT/folder).mkdir(exist_ok=True)
 # A metadata supervisor owns no queue/loop/execution lock. The standard r3
 # publisher acquires all three itself; busy foreign work fails safely.
 for old in(OUT/'attempts').glob('*/registration.json'):
  oldreg=read(old);require(not b.live(oldreg['supervisor_pid'],oldreg['proc_start_ticks']),'A live metadata supervisor already owns this output; no duplicate publication worker')
 attempt=max([int(p.name)for p in(OUT/'attempts').iterdir()if p.is_dir()and p.name.isdigit()]+[0])+1;adir=OUT/'attempts'/str(attempt);adir.mkdir();pid=os.getpid();tick=b.ticks(pid);started=time.monotonic();owned={pid:tick};known={};mutex=threading.RLock();stop=threading.Event();git_wall=0.;counter=0;absence_pins=[]
 state=dict(phase='validating_completed_scopes',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0)
 reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=tick,controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),source_sha256=source_refs,metadata_only=True,new_PDE_RHS=0,new_physical_lease=False,outer_deadline_seconds=CAP,publication_child_deadline_seconds=PUB_CAP,configured=configured,limits=limits)
 new(adir/'registration.json',reg);pins={**source_refs,str(OUT/'request.json'):sha(OUT/'request.json'),str(adir/'registration.json'):sha(adir/'registration.json')};receipt=dict(schema='task1-terminal-fine-and-failed-R5-closure-attempt-v1',status='failed_preserved',started_utc=b.now(),attempt=attempt,metadata_only=True,new_PDE_RHS=0,new_native_field_reads=0,Windows_backup_complete=False,OneDrive_sync_verified=False)
 def pin(path):
  digest=sha(path)
  with mutex:pins[str(path)]=digest
 def guard():
  with mutex:live=b.owned_descendants(pid,tick,dict(owned));owned.update(live);remembered=dict(known);frozen=dict(pins)
  observed=resource_scope.observe(live,b.ticks,remembered);rss=observed['research_RSS_bytes'];tmp=sum(tree_size(p)for p in Path('/dev/shm').glob('task1-*'))
  with mutex:known.update(observed['members']);state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp));state['process_audit']=observed
  require(rss+tmp<=limits['total_memory_bytes'],'ALL proven research RSS plus ALL task1 tmpfs8e9 cap');require(time.monotonic()-started<CAP and not(OUT/'STOP').exists(),'Finite1000s closure watchdog or STOP')
  for path,expected in frozen.items():require(sha(path)==expected,'Exact original/source/plan bytes changed '+path)
  for path in absence_pins:require(not path.exists(),'Original recorded absence changed '+str(path))
 def checkpoint(phase,**extra):
  nonlocal counter
  with mutex:
   counter+=1;state['phase']=phase;row=dict(updated_utc=b.now(),pid=pid,proc_start_ticks=tick,attempt=attempt,phase=phase,elapsed_seconds=time.monotonic()-started,**extra);new(adir/('checkpoint-%04d.json'%counter),row);temp=OUT/('current-'+str(pid)+'.tmp');new(temp,row);os.replace(temp,OUT/'current.json')
 def interrupt(signum,frame):raise InterruptedError(state.get('error','Finite metadata watchdog or signal'))
 def monitor():
  while not stop.wait(.25):
   try:guard()
   except BaseException as error:state['error']=str(error);os.kill(pid,signal.SIGTERM);return
 handlers={sig:signal.getsignal(sig)for sig in(signal.SIGINT,signal.SIGTERM,signal.SIGALRM)}
 for sig in handlers:signal.signal(sig,interrupt)
 signal.setitimer(signal.ITIMER_REAL,CAP);thread=threading.Thread(target=monitor,daemon=True);thread.start()
 def copy_original(label,name,path):
  path=Path(path);require(path.is_file()and path==path.resolve()and not path.is_symlink()and path.stat().st_size<=MAX_METADATA,'Bounded original metadata only, no arrays '+str(path));raw=path.read_bytes();pin(path);directory=OUT/'originals'/label;directory.mkdir(exist_ok=True);target=directory/name
  if target.exists():require(target.read_bytes()==raw,'Old metadata snapshot differs; preserve both and stop')
  else:
   with target.open('xb')as stream:stream.write(raw)
  require(sha(path)==sha(target),'Byte-exact original metadata copy');pin(target);return target
 def publish(stage,plan):
  nonlocal git_wall
  planpath=OUT/(stage+'-plan.json');same_or_create(planpath,plan);pin(planpath);guard();checkpoint(stage+'_publication')
  workspace=Path('/dev/shm')/('task1-git-fineXY-R5-closure-'+stage+'-20261025');argv=[sys.executable,'-B',str(PUB),'--plan',str(planpath),'--output',str(workspace),'--queue-registration',str(adir/'registration.json')];log=adir/(stage+'-publisher.log');before=time.monotonic();ledger_before=len(budget.load_ledger()['runs'])
  with log.open('xb')as stream:
   child=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
   with mutex:owned[child.pid]=b.ticks(child.pid)
   try:code=child.wait(timeout=max(.01,min(PUB_CAP,CAP-(time.monotonic()-started))))
   finally:
    if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
    recorded=sum(row.get('seconds',0.)for row in budget.load_ledger()['runs'][ledger_before:]if row.get('run_id')==workspace.name);git_wall+=min(time.monotonic()-before,recorded)
  require(code==0,'Publication failed; preserve exact plan/workspace/checkpoints and resume this same command, no PDE repeated')
  doc=read(plan['required_result_receipt']);publication_proof(doc,plan);pin(Path(plan['required_result_receipt']));return doc
 try:
  require(sha(PREVIOUS)==PREVIOUS_SHA,'Pinned actual previous FULL fine47/nativeGUI manifest');previous=read(PREVIOUS);validate_manifest(previous);pin(PREVIOUS)
  scopes={};copies={};identities={};public_states={}
  # Terminal identity checks precede every publisher. No publication while either
  # original owner remains live. No numerical/model APIs or raw bytes are read.
  for label,run in RUNS.items():
   owner_path=run/'receipt.json';owner=read(owner_path);registration=read(run/'registration.json')
   require(not b.live(registration['supervisor_pid'],registration['proc_start_ticks']),'Original owner still live; wait for terminal fine/R5 outcome before any closure publication')
   require(sha(owner_path)==(args.r5_owner_receipt_sha256 if label=='r5_failed'else args.fine_owner_receipt_sha256),'Root-selected terminal owner exact SHA '+label)
   source_path=run/'source-publication/result-publication.json';source=read(source_path);publication_proof(source)
   if label=='r5_failed':
    require(source['commit']==R5_SOURCE_COMMIT and sha(source_path)==R5_SOURCE_RECEIPT_SHA,'Exact actual R5 source publication receipt');direct_metadata_proof(source,run/'registration.json');direct_metadata_proof(source,run/'preregistration.json');semantic=validate_r5(owner)
    result_path=None;result=None
   else:
    result_path=run/'result-publication/result-publication.json';result=read(result_path);publication_proof(result)
    require(result['commit']==args.fine_result_commit and sha(result_path)==args.fine_result_receipt_sha256,'Explicit root-selected actual fine result publication');direct_metadata_proof(result,source_path,'data-native/P23-fineXY-20261025/source-publication-receipt.json')
    semantic=validate_fine(owner,source,result,args.fine_outcome,read(run/'execution-stage.json')if(run/'execution-stage.json').is_file()else None)
   scopes[label]=dict(source=source,result=result,owner=owner,semantic=semantic)
   original={'source-publication-receipt.json':source_path,'owner-receipt.json':owner_path,'registration.json':run/'registration.json','preregistration.json':run/'preregistration.json'}
   if result_path is not None:original['result-publication-receipt.json']=result_path
   # Only actual bounded JSON/logs are packaged. Browser scratch is preserved
   # locally and explicitly not claimed as an off-machine full profile backup.
   for path in sorted(run.iterdir()):
    if path.is_file()and path.suffix=='.json'and path.name not in('source-plan.json','result-plan.json')and path.name not in original:original[path.name]=path
   for path in sorted((run/'logs').glob('*.log')):original['log-'+path.name]=path
   copies[label]={name:copy_original(label,name,path)for name,path in original.items()}
   identities[label]={name:dict(SHA256=sha(path),bytes=path.stat().st_size)for name,path in copies[label].items()}
  r5run=RUNS['r5_failed'];absent=[name for name in('worker-receipt.json','browser-receipt.json','input-SHA-verification.json','worker-stage-01-before-loopback.json','worker-stage-02-loopback-closed.json')if not(r5run/name).exists()]
  absence_pins.extend(r5run/name for name in absent)
  r5audit=dict(schema='task1-R5-failed-preserved-evidence-inventory-v1',semantic_status='FAILED_preserved_not_browser_PASS',owner_status=scopes['r5_failed']['owner']['status'],source_commit=R5_SOURCE_COMMIT,absent_original_metadata=absent,preserved_existing_metadata=identities['r5_failed'],worker_or_browser_receipt_created=False,browser_PASS_inferred=False,new_PDE_RHS=0,browser_scratch_preserved_locally=True,browser_scratch_in_this_publication=False,full_browser_profile_backup_claim=False,scientific_validation_inferred=False)
  audit_path=OUT/'R5-failure-inventory.json';same_or_create(audit_path,r5audit);pin(audit_path)
  guard();checkpoint('preserve_actual_R5_failure_before_metadata_closure')
  rfiles={PUBLIC+'/'+PACKAGE+'-R5-failure/'+name:file_plan(path)for name,path in copies['r5_failed'].items()};rfiles[PUBLIC+'/'+PACKAGE+'-R5-failure/R5-failure-inventory.json']=file_plan(audit_path)
  rplan=dict(schema='task1-supported-Git-transport-plan-v1',repository='yoodohyun-codex-cloud/ngg-tis-task1',branch='codex/task1-cloud-restart-20261020',expected_parent=initial_parent,new_PDE_required=False,message='Preserve actual R5 memory-cap failure, original logs and honest missing worker/browser receipts; no PASS claim',required_result_receipt=str(OUT/'R5-R/result-publication.json'),files=rfiles)
  r5result=publish('R5-R',rplan);scopes['r5_failed']['result']=r5result
  r5copy=copy_original('r5_failed','result-publication-receipt.json',OUT/'R5-R/result-publication.json');copies['r5_failed']['result-publication-receipt.json']=r5copy;identities['r5_failed']['result-publication-receipt.json']=dict(SHA256=sha(r5copy),bytes=r5copy.stat().st_size)
  for label,scope in scopes.items():public_states[label]=dict(**scope['semantic'],source_commit=scope['source']['commit'],result_commit=scope['result']['commit'])
  status_path=OUT/'scope-statuses.json';same_or_create(status_path,dict(schema='task1-fine-R5-scientific-status-preservation-v1',scopes=public_states,integrity_is_not_scientific_validation=True,candidate_adopted=False,Windows_backup_complete=False,OneDrive_sync_verified=False));pin(status_path)
  maincopies=copies['fine'];extras={'scope-statuses.json':status_path,'R5-failure-inventory.json':audit_path}
  for label,files in copies.items():
   for name,path in files.items():
    if label!='fine'or name not in('source-publication-receipt.json','result-publication-receipt.json','owner-receipt.json','preregistration.json'):extras[label+'/'+name]=path
  mplan=metadata_publication_plan(source_receipt_path=maincopies['source-publication-receipt.json'],result_receipt_path=maincopies['result-publication-receipt.json'],owner_receipt_path=maincopies['owner-receipt.json'],preregistration_path=maincopies['preregistration.json'],repo_prefix=PUBLIC+'/'+PACKAGE+'-metadata',expected_parent=r5result['commit'],required_result_receipt=OUT/'M/result-publication.json',package_id=PACKAGE,extra_metadata=extras)
  for path in SOURCE.iterdir():
   if path.is_file()and path.suffix in('.py','.json','.md'):mplan['files']['tools/fineXY_R5_closure_20261025/'+path.name]=file_plan(path)
  mplan['message']='Close actual fineXY terminal metadata and R5 failure without changing scientific or browser validation status';metadata=publish('M',mplan)
  flat={label+'-'+name:row for label,rows in identities.items()for name,row in rows.items()};require_metadata_covered(metadata,flat)
  last=PREVIOUS;lastsha=PREVIOUS_SHA;manifest_paths=[];build_proofs=[]
  for index,label in enumerate(('r5_failed','fine'),1):
   name='fineXY-R5-01-failed-browser-transfer-manifest.json'if index==1 else'fineXY-R5-transfer-manifest.json';target=OUT/'manifests'/name;proofpath=OUT/'manifests'/(name+'.build.json');files=copies[label];extra={('original-'+key.replace('.','-')):path for key,path in files.items()if path.suffix=='.json'and key not in('source-publication-receipt.json','result-publication-receipt.json')};package=PACKAGE+'-'+label
   if target.exists():
    verify=OUT/'resume-verification'/('%d-%s.json'%(attempt,label));checkproof=merge_files(last,files['source-publication-receipt.json'],files['result-publication-receipt.json'],OUT/'M/result-publication.json',verify,package_id=package,expected_previous_sha256=lastsha,extra_original_metadata=extra);existing=read(target);recomputed=read(verify);recomputed['created_UTC']=existing['created_UTC'];require(existing==recomputed,'Exact additive manifest differs on resume beyond helper-created timestamp');validate_manifest(existing);build=dict(checkproof,manifest_SHA256=sha(target),manifest_bytes=target.stat().st_size)
   else:build=merge_files(last,files['source-publication-receipt.json'],files['result-publication-receipt.json'],OUT/'M/result-publication.json',target,package_id=package,expected_previous_sha256=lastsha,extra_original_metadata=extra)
   validate_manifest(read(target));same_or_create(proofpath,build)if not proofpath.exists()else require(read(proofpath)['manifest_SHA256']==sha(target),'Existing merge build receipt SHA');pin(target);pin(proofpath);manifest_paths.append(target);build_proofs.append(build);last=target;lastsha=sha(target)
  identity=dict(schema='task1-terminal-fine-R5-transfer-identity-v1',repository='yoodohyun-codex-cloud/ngg-tis-task1',package_id=PACKAGE,previous_manifest_SHA256=PREVIOUS_SHA,metadata_commit=metadata['commit'],manifest_repo_relative_path=PUBLIC+'/'+last.name,manifest_SHA256=lastsha,manifest_bytes=last.stat().st_size,intermediate_manifests=[dict(repo_relative_path=PUBLIC+'/'+p.name,SHA256=sha(p),bytes=p.stat().st_size)for p in manifest_paths],scope_statuses=public_states,original_metadata_SHA256={label:{name:row['SHA256']for name,row in rows.items()}for label,rows in identities.items()},Windows_backup_complete=False,OneDrive_sync_verified=False,integrity_is_not_scientific_validation=True,hash_only_backup_claim=False,originals_deleted_or_overwritten=False,new_PDE_RHS=0,transfer_receipt_closure='The later T readback receipt remains separate; R5 remains FAILED and fine outcome is conditional. No self-referential manifest, full-convergence or Windows-backup claim')
  identity_path=OUT/'fineXY-R5-transfer-identity.json';same_or_create(identity_path,identity);pin(identity_path)
  # Validate the identity's path/string discipline with the same manifest checker.
  safe=read(last);safe['transfer_identity_validation_payload']=identity;validate_manifest(safe)
  tplan=dict(schema='task1-supported-Git-transport-plan-v1',repository='yoodohyun-codex-cloud/ngg-tis-task1',branch='codex/task1-cloud-restart-20261020',expected_parent=metadata['commit'],new_PDE_required=False,message='Publish additive R5-failure/fine-terminal manifests and transparent conditional transfer identity',required_result_receipt=str(OUT/'T/result-publication.json'),files={PUBLIC+'/'+p.name:file_plan(p)for p in manifest_paths+[identity_path]});transfer=publish('T',tplan)
  require(all(not(RUNS['r5_failed']/name).exists()for name in absent),'Recorded original R5 missing receipts changed; preserve and inspect before any success claim')
  guard();completed=dict(schema='task1-terminal-fine-R5-MT-completed-v1',metadata_commit=metadata['commit'],transfer_commit=transfer['commit'],manifest_repo_relative_path=PUBLIC+'/'+last.name,manifest_SHA256=lastsha,manifest_bytes=last.stat().st_size,scope_statuses=public_states,Windows_backup_complete=False,OneDrive_sync_verified=False,new_PDE_RHS=0,original_metadata_before_after_SHA_passed=True);same_or_create(OUT/'completed-transfer-identity.json',completed);receipt.update(status='fine_terminal_and_R5_failure_additive_manifests_published_readback_verified',metadata_commit=metadata['commit'],transfer_commit=transfer['commit'],completed_identity=completed);checkpoint('completed',metadata_commit=metadata['commit'],transfer_commit=transfer['commit'])
 except BaseException as error:
  receipt.update(error_type=type(error).__name__,error=str(error),failed_phase=state['phase'],blocker='Original bytes and exact M/T plans/workspaces/checkpoints preserved; no PDE or field work was run',resume_condition='Resolve the recorded metadata/resource/transport blocker, keep this exact source/input request and initial parent, then rerun the identical CLI with --resume; standard publisher resumes verify-only after push attempts');checkpoint('failed_preserved',error=str(error));raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
  for child,startticks in b.owned_descendants(pid,tick,dict(owned)).items():
   if child!=pid and b.live(child,startticks):
    try:os.kill(child,signal.SIGKILL)
    except ProcessLookupError:pass
  if state.get('process_audit')is not None:new(adir/'research-process-accounting.json',state['process_audit'])
  elapsed=time.monotonic()-started;ledger=budget.load_ledger();debit=max(0.,elapsed-git_wall);ledger['spent_seconds']+=debit;ledger['runs'].append(dict(run_id=OUT.name+'-attempt-'+str(attempt),stage='metadata_only_fine_terminal_R5_failure_transfer_supervision',seconds=debit,status=receipt['status'],Git_children_debited_separately=True,new_PDE_RHS=0));tmp=ROOT/'runtime'/('task1-budget-fine-R5-transfer-'+str(pid)+'.tmp');new(tmp,ledger);os.replace(tmp,ROOT/'runtime/task1-budget.json');receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,resources={key:value for key,value in state.items()if key.startswith('peak_')});new(adir/'receipt.json',receipt)
  for sig,handler in handlers.items():signal.signal(sig,handler)
  output_mutex.close()
  print(json.dumps(receipt,ensure_ascii=False,allow_nan=False))
if __name__=='__main__':main()
