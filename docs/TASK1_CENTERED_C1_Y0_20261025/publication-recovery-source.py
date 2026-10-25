#!/usr/bin/env python3
"""Complete postprocessing of the successful centered solve, without another PDE.

The sole correction is the explicit frozen research-module search path. All
previous source, failed attempts, raw fields and validation evidence are kept.
"""
import argparse,base64,hashlib,json,os,signal,subprocess,sys,threading,time,gzip,re,tempfile
from pathlib import Path
for key in('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path('/workspace/ngg-tis-task1');RAW=Path('/dev/shm/task1-centered-c1-y0-20261025-run-r2')
SRC=Path('/dev/shm/task1-centered-c1-y0-20261025-source-r2');OUT=Path('/dev/shm/task1-centered-c1-y0-20261025-final-r4')
sys.path[:0]=[str(SRC),str(ROOT/'tis-java'),str(ROOT/'tools')]
import centered_run as r
require=r.require
PARENT='2339c6b4d638294cb615d1eafa7d806b9a838f74'

def saved_payload():
    prior=Path('/dev/shm/task1-centered-c1-y0-20261025-post-r3/results')
    html=(prior/'index.html').read_text()
    packed=re.search(r'<script id="packed" type="application/octet-stream">(.*?)</script>',html,re.S)
    require(packed is not None,'Existing complete centered payload required')
    payload=json.loads(gzip.decompress(base64.b64decode(packed.group(1),validate=True)))
    require(payload['analysis']==json.loads((prior/'analysis.json').read_text()),'Saved centered metrics drift')
    stats=json.loads((prior/'statistics.json').read_text())
    require(all(payload[k]==stats[k] for k in ('offcenter_comparison','proofs','unit')),'Saved native/control proofs drift')
    require(payload['probe40']['status']=='complete' and payload['probe40']['numerical_checks']['all_passed'] and len(payload['probe40']['measurements'])==40,'Actual new phi40 proof required')
    require(payload['analysis']['new_PDE']==1 and payload['analysis']['new_native_RHS']==1,'Exactly one existing new native solve required')
    return payload

def short_browser(output,guard,state):
    from playwright.sync_api import sync_playwright
    html=Path('/dev/shm/task1-centered-c1-y0-20261025-post-r3/results/index.html').read_text()
    with (output/'results/index.html').open('x')as stream:stream.write(html)
    errors=[];requests=[]
    with tempfile.TemporaryDirectory(prefix='c1b-',dir='/dev/shm')as temporary:
        scratch=Path(temporary);state['scratch']=scratch
        for name in ('tmp','config','cache','dumps'):(scratch/name).mkdir()
        with sync_playwright()as engine:
            context=engine.chromium.launch_persistent_context(str(scratch/'p'),executable_path='/usr/bin/chromium',headless=True,viewport=dict(width=1400,height=1100),
                env=dict(os.environ,TMPDIR=str(scratch/'tmp'),TMP=str(scratch/'tmp'),TEMP=str(scratch/'tmp'),XDG_CONFIG_HOME=str(scratch/'config'),XDG_CACHE_HOME=str(scratch/'cache')),
                ignore_default_args=['--disable-dev-shm-usage'],args=['--disk-cache-size=0','--media-cache-size=0','--crash-dumps-dir='+str(scratch/'dumps')])
            try:
                page=context.pages[0];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text)if m.type=='error'else None)
                page.on('request',lambda q:requests.append(q.url)if q.url.startswith(('http:','https:'))else None)
                page.set_content(html,wait_until='load',timeout=30000);page.wait_for_function("document.querySelectorAll('.case-card').length===2",timeout=30000)
                count=0
                for mode in ('raw_1Vpp','skin_contact_only'):
                    for criterion in ('ROI_energy_RMS','centre20_E_RMS'):
                        for plane in ('xy','xz','yz'):
                            guard()
                            for key,value in (('mode',mode),('match',criterion),('plane',plane)):page.select_option('#'+key,value)
                            for selector in ('.field-map','.contact-map'):
                                ranges=page.locator(selector).evaluate_all('(a)=>a.map(c=>c.dataset.vmax)')
                                require(len(ranges)==2 and ranges[0]==ranges[1] and ranges[0]is not None,'Actual shared map range required')
                            count+=1
                page.select_option('#plane','xy')
                for depth in range(5):page.select_option('#depth',str(depth));guard()
                page.select_option('#mode','skin_contact_only');page.select_option('#match','ROI_energy_RMS');page.select_option('#plane','xz');page.evaluate('window.scrollTo(0,850)');page.wait_for_timeout(50)
                image=page.screenshot(type='jpeg',quality=75,full_page=False);require(len(image)<256*1024,'Bounded preview required');(output/'results/preview.jpg').write_bytes(image)
                page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(100);width=page.evaluate('document.documentElement.scrollWidth')
                require(width<=392 and not errors and not requests,'Mobile/offline/JavaScript gate failed')
                return dict(status='passed',actual_data=True,combinations=count,XY_depth_selections=5,mobile_width=390,mobile_scroll_width=width,JS_errors=errors,external_requests=requests,original_GUI_scientific_payload_unchanged=True,new_PDE_in_verification=0)
            finally:context.close()
    state.pop('scratch',None)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('publish-source','postprocess','publish-results'));stage=parser.parse_args().stage
    require(stage=='publish-results','This adapter only publishes already-verified results; no recomputation');receiptpath=OUT/'publish-results-recovery1-receipt.json';require(not receiptpath.exists(),'One new immutable publication recovery attempt')
    with r.bounded.dual_lock(ROOT/'.task1-loop.lock'),r.bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledgerpath=ROOT/'runtime/task1-budget.json';ledger=r.policy.load_ledger(ledgerpath);cap=90 if stage=='publish-source' else 180 if stage=='postprocess' else 300
        require(r.policy.remaining_seconds(ledger)>=cap,'Existing authorized finite time budget required')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();pid=os.getpid();ticks=r.bounded.ticks(pid)
        state=dict(owned={pid:ticks},peak_RSS=0,peak_tmpfs=0,peak_accounted=0);stop=threading.Event()
        receipt=dict(schema='task1-centered-post-recovery-v1',stage=stage,status='failed_preserved',started_utc=r.bounded.now(),new_PDE=0,existing_native_PDE_reused=1)
        def size(path):
            if not path.is_dir():return path.stat().st_size
            total=0
            for item in path.rglob('*'):
                try:
                    if item.is_file():total+=item.stat().st_size
                except FileNotFoundError:pass
            return total
        def guard():
            live=r.bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in live.items()if r.bounded.live(p,t)}
            rss=sum(r.bounded.rss(p)for p in live);used=sum(size(p)for p in Path('/dev/shm').glob('task1-centered-c1-y0-20261025-*'))
            if state.get('scratch') is not None and state['scratch'].exists():used+=size(state['scratch'])
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss),peak_tmpfs=max(state['peak_tmpfs'],used),peak_accounted=max(state['peak_accounted'],rss+used))
            require(time.monotonic()-start<cap and rss+used<3*r.GIB and used<r.MAX_NEW,'Original finite RSS-plus-tmpfs resource limits')
            require(r.shutil.disk_usage(ROOT).free>=2*r.GIB+ledgerpath.stat().st_size+8192,'Original2GiB plus atomic ledger reserve')
        def interrupted(sig,frame):raise TimeoutError(state.get('failure','Finite postprocess recovery stopped'))
        def monitor():
            last=0
            while not stop.wait(1):
                try:
                    guard()
                    if OUT.exists()and time.monotonic()-last>5:r.bounded.write(OUT/'heartbeat.json',dict(pid=pid,proc_start_ticks=ticks,stage=stage,updated_utc=r.bounded.now(),elapsed_seconds=time.monotonic()-start));last=time.monotonic()
                except BaseException as error:state['failure']=str(error);os.kill(pid,signal.SIGTERM);return
        old={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for sig in old:signal.signal(sig,interrupted)
        signal.setitimer(signal.ITIMER_REAL,cap);thread=threading.Thread(target=monitor,daemon=True);thread.start()
        def command(argv,data=None):
            guard();child=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
            state['owned'][child.pid]=r.bounded.ticks(child.pid)
            try:
                raw,_=child.communicate(input=data,timeout=max(.01,cap-time.monotonic()+start));require(child.returncode==0 and len(raw)<=64*1024**2,'Bounded command failed');return raw
            finally:
                if child.poll()is None:child.kill();child.wait(timeout=3)
        def api(endpoint,obj=None,method='GET'):
            argv=['gh','api','repos/'+r.REPO+'/'+endpoint,'-X',method]
            if obj is not None:argv+=['--input','-']
            body=None if obj is None else json.dumps(obj,separators=(',',':'),ensure_ascii=False).encode()
            for attempt in range(3 if method=='GET' else 1):
                try:return json.loads(command(argv,body))
                except ValueError:
                    if method!='GET' or attempt==2:raise
                    receipt.setdefault('bounded_read_retries',[]).append(dict(endpoint=endpoint,attempt=attempt+1));time.sleep(.2*(attempt+1))
        def publish(files,parent,message):
            require(api('git/ref/heads/'+r.BRANCH)['object']['sha']==parent,'Concurrent remote advance; do not overwrite')
            base=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
            for target,path in files.items():
                raw=Path(path).read_bytes();require(len(raw)<=32*1024**2,'Native32MiB individual bound')
                try:blob=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST')
                except ValueError:
                    blob=api('git/blobs/'+r.gitsha(raw));receipt.setdefault('blob_POST_response_recoveries',[]).append(target)
                require(blob['sha']==r.gitsha(raw),'Exact Git blob identity failed')
                entries.append(dict(path=target,mode='100644',type='blob',sha=blob['sha']));proof[target]=dict(path=str(path),SHA256=r.rawsha(raw),bytes=len(raw),Git_blob_SHA=blob['sha'])
            tree=api('git/trees',dict(base_tree=base,tree=entries),'POST')['sha'];commit=api('git/commits',dict(message=message,tree=tree,parents=[parent]),'POST')['sha'];receipt['created_remote_commit']=commit
            require(api('git/ref/heads/'+r.BRANCH)['object']['sha']==parent,'Concurrent remote update; preserve orphan objects')
            api('git/refs/heads/'+r.BRANCH,dict(sha=commit,force=False),'PATCH');receipt['remote_updated']=True
            require(api('git/ref/heads/'+r.BRANCH)['object']['sha']==commit,'Updated remote commit differs')
            for target,item in proof.items():
                raw=base64.b64decode(api('git/blobs/'+item['Git_blob_SHA'])['content']);require(len(raw)==item['bytes']and r.rawsha(raw)==item['SHA256'],'Native/source full immutable restore failed');item['readback_passed']=True
            return dict(status='published_readback_verified',commit=commit,files=proof)
        try:
            guard()
            if stage=='publish-source':
                require(not OUT.exists(),'Unique recovery directory only');OUT.mkdir();(OUT/'results').mkdir()
                result=publish({'tools/centered_c1_y0/centered_final_verification.py':Path(__file__)},'1d1b3208c7cc0b99fee908c1d6876b6c4eec3379','Pin postprocess path recovery for already-completed centered C1 solve; no new PDE')
                r.write_new(OUT/'source-publication.json',result);receipt.update(status='recovery_source_published',source_commit=result['commit'])
            else:
                publication=r.core.read(OUT/'source-publication.json');require(publication['status']=='published_readback_verified','Recovery source readback required')
                pre=r.core.read(RAW/'preregistration.json');require(pre['source_sha256']==r.all_sources(),'Original scientific source set drift')
                for path,digest in{**pre['source_sha256'],**pre['class_sha256'],**pre['old_input_sha256']}.items():guard();require(r.sha(path)==digest,'Original source/input/class changed')
                basis=RAW/'bases'/r.CASE_ID;require((basis/'BASIS_COMPLETE').is_file(),'Successful existing native solve required')
                validation=r.core.read(basis/'validation.json')
                for key,limit in r.GATES.items():require(0<=validation[key]<=limit,'Original five native gates required')
                nativepins={str(p):r.sha(p)for p in basis.iterdir()if p.is_file()}
                if stage=='postprocess':
                    require(not(OUT/'results/index.html').exists(),'Do not overwrite derived results')
                    payload=saved_payload()
                    for name,key in(('analysis.json','analysis'),('statistics.json',None),('native-phi-probe40.json','probe40')):
                        obj=payload[key]if key else{k:payload[k]for k in('offcenter_comparison','proofs','unit')};r.write_new(OUT/'results'/name,obj)
                    r.write_new(OUT/'results/spatial-statistics.json',{k:payload['spatial'][k]for k in('regions','shape_comparison','proofs')})
                    browser=short_browser(OUT,guard,state)
                    for path,digest in nativepins.items():require(r.sha(path)==digest,'Existing native changed during postprocess')
                    for path,digest in pre['old_input_sha256'].items():guard();require(r.sha(path)==digest,'Old reference source changed')
                    require(pre['source_sha256']==r.all_sources(),'Original scientific sources changed after postprocess')
                    r.write_new(OUT/'results/validation.json',dict(status='calculated_GUI_verified_unadopted',source_commit=PARENT,postprocess_adapter_source_commit=publication['commit'],
                        native_gates=validation,native_files_sha256=nativepins,browser_validation=browser,new_native_PDE=1,new_PDE_in_postprocess=0,
                        full_convergence_validated=False,experimentally_validated=False,inputs_unchanged=True))
                    receipt.update(status='postprocess_GUI_verified_unadopted',source_commit=publication['commit'],native_PDE_source_commit=PARENT,browser_validation=browser)
                else:
                    require(r.core.read(OUT/'results/validation.json')['status']=='calculated_GUI_verified_unadopted','Actual postprocess and GUI pass required')
                    files={r.PUBLIC_GUI+'/publication-recovery-source.py':Path(__file__)}
                    for directory,prefix in((RAW,r.PUBLIC_RUN),(OUT,r.PUBLIC_RUN+'/final-verification'),(Path('/dev/shm/task1-centered-c1-y0-20261025-post-r3'),r.PUBLIC_RUN+'/prior-postprocess-failure'),(Path('/dev/shm/task1-centered-c1-y0-20261025-run'),r.PUBLIC_RUN+'/prior-prepare-failure')):
                        for path in directory.rglob('*'):
                            if path.is_file()and 'tmp'not in path.relative_to(directory).parts and path.name not in('heartbeat.json','controller.json')and not path.name.endswith('.partial')and path!=receiptpath:
                                files[prefix+'/'+path.relative_to(directory).as_posix()]=path
                    for path in Path('/dev/shm/task1-centered-c1-y0-20261025-source').iterdir():
                        if path.suffix in('.py','.java'):files[r.PUBLIC_RUN+'/prior-source/'+path.name]=path
                    for path in(OUT/'results').iterdir():
                        if path.is_file():files[r.PUBLIC_GUI+'/'+path.name]=path
                    result=publish(files,publication['commit'],'Publish centered y=0 C1 native fields, corrected comparison GUI and all failure evidence')
                    r.write_new(OUT/'immutable-result-publication.json',result)
                    commit=result['commit'];body=f'''y=0 중앙배치 수정의 실제 새1주파수·1RHS 계산과 GUI를 완료했습니다. [GUI HTML](https://github.com/{r.REPO}/raw/{commit}/{r.PUBLIC_GUI}/index.html) · [새 배치/전기장/접촉 지도](https://github.com/{r.REPO}/blob/{commit}/{r.PUBLIC_GUI}/preview.jpg) · [y−10 대 y0 정량대조](https://github.com/{r.REPO}/blob/{commit}/{r.PUBLIC_GUI}/statistics.json).

전극중심(-10,0)/(10,0)mm,15mm사각2패드,1출력/귀환포함/3kHz/50Ω입니다. 기존y−10단일쌍과best1 f35는대조군으로보존했고기존장을이동하거나재계산하지않았습니다. 고정D50/층0.1·5·5·15mm,SC2/XY0.625/bulk14·14·40,기존PBS접촉을유지한새FVM해입니다. 기존5native게이트·동일fractional ROI·nativeφ40프로브와GUI12조합/깊이5개/390px 검증을연결했습니다. fullconvergence/실험/장비부하/안전·활성화/후보채택은보류입니다.

새native source `{PARENT}`, 경로의존성후처리복구source `{publication['commit']}`, 결과 `{commit}`. 새PDE는전체1회뿐이고복구에서는0회입니다. 준비PATH실패와후처리import실패는source/receipt와함께보존했습니다. 원시E/φ/grid/density/source/loss및모든신규연구파일{len(files)}개를GitHub불변blob에서RAM으로복원해전부SHA256/bytes검증했습니다. 이는과거전체native이관완료주장이아닙니다. 기존2GiB예약/CPU1/heap2GiB/RSS+소유tmpfs3GiB/승인시간예산을유지했고main미변경/force:false입니다.'''
                    comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='all_native_and_GUI_immutable_readback_verified_unadopted',source_commit=publication['commit'],result_commit=commit,comment_url=comment['html_url'],native_files_restored=len(nativepins),public_files_restored=len(files))
        except BaseException as error:receipt.update(error_type=type(error).__name__,error=str(error));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
            known=r.bounded.owned_descendants(pid,ticks,state['owned']);children={p:t for p,t in known.items()if p!=pid and r.bounded.live(p,t)}
            for p,t in children.items():
                if r.bounded.live(p,t):
                    try:os.kill(p,signal.SIGKILL)
                    except ProcessLookupError:pass
            end=time.monotonic()+2
            while any(r.bounded.live(p,t)for p,t in children.items())and time.monotonic()<end:time.sleep(.05)
            receipt['remaining_owned_children']={p:t for p,t in children.items()if r.bounded.live(p,t)}
            if receipt['remaining_owned_children']:receipt.update(status='failed_preserved',error='Owned child cleanup incomplete')
            elapsed=time.monotonic()-start;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=OUT.name,stage='centered_C1_recovery_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=r.bounded.now()))
            data=(json.dumps(ledger,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode();require(r.shutil.disk_usage(ROOT).free>=2*r.GIB+len(data)+4096,'Exact compact atomic ledger peak preserves2GiB');temporary=ledgerpath.with_name(ledgerpath.name+'.compact.partial');require(not temporary.exists(),'Preserve prior partial ledger');temporary.write_bytes(data);require(json.loads(temporary.read_bytes())==ledger,'Compact ledger semantic verification');os.replace(temporary,ledgerpath)
            receipt.update(finished_utc=r.bounded.now(),resources=dict(wall_seconds=elapsed,max_seconds=cap,CPU_count=1,peak_RSS_bytes=state['peak_RSS'],peak_owned_tmpfs_bytes=state['peak_tmpfs'],peak_accounted_memory_bytes=state['peak_accounted']),remaining_approved_seconds=r.policy.remaining_seconds(ledger))
            if OUT.exists()and not receiptpath.exists():r.write_new(receiptpath,receipt)
            for sig,handler in old.items():signal.signal(sig,handler)
        print(json.dumps({key:receipt.get(key)for key in('stage','status','source_commit','result_commit','comment_url','remaining_approved_seconds')}))
        if receipt['status']=='failed_preserved':raise SystemExit(1)

if __name__=='__main__':main()
