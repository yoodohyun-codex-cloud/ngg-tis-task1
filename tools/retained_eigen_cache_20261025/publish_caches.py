#!/usr/bin/env python3
"""Finite Git Database cache retention; no PDE, local Git repository or Q copy.

The root runs this only after numerical work. Existing gh authentication and
network configuration are inherited. All operational evidence stays private;
only the whitelisted cache chunks, sanitized indexes and tool source enter Git.
A failed/unknown mutation is never retried automatically, including on resume.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,os,re,shutil,signal,subprocess,sys,threading,time
from contextlib import ExitStack
from pathlib import Path,PurePosixPath

ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-transfer-20261025/cache-publisher')
REPO='yoodohyun-codex-cloud/ngg-tis-task1'
BRANCH='codex/task1-cloud-restart-20261020'
PREFIX='data-native/retained-eigen-cache-20261025'
TOOL_PREFIX='tools/retained_eigen_cache_20261025'
MAX_CHUNK=32*1024**2
MAX_STDOUT=128*1024**2
BLOB_STDOUT=96*1024**2
MAX_STDERR=1024**2
MAX_MANIFEST=2*1024**2
CACHE_INPUTS={
 'xy100':(Path('/dev/shm/task1-layer-dtn-20261025-run/eigen-cache/manifest.json'),7860),
 'xy102':(Path('/dev/shm/task1-layer-dtn-xy102-20261025-run/eigen-cache/manifest.json'),8184),
}
SOURCE_NAMES=('publish_caches.py','test_cache_paths.py','test_cache_manifests.py')


def require(ok,message):
 if not ok:raise ValueError(message)
def sha_bytes(raw):return hashlib.sha256(raw).hexdigest()
def read_json(path):return json.loads(Path(path).read_bytes())
def new_json(path,obj):
 with Path(path).open('x',encoding='utf-8')as stream:
  json.dump(obj,stream,ensure_ascii=False,allow_nan=False,indent=2)
 os.chmod(path,0o600)
def canonical_target(target):
 require(isinstance(target,str),'Repository target must be a string')
 p=PurePosixPath(target)
 require(str(p)==target and not p.is_absolute()and '..'not in p.parts and '.git'not in p.parts and not any(c in target for c in('\x00','\n','\r','\t','\\')), 'Canonical repository-relative target required')
 require(target.startswith((PREFIX+'/',TOOL_PREFIX+'/')),'Target outside retained caches/tool source')
 return target

def validate_manifest(obj,logical,path,*,expected_n=None):
 """Pure structural validation; no filesystem access or chunk hashing."""
 require(logical in CACHE_INPUTS,'Exactly the approved logical caches')
 path=Path(path)
 n=CACHE_INPUTS[logical][1]if expected_n is None else expected_n
 require(type(n)is int and n>0,'Positive declared square shape')
 require(obj.get('schema')=='task1-local-recomputable-eigen-cache-v1'and obj.get('shape')==[n,n]and obj.get('dtype')=='<f8'and obj.get('order')=='F'and obj.get('local_readback_passed')is True,'Exact locally verified real Fortran cache manifest')
 require(isinstance(obj.get('chunks'),list)and 0<len(obj['chunks'])<=64,'Bounded declared chunk list')
 at=0;rows=[];seen=set()
 for row in obj['chunks']:
  require(type(row.get('column_start'))is int and type(row.get('column_stop'))is int and row['column_start']==at and at<row['column_stop']<=n,'Ordered disjoint complete column chunks')
  stop=row['column_stop'];name='Q-cols-%05d-%05d.f64le'%(at,stop);p=Path(row['path'])
  require(p.is_absolute()and p==path.parent/name and p.name==name and str(p)==row['path']and '..'not in p.parts,'Exact original cache chunk basename and directory')
  require(row.get('row_start')==0 and row.get('row_stop')==n and row.get('dtype')=='<f8'and row.get('order')=='F'and row.get('local_readback_passed')is True,'Exact native column-major chunk ABI')
  require(type(row.get('bytes'))is int and row['bytes']==n*(stop-at)*8 and 0<row['bytes']<=MAX_CHUNK and isinstance(row.get('SHA256'),str)and re.fullmatch('[0-9a-f]{64}',row['SHA256'])is not None,'Bounded original byte count and SHA256')
  target=canonical_target(PREFIX+'/'+logical+'/'+name);require(target not in seen,'Unique target');seen.add(target)
  rows.append(dict(logical_cache=logical,path=str(p),basename=name,repo_relative_path=target,bytes=row['bytes'],SHA256=row['SHA256'],row_start=0,row_stop=n,column_start=at,column_stop=stop))
  at=stop
 require(at==n and sum(r['bytes']for r in rows)==n*n*8,'Complete unmodified square cache coverage')
 return rows

def sanitized_index(obj,logical,rows):
 """Whitelist only portable reconstruction metadata, never local path fields."""
 return dict(schema='task1-retained-eigen-cache-index-v1',logical_cache=logical,shape=list(obj['shape']),dtype='<f8',order='F',
  chunks=[{key:row[key]for key in('basename','repo_relative_path','bytes','SHA256','row_start','row_stop','column_start','column_stop')}for row in rows])

def stat_token(path):
 p=Path(path);s=p.stat()
 require(p.is_file()and not p.is_symlink()and p==p.resolve(),'Canonical original file, never a symlink')
 return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns]
def file_sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def size(path):
 try:
  if path.is_file():return path.stat().st_size
  return sum(p.stat().st_size for p in path.rglob('*')if p.is_file())
 except FileNotFoundError:return 0

def main():
 sys.dont_write_bytecode=True
 parser=argparse.ArgumentParser()
 parser.add_argument('--parent',required=True)
 parser.add_argument('--output',required=True)
 parser.add_argument('--seconds',type=int,choices=(600,900),default=900)
 parser.add_argument('--resume',action='store_true',help='Reuse exact immutable plan and verified blobs; never repeat an uncertain mutation')
 args=parser.parse_args();out=Path(args.output)
 require(re.fullmatch('[0-9a-f]{40}',args.parent)is not None,'Explicit parent commit after fine CEM publication')
 require(Path(__file__).resolve()==SOURCE/'publish_caches.py','Exact root-reviewed publisher source')
 require(shutil.which('gh')and shutil.which('setpriv'),'Existing gh/setpriv required; no installation or configuration change')
 require(out.is_absolute()and out.parent==Path('/dev/shm')and out.name.startswith('task1-')and '..'not in out.parts,'Private task-owned tmpfs output')
 sys.path.insert(0,str(ROOT/'tools'))
 import task1_bounded_continuation as bounded
 import task1_execution_policy as execution
 import task1_resource_policy as budget
 ledger_path=ROOT/'runtime/task1-budget.json'
 active=execution.load_active_policy();limits=execution.resolve_limits(active);configured=execution.configure_process(limits)
 policy_refs=execution.execution_policy_refs(active)
 with ExitStack()as locks:
  for name in('.task1-queue-owner.lock','.task1-loop.lock','.task1-execution.lock'):locks.enter_context(bounded.dual_lock(ROOT/name))
  ledger=budget.load_ledger(ledger_path);budget.require_time_budget(ledger,args.seconds)
  require(ledger.get('cumulative_time_unlimited')is True,'Approved unlimited cumulative time with finite transfer cap')
  manifests={};files=[];small_data={};source_refs={};input_refs={};tokens={}
  for logical,(path,n)in CACHE_INPUTS.items():
   require(path.is_file()and path==path.resolve()and not path.is_symlink()and path.stat().st_size<=MAX_MANIFEST,'Canonical bounded original cache manifest')
   raw=path.read_bytes();obj=json.loads(raw);rows=validate_manifest(obj,logical,path)
   input_refs[str(path)]=sha_bytes(raw);manifests[logical]=obj
   for row in rows:tokens[row['path']]=stat_token(row['path']);require(tokens[row['path']][2]==row['bytes'],'Original declared chunk size');files.append(row)
   target=canonical_target(PREFIX+'/'+logical+'/index.json');small_data[target]=(json.dumps(sanitized_index(obj,logical,rows),ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()
  for name in SOURCE_NAMES:
   p=SOURCE/name;require(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size<=MAX_MANIFEST,'Reviewed bounded tool source')
   raw=p.read_bytes();source_refs[str(p)]=sha_bytes(raw);small_data[canonical_target(TOOL_PREFIX+'/'+name)]=raw
  helper_refs={str(ROOT/'tools'/name):file_sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  registration=dict(schema='task1-finite-cache-REST-publication-registration-v1',expected_parent=args.parent,repository=REPO,branch=BRANCH,source_sha256=source_refs,manifest_sha256=input_refs,
   original_file_stat=tokens,declared_chunks=files,public_small_files={k:dict(bytes=len(v),SHA256=sha_bytes(v))for k,v in small_data.items()},helper_sha256=helper_refs,
   execution_policy_refs=policy_refs,limits=limits,configured=configured,finite_attempt_seconds=args.seconds,max_blob_bytes=MAX_CHUNK,max_stdout_bytes=MAX_STDOUT,blob_stdout_limit_bytes=BLOB_STDOUT,new_PDE=0,originals_modified=False)
  if out.exists():
   require(args.resume and out==out.resolve()and not out.is_symlink(),'Existing transfer evidence requires explicit exact resume')
   old=read_json(out/'registration.json')
   # Visible environment metadata may evolve; frozen effective limits/policy do not.
   for key in('expected_parent','repository','branch','source_sha256','manifest_sha256','original_file_stat','declared_chunks','public_small_files','helper_sha256','execution_policy_refs','finite_attempt_seconds'):
    require(old[key]==registration[key],'Resume exact original transfer registration: '+key)
   for key in('cpu_limit','total_memory_bytes','java_heap_bytes','blas_threads'):require(old['limits'][key]==limits[key],'Resume same resource limits')
  else:
   require(not args.resume,'No existing evidence to resume');out.mkdir(mode=0o700);(out/'checkpoints').mkdir(mode=0o700);(out/'private-errors').mkdir(mode=0o700)
   new_json(out/'registration.json',registration)
  attempt=1+len(list(out.glob('attempt-*.json')));statepath=out/'transport-state.json';state=read_json(statepath)if statepath.is_file()else dict(schema='task1-cache-REST-private-state-v1',verified={},pending_mutation=None)
  pid=os.getpid();ticks=bounded.ticks(pid);owned={pid:ticks};start=time.monotonic();deadline=start+args.seconds;stop=threading.Event();mutex=threading.RLock();calls=0;sequence=0
  resources=dict(peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);receipt=dict(schema='task1-cache-REST-private-attempt-v1',status='failed_preserved',attempt=attempt,started_utc=bounded.now(),pid=pid,proc_start_ticks=ticks,new_PDE=0,originals_modified=False)
  frozen_registration_sha=file_sha(out/'registration.json')
  def checkpoint(phase,**extra):
   nonlocal sequence
   with mutex:
    sequence+=1;state.update(phase=phase,**extra)
    item=dict(state,updated_utc=bounded.now(),attempt=attempt,pid=pid,proc_start_ticks=ticks)
    new_json(out/'checkpoints'/('%03d-%04d-%s.json'%(attempt,sequence,phase)),item)
    temporary=out/('state-%d-%d.new'%(attempt,sequence));new_json(temporary,state);os.replace(temporary,statepath)
  def guard():
   require(time.monotonic()<deadline,'Finite cache publication deadline')
   require(not(out/'STOP').exists(),'Explicit transfer STOP marker')
   live=bounded.owned_descendants(pid,ticks,dict(owned));owned.update(live);rss=sum(bounded.rss(p)for p,t in live.items()if bounded.live(p,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
   resources.update(peak_RSS=max(resources['peak_RSS'],rss),peak_owned_tmpfs=max(resources['peak_owned_tmpfs'],tmp),peak_accounted=max(resources['peak_accounted'],rss+tmp));require(rss+tmp<=limits['total_memory_bytes'],'Approved aggregate RSS plus ALLtask1tmpfs cap')
   for p,h in{**source_refs,**input_refs,**helper_refs,**policy_refs}.items():require(file_sha(p)==h,'Frozen source/manifest/policy changed')
   require(file_sha(out/'registration.json')==frozen_registration_sha,'Private registration changed')
   for p,token in tokens.items():require(stat_token(p)==token,'Original cache stat changed')
  def interrupt(sig,frame):raise TimeoutError(resources.get('error','Finite transfer interrupted'))
  def monitor():
   while not stop.wait(.25):
    try:guard()
    except BaseException as error:resources['error']=str(error);os.kill(pid,signal.SIGTERM);return
  handlers={s:signal.getsignal(s)for s in(signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
  for sig in handlers:signal.signal(sig,interrupt)
  signal.setitimer(signal.ITIMER_REAL,args.seconds);thread=threading.Thread(target=monitor,daemon=True);thread.start()
  def command(method,endpoint,body=None):
   """Exact failed responses private; no request payload or credentials logged."""
   nonlocal calls
   calls+=1;guard();argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
   if body is not None:argv+=['--input','-']
   child=subprocess.Popen(['setpriv','--pdeathsig','KILL',*argv],cwd=ROOT,stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
   owned[child.pid]=bounded.ticks(child.pid)
   try:
    stdout,stderr=child.communicate(input=body,timeout=max(.01,min(90.,deadline-time.monotonic())))
    require(len(stdout)<=BLOB_STDOUT<=MAX_STDOUT and len(stderr)<=MAX_STDERR,'Predeclared API response byte bounds')
    if child.returncode:
     prefix=out/'private-errors'/('%03d-%04d'%(attempt,calls))
     for suffix,data in(('.stdout',stdout),('.stderr',stderr)):
      with Path(str(prefix)+suffix).open('xb')as stream:stream.write(data)
      os.chmod(str(prefix)+suffix,0o600)
     new_json(str(prefix)+'.json',dict(method=method,endpoint=endpoint,returncode=child.returncode,stdout_bytes=len(stdout),stderr_bytes=len(stderr),stdout_SHA256=sha_bytes(stdout),stderr_SHA256=sha_bytes(stderr),request_body_bytes=0 if body is None else len(body),request_body_SHA256=None if body is None else sha_bytes(body)))
    return child.returncode,stdout,stderr
   finally:
    if child.poll()is None:child.kill();child.wait(timeout=3)
  def api(method,endpoint,obj=None,*,body=None,allow404=False):
   if obj is not None:require(body is None,'One request representation');body=json.dumps(obj,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
   code,raw,error=command(method,endpoint,body)
   if code:
    if allow404:
     try:detail=json.loads(raw)
     except(ValueError,UnicodeError):detail={}
     if str(detail.get('status'))=='404'and detail.get('message')=='Not Found'and re.search(rb'HTTP\s+404',error):return None
    raise RuntimeError('Git Database API failed; exact response retained privately; no mutation retry')
   try:return json.loads(raw)
   except(ValueError,UnicodeError)as e:raise RuntimeError('Unexpected API JSON; no mutation retry')from e
  def head():
   result=api('GET','git/ref/heads/'+BRANCH);value=result['object']['sha'];require(re.fullmatch('[0-9a-f]{40}',value)is not None,'Exact branch Git identity');return value
  def original_bytes(item):
   p=Path(item['path']);require(stat_token(p)==tokens[str(p)],'Unchanged original cache before read');raw=p.read_bytes()
   require(len(raw)==item['bytes']<=MAX_CHUNK and sha_bytes(raw)==item['SHA256'],'Original root-declared chunk SHA/bytes');require(stat_token(p)==tokens[str(p)],'Unchanged original cache after read');return raw
  def git_identity(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
  def verify_blob(record,expected):
   require(record['sha']==expected['Git_blob_SHA']and record.get('encoding')=='base64'and record.get('size',expected['bytes'])==expected['bytes'],'Exact Git blob identity/encoding/size')
   decoded=base64.b64decode(record['content']);require(len(decoded)==expected['bytes']and sha_bytes(decoded)==expected['SHA256']and git_identity(decoded)==expected['Git_blob_SHA'],'Full GET decoded blob SHA256/bytes/GitSHA readback')
  def retain_blob(target,item=None,small=None):
   canonical_target(target)
   if item is not None:
    raw=original_bytes(item);expected=dict(bytes=item['bytes'],SHA256=item['SHA256'],Git_blob_SHA=git_identity(raw));del raw
   else:
    require(small is not None and len(small)<=MAX_MANIFEST,'Bounded approved source/index bytes');expected=dict(bytes=len(small),SHA256=sha_bytes(small),Git_blob_SHA=git_identity(small))
   prior=state['verified'].get(target)
   if prior is not None:
    require(prior==expected,'Previously verified exact blob identity');return
   checkpoint('blob_identity_declared',current_target=target,current_blob=expected)
   record=api('GET','git/blobs/'+expected['Git_blob_SHA'],allow404=True)
   pending=state.get('pending_mutation')
   if record is None:
    require(pending is None,'Previously attempted mutation has unresolved absence; explicit root recovery required, no POST retry')
    raw=original_bytes(item)if item is not None else small
    require(git_identity(raw)==expected['Git_blob_SHA']and sha_bytes(raw)==expected['SHA256'],'Exact bytes again before the only blob POST')
    encoded=base64.b64encode(raw).decode('ascii');body=json.dumps(dict(content=encoded,encoding='base64'),separators=(',',':')).encode();del encoded,raw
    checkpoint('blob_POST_attempted',pending_mutation=dict(kind='blob_POST',target=target,Git_blob_SHA=expected['Git_blob_SHA']))
    created=api('POST','git/blobs',body=body);del body
    require(created['sha']==expected['Git_blob_SHA'],'Created exact deterministic Git blob')
    record=api('GET','git/blobs/'+expected['Git_blob_SHA'])
   elif pending is not None:require(pending==dict(kind='blob_POST',target=target,Git_blob_SHA=expected['Git_blob_SHA']),'Resolve only the exact pending mutation')
   verify_blob(record,expected);del record
   state['verified'][target]=expected;checkpoint('blob_full_GET_readback_verified',pending_mutation=None,current_target=target)
  def mutate_once(kind,endpoint,obj):
   require(state.get('pending_mutation')is None,'Unresolved prior mutation; no blind mutation retry')
   checkpoint(kind+'_attempted',pending_mutation=dict(kind=kind,request_SHA256=sha_bytes(json.dumps(obj,separators=(',',':')).encode())))
   result=api('POST',endpoint,obj)
   require(re.fullmatch('[0-9a-f]{40}',result.get('sha',''))is not None,'Returned exact Git object identity')
   checkpoint(kind+'_confirmed',pending_mutation=None,**{kind+'_sha':result['sha']});return result['sha']
  def verify_commit_paths(commit,tree,entries):
   record=api('GET','git/commits/'+commit);require(record['sha']==commit and record['tree']['sha']==tree and [p['sha']for p in record['parents']]==[args.parent],'Fixed commit binds exact tree and declared parent')
   cache={}
   def tree_rows(value):
    if value not in cache:
     obj=api('GET','git/trees/'+value);require(obj['sha']==value and obj.get('truncated')is False,'Complete exact nonrecursive Git tree')
     cache[value]={r['path']:r for r in obj['tree']}
    return cache[value]
   for entry in entries:
    value=tree;parts=PurePosixPath(entry['path']).parts
    for index,part in enumerate(parts):
     row=tree_rows(value).get(part);require(row is not None,'Committed repository path missing')
     if index==len(parts)-1:require(row['type']=='blob'and row['mode']=='100644'and row['sha']==entry['sha'],'Committed path binds verified blob')
     else:require(row['type']=='tree','Exact intermediate tree');value=row['sha']
  try:
   guard();checkpoint('attempt_started')
   if not state.get('commit_POST_sha'):require(head()==args.parent,'Remote branch advanced; no overwrite')
   for item in files:retain_blob(item['repo_relative_path'],item=item)
   for target,raw in small_data.items():retain_blob(target,small=raw)
   entries=[dict(path=target,mode='100644',type='blob',sha=proof['Git_blob_SHA'])for target,proof in sorted(state['verified'].items())]
   require({e['path']for e in entries}=={r['repo_relative_path']for r in files}|set(small_data),'Exact public whitelist; private checkpoints never enter Git')
   if not state.get('tree_POST_sha'):
    require(head()==args.parent,'Remote advanced before tree creation');base=api('GET','git/commits/'+args.parent)['tree']['sha']
    mutate_once('tree_POST','git/trees',dict(base_tree=base,tree=entries))
   tree=state['tree_POST_sha']
   if not state.get('commit_POST_sha'):mutate_once('commit_POST','git/commits',dict(message='Retain exact coarse/fine real eigen cache chunks with portable indexes and byte readback',tree=tree,parents=[args.parent]))
   commit=state['commit_POST_sha'];verify_commit_paths(commit,tree,entries)
   current=head()
   if current!=commit:
    require(current==args.parent and not state.get('ref_update_attempted'),'Remote advance or uncertain earlier ref update; no second PATCH')
    checkpoint('nonforce_ref_PATCH_attempted',ref_update_attempted=True)
    answer=api('PATCH','git/refs/heads/'+BRANCH,dict(sha=commit,force=False));require(answer['object']['sha']==commit,'Exact nonforce ref response')
   require(head()==commit,'Final branch head readback must bind fixed retained-cache commit')
   verify_commit_paths(commit,tree,entries)
   rows=[dict(commit=commit,repo_relative_path=target,bytes=proof['bytes'],SHA256=proof['SHA256'],readback_passed=True,Git_blob_SHA=proof['Git_blob_SHA'])for target,proof in sorted(state['verified'].items())]
   public=dict(schema='task1-retained-cache-public-readback-receipt-v1',repository=REPO,commit=commit,files=rows)
   destination=out/'public-receipt.json'
   if destination.exists():require(read_json(destination)==public,'Preserved public receipt differs; no overwrite')
   else:new_json(destination,public)
   checkpoint('fixed_commit_full_readback_verified',remote_commit=commit)
   receipt.update(status='published_fixed_commit_full_blob_and_path_readback_verified',commit=commit,public_files=len(rows),public_receipt_SHA256=file_sha(destination),originals_modified=False)
  except BaseException as error:
   receipt.update(error_type=type(error).__name__,error=str(error),phase=state.get('phase'),pending_mutation=state.get('pending_mutation'))
   checkpoint('failed_preserved_no_blind_retry');raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   for p,t in bounded.owned_descendants(pid,ticks,dict(owned)).items():
    if p!=pid and bounded.live(p,t):
     try:os.kill(p,signal.SIGKILL)
     except ProcessLookupError:pass
   elapsed=time.monotonic()-start;ledger=budget.load_ledger(ledger_path);ledger['spent_seconds']+=elapsed
   ledger['runs'].append(dict(run_id=out.name,stage='retained_eigen_cache_REST_publication',seconds=elapsed,status=receipt['status'],new_PDE=0))
   temporary=ledger_path.with_name('task1-budget-cache-retain-'+str(pid)+'.tmp');new_json(temporary,ledger);os.replace(temporary,ledger_path)
   receipt.update(finished_utc=bounded.now(),elapsed_seconds=elapsed,resources=resources,remaining_approved_seconds=budget.remaining_seconds(ledger))
   new_json(out/('attempt-%03d.json'%attempt),receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(dict(status=receipt['status'],commit=receipt.get('commit'),attempt=attempt,private_receipt=str(out/('attempt-%03d.json'%attempt))),ensure_ascii=False))

if __name__=='__main__':main()
