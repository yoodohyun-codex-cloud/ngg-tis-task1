#!/usr/bin/env python3
"""Official Git pack transport for a GitHub REST422 large-input refusal.
No install, credential change, TLS/proxy change, force push, main merge or PDE.
All source/native failures and original bytes remain immutable.
"""
import sys,os,json,time,signal,threading,subprocess,hashlib,base64,shutil
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');RUN=Path('/workspace/task1-xy100-2000-20261025-run-r2');OUT=Path('/dev/shm/task1-git-xy-recovery-20261025-run');L=ROOT/'runtime/task1-budget.json';CASE='baseline-square15-human-sine2000-xy100';PUBLIC='data-native/cloud-xy100-2000-20261025';DOC='docs/TASK1_XY100_2000_20261025';REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020';PARENT='0c282061b1e9da556c4ae4840f9470ce4b463cfa'
sys.path.insert(0,str(ROOT/'tools'))
import task1_resource_policy as p,task1_execution_policy as ep,task1_bounded_continuation as b
os.environ['GODEBUG']='http2client=0'
def req(ok,msg):
 if not ok:raise ValueError(msg)
def sha(f):
 h=hashlib.sha256()
 with Path(f).open('rb')as stream:
  for raw in iter(lambda:stream.read(1024**2),b''):h.update(raw)
 return h.hexdigest()
def read(f):return json.loads(Path(f).read_text())
def new(f,obj):
 with Path(f).open('x')as stream:json.dump(obj,stream,ensure_ascii=False,allow_nan=False,indent=2)
def size(q):return q.stat().st_size if q.is_file()else sum(v.stat().st_size for v in q.rglob('*')if v.is_file())
with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
 req(not OUT.exists(),'Preserve all previous attempts');OUT.mkdir();(OUT/'logs').mkdir();(OUT/'tmp').mkdir();start=time.monotonic();deadline=start+240;pid=os.getpid();ticks=b.ticks(pid);owned={pid:ticks};stop=threading.Event();limits=ep.resolve_limits();ep.configure_process(limits);state=dict(peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);receipt=dict(status='failed_preserved',schema='task1-supported-Git-transport-recovery-v1',new_PDE=0,stage_cap_seconds=240,cumulative_time_unlimited=True,limits=limits,original_rest422_preserved=True)
 def guard():
  live=b.owned_descendants(pid,ticks,dict(owned));rss=sum(b.rss(v)for v,t in live.items()if b.live(v,t));tmp=sum(size(q)for q in Path('/dev/shm').glob('task1-*'));state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp));req(time.monotonic()<deadline,'FiniteGittransportdeadline');req(rss+tmp<=limits['total_memory_bytes'],'Approvedaggregate8GB')
 def interrupt(s,f):raise TimeoutError(state.get('error','FiniteGittransportinterrupted'))
 def monitor():
  while not stop.wait(1):
   try:guard()
   except BaseException as e:state['error']=str(e);os.kill(pid,signal.SIGTERM);return
 handlers={s:signal.getsignal(s)for s in(signal.SIGINT,signal.SIGTERM,signal.SIGALRM)}
 for s in handlers:signal.signal(s,interrupt)
 signal.setitimer(signal.ITIMER_REAL,240);thread=threading.Thread(target=monitor,daemon=True);thread.start();calls=0
 env=dict(os.environ,TMPDIR=str(OUT/'tmp'),GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never',GIT_AUTHOR_NAME='Codex Research',GIT_AUTHOR_EMAIL='codex@openai.com',GIT_COMMITTER_NAME='Codex Research',GIT_COMMITTER_EMAIL='codex@openai.com',GIT_INDEX_FILE=str(OUT/'index'))
 def command(argv,body=None,allow_missing=False):
  global calls
  calls+=1;guard();child=subprocess.Popen(argv,stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env=env);owned[child.pid]=b.ticks(child.pid)
  try:
   raw,err=child.communicate(input=body,timeout=max(.01,deadline-time.monotonic()));req(len(raw)<=100*1024**2 and len(err)<=2*1024**2,'Finitecommandresponse')
   if child.returncode:
    if allow_missing and b'HTTP 404'in err:return None
    new(OUT/'logs'/('failed-'+str(calls)+'.json'),dict(argv=argv,returncode=child.returncode,stderr=err.decode(errors='replace')[:8000],stdout_prefix=raw[:8000].decode(errors='replace')));raise RuntimeError('Commandfailed; preserved '+str(OUT/'logs'/('failed-'+str(calls)+'.json')))
   if err:new(OUT/'logs'/('stderr-'+str(calls)+'.json'),dict(argv=argv,stderr=err.decode(errors='replace')[:8000]))
   return raw
  finally:
   if child.poll()is None:child.kill();child.wait(timeout=2)
 def api(endpoint,obj=None,method='GET',missing=False):
  argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
  if obj is not None:argv+=['--input','-']
  raw=command(argv,None if obj is None else json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode(),missing);return None if raw is None else json.loads(raw)
 bare=OUT/'repo.git'
 def git(*args,body=None):return command(['git','-c','credential.helper=!gh auth git-credential','-c','gc.auto=0','-c','pack.threads=2','-c','pack.window=0','-c','pack.compression=1','--git-dir='+str(bare),*args],body)
 try:
  req(api('git/ref/heads/'+BRANCH)['object']['sha']==PARENT,'Concurrentremoteadvance')
  new(OUT/'registration.json',dict(source_SHA256=sha(__file__),expected_parent=PARENT,scope='Supported HTTPS Git pack transport explicitly recommended by GitHub422 response; metadata-only shallow blobless fetch; no large-file RESTPOSTretry',resource_limits=limits,original_failure_receipt_SHA256=sha(RUN/'publish-results-receipt.json'),native_manifest_SHA256=sha(RUN/'native-sha256.json'),new_PDE=0))
  git('init','--bare',str(bare));git('remote','add','origin','https://github.com/'+REPO+'.git');git('fetch','--no-tags','--depth=1','--filter=blob:none','origin','refs/heads/'+BRANCH)
  req(git('rev-parse','FETCH_HEAD').decode().strip()==PARENT,'Fetchedbranchdoesnotmatchexpectedparent');git('read-tree','FETCH_HEAD')
  basis=RUN/'bases'/CASE;files={PUBLIC+'/'+q.relative_to(RUN).as_posix():q for q in basis.iterdir()if q.is_file()}
  for dirname in('postprocess',):
   for q in(RUN/dirname).iterdir():
    if q.is_file():files[PUBLIC+'/'+q.relative_to(RUN).as_posix()]=q
  for name in('preregistration.json','native-sha256.json','prepare-receipt.json','execute-receipt.json','postprocess-receipt.json','source-publication.json','publish-results-receipt.json','publication-controller-snapshot.json'):files[PUBLIC+'/'+name]=RUN/name
  files[PUBLIC+'/evidence.tar.gz']=RUN/'publication-evidence/evidence.tar.gz';files[PUBLIC+'/evidence-manifest.json']=RUN/'publication-evidence/manifest.json';files[PUBLIC+'/failure-evidence/rest422.log']=RUN/'logs/failed-publish-results-56523.log'
  for name in('summary.json','material-table.json','material-evidence.json','config-diff.json'):files[DOC+'/'+name]=RUN/('postprocess/'+name if name=='summary.json'else name)
  files[PUBLIC+'/transport-recovery/registration.json']=OUT/'registration.json';files['tools/git_transport_20261025/git_recover.py']=Path(__file__)
  records=[]
  for target,q in files.items():
   guard();req(q.is_file()and not q.is_symlink(),'Regularoriginalartifact');blob=git('hash-object','-w',str(q)).decode().strip();req(len(blob)==40,'LocalGitblobidentity');git('update-index','--add','--cacheinfo','100644,'+blob+','+target);records.append(dict(target=target,file=str(q),blob=blob,SHA256=sha(q),bytes=q.stat().st_size))
  tree=git('write-tree','--missing-ok').decode().strip();message=OUT/'commit-message.txt';message.write_text('Preserve actual XY100 native fields and diagnostics through supported Git transport\n\nREST large-input422 and all original evidence are retained.\n');commit=git('commit-tree',tree,'-p',PARENT,'-F',str(message)).decode().strip();receipt['local_commit']=commit
  req(api('git/ref/heads/'+BRANCH)['object']['sha']==PARENT,'Concurrentadvancebeforepush');git('push','origin',commit+':refs/heads/'+BRANCH);req(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Pushrefreadback');metadata=api('git/commits/'+commit);req(metadata['tree']['sha']==tree and [x['sha']for x in metadata['parents']]==[PARENT],'Exactcommittreeparentreadback')
  cache={}
  for old in(RUN/'source-publication.json',):
   for v in read(old)['files'].values():
    if v['readback_passed']:cache[v['Git_blob_SHA']]=v
  for ck in(RUN/'publication-checkpoints').glob('*.json'):
   v=read(ck)['proof']
   if v.get('readback_passed'):cache[v['Git_blob_SHA']]=v
  proof={};same_stage={}
  for index,record in enumerate(records):
   guard();old=cache.get(record['blob'],same_stage.get(record['blob']))
   if old is not None and old['SHA256']==record['SHA256']and old['bytes']==record['bytes']:kind='reused_prior_full_immutable_readback'
   else:
    got=api('git/blobs/'+record['blob']);raw=base64.b64decode(got['content']);req(got['sha']==record['blob']and len(raw)==record['bytes']and hashlib.sha256(raw).hexdigest()==record['SHA256'],'FullremoteimmutableGitblobreadback');kind='fresh_full_immutable_readback';del raw,got
   v=dict(SHA256=record['SHA256'],bytes=record['bytes'],Git_blob_SHA=record['blob'],readback_passed=True,proof_kind=kind);proof[record['target']]=v;same_stage[record['blob']]=v;new(OUT/('verified-'+str(index)+'.json'),dict(target=record['target'],proof=v))
  new(RUN/'result-publication.json',dict(status='published_readback_verified',commit=commit,files=proof,transport='SupportednormalGitHTTPSnonforcepush; no RESTsizebypass'))
  comment=api('issues/2/comments',dict(body='XY0.625→0.5mm/2000Hz/2RHS 새 PDE와 후처리 결과를 게시했습니다. 기존CPU1/3GiB 실행으로550200셀,34.266초 실제계산이며5개nativegate와13개scalar인접검사는통과했습니다. 목표carrierRMSmean0.0289694→0.0289374V/m(0.1104%),P10약0.0131%,접촉Jmax약0.849% 변화입니다. 단일carrier 진단이며새TIS변조가아닙니다.\n\n그러나동일r23.75mm 영역의SC독립계면2점차이는전체16.775→17.483%,외곽50.090→60.112%로악화됐고,up3도실패합니다. 전체수렴/후보채택/활성화/안전성은미검증상태를유지합니다. 다음은정확해를이용한계면재구성편향과수직격자진단입니다.\n\n원시파일11개와후처리/실패: https://github.com/'+REPO+'/tree/'+commit+'/'+PUBLIC+'\n요약: https://github.com/'+REPO+'/blob/'+commit+'/'+DOC+'/summary.json\n\nRESTAPI의48.7MBblob입력422와원본을보존하고,해당응답이권고한공식GitpackHTTPS전송으로복구했습니다. bloblessshallowmetadatafetch,비강제topicbranchpush후모든결과SHA/bytesreadback을확인했습니다. 설치/자격정보/보안/요금/main병합/서비스제한우회/중복PDE는없습니다. 최신4CPU/총8GB정책은별도승인기록에연결하며이배치의과거CPU1실행을4코어로표시하지않습니다. Windows실제저장은미확인입니다.'),'POST');receipt.update(status='XY_native_and_diagnostics_published_supported_Git_verified',result_commit=commit,files_verified=len(proof),native_files_verified=len(list(basis.iterdir())),comment_url=comment['html_url'])
 except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
  for v,t in b.owned_descendants(pid,ticks,dict(owned)).items():
   if v!=pid and b.live(v,t):
    try:os.kill(v,signal.SIGKILL)
    except ProcessLookupError:pass
  elapsed=time.monotonic()-start;ledger=p.load_ledger();ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=RUN.name,stage='supported_Git_transport_recovery',status=receipt['status'],seconds=elapsed));temp=L.with_name('task1-budget-git-transport.tmp')
  with temp.open('x')as f:json.dump(ledger,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
  os.replace(temp,L);receipt.update(elapsed_seconds=elapsed,remaining_seconds=p.remaining_seconds(ledger),resources=state);new(OUT/'receipt.json',receipt)
  for s,h in handlers.items():signal.signal(s,h)
  print(json.dumps(receipt,ensure_ascii=False))
