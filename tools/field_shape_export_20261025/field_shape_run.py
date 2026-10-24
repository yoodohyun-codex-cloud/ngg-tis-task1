#!/usr/bin/env python3
"""One finite locked postprocess/export owner. No PDE, installation, or cleanup."""
import sys
sys.dont_write_bytecode=True
import argparse,base64,gzip,hashlib,json,os,re,shutil,signal,subprocess,tempfile,threading,time
from pathlib import Path
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path('/workspace/ngg-tis-task1')
RUN=Path('/dev/shm/task1-field-shape-export-20261025')
SRC=RUN/'source';OUT=RUN/'results'
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020'
PARENT='b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe'
PUBLIC='docs/TASK1_FIELD_SHAPE_20261025';PUBLIC_SRC='tools/field_shape_export_20261025'
BASE=Path('/dev/shm/task1-centered-c1-y0-20261025-final-r4/results/index.html')
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
    with tempfile.TemporaryDirectory(prefix='fsv-',dir='/dev/shm')as temporary:
        scratch=Path(temporary);state['scratch']=scratch
        for name in ('tmp','config','cache','dumps'):(scratch/name).mkdir()
        with sync_playwright()as engine:
            context=engine.chromium.launch_persistent_context(str(scratch/'p'),executable_path='/usr/bin/chromium',headless=True,viewport=dict(width=1440,height=1100),
                env=dict(os.environ,TMPDIR=str(scratch/'tmp'),TMP=str(scratch/'tmp'),TEMP=str(scratch/'tmp'),XDG_CONFIG_HOME=str(scratch/'config'),XDG_CACHE_HOME=str(scratch/'cache')),
                ignore_default_args=['--disable-dev-shm-usage'],args=['--disk-cache-size=0','--media-cache-size=0','--crash-dumps-dir='+str(scratch/'dumps')])
            try:
                page=context.pages[0];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text)if m.type=='error'else None)
                page.on('request',lambda q:requests.append(q.url)if q.url.startswith(('http:','https:'))else None)
                page.set_content(html,wait_until='load');page.wait_for_function('window.task1FieldShape && window.task1Best1Pair',timeout=30000)
                # GUI module supplies scientific/geometry invariants at the actual saved data.
                info=page.evaluate('window.task1FieldShape.validateForTest()')
                require(info.get('passed')is True,'Field shape actual browser invariants failed')
                combinations=0
                for mode in ('raw_1Vpp','skin_contact_only'):
                    for match in ('ROI_energy_RMS','centre20_E_RMS'):
                        page.select_option('#mode',mode);page.select_option('#match',match)
                        page.select_option('#shape-mode',mode);page.select_option('#shape-match',match)
                        for plane in page.locator('#shape-plane option').evaluate_all('(a)=>a.map(x=>x.value)'):
                            for tone in ('all','3000','3030'):
                                guard();page.select_option('#shape-plane',plane);page.select_option('#shape-frequency',tone)
                                for t in (0,.083333333,8.333333,16.666667):
                                    page.eval_on_selector('#shape-time','(e,t)=>{e.value=String(t);e.dispatchEvent(new Event("input",{bubbles:true}));}',t)
                                    check=page.evaluate('window.task1FieldShape.validateForTest()');require(check.get('passed')is True,'Interactive physical/vector invariants failed')
                                combinations+=1
                page.select_option('#mode','skin_contact_only');page.select_option('#match','ROI_energy_RMS')
                page.select_option('#shape-mode','skin_contact_only');page.select_option('#shape-match','ROI_energy_RMS');page.select_option('#shape-plane','XZ');page.select_option('#shape-frequency','all')
                page.eval_on_selector('#shape-time','e=>{e.value=".083333333";e.dispatchEvent(new Event("input",{bubbles:true}));}')
                page.locator('#field-shape').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'field-shape-preview.jpg'),type='jpeg',quality=80,full_page=False)
                page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(100)
                width=page.evaluate('document.documentElement.scrollWidth');require(width<=392,'Mobile overflow')
                require(not errors and not requests,'Offline JavaScript/browser errors')
                return dict(status='passed',actual_data=True,plane_tone_normalization_combinations=combinations,time_samples_per_combination=4,
                    mobile_width=390,mobile_scroll_width=width,JS_errors=errors,external_requests=requests,field_checks=info,new_PDE=0)
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
            rss=sum(bounded.rss(p)for p in live);used=total_size(RUN)+sum(total_size(p)if p.is_dir()else p.stat().st_size for p in Path('/dev/shm').glob('task1-centered-c1-y0-20261025-*'))
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
                tests=command([sys.executable,'-B','-m','unittest','discover','-s',str(SRC),'-p','test_*.py','-v']).decode()
                (RUN/'prepare-tests.log').write_text(tests)
                write_new(RUN/'preregistration.json',dict(schema='task1-field-shape-preregistration-v1',question='Show actual cached complex-vector spatial field shape and export immutable results to user-selected Windows storage',
                    new_PDE=0,parent_result_commit=PARENT,source_sha256=source_pins(),input_sha256=pins,CPU=1,RSS_plus_owned_tmpfs_bytes=3*GIB,max_new_tmpfs_bytes=128*1024**2,
                    minimum_free_disk_bytes=2*GIB,new_validation='cached carrier RMS against existing Float64 reference; display Float32 conversion error bound; phase synthesis; same map scales; offline mobile browser',
                    Windows_destination_connected=False,OneDrive_sync_verified=False,full_convergence_validated=False,fat_new_batch_executed=False))
                receipt['status']='prepared_preregistered_no_PDE'
            else:
                pre=read(RUN/'preregistration.json');require(pre['source_sha256']==source_pins(),'Preregistered source drift')
                for p,digest in pre['input_sha256'].items():guard();require(sha(p)==digest,'Pinned input drift: '+p)
                if stage=='publish-source':
                    files={PUBLIC_SRC+'/'+p.name:p for p in SRC.iterdir()if p.suffix in ('.py','.ps1')}
                    files[PUBLIC+'/preregistration.json']=RUN/'preregistration.json'
                    result=publish(files,PARENT,'Pin finite cached electric-field shape GUI and Windows export sources; no new PDE')
                    write_new(RUN/'source-publication.json',result);receipt.update(status='source_published_readback_verified',source_commit=result['commit'])
                else:
                    source=read(RUN/'source-publication.json');require(source['status']=='published_readback_verified','Source publication prerequisite')
                    if stage=='build':
                        import field_shape_gui as gui
                        payload=data.build(guard,pre['input_sha256']);payload['display_source_commit']=source['commit']
                        require(payload['analysis']==read('/dev/shm/task1-centered-c1-y0-20261025-final-r4/results/analysis.json'),'Frozen statistics changed')
                        write_new(OUT/'field-shape.json',payload)
                        html=gui.render(BASE.read_text(),payload)
                        with (OUT/'index.html').open('x')as f:f.write(html)
                        browser=browser_check(html,guard,state)
                        for p,digest in pre['input_sha256'].items():guard();require(sha(p)==digest,'Pinned input changed after display')
                        write_new(OUT/'validation.json',dict(status='cached_fields_GUI_verified_unadopted',source_commit=source['commit'],native_source_result_commit=PARENT,new_PDE=0,
                            input_sha256=pre['input_sha256'],proofs=payload['proofs'],browser=browser,Windows_write_verified=False,OneDrive_sync_verified=False,
                            full_convergence_validated=False,fat_new_batch_executed=False,experimentally_validated=False))
                        receipt.update(status='cached_field_shape_GUI_verified',browser=browser)
                    elif stage=='publish-results':
                        require(read(OUT/'validation.json')['status']=='cached_fields_GUI_verified_unadopted','Actual GUI validation prerequisite')
                        files={PUBLIC+'/'+p.name:p for p in OUT.iterdir()if p.is_file()}
                        for name in ('prepare-receipt.json','prepare-tests.log','build-receipt.json'):files[PUBLIC+'/evidence/'+name]=RUN/name
                        result=publish(files,source['commit'],'Publish native electric-field direction and shape comparison; preserve RMS metrics and validation holds')
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
                        body='''새 field-shape GUI에 native complex E(t)의 세기·방향과 단면/전극 배치를 추가했습니다. RMS와 순간 벡터를 구분하고 같은 주파수의 두 출력은 복소 합산했습니다. 기존 y=0 C1/best1 수치·원본·수렴 보류는 유지했고 이번 단계 새 PDE는0입니다.\n\nGUI: https://github.com/'''+REPO+'/raw/'+newpub['commit']+'/'+PUBLIC+'''/index.html\n\nWindows 다운로드·SHA256 검증 스크립트: https://github.com/'''+REPO+'/raw/'+result['commit']+'/'+PUBLIC+'''/Save-TIS-Results.ps1\n\n사용자가 지정한 로컬 저장 경로는 비공개 runtime 설정으로 보존했습니다. 현재 cloud에는 Windows/OneDrive 직접 연결이 없으므로 실제 Windows 저장·OneDrive 동기화·cloud 공간 회수는 완료 주장하지 않습니다. 사용자 지정 경로·개인정보는 공개 파일에 포함하지 않았습니다. fat 새 baseline/bulk 요청은 별도 미실행 상태이며 이 GUI 후처리로 대체하지 않습니다.'''
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
