"""Finite publication/accounting of the explicit cumulative-time override."""
import sys,os,json,time,hashlib,base64,subprocess,signal,threading,shutil
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/workspace/ngg-tis-task1');D=Path('/workspace/task1-interface-fourier-20261025-run-r2');L=R/'runtime/task1-budget.json';PUB='docs/TASK1_INTERFACE_FOURIER_20261025';REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020';PARENT='1cc13766cb687ed5065df46916c141ea66ccab16'
sys.path[:0]=[str(R/'tools'),'/dev/shm/task1-interface-fourier-20261025/source']
import task1_resource_policy as p,task1_bounded_continuation as b,task1_execution_policy as ep
os.environ['GODEBUG']='http2client=0'
def req(x,m):
 if not x:raise ValueError(m)
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def read(x):return json.loads(Path(x).read_text())
def new(x,o):
 with Path(x).open('x')as f:json.dump(o,f,ensure_ascii=False,allow_nan=False,indent=2)
def size(x):return x.stat().st_size if x.is_file()else sum(q.stat().st_size for q in x.rglob('*')if q.is_file())
with b.dual_lock(R/'.task1-loop.lock'),b.dual_lock(R/'.task1-execution.lock'):
 start=time.monotonic();deadline=start+90;pid=os.getpid();ticks=b.ticks(pid);owned={pid:ticks};stop=threading.Event();state=dict(peak_RSS=0,peak_owned_tmpfs=0);limits=ep.resolve_limits();ep.configure_process(limits);receipt=dict(status='failed_preserved',new_PDE=0,cap_seconds=90,cumulative_time_unlimited=True)
 def guard():
  rss=sum(b.rss(v)for v,t in b.owned_descendants(pid,ticks,dict(owned)).items()if b.live(v,t));tmp=sum(size(q)for q in Path('/dev/shm').glob('task1-*'));state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp));req(rss+tmp<=limits['total_memory_bytes'],'Approvedaggregate8GB');req(time.monotonic()<deadline,'Finite90secondpublicationdeadline')
 def interrupt(s,f):raise TimeoutError('Finitepolicypublicationinterrupted')
 def monitor():
  while not stop.wait(1):
   try:guard()
   except BaseException:os.kill(pid,signal.SIGTERM);return
 old={s:signal.getsignal(s)for s in(signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
 for s in old:signal.signal(s,interrupt)
 signal.setitimer(signal.ITIMER_REAL,90);thread=threading.Thread(target=monitor,daemon=True);thread.start()
 def api(endpoint,obj=None,method='GET'):
  guard();a=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
  if obj is not None:a+=['--input','-']
  c=subprocess.Popen(a,stdin=subprocess.PIPE if obj is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);owned[c.pid]=b.ticks(c.pid)
  try:
   raw,err=c.communicate(input=None if obj is None else json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode(),timeout=max(.01,deadline-time.monotonic()));req(c.returncode==0,'GitHubfailed '+err.decode(errors='replace')[:500]);return json.loads(raw)
  finally:
   if c.poll()is None:c.kill();c.wait(timeout=2)
 def command(argv):
  guard();child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);owned[child.pid]=b.ticks(child.pid)
  try:
   raw,err=child.communicate(timeout=max(.01,deadline-time.monotonic()));req(len(raw)<4*1024**2,'Boundedtestoutput')
   if child.returncode:
    new(D/'test-failure.json',dict(argv=argv,stdout=raw.decode(errors='replace'),stderr=err.decode(errors='replace')))
   req(child.returncode==0,'Analyticcontracttestsfailed; preservedtest-failure.json');return raw
  finally:
   if child.poll()is None:child.kill();child.wait(timeout=2)
 try:
  ledger=p.load_ledger();req(p.effective_limit(ledger)is None,'Unlimitedauthorizationpreserved')
  import fourier_benchmark as fb
  source=Path('/dev/shm/task1-interface-fourier-20261025/source');(D/'source').mkdir()
  pins={str(f):sha(f)for f in source.iterdir()if f.is_file()and f.suffix in('.py','.md')}
  inputs=fb.required_inputs();spec=fb.make_spec((fb.COARSE/'material-input.json').read_bytes(),(fb.COARSE/'configs'/(fb.COARSE_CASE+'.properties')).read_bytes(),optional_sc4=True)
  new(D/'spec.json',spec);new(D/'registration.json',dict(schema='task1-manufactured-interface-finite-registration-v1',question='XYscalarstablebutindependentSCjumpworsens: separate fittruncation on exactdata from lateral/verticaldiscretization',source_sha256=pins,input_sha256=inputs,spec_SHA256=sha(D/'spec.json'),resource_limits=limits,maximum_manufactured_cases=20,new_real_phantom_PDE=0,compute_deadline_seconds=30,total_stage_deadline_seconds=90,unchanged_independent_QA_limit=.05))
  for f in source.iterdir():
   if f.is_file():shutil.copyfile(f,D/'source'/f.name)
  tests=command([sys.executable,'-B','-c','import unittest,sys; suite=unittest.defaultTestLoader.discover(sys.argv[1],pattern="test_fourier_benchmark.py"); result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite); sys.exit(0 if result.wasSuccessful() else 1)',str(source)])
  with(D/'tests.log').open('xb')as f:f.write(tests)
  c0=time.process_time();t0=time.monotonic();result=fb.build(spec,guard,deadline_monotonic=start+30);wall=time.monotonic()-t0;cpu=time.process_time()-c0
  new(D/'summary.json',result['summary']);new(D/'profiles.json',result['arrays']);new(D/'computation-receipt.json',dict(status='manufactured_cases_computed',new_real_phantom_PDE=0,manufactured_cases=len(result['summary']['rows']),analytic_contracts=result['summary']['analytic_contracts'],wall_seconds=wall,process_CPU_seconds=cpu,observed_average_CPU_cores=cpu/max(wall,1e-30),implementation='stdlib complex tridiagonal serial; CPU4cap is not4coreusageclaim',resource_limits=limits))
  for f,h in{**pins,**inputs}.items():req(sha(f)==h,'Source/inputchanged')
  files={PUB+'/'+name:D/name for name in('spec.json','registration.json','summary.json','computation-receipt.json','tests.log')};files['data-manufactured/interface-fourier-20261025/profiles.json']=D/'profiles.json';files.update({'tools/interface_fourier_20261025/'+f.name:f for f in(D/'source').iterdir()if f.is_file()and f.suffix in('.py','.md')})
  req(api('git/ref/heads/'+BRANCH)['object']['sha']==PARENT,'Otherworkadvancedbranch');base=api('git/commits/'+PARENT)['tree']['sha'];entries=[];proof={}
  for target,f in files.items():
   raw=f.read_bytes();blob=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST');identity=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();req(blob['sha']==identity,'Deterministicblob');back=base64.b64decode(api('git/blobs/'+identity)['content']);req(back==raw,'Fullimmutablebytesreadback');proof[target]=dict(SHA256=sha(f),bytes=len(raw),Git_blob_SHA=identity,readback_passed=True);entries.append(dict(path=target,mode='100644',type='blob',sha=identity))
  tree=api('git/trees',dict(base_tree=base,tree=entries),'POST')['sha'];commit=api('git/commits',dict(message='Separate interface polynomial-fit bias from exact Fourier and vertical-FVM errors',tree=tree,parents=[PARENT]),'POST')['sha'];receipt['created_commit']=commit
  req(api('git/ref/heads/'+BRANCH)['object']['sha']==PARENT,'Concurrentadvance');api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');req(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Refreadback');new(D/'publication.json',dict(status='published_readback_verified',commit=commit,files=proof))
  body='XY격자세분화에서13개scalar지표가안정적인데SC독립계면차이가악화돼, 정확해가있는별도계면진단을계산했습니다. 고정층두께와기존2000Hz복소gamma를그대로사용한20개제조해Fourier케이스와9개해석계약검사이며, 실제원통/CEM/전극/50Ω/2carrierTIS계산을대신하지않습니다. 정확전위샘플의2점/up3재구성편향, 수평차분symbol, 수직FVM오차와각면의정확J대비차이를분리했습니다. 기존5%QA/실제모델hold는바꾸거나해제하지않았습니다. CPU4/총RSS+tasktmpfs8,000,000,000B/heap2GiB/단일소유자/유한watchdog/누적시간무제한정책을적용했고이작은stdlib계산은순차이며4코어가속으로표시하지않습니다.\n\n결과/사전명세: https://github.com/'+REPO+'/tree/'+commit+'/'+PUB+'\n\n계산소스와해시/실제완료영수증/프로파일을함께게시했습니다. 다음실제팬텀배치는결과를검토해선정하며전체수렴/후보채택/활성화/안전성은여전히미검증입니다. Windows실제저장은미확인입니다.'
  comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='manufactured_interface_diagnostic_computed_published',commit=commit,files_verified=len(proof),manufactured_cases=len(result['summary']['rows']),new_real_phantom_PDE=0,comment_url=comment['html_url'])
 except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
  for v,t in b.owned_descendants(pid,ticks,dict(owned)).items():
   if v!=pid and b.live(v,t):
    try:os.kill(v,signal.SIGKILL)
    except ProcessLookupError:pass
  elapsed=time.monotonic()-start;ledger=p.load_ledger();ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id='interface-fourier-20261025',stage='finite_manufactured_interface_batch',status=receipt['status'],seconds=elapsed));tmp=L.with_name('task1-budget-unlimited-publication.tmp')
  with tmp.open('x')as f:json.dump(ledger,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
  os.replace(tmp,L);receipt.update(elapsed_seconds=elapsed,spent_seconds=ledger['spent_seconds'],remaining_seconds=p.remaining_seconds(ledger),resources=state);new(D/'publication-receipt.json',receipt)
  for s,h in old.items():signal.signal(s,h)
  print(json.dumps(receipt,ensure_ascii=False))
