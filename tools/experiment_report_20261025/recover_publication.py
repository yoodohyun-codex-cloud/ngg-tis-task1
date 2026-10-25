#!/usr/bin/env python3
"""Single-owner finite publication recovery; reuse immutable receipts, archive
small evidence together, verify fresh blobs in two concurrent read-only calls.
No PDE; no changed scientific gates; original publication failure is preserved.
"""
import sys,os,json,time,signal,threading,hashlib,base64,subprocess,shutil,tarfile,io,gzip,re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.dont_write_bytecode=True
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
os.environ['GODEBUG']='http2client=0'
ROOT=Path('/workspace/ngg-tis-task1');RUN=Path('/workspace/task1-experiment-2000-2010-20261025-run');OUT=RUN/'publication-recovery-r2';SOURCE=Path('/dev/shm/task1-experiment-report-20261025/source');LEDGER=ROOT/'runtime/task1-budget.json';CAP=75;GIB=1024**3
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020';PARENT='1d32c5734cce73fd13a671edfc264d9d9cb327e4';PUBLIC='data-native/cloud-experiment-2000-2010-20261025';DOC='docs/TASK1_EXPERIMENT_2000_2010_20261025';CASE='baseline-square15-human-sine2000-2010-xy80'
sys.path[:0]=[str(ROOT/'tools'),str(SOURCE)]
import task1_bounded_continuation as bounded,task1_resource_policy as policy

def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def new(p,obj):
 with Path(p).open('x')as f:json.dump(obj,f,ensure_ascii=False,allow_nan=False,indent=2)
def size(p):
 if p.is_file():return p.stat().st_size
 return sum(q.stat().st_size for q in p.rglob('*')if q.is_file())
def main():
 with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
  ledger=policy.load_ledger(LEDGER);require(policy.remaining_seconds(ledger)>=85,'Recovery75+persistence10within original cumulative budget');require(not OUT.exists(),'Preserve all attempts');OUT.mkdir();(OUT/'GUI').mkdir();(OUT/'source').mkdir()
  start=time.monotonic();deadline=start+CAP;pid=os.getpid();ticks=bounded.ticks(pid);os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});stop=threading.Event();owned={pid:ticks};mu=threading.RLock();state=dict(peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0)
  receipt=dict(schema='task1-compact-publication-recovery-v1',status='failed_preserved',pid=pid,proc_start_ticks=ticks,started_utc=bounded.now(),stage_cap_seconds=CAP,new_PDE=0,original_failure_preserved=True,storage_capacity_guards_enabled=False)
  def guard():
   with mu:known=bounded.owned_descendants(pid,ticks,dict(owned));owned.update(known);live={p:t for p,t in known.items()if bounded.live(p,t)}
   rss=sum(bounded.rss(p)for p in live);tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp));require(time.monotonic()<deadline,'Recovery finite deadline');require(rss+tmp<=3*GIB,'Original aggregateRAM3GiB')
  def interrupt(s,f):raise TimeoutError(state.get('error','Finite recovery interrupted'))
  def monitor():
   while not stop.wait(1):
    try:guard()
    except BaseException as e:state['error']=str(e);os.kill(pid,signal.SIGTERM);return
  handlers={s:signal.getsignal(s)for s in(signal.SIGINT,signal.SIGTERM,signal.SIGALRM)}
  for s in handlers:signal.signal(s,interrupt)
  signal.setitimer(signal.ITIMER_REAL,CAP);thread=threading.Thread(target=monitor,daemon=True);thread.start()
  def command(argv,body=None,missing=False):
   guard();c=subprocess.Popen(argv,stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env=dict(os.environ,TMPDIR=str(RUN/'tmp'),PYTHONDONTWRITEBYTECODE='1'))
   with mu:owned[c.pid]=bounded.ticks(c.pid)
   try:
    raw,err=c.communicate(input=body,timeout=max(.05,deadline-time.monotonic()));require(len(raw)<=96*1024**2,'Finite command response')
    if c.returncode:
     if missing and b'HTTP 404'in err:return None
     raise RuntimeError('Command failed: '+str(argv[:4])+' '+err.decode(errors='replace')[:1000])
    return raw
   finally:
    if c.poll()is None:c.kill();c.wait(timeout=2)
  def api(endpoint,obj=None,method='GET',missing=False):
   argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
   if obj is not None:argv+=['--input','-']
   raw=command(argv,None if obj is None else json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode(),missing)
   return None if raw is None else json.loads(raw)
  try:
   sources={str(p):sha(p)for p in SOURCE.glob('*.py')};pins={str(RUN/'modulation-completion/summary.json'):sha(RUN/'modulation-completion/summary.json')}
   new(OUT/'registration.json',dict(source_sha256=sources,input_sha256=pins,new_PDE=0,read_only_blob_concurrency=2,mutations='sequential; explicit404onlyPOST; expectedparent; noforce',remaining_before_seconds=policy.remaining_seconds(ledger),cap_seconds=CAP))
   for p in SOURCE.glob('*.py'):shutil.copyfile(p,OUT/'source'/p.name)
   summary=read(RUN/'modulation-completion/summary.json');require(summary['scenarios']['human_2000_2010_sine']['maximum_direction_search']['status']=='complete','Complete exact native modulation required')
   import experiment_summary_view,experiment_field_maps,numpy as np
   artifact=experiment_summary_view.build_artifact(summary);basis=RUN/'bases'/CASE
   grid=np.loadtxt(io.BytesIO(gzip.decompress((basis/'grid.csv.gz').read_bytes())),delimiter=',',skiprows=1);ys=np.unique(grid[:,1]);slice_y=float(ys[np.argmin(abs(ys))]);take=np.flatnonzero(grid[:,1]==slice_y);meta=read(basis/'mesh-metadata.json');faces=np.asarray(meta['z_faces_mm']);zs=np.unique(grid[:,2]);zi=np.searchsorted(zs,grid[take,2]);dz=np.diff(faces)[zi]
   with np.load(RUN/'modulation-completion/scalars.npz',allow_pickle=False)as a:newmax=np.array(a['fundamental_maxTIS_2074_V_m'],copy=True)
   with np.load('/dev/shm/task1-human-tissue-20261025-run/postprocess/scalars.npz',allow_pickle=False)as a:humanmax=np.array(a['fundamental_maxTIS_2074_V_m'],copy=True)/(3/(2*np.sqrt(2)))
   legacy=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80';ls=read(legacy/'summary.json');sq=next(c for c in ls['conditions']if c['waveform']=='square_3h')
   with np.load(legacy/sq['native_volume_archive'],allow_pickle=False)as a:oldmax=np.array(a['maxTIS'],copy=True)/(3/(2*np.sqrt(2)))
   caseids=['human_2000_2010_sine','human_3000_3030_sine','legacy_3000_3030_sine'];labels=['문헌 대체 2000/2010 Hz','문헌 대체 3000/3030 Hz','기존 팬텀 3000/3030 Hz']
   payload=dict(slice_y_mm=slice_y,dx_mm=.625,cells=[dict(x=float(grid[i,0]),z=float(grid[i,2]),dz=float(d))for i,d in zip(take,dz)],cases=[dict(id=k,label=l,values=v[take].tolist(),global_max=float(v.max()))for k,l,v in zip(caseids,labels,[newmax,humanmax,oldmax])])
   html=experiment_field_maps.apply(artifact['html'],payload);html=html.replace('이 요약 JSON에서 공간 분포 지도를 만들어내지 않습니다.','위 공간 지도는 저장된 native scalar와 실제 격자에서 직접 추출했으며 요약 통계로 합성하지 않았습니다.')
   with(OUT/'GUI/index.html').open('x')as f:f.write(html)
   new(OUT/'GUI/manifest.json',dict(**artifact['manifest'],native_scalar_maps=True,slice_y_mm=slice_y,map_cells=len(take),map_sources=dict(new=sha(RUN/'modulation-completion/scalars.npz'),human=sha(Path('/dev/shm/task1-human-tissue-20261025-run/postprocess/scalars.npz')),legacy=sha(legacy/sq['native_volume_archive'])),new_PDE=0))
   del newmax,humanmax,oldmax,grid,payload;guard()
   for i,script in enumerate(re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',html,re.S)):
    if script.lstrip().startswith(('{','[')):continue
    p=OUT/('script-'+str(i)+'.js')
    with p.open('x')as f:f.write(script)
    command(['node','--check',str(p)])
   from playwright.sync_api import sync_playwright
   errors=[]
   with sync_playwright()as e:
    context=e.chromium.launch_persistent_context(str(OUT/'browser-profile'),executable_path='/usr/bin/chromium',headless=True,viewport=dict(width=1440,height=1000),ignore_default_args=['--disable-dev-shm-usage'],env=dict(os.environ,TMPDIR='/dev/shm',XDG_CONFIG_HOME='/dev/shm',XDG_CACHE_HOME='/dev/shm'))
    try:
     page=context.pages[0];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(html,wait_until='load');require(page.evaluate('!!window.task1SineExperimentView&&!!window.task1ExperimentFieldMaps'),'ActualsummaryandmapsAPI')
     before=page.evaluate('window.task1SineExperimentView.getRanges()');page.locator('#e-controls select').select_option('1');require(page.evaluate('window.task1SineExperimentView.getRanges()')==before,'Chartmetricchangedaxislimits')
     r=page.evaluate('window.task1ExperimentFieldMaps.getRanges()');require(page.evaluate('(r)=>window.task1ExperimentFieldMaps.setRanges({...r,cmax:5})',r),'Actualmapmanualcolour');require(len(page.evaluate('window.task1ExperimentFieldMaps.getClipping()'))==3,'All3mapsclipcounts')
     require(not errors,'JS errors: '+str(errors));page.set_viewport_size(dict(width=390,height=844));require(page.evaluate('document.documentElement.scrollWidth')<=392,'Mobile390width');new(OUT/'GUI/validation.json',dict(status='browser_verified',JS_errors=errors,native_maps=3,chart_variable_ranges_persist=True,shared_manual_colour=True,clipping_counts=True,mobile_width=390,new_PDE=0))
    finally:context.close()
   guard()
   # All smaller originals/failure logs/config/classes/source survive together.
   archive=OUT/'evidence.tar.gz'
   with tarfile.open(archive,'w:gz')as tar:
    for p in RUN.rglob('*'):
     if not p.is_file()or p.is_relative_to(OUT)or'bases'in p.relative_to(RUN).parts or'tmp'in p.relative_to(RUN).parts or p.suffix=='.npz':continue
     tar.add(p,arcname=p.relative_to(RUN).as_posix(),recursive=False)
    for p in(OUT/'source').glob('*.py'):tar.add(p,arcname='report-source/'+p.name,recursive=False)
   files={PUBLIC+'/'+p.relative_to(RUN).as_posix():p for p in basis.iterdir()if p.is_file()}
   for rel in ['native-sha256.json','execute-receipt.json','postprocess-receipt.json','publish-results-receipt.json','modulation-completion/summary.json','modulation-completion/scalars.npz','modulation-completion/receipt.json','modulation-completion/artifact-sha256.json','postprocess/summary.json','postprocess/scalars.npz'] :files[PUBLIC+'/'+rel]=RUN/rel
   files[PUBLIC+'/publication-recovery/evidence.tar.gz']=archive;files[PUBLIC+'/publication-recovery/registration.json']=OUT/'registration.json'
   files.update({DOC+'/'+p.name:p for p in(OUT/'GUI').glob('*')if p.is_file()});files[DOC+'/completed-summary.json']=RUN/'modulation-completion/summary.json';files.update({'tools/experiment_report_20261025/'+p.name:p for p in(OUT/'source').glob('*.py')})
   require(api('git/ref/heads/'+BRANCH)['object']['sha']==PARENT,'Remoteadvancepreserved');base=api('git/commits/'+PARENT)['tree']['sha'];cache={}
   for p in [RUN/'source-publication.json',Path('/dev/shm/task1-human-tissue-20261025-run/result-publication.json')]:
    prior=read(p)
    for v in prior['files'].values():
     if v['readback_passed']:cache[v['Git_blob_SHA']]=(v,str(p),sha(p))
   records=[];proof={}
   for target,p in files.items():
    raw=p.read_bytes();require(len(raw)<=64*1024**2,'Blobbound');records.append(dict(target=target,path=p,SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()))
   def check(rec):
    cached=cache.get(rec['blob'])
    if cached and cached[0]['SHA256']==rec['SHA256']and cached[0]['bytes']==rec['bytes']:return dict(**rec,verified=True,proof_kind='reused_prior_full_immutable_readback',prior_receipt_SHA256=cached[2])
    got=api('git/blobs/'+rec['blob'],missing=True)
    if got is None:return dict(**rec,verified=False)
    back=base64.b64decode(got['content']);require(got['sha']==rec['blob']and len(back)==rec['bytes']and hashlib.sha256(back).hexdigest()==rec['SHA256'],'Full immutable GETreadback');return dict(**rec,verified=True,proof_kind='fresh_full_immutable_readback')
   with ThreadPoolExecutor(max_workers=2)as pool:checked=list(pool.map(check,records))
   published_this_stage=set()
   for rec in checked:
    guard()
    if rec['blob']in published_this_stage:rec.update(verified=True,proof_kind='fresh_full_immutable_readback_same_stage')
    if not rec['verified']:
     raw=rec['path'].read_bytes();created=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST');require(created['sha']==rec['blob'],'POSTdeterministicidentity');back=base64.b64decode(api('git/blobs/'+rec['blob'])['content']);require(len(back)==rec['bytes']and hashlib.sha256(back).hexdigest()==rec['SHA256'],'Fullnewblobreadback');rec.update(verified=True,proof_kind='fresh_full_immutable_readback')
    published_this_stage.add(rec['blob'])
    proof[rec['target']]=dict(SHA256=rec['SHA256'],bytes=rec['bytes'],Git_blob_SHA=rec['blob'],readback_passed=True,proof_kind=rec['proof_kind'])
    # Immutable progress survives another deadline without another full sweep.
    new(OUT/('verified-'+str(len(proof))+'.json'),dict(path=rec['target'],**proof[rec['target']]))
   tree=api('git/trees',dict(base_tree=base,tree=[dict(path=r['target'],mode='100644',type='blob',sha=r['blob'])for r in checked]),'POST')['sha'];commit=api('git/commits',dict(message='Recover2k native publication, retain failure evidence and add same-scale native-field GUI',tree=tree,parents=[PARENT]),'POST')['sha'];receipt['created_commit']=commit
   require(api('git/ref/heads/'+BRANCH)['object']['sha']==PARENT,'Concurrentbranchadvance');api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');require(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Refreadback');new(RUN/'result-publication.json',dict(status='published_readback_verified',commit=commit,files=proof))
   body='2000/2010 Hz 실제 새 PDE4RHS와 완성된2074방향 변조 후처리를 게시했습니다. 원래35초 후처리에서 중단·폐기한 각도 검색은 별도10.79초 유한 후처리로 저장E에서 완성했으며 새PDE0입니다. 원래요약/게시75초 timeout과 로그를 보존했습니다. 작은증거는 archive로 묶고 기존 불변소스 readback proof를 재사용하여 게시를 복구했습니다.\n\n목표mean/P10=0.07773685/0.07045450 V/m; 같은문헌3k sine=0.10724899/0.09724878. 각출력1Vpp RMS전류=0.0161680/0.0162238mA,전원2.59727µW. 같은출력RMS전류합(회계용)에서는목표mean0.1109004,같은전원전력0.0923039,문헌3k의8개부담상한을함께지키면0.0869625V/m(접촉전압제한)입니다. 기존팬텀3k의복합상한에서는SC손실때문에0.0675658V/m로제한됩니다. 전류합정규화는정전류구동/안전성 검증이아닙니다.\n\nSC계면2점진단전체16.775%/외곽50.090%,사전5%QA실패를유지하며 전체수렴/후보채택/활성화/안전은미검증입니다. 얇은SC의큰E와SC제외표층을구별합니다. 실제장비배선은미확인이고4pads/2outputs/commonreturn/각50Ω와inactive0V/50Ω모델시나리오입니다.\n\nGUI(3정현파비교·같은색범위native단면·수동축): https://github.com/'+REPO+'/raw/'+commit+'/'+DOC+'/index.html\n완성요약: https://github.com/'+REPO+'/blob/'+commit+'/'+DOC+'/completed-summary.json\n원시자료: https://github.com/'+REPO+'/tree/'+commit+'/'+PUBLIC+'\n\n원본과실패를보존했고Windows저장/OneDrive동기화는미확인입니다. 원래13800초CPU시간예산만사용했고 설치/삭제/보안변경/main병합/중복PDE워커는없습니다.'
   comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='native_results_and_GUI_published_readback_verified',result_commit=commit,public_files_verified=len(proof),native_files_verified=len(list(basis.iterdir())),comment_url=comment['html_url'])
  except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   with mu:live=bounded.owned_descendants(pid,ticks,dict(owned))
   for p,t in live.items():
    if p!=pid and bounded.live(p,t):
     try:os.kill(p,signal.SIGKILL)
     except ProcessLookupError:pass
   elapsed=time.monotonic()-start;ledger=policy.load_ledger(LEDGER);ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=RUN.name,stage='compact_publication_and_GUI_recovery',status=receipt['status'],seconds=elapsed,finished_utc=bounded.now()));tmp=LEDGER.with_name('task1-budget-recovery.tmp')
   with tmp.open('x')as f:json.dump(ledger,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
   os.replace(tmp,LEDGER);receipt.update(elapsed_seconds=elapsed,finished_utc=bounded.now(),remaining_approved_seconds=policy.remaining_seconds(ledger),resources=state);new(OUT/'receipt.json',receipt)
   for s,v in handlers.items():signal.signal(s,v)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
