#!/usr/bin/env python3
"""Finite source-only prepared controller for human-reference proxy report/export/persistence.

No PDE or work on import. Root explicitly selects one stage, owns the same two
execution locks and preserves every prior native/result/failure artifact.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse,base64,gzip,hashlib,io,json,os,re,shutil,signal,subprocess,tempfile,threading,time
from pathlib import Path
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-human-report-20261025/source')
DEFAULT_RUN=Path('/dev/shm/task1-human-report-20261025-output')
SC2=Path('/dev/shm/task1-human-tissue-20261025-run')
SC4=Path('/workspace/task1-human-sc4-20261025-run')
CASE='baseline-square15-human-reference-xy80'
OLD=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json'
LEDGER=ROOT/'runtime/task1-budget.json'
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020'
PUBLIC='docs/TASK1_HUMAN_REFERENCE_REPORT_20261025';PUBLIC_SOURCE='tools/human_report_20261025'
GIB=1024**3;MAX_FILE=64*1024**2;MAX_REPORT=128*1024**2;CAPS={'build':45,'publish':90,'export':20,'persist':25}
GATES={'max_residual':2e-7,'max_power_error':2e-7,'max_current_error':2e-6,'max_area_relative_error':1e-10,'max_interface_normal_current_relative_error':2e-7}
sys.path[:0]=[str(SOURCE),str(ROOT/'tools')]
import task1_bounded_continuation as bounded
import task1_resource_policy as policy

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def new_json(path,value):
    with Path(path).open('x',encoding='utf-8')as stream:json.dump(value,stream,ensure_ascii=False,allow_nan=False,indent=2)
def size(path):
    p=Path(path)
    if not p.exists():return 0
    if p.is_file():return p.stat().st_size
    total=0
    for item in p.rglob('*'):
        try:
            if item.is_file():total+=item.stat().st_size
        except FileNotFoundError:pass
    return total
def sources():return {str(p):sha(p)for p in sorted(SOURCE.iterdir())if p.is_file()and p.suffix in('.py','.md','.json')}
def load_publication(path,*,required=False):
    path=Path(path)
    if not path.is_file():
        require(not required,'Required result publication is unavailable: '+str(path));return None
    require(not path.is_symlink()and path.stat().st_size<2*1024**2,'Bounded publication receipt')
    pub=read(path)
    require(pub.get('status')=='published_readback_verified'and re.fullmatch('[0-9a-f]{40}',pub.get('commit',''))and
        isinstance(pub.get('files'),dict)and pub['files']and all(x.get('readback_passed')is True for x in pub['files'].values()),'Only immutable fully readback verified publications may be exported')
    return pub

def required_inputs(guard):
    """Verify local completed computation; native public posting is not required."""
    pins={}
    def pin(path,expected=None):
        guard();path=Path(path)
        require(path.is_file()and not path.is_symlink()and path==path.resolve()and path.stat().st_size<=MAX_FILE,'Canonical bounded report input')
        digest=sha(path);require(expected is None or digest==expected,'Report input SHA mismatch: '+str(path));pins[str(path)]=digest;return path
    for name in ('preregistration.json','source-publication.json','execute-receipt.json','postprocess-receipt.json','native-sha256.json','postprocess/artifact-sha256.json'):pin(SC2/name)
    pre=read(SC2/'preregistration.json');executed=read(SC2/'execute-receipt.json');post=read(SC2/'postprocess-receipt.json');pub=read(SC2/'source-publication.json')
    require(pre['case_id']==CASE and executed.get('new_native_conditions_completed')==1 and executed.get('new_native_RHS_completed')==8,'Actual completed one-condition/eight-RHS SC2 run required')
    require(post.get('status')=='new_native_postprocessed_human_reference_unadopted'and pub['status']=='published_readback_verified','Completed human-reference postprocess and pinned source publication required')
    for path,digest in {**pre['source_sha256'],**pre['class_sha256']}.items():pin(path,digest)
    pin(pre['config_file'],pre['config_sha256']);pin(pre['mask_file'],pre['mask_sha256'])
    native=read(SC2/'native-sha256.json')['files'];basis=SC2/'bases'/CASE
    for name in ('grid.csv.gz','mesh-metadata.json','validation.json','BASIS_COMPLETE'):
        path=basis/name;pin(path,native[str(path)])
    values=read(basis/'validation.json')
    for key,limit in GATES.items():require(0<=values[key]<=limit,'Completed native gate failed: '+key)
    artifacts=read(SC2/'postprocess/artifact-sha256.json')
    for name in ('summary.json','scalars.npz'):
        path=SC2/'postprocess'/name;item=artifacts[name];require(path.stat().st_size==item['bytes'],'Derived artifact exact byte count');pin(path,item['SHA256'])
    require(pins[str(SC2/'postprocess/summary.json')]==post['summary_sha256']and pins[str(SC2/'postprocess/scalars.npz')]==post['scalar_archive_sha256'],'Postprocess receipt and artifact pins agree')
    pin(OLD,pre['old_input_sha256'][str(OLD)]);old=read(OLD);square=next(row for row in old['conditions']if row['waveform']=='square_3h')
    archive=OLD.parent/square['native_volume_archive'];item=old['artifacts']['files'][square['native_volume_archive']]
    pin(archive,item['SHA256']);require(pre['old_input_sha256'][str(archive)]==pins[str(archive)],'Original comparator archive identity')
    supplementary=Path('/dev/shm/task1-human-tissue-20261025/evidence/hershkovich2019-band-exclusion.json')
    if supplementary.is_file():pin(supplementary)
    pin(SC2/'material-input.json')
    return dict(pins=pins,baseline_archive=str(archive),source_commit=pub['commit'],native_grid=str(basis/'grid.csv.gz'),supplementary_json=str(supplementary)if supplementary.is_file()else None)

def browser_check(document,guard,state,out):
    """Smoke actual data and manual ranges with the already installed browser."""
    from playwright.sync_api import sync_playwright
    errors=[];requests=[]
    with tempfile.TemporaryDirectory(prefix='task1-human-report-browser-',dir='/dev/shm')as temporary:
        scratch=Path(temporary);state['scratch']=scratch
        for name in ('tmp','config','cache','dumps'):(scratch/name).mkdir()
        with sync_playwright()as engine:
            context=engine.chromium.launch_persistent_context(str(scratch/'p'),executable_path='/usr/bin/chromium',headless=True,viewport=dict(width=1450,height=1050),
                env=dict(os.environ,TMPDIR=str(scratch/'tmp'),TMP=str(scratch/'tmp'),TEMP=str(scratch/'tmp'),XDG_CONFIG_HOME=str(scratch/'config'),XDG_CACHE_HOME=str(scratch/'cache')),
                ignore_default_args=['--disable-dev-shm-usage'],args=['--disk-cache-size=0','--media-cache-size=0','--crash-dumps-dir='+str(scratch/'dumps')])
            try:
                page=context.pages[0];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text)if m.type=='error'else None)
                page.on('request',lambda q:requests.append(q.url)if q.url.startswith(('http:','https:'))else None)
                page.set_content(document,wait_until='load',timeout=30000);page.wait_for_function('window.task1WholeLayerView && document.querySelectorAll("#metric option").length>0',timeout=15000)
                summary_before=page.evaluate('JSON.stringify(JSON.parse(document.getElementById("payload").textContent).summary)')
                count=0
                for metric in page.locator('#metric option').evaluate_all('(a)=>a.map(e=>e.value)'):
                    page.select_option('#metric',metric)
                    for plane in page.locator('#plane option').evaluate_all('(a)=>a.map(e=>e.value)'):
                        guard();page.select_option('#plane',plane);require(page.locator('#scope').inner_text().strip(),'Actual report scope absent');count+=1
                page.select_option('#metric','total_E_RMS_V_m');page.select_option('#plane','0')
                for normal in page.locator('#normal option').evaluate_all('(a)=>a.map(e=>e.value)'):guard();page.select_option('#normal',normal)
                page.select_option('#normal','fixed_source_Vpp')
                before=page.evaluate('JSON.stringify(window.task1WholeLayerView.getState().range)')
                page.locator('#limits input[data-field="cmax"]').fill('-1');page.locator('#limits input[data-field="cmax"]').dispatch_event('change')
                require(page.evaluate('JSON.stringify(window.task1WholeLayerView.getState().range)')==before and page.locator('#range-error').inner_text().strip(),'Invalid range was not refused transactionally')
                for key,value in (('xmin',-5),('xmax',5),('ymin',15),('ymax',20),('cmin',0),('cmax',.00001)):
                    field=page.locator('#limits input[data-field="'+key+'"]');field.fill(str(value));field.dispatch_event('change')
                chosen=page.evaluate('window.task1WholeLayerView.getState().range');require(chosen['xmin']==-5 and chosen['xmax']==5 and chosen['ymin']==15 and chosen['ymax']==20 and chosen['cmax']==.00001,'Manual spatial/colour bounds not applied')
                info=page.locator('#new-info').inner_text();match=re.search(r'상한 초과\s+(\d+)',info);require(match is not None and int(match.group(1))>0,'Manual clipping count not disclosed')
                for id,value in (('bar-min',0),('bar-max',.5)):
                    page.locator('#'+id).fill(str(value));page.locator('#'+id).dispatch_event('change')
                chosen=page.evaluate('window.task1WholeLayerView.getState().range');require(chosen['barmin']==0 and chosen['barmax']==.5,'Manual graph ordinate bounds not applied')
                require(summary_before==page.evaluate('JSON.stringify(JSON.parse(document.getElementById("payload").textContent).summary)'),'Manual view changed Float64 summary')
                page.locator('#reset').click();page.screenshot(path=str(out/'preview.jpg'),type='jpeg',quality=78,full_page=False)
                page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(50);width=page.evaluate('document.documentElement.scrollWidth');require(width<=392,'Report mobile overflow')
                require(not errors and not requests,'Report JavaScript or external-request failure')
                return dict(status='passed',actual_data=True,metric_plane_combinations=count,normalization_choices=4,invalid_input_transaction=True,manual_axes=True,manual_colour_clipping_disclosed=True,manual_bar_ordinate=True,summary_unchanged=True,mobile_width=390,mobile_scroll_width=width,JS_errors=errors,external_requests=requests,new_PDE=0)
            except BaseException:
                new_json(out/'browser-failure.json',dict(JS_errors=errors,external_requests=requests,current_URL=page.url,HTML_bytes=len(document.encode())))
                raise
            finally:context.close()
    state.pop('scratch',None)

def main():
    parser=argparse.ArgumentParser();flags=parser.add_mutually_exclusive_group(required=True)
    for stage in CAPS:flags.add_argument('--'+stage,action='store_true')
    parser.add_argument('--parent');parser.add_argument('--output',default=str(DEFAULT_RUN));parser.add_argument('--attempt',default='first');args=parser.parse_args()
    stage=next(name for name in CAPS if getattr(args,name));run=Path(args.output)
    require(run.parent==Path('/dev/shm')and run.name.startswith('task1-human-report-20261025-output')and re.fullmatch('[A-Za-z0-9_.-]+',run.name),'Unique bounded report directory')
    require(re.fullmatch('[A-Za-z0-9_-]{1,24}',args.attempt),'Short immutable attempt identifier')
    require(stage in('build','persist')or re.fullmatch('[0-9a-f]{40}',args.parent or''),'Publish/export require exact --parent topic HEAD')
    require(Path(__file__).resolve()==SOURCE/'human_report_run.py','Frozen controller source path')
    with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledger=policy.load_ledger(LEDGER);require(policy.remaining_seconds(ledger)>=CAPS[stage],'Existing approved finite time admission')
        if stage=='build':
            require(not run.exists(),'Build needs a new output directory; preserve prior report attempts');run.mkdir()
            for name in ('results','logs','tmp'):(run/name).mkdir()
        else:require(run.is_dir()and run==run.resolve()and not run.is_symlink(),'Existing canonical report output required')
        out=run/'results';receiptpath=run/(stage+'-receipt-'+args.attempt+'.json');require(not receiptpath.exists(),'Stage attempt receipt already exists')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});pid=os.getpid();ticks=bounded.ticks(pid);start=time.monotonic();deadline=start+CAPS[stage]
        state=dict(owned={pid:ticks},phase='verify_inputs',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);stop=threading.Event()
        receipt=dict(schema='task1-human-reference-report-stage-v1',stage=stage,attempt=args.attempt,status='failed_preserved',started_utc=bounded.now(),pid=pid,proc_start_ticks=ticks,new_PDE=0,storage_capacity_guards_enabled=False,storage_override_policy_sha256=sha(ROOT/'runtime/task1-storage-policy.json'),remaining_before_seconds=policy.remaining_seconds(ledger),stage_cap_seconds=CAPS[stage])
        def guard():
            known=bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in known.items()if bounded.live(p,t)}
            rss=sum(bounded.rss(p)for p in live);owned=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],owned),peak_accounted=max(state['peak_accounted'],rss+owned))
            require(time.monotonic()<deadline and rss+owned<=3*GIB,'Finite time / all-owned tmpfs+RSS3GiB RAM gate; storage capacity guards disabled by explicit user override')
        def interrupt(sig,frame):raise TimeoutError(state.get('failure','Finite report stage interrupted'))
        def monitor():
            last=0
            while not stop.wait(1):
                try:
                    guard()
                    if time.monotonic()-last>5:
                        temp=run/'heartbeat.new';temp.write_text(json.dumps(dict(stage=stage,phase=state['phase'],pid=pid,proc_start_ticks=ticks,updated_utc=bounded.now(),new_PDE=0)));os.replace(temp,run/'heartbeat.json');last=time.monotonic()
                except BaseException as error:state['failure']=str(error);os.kill(pid,signal.SIGTERM);return
        previous={s:signal.getsignal(s)for s in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for sig in previous:signal.signal(sig,interrupt)
        signal.setitimer(signal.ITIMER_REAL,CAPS[stage]);thread=threading.Thread(target=monitor,daemon=True);thread.start()
        def command(argv,body=None,allow_failure=False):
            guard();child=subprocess.Popen([str(a)for a in argv],cwd=SOURCE,stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(run/'tmp'),TMP=str(run/'tmp'),TEMP=str(run/'tmp')))
            state['owned'][child.pid]=bounded.ticks(child.pid)
            try:
                raw,err=child.communicate(input=body,timeout=max(.01,deadline-time.monotonic()));require(len(raw)<=96*1024**2 and len(err)<=2*1024**2,'Bounded subprocess output')
                if child.returncode:
                    path=run/'logs'/('failed-'+stage+'-'+str(child.pid)+'.json')
                    new_json(path,dict(argv=[str(a)for a in argv],returncode=child.returncode,stdout_bytes=len(raw),stderr_bytes=len(err),stdout_SHA256=hashlib.sha256(raw).hexdigest(),stderr=err.decode(errors='replace')[:12000],stdout_prefix=raw[:16000].decode(errors='replace')))
                    require(allow_failure,'Finite command failed; see '+str(path))
                return child.returncode,raw,err
            finally:
                if child.poll()is None:child.kill();child.wait(timeout=3)
        def api(endpoint,obj=None,method='GET',missing=False):
            argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
            if obj is not None:argv+=['--input','-']
            body=None if obj is None else json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode()
            for attempt in range(2 if method=='GET'else 1):
                code,raw,err=command(argv,body,allow_failure=True)
                if code==0:return json.loads(raw)
                if missing and method=='GET'and b'(HTTP 404)'in err:return None
                if method!='GET'or attempt==1:raise RuntimeError('GitHub '+method+' failed; immutable failure evidence retained')
        def verify(pins):
            for path,digest in pins.items():guard();require(sha(path)==digest,'Pinned report/source input changed: '+path)
        def publish(files,parent,message):
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Topic HEAD advanced; no force/overwrite')
            base=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
            for target,path in files.items():
                guard();path=Path(path);require(path.is_file()and not path.is_symlink()and path.stat().st_size<=MAX_FILE,'Regular64MiB maximum publication file')
                raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest();blobsha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                blob=api('git/blobs/'+blobsha,missing=True)
                if blob is None:
                    try:blob=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST')
                    except RuntimeError:
                        # An unknown POST response is resolved only by reading the
                        # deterministic immutable object; no blind mutation retry.
                        blob=api('git/blobs/'+blobsha,missing=True);require(blob is not None,'Blob POST failed and immutable object not confirmed')
                require(blob['sha']==blobsha,'Exact Git blob identity')
                if 'content'in blob:
                    restored=base64.b64decode(blob['content']);require(restored==raw,'Existing immutable blob bytes differ');del restored
                entries.append(dict(path=target,mode='100644',type='blob',sha=blobsha));proof[target]=dict(SHA256=digest,bytes=len(raw),Git_blob_SHA=blobsha)
            tree=api('git/trees',dict(base_tree=base,tree=entries),'POST')['sha'];commit=api('git/commits',dict(message=message,tree=tree,parents=[parent]),'POST')['sha'];receipt['created_remote_commit']=commit
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrent topic advance; preserve created objects')
            api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');receipt['remote_ref_updated']=True
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Topic ref readback differs')
            for target,item in proof.items():
                guard();restored=base64.b64decode(api('git/blobs/'+item['Git_blob_SHA'])['content']);require(len(restored)==item['bytes']and hashlib.sha256(restored).hexdigest()==item['SHA256'],'Full RAM immutable readback differs');item['readback_passed']=True;del restored
            return dict(status='published_readback_verified',commit=commit,files=proof)
        try:
            guard()
            if stage=='build':
                pins=required_inputs(guard);pins['pins'][str(ROOT/'runtime/task1-storage-policy.json')]=sha(ROOT/'runtime/task1-storage-policy.json');sourcepins=sources();new_json(run/'input-source-registration.json',dict(schema='task1-human-reference-report-inputs-v1',source_sha256=sourcepins,input_sha256=pins['pins'],new_PDE=0,human_reference_native_case=CASE))
                state['phase']='report_source_contract_tests'
                code,testout,testerr=command([sys.executable,'-B','-m','unittest','discover','-s',str(SOURCE),'-p','test_*.py','-v'])
                with(run/'logs/report-source-tests.log').open('xb')as f:f.write(testout+testerr)
                state['phase']='actual_scalar_and_grid_decode';import numpy as np
                summary=read(SC2/'postprocess/summary.json');require(summary['case_id']==CASE and summary['actual_native_new_conditions']==1 and summary['actual_native_new_RHS']==8,'Completed actual native sensitivity summary')
                with gzip.open(pins['native_grid'],'rb')as stream:raw=stream.read(32*1024**2+1)
                require(len(raw)<=32*1024**2,'Bounded actual grid decode');grid=np.loadtxt(io.BytesIO(raw),delimiter=',',skiprows=1);del raw
                require(grid.shape==(summary['model']['cells'],5)and np.isfinite(grid).all(),'Actual human-reference same-grid shape and finite values')
                import human_report as renderer
                with np.load(SC2/'postprocess/scalars.npz',allow_pickle=False)as archive:arrays={name:np.array(archive[name],copy=True)for name in renderer.METRICS if name in archive}
                oldnames={x[2]for x in renderer.METRICS.values()if x[2]}
                with np.load(pins['baseline_archive'],allow_pickle=False)as archive:baseline={name:np.array(archive[name],copy=True)for name in oldnames if name in archive}
                require('RMS'in baseline and'maxTIS'in baseline,'Original same-grid RMS/maxTIS archive required')
                for name,value in {**arrays,**baseline}.items():require(value.shape==(len(grid),)and value.dtype==np.dtype('<f8')and np.isfinite(value).all(),'Finite exact Float64 scalar array: '+name)
                nativepub=load_publication(SC2/'result-publication.json');sc4pub=load_publication(SC4/'result-publication.json')
                import human_volume_audit
                with np.load(pins['baseline_archive'],allow_pickle=False)as weight_archive:
                    volume_weights={key:np.array(weight_archive['region_'+key+'_m3'],copy=True)for key in('target','surface_0_5','off_target','total')}
                volume_audit=human_volume_audit.build(summary,arrays['fundamental_maxTIS_2074_V_m'],baseline['maxTIS'],volume_weights,grid,guard)
                new_json(out/'high-modulation-volume-audit.json',volume_audit);del volume_weights
                report=renderer.build_report(summary,arrays,grid,baseline_arrays=baseline,run_id=SC2.name,source_commit=pins['source_commit'],result_commit=nativepub['commit']if nativepub else None,volume_audit=volume_audit)
                del arrays,baseline,grid;guard();state['phase']='report_write_syntax_and_browser'
                document=report['html']
                if sc4pub:
                    candidates=[k for k in sc4pub['files']if k.endswith('/summary.json')and k.startswith('docs/')]
                    if candidates:document=document.replace('</header>','<p><a href="https://github.com/'+REPO+'/blob/'+sc4pub['commit']+'/'+candidates[0]+'">새 문헌 대리물성 SC4 별도 인접 검증 (전체 수렴 미확립)</a></p></header>',1)
                with(out/'index.html').open('x')as f:f.write(document)
                with(out/'README.md').open('x')as f:f.write(report['markdown'])
                new_json(out/'report.json',report['report_json']);new_json(out/'summary.json',summary)
                new_json(out/'native-publication-links.json',dict(HUMAN_commit=nativepub['commit']if nativepub else None,HUMANSC4_commit=sc4pub['commit']if sc4pub else None,native_publication_required_for_local_build=False,local_human_reference_execution_and_postprocess_verified=True))
                scripts=re.findall(r'<script>(.*?)</script>',document,re.S);require(scripts,'Report executable inline script required')
                require(shutil.which('node'),'Existing node required; no installation')
                for i,script in enumerate(scripts):
                    path=run/'logs'/('inline-'+str(i)+'.js')
                    with path.open('x')as f:f.write(script)
                    command(['node','--check',str(path)])
                browser=browser_check(document,guard,state,out);verify(pins['pins']);verify(sourcepins)
                new_json(out/'validation.json',dict(status='actual_human_reference_report_manual_view_verified_unadopted',new_PDE=0,new_raw_E_phi_decode=0,new_native_grid_decode=1,browser=browser,input_sha256=pins['pins'],report_source_sha256=sourcepins,material_calibrated=False,full_convergence_validated=False,experimentally_validated=False,Windows_saved=False,OneDrive_sync_verified=False))
                manifest={p.relative_to(run).as_posix():dict(SHA256=sha(p),bytes=p.stat().st_size)for p in run.rglob('*')if p.is_file()and p.name not in('heartbeat.json','heartbeat.new')and'tmp'not in p.relative_to(run).parts}
                new_json(run/'build-manifest.json',dict(status='report_built_verified',files=manifest,source_sha256=sourcepins,input_sha256=pins['pins']))
                receipt.update(status='human_reference_report_built_browser_verified_unadopted',browser=browser)
            else:
                built=read(run/'build-manifest.json');require(built['status']=='report_built_verified','Passed actual report build required');verify(built['source_sha256']);verify(built['input_sha256'])
                for relative,item in built['files'].items():require((run/relative).stat().st_size==item['bytes']and sha(run/relative)==item['SHA256'],'Immutable built report changed')
                if stage=='persist':
                    state['phase']='cloud_workspace_verified_copy_originals_unchanged'
                    destination=Path('/workspace/task1-human-report-20261025')
                    require(destination.parent==Path('/workspace')and not destination.is_symlink(),'Exact durable cloud fallback destination')
                    destination.mkdir(exist_ok=True);proof={};total=0
                    collections=[('HUMAN',SC2),('GUI',run),('source/HUMAN',Path('/dev/shm/task1-human-tissue-20261025/source')),('source/report',SOURCE),('evidence',Path('/dev/shm/task1-human-tissue-20261025/evidence'))]
                    for label,source in collections:
                        if not source.is_dir():continue
                        for original in sorted(source.rglob('*')):
                            if not original.is_file()or original.is_symlink()or'tmp'in original.relative_to(source).parts or original.name in('heartbeat.json','heartbeat.new')or original==receiptpath:continue
                            if label=='evidence'and original.suffix!='.json':continue
                            guard();relative=label+'/'+original.relative_to(source).as_posix();target=destination/relative;expected=sha(original)
                            target.parent.mkdir(parents=True,exist_ok=True)
                            if target.exists():require(target.is_file()and not target.is_symlink()and sha(target)==expected,'Preserve conflicting durable cloud copy: '+str(target))
                            else:
                                with original.open('rb')as src,target.open('xb')as dst:shutil.copyfileobj(src,dst,1024**2)
                            require(sha(target)==expected and target.stat().st_size==original.stat().st_size,'Actual durable cloud copy SHA/bytes')
                            proof[relative]=dict(SHA256=expected,bytes=target.stat().st_size,original=str(original));total+=target.stat().st_size
                    durable_sc4=None
                    if SC4.is_dir():
                        require(SC4.parent==Path('/workspace')and SC4==SC4.resolve()and not SC4.is_symlink(),'Human SC4 existing durable originals')
                        durable_sc4=dict(directory=str(SC4),originals_copied_again=False,publication=load_publication(SC4/'result-publication.json'))
                    evidence=dict(status='cloud_workspace_copies_SHA256_verified_Windows_unconnected',destination=str(destination),files=proof,total_bytes=total,already_durable_SC4=durable_sc4,storage_capacity_guards_enabled=False,Windows_saved=False,OneDrive_sync_verified=False,originals_deleted=False)
                    new_json(destination/('copy-receipt-'+args.attempt+'.json'),evidence);new_json(run/('cloud-copy-receipt-'+args.attempt+'.json'),evidence)
                    receipt.update(status='cloud_workspace_copies_verified_Windows_unconnected',copied_files=len(proof),copied_bytes=total,cloud_destination=str(destination),Windows_saved=False)
                elif stage=='publish':
                    require(not(run/'result-publication.json').exists(),'GUI already published; no duplicate commit')
                    files={PUBLIC+'/'+p.name:p for p in out.iterdir()if p.is_file()}
                    files[PUBLIC_SOURCE+'/storage-policy.json']=ROOT/'runtime/task1-storage-policy.json'
                    files.update({PUBLIC_SOURCE+'/'+p.name:p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.md','.json')})
                    for name in ('input-source-registration.json','build-manifest.json'):files[PUBLIC+'/evidence/'+name]=run/name
                    own_evidence=Path('/dev/shm/task1-human-tissue-20261025/evidence/hershkovich2019-band-exclusion.json')
                    if own_evidence.is_file():files[PUBLIC+'/evidence/'+own_evidence.name]=own_evidence
                    for p in run.glob('build-receipt-*.json'):files[PUBLIC+'/evidence/'+p.name]=p
                    for p in(run/'logs').iterdir():
                        if p.is_file():files[PUBLIC+'/evidence/'+p.name]=p
                    pub=publish(files,args.parent,'Publish actual human-reference hybrid material field comparison and manual-range validation')
                    new_json(run/'result-publication.json',pub);summary=read(out/'summary.json')
                    body=('사람 조직 문헌 기반 혼합 대리물성의 실제 새1조건·8RHS 결과 GUI를 추가했습니다. SC는 Tsai2018 Eq89/90 전완 모델, dermis 슬롯은 Eq91/92 viable skin(LE+DE) 대리이며 순수 dermis가 아닙니다. 지방 전도도 및 근육 tensor trace/3 전도도와 Gabriel 혼합 출처 εr를 사용했으며 흉복부 직접 측정·공동 측정 복소 스펙트럼·교정된 팬텀을 뜻하지 않습니다.\n\nGUI: https://github.com/'+REPO+'/raw/'+pub['commit']+'/'+PUBLIC+'/index.html\n\n기존4패드·동일 ROI 원자료와 비교하고 전 층/목표/표층/비표적 통계, carrier/전체RMS·방향변조·2074방향 최대, 전도+변위J/전도J, 실제 층/접촉/전원 손실을 구분합니다. 원래 native loss로 재계산된 baseline 층 전력의 출처를 유지했습니다. 수동 축·색 범위와 잘린 셀 수는 원시 통계와 별도입니다. 동일 총전력/접촉Jmax/출력RMS전류합 정규화는 한 항목씩만 맞춘 비교이며 안전 기준 또는 실험 구동 제안이 아닙니다. 초기2k/2.01kHz는 이번에 재계산하지 않았습니다.\n\n보고 단계 새PDE0; 원본·실패·이전GUI를 보존했습니다. 물성 교정·전체SC/XY/bulk/edge/접촉 수렴·실험·생리활성화·안전·새 best 채택은 미검증입니다. 원 논문 전문을 게시하지 않았으며 실제 Windows/OneDrive 저장은 미확인입니다.')
                    comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='human_reference_GUI_published_full_readback_verified',result_commit=pub['commit'],comment_url=comment['html_url'],public_files_verified=len(pub['files']))
                else:
                    require(not(run/'export-publication.json').exists(),'Export already published; no duplicate commit')
                    import human_export as export
                    publications=[('HUMAN',load_publication(SC2/'result-publication.json',required=True)),('GUI',load_publication(run/'result-publication.json',required=True))]
                    optional=load_publication(SC4/'result-publication.json')
                    if optional:publications.append(('HUMANSC4',optional))
                    entries=export.build_entries(publications);script=export.powershell_document(entries)
                    with(out/'Save-TIS-Human-Results.ps1').open('x',encoding='ascii')as f:f.write(script)
                    new_json(out/'windows-export-manifest.json',export.manifest_document(entries))
                    files={PUBLIC+'/'+name:out/name for name in ('Save-TIS-Human-Results.ps1','windows-export-manifest.json')}
                    pub=publish(files,args.parent,'Add compact immutable Windows handoff for human-reference native results and GUI')
                    new_json(run/'export-publication.json',pub)
                    body=('사람 조직 문헌 혼합 대리물성 native/GUI의 Windows export를 추가했습니다. Manifest groups HUMAN/HUMANSC4/GUI are separate; full original repository paths, immutable commits, SHA256 and bytes remain linked. Local paths use short layer-human-20261025 groups, without a private destination.\n\nScript: https://github.com/'+REPO+'/raw/'+pub['commit']+'/'+PUBLIC+'/Save-TIS-Human-Results.ps1\n\nExisting matching files may be verified and reused; conflicting or partial files are preserved. No original is deleted. This publication does not verify actual Windows saving or OneDrive sync.')
                    comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='compact_Windows_handoff_published_readback_verified',result_commit=pub['commit'],comment_url=comment['html_url'],download_files=len(entries),download_bytes=sum(i['bytes']for i in entries),groups=sorted({i['group']for i in entries}))
        except BaseException as error:receipt.update(error_type=type(error).__name__,error=str(error));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
            known=bounded.owned_descendants(pid,ticks,state['owned'])
            for p,t in known.items():
                if p!=pid and bounded.live(p,t):
                    try:os.kill(p,signal.SIGKILL)
                    except ProcessLookupError:pass
            elapsed=time.monotonic()-start;ledger=policy.load_ledger(LEDGER);ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=run.name,stage='human_reference_report_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=bounded.now()))
            raw=json.dumps(ledger,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
            temp=LEDGER.with_name('task1-budget-human-report.tmp')
            with temp.open('xb')as f:f.write(raw)
            os.replace(temp,LEDGER)
            receipt.update(finished_utc=bounded.now(),elapsed_seconds=elapsed,remaining_approved_seconds=policy.remaining_seconds(ledger),resources={k:v for k,v in state.items()if k.startswith('peak_')},free_root_bytes=shutil.disk_usage(ROOT).free,remaining_owned_children={str(p):t for p,t in known.items()if p!=pid and bounded.live(p,t)})
            new_json(receiptpath,receipt)
            for sig,handler in previous.items():signal.signal(sig,handler)
            print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
