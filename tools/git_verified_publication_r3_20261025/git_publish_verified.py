#!/usr/bin/env python3
"""Finite supported Git publication. No research execution or REST verification.

Existing HTTPS credentials/proxy/TLS are inherited unchanged. A fresh second
remote object database supplies every byte of readback. Resuming after a push
attempt never creates or pushes another commit. Optional comment failure cannot
invalidate a completed scientific publication receipt.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse,hashlib,json,os,re,signal,subprocess,threading,time
from contextlib import ExitStack
from pathlib import Path,PurePosixPath
ROOT=Path('/workspace/ngg-tis-task1');LEDGER=ROOT/'runtime/task1-budget.json'
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020'
URL='https://github.com/'+REPO+'.git';CAP=300;MAX_FILE=80*1024**2;MAX_OUTPUT=160*1024**2
sys.path.insert(0,str(ROOT/'tools'))
import task1_bounded_continuation as bounded
import task1_resource_policy as budget
import task1_execution_policy as execution

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def publication_action(state,head,parent):
 if 'commit'not in state:
  require(not state.get('push_attempted'),'Cannot recreate a commit after a push attempt')
  return 'prepare_commit'
 if state.get('push_attempted')or head==state['commit']:return 'verify_only'
 require(head==parent,'Remote changed before the only permitted push')
 return 'first_push'
def optional_comment_outcome(scientific_status,returncode):
 require(scientific_status=='published_readback_verified','Scientific proof must precede optional messaging')
 return dict(status=scientific_status,comment_status='posted'if returncode==0 else'pending')
def new(path,obj):
 with Path(path).open('x',encoding='utf-8')as stream:json.dump(obj,stream,ensure_ascii=False,allow_nan=False,indent=2)
def size(path):
 try:
  if path.is_file():return path.stat().st_size
  return sum(q.stat().st_size for q in path.rglob('*')if q.is_file())
 except FileNotFoundError:return 0

def owns_queue(pid):
 lock=ROOT/'.task1-queue-owner.lock';inode=lock.stat().st_ino;found=set()
 for fd in Path('/proc',str(pid),'fd').glob('*'):
  try:
   if fd.stat().st_ino!=inode:continue
   for line in Path('/proc',str(pid),'fdinfo',fd.name).read_text().splitlines():
    if line.startswith('lock:')and (' '+str(pid)+' ')in line:
     if ' POSIX 'in line:found.add('POSIX')
     if ' FLOCK 'in line:found.add('FLOCK')
  except OSError:pass
 return found=={'POSIX','FLOCK'}

def executed_script_argument(argv):
 """First actual Python script, never a later path-looking argument."""
 require(argv and Path(argv[0]).name.startswith('python'),'Queue parent must be a Python controller')
 index=1
 while index<len(argv)and argv[index].startswith('-'):
  if argv[index]=='--':index+=1;break
  require(argv[index]in('-B','-u','-E','-s','-S','-I','-O','-OO','-q','-R'),'Unsupported queue interpreter option; no -c/-m argument spoofing')
  index+=1
 require(index<len(argv),'Actual queue controller argument missing')
 return argv[index]

def validate_queue_identity(reg,pid,ticks,controller,controller_sha,publisher,publisher_sha):
 require(reg.get('schema')=='task1-finite-native-continuation-registration-v1','Explicit finite continuation registration required')
 require(type(reg.get('supervisor_pid'))is int and type(reg.get('proc_start_ticks'))is int and
  reg['supervisor_pid']==pid and reg['proc_start_ticks']==ticks,'Exact supervisor PID/startticks required')
 require(reg.get('controller_path')==controller and reg.get('controller_sha256')==controller_sha and
  re.fullmatch('[0-9a-f]{64}',controller_sha)is not None,'Actual executed controller path/source SHA mismatch')
 require(reg.get('publisher_path')==publisher and reg.get('publisher_sha256')==publisher_sha and
  re.fullmatch('[0-9a-f]{64}',publisher_sha)is not None,'Registered publisher must be this exact frozen source')
 return True

def task_registration_path(path):
 path=Path(path)
 require(path.is_absolute()and path==path.resolve()and path.is_file()and not path.is_symlink()and path.stat().st_size<=2*1024**2,'Canonical bounded immutable queue registration')
 require(path.is_relative_to(ROOT/'runtime')or(path.is_relative_to(Path('/dev/shm'))and len(path.parts)>3 and path.parts[3].startswith('task1-')),'Queue registration must be task-owned or repository runtime metadata')
 return path

def actual_parent_controller(pid):
 argv=[item.decode()for item in Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0')if item]
 require(Path('/proc',str(pid),'exe').resolve().name.startswith('python'),'Actual parent executable must be Python')
 argument=executed_script_argument(argv);cwd=Path('/proc',str(pid),'cwd').resolve();controller=(cwd/argument).resolve()
 require(controller.is_file()and not controller.is_symlink()and controller==Path(controller).absolute(),'Canonical actual queue source')
 return controller

def authenticate_queue_parent(registration,publisher,publisher_sha):
 path=task_registration_path(registration);digest=sha(path);reg=read(path);pid=os.getppid();ticks=bounded.ticks(pid)
 controller=actual_parent_controller(pid);controller_sha=sha(controller)
 validate_queue_identity(reg,pid,ticks,str(controller),controller_sha,str(publisher),publisher_sha)
 require(bounded.live(pid,ticks)and owns_queue(pid),'Actual direct parent must hold both FLOCK and POSIX queue locks')
 return dict(pid=pid,proc_start_ticks=ticks,controller_path=str(controller),controller_sha256=controller_sha,
  publisher_path=str(publisher),publisher_sha256=publisher_sha,registration_path=str(path),registration_sha256=digest)

def guard_queue_parent(lease):
 require(os.getppid()==lease['pid']and bounded.live(lease['pid'],lease['proc_start_ticks'])and owns_queue(lease['pid']),'Delegated actual queue parent identity/dual locks changed')
 require(sha(task_registration_path(lease['registration_path']))==lease['registration_sha256'],'Immutable queue registration changed')
 require(str(actual_parent_controller(lease['pid']))==lease['controller_path']and sha(lease['controller_path'])==lease['controller_sha256'],'Actual queue command/source changed')
 require(sha(lease['publisher_path'])==lease['publisher_sha256'],'Registered publisher source changed')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--plan',required=True);parser.add_argument('--output',required=True);parser.add_argument('--queue-registration');args=parser.parse_args()
 planpath=Path(args.plan);out=Path(args.output)
 require(planpath.is_absolute()and planpath==planpath.resolve()and planpath.is_file()and not planpath.is_symlink()and planpath.stat().st_size<8*1024**2,'Canonical bounded explicit publication plan')
 require(out.is_absolute()and out==out.absolute()and out.parent==Path('/dev/shm')and out.name.startswith('task1-'),'Unique task-owned tmpfs output')
 plan=read(planpath);plan_sha=sha(planpath);source_sha=sha(__file__)
 require(plan.get('schema')=='task1-supported-Git-transport-plan-v1'and plan.get('repository')==REPO and plan.get('branch')==BRANCH and plan.get('new_PDE_required')is False,'Exact approved non-PDE topic publication plan')
 parent=plan['expected_parent'];require(re.fullmatch('[0-9a-f]{40}',parent)is not None,'Expected parent Git identity')
 require(isinstance(plan['message'],str)and 0<len(plan['message'])<=16000 and '\0'not in plan['message'],'Bounded commit message')
 destination=Path(plan['required_result_receipt'])
 require(destination.is_absolute()and destination.parent==destination.parent.resolve()and destination.parent.is_dir()and destination.name=='result-publication.json','Canonical task result receipt')
 files={}
 for target,item in plan['files'].items():
  name=PurePosixPath(target)
  require(target.startswith(('data-native/','data-manufactured/','docs/','tools/'))and str(name)==target and not name.is_absolute()and '..'not in name.parts and '.git'not in name.parts and not any(c in target for c in('\0','\n','\r','\t','\\')),'Canonical approved research repository target')
  path=Path(item['local_path']);require(path.is_absolute()and path==path.resolve()and path.is_file()and not path.is_symlink(),'Canonical user-owned publication input')
  require(path.is_relative_to(Path('/workspace'))or(path.is_relative_to(Path('/dev/shm'))and path.parts[3].startswith('task1-')),'Task-owned local publication input')
  require(type(item['bytes'])is int and 0<=item['bytes']<=MAX_FILE and path.stat().st_size==item['bytes']and sha(path)==item['SHA256'],'Exact approved file SHA/bytes within80MiB supported format')
  files[target]=dict(local_path=str(path),SHA256=item['SHA256'],bytes=item['bytes'])
 require(files,'Nonempty explicit publication files')
 active=execution.load_active_policy();limits=execution.resolve_limits(active);configured=execution.configure_process(limits);execution_refs=execution.execution_policy_refs(active)
 with ExitStack()as locks:
  queue_parent=None
  try:locks.enter_context(bounded.dual_lock(ROOT/'.task1-queue-owner.lock'))
  except BlockingIOError:
   require(args.queue_registration is not None,'Busy queue requires explicit immutable --queue-registration; old r2 remains available for its old controller')
   queue_parent=authenticate_queue_parent(args.queue_registration,Path(__file__).resolve(),source_sha)
  locks.enter_context(bounded.dual_lock(ROOT/'.task1-loop.lock'));locks.enter_context(bounded.dual_lock(ROOT/'.task1-execution.lock'))
  ledger=budget.load_ledger();budget.require_time_budget(ledger,CAP)
  if out.exists():
   require(out==out.resolve()and not out.is_symlink(),'Canonical preserved output')
   registration=read(out/'registration.json');require(registration['plan_SHA256']==plan_sha and registration['source_SHA256']==source_sha,'Resume exact same frozen plan/source')
  else:
   out.mkdir();(out/'logs').mkdir();(out/'tmp').mkdir();(out/'checkpoints').mkdir()
   new(out/'registration.json',dict(schema='task1-Git-only-publication-v1',plan_path=str(planpath),plan_SHA256=plan_sha,source_SHA256=source_sha,expected_parent=parent,
    repository=REPO,branch=BRANCH,limits=limits,configured=configured,execution_policy_refs=execution_refs,queue_lock_delegated_to_parent=queue_parent,new_PDE=0,stage_cap_seconds=CAP))
  attempt=len(list(out.glob('attempt-start-*.json')))+1
  new(out/('attempt-start-'+str(attempt)+'.json'),dict(started_utc=bounded.now(),plan_SHA256=plan_sha,source_SHA256=source_sha))
  statepath=out/'transport-state.json';state=read(statepath)if statepath.exists()else dict(phase='registered',push_attempted=False)
  pid=os.getpid();ticks=bounded.ticks(pid);owned={pid:ticks};started=time.monotonic();deadline=started+CAP;stop=threading.Event();resources=dict(peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);calls=0
  receipt=dict(schema='task1-Git-only-attempt-v1',status='failed_preserved',attempt=attempt,started_utc=bounded.now(),stage_cap_seconds=CAP,new_PDE=0,REST_required=False,cumulative_time_unlimited=ledger.get('cumulative_time_unlimited')is True)
  def checkpoint(phase,**fields):
   state.update(phase=phase,**fields);entry=out/'checkpoints'/(str(time.time_ns())+'-'+phase+'.json');new(entry,state)
   temporary=out/('state-'+str(time.time_ns())+'.new')
   with temporary.open('x',encoding='utf-8')as stream:json.dump(state,stream,ensure_ascii=False,allow_nan=False,separators=(',',':'));stream.flush();os.fsync(stream.fileno())
   os.replace(temporary,statepath)
  def guard():
   require(time.monotonic()<deadline,'Finite300s Git publication deadline')
   live=bounded.owned_descendants(pid,ticks,dict(owned));rss=sum(bounded.rss(p)for p,t in live.items()if bounded.live(p,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
   resources.update(peak_RSS=max(resources['peak_RSS'],rss),peak_owned_tmpfs=max(resources['peak_owned_tmpfs'],tmp),peak_accounted=max(resources['peak_accounted'],rss+tmp));require(rss+tmp<=limits['total_memory_bytes'],'Approved aggregate RSS plus all task tmpfs cap')
   require(sha(planpath)==plan_sha and sha(__file__)==source_sha,'Frozen plan/source changed')
   for path,digest in execution_refs.items():require(sha(path)==digest,'Execution policy changed')
   if queue_parent:guard_queue_parent(queue_parent)
  def interrupt(sig,frame):raise TimeoutError(resources.get('error','Finite Git publication interrupted'))
  def monitor():
   while not stop.wait(1):
    try:guard()
    except BaseException as error:resources['error']=str(error);os.kill(pid,signal.SIGTERM);return
  handlers={s:signal.getsignal(s)for s in(signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
  for s in handlers:signal.signal(s,interrupt)
  signal.setitimer(signal.ITIMER_REAL,CAP);thread=threading.Thread(target=monitor,daemon=True);thread.start()
  env=dict(os.environ,TMPDIR=str(out/'tmp'),GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never',GIT_AUTHOR_NAME='Codex Research',GIT_AUTHOR_EMAIL='codex@openai.com',GIT_COMMITTER_NAME='Codex Research',GIT_COMMITTER_EMAIL='codex@openai.com')
  for key in('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_COMMON_DIR'):env.pop(key,None)
  def command(argv,body=None,optional=False):
   nonlocal calls
   # Same existing gh credential transport used by prior successful publications.
   # Per-command selection only; no Git/gh credential or security configuration write.
   if argv and str(argv[0])=='git':argv=['git','-c','credential.helper=!gh auth git-credential',*argv[1:]]
   calls+=1;guard();child=subprocess.Popen([str(a)for a in argv],cwd=ROOT,stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env=env);owned[child.pid]=bounded.ticks(child.pid)
   try:
    stdout,stderr=child.communicate(input=body,timeout=max(.01,deadline-time.monotonic()));require(len(stdout)<=MAX_OUTPUT and len(stderr)<=4*1024**2,'Bounded child Git response')
    if child.returncode:
     new(out/'logs'/('failed-'+str(attempt)+'-'+str(calls)+'.json'),dict(argv=argv,returncode=child.returncode,stderr=stderr.decode(errors='replace')[:12000],stdout_bytes=len(stdout),stdout_SHA256=hashlib.sha256(stdout).hexdigest()))
     if optional:return None
     raise RuntimeError('Git command failed; see preserved command log '+str(calls))
    if stderr:new(out/'logs'/('stderr-'+str(attempt)+'-'+str(calls)+'.json'),dict(argv=argv,stderr=stderr.decode(errors='replace')[:12000]))
    return stdout
   finally:
    if child.poll()is None:child.kill();child.wait(timeout=3)
  def git(directory,*argv,body=None,optional=False):return command(['git','-c','gc.auto=0','-c','pack.threads='+str(limits['cpu_limit']),'-c','pack.window=0','-c','pack.compression=1','--git-dir='+str(directory),*argv],body,optional)
  def remote_head():
   raw=command(['git','ls-remote','--refs',URL,'refs/heads/'+BRANCH]).decode().splitlines();require(len(raw)==1,'One remote topic branch');value,ref=raw[0].split('\t');require(ref=='refs/heads/'+BRANCH and re.fullmatch('[0-9a-f]{40}',value),'Exact remote branch identity');return value
  try:
   guard();writer=out/'writer.git'
   if 'commit'not in state:
    require(not state['push_attempted']and remote_head()==parent,'Expected parent changed before commit; no mutation')
    if not(writer/'config').is_file():git(writer,'init','--bare',str(writer));git(writer,'remote','add','origin',URL)
    else:require(git(writer,'remote','get-url','origin').decode().strip()==URL,'Preserved writer remote differs')
    git(writer,'fetch','--no-tags','--depth=1','--filter=blob:none','origin','refs/heads/'+BRANCH)
    require(git(writer,'rev-parse','FETCH_HEAD').decode().strip()==parent,'Fetched parent mismatch');git(writer,'read-tree','FETCH_HEAD')
    records=[]
    for target,item in files.items():
     path=Path(item['local_path']);require(path.stat().st_size==item['bytes']and sha(path)==item['SHA256'],'Local publication bytes changed')
     blob=git(writer,'hash-object','-w','--no-filters',str(path)).decode().strip();require(re.fullmatch('[0-9a-f]{40}',blob),'Local Gitblob identity')
     git(writer,'update-index','--add','--cacheinfo','100644,'+blob+','+target);records.append(dict(target=target,Git_blob_SHA=blob,**item))
    tree=git(writer,'write-tree','--missing-ok').decode().strip();commit=git(writer,'commit-tree',tree,'-p',parent,body=(plan['message']+'\n').encode()).decode().strip()
    checkpoint('commit_prepared',commit=commit,tree=tree,parent=parent,records=records,push_attempted=False)
   commit=state['commit'];tree=state['tree'];records=state['records'];head=remote_head();action=publication_action(state,head,parent)
   if head==commit:checkpoint('remote_ref_confirmed',push_attempted=True,push_confirmed=True)
   elif action=='first_push':
    require(head==parent,'Remote advanced before first push; preserve commit, no force')
    checkpoint('push_attempt_recorded',push_attempted=True,push_confirmed=False)
    try:git(writer,'push','origin',commit+':refs/heads/'+BRANCH)
    except BaseException:
     checkpoint('push_outcome_unknown',push_attempted=True,push_confirmed=False)
     raise
    checkpoint('push_server_acknowledged',push_attempted=True,push_confirmed=True)
    require(remote_head()==commit,'Remote branch advanced after acknowledged push; resume verification only')
    checkpoint('remote_ref_confirmed',push_confirmed=True)
   else:
    require(state.get('push_confirmed')or head==commit,'Previous push outcome unresolved; no duplicate push permitted')
   # A NEW second bare repository is populated only over the remote Git protocol.
   verifier=out/('verify-'+str(attempt)+'.git');require(not verifier.exists(),'Preserve previous verification attempts')
   command(['git','clone','--bare','--no-local','--no-tags','--depth=1','--filter=blob:none','--single-branch','--branch',BRANCH,URL,str(verifier)])
   require(not(verifier/'objects/info/alternates').exists(),'Fresh verifier may not share writer object storage')
   git(verifier,'fetch','--no-tags','--depth=1','--filter=blob:none','origin',commit)
   require(git(verifier,'rev-parse','FETCH_HEAD').decode().strip()==commit,'Fresh remote commit identity')
   commit_headers=git(verifier,'cat-file','-p',commit).split(b'\n\n',1)[0].decode().splitlines()
   require([line[7:]for line in commit_headers if line.startswith('parent ')]==[parent],'Remote commit exact parent header, including shallow fetches')
   require(git(verifier,'rev-parse',commit+'^{tree}').decode().strip()==tree,'Remote exact tree')
   observed_head=remote_head()
   if observed_head!=commit:
    git(verifier,'fetch','--no-tags','--depth=64','--filter=blob:none','origin','refs/heads/'+BRANCH)
    require(git(verifier,'rev-parse','FETCH_HEAD').decode().strip()==observed_head,'Remote branch changed during ancestry check')
    require(git(verifier,'merge-base','--is-ancestor',commit,observed_head,optional=True)is not None,'Published commit not proven on current branch; no mutation')
   raw_tree=git(verifier,'ls-tree','-r','-z',commit);entries={}
   for row in raw_tree.split(b'\0'):
    if not row:continue
    info,name=row.split(b'\t',1);mode,kind,blob=info.decode().split();entries[name.decode()]=(mode,kind,blob)
   proof={}
   for index,item in enumerate(records):
    require(entries.get(item['target'])==('100644','blob',item['Git_blob_SHA']),'Fresh remote tree file identity')
    raw=git(verifier,'cat-file','blob',item['Git_blob_SHA'])
    require(len(raw)==item['bytes']and hashlib.sha256(raw).hexdigest()==item['SHA256'],'Full fresh remote Git object SHA/bytes readback')
    value=dict(SHA256=item['SHA256'],bytes=item['bytes'],Git_blob_SHA=item['Git_blob_SHA'],readback_passed=True,proof_kind='fresh_second_remote_Git_object_database_full_readback')
    proof[item['target']]=value;new(out/'checkpoints'/('verified-'+str(attempt)+'-'+str(index)+'.json'),dict(target=item['target'],proof=value,remote_commit=commit,verifier=str(verifier)));del raw
   result=dict(status='published_readback_verified',commit=commit,files=proof,transport='supported_Git_HTTPS_only',verification='fresh_separate_remote_blobless_fetch_then_ls_tree_and_cat_file; no REST',expected_parent=parent,tree=tree,remote_branch_head_verified=observed_head,new_PDE=0)
   if destination.exists():
    old=read(destination);require(old['status']=='published_readback_verified'and old['commit']==commit and all(old['files'][k]['SHA256']==v['SHA256']and old['files'][k]['bytes']==v['bytes']for k,v in proof.items()),'Existing result receipt differs; never overwrite')
   else:new(destination,result)
   checkpoint('scientific_publication_verified',push_confirmed=True,result_receipt=str(destination),result_receipt_SHA256=sha(destination))
   receipt.update(status='published_readback_verified',result_commit=commit,result_receipt=str(destination),files_verified=len(proof),REST_required=False)
   body=plan.get('comment_body')
   if body:
    try:
     require(isinstance(body,str)and len(body)<=32000,'Bounded optional PR2 comment')
     attempted=out/'comment-attempted.json'
     if not attempted.exists():
      new(attempted,dict(attempted_utc=bounded.now(),body_SHA256=hashlib.sha256(body.encode()).hexdigest(),unknown_outcome_must_not_be_retried=True))
      response=command(['gh','api','repos/'+REPO+'/issues/2/comments','-X','POST','--input','-'],json.dumps(dict(body=body)).encode(),optional=True)
      if response is not None:new(out/'comment-result.json',json.loads(response));receipt.update(optional_comment_outcome(receipt['status'],0))
      else:new(out/'comment-pending.json',dict(status='scientific_publication_succeeded_comment_pending',body=body,reason='Optional comment command failed; no blind POST retry'));receipt.update(optional_comment_outcome(receipt['status'],1))
     else:receipt['comment_status']='previously_attempted_no_POST_retry'
    except BaseException as comment_error:
     # Scientific receipt is already durable; ancillary REST/auth/time failures
     # cannot revoke it or cause a duplicate scientific commit/push.
     signal.setitimer(signal.ITIMER_REAL,0);stop.set()
     receipt.update(optional_comment_outcome(receipt['status'],1),comment_error=str(comment_error))
     try:new(out/('comment-pending-attempt-'+str(attempt)+'.json'),dict(status='scientific_publication_succeeded_comment_pending',body=body,error=str(comment_error),no_blind_POST_retry=True))
     except OSError as pending_error:receipt['comment_pending_record_error']=str(pending_error)
  except BaseException as error:
   receipt.update(error_type=type(error).__name__,error=str(error),recorded_commit=state.get('commit'),push_attempted=state.get('push_attempted'),push_confirmed=state.get('push_confirmed'))
   raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   for p,t in bounded.owned_descendants(pid,ticks,dict(owned)).items():
    if p!=pid and bounded.live(p,t):
     try:os.kill(p,signal.SIGKILL)
     except ProcessLookupError:pass
   elapsed=time.monotonic()-started;ledger=budget.load_ledger();ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=out.name,stage='supported_Git_only_publication',seconds=elapsed,status=receipt['status'],new_PDE=0))
   temporary=LEDGER.with_name('task1-budget-git-verified-'+str(pid)+'.tmp')
   with temporary.open('x')as stream:json.dump(ledger,stream,ensure_ascii=False,allow_nan=False,separators=(',',':'))
   os.replace(temporary,LEDGER);receipt.update(finished_utc=bounded.now(),elapsed_seconds=elapsed,remaining_approved_seconds=budget.remaining_seconds(ledger),resources=resources)
   new(out/('attempt-'+str(attempt)+'.json'),receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False,allow_nan=False))
if __name__=='__main__':main()
