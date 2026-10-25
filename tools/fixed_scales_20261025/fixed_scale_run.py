#!/usr/bin/env python3
"""One finite locked postprocess/export owner. No PDE, installation, or cleanup."""
import sys
sys.dont_write_bytecode=True
import argparse,base64,gzip,hashlib,json,os,re,shutil,signal,subprocess,tempfile,threading,time
from pathlib import Path
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path('/workspace/ngg-tis-task1')
RUN=Path('/dev/shm/task1-fixed-scales-20261025-r2')
SRC=RUN/'source';OUT=RUN/'results'
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020'
PARENT='cdf34835dcb79c95fe4d74c1e0f63e9c29112ab0'
PUBLIC='docs/TASK1_FIXED_SCALES_20261025';PUBLIC_SRC='tools/fixed_scales_20261025'
BASE=Path('/dev/shm/task1-paper-figure-20261025/results/index.html')
LEDGER=ROOT/'runtime/task1-budget.json';GIB=1024**3
sys.path[:0]=[str(SRC),str(ROOT/'tools')]
import task1_bounded_continuation as bounded
import task1_resource_policy as policy

def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write_new(p,obj):
    with Path(p).open('x',encoding='utf-8')as f:json.dump(obj,f,ensure_ascii=False,allow_nan=False,indent=2)
def source_pins():return {str(p):sha(p)for p in SRC.iterdir()if p.suffix in ('.py','.ps1')}
def total_size(p):return sum(x.stat().st_size for x in Path(p).rglob('*')if x.is_file())

def browser_check(html,guard,state):
    from playwright.sync_api import sync_playwright
    errors=[];requests=[]
    with tempfile.TemporaryDirectory(prefix='fxs-',dir='/dev/shm')as temporary:
        scratch=Path(temporary);state['scratch']=scratch
        for name in ('tmp','config','cache','dumps'):(scratch/name).mkdir()
        with sync_playwright()as engine:
            context=engine.chromium.launch_persistent_context(str(scratch/'p'),executable_path='/usr/bin/chromium',headless=True,viewport=dict(width=1500,height=1100),
                env=dict(os.environ,TMPDIR=str(scratch/'tmp'),TMP=str(scratch/'tmp'),TEMP=str(scratch/'tmp'),XDG_CONFIG_HOME=str(scratch/'config'),XDG_CACHE_HOME=str(scratch/'cache')),
                ignore_default_args=['--disable-dev-shm-usage'],args=['--disk-cache-size=0','--media-cache-size=0','--crash-dumps-dir='+str(scratch/'dumps')])
            try:
                page=context.pages[0];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text)if m.type=='error'else None)
                page.on('request',lambda q:requests.append(q.url)if q.url.startswith(('http:','https:'))else None)
                page.set_content(html,wait_until='load');page.wait_for_function('window.task1PaperFigure && window.task1FieldShape && window.task1Best1Pair && window.task1FixedScales',timeout=30000)
                first=page.evaluate('window.task1FixedScales.validateForTest()');require(first.get('passed')is True,'Initial fixed-axis/physics checks: '+str(first))
                counts=dict(paper=0,instant=0,original=0)
                def check():
                    guard();v=page.evaluate('window.task1FixedScales.validateForTest(true)');require(v.get('passed')is True,'Variable change modified a fixed axis: '+str(v));return v
                for mode in ('raw_1Vpp','skin_contact_only'):
                    for match in ('ROI_energy_RMS','centre20_E_RMS'):
                        page.select_option('#mode',mode);page.select_option('#match',match)
                        for plane in page.locator('#paper-plane option').evaluate_all('(a)=>a.map(x=>x.value)'):
                            for direction in ('x','y','z'):
                                for color in ('linear','log'):
                                    for window in ('100','2'):
                                        page.evaluate('(v)=>{for(const [id,value]of Object.entries(v))document.getElementById(id).value=value;document.getElementById("paper-color").dispatchEvent(new Event("change",{bubbles:true}));}',{'paper-plane':plane,'paper-direction':direction,'paper-color':color,'paper-window':window})
                                        check();counts['paper']+=1
                        for plane in page.locator('#shape-plane option').evaluate_all('(a)=>a.map(x=>x.value)'):
                            for frequency in ('all','3000','3030'):
                                for t in (0,.083333333,16.666667):
                                    page.evaluate('(v)=>{for(const [id,value]of Object.entries(v))document.getElementById(id).value=value;document.getElementById("shape-time").dispatchEvent(new Event("input",{bubbles:true}));}',{'shape-plane':plane,'shape-frequency':frequency,'shape-time':str(t)})
                                    check();counts['instant']+=1
                        for plane in ('xz','yz','xy'):
                            page.select_option('#plane',plane)
                            for depth in (range(5)if plane=='xy'else(0,)):
                                if plane=='xy':page.select_option('#depth',str(depth))
                                check();counts['original']+=1
                # Spatial axes are fixed physical faces and XY is y-up in all layers.
                page.select_option('#paper-plane','XY_17.5');page.select_option('#shape-plane','XY_17.5');page.select_option('#plane','xy');value=check()
                for row in value['canvases']:
                    if row['id'].startswith(('paper-map-','shape-'))or row['id'].endswith('-field'):require(row['axis_orientation']=='y_up','XY axis orientation mismatch')
                    if row['id'].startswith('paper-profile-'):require(row['coordinate_min']==-25 and row['coordinate_max']==25,'Fixed horizontal coordinate range')
                page.select_option('#paper-plane','XZ');value=check()
                for row in value['canvases']:
                    if row['id'].startswith('paper-profile-'):require(row['coordinate_min']==0 and row['coordinate_max']==25.1,'Fixed depth coordinate range')
                page.select_option('#mode','skin_contact_only');page.select_option('#match','ROI_energy_RMS');page.select_option('#paper-direction','x');page.select_option('#paper-color','log');page.select_option('#paper-window','100')
                page.select_option('#shape-plane','XZ');page.select_option('#shape-frequency','all');page.select_option('#plane','xz')
                final=page.evaluate('window.task1FixedScales.validateForTest()');require(final.get('passed')is True,'Final fixed-axis/physics check')
                page.locator('#paper-figure').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'field-shape-preview.jpg'),type='jpeg',quality=80,full_page=False)
                page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(100);width=page.evaluate('document.documentElement.scrollWidth');require(width<=392,'Mobile overflow')
                require(not errors and not requests,'Offline JavaScript errors')
                return dict(status='passed',actual_data=True,selection_combinations=counts,total_combinations=sum(counts.values()),mobile_width=390,mobile_scroll_width=width,JS_errors=errors,external_requests=requests,initial_fixed_axis_checks=first,final_fixed_axis_checks=final,new_PDE=0)
            finally:context.close()
    state.pop('scratch',None)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('prepare','publish-source','build','publish-results','export'));stage=parser.parse_args().stage
    receiptpath=RUN/(stage+'-receipt.json');require(not receiptpath.exists(),'No repeated immutable stage; preserve failure and use reviewed recovery')
    with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledger=policy.load_ledger(LEDGER);cap={'prepare':45,'publish-source':90,'build':240,'publish-results':240,'export':150}[stage]
        require(policy.remaining_seconds(ledger)>=cap,'Finite approved time admission failed')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();pid=os.getpid();ticks=bounded.ticks(pid)
        state=dict(owned={pid:ticks},peak_RSS=0,peak_tmpfs=0,peak_accounted=0);stop=threading.Event()
        receipt=dict(schema='task1-field-shape-stage-v1',stage=stage,status='failed_preserved',started_utc=bounded.now(),pid=pid,proc_start_ticks=ticks,new_PDE=0,remaining_before=policy.remaining_seconds(ledger))
        def guard():
            known=bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in known.items()if bounded.live(p,t)}
            rss=sum(bounded.rss(p)for p in live);used=total_size(RUN)+total_size('/dev/shm/task1-fixed-scales-20261025')+total_size('/dev/shm/task1-paper-figure-20261025')+total_size('/dev/shm/task1-field-shape-export-20261025')+sum(total_size(p)if p.is_dir()else p.stat().st_size for p in Path('/dev/shm').glob('task1-centered-c1-y0-20261025-*'))
            if state.get('scratch')is not None and state['scratch'].exists():used+=total_size(state['scratch'])
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss),peak_tmpfs=max(state['peak_tmpfs'],used),peak_accounted=max(state['peak_accounted'],rss+used))
            require(time.monotonic()-start<cap and rss+used<3*GIB and total_size(RUN)<128*1024**2,'Finite RSS+tmpfs/time/output gate')
            require(shutil.disk_usage(ROOT).free>=2*GIB+LEDGER.stat().st_size+8192,'Original2GiB plus compact atomic-ledger reserve')
        def interrupt(sig,frame):raise TimeoutError(state.get('failure','Finite field-shape stage interrupted'))
        def monitor():
            last=0
            while not stop.wait(1):
                try:
                    guard()
                    if time.monotonic()-last>5:
                        # Mutable live checkpoint only; immutable receipts remain separate.
                        (RUN/'heartbeat.json').write_text(json.dumps(dict(stage=stage,pid=pid,proc_start_ticks=ticks,updated_utc=bounded.now(),new_PDE=0)))
                        last=time.monotonic()
                except BaseException as e:state['failure']=str(e);os.kill(pid,signal.SIGTERM);return
        old={s:signal.getsignal(s)for s in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for s in old:signal.signal(s,interrupt)
        signal.setitimer(signal.ITIMER_REAL,cap);thread=threading.Thread(target=monitor,daemon=True);thread.start()
        def command(argv,body=None):
            guard();child=subprocess.Popen(argv,cwd=SRC,stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(RUN)))
            state['owned'][child.pid]=bounded.ticks(child.pid)
            try:
                raw,err=child.communicate(input=body,timeout=max(.01,cap-time.monotonic()+start));require(child.returncode==0 and len(raw)<64*1024**2,'Bounded subprocess failed: '+err.decode(errors='replace')[:600]);return raw
            finally:
                if child.poll()is None:child.kill();child.wait(timeout=3)
        def api(endpoint,obj=None,method='GET'):
            argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
            if obj is not None:argv+=['--input','-']
            return json.loads(command(argv,None if obj is None else json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode()))
        def publish(files,parent,message):
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrent remote update; no overwrite')
            treebase=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
            for target,p in files.items():
                raw=Path(p).read_bytes();require(len(raw)<32*1024**2,'32MiB individual publication gate')
                expected=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                item=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST');require(item['sha']==expected,'Exact Gitblob identity')
                entries.append(dict(path=target,mode='100644',type='blob',sha=expected));proof[target]=dict(SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),Git_blob_SHA=expected)
            tree=api('git/trees',dict(base_tree=treebase,tree=entries),'POST')['sha']
            commit=api('git/commits',dict(message=message,tree=tree,parents=[parent]),'POST')['sha'];receipt['remote_commit_created']=commit
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Remote advanced; preserve immutable objects')
            api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');receipt['remote_ref_updated']=True
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Remotehead mismatch')
            for target,item in proof.items():
                raw=base64.b64decode(api('git/blobs/'+item['Git_blob_SHA'])['content']);require(len(raw)==item['bytes']and hashlib.sha256(raw).hexdigest()==item['SHA256'],'Immutable full readback mismatch');item['readback_passed']=True
            return dict(status='published_readback_verified',commit=commit,files=proof)
        try:
            guard()
            import field_shape_data as data
            if stage=='prepare':
                pins=data.required_inputs();pins[str(BASE)]=sha(BASE)
                tests=command([sys.executable,'-B','-c','import sys,unittest; suite=unittest.defaultTestLoader.discover(sys.argv[1],pattern="test_*.py"); result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite); sys.exit(0 if result.wasSuccessful() else 1)',str(SRC)]).decode()
                (RUN/'prepare-tests.log').write_text(tests)
                write_new(RUN/'preregistration.json',dict(schema='task1-field-shape-preregistration-v1',question='Lock all stacked-GUI electric-field color/axis ranges and contact J across every supported selection; preserve cached numerical data',
                    new_PDE=0,parent_topic_commit=PARENT,native_source_result_commit='b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe',cached_display_result_commit='2b4abb6206fe1e3d0dc30c7d3bd7e1ba350da077',source_sha256=source_pins(),input_sha256=pins,CPU=1,RSS_plus_owned_tmpfs_bytes=3*GIB,max_new_tmpfs_bytes=128*1024**2,
                    minimum_free_disk_bytes=2*GIB,new_validation='Fixed all-selection phase-independent E/J contract; same unsigned/signed limits on18canvases across336paper+252instant+28original selections; XYorientation; preserved packed scientific data; no new native field re-decode',
                    Windows_destination_connected=False,OneDrive_sync_verified=False,full_convergence_validated=False,fat_new_batch_executed=False))
                receipt['status']='prepared_preregistered_no_PDE'
            else:
                pre=read(RUN/'preregistration.json');require(pre['source_sha256']==source_pins(),'Preregistered source drift')
                for p,digest in pre['input_sha256'].items():guard();require(sha(p)==digest,'Pinned input drift: '+p)
                if stage=='publish-source':
                    files={PUBLIC_SRC+'/'+p.name:p for p in SRC.iterdir()if p.suffix in ('.py','.ps1')}
                    files[PUBLIC+'/preregistration.json']=RUN/'preregistration.json'
                    result=publish(files,PARENT,'Pin fixed electric-field and graph-axis scale contract across all GUI layers; cached data only')
                    write_new(RUN/'source-publication.json',result);receipt.update(status='source_published_readback_verified',source_commit=result['commit'])
                else:
                    source=read(RUN/'source-publication.json');require(source['status']=='published_readback_verified','Source publication prerequisite')
                    if stage=='build':
                        import field_shape_gui as gui
                        payload=data.build(guard,pre['input_sha256']);payload['display_source_commit']=source['commit']
                        require(payload['analysis']==read('/dev/shm/task1-centered-c1-y0-20261025-final-r4/results/analysis.json'),'Frozen statistics changed')
                        write_new(OUT/'field-shape.json',payload)
                        write_new(OUT/'fixed-scale-contract.json',payload['fixed_scale_contract'])
                        html=gui.render(BASE.read_text(),payload)
                        with (OUT/'index.html').open('x')as f:f.write(html)
                        browser=browser_check(html,guard,state)
                        for p,digest in pre['input_sha256'].items():guard();require(sha(p)==digest,'Pinned input changed after display')
                        write_new(OUT/'validation.json',dict(status='cached_fields_GUI_verified_unadopted',source_commit=source['commit'],native_source_result_commit='b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe',cached_display_result_commit='2b4abb6206fe1e3d0dc30c7d3bd7e1ba350da077',parent_topic_commit=PARENT,new_PDE=0,
                            input_sha256=pre['input_sha256'],proofs=payload['proofs'],paper_proofs=payload['paper_proofs'],paper_reference=payload['paper_reference'],fixed_scale_contract=payload['fixed_scale_contract'],fixed_scale_proof=payload['fixed_scale_proof'],browser=browser,Windows_write_verified=False,OneDrive_sync_verified=False,
                            full_convergence_validated=False,fat_new_batch_executed=False,experimentally_validated=False))
                        receipt.update(status='cached_field_shape_GUI_verified',browser=browser)
                    elif stage=='publish-results':
                        require(read(OUT/'validation.json')['status']=='cached_fields_GUI_verified_unadopted','Actual GUI validation prerequisite')
                        files={PUBLIC+'/'+p.name:p for p in OUT.iterdir()if p.is_file()}
                        files[PUBLIC+'/evidence/axis-only-v1-build-receipt.json']=Path('/dev/shm/task1-fixed-scales-20261025/build-receipt.json')
                        files[PUBLIC+'/evidence/axis-only-v1-preregistration.json']=Path('/dev/shm/task1-fixed-scales-20261025/preregistration.json')
                        for name in ('prepare-receipt.json','prepare-tests.log','build-receipt.json'):files[PUBLIC+'/evidence/'+name]=RUN/name
                        result=publish(files,source['commit'],'Publish globally fixed E/J scales and plot axes across all GUI selections; preserve scientific data')
                        write_new(RUN/'result-publication.json',result);receipt.update(status='GUI_published_readback_verified',result_commit=result['commit'])
                    else:
                        import windows_export
                        oldpub=read('/dev/shm/task1-centered-c1-y0-20261025-final-r4/immutable-result-publication.json');newpub=read(RUN/'result-publication.json')
                        entries=[]
                        for pub in (oldpub,newpub):
                            require(pub['status']=='published_readback_verified','Only fully readback verified results exportable')
                            for path,item in pub['files'].items():
                                require(item['readback_passed'],'Readback prerequisite')
                                entries.append(dict(path=path,commit=pub['commit'],SHA256=item['SHA256'],bytes=item['bytes']))
                        script=windows_export.render(entries)
                        with (OUT/'Save-TIS-Results.ps1').open('x',encoding='ascii')as f:f.write(script)
                        write_new(OUT/'windows-export-manifest.json',dict(schema='task1-windows-export-manifest-v1',files=entries,total_bytes=sum(x['bytes']for x in entries),
                            Windows_files_verified=False,OneDrive_sync_verified=False,private_destination_excluded=True,automatic_sync_configured=False))
                        files={PUBLIC+'/'+name:OUT/name for name in ('Save-TIS-Results.ps1','windows-export-manifest.json')}
                        result=publish(files,newpub['commit'],'Add immutable SHA256-verified Windows download handoff without exposing private destination')
                        write_new(RUN/'export-publication.json',result)
                        contract=read(OUT/'fixed-scale-contract.json')
                        body='''모든 GUI 계층의 자동 범위를 제거했습니다. 원 RMS·접촉 지도, 순간 벡터·화살표 분모, 논문형 carrier/변조 지도, 네 파형과 두 선 프로파일에 전역 고정 눈금을 적용했습니다. E 지도·프로파일0–'''+str(contract['electric_field']['upper_V_m'])+'''V/m, 파형±같은 상한, J0–'''+str(contract['current_density']['upper_A_m2'])+'''A/m²입니다. 전체 저장 조건과 위상 독립 복소장 상한을 포함해 한 번 산출했고 단면/깊이/방향/시간/주파수/구동/RMS매칭 변경으로 재조정하지 않습니다. XY는+y위쪽, 깊이는+z아래쪽, 프로파일 좌표틀은수평±25mm/깊이0–25.1mm로 통일했습니다.

GUI: https://github.com/'''+REPO+'/raw/'+newpub['commit']+'/'+PUBLIC+'''/index.html

최신 Windows 다운로드·SHA256 검증: https://github.com/'''+REPO+'/raw/'+result['commit']+'/'+PUBLIC+'''/Save-TIS-Results.ps1

기존 packed 과학 데이터와 Float64 통계는 byte보존하고 표시 코드/CSP만 새 버전으로 바꿨습니다. 기존 수렴 실패·접촉/실험 보류를 유지하며 새 PDE/원시 복소장 decode/fat검증은0입니다. 실제 Windows/OneDrive 저장은 직접 연결이 없어 미확인입니다.'''
                        comment=api('issues/2/comments',dict(body=body),'POST')
                        receipt.update(status='Windows_handoff_published_direct_connection_unavailable',result_commit=result['commit'],comment_url=comment['html_url'],download_files=len(entries),download_bytes=sum(x['bytes']for x in entries))
        except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
            known=bounded.owned_descendants(pid,ticks,state['owned'])
            for p,t in known.items():
                if p!=pid and bounded.live(p,t):
                    try:os.kill(p,signal.SIGKILL)
                    except ProcessLookupError:pass
            elapsed=time.monotonic()-start;ledger=policy.load_ledger(LEDGER)
            ledger['spent_seconds']+=elapsed;ledger.setdefault('runs',[]).append(dict(run_id=RUN.name,stage='field_shape_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=bounded.now()))
            raw=json.dumps(ledger,ensure_ascii=False,separators=(',',':')).encode()
            require(shutil.disk_usage(ROOT).free>=2*GIB+len(raw)+8192,'Exact compact atomic-ledger write admission')
            temporary=LEDGER.with_name('task1-budget-field-shape.tmp')
            with temporary.open('xb')as f:f.write(raw)
            os.replace(temporary,LEDGER)
            receipt.update(finished_utc=bounded.now(),elapsed_seconds=elapsed,remaining_approved_seconds=policy.remaining_seconds(ledger),resources={k:v for k,v in state.items()if k.startswith('peak_')},
                free_workspace_bytes=shutil.disk_usage(ROOT).free,remaining_owned_children={str(p):t for p,t in known.items()if p!=pid and bounded.live(p,t)})
            write_new(receiptpath,receipt)
            for s,h in old.items():signal.signal(s,h)
            print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
