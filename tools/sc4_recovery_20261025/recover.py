"""Recover verification of an ALREADY PUSHED SC4 commit. Never rerun/push it.
Historical pipeline401/failures remain unchanged. Bounded GET-only retries reuse
configured credentials; no authentication, network or security setting changes.
"""
import sys,os,json,time,hashlib,base64,subprocess,threading,signal
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');RUN=Path('/dev/shm/task1-sc4-2000-20261025-run');OLD=Path('/dev/shm/task1-git-queue-task1-sc4-2000-20261025-run-66055');OUT=Path('/dev/shm/task1-sc4-readback-recovery-20261025-run');L=ROOT/'runtime/task1-budget.json';REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020';COMMIT='c440ccec3ed2c8168190bf5827bce07fdc6596c3';PUB='data-native/cloud-sc4-2000-20261025';DOC='docs/TASK1_SC4_CONTINUATION_RECOVERY_20261025'
sys.path.insert(0,str(ROOT/'tools'));import task1_resource_policy as policy,task1_execution_policy as ep,task1_bounded_continuation as b
os.environ['GODEBUG']='http2client=0'
def req(x,m):
 if not x:raise ValueError(m)
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for a in iter(lambda:f.read(1024**2),b''):h.update(a)
 return h.hexdigest()
def new(p,o):
 with Path(p).open('x')as f:json.dump(o,f,ensure_ascii=False,allow_nan=False,indent=2)
def size(p):return p.stat().st_size if p.is_file()else sum(q.stat().st_size for q in p.rglob('*')if q.is_file())
with b.dual_lock(ROOT/'.task1-queue-owner.lock'),b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
 req(not OUT.exists(),'Preserve recovery attempts');OUT.mkdir();(OUT/'logs').mkdir();start=time.monotonic();deadline=start+240;pid=os.getpid();ticks=b.ticks(pid);known={pid:ticks};limits=ep.resolve_limits();ep.configure_process(limits);stop=threading.Event();state=dict(peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);receipt=dict(schema='task1-SC4-existing-commit-verification-recovery-v1',status='failed_preserved',pid=pid,proc_start_ticks=ticks,started_utc=b.now(),new_native_PDE=0,SC8_started=False,cap_seconds=240,existing_result_commit=COMMIT,previous_pipeline_stop='HTTP401onreadonlyrefGETafterGitpush',credentials_changed=False)
 def guard():
  live=b.owned_descendants(pid,ticks,dict(known));known.update(live);rss=sum(b.rss(v)for v,t in live.items()if b.live(v,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp));req(time.monotonic()<deadline,'Finite recoverydeadline');req(rss+tmp<=limits['total_memory_bytes'],'ApprovedRSS+allownedtmpfs8e9')
 def interrupt(s,f):raise TimeoutError(state.get('error','Finite recovery interrupted'))
 def monitor():
  while not stop.wait(1):
   try:guard()
   except BaseException as e:state['error']=str(e);os.kill(pid,signal.SIGTERM);return
 handlers={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGINT,signal.SIGTERM)}
 for s in handlers:signal.signal(s,interrupt)
 signal.setitimer(signal.ITIMER_REAL,240);thread=threading.Thread(target=monitor,daemon=True);thread.start();counter=0
 def command(argv,body=None,allow_error=False):
  global counter
  counter+=1;guard();child=subprocess.Popen(argv,stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);known[child.pid]=b.ticks(child.pid)
  try:
   raw,err=child.communicate(input=body,timeout=max(.01,deadline-time.monotonic()));req(len(raw)<=160*1024**2,'Boundedresponse')
   if child.returncode:new(OUT/'logs'/('command-'+str(counter)+'.json'),dict(argv=argv,returncode=child.returncode,stderr=err.decode(errors='replace')[:5000],stdout_prefix=raw[:3000].decode(errors='replace')))
   req(allow_error or child.returncode==0,'Commandfailed; evidencepreserved');return child.returncode,raw,err
  finally:
   if child.poll()is None:child.kill();child.wait(timeout=2)
 def api(endpoint,obj=None,method='GET',missing=False):
  for attempt in range(3 if method=='GET' else 1):
   argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
   if obj is not None:argv+=['--input','-']
   code,raw,err=command(argv,None if obj is None else json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode(),True)
   if not code:return json.loads(raw)
   if missing and b'HTTP 404'in err:return None
   if method!='GET'or attempt==2:raise RuntimeError('GitHub '+method+' failed after bounded readonly attempts; no credential changes or mutation retry')
   time.sleep(attempt+1)
 def publish(files,parent):
  req(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrentbranchadvance');base=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
  for target,p in files.items():
   raw=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();got=api('git/blobs/'+blob,missing=True)
   if got is None:got=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST')
   back=base64.b64decode(api('git/blobs/'+blob)['content']);req(back==raw,'Recovery evidencefullreadback');entries.append(dict(path=target,mode='100644',type='blob',sha=blob));proof[target]=dict(SHA256=sha(p),bytes=len(raw),Git_blob_SHA=blob,readback_passed=True)
  tree=api('git/trees',dict(base_tree=base,tree=entries),'POST')['sha'];commit=api('git/commits',dict(message='Recover SC4 post-push verification and record why conditional SC8 never started',tree=tree,parents=[parent]),'POST')['sha'];req(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrentadvance');api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');req(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Recoveryrefreadback');return dict(status='published_readback_verified',commit=commit,files=proof)
 try:
  plan=read(RUN/'external-git-publication-plan.json');req(read(OLD/'receipt.json')['local_commit']==COMMIT,'Preservedlocalpushcommit');req(not(RUN/'result-publication.json').exists(),'No overwrite completedpublicationreceipt');req(not Path('/dev/shm/task1-sc8-2000-20261025-run').exists(),'SC8alreadyexists; re-evaluateownershipbeforework')
  new(OUT/'registration.json',dict(source_SHA256=sha(__file__),existing_commit=COMMIT,failed_transport_receipt_SHA256=sha(OLD/'receipt.json'),old_queue_receipt_SHA256=sha(ROOT/'runtime/finite-native-queue-20261025/sc4-sc8/receipt.json'),native_manifest_SHA256=sha(RUN/'native-sha256.json'),resource_limits=limits,scope='Full byte verification only of existing public commit; no solver or Gitpushrepeat',GET_retries=3,mutation_retries=0))
  head=api('git/ref/heads/'+BRANCH)['object']['sha'];req(head==COMMIT,'Remoteadvanced; preserveworkandreevaluateparent');metadata=api('git/commits/'+COMMIT);req([x['sha']for x in metadata['parents']]==[read(RUN/'source-publication.json')['commit']],'Exactoriginalsourceparent');tree=api('git/trees/'+metadata['tree']['sha']+'?recursive=1');req(not tree.get('truncated'),'Completecommitmetadatarequired');entries={x['path']:x for x in tree['tree']if x['type']=='blob'}
  files={t:Path(v['local_path'])for t,v in plan['files'].items()}
  for name in('publish-results-receipt.json','external-git-publication-plan.json'):files[PUB+'/'+name]=RUN/name
  files[PUB+'/transport-recovery/registration.json']=OLD/'registration.json'
  source_target='tools/git_transport_20261025/git_publish_plan.py';code,raw,err=command(['git','--git-dir='+str(OLD/'repo.git'),'show',COMMIT+':'+source_target]);original=OUT/'original-git-publisher.py'
  with original.open('xb')as f:f.write(raw)
  files[source_target]=original;proof={};cache={}
  for index,(target,path)in enumerate(files.items()):
   guard();raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();req(target in entries and entries[target]['sha']==blob,'Exacttreepath/localbytesbinding: '+target)
   if blob not in cache:
    got=api('git/blobs/'+blob);back=base64.b64decode(got['content']);req(got['sha']==blob and len(back)==len(raw)and hashlib.sha256(back).hexdigest()==digest,'Fullremoteimmutablepayloadreadback');cache[blob]=True;del got,back
   proof[target]=dict(SHA256=digest,bytes=len(raw),Git_blob_SHA=blob,readback_passed=True,proof_kind='existing_public_commit_full_readback_recovered');new(OUT/('verified-'+str(index)+'.json'),dict(target=target,proof=proof[target]));del raw
  req(api('git/ref/heads/'+BRANCH)['object']['sha']==COMMIT,'Remoteadvancewhileverification; nooverwrite');new(RUN/'result-publication.json',dict(status='published_readback_verified',commit=COMMIT,files=proof,transport='ExistingGitpushalreadycompleted; recoveredverificationonly',recovery_registration_SHA256=sha(OUT/'registration.json')))
  recovery=dict(schema='task1-SC4-SC8-status-reconciliation-v1',SC4_calculation='complete2RHS754560cells',SC4_postprocessing='complete_unadopted',SC4_Gitpush_commit=COMMIT,SC4_full_byte_readback='complete_now_recovered',original_queue_PID=66055,original_queue_PID_live=False,original_queue_stop_utc='2026-10-25T03:26:38.598284+00:00',original_stop_cause='GitHubread-onlyrefGETHTTP401after successfulGitpush',current_configured_CLI_read='successful without credential changes',SC8='not_run; no native run directory and no public2kHzSC8 result',all_original_failures_preserved=True,new_PDE_in_recovery=0,full_convergence_validated=False,Windows_saved=False)
  new(OUT/'recovery.json',recovery);result=publish({DOC+'/recovery.json':OUT/'recovery.json',DOC+'/original-queue-receipt.json':ROOT/'runtime/finite-native-queue-20261025/sc4-sc8/receipt.json',DOC+'/original-transport-failure.json':OLD/'logs/failed-73.json',DOC+'/SC4-full-publication-readback.json':RUN/'result-publication.json',DOC+'/registration.json':OUT/'registration.json','tools/sc4_recovery_20261025/recover.py':Path(__file__)},COMMIT);new(OUT/'evidence-publication.json',result)
  comment=api('issues/2/comments',dict(body='PID66055는03:26:38UTC에종료됐으며SC8은미실행입니다. SC4계산/후처리와Gitpush(c440ccec)는성공했지만그직후readonlyrefGET에서HTTP401이발생해검증영수증을못쓰고조건부SC8로넘어가지못했습니다. 현재같은설정의CLI조회가정상이며자격정보/보안변경없이기존c440의31파일을tree경로·SHA·bytes로전체재검증했습니다. SC4재계산/중복push/SC8중복worker는없습니다.\n\n복구와실패근거: https://github.com/'+REPO+'/tree/'+result['commit']+'/'+DOC+'\n\nSC4의13scalar검사는통과하지만동일r23.75/공통2점SC계면차이14.54%·외곽50.56%는5%미달입니다. 절대차이/분모와동일fitorder를분리해검토하고, 정확Fourier제조해에서추정편향과진짜이산화오차를분리하는다음유한배치를선정합니다. 기존5%기준·원본/실패·누적시간무제한·CPU4·RSS+ownedtmpfs8e9·800000셀·단일소유자/dual locks를유지합니다. Windows실제저장은미확인입니다.'),'POST');receipt.update(status='SC4_existing_publication_readback_recovered_and_evidence_published',original_result_commit=COMMIT,recovery_evidence_commit=result['commit'],verified_files=len(proof),comment_url=comment['html_url'])
 except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
  for v,t in b.owned_descendants(pid,ticks,dict(known)).items():
   if v!=pid and b.live(v,t):
    try:os.kill(v,signal.SIGKILL)
    except ProcessLookupError:pass
  elapsed=time.monotonic()-start;ledger=policy.load_ledger();ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id='sc4-readback-recovery-20261025',stage='recover_existing_SC4_bytes_and_publish_failure_evidence',status=receipt['status'],seconds=elapsed));temp=L.with_name('task1-budget-sc4-readback-recovery.tmp')
  with temp.open('x')as f:json.dump(ledger,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
  os.replace(temp,L);receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,resources=state,remaining_seconds=policy.remaining_seconds(ledger));new(OUT/'receipt.json',receipt)
  for s,h in handlers.items():signal.signal(s,h)
  print(json.dumps(receipt,ensure_ascii=False))
