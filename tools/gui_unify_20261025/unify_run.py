#!/usr/bin/env python3
"""Finite display-only reconciliation of today's requested GUI features. No PDE."""
import sys
sys.dont_write_bytecode=True
import os,json,re,base64,hashlib,subprocess,time,signal,threading,shutil,argparse,tempfile
from pathlib import Path
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
os.environ['GODEBUG']='http2client=0'
ROOT=Path('/workspace/ngg-tis-task1');SOURCE=Path('/dev/shm/task1-gui-unify-20261025/source');DEFAULT=Path('/dev/shm/task1-gui-unified-20261025-output');LEDGER=ROOT/'runtime/task1-budget.json'
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020';PUBLIC='docs/TASK1_UNIFIED_GUI_20261025';SRC_PUBLIC='tools/gui_unify_20261025'
CAPS={'build':20,'publish':55,'export':10,'persist':5};RESERVE={'build':320,'publish':300,'export':245,'persist':235};GIB=1024**3
sys.path[:0]=[str(SOURCE),str(ROOT/'tools')]
import task1_bounded_continuation as bounded
import task1_resource_policy as policy

def require(ok,m):
 if not ok:raise ValueError(m)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def new(p,x):
 with Path(p).open('x',encoding='utf-8')as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def size(p):
 p=Path(p)
 if not p.exists():return 0
 if p.is_file():return p.stat().st_size
 n=0
 for q in p.rglob('*'):
  try:
   if q.is_file():n+=q.stat().st_size
  except FileNotFoundError:pass
 return n
def sourcepins():return {str(p):sha(p)for p in sorted(SOURCE.iterdir())if p.is_file()and p.suffix in('.py','.md','.json')}
def old_publication(folder,target):
 p=Path(folder)/'result-publication.json';x=read(p);require(x['status']=='published_readback_verified'and x['files'][target]['readback_passed'],'Verified preserved view publication');return x['commit'],x['files'][target]['SHA256']

def inputs():
 records={
 'human':dict(path='/workspace/task1-human-report-20261025/GUI/results/index.html',file='views/human-current.html',pub='/dev/shm/task1-human-report-20261025-output',target='docs/TASK1_HUMAN_REFERENCE_REPORT_20261025/index.html',label='사람 문헌 비교',model='HREF-MIX-v1: 전완 SC·VS, 인간 전도도와 혼합 출처 유전율',run_id='task1-human-tissue-20261025-run / task1-human-sc4-20261025-run',topology='4 pads / 2 outputs / common return / 50 Ω',validation='계산·보존검사 및 SC 인접 비교 완료; 전체 수렴·실험 미검증',source_commit='8b50883a66ab270ea0a43b4abeeacc1ce9e4aa7a',limitations='dermis 위치는 VS(LE+DE) 대체층. 흉복부 직접 물성·새 Best5/C1/프로브 예측은 미계산.'),
 'manual':dict(path='/dev/shm/task1-manual-ranges-20261025-r2/results/index.html',file='views/manual-phantom.html',pub='/dev/shm/task1-manual-ranges-20261025-r2',target='docs/TASK1_MANUAL_RANGES_20261025/index.html',label='기존 best1/C1·전기장·파형',model='기존 팬텀 가정 물성; 사람 문헌 모델과 별도',run_id='rounded-expand-f35b23a22166 / centered-square15-C1-y0-xy80-f3000',topology='TIS 4 pads / 2 outputs / common return; C1 2 pads / 1 output / y=0',validation='기존 실제 계산과 22개 수동 그래프 검증; 전체 수렴·장비 부하 미검증',source_commit='70a551dab57e85576820406825ee418529687cc6',limitations='단일 전극쌍은 귀환 포함 2전극. RMS 일치는 생리적 활성화 일치가 아님. 기존 source/run/원시 통계 유지.'),
 'top5':dict(path=str(ROOT/'docs/TASK1_TOP5_20261022_compact/index.html'),file='views/top5-phantom.html',label='기존 전극 Best5',model='기존 팬텀 가정 물성에서의 후보 순위',run_id='task1-top5-context-20261022 / 기존 후보별 run 참조',topology='기준 4 pads / 2 outputs / common return; 4·8·12·16 pad 대조 별도',validation='기존 후보 보존; 수렴·실험 미검증. 이번 변경은 표시용 눈금만.',source_commit='317cd38af623d02a902d6b713d6433fb8f8800fc',result_commit='f0749c17b99a4d4096b9b0fdbd070a3518190651',expected_SHA256='b7b76be60f82ee14e494f08c8982a99907ca8c75cf7942a8498163bf613e0400',limitations='새 사람 문헌 물성의 Best5가 아님. packed 과학 데이터와 순위는 보존하고 모든 배치의 공통 수동 축·색 범위만 추가.'),
 'sc':dict(path='/workspace/task1-all-layer-20261025/GUI/results/index.html',file='views/sc-sensitivity.html',pub='/dev/shm/task1-all-layer-report-20261025',target='docs/TASK1_ALL_LAYER_REPORT_20261025/index.html',label='이전 SC 민감도',model='SC εr110000→1100 가정 민감도; 나머지 기존 물성 유지',run_id='task1-all-layer-sensitivity-20261025-run / task1-all-layer-sc4-check-20261025-run',topology='4 pads / 2 outputs / common return / 50 Ω',validation='계산·SC 인접 비교 완료; 물성 교정·전체 수렴 미완료',source_commit='3b9fd031f42226201f1578307cebd4b67466332a',limitations='문헌 기반 사람 모델과 별도 가정 민감도이며 후보 채택·안전·활성화 검증 아님.')}
 pins={}
 for k,v in records.items():
  p=Path(v['path']);require(p.is_file()and not p.is_symlink(),'Existing preserved page')
  if 'pub'in v:v['result_commit'],v['expected_SHA256']=old_publication(v['pub'],v['target'])
  require(sha(p)==v['expected_SHA256'],'Preserved page SHA mismatch '+k);pins[str(p)]=v['expected_SHA256']
 extra={
 'c1':Path('/dev/shm/task1-centered-c1-y0-20261025-final-r4/results/native-phi-probe40.json'),
 'tis':ROOT/'docs/cloud-rounded-drive-expansion-20261021T214000Z/rounded-expand-f35b23a22166/probes.json',
 'analysis':Path('/dev/shm/task1-centered-c1-y0-20261025-final-r4/results/analysis.json'),
 'audit':SOURCE.parent/'audit/requested-features-audit.json',
 'storage':ROOT/'runtime/task1-storage-policy.json'}
 for p in extra.values():require(p.is_file()and not p.is_symlink(),'Required processed metadata');pins[str(p)]=sha(p)
 return records,extra,pins

def browser_check(out,guard,state):
 from playwright.sync_api import sync_playwright
 errors=[];requests=[];checks={}
 def ready(frame,expression):
  until=time.monotonic()+10
  while not frame.evaluate('Boolean('+expression+')'):
   guard();require(time.monotonic()<until,'Browser view readiness timeout: '+expression);frame.wait_for_timeout(50)
 with tempfile.TemporaryDirectory(prefix='task1-unify-browser-',dir='/dev/shm')as temp:
  temp=Path(temp)
  with sync_playwright()as engine:
   context=engine.chromium.launch_persistent_context(str(temp/'profile'),executable_path='/usr/bin/chromium',headless=True,viewport=dict(width=1450,height=1050),env=dict(os.environ,TMPDIR=str(temp),TMP=str(temp),TEMP=str(temp),XDG_CONFIG_HOME=str(temp/'config'),XDG_CACHE_HOME=str(temp/'cache')),ignore_default_args=['--disable-dev-shm-usage'],args=['--disk-cache-size=0','--media-cache-size=0'])
   try:
    page=context.pages[0];page.route('https://tis-gui.test/**',lambda route: route.fulfill(path=str(out/(route.request.url.split('https://tis-gui.test/',1)[1].split('?',1)[0]or'index.html')),content_type='text/html'));page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url)if r.url.startswith(('http:','https:'))and not r.url.startswith('https://tis-gui.test/')else None)
    page.goto('https://tis-gui.test/index.html',wait_until='load');ready(page,'window.task1UnifiedGUI')
    ids=page.evaluate('window.task1UnifiedGUI.viewIds()');require(len(ids)>=14,'All requested navigation groups')
    for ident in ['human-fields','top5','pair','paper-waveforms','field-shape','probes','pad-count']:
     guard();page.evaluate('(id)=>window.task1UnifiedGUI.select(id)',ident);page.wait_for_timeout(120)
     frame=page.frames[-1];expected={'human-fields':'window.task1WholeLayerView','sc-sensitivity':'window.task1WholeLayerView','top5':'window.task1Top5Manual','pad-count':'window.task1Top5Manual'}.get(ident)
     if expected:ready(frame,expected)
     else:ready(frame,'document.readyState==="complete"')
     require(page.locator('iframe').count()==1,'Exactly one active view iframe');require(page.locator('#view-model').inner_text().strip(),'Model context badge')
     checks[ident]=dict(loaded=True,model=page.locator('#view-model').inner_text(),canvases=frame.locator('canvas').count())
     if ident=='top5':
      before=frame.evaluate('JSON.stringify(window.task1Top5.catalog)');ranges=frame.evaluate('window.task1Top5Manual.getState()')
      custom=dict(ranges,xMin=-15,xMax=15,yMin=-20,yMax=20,zMin=0,zMax=25,eMin=0,eMax=10,jMin=0,jMax=12,burdenMax=2)
      require(frame.evaluate('(v)=>window.task1Top5Manual.setRanges(v)',custom),'Top5 actual manual setter')
      for select in ['mode','metric','plane']:
       options=frame.locator('#'+select+' option').evaluate_all('(a)=>a.map(x=>x.value)')
       for value in options[:2]:guard();frame.select_option('#'+select,value);require(frame.evaluate('window.task1Top5Manual.getState()')==custom,'Top5 limits reset on variable change')
      require(not frame.evaluate('(v)=>window.task1Top5Manual.setRanges({...v,eMax:-1})',custom),'Top5 invalid range rejected')
      require(frame.evaluate('JSON.stringify(window.task1Top5.catalog)')==before,'Top5 catalog/rank/science mutated')
      clipping=frame.evaluate('window.task1Top5Manual.getClipping()');require(len(clipping)==12 and all(v['max']in(10,12)for v in clipping),'Shared E/J colour limits across all cases')
      frame.evaluate('window.task1Top5Manual.reset()');checks[ident].update(manual_ranges=True,mode_persistence=True,catalog_unchanged=True,clipping_disclosed=True)
     if ident=='probes':
      require(frame.locator('tr[data-probe]').count()>=40,'Actual40probe rows visible');require('무부하'in frame.locator('body').inner_text(),'Unloaded prediction disclosure');checks[ident]['probe_rows']=frame.locator('tr[data-probe]').count()
    checks['sc-sensitivity']=dict(status='byte-identical previously verified view; no repeated browser load to preserve aggregate RAM',previous_published_commit='5d1e7ab24dd7ba933aeb80f178a90e56515cce12');page.screenshot(path=str(out/'preview.jpg'),type='jpeg',quality=78,full_page=False)
    page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(100);require(page.evaluate('document.documentElement.scrollWidth')<=392,'Hub mobile width')
    require(not errors and not requests,'Offline JS or request failure: '+str(errors[:2]))
    return dict(status='passed',navigation_ids=ids,views=checks,one_active_iframe=True,browser_transport='all requests fulfilled from saved HTML by test route; file navigation is blocked by managed browser policy; no security settings changed',JS_errors=errors,external_requests=requests,mobile_width=390,new_PDE=0)
   except BaseException:
    new(out/'browser-failure.json',dict(JS_errors=errors,external_requests=requests,checks=checks));raise
   finally:context.close()

def main():
 a=argparse.ArgumentParser();group=a.add_mutually_exclusive_group(required=True)
 for k in CAPS:group.add_argument('--'+k,action='store_true')
 a.add_argument('--output',default=str(DEFAULT));a.add_argument('--parent');a.add_argument('--attempt',default='first');args=a.parse_args();stage=next(k for k in CAPS if getattr(args,k));run=Path(args.output)
 require(run.parent==Path('/dev/shm')and run.name.startswith('task1-gui-unified-20261025-output'),'Unique canonical GUI output');require(re.fullmatch('[A-Za-z0-9_-]{1,25}',args.attempt),'Safe attempt label')
 require(stage not in('publish','export')or re.fullmatch('[0-9a-f]{40}',args.parent or''),'Exact topic parent required')
 with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
  ledger=policy.load_ledger(LEDGER);require(policy.remaining_seconds(ledger)>=RESERVE[stage],'Existing finite time admission; no budget expansion')
  if stage=='build':require(not run.exists(),'Preserve all prior attempts');run.mkdir();(run/'results').mkdir();(run/'logs').mkdir()
  else:require(run.is_dir()and not run.is_symlink(),'Existing canonical GUI run')
  out=run/'results';receiptpath=run/(stage+'-'+args.attempt+'-receipt.json');require(not receiptpath.exists(),'Immutable stage receipt')
  start=time.monotonic();deadline=start+CAPS[stage];os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});pid=os.getpid();ticks=bounded.ticks(pid);state=dict(owned={pid:ticks},peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0,phase=stage);stop=threading.Event()
  receipt=dict(schema='task1-unified-gui-stage-v1',stage=stage,status='failed_preserved',pid=pid,proc_start_ticks=ticks,started_utc=bounded.now(),remaining_before_seconds=policy.remaining_seconds(ledger),stage_cap_seconds=CAPS[stage],new_PDE=0,new_native_E_phi_decode=0,storage_capacity_guards_enabled=False)
  def guard():
   live={p:t for p,t in bounded.owned_descendants(pid,ticks,state['owned']).items()if bounded.live(p,t)};rss=sum(bounded.rss(p)for p in live);owned=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));state.update(owned=live,peak_RSS=max(rss,state['peak_RSS']),peak_owned_tmpfs=max(owned,state['peak_owned_tmpfs']),peak_accounted=max(rss+owned,state['peak_accounted']))
   require(time.monotonic()<deadline,'Finite GUI deadline');require(rss+owned<=3*GIB,'Original RAM RSS plus all owned tmpfs3GiB')
  def interrupt(signum,frame):raise TimeoutError(state.get('error','Finite GUI stage interrupted'))
  def monitor():
   while not stop.wait(1):
    try:guard()
    except BaseException as error:state['error']=str(error);os.kill(pid,signal.SIGTERM);return
  previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
  for sig in previous:signal.signal(sig,interrupt)
  signal.setitimer(signal.ITIMER_REAL,CAPS[stage]);thread=threading.Thread(target=monitor,daemon=True);thread.start()
  def command(argv,body=None,allowed_failure=False):
   guard();child=subprocess.Popen(argv,cwd=SOURCE,stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(run),TMP=str(run),TEMP=str(run)))
   state['owned'][child.pid]=bounded.ticks(child.pid)
   try:
    raw,error=child.communicate(input=body,timeout=max(.01,deadline-time.monotonic()));require(len(raw)<=96*1024**2 and len(error)<=2*1024**2,'Finite subprocess bytes')
    if child.returncode:
     new(run/'logs'/('failed-'+stage+'-'+str(child.pid)+'.json'),dict(argv=argv,returncode=child.returncode,stderr=error.decode(errors='replace')[:8000],stdout_prefix=raw[:16000].decode(errors='replace')));require(allowed_failure,'Subprocess failed; evidence preserved')
    return child.returncode,raw,error
   finally:
    if child.poll()is None:child.kill();child.wait(timeout=3)
  def api(endpoint,obj=None,method='GET',missing=False):
   argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
   if obj is not None:argv+=['--input','-']
   body=None if obj is None else json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode()
   for attempt in range(2 if method=='GET'else 1):
    code,raw,error=command(argv,body,True)
    if code==0:return json.loads(raw)
    if missing and method=='GET'and b'(HTTP 404)'in error:return None
    if method!='GET'or attempt:raise ValueError('GitHub '+method+' failed; no blind mutation retry')
  def publish(files,parent,message):
   require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Remote advanced; preserve other work')
   base=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
   for target,path in files.items():
    guard();p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<=64*1024**2,'Provider/format file bound');raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest();gitsha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();blob=api('git/blobs/'+gitsha,missing=True)
    if blob is None:
     try:blob=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST')
     except ValueError:blob=api('git/blobs/'+gitsha,missing=True);require(blob is not None,'Uncertain POST not confirmed by readonly lookup')
    require(blob['sha']==gitsha,'Gitblob identity');back=base64.b64decode(api('git/blobs/'+gitsha)['content']);require(back==raw,'Full immutable bytes readback');del raw,back
    entries.append(dict(path=target,mode='100644',type='blob',sha=gitsha));proof[target]=dict(SHA256=h,bytes=p.stat().st_size,Git_blob_SHA=gitsha,readback_passed=True)
   tree=api('git/trees',dict(base_tree=base,tree=entries),'POST')['sha'];commit=api('git/commits',dict(message=message,tree=tree,parents=[parent]),'POST')['sha'];receipt['created_remote_commit']=commit
   require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrent work advanced branch');api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');require(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Ref readback');return dict(status='published_readback_verified',commit=commit,files=proof)
  def verify(pins):
   for p,h in pins.items():guard();require(sha(p)==h,'Pinned original/source changed: '+p)
  try:
   guard()
   if stage=='build':
    records,extra,pins=inputs();spins=sourcepins();new(run/'registration.json',dict(schema='task1-gui-reconciliation-registration-v1',source_sha256=spins,input_sha256=pins,new_PDE=0,question='Restore requested GUI coverage while preserving source model separation',limits=dict(CPU=1,RSS_plus_all_owned_tmpfs_bytes=3*GIB,stage_caps_seconds=CAPS,storage_capacity_guards_enabled=False)))
    import unify_gui,top5_ranges,probe_view
    metadata={}
    for key,record in records.items():
     guard();target=out/record['file'];target.parent.mkdir(exist_ok=True);raw=Path(record['path']).read_bytes()
     if key=='top5':
      text=top5_ranges.apply(raw.decode());original_block=re.search(r'<script[^>]*type="application/gzip"[^>]*>(.*?)</script>',raw.decode(),re.S)
      if original_block:require(original_block.group(1)in text,'Packed scientific payload byte preservation')
      raw=text.encode()
     with target.open('xb')as f:f.write(raw)
     metadata[key]={k:v for k,v in record.items()if k not in('path','pub','target','expected_SHA256')};metadata[key].update(SHA256=sha(target),bytes=target.stat().st_size,original_SHA256=record['expected_SHA256'],display_adapter=key=='top5')
    probe=probe_view.build(read(extra['c1']),read(extra['tis']),read(extra['analysis']))
    document=probe['html']if isinstance(probe,dict)else probe
    document=document.replace('</header>','<p>이 표의 전압 envelope는 전기장 최대 방향 TIS 지표와 다릅니다. 파형의 표본 Vpp/RMS는 선택한 시간창의 값이며, 표의 원래 공통주기 Vpp 경계/RMS와 구분합니다.</p></header>',1)
    with(out/'views/probes.html').open('x')as f:f.write(document)
    metadata['probe']=dict(file='views/probes.html',label='실제 저장된40점 차동 전압',model='기존 팬텀 가정의 TIS f35와 중앙 C1 무부하 예측',run_id='rounded-expand-f35b23a22166 / centered-C1-y0',topology='TIS4pads/2outputs/commonreturn; C1twoelectrodes/oneoutput',validation='기존 native-phi 후처리 완료; 장비 부하/실측 미검증',source_commit=None,result_commit=None,limitations='5mm는 팁 간격이며 중심 위치±5mm와 별개. ETA5001 감쇠·표시배율과 물리적 부하를 구분. 사람 모델 프로브는 미계산.',SHA256=sha(out/'views/probes.html'),bytes=(out/'views/probes.html').stat().st_size)
    if isinstance(probe,dict):new(out/'probe-view-manifest.json',{k:v for k,v in probe.items()if k!='html'})
    hub=unify_gui.build(metadata,generated_utc=bounded.now())
    with(out/'index.html').open('x')as f:f.write(hub['html'])
    new(out/'manifest.json',hub['manifest']);new(out/'first-build-failure.json',read(Path('/dev/shm/task1-gui-unified-20261025-output/build-first-receipt.json')));new(out/'requested-features-audit.json',read(extra['audit']));new(out/'input-sha256.json',pins);new(out/'prior-build-failures.json',[read(p) for p in Path('/dev/shm').glob('task1-gui-unified-20261025-output*/build-first-receipt.json')])
    for p in out.rglob('*.html'):
     for i,script in enumerate(re.findall(r'<script>(.*?)</script>',p.read_text(),re.S)):
      q=run/'logs'/(p.stem+'-'+str(i)+'.js')
      with q.open('x')as f:f.write(script)
      command(['node','--check',str(q)])
    validation=browser_check(out,guard,state);new(out/'validation.json',validation);verify(pins);verify(spins)
    new(run/'build-manifest.json',dict(status='built_browser_verified',source_sha256=spins,input_sha256=pins,files={p.relative_to(out).as_posix():dict(SHA256=sha(p),bytes=p.stat().st_size)for p in out.rglob('*')if p.is_file()}));receipt.update(status='unified_GUI_built_browser_verified',validation=validation)
   else:
    built=read(run/'build-manifest.json');require(built['status']=='built_browser_verified','Verified build required');verify(built['source_sha256']);verify(built['input_sha256'])
    for relative,item in built['files'].items():require(sha(out/relative)==item['SHA256'],'Built result changed')
    if stage=='publish':
     files={PUBLIC+'/'+p.relative_to(out).as_posix():p for p in out.rglob('*')if p.is_file()};files.update({SRC_PUBLIC+'/'+p.name:p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')});files[PUBLIC+'/evidence/registration.json']=run/'registration.json';files[PUBLIC+'/evidence/build-receipt.json']=run/'build-first-receipt.json'
     pub=publish(files,args.parent,'Restore today requested TIS GUI navigation, manual Top5 ranges and saved probe40 details');new(run/'result-publication.json',pub)
     body='오늘 GUI 요청을 대조해 최신 사람 물성 화면에서 빠졌던 기존 Best5·y=0 C1·전극/전기장벡터·carrier/envelope/파형·프로파일·패드가족·프로브·수동눈금 접근을 하나의 오프라인 GUI로 통합했습니다. 기존자료와 새 사람 문헌 모델은 화면상단에 물성/run/검증상태로 구분합니다. Top5의18개수치캔버스에 공통수동XYZ/E/J/막대축을 추가했고 packed과학데이터는byte보존했습니다. 기존저장복소전위차에서40점무부하Vpp/RMS·파형·스펙트럼을 보여주며 인간모델의미계산Best5/C1/프로브나장비부하검증을만들어내지않습니다. 새PDE/원시E·phi decode0,이전GUI와원본/실패보존,storageguardsOFF,CPU/RAM/시간예산유지입니다.\n\nGUI: https://github.com/'+REPO+'/raw/'+pub['commit']+'/'+PUBLIC+'/index.html\n\n모든하위HTML을함께다운로드해야오프라인탭이작동합니다. 실제Windows저장/OneDrive동기화는미확인입니다.'
     comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='unified_GUI_published_readback_verified',result_commit=pub['commit'],comment_url=comment['html_url'],public_files_verified=len(pub['files']))
    elif stage=='export':
     require(not(run/'export-publication.json').exists(),'Preserve existing export');pub=read(run/'result-publication.json')
     sys.path.insert(0,'/dev/shm/task1-human-report-20261025/source');import human_export
     entries=human_export.build_entries([('GUI',pub)]);script=human_export.powershell_document(entries)
     with(out/'Save-TIS-Unified-GUI.ps1').open('x',encoding='ascii')as f:f.write(script)
     new(out/'windows-export-manifest.json',human_export.manifest_document(entries));result=publish({PUBLIC+'/'+n:out/n for n in('Save-TIS-Unified-GUI.ps1','windows-export-manifest.json')},args.parent,'Add verified Windows handoff for all unified offline GUI pages');new(run/'export-publication.json',result);receipt.update(status='unified_GUI_export_published',result_commit=result['commit'],download_files=len(entries),download_bytes=sum(x['bytes']for x in entries))
    else:
     destination=Path('/workspace/task1-gui-unified-20261025');require(not destination.exists(),'Preserve prior durable GUI');destination.mkdir();proof={}
     for p in out.rglob('*'):
      if not p.is_file():continue
      guard();q=destination/p.relative_to(out);q.parent.mkdir(parents=True,exist_ok=True)
      with p.open('rb')as src,q.open('xb')as dst:shutil.copyfileobj(src,dst,1024**2)
      require(sha(p)==sha(q),'Durable output copy SHA');proof[q.relative_to(destination).as_posix()]=dict(SHA256=sha(q),bytes=q.stat().st_size)
     new(destination/'copy-receipt.json',dict(status='cloud_copy_verified',files=proof,Windows_saved=False,OneDrive_sync_verified=False,new_PDE=0));receipt.update(status='unified_GUI_cloud_copy_verified',cloud_destination=str(destination),files_copied=len(proof),bytes_copied=sum(v['bytes']for v in proof.values()),Windows_saved=False)
  except BaseException as error:receipt.update(error_type=type(error).__name__,error=str(error));raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   for p,t in bounded.owned_descendants(pid,ticks,state['owned']).items():
    if p!=pid and bounded.live(p,t):
     try:os.kill(p,signal.SIGKILL)
     except ProcessLookupError:pass
   elapsed=time.monotonic()-start;ledger=policy.load_ledger(LEDGER);ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=run.name,stage='gui_unification_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=bounded.now()));data=json.dumps(ledger,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode();tmp=LEDGER.with_name('task1-budget-gui-unification.tmp')
   with tmp.open('xb')as f:f.write(data)
   os.replace(tmp,LEDGER);receipt.update(finished_utc=bounded.now(),elapsed_seconds=elapsed,remaining_approved_seconds=policy.remaining_seconds(ledger),resources={k:v for k,v in state.items()if k.startswith('peak_')},free_root_bytes=shutil.disk_usage(ROOT).free);new(receiptpath,receipt)
   for sig,handler in previous.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
